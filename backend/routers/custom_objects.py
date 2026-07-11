"""Enterprise CRM Phase 7: Custom Objects, Forms & No-Code Platform endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend import custom_objects_service as svc
from backend.dependencies import get_session
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
    CustomRecordCreate,
    CustomRecordOut,
    CustomRecordPatch,
    Page,
)
from backend.security import get_current_user
from master_db.models import User

router = APIRouter(prefix="/custom-objects", tags=["custom-objects"])

_RESERVED_QUERY_PARAMS = {"limit", "offset", "search", "sort_by", "sort_dir"}


# ============================================================ objects
@router.get("", response_model=Page)
def list_objects(
    status_: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_objects(session, user, status=status_, limit=limit, offset=offset)


@router.post("", response_model=CustomObjectOut, status_code=status.HTTP_201_CREATED)
def create_object(
    data: CustomObjectCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_object(session, data, user)


@router.get("/dashboard/summary", response_model=CustomObjectDashboardOut)
def object_dashboard(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.object_dashboard(session, user)


@router.get("/{object_id}", response_model=CustomObjectOut)
def get_object(
    object_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.get_object(session, object_id, user)


@router.patch("/{object_id}", response_model=CustomObjectOut)
def patch_object(
    object_id: int, data: CustomObjectPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_object(session, object_id, data, user)


@router.delete("/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object(
    object_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_object(session, object_id, user)


@router.get("/{object_id}/analytics", response_model=CustomObjectAnalyticsOut)
def object_analytics(
    object_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.object_analytics(session, object_id, user)


# ============================================================ fields
@router.get("/{object_id}/fields", response_model=list[CustomFieldOut])
def list_fields(
    object_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_fields(session, object_id, user)


@router.post("/{object_id}/fields", response_model=CustomFieldOut, status_code=status.HTTP_201_CREATED)
def create_field(
    object_id: int, data: CustomFieldCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_field(session, object_id, data, user)


@router.patch("/fields/{field_id}", response_model=CustomFieldOut)
def patch_field(
    field_id: int, data: CustomFieldPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_field(session, field_id, data, user)


@router.delete("/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(
    field_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_field(session, field_id, user)


# ============================================================ forms
@router.get("/{object_id}/forms", response_model=list[CustomFormOut])
def list_forms(
    object_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_forms(session, object_id, user)


@router.post("/{object_id}/forms", response_model=CustomFormOut, status_code=status.HTTP_201_CREATED)
def create_form(
    object_id: int, data: CustomFormCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_form(session, object_id, data, user)


@router.patch("/forms/{form_id}", response_model=CustomFormOut)
def patch_form(
    form_id: int, data: CustomFormPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_form(session, form_id, data, user)


@router.delete("/forms/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_form(
    form_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_form(session, form_id, user)


# ============================================================ records
@router.get("/{object_id}/records", response_model=Page)
def list_records(
    object_id: int, request: Request,
    search: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    filters = {k: v for k, v in request.query_params.items() if k not in _RESERVED_QUERY_PARAMS}
    return svc.list_records(session, object_id, user, filters=filters or None, search=search, sort_by=sort_by, sort_dir=sort_dir, limit=limit, offset=offset)


@router.post("/{object_id}/records", response_model=CustomRecordOut, status_code=status.HTTP_201_CREATED)
def create_record(
    object_id: int, data: CustomRecordCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_record(session, object_id, data.data, user)


@router.get("/{object_id}/records/{record_id}", response_model=CustomRecordOut)
def get_record(
    object_id: int, record_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.get_record(session, record_id, user)


@router.patch("/{object_id}/records/{record_id}", response_model=CustomRecordOut)
def patch_record(
    object_id: int, record_id: int, data: CustomRecordPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_record(session, record_id, data.data, user)


@router.delete("/{object_id}/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    object_id: int, record_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_record(session, record_id, user)


@router.get("/{object_id}/records/{record_id}/audit", response_model=list[CustomRecordAuditOut])
def record_audit_history(
    object_id: int, record_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.record_audit_history(session, record_id, user)


@router.get("/{object_id}/records/{record_id}/related", response_model=dict[str, list[CustomRecordOut]])
def related_records(
    object_id: int, record_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.related_records(session, record_id, user)


# ============================================================ import / export
@router.get("/{object_id}/export")
def export_records(
    object_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    csv_text, filename = svc.export_records_csv(session, object_id, user)
    return Response(
        content=csv_text, media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{object_id}/import", response_model=CustomDataJobOut, status_code=status.HTTP_201_CREATED,
             summary="Import records from a raw CSV body (Content-Type: text/csv)")
async def import_records(
    object_id: int, request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    raw = await request.body()
    return svc.import_records_csv(session, object_id, raw.decode("utf-8"), user)


@router.get("/{object_id}/jobs", response_model=list[CustomDataJobOut])
def list_data_jobs(
    object_id: int, job_type: str | None = Query(None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_data_jobs(session, object_id, user, job_type=job_type)
