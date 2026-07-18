"""Run Details drill-down: the records a specific Standard Run's engine touched.

Reads the lightweight ``run_engine_records`` provenance (migration 0053) for one
(run, engine) and joins each reference back to its canonical row for display. Run
isolation is by construction — every query filters on the run's own ``run_id``, so
one run can never surface another's records.

Historical runs predating provenance have no rows here; :func:`engine_records`
reports ``available=False`` for the whole run so the UI can say "detailed record
tracking unavailable" instead of fabricating contents from current DB state.
"""
from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.schemas import RunEngineRecordOut, RunEngineRecordsOut
from master_db.models import (
    Company,
    CompanyRollup,
    DemandSignal,
    EngagementRecommendation,
    Job,
    LeadScore,
    LeadershipSignal,
    Opportunity,
    RunEngineRecord,
)


# ---- per canonical-table display projections ---------------------------------
# Each entry: (Model, pk_attr, project(row, detail) -> dict). `project` returns the
# display shape the frontend renders generically (title / subtitle / fields / link).
def _companies(row: Company, detail: dict) -> dict:
    return {
        "title": row.company_name or row.company_domain,
        "subtitle": row.company_domain,
        "fields": _pairs([
            ("Industry", row.industry_category), ("Country", row.country),
            ("Tier", row.company_tier), ("Type", row.prospect_type),
        ]),
        "link": f"/companies/{row.company_domain}",
    }


def _opportunities(row: Opportunity, detail: dict) -> dict:
    return {
        "title": row.article_title or row.opportunity_type or row.opportunity_id,
        "subtitle": row.company_name or row.company_domain,
        "fields": _pairs([
            ("Type", row.opportunity_type), ("Published", row.published_date),
            ("Source", row.source), ("Score", row.effective_opportunity_score),
        ]),
        "link": f"/opportunities?company_domain={row.company_domain}",
        "url": row.article_url or "",
    }


def _jobs(row: Job, detail: dict) -> dict:
    return {
        "title": row.job_title or row.job_id,
        "subtitle": row.company_name or row.company_domain,
        "fields": _pairs([
            ("Location", row.location), ("Category", row.job_category),
            ("Tech", row.technologies), ("Seniority", row.seniority),
        ]),
        "link": f"/companies/{row.company_domain}",
        "url": row.job_url or "",
    }


def _demand(row: DemandSignal, detail: dict) -> dict:
    return {
        "title": row.company_name or row.company_domain,
        "subtitle": row.company_domain,
        "fields": _pairs([
            ("Demand score", round(row.demand_score or 0, 1)),
            ("Eng jobs", row.total_engineering_jobs), ("Focus", row.primary_focus),
            ("Trend", row.hiring_trend),
        ]),
        "link": f"/companies/{row.company_domain}",
    }


def _rollup(row: CompanyRollup, detail: dict) -> dict:
    return {
        "title": row.company_name or row.company_domain,
        "subtitle": row.company_domain,
        "fields": _pairs([
            ("Priority", row.priority_rank), ("Demand score", round(row.demand_score or 0, 1)),
            ("Eng jobs", row.total_engineering_jobs), ("Focus", row.primary_focus),
        ]),
        "link": f"/companies/{row.company_domain}",
    }


def _lead_scores(row: LeadScore, detail: dict) -> dict:
    prev, new = detail.get("prev_score"), detail.get("new_score", round(row.lead_score or 0, 2))
    changed = detail.get("changed")
    return {
        "title": row.company_domain,
        "subtitle": f"Grade {detail.get('grade') or row.grade}",
        "fields": _pairs([
            ("Previous", "—" if prev is None else prev),
            ("New", new),
            ("Grade", detail.get("grade") or row.grade),
            ("Changed", "yes" if changed else "no"),
        ]),
        "link": f"/companies/{row.company_domain}",
    }


def _leadership(row: LeadershipSignal, detail: dict) -> dict:
    return {
        "title": row.person_name or detail.get("person_name") or "—",
        "subtitle": row.company_name or row.company_domain or detail.get("company_name") or "",
        "fields": _pairs([
            ("Role", row.to_title), ("Movement", (row.movement_type or "").replace("_", " ")),
            ("Effective", row.effective_date), ("Source", row.source),
        ]),
        "link": (f"/companies/{row.company_domain}" if row.company_domain else None),
    }


def _engagement(row: EngagementRecommendation, detail: dict) -> dict:
    return {
        "title": row.company_domain,
        "subtitle": row.offering or detail.get("offering") or "",
        "fields": _pairs([
            ("Need", row.business_need), ("Confidence", row.confidence),
            ("Level", row.confidence_label),
        ]),
        "link": f"/companies/{row.company_domain}",
    }


# entity_table -> (Model, pk column attr name, projector)
_ENTITY_MAP: dict[str, tuple[type, str, Callable[[Any, dict], dict]]] = {
    "companies": (Company, "company_domain", _companies),
    "opportunities": (Opportunity, "opportunity_id", _opportunities),
    "jobs": (Job, "job_id", _jobs),
    "demand_signals": (DemandSignal, "company_domain", _demand),
    "company_rollups": (CompanyRollup, "company_domain", _rollup),
    "lead_scores": (LeadScore, "company_domain", _lead_scores),
    "leadership_signals": (LeadershipSignal, "signal_id", _leadership),
    "engagement_recommendations": (EngagementRecommendation, "company_domain", _engagement),
}


def _pairs(items: list[tuple[str, Any]]) -> list[dict[str, str]]:
    """Keep only fields with a real value; stringify for a uniform display contract."""
    out: list[dict[str, str]] = []
    for label, value in items:
        if value is None or value == "" or value == 0:
            continue
        out.append({"label": label, "value": str(value)})
    return out


def run_has_provenance(session: Session, run_id: str) -> bool:
    return session.scalar(
        select(RunEngineRecord.id).where(RunEngineRecord.run_id == run_id).limit(1)
    ) is not None


def engine_records(session: Session, run_id: str, engine: str, *, limit: int, offset: int) -> RunEngineRecordsOut:
    """Page through the records *engine* touched during run *run_id*, each joined to
    its canonical row for display, plus a full operation breakdown for the header."""
    available = run_has_provenance(session, run_id)

    base = select(RunEngineRecord).where(
        RunEngineRecord.run_id == run_id, RunEngineRecord.engine == engine
    )
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0

    breakdown = {
        op: n for op, n in session.execute(
            select(RunEngineRecord.operation, func.count())
            .where(RunEngineRecord.run_id == run_id, RunEngineRecord.engine == engine)
            .group_by(RunEngineRecord.operation)
        ).all()
    }

    rows = list(session.scalars(
        base.order_by(RunEngineRecord.id).limit(limit).offset(offset)
    ))
    items = _project(session, rows)

    return RunEngineRecordsOut(
        run_id=run_id, engine=engine, available=available, total=total,
        breakdown=breakdown, items=items,
    )


def _project(session: Session, rows: list[RunEngineRecord]) -> list[RunEngineRecordOut]:
    """Batch-load the canonical rows for a page (grouped by table, one query each) and
    project each provenance row to its display shape. A record whose canonical row was
    since deleted degrades to id-only rather than vanishing."""
    # group ids by table to load in bulk
    by_table: dict[str, list[str]] = {}
    for r in rows:
        by_table.setdefault(r.entity_table, []).append(r.entity_id)

    loaded: dict[tuple[str, str], Any] = {}
    for table, ids in by_table.items():
        spec = _ENTITY_MAP.get(table)
        if spec is None:
            continue
        model, pk_attr, _ = spec
        col = getattr(model, pk_attr)
        for obj in session.scalars(select(model).where(col.in_(ids))):
            loaded[(table, str(getattr(obj, pk_attr)))] = obj

    out: list[RunEngineRecordOut] = []
    for r in rows:
        spec = _ENTITY_MAP.get(r.entity_table)
        obj = loaded.get((r.entity_table, r.entity_id))
        detail = r.detail if isinstance(r.detail, dict) else {}
        if spec is not None and obj is not None:
            proj = spec[2](obj, detail)
        else:  # canonical row gone (or unknown table) — honest id-only fallback
            proj = {"title": r.entity_id, "subtitle": r.entity_table, "fields": [], "link": None}
        out.append(RunEngineRecordOut(
            entity_id=r.entity_id, entity_table=r.entity_table, operation=r.operation,
            title=proj.get("title") or r.entity_id, subtitle=proj.get("subtitle") or "",
            fields=proj.get("fields") or [], link=proj.get("link"), url=proj.get("url") or "",
            detail=detail,
        ))
    return out
