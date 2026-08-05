"""The orchestrator: run a stage (or the whole pipeline) with run-tracking,
error isolation, idempotency, and checkpoint/resume.
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from master_db.models import PipelineRun
from orchestrator import provenance
from orchestrator.runs import RunTracker
from orchestrator.stages import PIPELINE_ORDER, STAGES, SkipStage, Stage

logger = logging.getLogger("orchestrator")


@dataclass(slots=True)
class StageResult:
    component: str
    status: str
    processed: int = 0
    created: int = 0
    updated: int = 0
    review: int = 0
    duration_ms: int = 0
    errors: list[str] = field(default_factory=list)
    notes: str = ""


def _count(session: Session, tables) -> int:
    total = 0
    for table in tables:
        total += session.scalar(select(func.count()).select_from(table)) or 0
    return total


class Orchestrator:
    def __init__(self, session: Session, *, run_engine: bool = False, trigger: str = "manual",
                 company_limit: int | None = None) -> None:
        self.session = session
        self.run_engine = run_engine
        self.trigger = trigger
        # Benchmark mode (see orchestrator/cli.py's `--limit`): caps the company
        # universe for stages that support it (currently just
        # decision_maker_intelligence — see _invoke_ingest). `None` is the
        # unchanged production path.
        self.company_limit = company_limit
        self.tracker = RunTracker(session)

    # ---------------------------------------------------------------- stage
    def run_stage(self, name: str, *, pipeline_id: str = "") -> StageResult:
        stage = STAGES[name]
        use_engine = self.run_engine and stage.engine is not None
        mode = "full" if use_engine else ("scoring" if name == "scoring" else "ingest")
        run = self.tracker.start(component=name, pipeline_id=pipeline_id, mode=mode, trigger=self.trigger)
        # Per-run record provenance is scoped to grouped pipeline runs (a Standard Run
        # or `run all` passes an explicit pipeline_id). Ad-hoc single-stage runs
        # (pipeline_id="") don't surface in the Run History UI, so we skip capture.
        recorder = provenance.begin_stage(self.session, pipeline_id, name) if pipeline_id else None
        notes = ""
        # One start + one completion line per stage (9 stages x 2 runs/day). Cheap, and
        # the only way to tell a hung stage from a slow one in the hosted logs, where
        # the pipeline_runs row isn't written until the stage returns.
        logger.info("stage %s started (mode=%s pipeline=%s)", name, mode, pipeline_id or "-")
        try:
            if use_engine:
                ok, engine_note = self._run_engine(stage)
                notes = engine_note
                if not ok:
                    provenance.detach(self.session)
                    self.tracker.finish(run, status="failed", errors=[engine_note], notes=notes)
                    return StageResult(name, "failed", duration_ms=run.duration_ms,
                                       errors=[engine_note], notes=notes)

            before = _count(self.session, stage.tables)
            metrics = self._invoke_ingest(stage)
            after = _count(self.session, stage.tables)

            created = max(0, after - before)
            updated = max(0, metrics.rows_upserted - created)
            status = self._derive_status(metrics)
            notes = (notes + " " + metrics.notes).strip()
            self.tracker.finish(
                run, status=status, processed=metrics.rows_in, created=created,
                updated=updated, review=metrics.rows_review, errors=metrics.errors, notes=notes,
            )
            provenance.flush(self.session, recorder)   # only reached on the success path
            # WARNING for partial (a feed died, rows were rejected) so degraded runs are
            # greppable without opening the DB; INFO for a clean stage.
            logger.log(
                logging.WARNING if status in ("partial", "failed") else logging.INFO,
                "stage %s %s in %dms (processed=%d created=%d updated=%d review=%d errors=%d)%s",
                name, status, run.duration_ms, metrics.rows_in, created, updated,
                metrics.rows_review, len(metrics.errors), f" — {notes}" if notes else "",
            )
            return StageResult(name, status, metrics.rows_in, created, updated,
                               metrics.rows_review, run.duration_ms, metrics.errors, notes)

        except SkipStage as exc:
            logger.info("stage %s skipped: %s", name, exc)
            self.tracker.finish(run, status="skipped", notes=str(exc))
            return StageResult(name, "skipped", duration_ms=run.duration_ms, notes=str(exc))
        except Exception as exc:  # isolate stage failure
            logger.exception("stage %s failed", name)
            self.session.rollback()   # discards this stage's writes AND its buffered provenance
            self.tracker.finish(run, status="failed", errors=[str(exc)], notes="exception")
            return StageResult(name, "failed", duration_ms=run.duration_ms, errors=[str(exc)], notes=str(exc))
        finally:
            provenance.detach(self.session)

    def _invoke_ingest(self, stage: Stage):
        """Call stage.ingest(session), threading company_limit through only for the
        one stage that understands it (decision_maker_intelligence) — every other
        stage is called exactly as before (stage.ingest(self.session)), unaffected
        by benchmark mode."""
        if stage.name == "decision_maker_intelligence" and self.company_limit is not None:
            return stage.ingest(self.session, limit=self.company_limit)
        return stage.ingest(self.session)

    @staticmethod
    def _derive_status(metrics) -> str:
        """Map ingest metrics to a pipeline status.

        An explicit status hint from the ingestor wins (so a fully-failed Apify
        fetch reports "failed", not a hollow "success"). Otherwise fall back to
        row-level signals: any errors or rejected rows => "partial", else success.
        """
        if metrics.status in ("failed", "partial", "success"):
            return metrics.status
        if metrics.errors or metrics.rows_rejected:
            return "partial"
        return "success"

    def _run_engine(self, stage: Stage) -> tuple[bool, str]:
        spec = stage.engine
        logger.info("running engine for %s: %s", stage.name, " ".join(spec.cmd))
        try:
            proc = subprocess.run(
                spec.cmd, cwd=str(spec.cwd), capture_output=True, text=True, timeout=spec.timeout,
            )
        except OSError as exc:
            # covers a missing engine (FileNotFoundError) and an unusable working
            # directory (WinError 267 / NotADirectoryError) — both are OSError. Turn
            # them into a clean stage failure instead of an unhandled exception.
            return False, f"engine launch failed (cwd={spec.cwd}): {exc}"
        except subprocess.TimeoutExpired:
            return False, f"engine timed out after {spec.timeout}s"
        if proc.returncode == 0:
            return True, f"engine ok ({stage.description})"
        tail = (proc.stderr or proc.stdout or "").strip()[-300:]
        return False, f"engine exit {proc.returncode}: {tail}"

    # ------------------------------------------------------------- pipeline
    def run_pipeline(self, *, components: list[str] | None = None, resume: bool = False,
                     pipeline_id: str | None = None) -> list[StageResult]:
        """Run the pipeline, grouping its stages under one ``pipeline_id``.

        ``pipeline_id`` is generated when not supplied (unchanged behaviour). The
        Standard Run (backend/standard_run.py) passes an explicit id so its
        run-level ``pipeline_executions`` row shares the same id as these stage
        rows — nothing else about how stages run changes."""
        pipeline_id = pipeline_id or datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S")
        if resume:
            order = self._resume_components()
            pipeline_id += "-resume"
            if not order:
                logger.info("resume: nothing to re-run (last pipeline fully succeeded)")
        else:
            order = components or list(PIPELINE_ORDER)
        return [self.run_stage(name, pipeline_id=pipeline_id) for name in order]

    def _resume_components(self) -> list[str]:
        last_pid = self.session.scalar(
            select(PipelineRun.pipeline_id)
            .where(PipelineRun.pipeline_id != "")
            .order_by(PipelineRun.run_id.desc())
        )
        if not last_pid:
            return list(PIPELINE_ORDER)
        unfinished = {
            r.component
            for r in self.session.scalars(
                select(PipelineRun).where(PipelineRun.pipeline_id == last_pid)
            )
            if r.status != "success"
        }
        return [c for c in PIPELINE_ORDER if c in unfinished]
