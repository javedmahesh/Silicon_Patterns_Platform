"""Data access for Enterprise CRM Phase 7: Custom Objects, Forms & No-Code Platform."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from master_db.models import (
    CustomDataJob,
    CustomField,
    CustomForm,
    CustomObject,
    CustomRecord,
    CustomRecordAudit,
)


# ----------------------------------------------------------------- objects
def create_object(session: Session, **kw) -> CustomObject:
    o = CustomObject(**kw)
    session.add(o)
    session.flush()
    return o


def get_object(session: Session, object_id: int) -> CustomObject | None:
    return session.get(CustomObject, object_id)


def get_object_by_api_name(session: Session, api_name: str) -> CustomObject | None:
    return session.scalar(select(CustomObject).where(CustomObject.api_name == api_name))


def list_objects(
    session: Session, *, status: str | None = None, limit: int = 50, offset: int = 0,
) -> tuple[list[CustomObject], int]:
    q = select(CustomObject)
    if status:
        q = q.where(CustomObject.status == status)
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(CustomObject.id.desc()).limit(limit).offset(offset)))
    return rows, total


def delete_object(session: Session, object_id: int) -> bool:
    o = session.get(CustomObject, object_id)
    if not o:
        return False
    session.delete(o)
    return True


def count_objects(session: Session, *, status: str | None = None) -> int:
    q = select(func.count()).select_from(CustomObject)
    if status:
        q = q.where(CustomObject.status == status)
    return session.scalar(q) or 0


# ----------------------------------------------------------------- fields
def create_field(session: Session, **kw) -> CustomField:
    f = CustomField(**kw)
    session.add(f)
    session.flush()
    return f


def get_field(session: Session, field_id: int) -> CustomField | None:
    return session.get(CustomField, field_id)


def list_fields(session: Session, object_id: int) -> list[CustomField]:
    return list(session.scalars(
        select(CustomField).where(CustomField.object_id == object_id).order_by(CustomField.display_order, CustomField.id)
    ))


def delete_field(session: Session, field_id: int) -> bool:
    f = session.get(CustomField, field_id)
    if not f:
        return False
    session.delete(f)
    return True


# ----------------------------------------------------------------- forms
def create_form(session: Session, **kw) -> CustomForm:
    f = CustomForm(**kw)
    session.add(f)
    session.flush()
    return f


def get_form(session: Session, form_id: int) -> CustomForm | None:
    return session.get(CustomForm, form_id)


def list_forms(session: Session, object_id: int) -> list[CustomForm]:
    return list(session.scalars(select(CustomForm).where(CustomForm.object_id == object_id).order_by(CustomForm.id)))


def delete_form(session: Session, form_id: int) -> bool:
    f = session.get(CustomForm, form_id)
    if not f:
        return False
    session.delete(f)
    return True


# ----------------------------------------------------------------- records
def create_record(session: Session, **kw) -> CustomRecord:
    r = CustomRecord(**kw)
    session.add(r)
    session.flush()
    return r


def get_record(session: Session, record_id: int) -> CustomRecord | None:
    return session.get(CustomRecord, record_id)


def list_records_for_object(session: Session, object_id: int) -> list[CustomRecord]:
    """All records for one object. ponytail: in-memory filter/sort/search happens on this
    list in the service layer — fine at demo/test scale (a few thousand rows per object);
    upgrade path: push filter/sort/search into SQL (JSON path expressions) if a real object
    grows past that."""
    return list(session.scalars(
        select(CustomRecord)
        .where(CustomRecord.object_id == object_id, CustomRecord.is_deleted.is_(False))
        .order_by(CustomRecord.id)
    ))


def delete_record(session: Session, record_id: int) -> bool:
    r = session.get(CustomRecord, record_id)
    if not r:
        return False
    session.delete(r)
    return True


def count_records(session: Session, object_id: int) -> int:
    return session.scalar(
        select(func.count()).select_from(CustomRecord).where(CustomRecord.object_id == object_id)
    ) or 0


def total_records(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(CustomRecord)) or 0


def recent_records(session: Session, limit: int = 10) -> list[CustomRecord]:
    return list(session.scalars(select(CustomRecord).order_by(CustomRecord.id.desc()).limit(limit)))


def records_created_counts_by_day(session: Session, object_id: int) -> dict:
    """(day_string -> count). SQLite/Postgres both support func.date(); portable. 1 query."""
    rows = session.execute(
        select(func.date(CustomRecord.created_at), func.count(CustomRecord.id))
        .where(CustomRecord.object_id == object_id)
        .group_by(func.date(CustomRecord.created_at))
    ).all()
    return {str(r[0]): r[1] for r in rows}


# ----------------------------------------------------------------- audit
def create_audit(session: Session, **kw) -> CustomRecordAudit:
    a = CustomRecordAudit(**kw)
    session.add(a)
    session.flush()
    return a


def list_audit(session: Session, record_id: int) -> list[CustomRecordAudit]:
    return list(session.scalars(
        select(CustomRecordAudit).where(CustomRecordAudit.record_id == record_id).order_by(CustomRecordAudit.id.desc())
    ))


def count_updated_records(session: Session, object_id: int) -> int:
    """Distinct records with at least one 'updated' audit row. 1 query."""
    return session.scalar(
        select(func.count(func.distinct(CustomRecordAudit.record_id)))
        .join(CustomRecord, CustomRecord.id == CustomRecordAudit.record_id)
        .where(CustomRecord.object_id == object_id, CustomRecordAudit.action == "updated")
    ) or 0


# ----------------------------------------------------------------- data jobs (import/export)
def create_job(session: Session, **kw) -> CustomDataJob:
    j = CustomDataJob(**kw)
    session.add(j)
    session.flush()
    return j


def get_job(session: Session, job_id: int) -> CustomDataJob | None:
    return session.get(CustomDataJob, job_id)


def list_jobs(session: Session, object_id: int, *, job_type: str | None = None) -> list[CustomDataJob]:
    q = select(CustomDataJob).where(CustomDataJob.object_id == object_id)
    if job_type:
        q = q.where(CustomDataJob.job_type == job_type)
    return list(session.scalars(q.order_by(CustomDataJob.id.desc())))


def import_stats(session: Session, object_id: int) -> dict:
    """Aggregate success/total across all import jobs for an object. 1 query."""
    row = session.execute(
        select(func.coalesce(func.sum(CustomDataJob.success_count), 0), func.coalesce(func.sum(CustomDataJob.total_rows), 0))
        .where(CustomDataJob.object_id == object_id, CustomDataJob.job_type == "import")
    ).one()
    success, total = row
    return {"success": success, "total": total}


def export_count(session: Session, object_id: int) -> int:
    return session.scalar(
        select(func.count()).select_from(CustomDataJob)
        .where(CustomDataJob.object_id == object_id, CustomDataJob.job_type == "export")
    ) or 0


def recent_import_error_count(session: Session, limit_jobs: int = 5) -> int:
    """Sum of error_count across the most recent import jobs (platform-wide). 1 query + Python sum."""
    rows = session.execute(
        select(CustomDataJob.error_count)
        .where(CustomDataJob.job_type == "import")
        .order_by(CustomDataJob.id.desc())
        .limit(limit_jobs)
    ).all()
    return sum(r[0] for r in rows)


def total_import_jobs(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(CustomDataJob).where(CustomDataJob.job_type == "import")
    ) or 0
