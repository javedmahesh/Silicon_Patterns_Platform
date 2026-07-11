"""Enterprise CRM Phase 7: Custom Objects, Forms & No-Code Platform.

Records are stored as a single JSON `data` dict per row (CustomRecord.data), keyed by
field api_name — not classic EAV. This keeps writes/reads O(1) per record and lets every
object share one table, at the cost of doing filter/sort/search in Python rather than SQL.
ponytail: fine at demo/test scale (a few thousand rows/object); upgrade path noted in
custom_objects_repo.list_records_for_object if a real object needs it pushed into SQL.
"""
from __future__ import annotations

import csv
import io
import re
import time
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import admin_service
from backend import custom_objects_repo as repo
from backend.schemas import (
    CustomDataJobOut,
    CustomFieldCreate,
    CustomFieldOut,
    CustomFieldPatch,
    CustomFormCreate,
    CustomFormOut,
    CustomFormPatch,
    CustomObjectAnalyticsOut,
    CustomObjectCreate,
    CustomObjectDashboardOut,
    CustomObjectOut,
    CustomObjectPatch,
    CustomRecordAuditOut,
    CustomRecordOut,
    CustomRecordValidationError,
    FieldUtilizationOut,
    Page,
)
from config.enums import CUSTOM_FIELD_TYPES
from master_db.models import CustomField, User

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_RE = re.compile(r"^https?://[^\s]+$")
_PHONE_RE = re.compile(r"^[+\d][\d\s().-]{5,}$")

from backend.timeutil import utc as _utc, utcnow as _utcnow


def _is_manager(user) -> bool:
    return getattr(user, "role", "member") in ("admin", "manager")


def _require_manager(user) -> None:
    if not _is_manager(user):
        raise HTTPException(403, "manager or admin required")


def _load_user_emails(session: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    from sqlalchemy import select
    rows = session.scalars(select(User).where(User.id.in_(ids))).all()
    return {u.id: u.email for u in rows}


# ================================================================== field metadata cache
_FIELD_TTL_SECONDS = 30
_field_cache: dict[str, tuple[float, list[CustomField]]] = {}


def _cache_key(session: Session, object_id: int) -> str:
    try:
        db_url = str(session.get_bind().url)
    except Exception:
        db_url = "default"
    return f"{db_url}::{object_id}"


def cached_fields(session: Session, object_id: int) -> list[CustomField]:
    key = _cache_key(session, object_id)
    cached = _field_cache.get(key)
    if cached and time.monotonic() - cached[0] < _FIELD_TTL_SECONDS:
        return cached[1]
    fields = repo.list_fields(session, object_id)
    _field_cache[key] = (time.monotonic(), fields)
    return fields


def invalidate_field_cache() -> None:
    _field_cache.clear()


# ================================================================== validation engine
def _validate_value(f: CustomField, value) -> CustomRecordValidationError | None:
    v = f.validation or {}
    custom_msg = v.get("error_message")

    def err(msg: str) -> CustomRecordValidationError:
        return CustomRecordValidationError(field_api_name=f.api_name, message=custom_msg or msg)

    t = f.field_type
    if t in ("text", "long_text", "email", "url", "phone"):
        if not isinstance(value, str):
            return err(f"{f.name} must be text")
        if t == "email" and not _EMAIL_RE.match(value):
            return err(f"{f.name} must be a valid email")
        if t == "url" and not _URL_RE.match(value):
            return err(f"{f.name} must be a valid URL")
        if t == "phone" and not _PHONE_RE.match(value):
            return err(f"{f.name} must be a valid phone number")
        max_len = v.get("max_length")
        if max_len and len(value) > max_len:
            return err(f"{f.name} exceeds max length {max_len}")
        pattern = v.get("pattern")
        if pattern and not re.match(pattern, value):
            return err(f"{f.name} does not match the required format")
    elif t in ("integer", "decimal", "currency"):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return err(f"{f.name} must be numeric")
        if t == "integer" and not float(value).is_integer():
            return err(f"{f.name} must be a whole number")
        min_v, max_v = v.get("min"), v.get("max")
        if min_v is not None and value < min_v:
            return err(f"{f.name} must be >= {min_v}")
        if max_v is not None and value > max_v:
            return err(f"{f.name} must be <= {max_v}")
    elif t == "boolean":
        if not isinstance(value, bool):
            return err(f"{f.name} must be true or false")
    elif t in ("date", "datetime"):
        if not isinstance(value, str):
            return err(f"{f.name} must be an ISO date string")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return err(f"{f.name} is not a valid date")
        min_d, max_d = v.get("min_date"), v.get("max_date")
        if min_d and parsed < datetime.fromisoformat(min_d.replace("Z", "+00:00")):
            return err(f"{f.name} must be on or after {min_d}")
        if max_d and parsed > datetime.fromisoformat(max_d.replace("Z", "+00:00")):
            return err(f"{f.name} must be on or before {max_d}")
    elif t == "picklist":
        if value not in (f.picklist_options or []):
            return err(f"{f.name} must be one of {f.picklist_options}")
    elif t == "multiselect":
        if not isinstance(value, list) or any(x not in (f.picklist_options or []) for x in value):
            return err(f"{f.name} contains an invalid option")
    return None


def validate_record_data(fields: list[CustomField], data: dict, *, partial: bool = False) -> list[CustomRecordValidationError]:
    errors: list[CustomRecordValidationError] = []
    for f in fields:
        if f.api_name not in data:
            if f.is_required and not partial:
                errors.append(CustomRecordValidationError(field_api_name=f.api_name, message=f"{f.name} is required"))
            continue
        value = data[f.api_name]
        if value is None:
            if f.is_required:
                errors.append(CustomRecordValidationError(field_api_name=f.api_name, message=f"{f.name} is required"))
            continue
        err = _validate_value(f, value)
        if err:
            errors.append(err)
    return errors


def _validate_lookups(session: Session, fields: list[CustomField], data: dict) -> list[CustomRecordValidationError]:
    errors = []
    for f in fields:
        if f.field_type != "lookup" or f.api_name not in data or data[f.api_name] is None:
            continue
        if not repo.get_record(session, int(data[f.api_name])):
            errors.append(CustomRecordValidationError(field_api_name=f.api_name, message=f"{f.name} references a record that does not exist"))
    return errors


# ================================================================== object CRUD
def _object_out(o) -> CustomObjectOut:
    return CustomObjectOut(
        id=o.id, name=o.name, api_name=o.api_name, description=o.description, icon=o.icon,
        status=o.status, version=o.version, created_by=o.created_by,
        created_at=_utc(o.created_at), updated_at=_utc(o.updated_at),
    )


def list_objects(session: Session, user, *, status: str | None = None, limit: int = 50, offset: int = 0) -> Page:
    rows, total = repo.list_objects(session, status=status, limit=limit, offset=offset)
    return Page.build([_object_out(o) for o in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


def create_object(session: Session, data: CustomObjectCreate, user) -> CustomObjectOut:
    _require_manager(user)
    if repo.get_object_by_api_name(session, data.api_name):
        raise HTTPException(409, "api_name already in use")
    o = repo.create_object(
        session, name=data.name, api_name=data.api_name, description=data.description,
        icon=data.icon, status=data.status, created_by=user.id,
    )
    session.commit()
    return _object_out(o)


def get_object(session: Session, object_id: int, user) -> CustomObjectOut:
    o = repo.get_object(session, object_id)
    if not o:
        raise HTTPException(404, "object not found")
    return _object_out(o)


def patch_object(session: Session, object_id: int, data: CustomObjectPatch, user) -> CustomObjectOut:
    _require_manager(user)
    o = repo.get_object(session, object_id)
    if not o:
        raise HTTPException(404, "object not found")
    changed = False
    for field in ("name", "description", "icon", "status"):
        val = getattr(data, field)
        if val is not None:
            setattr(o, field, val)
            changed = True
    if changed:
        o.version += 1
    session.commit()
    return _object_out(o)


def delete_object(session: Session, object_id: int, user) -> None:
    _require_manager(user)
    if not repo.delete_object(session, object_id):
        raise HTTPException(404, "object not found")
    session.commit()
    invalidate_field_cache()


# ================================================================== field CRUD
def _field_out(f) -> CustomFieldOut:
    return CustomFieldOut(
        id=f.id, object_id=f.object_id, name=f.name, api_name=f.api_name, field_type=f.field_type,
        is_required=f.is_required, default_value=f.default_value, validation=f.validation or {},
        picklist_options=f.picklist_options or [], lookup_object_id=f.lookup_object_id,
        display_order=f.display_order, created_at=_utc(f.created_at), updated_at=_utc(f.updated_at),
    )


def list_fields(session: Session, object_id: int, user) -> list[CustomFieldOut]:
    if not repo.get_object(session, object_id):
        raise HTTPException(404, "object not found")
    return [_field_out(f) for f in cached_fields(session, object_id)]


def create_field(session: Session, object_id: int, data: CustomFieldCreate, user) -> CustomFieldOut:
    _require_manager(user)
    obj = repo.get_object(session, object_id)
    if not obj:
        raise HTTPException(404, "object not found")
    if data.field_type not in CUSTOM_FIELD_TYPES:
        raise HTTPException(422, f"invalid field_type: {data.field_type}")
    if data.field_type == "lookup" and not data.lookup_object_id:
        raise HTTPException(422, "lookup fields require lookup_object_id")
    if any(f.api_name == data.api_name for f in repo.list_fields(session, object_id)):
        raise HTTPException(409, "api_name already exists on this object")
    f = repo.create_field(
        session, object_id=object_id, name=data.name, api_name=data.api_name,
        field_type=data.field_type, is_required=data.is_required, default_value=data.default_value,
        validation=data.validation, picklist_options=data.picklist_options,
        lookup_object_id=data.lookup_object_id, display_order=data.display_order,
    )
    session.commit()
    invalidate_field_cache()
    return _field_out(f)


def patch_field(session: Session, field_id: int, data: CustomFieldPatch, user) -> CustomFieldOut:
    _require_manager(user)
    f = repo.get_field(session, field_id)
    if not f:
        raise HTTPException(404, "field not found")
    for field in ("name", "is_required", "validation", "picklist_options", "display_order"):
        val = getattr(data, field)
        if val is not None:
            setattr(f, field, val)
    session.commit()
    invalidate_field_cache()
    return _field_out(f)


def delete_field(session: Session, field_id: int, user) -> None:
    _require_manager(user)
    if not repo.delete_field(session, field_id):
        raise HTTPException(404, "field not found")
    session.commit()
    invalidate_field_cache()


# ================================================================== form CRUD
def _form_out(fm) -> CustomFormOut:
    return CustomFormOut(
        id=fm.id, object_id=fm.object_id, name=fm.name, description=fm.description,
        layout=fm.layout or {}, is_default=fm.is_default,
        created_at=_utc(fm.created_at), updated_at=_utc(fm.updated_at),
    )


def list_forms(session: Session, object_id: int, user) -> list[CustomFormOut]:
    if not repo.get_object(session, object_id):
        raise HTTPException(404, "object not found")
    return [_form_out(f) for f in repo.list_forms(session, object_id)]


def create_form(session: Session, object_id: int, data: CustomFormCreate, user) -> CustomFormOut:
    _require_manager(user)
    if not repo.get_object(session, object_id):
        raise HTTPException(404, "object not found")
    f = repo.create_form(
        session, object_id=object_id, name=data.name, description=data.description,
        layout=data.layout.model_dump(), is_default=data.is_default,
    )
    session.commit()
    return _form_out(f)


def patch_form(session: Session, form_id: int, data: CustomFormPatch, user) -> CustomFormOut:
    _require_manager(user)
    f = repo.get_form(session, form_id)
    if not f:
        raise HTTPException(404, "form not found")
    if data.name is not None:
        f.name = data.name
    if data.description is not None:
        f.description = data.description
    if data.layout is not None:
        f.layout = data.layout.model_dump()
    if data.is_default is not None:
        f.is_default = data.is_default
    session.commit()
    return _form_out(f)


def delete_form(session: Session, form_id: int, user) -> None:
    _require_manager(user)
    if not repo.delete_form(session, form_id):
        raise HTTPException(404, "form not found")
    session.commit()


# ================================================================== record CRUD
def _record_out(r) -> CustomRecordOut:
    return CustomRecordOut(
        id=r.id, object_id=r.object_id, data=r.data or {}, created_by=r.created_by,
        updated_by=r.updated_by, created_at=_utc(r.created_at), updated_at=_utc(r.updated_at),
    )


def create_record(session: Session, object_id: int, data: dict, user) -> CustomRecordOut:
    obj = repo.get_object(session, object_id)
    if not obj:
        raise HTTPException(404, "object not found")
    fields = cached_fields(session, object_id)
    errors = validate_record_data(fields, data) + _validate_lookups(session, fields, data)
    if errors:
        raise HTTPException(422, detail=[e.model_dump() for e in errors])
    r = repo.create_record(session, object_id=object_id, data=data, created_by=user.id, updated_by=user.id)
    repo.create_audit(session, record_id=r.id, action="created", changed_by=user.id, field_changes=data)
    admin_service.log_audit_event(session, category="record_crud", action="custom_record_created", actor=user, entity_type=obj.api_name, entity_id=r.id)
    session.commit()
    return _record_out(r)


def get_record(session: Session, record_id: int, user) -> CustomRecordOut:
    r = repo.get_record(session, record_id)
    if not r:
        raise HTTPException(404, "record not found")
    return _record_out(r)


def patch_record(session: Session, record_id: int, data: dict, user) -> CustomRecordOut:
    r = repo.get_record(session, record_id)
    if not r:
        raise HTTPException(404, "record not found")
    fields = cached_fields(session, r.object_id)
    merged = {**(r.data or {}), **data}
    errors = validate_record_data(fields, merged) + _validate_lookups(session, fields, data)
    if errors:
        raise HTTPException(422, detail=[e.model_dump() for e in errors])
    diff = {k: {"old": (r.data or {}).get(k), "new": v} for k, v in data.items() if (r.data or {}).get(k) != v}
    r.data = merged
    r.updated_by = user.id
    if diff:
        repo.create_audit(session, record_id=r.id, action="updated", changed_by=user.id, field_changes=diff)
        admin_service.log_audit_event(session, category="record_crud", action="custom_record_updated", actor=user, entity_type="custom_record", entity_id=r.id, detail={"fields": list(diff)})
    session.commit()
    return _record_out(r)


def delete_record(session: Session, record_id: int, user) -> None:
    # ponytail: no pre-delete custom_record_audit row — that table cascades with the
    # record, so a "deleted" entry written just before would be destroyed in the same
    # transaction. The cross-cutting audit_events row survives, since it isn't FK-tied
    # to the record.
    if not repo.delete_record(session, record_id):
        raise HTTPException(404, "record not found")
    admin_service.log_audit_event(session, category="record_crud", action="custom_record_deleted", actor=user, entity_type="custom_record", entity_id=record_id)
    session.commit()


def list_records(
    session: Session, object_id: int, user, *, filters: dict | None = None, search: str | None = None,
    sort_by: str | None = None, sort_dir: str = "asc", limit: int = 50, offset: int = 0,
) -> Page:
    if not repo.get_object(session, object_id):
        raise HTTPException(404, "object not found")
    rows = repo.list_records_for_object(session, object_id)
    if filters:
        rows = [r for r in rows if all(str((r.data or {}).get(k)) == str(v) for k, v in filters.items())]
    if search:
        needle = search.lower()
        rows = [r for r in rows if any(needle in str(v).lower() for v in (r.data or {}).values())]
    if sort_by:
        rows = sorted(rows, key=lambda r: ((r.data or {}).get(sort_by) is None, (r.data or {}).get(sort_by)), reverse=(sort_dir == "desc"))
    total = len(rows)
    page_rows = rows[offset:offset + limit] if limit else rows
    return Page.build([_record_out(r) for r in page_rows], total, max(1, offset // limit + 1) if limit else 1, limit)


def record_audit_history(session: Session, record_id: int, user) -> list[CustomRecordAuditOut]:
    if not repo.get_record(session, record_id):
        raise HTTPException(404, "record not found")
    rows = repo.list_audit(session, record_id)
    email_map = _load_user_emails(session, [a.changed_by for a in rows if a.changed_by])
    return [
        CustomRecordAuditOut(
            id=a.id, record_id=a.record_id, action=a.action, changed_by=a.changed_by,
            changed_by_email=email_map.get(a.changed_by, ""), field_changes=a.field_changes or {},
            created_at=_utc(a.created_at),
        )
        for a in rows
    ]


def related_records(session: Session, record_id: int, user) -> dict[str, list[CustomRecordOut]]:
    """Records in other objects whose lookup field points at this record.

    ponytail: scans every candidate object's full record set — fine at demo scale;
    upgrade path: a dedicated relationship index table if related-list lookups get hot.
    """
    r = repo.get_record(session, record_id)
    if not r:
        raise HTTPException(404, "record not found")
    from sqlalchemy import select
    lookup_fields = session.scalars(
        select(CustomField).where(CustomField.field_type == "lookup", CustomField.lookup_object_id == r.object_id)
    ).all()
    result: dict[str, list[CustomRecordOut]] = {}
    for f in lookup_fields:
        candidates = repo.list_records_for_object(session, f.object_id)
        matches = [c for c in candidates if str((c.data or {}).get(f.api_name)) == str(record_id)]
        if matches:
            result[f"{f.object_id}:{f.api_name}"] = [_record_out(m) for m in matches]
    return result


# ================================================================== CSV import / export
_CSV_LIST_SEP = ";"


def _coerce_csv_value(field_type: str, raw: str):
    raw = raw.strip()
    if field_type == "integer":
        try:
            return int(raw)
        except ValueError:
            return raw
    if field_type in ("decimal", "currency"):
        try:
            return float(raw)
        except ValueError:
            return raw
    if field_type == "boolean":
        return raw.lower() in ("true", "1", "yes")
    if field_type == "multiselect":
        return [x.strip() for x in raw.split(_CSV_LIST_SEP) if x.strip()]
    return raw


def export_records_csv(session: Session, object_id: int, user) -> tuple[str, str]:
    obj = repo.get_object(session, object_id)
    if not obj:
        raise HTTPException(404, "object not found")
    fields = cached_fields(session, object_id)
    records = repo.list_records_for_object(session, object_id)
    buf = io.StringIO()
    fieldnames = ["id", "created_at", "updated_at"] + [f.api_name for f in fields]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for r in records:
        row = {
            "id": r.id,
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "updated_at": r.updated_at.isoformat() if r.updated_at else "",
        }
        for f in fields:
            v = (r.data or {}).get(f.api_name)
            row[f.api_name] = _CSV_LIST_SEP.join(v) if isinstance(v, list) else ("" if v is None else v)
        writer.writerow(row)
    repo.create_job(
        session, object_id=object_id, job_type="export", status="completed",
        total_rows=len(records), success_count=len(records), created_by=user.id, completed_at=_utcnow(),
    )
    session.commit()
    return buf.getvalue(), f"{obj.api_name}_export.csv"


def import_records_csv(session: Session, object_id: int, csv_text: str, user) -> CustomDataJobOut:
    obj = repo.get_object(session, object_id)
    if not obj:
        raise HTTPException(404, "object not found")
    fields = cached_fields(session, object_id)
    field_map = {f.api_name: f for f in fields}
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    errors: list[dict] = []
    success = 0
    for i, row in enumerate(rows, start=1):
        data = {}
        for k, raw in row.items():
            f = field_map.get(k)
            if f is None or raw is None or raw == "":
                continue
            data[k] = _coerce_csv_value(f.field_type, raw)
        row_errors = validate_record_data(fields, data) + _validate_lookups(session, fields, data)
        if row_errors:
            errors.append({"row": i, "errors": [e.model_dump() for e in row_errors]})
            continue
        r = repo.create_record(session, object_id=object_id, data=data, created_by=user.id, updated_by=user.id)
        repo.create_audit(session, record_id=r.id, action="created", changed_by=user.id, field_changes=data)
        success += 1
    job = repo.create_job(
        session, object_id=object_id, job_type="import",
        status="failed" if rows and success == 0 else "completed",
        total_rows=len(rows), success_count=success, error_count=len(errors),
        errors=errors[:50], created_by=user.id, completed_at=_utcnow(),
    )
    session.commit()
    return CustomDataJobOut(
        id=job.id, object_id=job.object_id, job_type=job.job_type, status=job.status,
        total_rows=job.total_rows, success_count=job.success_count, error_count=job.error_count,
        errors=job.errors or [], created_by=job.created_by,
        created_at=_utc(job.created_at), completed_at=_utc(job.completed_at),
    )


def list_data_jobs(session: Session, object_id: int, user, *, job_type: str | None = None) -> list[CustomDataJobOut]:
    if not repo.get_object(session, object_id):
        raise HTTPException(404, "object not found")
    return [
        CustomDataJobOut(
            id=j.id, object_id=j.object_id, job_type=j.job_type, status=j.status,
            total_rows=j.total_rows, success_count=j.success_count, error_count=j.error_count,
            errors=j.errors or [], created_by=j.created_by,
            created_at=_utc(j.created_at), completed_at=_utc(j.completed_at),
        )
        for j in repo.list_jobs(session, object_id, job_type=job_type)
    ]


# ================================================================== dashboard + analytics
def object_dashboard(session: Session, user) -> CustomObjectDashboardOut:
    return CustomObjectDashboardOut(
        total_objects=repo.count_objects(session),
        active_objects=repo.count_objects(session, status="active"),
        total_records=repo.total_records(session),
        recent_records=[_record_out(r) for r in repo.recent_records(session, 10)],
        recent_import_errors=repo.recent_import_error_count(session),
        import_jobs_run=repo.total_import_jobs(session),
    )


def object_analytics(session: Session, object_id: int, user) -> CustomObjectAnalyticsOut:
    if not repo.get_object(session, object_id):
        raise HTTPException(404, "object not found")
    fields = cached_fields(session, object_id)
    records = repo.list_records_for_object(session, object_id)
    total = len(records)
    utilization = []
    for f in fields:
        filled = sum(1 for r in records if (r.data or {}).get(f.api_name) not in (None, "", []))
        utilization.append(FieldUtilizationOut(field_api_name=f.api_name, filled_pct=round(filled / total, 4) if total else 0.0))
    imp = repo.import_stats(session, object_id)
    import_rate = round(imp["success"] / imp["total"], 4) if imp["total"] else 1.0
    return CustomObjectAnalyticsOut(
        object_id=object_id,
        records_created_total=total,
        records_created_by_period=repo.records_created_counts_by_day(session, object_id),
        records_updated_total=repo.count_updated_records(session, object_id),
        field_utilization=utilization,
        import_success_rate=import_rate,
        export_count=repo.export_count(session, object_id),
    )
