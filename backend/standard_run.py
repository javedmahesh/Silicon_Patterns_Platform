"""The Standard Run: one full pipeline execution, recorded run-level.

A Standard Run is exactly a ``run all`` (the full orchestrator pipeline — no engine
logic is duplicated here; it delegates to orchestrator.Orchestrator.run_pipeline).
Both the scheduler (trigger='scheduled') and the manual CLI (trigger='manual') call
:func:`execute_standard_run`, so manual and scheduled runs execute the identical
pipeline. The only differences are the recorded ``trigger`` and whether an Outlook
summary is sent afterwards (scheduled only).

Each run:
  * gets a unique run id (``run-YYYYMMDD-HHMMSS``, shared with its per-stage
    pipeline_runs rows via ``pipeline_id``),
  * writes ONE ``pipeline_executions`` row (start/finish/duration/trigger/status +
    per-engine stats + platform totals + notification outcome),
  * is guarded against overlap by a Postgres advisory lock (cross-process) or an
    in-process lock (SQLite/tests) — a second run started while one is active is
    refused with :class:`RunInProgress` rather than run concurrently.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.config import Settings
from master_db.models import (
    Company,
    DecisionMaker,
    Job,
    LeadScore,
    Opportunity,
    PipelineExecution,
)
from orchestrator.orchestrator import Orchestrator, StageResult

logger = logging.getLogger("backend.standard_run")

# The Standard Run IS the full `run all` pipeline (orchestrator.PIPELINE_ORDER), so
# manual (`run all`) and scheduled runs execute the identical pipeline. That order
# runs the 7 core engines the spec names — industry, blog, career,
# decision_maker_intelligence, scoring, leadership, engagement — plus the optional
# annual_list / company_news file-feed ingestors, which no-op when no feed is
# present. `None` here means "the full PIPELINE_ORDER" (run_pipeline's own default),
# keeping the component list in one place; override per-call only for tests.
STANDARD_RUN_COMPONENTS: list[str] | None = None

# Fixed advisory-lock key (arbitrary constant, unique to the Standard Run). Cross-
# process singleton on Postgres; the in-process lock covers SQLite/tests.
_ADVISORY_LOCK_KEY = 748291013
_local_lock = threading.Lock()


class RunInProgress(Exception):
    """Another Standard Run holds the lock — this one is refused (no overlap)."""


class _RunLock:
    """Best-effort mutual exclusion for a Standard Run. Postgres: a session-level
    advisory lock (survives across processes/instances). Otherwise: a process-local
    lock. Both are non-blocking — if not acquired, the run is refused."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._is_pg = session.get_bind().dialect.name == "postgresql"
        self._local_held = False
        self._pg_held = False

    def __enter__(self) -> "_RunLock":
        if not _local_lock.acquire(blocking=False):
            raise RunInProgress("another Standard Run is already in progress (this process)")
        self._local_held = True
        if self._is_pg:
            got = self.session.execute(
                text("SELECT pg_try_advisory_lock(:k)"), {"k": _ADVISORY_LOCK_KEY}
            ).scalar()
            if not got:
                _local_lock.release()
                self._local_held = False
                raise RunInProgress("another Standard Run is already in progress (cluster)")
            self._pg_held = True
        return self

    def __exit__(self, *exc) -> None:
        if self._pg_held:
            try:
                self.session.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _ADVISORY_LOCK_KEY})
                self.session.commit()
            except Exception:  # pragma: no cover - unlock is best-effort
                logger.warning("failed to release advisory lock", exc_info=True)
        if self._local_held:
            _local_lock.release()


def _platform_totals(session: Session) -> dict[str, int]:
    """Snapshot the headline counts shown in the run summary / notification."""
    def c(model) -> int:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)

    return {
        "companies": c(Company),
        "opportunities": c(Opportunity),
        "decision_makers": c(DecisionMaker),
        "jobs": c(Job),
        "leads_scored": c(LeadScore),
    }


def _stage_dict(r: StageResult) -> dict:
    return {
        "component": r.component,
        "status": r.status,
        "processed": r.processed,
        "created": r.created,
        "updated": r.updated,
        "review": r.review,
        "duration_ms": r.duration_ms,
        "errors": list(r.errors),
        "notes": r.notes,
    }


def _overall_status(results: list[StageResult]) -> str:
    """failed only if EVERY stage failed; partial if any failed/partial (or a stage
    queued review items); else success. 'skipped' stages (no creds / no feed) are
    neutral — a normal decision_maker skip must not turn the run yellow."""
    statuses = [r.status for r in results]
    real = [s for s in statuses if s != "skipped"]
    if real and all(s == "failed" for s in real):
        return "failed"
    if any(s in ("failed", "partial") for s in statuses) or any(r.review for r in results):
        return "partial"
    return "success"


def execute_standard_run(
    session: Session,
    settings: Settings,
    *,
    trigger: str = "manual",
    slot: str | None = None,
    notify: bool = False,
    run_engine: bool = False,
    components: list[str] | None = None,
    company_limit: int | None = None,
    stage_trigger: str | None = None,
) -> tuple[PipelineExecution, list[StageResult]]:
    """Run the Standard Run once, recording a ``pipeline_executions`` row.

    ``trigger`` is the execution-level label ('manual' | 'scheduled'). ``stage_trigger``
    is what each per-stage pipeline_runs row records (defaults to ``trigger``; the CLI
    passes its own manual|daily|weekly label so cadence reporting is unchanged).
    ``company_limit`` is the benchmark cap for decision_maker_intelligence (unused in
    normal runs).

    Raises :class:`RunInProgress` if another run is active (overlap prevention). Never
    raises for a notification failure — that is caught and recorded on the row.
    """
    comps = components if components is not None else STANDARD_RUN_COMPONENTS
    # Microsecond suffix keeps the id (and its UNIQUE constraint) collision-free even
    # for two runs started in the same second (e.g. a manual run right after a slot).
    _now = datetime.now(timezone.utc)
    run_id = _now.strftime("run-%Y%m%d-%H%M%S-") + f"{_now.microsecond:06d}"

    with _RunLock(session):
        execution = PipelineExecution(
            run_id=run_id, trigger=trigger, scheduled_slot=slot, status="running",
            started_at=datetime.now(timezone.utc), notification_status="pending",
        )
        session.add(execution)
        session.commit()
        logger.info("Standard Run %s started (trigger=%s slot=%s)", run_id, trigger, slot)

        orch = Orchestrator(session, run_engine=run_engine, trigger=(stage_trigger or trigger),
                            company_limit=company_limit)
        results = orch.run_pipeline(components=comps, pipeline_id=run_id)

        finished = datetime.now(timezone.utc)
        started = execution.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        execution.finished_at = finished
        execution.duration_ms = max(0, int((finished - started).total_seconds() * 1000))
        execution.status = _overall_status(results)
        execution.stages = [_stage_dict(r) for r in results]
        execution.totals = _platform_totals(session)
        execution.records_processed = sum(r.processed for r in results)
        execution.failure_count = sum(1 for r in results if r.status == "failed")
        execution.warning_count = sum(1 for r in results if r.status == "partial")
        session.commit()
        logger.info(
            "Standard Run %s finished: status=%s duration_ms=%d processed=%d failures=%d",
            run_id, execution.status, execution.duration_ms,
            execution.records_processed, execution.failure_count,
        )

        if notify:
            _notify(session, settings, execution)
        else:
            execution.notification_status = "skipped"
            execution.notification_detail = "manual run (notifications are sent for scheduled runs only)"
            session.commit()

        return execution, results


def _notify(session: Session, settings: Settings, execution: PipelineExecution) -> None:
    """Send the Outlook summary; a failure here is recorded but never propagates."""
    from backend import notifications

    try:
        status, detail, count = notifications.send_run_notification(session, settings, execution)
    except Exception as exc:  # pragma: no cover - defensive; notifications also guards internally
        logger.warning("run notification raised (ignored): %s", exc, exc_info=True)
        status, detail, count = "failed", f"unexpected error: {exc}", 0
    execution.notification_status = status
    execution.notification_detail = detail[:2000]
    execution.notified_count = count
    session.commit()
