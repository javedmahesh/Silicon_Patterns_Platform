"""Run tracking: open/close ``pipeline_runs`` rows with timing + metrics."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from master_db.models import PipelineRun


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime | None) -> datetime | None:
    """Drop tzinfo so we can subtract regardless of how the DB returned it
    (SQLite hands back naive datetimes; Postgres returns aware ones)."""
    return dt.replace(tzinfo=None) if dt and dt.tzinfo is not None else dt


class RunTracker:
    def __init__(self, session: Session) -> None:
        self.session = session

    def start(self, *, component: str, pipeline_id: str = "", mode: str = "ingest",
              trigger: str = "manual") -> PipelineRun:
        run = PipelineRun(
            component=component, pipeline_id=pipeline_id, mode=mode, trigger=trigger,
            status="running", started_at=_utcnow(),
        )
        self.session.add(run)
        self.session.commit()
        return run

    def finish(self, run: PipelineRun, *, status: str, processed: int = 0, created: int = 0,
               updated: int = 0, review: int = 0, errors: list[str] | None = None,
               notes: str = "") -> PipelineRun:
        run.finished_at = _utcnow()
        finished = _naive(run.finished_at)
        start = _naive(run.started_at) or finished
        run.duration_ms = max(0, int((finished - start).total_seconds() * 1000))
        run.status = status
        run.records_processed = processed
        run.records_created = created
        run.records_updated = updated
        run.records_review = review
        errs = errors or []
        run.error_count = len(errs)
        run.errors = json.dumps(errs)[:4000]
        run.notes = (notes or "")[:1000]
        self.session.commit()
        return run
