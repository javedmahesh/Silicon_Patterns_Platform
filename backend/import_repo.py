"""Reusable persistence for historical import-run tracking (:class:`ImportJob`).

One row per import run, written once at preview time (``status='previewed'``) and
reused by the Phase-4 apply step. This is the only thing the Phase-3 sync flow writes —
never companies or decision makers.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from master_db.models import ImportJob


def new_import_id() -> str:
    return uuid.uuid4().hex


def record_import_job(
    session: Session,
    *,
    source: str,
    filename: str,
    initiated_by: str,
    status: str = "previewed",
    companies_processed: int = 0,
    decision_makers_processed: int = 0,
    created: int = 0,
    updated: int = 0,
    unchanged: int = 0,
    duplicates: int = 0,
    conflicts: int = 0,
    invalid: int = 0,
    summary: str = "",
    stats: dict | None = None,
    preview: dict | None = None,
    total_records: int = 0,
    started_at: datetime | None = None,
) -> ImportJob:
    """Insert one import-run row and return it (committed).

    ``preview`` holds the full serialized synchronization results so a later commit
    consumes them without reconciling again.
    """
    now = datetime.now(timezone.utc)
    started = started_at or now
    job = ImportJob(
        import_id=new_import_id(), source=source, filename=filename,
        initiated_by=initiated_by, status=status,
        companies_processed=companies_processed,
        decision_makers_processed=decision_makers_processed,
        created_count=created, updated_count=updated, unchanged_count=unchanged,
        duplicate_count=duplicates, conflict_count=conflicts, invalid_count=invalid,
        summary=summary, stats=stats or {}, preview=preview or {}, total_records=total_records,
        started_at=started,
        finished_at=now, duration_ms=max(0, int((now - started).total_seconds() * 1000)),
    )
    session.add(job)
    session.commit()
    return job


def get_import_job(session: Session, import_id: str) -> ImportJob | None:
    return session.scalar(select(ImportJob).where(ImportJob.import_id == import_id))


def list_import_jobs(session: Session, *, limit: int = 50) -> list[ImportJob]:
    return list(session.scalars(
        select(ImportJob).order_by(ImportJob.id.desc()).limit(limit)
    ))


def import_job_to_dict(job: ImportJob) -> dict[str, Any]:
    return {
        "import_id": job.import_id, "source": job.source, "filename": job.filename,
        "initiated_by": job.initiated_by, "status": job.status,
        "companies_processed": job.companies_processed,
        "decision_makers_processed": job.decision_makers_processed,
        "created": job.created_count, "updated": job.updated_count,
        "unchanged": job.unchanged_count, "duplicates": job.duplicate_count,
        "conflicts": job.conflict_count, "invalid": job.invalid_count,
        "summary": job.summary,
        "current_stage": job.current_stage,
        "records_processed": job.records_processed,
        "total_records": job.total_records,
        "progress_pct": job.progress_pct,
        "error_message": job.error_message,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "duration_ms": job.duration_ms,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }
