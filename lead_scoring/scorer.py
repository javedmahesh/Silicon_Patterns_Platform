"""Pure lead-scoring math: CompanyInputs -> ScoreResult. No DB, no I/O.

Four 0-100 subscores, blended by configurable weights into a base score, then
adjusted by region / prospect-type / company-tier multipliers and clamped to
0-100. Every intermediate value is recorded in ``rationale`` for explainability.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from lead_scoring.config import ScoringConfig


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


@dataclass(slots=True)
class CompanyInputs:
    company_domain: str
    company_name: str = ""
    # classification (Industry Discovery)
    company_tier: str = "UNKNOWN"
    prospect_type: str = "UNKNOWN"
    compliance_flag: str = "UNKNOWN"
    # opportunity (Blog Crawler)
    max_effective_opportunity_score: float = 0.0
    num_opportunities: int = 0
    opp_readiness: float = 0.0
    # demand (Career Scraper)
    demand_score: float = 0.0
    normalized_demand_score: float = 0.0
    demand_readiness: float = 0.0
    rollup_readiness: float = 0.0
    total_engineering_jobs: int = 0
    # decision makers (LinkedIn)
    dm_count: int = 0
    senior_dm_count: int = 0
    avg_match_score: float = 0.0

    @property
    def has_opportunity(self) -> bool:
        return self.num_opportunities > 0

    @property
    def has_demand(self) -> bool:
        return self.demand_score > 0 or self.total_engineering_jobs > 0

    @property
    def has_decision_makers(self) -> bool:
        return self.dm_count > 0


@dataclass(slots=True)
class ScoreResult:
    company_domain: str
    opportunity_subscore: float
    demand_subscore: float
    readiness_subscore: float
    dm_subscore: float
    region_mult: float
    prospect_mult: float
    tier_mult: float
    base_score: float
    final_score: float
    grade: str
    coverage: int = 0
    confidence: str = "low"
    missing: list[str] = field(default_factory=list)
    rationale: dict = field(default_factory=dict)


def score_company(inp: CompanyInputs, cfg: ScoringConfig) -> ScoreResult:
    # --- four component subscores (each 0-100) ---
    opportunity = _clamp(
        inp.max_effective_opportunity_score
        + cfg.opportunity_multi_bonus * max(0, inp.num_opportunities - 1)
    )
    demand_value = inp.normalized_demand_score if inp.normalized_demand_score > 0 else inp.demand_score
    demand = _clamp(100.0 * demand_value / cfg.demand_reference) if cfg.demand_reference else 0.0
    readiness = _clamp(max(inp.opp_readiness, inp.demand_readiness, inp.rollup_readiness))
    dm = _clamp(min(
        cfg.dm_cap,
        cfg.dm_points_senior * inp.senior_dm_count
        + cfg.dm_points_other * max(0, inp.dm_count - inp.senior_dm_count),
    ))

    # --- coverage-normalized weighted base ---
    # Blend the four subscores, but divide the weighted sum by the weight that
    # actually had data (raised to a tunable strength) so a strong company with
    # missing signals is not diluted by the absent zeros. coverage_normalization
    # 0 == legacy weighted average; 1 == full normalization (one present signal
    # can stand on its own merit). Full-coverage companies are unaffected.
    w = cfg.weights
    components = (
        ("opportunity", opportunity, inp.has_opportunity),
        ("demand", demand, inp.has_demand),
        ("readiness", readiness, readiness > 0),
        ("decision_maker", dm, inp.has_decision_makers),
    )
    weighted_sum = sum(w[name] * value for name, value, _ in components)
    present_weight = sum(w[name] for name, _, present in components if present)
    base = _clamp(weighted_sum / present_weight ** cfg.coverage_normalization) if present_weight else 0.0

    # --- coverage / confidence (the 3 engine signals: opportunity, demand, DMs) ---
    coverage = sum((inp.has_opportunity, inp.has_demand, inp.has_decision_makers))
    confidence = cfg.confidence_for(coverage)

    # --- fit multipliers ---
    r_mult = cfg.region_for(inp.compliance_flag)
    p_mult = cfg.prospect_for(inp.prospect_type)
    t_mult = cfg.tier_for(inp.company_tier)
    final = _clamp(base * r_mult * p_mult * t_mult)
    grade = cfg.grade_for(final)

    missing: list[str] = []
    if not inp.has_opportunity:
        missing.append("opportunity")
    if not inp.has_demand:
        missing.append("demand")
    if not inp.has_decision_makers:
        missing.append("decision_makers")
    if inp.company_tier == "UNKNOWN" and inp.prospect_type == "UNKNOWN":
        missing.append("classification")

    rationale = {
        "subscores": {
            "opportunity": round(opportunity, 1), "demand": round(demand, 1),
            "readiness": round(readiness, 1), "decision_maker": round(dm, 1),
        },
        "weights": dict(w),
        "weighted_base": round(base, 2),
        "coverage": {
            "signals_present": coverage, "signals_total": 3, "confidence": confidence,
            "raw_weighted_sum": round(weighted_sum, 2),
            "normalization": cfg.coverage_normalization,
        },
        "multipliers": {
            "region": r_mult, "prospect": p_mult, "tier": t_mult,
            "combined": round(r_mult * p_mult * t_mult, 3),
        },
        "inputs": {
            "opportunities": inp.num_opportunities,
            "demand_score": round(inp.demand_score, 1),
            "engineering_jobs": inp.total_engineering_jobs,
            "decision_makers": inp.dm_count,
            "senior_decision_makers": inp.senior_dm_count,
            "company_tier": inp.company_tier,
            "prospect_type": inp.prospect_type,
            "compliance_flag": inp.compliance_flag,
        },
        "missing_inputs": missing,
        "final_lead_score": round(final, 2),
        "grade": grade,
    }
    return ScoreResult(
        company_domain=inp.company_domain,
        opportunity_subscore=round(opportunity, 2),
        demand_subscore=round(demand, 2),
        readiness_subscore=round(readiness, 2),
        dm_subscore=round(dm, 2),
        region_mult=r_mult, prospect_mult=p_mult, tier_mult=t_mult,
        base_score=round(base, 2), final_score=round(final, 2), grade=grade,
        coverage=coverage, confidence=confidence,
        missing=missing, rationale=rationale,
    )
