"""Manual Decision Maker Intelligence jobs (paid Apify actor — run on demand).

DM intelligence is intentionally NOT part of the automatic pipeline (see
orchestrator/stages.py). It is triggered from the Decision Makers page for a chosen
set of companies, each with its OWN requested lead count. A job:

  * creates a ``dm_intelligence_jobs`` row + one ``dm_intelligence_job_items`` row per
    company (status ``queued``),
  * runs on a BACKGROUND thread (a full multi-company run takes minutes; the HTTP
    request returns immediately with the queued job), so the frontend can poll for
    live per-company progress,
  * reuses the EXISTING engine primitives — ``import_decision_makers_for_company``
    wraps ``_call_apify_actor`` + ``ApifyIngestor`` — so there is no duplicated scraper
    logic, retries / logging / ApifyActorRun records are all preserved,
  * records a ``pipeline_runs`` row (component=``decision_maker_intelligence``,
    trigger=``manual``) so the manual execution still appears in run history.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import repositories as repo
from backend.config import Settings
from config.apify import load_apify_credentials
from master_db.models import DmIntelligenceJob, DmIntelligenceJobItem
from orchestrator.runs import RunTracker

logger = logging.getLogger("backend.dm_intelligence_jobs")

# Guardrails for a manual, cost-incurring run.
MAX_COMPANIES_PER_JOB = 100          # dozens of companies per the spec; hard-cap for safety
MAX_REQUESTED_PER_COMPANY = 500      # per-company lead ceiling (actor allows far more)
DEFAULT_REQUESTED_PER_COMPANY = 25


class JobValidationError(ValueError):
    """The submitted run request is invalid (empty / unknown companies)."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clamp_count(n: int | None) -> int:
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = DEFAULT_REQUESTED_PER_COMPANY
    return max(1, min(n, MAX_REQUESTED_PER_COMPANY))


def create_job(session: Session, *, items, requested_by_id: int | None,
               requested_by_email: str) -> DmIntelligenceJob:
    """Validate the request, resolve companies (dedup by domain), and create the job
    + its per-company items (all ``queued``). Does NOT start execution — the caller
    kicks that off on a background thread via :func:`start_job_async`.

    ``items`` is an iterable of objects/dicts carrying ``company_domain`` +
    ``requested_count``."""
    # Dedup by domain, keeping the LAST requested_count for a repeated domain.
    wanted: dict[str, int] = {}
    for it in items:
        domain = (getattr(it, "company_domain", None) or "").strip().lower()
        if not domain:
            continue
        wanted[domain] = _clamp_count(getattr(it, "requested_count", None))

    if not wanted:
        raise JobValidationError("Select at least one company to run.")
    if len(wanted) > MAX_COMPANIES_PER_JOB:
        raise JobValidationError(f"Too many companies (max {MAX_COMPANIES_PER_JOB} per run).")

    # Resolve to real companies; a manual run only targets companies already in the
    # platform (the picker offers those). Unknown domains are rejected clearly.
    resolved: list[tuple[str, str, int]] = []
    unknown: list[str] = []
    for domain, count in wanted.items():
        company = repo.get_company(session, domain)
        if company is None:
            unknown.append(domain)
        else:
            resolved.append((company.company_domain, company.company_name or company.company_domain, count))
    if not resolved:
        raise JobValidationError(f"No known companies to run (unknown: {', '.join(unknown) or 'none'}).")

    job = DmIntelligenceJob(
        status="queued",
        requested_by_id=requested_by_id,
        requested_by_email=requested_by_email or "",
        total_companies=len(resolved),
        total_requested=sum(c for _, _, c in resolved),
        total_found=0,
    )
    session.add(job)
    session.flush()  # assign job.id
    for domain, name, count in resolved:
        session.add(DmIntelligenceJobItem(
            job_id=job.id, company_domain=domain, company_name=name,
            requested_count=count, status="queued",
        ))
    session.commit()
    session.refresh(job)
    logger.info("DM intelligence job %s queued: %d companies, %d leads requested",
                job.id, job.total_companies, job.total_requested)
    return job


def get_job(session: Session, job_id: int) -> DmIntelligenceJob | None:
    return session.get(DmIntelligenceJob, job_id)


def list_jobs(session: Session, *, limit: int = 20) -> list[DmIntelligenceJob]:
    return list(session.scalars(
        select(DmIntelligenceJob).order_by(DmIntelligenceJob.id.desc()).limit(limit)
    ))


# --------------------------------------------------------------- execution
def start_job_async(app, job_id: int) -> None:
    """Run the job on a daemon thread (mirrors scheduler_service.trigger_run_now).

    The thread opens its OWN session from the app sessionmaker (sessions aren't
    thread-safe), so the request thread returns immediately with the queued job."""
    sessionmaker = app.state.db.sessionmaker
    settings: Settings = app.state.settings

    def _worker() -> None:
        try:
            with sessionmaker() as session:
                _run_job(session, settings, job_id)
        except Exception:  # a job must never take the process down
            logger.exception("DM intelligence job %s crashed", job_id)

    threading.Thread(target=_worker, name=f"dm-intel-job-{job_id}", daemon=True).start()


def _finish_item(session: Session, item: DmIntelligenceJobItem, *, status: str,
                 records_found: int = 0, apify_run_id: str | None = None,
                 error: str = "") -> None:
    item.status = status
    item.records_found = records_found
    item.apify_run_id = apify_run_id
    item.error = (error or "")[:2000]
    item.finished_at = _utcnow()
    start = item.started_at or item.finished_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    item.duration_ms = max(0, int((item.finished_at - start).total_seconds() * 1000))
    session.commit()


def _run_job(session: Session, settings: Settings, job_id: int) -> None:
    """Execute a queued job: run the Apify engine per company, updating live progress
    (committed after each step so pollers see it), then finalize job-level status."""
    from integration.ingestors.apify_source import (
        _capture_decision_maker_snapshots,
        import_decision_makers_for_company,
    )

    job = session.get(DmIntelligenceJob, job_id)
    if job is None or job.status not in ("queued",):
        return

    # Record the manual execution in the existing pipeline run history.
    tracker = RunTracker(session)
    run = tracker.start(component="decision_maker_intelligence",
                        pipeline_id=f"dm-job-{job_id}", mode="ingest", trigger="manual")
    job.pipeline_run_id = run.run_id
    job.status = "running"
    job.started_at = _utcnow()
    session.commit()

    api_token, actor_id = load_apify_credentials()
    items = list(session.scalars(
        select(DmIntelligenceJobItem).where(DmIntelligenceJobItem.job_id == job_id)
        .order_by(DmIntelligenceJobItem.id)
    ))

    total_found = 0
    inserted_total = 0
    updated_total = 0
    failures = 0
    any_records = False

    if not api_token:
        # No credentials → fail the whole job clearly (every item marked failed) so the
        # UI shows exactly why, rather than silently doing nothing.
        for item in items:
            item.started_at = _utcnow()
            _finish_item(session, item, status="failed",
                         error="No Apify credentials configured (set APIFY_API_TOKEN).")
            failures += 1
        _finalize(session, tracker, run, job, status="failed", total_found=0,
                  inserted=0, updated=0, error="No Apify credentials configured (set APIFY_API_TOKEN).")
        return

    for item in items:
        company = repo.get_company(session, item.company_domain)
        item.status = "running"
        item.started_at = _utcnow()
        session.commit()
        if company is None:
            _finish_item(session, item, status="failed", error="Company no longer exists.")
            failures += 1
            continue
        try:
            res = import_decision_makers_for_company(
                session, company=company, requested_count=item.requested_count,
                actor_id=actor_id, api_token=api_token, pipeline_run_id=run.run_id,
            )
        except Exception as exc:  # defensive: the helper shouldn't raise, but never abort the job
            logger.exception("DM job %s: company %s failed", job_id, item.company_domain)
            session.rollback()
            _finish_item(session, item, status="failed", error=str(exc))
            failures += 1
            continue

        if res.status == "failed":
            _finish_item(session, item, status="failed", apify_run_id=res.apify_run_id, error=res.error)
            failures += 1
        else:
            _finish_item(session, item, status="completed",
                         records_found=res.records_found, apify_run_id=res.apify_run_id)
            total_found += res.records_found
            inserted_total += res.inserted
            updated_total += res.updated
            if res.records_returned:
                any_records = True
        # Keep the job-level running totals fresh for the progress UI.
        job.total_found = total_found
        session.commit()

    # Snapshot decision makers once after the run (feeds leadership-signal derivation),
    # only when we actually fetched fresh records — mirrors the pipeline stage.
    if any_records:
        _capture_decision_maker_snapshots(session)

    if failures == len(items):
        status = "failed"
    elif failures:
        status = "partial"
    else:
        status = "completed"
    _finalize(session, tracker, run, job, status=status, total_found=total_found,
              inserted=inserted_total, updated=updated_total)


def _finalize(session: Session, tracker: RunTracker, run, job: DmIntelligenceJob, *,
              status: str, total_found: int, inserted: int, updated: int, error: str = "") -> None:
    job.status = status
    job.total_found = total_found
    job.finished_at = _utcnow()
    job.error = (error or "")[:2000]
    start = job.started_at or job.finished_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    job.duration_ms = max(0, int((job.finished_at - start).total_seconds() * 1000))
    session.commit()

    # Map job status onto the pipeline_runs audit row.
    run_status = {"completed": "success", "partial": "partial", "failed": "failed"}.get(status, "partial")
    tracker.finish(run, status=run_status, processed=job.total_requested,
                   created=inserted, updated=updated,
                   errors=[error] if error else [],
                   notes=f"manual DM job {job.id}: companies={job.total_companies} found={total_found}")
    logger.info("DM intelligence job %s finished: status=%s found=%d", job.id, status, total_found)
