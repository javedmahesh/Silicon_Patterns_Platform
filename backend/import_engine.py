"""Transactional historical import engine (Phase 4).

Consumes the *already-generated* Phase-2/3 synchronization previews (never reconciles
again) and applies them inside ONE database transaction:

    create companies -> update companies -> create decision makers ->
    update decision makers -> refresh relationships -> commit -> post-import hooks

Any failure rolls the whole thing back — no partial import ever persists — and the
:class:`~master_db.models.ImportJob` is marked failed/rolled_back. Only approved,
non-conflicting records are applied; conflicts / invalid / duplicates are skipped and
reported. Only synchronized (owned) fields are ever written, so lead scores, signals,
ML features, AI insights, user feedback, manual edits and outreach history are
preserved by construction (they live in other tables the engine never touches).

Lead-score / ML recomputation is intentionally NOT done here — that is Phase 6.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config.enums import IMPORT_STAGES
from integration.normalizer import canonical_company_id, name_key
from master_db.models import Company, DecisionMaker, ImportJob
from sync.linkedin import canonical_linkedin_url
from sync.normalization import COMPANY_OWNED_FIELDS, DM_OWNED_FIELDS

# actions from a FieldChange that represent a safe write (never a conflict).
_APPLY_ACTIONS = frozenset({"fill", "update"})
ProgressFn = Callable[[str, int, int], None]


@dataclass(slots=True)
class ImportReport:
    status: str = "previewed"
    companies_created: int = 0
    companies_updated: int = 0
    decision_makers_created: int = 0
    decision_makers_updated: int = 0
    unchanged: int = 0
    duplicates_skipped: int = 0
    conflicts_skipped: int = 0
    invalid_skipped: int = 0
    companies_with_decision_makers: int = 0
    total_decision_makers: int = 0
    duration_ms: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    # affected records (created/updated) — the incremental scope for the Phase-7 refresh
    affected_company_domains: set[str] = field(default_factory=set)
    affected_dm_ids: set[int] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "companies_created": self.companies_created,
            "companies_updated": self.companies_updated,
            "decision_makers_created": self.decision_makers_created,
            "decision_makers_updated": self.decision_makers_updated,
            "unchanged": self.unchanged,
            "duplicates_skipped": self.duplicates_skipped,
            "conflicts_skipped": self.conflicts_skipped,
            "invalid_skipped": self.invalid_skipped,
            "companies_with_decision_makers": self.companies_with_decision_makers,
            "total_decision_makers": self.total_decision_makers,
            "duration_ms": self.duration_ms,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "affected_company_domains": sorted(self.affected_company_domains),
            "affected_dm_ids": sorted(self.affected_dm_ids),
        }


def _changes(res: dict) -> dict[str, str]:
    """Map field -> proposed value for the safe (fill/update) changes of a result."""
    return {c["field"]: c["proposed"] for c in res.get("changes", [])
            if c.get("action") in _APPLY_ACTIONS}


def _approved(res: dict, approved_refs: set[str] | None) -> bool:
    return approved_refs is None or res.get("source_ref") in approved_refs


# --------------------------------------------------------------- stages
def _apply_companies(session: Session, results: list[dict], approved_refs, report: ImportReport,
                     *, create: bool) -> None:
    want = "new" if create else "update"
    new_rows: list[Company] = []
    # warm the identity map for updates in one query (avoid N+1)
    if not create:
        domains = [r["resolved_domain"] for r in results
                   if r.get("classification") == "update" and r.get("resolved_domain")]
        if domains:
            session.execute(select(Company).where(Company.company_domain.in_(domains))).all()
    for res in results:
        if res.get("classification") != want or not _approved(res, approved_refs):
            continue
        domain = res.get("resolved_domain")
        if not domain:
            report.warnings.append(f"company {res.get('raw_name')!r}: no domain, skipped")
            continue
        fields = _changes(res)
        existing = session.get(Company, domain)
        if create:
            if existing is not None:                     # external change since preview
                report.warnings.append(f"company {domain}: already exists, treated as update")
                _set_company_fields(existing, fields)
                report.companies_updated += 1
                report.affected_company_domains.add(domain)
                continue
            nm = fields.get("company_name") or res.get("raw_name") or domain
            company = Company(
                company_domain=domain, company_name=nm, name_key=name_key(nm),
                canonical_company_id=canonical_company_id(domain, nm),
                validation_status="VALID", is_stub=False,
                source="historical_import", source_type="historical_excel",
            )
            _set_company_fields(company, {k: v for k, v in fields.items() if k != "company_name"})
            new_rows.append(company)
            report.companies_created += 1
            report.affected_company_domains.add(domain)
        else:
            if existing is None:
                report.warnings.append(f"company {domain}: vanished before update, skipped")
                continue
            _set_company_fields(existing, fields)
            report.companies_updated += 1
            report.affected_company_domains.add(domain)
    if new_rows:
        session.add_all(new_rows)
        session.flush()


def _set_company_fields(company: Company, fields: dict[str, str]) -> None:
    touched_name = False
    for f, v in fields.items():
        if f in COMPANY_OWNED_FIELDS:
            setattr(company, f, v)
            touched_name = touched_name or f == "company_name"
    if touched_name and company.company_name:
        company.name_key = name_key(company.company_name)
        company.canonical_company_id = canonical_company_id(company.company_domain, company.company_name)


def _apply_decision_makers(session: Session, results: list[dict], approved_refs, report: ImportReport,
                           *, create: bool, existing_linkedins: set[str], company_names: dict[str, str]) -> None:
    want = "new" if create else "update"
    new_rows: list[DecisionMaker] = []
    created_linkedins: set[str] = set()
    if not create:
        ids = [r["matched_dm_id"] for r in results
               if r.get("classification") == "update" and r.get("matched_dm_id")]
        if ids:
            session.execute(select(DecisionMaker).where(DecisionMaker.id.in_(ids))).all()
    for res in results:
        if res.get("classification") != want or not _approved(res, approved_refs):
            continue
        fields = _changes(res)
        if create:
            li = res.get("linkedin_canonical") or ""
            if not li:
                report.invalid_skipped += 1
                report.warnings.append(f"dm {res.get('full_name')!r}: no LinkedIn, cannot create")
                continue
            if li in existing_linkedins or li in created_linkedins:
                report.duplicates_skipped += 1
                report.warnings.append(f"dm {li}: already present, skipped (no duplicate created)")
                continue
            domain = res.get("resolved_company_domain")
            domain = domain if (domain and session.get(Company, domain)) else None
            dm = DecisionMaker(
                linkedin_url=li, company_domain=domain,
                resolved_company_name=company_names.get(domain or "", ""),
                source="historical_import", status="sourced",
            )
            _set_dm_fields(dm, fields)
            new_rows.append(dm)
            created_linkedins.add(li)
            report.decision_makers_created += 1
            if domain:
                report.affected_company_domains.add(domain)
        else:
            dm = session.get(DecisionMaker, res.get("matched_dm_id"))
            if dm is None:
                report.warnings.append(f"dm {res.get('matched_dm_id')}: vanished before update, skipped")
                continue
            _set_dm_fields(dm, fields)
            report.decision_makers_updated += 1
            report.affected_dm_ids.add(dm.id)
            if dm.company_domain:
                report.affected_company_domains.add(dm.company_domain)
    if new_rows:
        session.add_all(new_rows)
        session.flush()
        report.affected_dm_ids.update(dm.id for dm in new_rows)   # ids assigned after flush


def _set_dm_fields(dm: DecisionMaker, fields: dict[str, str]) -> None:
    for f, v in fields.items():
        if f in DM_OWNED_FIELDS:
            setattr(dm, f, v)


def _refresh_relationships(session: Session, report: ImportReport) -> None:
    """Recompute company↔DM relationship metrics (coverage / DM counts) for the report.

    Validates that every decision maker's company_domain still points at a real company
    (relationships remain valid). Does NOT recompute lead scores or ML features (Phase 6).
    """
    rows = session.execute(
        select(DecisionMaker.company_domain, func.count())
        .where(DecisionMaker.company_domain.isnot(None))
        .group_by(DecisionMaker.company_domain)
    ).all()
    report.companies_with_decision_makers = len(rows)
    report.total_decision_makers = session.scalar(select(func.count()).select_from(DecisionMaker)) or 0


def _tally_skips(company_results: list[dict], dm_results: list[dict], report: ImportReport) -> None:
    for r in company_results:
        c = r.get("classification")
        if c == "unchanged":
            report.unchanged += 1
        elif c == "conflict":
            report.conflicts_skipped += 1
        elif c == "duplicate":
            report.duplicates_skipped += 1
    for r in dm_results:
        c = r.get("classification")
        if c == "unchanged":
            report.unchanged += 1
        elif c == "conflict":
            report.conflicts_skipped += 1
        elif c == "duplicate":
            report.duplicates_skipped += 1
        elif c == "invalid":
            report.invalid_skipped += 1


def _existing_canonical_linkedins(session: Session) -> set[str]:
    """One-shot lookup set of existing canonical LinkedIn URLs (duplicate guard)."""
    out: set[str] = set()
    for (url,) in session.execute(select(DecisionMaker.linkedin_url)).all():
        c = canonical_linkedin_url(url)
        if c:
            out.add(c)
    return out


def _dry_run_report(company_results, dm_results, approved_refs) -> ImportReport:
    report = ImportReport(status="previewed")
    for r in company_results:
        if r.get("classification") == "new" and _approved(r, approved_refs):
            report.companies_created += 1
        elif r.get("classification") == "update" and _approved(r, approved_refs):
            report.companies_updated += 1
    for r in dm_results:
        if r.get("classification") == "new" and _approved(r, approved_refs):
            report.decision_makers_created += 1
        elif r.get("classification") == "update" and _approved(r, approved_refs):
            report.decision_makers_updated += 1
    _tally_skips(company_results, dm_results, report)
    return report


def run_import(
    session: Session,
    *,
    company_preview: dict,
    dm_preview: dict,
    commit: bool,
    approved_refs: set[str] | None = None,
    job: ImportJob | None = None,
    force_rollback: bool = False,
    refresh: bool = False,
    progress: ProgressFn | None = None,
) -> ImportReport:
    """Apply the previews. ``commit=False`` is a dry run (zero writes).

    ``refresh=True`` fires the Phase-7 post-import intelligence pipeline AFTER a
    successful commit only (never on dry-run / rollback / failure)."""
    started = datetime.now(timezone.utc)
    company_results = company_preview.get("results", [])
    dm_results = dm_preview.get("results", [])

    if not commit:
        report = _dry_run_report(company_results, dm_results, approved_refs)
        report.duration_ms = _elapsed_ms(started)
        return report

    total = sum(1 for r in company_results + dm_results
                if r.get("classification") in ("new", "update") and _approved(r, approved_refs))
    if job is not None:
        job.status = "running"; job.started_at = started; job.total_records = total
        job.current_stage = IMPORT_STAGES[0]; job.progress_pct = 0; job.error_message = ""
        session.commit()                                  # persist RUNNING before any data write

    report = ImportReport(status="running")
    company_names = {r["resolved_domain"]: (r.get("raw_name") or "")
                     for r in company_results if r.get("resolved_domain")}
    try:
        existing_linkedins = _existing_canonical_linkedins(session)
        stages: list[tuple[str, Callable[[], None]]] = [
            ("create_companies", lambda: _apply_companies(session, company_results, approved_refs, report, create=True)),
            ("update_companies", lambda: _apply_companies(session, company_results, approved_refs, report, create=False)),
            ("create_decision_makers", lambda: _apply_decision_makers(
                session, dm_results, approved_refs, report, create=True,
                existing_linkedins=existing_linkedins, company_names=company_names)),
            ("update_decision_makers", lambda: _apply_decision_makers(
                session, dm_results, approved_refs, report, create=False,
                existing_linkedins=existing_linkedins, company_names=company_names)),
            ("refresh_relationships", lambda: _refresh_relationships(session, report)),
        ]
        for i, (stage, fn) in enumerate(stages):
            if job is not None:
                job.current_stage = stage
            fn()
            done = report.companies_created + report.companies_updated + \
                report.decision_makers_created + report.decision_makers_updated
            if progress is not None:
                progress(stage, done, total)
        _tally_skips(company_results, dm_results, report)

        if force_rollback:
            session.rollback()
            report.status = "rolled_back"
            _finalize_job(session, job, report, started, status="rolled_back")
            return report

        session.commit()                                  # atomic apply of every stage
        _post_import_hooks(session, report)
        report.status = "completed"
        report.duration_ms = _elapsed_ms(started)
        _finalize_job(session, job, report, started, status="completed")
        if refresh:                                       # Phase 7: only after a real commit
            _run_intelligence_refresh(session, report, job)
        return report
    except Exception as exc:                              # any failure -> full rollback
        session.rollback()
        report.status = "failed"
        report.errors.append(str(exc))
        report.duration_ms = _elapsed_ms(started)
        _finalize_job(session, job, report, started, status="failed", error=str(exc))
        return report


def _post_import_hooks(session: Session, report: ImportReport) -> None:
    """Extension seam that runs AFTER a successful commit. Refreshes read-side caches so
    coverage metrics reflect the import immediately."""
    try:
        from backend import cache
        cache.clear()
    except Exception:  # cache is best-effort; never fail an import over it
        report.warnings.append("post-import cache refresh skipped")


def _run_intelligence_refresh(session: Session, report: ImportReport, job: ImportJob | None) -> None:
    """Fire the Phase-7 post-import intelligence pipeline for the affected records.

    Runs AFTER the import has committed, so it can NEVER fail the import — any pipeline
    error is caught and recorded as a warning; each stage tracks itself in pipeline_runs.
    """
    try:
        from backend.post_import_pipeline import run_post_import_refresh
        summary = run_post_import_refresh(
            session, import_id=(job.import_id if job else "adhoc"),
            domains=sorted(report.affected_company_domains),
            dm_ids=sorted(report.affected_dm_ids),
        )
        for stage in summary.failed:
            report.warnings.append(f"intelligence refresh stage failed: {stage}")
    except Exception as exc:  # the import already committed — never propagate
        report.warnings.append(f"intelligence refresh error: {exc}")


def _finalize_job(session, job, report, started, *, status, error="") -> None:
    if job is None:
        return
    now = datetime.now(timezone.utc)
    job.status = status
    job.finished_at = now
    job.duration_ms = _elapsed_ms(started)
    job.error_message = error
    job.records_processed = (report.companies_created + report.companies_updated +
                             report.decision_makers_created + report.decision_makers_updated)
    job.progress_pct = 100 if status == "completed" else job.progress_pct
    job.created_count = report.companies_created + report.decision_makers_created
    job.updated_count = report.companies_updated + report.decision_makers_updated
    job.unchanged_count = report.unchanged
    job.duplicate_count = report.duplicates_skipped
    job.conflict_count = report.conflicts_skipped
    job.invalid_count = report.invalid_skipped
    job.stats = report.to_dict()
    job.summary = (f"{status}: {report.companies_created} companies + "
                   f"{report.decision_makers_created} DMs created, "
                   f"{report.companies_updated + report.decision_makers_updated} updated")
    job.current_stage = "done" if status == "completed" else status
    session.commit()


def _elapsed_ms(started: datetime) -> int:
    return max(0, int((datetime.now(timezone.utc) - started).total_seconds() * 1000))
