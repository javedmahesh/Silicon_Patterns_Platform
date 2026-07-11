"""Lead Scoring service: gather inputs from the master DB, score every company,
persist ``lead_scores`` (with an ordinal priority_rank), and summarize.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from lead_scoring.config import ScoringConfig
from lead_scoring.human_review import adjusted_score
from lead_scoring.scorer import CompanyInputs, score_company
from master_db.bulk import bulk_upsert
from master_db.models import (
    Company,
    CompanyRollup,
    DecisionMaker,
    DemandSignal,
    LeadReview,
    LeadScore,
    Opportunity,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def gather_inputs(session: Session) -> list[CompanyInputs]:
    """Build one CompanyInputs per company from cross-engine aggregates."""
    opp = {
        domain: (mx or 0.0, cnt or 0, rd or 0.0)
        for domain, mx, cnt, rd in session.execute(
            select(
                Opportunity.company_domain,
                func.max(Opportunity.effective_opportunity_score),
                func.count(Opportunity.opportunity_id),
                func.max(Opportunity.lead_readiness_score),
            ).group_by(Opportunity.company_domain)
        ).all()
    }
    demand = {d.company_domain: d for d in session.scalars(select(DemandSignal)).all()}
    rollup = {r.company_domain: r for r in session.scalars(select(CompanyRollup)).all()}
    dms = {
        domain: (cnt or 0, sen or 0, avg or 0.0)
        for domain, cnt, sen, avg in session.execute(
            select(
                DecisionMaker.company_domain,
                func.count(DecisionMaker.id),
                func.sum(case((DecisionMaker.seniority == "senior", 1), else_=0)),
                func.avg(func.coalesce(DecisionMaker.agent_score, DecisionMaker.match_score)),
            )
            .where(DecisionMaker.company_domain.isnot(None))
            .group_by(DecisionMaker.company_domain)
        ).all()
    }

    inputs: list[CompanyInputs] = []
    for c in session.scalars(select(Company)).all():
        o = opp.get(c.company_domain)
        d = demand.get(c.company_domain)
        r = rollup.get(c.company_domain)
        m = dms.get(c.company_domain)
        inputs.append(CompanyInputs(
            company_domain=c.company_domain,
            company_name=c.company_name,
            company_tier=c.company_tier or "UNKNOWN",
            prospect_type=c.prospect_type or "UNKNOWN",
            compliance_flag=c.compliance_flag or "UNKNOWN",
            max_effective_opportunity_score=float(o[0]) if o else 0.0,
            num_opportunities=int(o[1]) if o else 0,
            opp_readiness=float(o[2]) if o else 0.0,
            demand_score=float(d.demand_score) if d else 0.0,
            normalized_demand_score=float(d.normalized_demand_score) if d else 0.0,
            demand_readiness=float(d.lead_readiness_score) if d else 0.0,
            rollup_readiness=float(r.lead_readiness_score) if r else 0.0,
            total_engineering_jobs=int(d.total_engineering_jobs) if d else 0,
            dm_count=int(m[0]) if m else 0,
            senior_dm_count=int(m[1]) if m else 0,
            avg_match_score=float(m[2]) if m else 0.0,
        ))
    return inputs


@dataclass(slots=True)
class ScoringSummary:
    scored: int
    grade_counts: dict[str, int]
    missing_counts: dict[str, int]
    full_data_companies: int
    top: list[tuple] = field(default_factory=list)  # (domain, name, score, grade, subscores)


def score_all(session: Session, cfg: ScoringConfig | None = None) -> ScoringSummary:
    cfg = cfg or ScoringConfig.load()
    scored = [(inp, score_company(inp, cfg)) for inp in gather_inputs(session)]
    # Rank by final score, then by coverage so a fully-evidenced company wins ties
    # over an equally-scored single-signal one.
    scored.sort(key=lambda t: (t[1].final_score, t[1].coverage), reverse=True)

    grade_counts: dict[str, int] = {}
    missing_counts: dict[str, int] = {}
    full = 0
    now = _utcnow()
    # Optional human-review -> score adjustment (reconciled Change_05). The model
    # score/grade above are NEVER changed; we derive a SEPARATE adjusted value from
    # each company's current review (respecting expiry). adjusted == model when the
    # feature is off / no review / expired. Always from the pristine model score.
    reviews = {r.company_domain: r for r in session.scalars(select(LeadReview)).all()}
    rowdicts: list[dict] = []
    for rank, (inp, res) in enumerate(scored, start=1):
        review = reviews.get(inp.company_domain)
        status = review.review_status if review is not None else None
        expired = bool(review is not None and review.expires_at is not None
                       and _aware(review.expires_at) < now)
        adj_score, adj_grade, adj_rationale = adjusted_score(
            res.final_score, res.grade, status, cfg, expired=expired)
        rationale = dict(res.rationale)
        if adj_rationale and review is not None:
            adj_rationale = {
                **adj_rationale, "reason": review.human_notes,
                "reviewed_by": review.reviewed_by_email,
                "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
                "expires_at": review.expires_at.isoformat() if review.expires_at else None,
            }
        if adj_rationale:
            rationale["adjustment"] = adj_rationale
        rowdicts.append(dict(
            company_domain=inp.company_domain,
            lead_score=res.final_score, grade=res.grade, priority_rank=rank,
            opportunity_subscore=res.opportunity_subscore, demand_subscore=res.demand_subscore,
            readiness_subscore=res.readiness_subscore, dm_subscore=res.dm_subscore,
            region_mult=res.region_mult, prospect_mult=res.prospect_mult, tier_mult=res.tier_mult,
            coverage=res.coverage, confidence=res.confidence,
            adjusted_score=adj_score, adjusted_grade=adj_grade,
            rationale=rationale, model_version=cfg.model_version, scored_at=now,
        ))
        grade_counts[res.grade] = grade_counts.get(res.grade, 0) + 1
        for mi in res.missing:
            missing_counts[mi] = missing_counts.get(mi, 0) + 1
        if not res.missing:
            full += 1
    # One bulk upsert instead of a per-company SELECT+write loop.
    bulk_upsert(session, LeadScore, rowdicts, ["company_domain"])
    session.commit()

    top = [
        (inp.company_domain, inp.company_name, res.final_score, res.grade,
         (res.opportunity_subscore, res.demand_subscore, res.readiness_subscore, res.dm_subscore))
        for inp, res in scored[:25]
    ]
    return ScoringSummary(len(scored), grade_counts, missing_counts, full, top)
