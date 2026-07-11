"""Decision-maker decision-intelligence engine (Phase 2) — deterministic, no LLM.

Pure, documented scoring over data the platform already owns (decision_makers +
the company-level signals in lead_scores / opportunities / demand_signals /
leadership_signals / engagement_recommendations / companies). Nothing here is
persisted: the metrics are derived on read and the only DB cost is a handful of
*batched* lookups per request (``build_company_contexts`` — no N+1). Pure
per-DM helpers (department / seniority / confidence) are ``lru_cache``-memoised.

Exposed concepts
----------------
* ``classify_department`` — taxonomy classification from the title (+ functional
  area + the actor's raw department). No manual tagging.
* ``exec_rank`` / ``RANK_LABELS`` — organisation hierarchy inferred from titles.
* ``influence`` — influence_score (raw + normalised 0-100) + the factors behind it.
* ``confidence`` — confidence_score (0-100) + High/Medium/Low + factors.
* ``rank_contacts`` — primary / secondary / alternate per company, with reasons.
* ``department_group`` — the Company Contact Map bucket for a department.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from master_db.models import (
    Company,
    DecisionMaker,
    DemandSignal,
    EngagementRecommendation,
    LeadScore,
    LeadershipSignal,
    Opportunity,
)

# --------------------------------------------------------------------------- #
# Department taxonomy + Company Contact Map groups
# --------------------------------------------------------------------------- #
DEPARTMENTS: tuple[str, ...] = (
    "Executive", "Engineering", "ASIC", "RTL", "Verification", "DFT",
    "Physical Design", "Embedded", "AI", "Sales", "Marketing", "Operations",
    "HR", "Finance", "Legal", "Business Development", "Procurement", "Unknown",
)
_ENG_DEPTS = frozenset(
    ("Engineering", "ASIC", "RTL", "Verification", "DFT", "Physical Design", "Embedded", "AI")
)

# Engineering-leaning departments matched FIRST (most specific → general); a C-suite
# title only falls through to "Executive" when no engineering function is named.
_FUNCTION_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("DFT", ("design for test", "design-for-test", " dft", "dft ", "scan insertion", "atpg", "mbist")),
    ("RTL", (" rtl", "rtl ", "rtl design", "register transfer")),
    ("Verification", ("verification", "design verification", " dv ", " uvm", "formal verif", "verif")),
    ("Physical Design", ("physical design", "place and route", " pnr", "floorplan",
                          "timing closure", "static timing", " sta ", "signoff", "sign-off")),
    ("ASIC", ("asic", " soc ", "soc ", "system on chip", "system-on-chip", "vlsi",
              "chip design", "silicon design", "ip design")),
    ("Embedded", ("embedded", "firmware", "rtos", " bsp", "device driver", "bare metal")),
    ("AI", ("artificial intelligence", " ai ", " ai/", "ai/ml", "machine learning",
            "deep learning", "mlops", "data science", "data scien", "neural")),
    ("Engineering", ("engineer", "engineering", "hardware", "silicon", "semiconductor",
                     "architect", " cad ", "r&d", "research and development", "technolog")),
    ("Sales", ("sales", "account executive", "account manager", "revenue officer", " ae ", "go-to-market")),
    ("Marketing", ("marketing", "brand", "communications", "content", "growth", "demand gen")),
    ("Business Development", ("business development", "corporate development", "biz dev",
                              " bd ", "partnership", "alliances", "strategic partner")),
    ("Procurement", ("procurement", "purchasing", "sourcing", "supply chain", "vendor management")),
    ("HR", ("human resources", " hr ", "hr ", "talent", "recruit", "people operations",
            "people ops", "staffing", "hiring manager")),
    ("Finance", ("finance", "financial", "accounting", "controller", "treasury", "fp&a")),
    ("Legal", ("legal", "counsel", "compliance", "intellectual property", " ip ", "patent")),
    ("Operations", ("operations", "operating officer", " ops ", "program manager",
                    "project manager", " pmo ", "logistics")),
)

_GROUP_BY_DEPT = {
    "Executive": "Executive",
    **{d: "Engineering Leaders" for d in _ENG_DEPTS},
    "HR": "Recruiting",
    "Sales": "Sales",
    "Marketing": "Marketing",
    "Business Development": "Business Development",
}
CONTACT_GROUPS: tuple[str, ...] = (
    "Executive", "Engineering Leaders", "Recruiting", "Sales", "Marketing",
    "Business Development", "Other",
)


def department_group(department: str) -> str:
    """The Company Contact Map bucket for a classified department."""
    return _GROUP_BY_DEPT.get(department, "Other")


# --------------------------------------------------------------------------- #
# Organisation hierarchy (inferred from title)
# --------------------------------------------------------------------------- #
RANK_LABELS: dict[int, str] = {
    0: "Founder / CEO",
    1: "C-Suite",
    2: "EVP / SVP",
    3: "VP",
    4: "Director",
    5: "Manager",
    6: "Individual Contributor",
    7: "Unknown",
}
def _norm(*parts: str | None) -> str:
    # str(p) guards against non-string profile_data values (e.g. a list slipping in).
    return " " + " ".join(str(p).lower().strip() for p in parts if p) + " "


# Abbreviations (cto/cfo/vp/…) must match as whole WORDS, never as substrings of a
# larger word (otherwise "cto" matches inside "dire-cto-r"). Multi-word titles
# ("chief executive", "vice president") are matched as phrases.
@lru_cache(maxsize=4096)
def exec_rank(title: str) -> int:
    """Hierarchy rank from a title string (0 = Founder/CEO … 6 = IC, 7 = Unknown)."""
    t = (title or "").lower()
    words = set(re.findall(r"[a-z&]+", t))

    def w(*tokens: str) -> bool:
        return any(tok in words for tok in tokens)

    def p(*phrases: str) -> bool:
        return any(ph in t for ph in phrases)

    if (w("ceo", "founder", "chairman", "chairwoman", "owner", "proprietor")
            or p("chief executive", "co-founder", "managing director", "general manager")
            or ("president" in words and not w("vice", "vp"))):
        return 0
    if w("cto", "cfo", "coo", "cmo", "cro", "cio", "ciso", "cpo", "cdo", "clo", "cxo") or p("chief "):
        return 1
    if w("evp", "svp") or p("executive vice president", "senior vice president"):
        return 2
    if w("vp") or p("vice president"):
        return 3
    if w("director", "head"):
        return 4
    if w("manager", "principal", "staff", "lead", "supervisor"):
        return 5
    if w("engineer", "engineering", "specialist", "analyst", "associate", "consultant",
          "scientist", "designer", "developer", "architect", "intern", "coordinator", "representative"):
        return 6
    return 7


def rank_label(rank: int) -> str:
    return RANK_LABELS.get(rank, "Unknown")


@lru_cache(maxsize=4096)
def classify_department(title: str, functional_area: str = "", raw_department: str = "") -> str:
    """Deterministically classify a decision maker into the department taxonomy.

    Engineering functions win over a generic C-suite label (so a CTO → Engineering,
    a Chief AI Officer → AI), while pure top management (CEO/CFO/COO/CMO…) → Executive.
    """
    text = _norm(title, functional_area, raw_department)
    rank = exec_rank(title)
    eng_match = next((dept for dept, kws in _FUNCTION_RULES
                      if dept in _ENG_DEPTS and any(k in text for k in kws)), None)
    if rank <= 1:  # founder / C-suite
        return eng_match or "Executive"
    for dept, kws in _FUNCTION_RULES:
        if any(k in text for k in kws):
            return dept
    return "Unknown"


# engineering / buyer relevance per department (0–100) — feeds influence + ranking.
_ENG_RELEVANCE: dict[str, int] = {
    "ASIC": 100, "RTL": 100, "Verification": 100, "DFT": 100, "Physical Design": 100, "AI": 100,
    "Embedded": 90, "Engineering": 85, "Executive": 60,
    "Business Development": 45, "Procurement": 45, "Operations": 35,
    "Sales": 25, "Marketing": 25, "HR": 20, "Finance": 15, "Legal": 15, "Unknown": 30,
}


def engineering_relevance(department: str) -> int:
    return _ENG_RELEVANCE.get(department, 30)


# --------------------------------------------------------------------------- #
# Influence score — documented weighting (points sum to 100)
# --------------------------------------------------------------------------- #
INFLUENCE_WEIGHTS: dict[str, int] = {
    "executive_level": 25,        # hierarchy rank (CEO … IC)
    "seniority": 6,               # engine seniority flag / director+ title
    "department": 8,              # buyer-relevant function
    "engineering_relevance": 10,  # fine-grained engineering fit
    "leadership_signals": 9,      # recent leadership movement (company + this person)
    "hiring_signals": 9,          # company engineering hiring demand
    "company_lead_score": 13,     # Discovery lead score for the company
    "opportunity_score": 9,       # best opportunity signal for the company
    "company_tier": 6,            # company maturity tier
    "company_size": 5,            # organisation size
}
_RANK_POINTS = {0: 25, 1: 21, 2: 18, 3: 14, 4: 10, 5: 6, 6: 3, 7: 4}
_DEPT_POINTS = {  # the "department" factor (buyer relevance of the function)
    **{d: 8 for d in _ENG_DEPTS}, "Executive": 8,
    "Business Development": 5, "Procurement": 5, "Operations": 4,
    "Sales": 3, "Marketing": 3, "HR": 3, "Finance": 2, "Legal": 2, "Unknown": 3,
}
_TIER_WEIGHT = {"INCUMBENT": 1.0, "ESTABLISHED": 0.85, "SCALEUP": 0.65, "STARTUP": 0.45, "UNKNOWN": 0.5}


def _size_weight(size_label: str | None) -> float:
    """0–1 weight from an Apify org-size string like '10001+' / '1,001-5,000'."""
    s = (size_label or "").lower().replace(",", "").replace("+", "")
    digits = "".join(c if c.isdigit() else " " for c in s).split()
    n = max((int(d) for d in digits), default=0)
    if n >= 10000:
        return 1.0
    if n >= 1000:
        return 0.8
    if n >= 200:
        return 0.6
    if n >= 50:
        return 0.4
    if n > 0:
        return 0.25
    return 0.0


@dataclass
class CompanyContext:
    """Company-level inputs for influence — built once per company (batched)."""
    domain: str
    lead_score: float = 0.0           # 0–100
    opportunity_score: int = 0        # 0–100
    hiring_score: float = 0.0         # 0–100
    engineering_jobs: int = 0
    leadership_total: int = 0
    leadership_dm_ids: frozenset[int] = frozenset()
    tier: str = "UNKNOWN"
    offering: str = ""


@dataclass
class InfluenceResult:
    raw: float
    normalized: int
    factors: list[str] = field(default_factory=list)


@dataclass
class ConfidenceResult:
    score: int
    level: str
    factors: list[str] = field(default_factory=list)


def influence(dm: DecisionMaker, ctx: CompanyContext) -> InfluenceResult:
    """Deterministic influence_score. ``raw`` is the weighted point sum (0–100);
    ``normalized`` is ``round(raw)`` clamped to 0–100."""
    dept = classify_department(dm.current_title or dm.headline or "",
                               dm.functional_area or "", dm.department or "")
    rank = exec_rank(dm.current_title or dm.headline or "")
    eng_rel = engineering_relevance(dept)
    pts: dict[str, float] = {}
    factors: list[str] = []

    pts["executive_level"] = _RANK_POINTS.get(rank, 4)
    if rank <= 3:
        factors.append(f"{rank_label(rank)}-level seniority")

    sen = 6 if (dm.seniority or "").lower() == "senior" else (4 if rank <= 4 else 0)
    pts["seniority"] = sen

    pts["department"] = _DEPT_POINTS.get(dept, 3)
    pts["engineering_relevance"] = round(eng_rel / 100 * INFLUENCE_WEIGHTS["engineering_relevance"], 2)
    if dept in _ENG_DEPTS:
        factors.append(f"{dept} decision area")
    elif dept == "Executive":
        factors.append("Executive sponsor")

    ldr = 0.0
    if ctx.leadership_total:
        ldr += min(6.0, 2 + ctx.leadership_total)
    if dm.id in ctx.leadership_dm_ids:
        ldr += 3.0
        factors.append("Recent leadership activity")
    pts["leadership_signals"] = min(float(INFLUENCE_WEIGHTS["leadership_signals"]), ldr)

    pts["hiring_signals"] = round(ctx.hiring_score / 100 * INFLUENCE_WEIGHTS["hiring_signals"], 2)
    if ctx.engineering_jobs:
        factors.append("Active engineering hiring")

    pts["company_lead_score"] = round(min(100.0, ctx.lead_score) / 100 * INFLUENCE_WEIGHTS["company_lead_score"], 2)
    pts["opportunity_score"] = round(min(100, ctx.opportunity_score) / 100 * INFLUENCE_WEIGHTS["opportunity_score"], 2)
    if ctx.opportunity_score >= 60:
        factors.append("Strong company opportunity signals")
    pts["company_tier"] = round(_TIER_WEIGHT.get(ctx.tier, 0.5) * INFLUENCE_WEIGHTS["company_tier"], 2)
    pts["company_size"] = round(_size_weight(dm.company_size) * INFLUENCE_WEIGHTS["company_size"], 2)

    raw = round(sum(pts.values()), 2)
    normalized = max(0, min(100, round(raw)))
    return InfluenceResult(raw=raw, normalized=normalized, factors=factors)


# --------------------------------------------------------------------------- #
# Confidence score — documented weighting (points sum to 100)
# --------------------------------------------------------------------------- #
CONFIDENCE_WEIGHTS: dict[str, int] = {
    "verified_email": 25, "phone": 15, "linkedin": 12, "company_domain": 13,
    "profile_completeness": 20, "data_freshness": 10, "apify_enrichment": 5,
}
_VERIFIED_EMAIL = frozenset(("verified", "valid", "safe", "deliverable", "ok"))


def _freshness_points(ingested_at: datetime | None) -> int:
    if not ingested_at:
        return 0
    now = datetime.now(timezone.utc)
    ref = ingested_at if ingested_at.tzinfo else ingested_at.replace(tzinfo=timezone.utc)
    days = (now - ref).days
    if days <= 30:
        return 10
    if days <= 90:
        return 7
    if days <= 180:
        return 4
    return 2


def confidence(dm: DecisionMaker) -> ConfidenceResult:
    """Deterministic contact confidence (0–100) + High/Medium/Low."""
    pts = 0
    factors: list[str] = []
    email = (dm.work_email or "").strip()
    if email and (dm.email_status or "").lower() in _VERIFIED_EMAIL:
        pts += CONFIDENCE_WEIGHTS["verified_email"]
        factors.append("Verified email")
    elif email:
        pts += 12
        factors.append("Email on file")
    if (dm.work_phone or "").strip():
        pts += CONFIDENCE_WEIGHTS["phone"]
        factors.append("Phone on file")
    if (dm.linkedin_url or "").strip():
        pts += CONFIDENCE_WEIGHTS["linkedin"]
        factors.append("LinkedIn profile")
    if dm.company_domain:
        pts += CONFIDENCE_WEIGHTS["company_domain"]

    dept = classify_department(dm.current_title or dm.headline or "",
                               dm.functional_area or "", dm.department or "")
    complete = [
        bool((dm.full_name or "").strip() or (dm.first_name and dm.last_name)),
        bool((dm.current_title or dm.headline or "").strip()),
        bool((dm.seniority or "").strip()),
        bool(dm.city or dm.country or (dm.location or "").strip()),
        dept != "Unknown",
    ]
    pts += round(sum(complete) / len(complete) * CONFIDENCE_WEIGHTS["profile_completeness"])

    pts += _freshness_points(dm.ingested_at)

    pd = dm.profile_data or {}
    enrich = 2 if isinstance(pd.get("raw"), dict) else 0
    # Values can be scalars OR lists (e.g. skills) — coerce before truth-testing.
    curated = sum(1 for k in ("company_size", "industry", "department", "summary", "skills")
                  if str(pd.get(k) or "").strip())
    enrich += min(3, curated)
    pts += enrich

    score = max(0, min(100, pts))
    level = "High" if score >= 70 else "Medium" if score >= 40 else "Low"
    return ConfidenceResult(score=score, level=level, factors=factors)


# --------------------------------------------------------------------------- #
# Batched company-context loaders (no N+1)
# --------------------------------------------------------------------------- #
def build_company_contexts(session: Session, domains: list[str | None]) -> dict[str, CompanyContext]:
    """Build a {domain: CompanyContext} map for many companies in a few grouped
    queries (lead score, best opportunity, demand, leadership, tier, offering)."""
    doms = sorted({d for d in domains if d})
    out = {d: CompanyContext(domain=d) for d in doms}
    if not doms:
        return out

    for ls in session.scalars(select(LeadScore).where(LeadScore.company_domain.in_(doms))):
        out[ls.company_domain].lead_score = float(ls.adjusted_score if ls.adjusted_score is not None else ls.lead_score or 0.0)

    for dom, best in session.execute(
        select(Opportunity.company_domain, func.max(Opportunity.effective_opportunity_score))
        .where(Opportunity.company_domain.in_(doms)).group_by(Opportunity.company_domain)
    ):
        if dom in out:
            out[dom].opportunity_score = int(best or 0)

    for ds in session.scalars(select(DemandSignal).where(DemandSignal.company_domain.in_(doms))):
        ctx = out[ds.company_domain]
        ctx.hiring_score = max(0.0, min(100.0, float(ds.normalized_demand_score or ds.demand_score or 0.0)))
        ctx.engineering_jobs = int(ds.total_engineering_jobs or 0)

    for sig in session.scalars(select(LeadershipSignal).where(LeadershipSignal.company_domain.in_(doms))):
        ctx = out[sig.company_domain]
        ctx.leadership_total += 1
        if sig.decision_maker_id:
            ctx.leadership_dm_ids = ctx.leadership_dm_ids | {sig.decision_maker_id}

    for dom, tier in session.execute(
        select(Company.company_domain, Company.company_tier).where(Company.company_domain.in_(doms))
    ):
        if dom in out:
            out[dom].tier = tier or "UNKNOWN"

    for er in session.scalars(select(EngagementRecommendation).where(EngagementRecommendation.company_domain.in_(doms))):
        out[er.company_domain].offering = er.offering or ""

    return out


def context_for(session: Session, domain: str | None) -> CompanyContext:
    if not domain:
        return CompanyContext(domain="")
    return build_company_contexts(session, [domain]).get(domain, CompanyContext(domain=domain))


# --------------------------------------------------------------------------- #
# Per-DM intelligence bundle + contact ranking / recommendations
# --------------------------------------------------------------------------- #
@dataclass
class DmIntel:
    department: str
    department_group: str
    hierarchy_rank: int
    exec_level: str
    engineering_relevance: int
    influence_score: int
    influence_raw: float
    influence_factors: list[str]
    confidence_score: int
    confidence_level: str
    confidence_factors: list[str]


def compute(dm: DecisionMaker, ctx: CompanyContext) -> DmIntel:
    dept = classify_department(dm.current_title or dm.headline or "",
                               dm.functional_area or "", dm.department or "")
    rank = exec_rank(dm.current_title or dm.headline or "")
    inf = influence(dm, ctx)
    conf = confidence(dm)
    return DmIntel(
        department=dept,
        department_group=department_group(dept),
        hierarchy_rank=rank,
        exec_level=rank_label(rank),
        engineering_relevance=engineering_relevance(dept),
        influence_score=inf.normalized,
        influence_raw=inf.raw,
        influence_factors=inf.factors,
        confidence_score=conf.score,
        confidence_level=conf.level,
        confidence_factors=conf.factors,
    )


@dataclass
class RankedContact:
    dm: DecisionMaker
    intel: DmIntel
    ranking_score: float
    rank: str            # "primary" | "secondary" | "alternate" | ""
    reasons: list[str]


_ROLE_BY_INDEX = {0: "primary", 1: "secondary", 2: "alternate"}


def _reasons_for(dm: DecisionMaker, intel: DmIntel, ctx: CompanyContext) -> list[str]:
    reasons: list[str] = []
    title = (dm.current_title or dm.headline or "").strip()
    if intel.hierarchy_rank <= 3 and title:
        reasons.append(f"{title} ({intel.exec_level})")
    elif title:
        reasons.append(title)
    if intel.department in _ENG_DEPTS:
        reasons.append(f"{intel.department} decision area")
    elif intel.department == "Executive":
        reasons.append("Executive sponsor")
    reasons.append(f"Influence {intel.influence_score}/100")
    if intel.confidence_level == "High":
        reasons.append("Verified contact details")
    elif intel.confidence_score >= 40:
        reasons.append("Reachable contact")
    if dm.id in ctx.leadership_dm_ids:
        reasons.append("Recent leadership activity")
    if ctx.engineering_jobs:
        reasons.append("Company actively hiring engineers")
    if ctx.opportunity_score >= 60:
        reasons.append("Strong company opportunity signals")
    if ctx.offering:
        reasons.append(f"Aligned with Silicon Patterns {ctx.offering}")
    return reasons


def rank_contacts(dms: list[DecisionMaker], ctx: CompanyContext) -> list[RankedContact]:
    """Rank a company's decision makers and tag the top three primary/secondary/
    alternate, each with deterministic reasoning. Ranking blends influence (the
    dominant term), confidence (reachability) and a small department-relevance and
    leadership/hiring nudge — company-level terms are already inside influence."""
    scored: list[RankedContact] = []
    for dm in dms:
        intel = compute(dm, ctx)
        ranking = (
            intel.influence_score
            + intel.confidence_score * 0.25
            + intel.engineering_relevance * 0.05
            + (4 if dm.id in ctx.leadership_dm_ids else 0)
        )
        scored.append(RankedContact(dm=dm, intel=intel, ranking_score=round(ranking, 2),
                                    rank="", reasons=[]))
    # Highest ranking first; stable tiebreak on influence then id for determinism.
    scored.sort(key=lambda r: (-r.ranking_score, -r.intel.influence_score, r.dm.id))
    for i, rc in enumerate(scored):
        rc.rank = _ROLE_BY_INDEX.get(i, "")
        rc.reasons = _reasons_for(rc.dm, rc.intel, ctx)
    return scored
