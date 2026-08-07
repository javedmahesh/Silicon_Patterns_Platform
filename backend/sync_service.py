"""Read-only backend entry point for historical-company synchronization (Phase 2).

Delegates to the reusable :mod:`sync` engine. Generates a preview only — it never
writes to the database and never touches decision makers. The Phase-3 import UI /
apply step will build on this same preview.
"""
from __future__ import annotations

from pathlib import Path
from typing import IO

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from sqlalchemy import func, select

from backend import import_repo, review_repo
from backend.config import Settings
from backend.import_engine import ImportReport, run_import
from master_db.models import ImportJob, ImportReviewItem
from sync import (
    DmSyncPreview,
    SyncPreview,
    load_historical_companies,
    load_historical_decision_makers,
    reconcile_companies,
    reconcile_decision_makers,
)


def preview_company_sync_from_file(
    session: Session, source: str | Path | IO[bytes], *, sheet: str | None = None
) -> SyncPreview:
    records = load_historical_companies(source, sheet=sheet)
    return reconcile_companies(session, records)


def preview_company_sync_from_settings(session: Session, settings: Settings) -> SyncPreview:
    """Preview against the server-configured historical file (settings.historical_import_path).

    422 when no file is configured or it is missing — the endpoint reads a fixed
    configured path (never a client-supplied one), so there is no arbitrary-file-read
    surface. Phase 3 replaces this with a per-request upload.
    """
    path = (settings.historical_import_path or "").strip()
    if not path:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No historical import file configured (set SP_HISTORICAL_IMPORT_PATH).",
        )
    if not Path(path).is_file():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Configured historical import file not found: {path}",
        )
    return preview_company_sync_from_file(session, path)


def _require_configured_file(settings: Settings) -> str:
    path = (settings.historical_import_path or "").strip()
    if not path:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No historical import file configured (set SP_HISTORICAL_IMPORT_PATH).",
        )
    if not Path(path).is_file():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Configured historical import file not found: {path}",
        )
    return path


def preview_decision_maker_sync_from_settings(
    session: Session, settings: Settings, *, initiated_by: str = "", record_job: bool = True
) -> tuple[DmSyncPreview, ImportJob | None]:
    """DM reconciliation preview against the server-configured historical file.

    Read-only for company/decision-maker DATA. When ``record_job`` is set, writes ONE
    :class:`ImportJob` tracking row (status='previewed') — the reusable import
    infrastructure — never any decision_makers/companies rows.
    """
    path = _require_configured_file(settings)
    records = load_historical_decision_makers(path)
    preview = reconcile_decision_makers(session, records)
    job = None
    if record_job:
        st = preview.stats
        companies = len({r.resolved_company_domain for r in preview.results if r.resolved_company_domain})
        job = import_repo.record_import_job(
            session, source="historical_excel", filename=Path(path).name,
            initiated_by=initiated_by, status="previewed",
            companies_processed=companies, decision_makers_processed=st.total_input,
            created=st.new, updated=st.updated, unchanged=st.unchanged,
            duplicates=st.duplicates, conflicts=st.conflicts, invalid=st.invalid,
            summary=(f"preview: {st.new} new, {st.updated} update, {st.unchanged} unchanged, "
                     f"{st.duplicates} dup, {st.conflicts} conflict, {st.invalid} invalid "
                     f"across {companies} companies"),
            stats=st.to_dict(),
        )
    return preview, job


# ------------------------------------------------------------ Phase 4: apply
def preview_import_from_settings(
    session: Session, settings: Settings, *, initiated_by: str = ""
) -> ImportJob:
    """Generate the COMBINED company + decision-maker preview for the configured file
    and persist it as an :class:`ImportJob` (status='previewed') whose ``preview`` holds
    the full results so a later commit consumes them without reconciling again."""
    path = _require_configured_file(settings)
    company_prev = reconcile_companies(session, load_historical_companies(path))
    dm_prev = reconcile_decision_makers(session, load_historical_decision_makers(path))
    return _record_preview_job(session, company_prev=company_prev, dm_prev=dm_prev,
                               filename=Path(path).name, initiated_by=initiated_by)


def preview_import_from_upload(
    session: Session, *, filename: str, content_base64: str, initiated_by: str = ""
) -> ImportJob:
    """Decode an uploaded base64 Excel and produce a previewed ImportJob (422 on bad input)."""
    import base64
    import binascii

    try:
        content = base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid base64 content")
    if not content:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "empty file")
    try:
        return preview_import_from_bytes(session, content=content, filename=filename or "upload.xlsx",
                                         initiated_by=initiated_by)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — surface a clean 422 for an unreadable file
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"could not parse Excel file: {exc}")


def preview_import_from_bytes(
    session: Session, *, content: bytes, filename: str, initiated_by: str = ""
) -> ImportJob:
    """Phase 6 upload path: reconcile an uploaded Excel buffer and record a previewed
    ImportJob. Reuses the same synchronization engines — no matching/sync logic here."""
    import io

    company_prev = reconcile_companies(session, load_historical_companies(io.BytesIO(content)))
    dm_prev = reconcile_decision_makers(session, load_historical_decision_makers(io.BytesIO(content)))
    return _record_preview_job(session, company_prev=company_prev, dm_prev=dm_prev,
                               filename=filename, initiated_by=initiated_by)


def _record_preview_job(session: Session, *, company_prev, dm_prev, filename: str,
                        initiated_by: str) -> ImportJob:
    cs, ds = company_prev.stats, dm_prev.stats
    total = cs.new + cs.updated + ds.new + ds.updated
    job = import_repo.record_import_job(
        session, source="historical_excel", filename=filename,
        initiated_by=initiated_by, status="previewed",
        companies_processed=len(company_prev.results),
        decision_makers_processed=ds.total_input,
        created=cs.new + ds.new, updated=cs.updated + ds.updated,
        unchanged=cs.unchanged + ds.unchanged, duplicates=cs.duplicates + ds.duplicates,
        conflicts=cs.conflicts + ds.conflicts, invalid=ds.invalid, total_records=total,
        summary=(f"preview: {cs.new + ds.new} to create, {cs.updated + ds.updated} to update, "
                 f"{cs.conflicts + ds.conflicts} conflicts, {ds.invalid} invalid"),
        stats={"companies": cs.to_dict(), "decision_makers": ds.to_dict()},
        preview={"companies": company_prev.to_dict(), "decision_makers": dm_prev.to_dict()},
    )
    review_repo.seed_review_items(session, job)   # one reviewable item per record (Phase 5)
    return job


def commit_import(
    session: Session, import_id: str, *, commit: bool = True,
    approved_refs: set[str] | None = None, force_rollback: bool = False,
) -> ImportReport:
    """Apply a previewed import in one transaction (or dry-run when ``commit`` is False).

    Reuses the persisted preview — never reconciles again. 404 if unknown, 409 if the
    job is not in a runnable ('previewed') state.
    """
    job = import_repo.get_import_job(session, import_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "import job not found")
    if commit and job.status != "previewed":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"import job is '{job.status}', not 'previewed' — nothing to commit")
    # Phase 5: when the job has review items, the engine consumes ONLY the approved
    # (and conflict-resolved) records; otherwise fall back to the raw preview.
    has_review = session.scalar(select(func.count()).select_from(ImportReviewItem)
                                .where(ImportReviewItem.job_id == job.id))
    if has_review:
        company_preview, dm_preview = review_repo.build_approved_previews(session, job)
    else:
        prev = job.preview or {}
        company_preview = prev.get("companies", {})
        dm_preview = prev.get("decision_makers", {})
    return run_import(
        session, company_preview=company_preview, dm_preview=dm_preview, commit=commit,
        approved_refs=approved_refs, job=(job if commit else None),
        force_rollback=force_rollback, refresh=commit,   # Phase 7: refresh only on real commit
    )
