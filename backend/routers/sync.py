"""Historical-data synchronization endpoints (Phase 2 — read-only preview).

Generates the deterministic company reconciliation preview that the Phase-3 import UI
will render. Read-only: no database writes, no decision-maker import. Manager+ only.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend import import_repo, review_repo
from backend import sync_service as svc
from backend.dependencies import get_session
from backend.schemas import ImportUploadIn, ReviewBulkIn, ReviewDecisionIn, ReviewFieldResolveIn
from backend.security import require_admin, require_manager
from master_db.models import User

router = APIRouter(prefix="/sync", tags=["sync"])


def _load_job(session, import_id):
    job = import_repo.get_import_job(session, import_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "import job not found")
    return job


@router.post(
    "/companies/preview",
    response_model=None,
    summary="Preview company reconciliation of the configured historical file (manager+, read-only)",
)
def preview_companies(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_manager),
) -> dict:
    preview = svc.preview_company_sync_from_settings(session, request.app.state.settings)
    return preview.to_dict()


@router.post(
    "/decision-makers/preview",
    response_model=None,
    summary="Preview decision-maker reconciliation + record an import job (manager+, read-only)",
)
def preview_decision_makers(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_manager),
) -> dict:
    preview, job = svc.preview_decision_maker_sync_from_settings(
        session, request.app.state.settings, initiated_by=getattr(user, "email", ""),
    )
    out = preview.to_dict()
    out["import_id"] = job.import_id if job else None
    return out


@router.post(
    "/imports/preview",
    response_model=None,
    summary="Generate a combined company+DM import preview and record an import job (manager+)",
)
def preview_import(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_manager),
) -> dict:
    job = svc.preview_import_from_settings(
        session, request.app.state.settings, initiated_by=getattr(user, "email", ""))
    return import_repo.import_job_to_dict(job)


@router.post(
    "/imports/{import_id}/commit",
    response_model=None,
    summary="Apply a previewed import in one transaction — admin only (dry_run for zero-write rehearsal)",
)
def commit_import(
    import_id: str,
    dry_run: bool = False,
    session: Session = Depends(get_session),
    user: User = Depends(require_admin),
) -> dict:
    report = svc.commit_import(session, import_id, commit=not dry_run)
    return report.to_dict()


@router.post("/imports/upload", response_model=None,
             summary="Upload a historical Excel (base64) and generate a preview — admin only")
def upload_import(
    body: ImportUploadIn,
    session: Session = Depends(get_session),
    user: User = Depends(require_admin),
) -> dict:
    job = svc.preview_import_from_upload(
        session, filename=body.filename, content_base64=body.content_base64,
        initiated_by=getattr(user, "email", ""))
    return import_repo.import_job_to_dict(job)


@router.get("/imports/{import_id}/review", response_model=None,
            summary="Preview records merged with review state + field diffs (manager+)")
def get_review(
    import_id: str,
    category: str | None = None,
    state: str | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(require_manager),
) -> dict:
    job = _load_job(session, import_id)
    return {"import_id": import_id,
            "items": review_repo.list_review_items(session, job, category=category, state=state),
            "stats": review_repo.statistics(session, job)}


@router.get("/imports/{import_id}/review/stats", response_model=None,
            summary="Review statistics by state + category (manager+)")
def get_review_stats(
    import_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(require_manager),
) -> dict:
    return review_repo.statistics(session, _load_job(session, import_id))


@router.get("/imports/{import_id}/review/audit", response_model=None,
            summary="Immutable review audit trail (manager+)")
def get_review_audit(
    import_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(require_manager),
) -> dict:
    return {"events": review_repo.audit_trail(session, _load_job(session, import_id))}


@router.post("/imports/{import_id}/review/decide", response_model=None,
             summary="Approve / reject / skip one record (manager+)")
def decide_review(
    import_id: str,
    body: ReviewDecisionIn,
    session: Session = Depends(get_session),
    user: User = Depends(require_manager),
) -> dict:
    job = _load_job(session, import_id)
    item = review_repo.decide(session, job, kind=body.kind, source_ref=body.source_ref,
                              decision=body.decision, reviewer=getattr(user, "email", ""),
                              reason=body.reason)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "review record not found or bad decision")
    return {"state": item.state}


@router.post("/imports/{import_id}/review/resolve", response_model=None,
             summary="Resolve one update/conflict field: keep_platform | accept_historical (manager+)")
def resolve_review_field(
    import_id: str,
    body: ReviewFieldResolveIn,
    session: Session = Depends(get_session),
    user: User = Depends(require_manager),
) -> dict:
    job = _load_job(session, import_id)
    item = review_repo.resolve_field(session, job, kind=body.kind, source_ref=body.source_ref,
                                     field=body.field, choice=body.choice,
                                     reviewer=getattr(user, "email", ""), reason=body.reason)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "review record not found or bad choice")
    return {"state": item.state, "field_decisions": item.field_decisions}


@router.post("/imports/{import_id}/review/bulk", response_model=None,
             summary="Bulk approve/reject: all | selected | by category (manager+)")
def bulk_review(
    import_id: str,
    body: ReviewBulkIn,
    session: Session = Depends(get_session),
    user: User = Depends(require_manager),
) -> dict:
    job = _load_job(session, import_id)
    changed = review_repo.bulk(session, job, action=body.action, refs=body.refs,
                               category=body.category, reviewer=getattr(user, "email", ""))
    return {"changed": changed, "stats": review_repo.statistics(session, job)}


@router.get("/imports/{import_id}/refresh", response_model=None,
            summary="Post-import intelligence refresh status per stage (manager+)")
def get_refresh_status(
    import_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(require_manager),
) -> dict:
    from backend.post_import_pipeline import refresh_status
    _load_job(session, import_id)
    return refresh_status(session, import_id)


@router.post("/imports/{import_id}/refresh/retry", response_model=None,
             summary="Retry only the failed post-import refresh stages — admin only")
def retry_refresh(
    import_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(require_admin),
) -> dict:
    from backend.post_import_pipeline import retry_failed
    _load_job(session, import_id)
    return retry_failed(session, import_id).to_dict()


@router.get("/imports", response_model=None, summary="List historical import jobs (manager+)")
def list_imports(
    session: Session = Depends(get_session),
    user: User = Depends(require_manager),
) -> dict:
    return {"items": [import_repo.import_job_to_dict(j) for j in import_repo.list_import_jobs(session)]}


@router.get("/imports/{import_id}", response_model=None, summary="One import job's detail (manager+)")
def get_import(
    import_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(require_manager),
) -> dict:
    job = import_repo.get_import_job(session, import_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "import job not found")
    out = import_repo.import_job_to_dict(job)
    out["stats"] = job.stats
    return out
