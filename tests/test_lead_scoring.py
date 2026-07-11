"""Tests for the P3 Lead Scoring service."""
import pytest
from sqlalchemy import select

from lead_scoring.config import ScoringConfig
from lead_scoring.scorer import CompanyInputs, score_company
from lead_scoring.service import score_all
from master_db.local import make_session_factory
from master_db.models import Company, DemandSignal, LeadScore


def test_full_signal_scores_high_and_complete():
    cfg = ScoringConfig.default()
    inp = CompanyInputs(
        "acme.com", "Acme", company_tier="STARTUP", prospect_type="PRODUCT_COMPANY",
        compliance_flag="APPROVED", max_effective_opportunity_score=90, num_opportunities=2,
        opp_readiness=80, demand_score=100, demand_readiness=70, total_engineering_jobs=40,
        dm_count=4, senior_dm_count=4,
    )
    r = score_company(inp, cfg)
    assert r.opportunity_subscore == 95          # 90 + 5*(2-1)
    assert r.demand_subscore == 100
    assert r.dm_subscore == 100
    assert (r.region_mult, r.prospect_mult, r.tier_mult) == (1.0, 1.0, 1.0)
    assert r.final_score == r.base_score and r.final_score >= 70 and r.grade == "A+"
    assert r.missing == []


def test_excluded_region_crushes_score():
    cfg = ScoringConfig.default()
    inp = CompanyInputs(
        "x.cn", "X", company_tier="STARTUP", prospect_type="PRODUCT_COMPANY",
        compliance_flag="EXCLUDED_REGION", demand_score=100, dm_count=4, senior_dm_count=4,
        num_opportunities=1, max_effective_opportunity_score=80,
    )
    r = score_company(inp, cfg)
    assert r.region_mult == 0.3
    assert r.final_score < r.base_score * 0.4


def test_missing_inputs_flagged():
    r = score_company(CompanyInputs("y.com", "Y"), ScoringConfig.default())
    assert set(r.missing) == {"opportunity", "demand", "decision_makers", "classification"}
    assert r.final_score == 0.0 and r.grade == "C"


def test_coverage_normalization_lifts_strong_single_signal():
    cfg = ScoringConfig.default()
    # Demand-only company (no opportunity, no decision makers) but a perfect fit.
    inp = CompanyInputs(
        "solo.com", "Solo", company_tier="SCALEUP", prospect_type="PRODUCT_COMPANY",
        compliance_flag="APPROVED", demand_score=100, normalized_demand_score=100,
        demand_readiness=98, total_engineering_jobs=40,
    )
    r = score_company(inp, cfg)
    assert r.coverage == 1 and r.confidence == "low"
    # Not diluted by the two absent zeros -> ranks as a strong lead, not a B.
    assert r.final_score >= 90 and r.grade == "A+"


def test_confidence_tracks_signal_coverage():
    cfg = ScoringConfig.default()
    fit = dict(company_tier="STARTUP", prospect_type="PRODUCT_COMPANY", compliance_flag="APPROVED")
    one = score_company(CompanyInputs("a.com", demand_score=100, **fit), cfg)
    two = score_company(CompanyInputs("b.com", demand_score=100, num_opportunities=1,
                                      max_effective_opportunity_score=80, **fit), cfg)
    three = score_company(CompanyInputs("c.com", demand_score=100, num_opportunities=1,
                                        max_effective_opportunity_score=80, dm_count=2,
                                        senior_dm_count=1, **fit), cfg)
    assert (one.coverage, one.confidence) == (1, "low")
    assert (two.coverage, two.confidence) == (2, "medium")
    assert (three.coverage, three.confidence) == (3, "high")


def test_coverage_normalization_zero_is_legacy_weighted():
    cfg = ScoringConfig.default()
    cfg.coverage_normalization = 0.0
    inp = CompanyInputs("d.com", demand_score=100, normalized_demand_score=100,
                        demand_readiness=98, company_tier="SCALEUP",
                        prospect_type="PRODUCT_COMPANY", compliance_flag="APPROVED")
    r = score_company(inp, cfg)
    # legacy weighted average: 0.30*100 + 0.20*98 = 49.6 -> B (not lifted)
    assert 49 <= r.final_score <= 50 and r.grade == "B"


def test_grade_bands_are_config_driven():
    cfg = ScoringConfig.default()
    assert cfg.grade_for(75) == "A+"
    assert cfg.grade_for(55) == "A"
    assert cfg.grade_for(35) == "B"
    assert cfg.grade_for(10) == "C"


def test_score_all_persists_ranks_and_breakdown():
    Session = make_session_factory(":memory:")
    with Session() as s:
        s.add(Company(company_domain="a.com", canonical_company_id="A", company_name="A",
                      name_key="a", company_tier="STARTUP", prospect_type="PRODUCT_COMPANY",
                      compliance_flag="APPROVED", validation_status="VALID"))
        s.add(Company(company_domain="b.com", canonical_company_id="B", company_name="B",
                      name_key="b", validation_status="VALID"))
        s.add(DemandSignal(company_domain="a.com", demand_score=100.0,
                           lead_readiness_score=70.0, total_engineering_jobs=40))
        s.flush()

        summary = score_all(s)
        assert summary.scored == 2
        a = s.get(LeadScore, "a.com")
        b = s.get(LeadScore, "b.com")
        assert a.priority_rank == 1 and b.priority_rank == 2     # ordinal rank
        assert a.lead_score > b.lead_score
        assert a.demand_subscore == 100.0
        assert a.rationale["subscores"]["demand"] == 100.0       # score_breakdown stored
        assert "demand" in b.rationale["missing_inputs"]
