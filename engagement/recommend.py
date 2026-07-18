"""The recommendation rules — evidence in, (need, offering, pitch) out.

``recommend_for_company`` is pure (takes already-fetched ORM rows) so it is
unit-testable without a database. ``recommend_all`` / ``rebuild`` wire it to the
master DB and the ``engagement_recommendations`` table.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from master_db.models import (
    Company,
    DecisionMaker,
    DemandSignal,
    EngagementRecommendation,
    LeadershipSignal,
    Opportunity,
)

MODEL_VERSION = "engagement-v1"

# Discipline -> Silicon Patterns offering + a need template ({trigger} is the
# contextual framing) + a one-line, evidence-grounded pitch (1-2 sentences).
OFFERINGS: dict[str, dict[str, str]] = {
    "verification": {
        "offering": "Verification engineering services",
        "need": "Scaling ASIC/SoC verification capacity{trigger}.",
        "pitch": "Silicon Patterns can accelerate your verification schedule with experienced DV "
                 "engineers and scalable UVM/SystemVerilog support.",
    },
    "rtl": {
        "offering": "RTL / front-end design services",
        "need": "Expanding RTL / front-end design capacity{trigger}.",
        "pitch": "Silicon Patterns can extend your front-end team with proven RTL designers to keep "
                 "block- and SoC-level schedules on track.",
    },
    "physical_design": {
        "offering": "Physical design & timing-closure services",
        "need": "Adding physical-design / timing-closure capacity{trigger}.",
        "pitch": "Silicon Patterns can support your backend flow with experienced physical-design and "
                 "STA engineers to drive timing closure and tapeout readiness.",
    },
    "dft": {
        "offering": "DFT engineering services",
        "need": "Building DFT coverage for an active silicon program{trigger}.",
        "pitch": "Silicon Patterns can strengthen your DFT flow with scan, MBIST, and ATPG expertise "
                 "to protect test coverage and schedule.",
    },
    "fpga": {
        "offering": "FPGA design services",
        "need": "Expanding FPGA design and prototyping capacity{trigger}.",
        "pitch": "Silicon Patterns can augment your FPGA team with designers experienced in "
                 "prototyping and production FPGA flows.",
    },
    "asic": {
        "offering": "ASIC / SoC design services",
        "need": "Ramping a new ASIC/SoC design program{trigger}.",
        "pitch": "Silicon Patterns can accelerate your ASIC/SoC program with design support from "
                 "architecture through implementation.",
    },
    "embedded": {
        "offering": "Embedded / firmware engineering services",
        "need": "Growing embedded / firmware engineering capacity{trigger}.",
        "pitch": "Silicon Patterns can extend your embedded team with engineers experienced in "
                 "firmware and hardware/software bring-up.",
    },
    "staffing": {
        "offering": "Engineering staff augmentation",
        "need": "Scaling the silicon engineering organization{trigger}.",
        "pitch": "Silicon Patterns can help you scale delivery quickly with flexible, experienced "
                 "silicon engineering teams matched to your roadmap.",
    },
    "enablement": {
        "offering": "Silicon design enablement",
        "need": "Building out silicon design capability.",
        "pitch": "Silicon Patterns can partner on your silicon roadmap with design and verification "
                 "expertise scaled to your needs.",
    },
}

_FOCUS_TO_DISCIPLINE = (
    ("verification", "verification"), ("validation", "verification"), ("dv", "verification"),
    ("physical design", "physical_design"), ("timing", "physical_design"), ("backend", "physical_design"),
    ("back-end", "physical_design"), ("sta", "physical_design"),
    ("dft", "dft"),
    ("fpga", "fpga"),
    ("rtl", "rtl"), ("front-end", "rtl"), ("frontend", "rtl"),
    ("embedded", "embedded"), ("firmware", "embedded"),
    ("asic", "asic"), ("soc", "asic"), ("architecture", "asic"),
)
_SENIOR_SENIORITY = {"senior", "c_level", "chief", "executive", "founder", "owner", "partner"}


def _focus_discipline(text: str | None) -> str | None:
    low = (text or "").strip().lower()
    for needle, disc in _FOCUS_TO_DISCIPLINE:
        if needle in low:
            return disc
    return None


def _discipline_scores(demand: DemandSignal | None) -> dict[str, int]:
    if demand is None:
        return {}
    g = lambda v: v or 0  # noqa: E731 — tolerate unset/None counts on sparse rows
    return {
        "verification": g(demand.verification_jobs) + g(demand.validation_jobs),
        "rtl": g(demand.rtl_jobs),
        "physical_design": g(demand.physical_design_jobs) + g(demand.sta_jobs),
        "dft": g(demand.dft_jobs),
        "fpga": g(demand.fpga_jobs),
        "asic": g(demand.asic_jobs) + g(demand.architecture_jobs),
        "embedded": g(demand.embedded_jobs),
    }


def _confidence(key: str, top_jobs: int, demand: DemandSignal | None,
                opportunities: list, eng_hire, dm_count: int) -> int:
    if key == "enablement":
        return min(100, 15 + (10 if opportunities else 0) + (5 if dm_count else 0))
    score = 25
    score += min(35, top_jobs * 6)                     # per-discipline hiring evidence
    if demand is not None and (demand.hiring_trend or "").upper() == "GROWING":
        score += 10
    score += min(20, len(opportunities) * 8)           # corroborating market events
    if eng_hire is not None:
        score += 10
    if dm_count:
        score += 5
    return min(100, score)


def recommend_for_company(*, company: Company, opportunities: list, demand: DemandSignal | None,
                          leadership: list, dm_count: int = 0, dm_senior_count: int = 0) -> dict:
    """Pure rules: a company's signals -> a recommendation dict. Returns ``None``
    when there is no evidence at all (so empty companies get no pitch)."""
    if not opportunities and demand is None and not leadership and not dm_count:
        return None

    rationale: list[str] = []
    sources: set[str] = set()

    disc = _discipline_scores(demand)
    if demand is not None:
        pf = _focus_discipline(demand.primary_focus)
        if pf:
            disc[pf] = disc.get(pf, 0) + 3
    tech = f"{getattr(company, 'technology_focus', '') or ''} {(demand.technologies_detected if demand else '') or ''}".lower()
    if "fpga" in tech:
        disc["fpga"] = disc.get("fpga", 0) + 2

    top_disc = max(disc, key=lambda k: disc[k]) if disc and max(disc.values()) > 0 else None
    top_jobs = disc.get(top_disc, 0) if top_disc else 0

    if demand is not None and (demand.total_engineering_jobs or 0) > 0:
        sources.add("demand")
        bits = [f"{demand.total_engineering_jobs} engineering jobs"]
        if demand.primary_focus:
            bits.append(f"primary focus {demand.primary_focus}")
        if demand.hiring_trend:
            bits.append(f"trend {demand.hiring_trend}")
        rationale.append("Hiring activity: " + ", ".join(bits))

    if opportunities:
        sources.add("opportunities")
    funding = next((o for o in opportunities if o.opportunity_type == "Funding"), None)
    product = next((o for o in opportunities if o.opportunity_type in ("Product Launch", "Tapeout")), None)
    expansion = next((o for o in opportunities if o.opportunity_type == "Expansion"), None)
    partnership = next((o for o in opportunities if o.opportunity_type == "Partnership"), None)

    eng_hire = None
    if leadership:
        sources.add("leadership")
        eng_hire = next(
            (s for s in leadership
             if s.movement_type in ("new_executive_hire", "promotion")
             and (s.role_function in ("engineering", "technology", "product")
                  or s.seniority_band in ("vp", "svp", "evp", "c_level"))),
            None,
        )

    # Contextual trigger framing (highest-signal event wins).
    trigger = ""
    if funding is not None:
        trigger = (f" following its {funding.funding_stage} round" if funding.funding_stage
                   else " following a recent funding round")
        rationale.append("Funding: " + (funding.funding_stage or "round")
                         + (f" {funding.funding_amount}" if funding.funding_amount else ""))
    elif product is not None:
        trigger = " as it ramps a new silicon program"
        rationale.append(f"Product signal: {product.opportunity_type}"
                         + (f" — {product.product_mentioned}" if product.product_mentioned else ""))
    elif expansion is not None:
        trigger = " as it expands operations"
        rationale.append("Expansion event detected")
    elif eng_hire is not None:
        trigger = " under new engineering leadership"
    elif demand is not None and (demand.hiring_trend or "").upper() == "GROWING":
        trigger = " amid a growing hiring trend"

    if eng_hire is not None:
        rationale.append(f"Leadership: {eng_hire.movement_type.replace('_', ' ')} — {eng_hire.to_title}")
    if partnership is not None:
        rationale.append("Partnership signal detected")
    if getattr(company, "technology_focus", ""):
        rationale.append(f"Technology focus: {company.technology_focus}")
    prospect = (getattr(company, "prospect_type", "") or "").replace("_", " ").title()
    tier = (getattr(company, "company_tier", "") or "").title()
    if prospect not in ("", "Unknown") or tier not in ("", "Unknown"):
        rationale.append("Company type: " + " ".join(x for x in (tier, prospect) if x and x != "Unknown"))
    if dm_count:
        sources.add("decision_makers")
        rationale.append(f"Decision makers: {dm_count} resolved ({dm_senior_count} senior)")

    if top_disc:
        key = top_disc
    elif funding or product or expansion or eng_hire:
        key = "staffing"
    else:
        key = "enablement"

    spec = OFFERINGS[key]
    confidence = _confidence(key, top_jobs, demand, opportunities, eng_hire, dm_count)
    if not rationale:
        rationale.append("Limited intelligence available; recommendation is provisional.")

    return {
        "business_need": spec["need"].format(trigger=trigger),
        "offering": spec["offering"],
        "pitch": spec["pitch"],
        "confidence": confidence,
        "confidence_label": "high" if confidence >= 70 else ("medium" if confidence >= 40 else "low"),
        "rationale": rationale,
        "signals_used": len(sources),
    }


def _group(rows, attr: str) -> dict[str, list]:
    out: dict[str, list] = {}
    for r in rows:
        out.setdefault(getattr(r, attr), []).append(r)
    return out


def recommend_all(session: Session) -> list[dict]:
    companies = list(session.scalars(select(Company)))
    opps_by = _group(session.scalars(select(Opportunity)), "company_domain")
    demand_by = {d.company_domain: d for d in session.scalars(select(DemandSignal))}
    ldr_by = _group(session.scalars(select(LeadershipSignal)), "company_domain")
    dms_by = _group(session.scalars(select(DecisionMaker)), "company_domain")

    out: list[dict] = []
    for c in companies:
        d = c.company_domain
        dms = dms_by.get(d, [])
        senior = sum(1 for x in dms if (x.seniority or "").lower() in _SENIOR_SENIORITY)
        rec = recommend_for_company(
            company=c, opportunities=opps_by.get(d, []), demand=demand_by.get(d),
            leadership=ldr_by.get(d, []), dm_count=len(dms), dm_senior_count=senior,
        )
        if rec is not None:
            rec["company_domain"] = d
            out.append(rec)
    return out


def rebuild(session: Session) -> dict[str, int]:
    """Recompute every company's recommendation (idempotent: clear + insert)."""
    from orchestrator import provenance

    recs = recommend_all(session)
    session.execute(delete(EngagementRecommendation))
    session.flush()
    stamp = datetime.now(timezone.utc)
    for r in recs:
        session.add(EngagementRecommendation(**r, model_version=MODEL_VERSION, computed_at=stamp))
        provenance.record(session, "engagement_recommendations", r["company_domain"], "derived", {
            "offering": r.get("offering", ""),
            "business_need": r.get("business_need", ""),
            "confidence": r.get("confidence"),
            "confidence_label": r.get("confidence_label", ""),
        })
    session.commit()
    return {"total": len(recs)}
