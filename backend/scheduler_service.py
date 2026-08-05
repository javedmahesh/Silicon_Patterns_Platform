"""Service layer for the scheduler / run-history API (backend/routers/scheduler.py).

Read side reads the ``pipeline_executions`` rows written by backend/standard_run.py;
the write side ("run now") spins a Standard Run on a background thread so the HTTP
request returns immediately (a full run takes minutes) — reusing the exact same
execute_standard_run path as the scheduler and the CLI. No engine logic here.
"""
from __future__ import annotations

import logging
import threading

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend import notifications, repositories as repo
from backend.config import Settings
from backend.dependencies import Pagination
from backend.scheduler_config import read_config, write_config
from backend.schemas import ExecutionOut, Page, RunNowResult, SchedulerStatusOut
from backend.standard_run import RunInProgress, execute_standard_run, stale_running_cutoff
from master_db.models import PipelineExecution

logger = logging.getLogger("backend.scheduler_service")


def _notify_configured(settings: Settings) -> bool:
    return bool(
        settings.microsoft_tenant_id and settings.microsoft_client_id
        and settings.microsoft_client_secret
        and (settings.notify_sender_email or settings.bootstrap_admin_email)
    )


def _run_in_progress(session: Session) -> bool:
    """A run row is only "in progress" if it is also recent enough to still be alive.

    Without the cutoff a run killed mid-flight leaves status='running' forever and this
    answers True for good, permanently disabling "Run now" and showing a phantom run in
    the UI. Overlap itself is prevented by the advisory lock in standard_run, not here.
    """
    return session.scalar(
        select(func.count()).select_from(PipelineExecution).where(
            PipelineExecution.status == "running",
            PipelineExecution.started_at >= stale_running_cutoff(),
        )
    ) > 0


def scheduler_status(session: Session, settings: Settings, scheduler) -> SchedulerStatusOut:
    # Effective (runtime-editable) schedule — the persisted override over env defaults.
    cfg = read_config(session, settings)
    last = session.scalar(select(PipelineExecution).order_by(PipelineExecution.id.desc()))
    next_run = scheduler.next_run_at(cfg.schedule_times) if scheduler is not None else None
    return SchedulerStatusOut(
        enabled=cfg.enabled,
        running=scheduler.is_running() if scheduler is not None else False,
        schedule_times=cfg.schedule_times,
        grace_minutes=cfg.grace_minutes,
        next_run=next_run,
        notify_mode=settings.notify_mode,
        notify_configured=_notify_configured(settings),
        active_recipient_count=len(repo.list_active_users(session)),
        is_run_in_progress=_run_in_progress(session),
        last_run=ExecutionOut.model_validate(last) if last else None,
    )


def update_scheduler_config(session: Session, settings: Settings, *, payload, actor) -> None:
    """Persist a new schedule (times / enabled / grace). Raises ValueError on bad input;
    the scheduler thread picks up the change on its next tick."""
    write_config(
        session, schedule_times=payload.schedule_times, enabled=payload.enabled,
        grace_minutes=payload.grace_minutes, actor_id=getattr(actor, "id", None),
    )


def list_executions(session: Session, pagination: Pagination) -> Page[ExecutionOut]:
    total = session.scalar(select(func.count()).select_from(PipelineExecution)) or 0
    rows = list(session.scalars(
        select(PipelineExecution)
        .order_by(PipelineExecution.id.desc())
        .limit(pagination.limit).offset(pagination.offset)
    ))
    return Page.build(
        [ExecutionOut.model_validate(r) for r in rows], total, pagination.page, pagination.page_size
    )


def get_execution(session: Session, run_id: str) -> ExecutionOut | None:
    row = session.scalar(select(PipelineExecution).where(PipelineExecution.run_id == run_id))
    return ExecutionOut.model_validate(row) if row else None


def trigger_run_now(app) -> RunNowResult:
    """Kick off a Standard Run on a background thread (trigger='manual', no
    notification — notifications are for scheduled runs). Returns immediately."""
    sessionmaker = app.state.db.sessionmaker
    settings: Settings = app.state.settings

    with sessionmaker() as s:
        if _run_in_progress(s):
            return RunNowResult(status="busy", detail="a Standard Run is already in progress")

    def _worker() -> None:
        try:
            with sessionmaker() as session:
                execution, _ = execute_standard_run(session, settings, trigger="manual", notify=False)
                logger.info("run-now %s complete: status=%s", execution.run_id, execution.status)
        except RunInProgress as exc:
            logger.info("run-now skipped: %s", exc)
        except Exception:
            logger.exception("run-now failed")

    threading.Thread(target=_worker, name="standard-run-now", daemon=True).start()
    return RunNowResult(status="accepted", detail="Standard Run started; refresh run history to follow progress")
