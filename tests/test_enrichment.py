"""Test manual company enrichment + its effect on lead scoring."""

from integration.enrichment import apply_enrichment
from lead_scoring.service import score_all
from master_db.local import make_session_factory
from master_db.models import Company, DemandSignal, LeadScore


def _stub(domain, name):
    return Company(company_domain=domain, canonical_company_id=name.upper(),
                   company_name=name, name_key=name.lower(), is_stub=True,
                   validation_status="STUB")  # UNKNOWN tier/prospect/compliance by default


def test_enrichment_classifies_stub_and_lifts_score():
    Session = make_session_factory(":memory:")
    with Session() as s:
        s.add(_stub("tenstorrent.com", "Tenstorrent"))
        s.add(DemandSignal(company_domain="tenstorrent.com", demand_score=100.0,
                           lead_readiness_score=98.0, total_engineering_jobs=42))
        s.flush()

        score_all(s)
        before = s.get(LeadScore, "tenstorrent.com")
        assert before.tier_mult == 0.9 and before.prospect_mult == 0.9 and before.region_mult == 0.9
        before_score = before.lead_score

        changes = apply_enrichment(s)
        c = s.get(Company, "tenstorrent.com")
        assert c.company_tier == "SCALEUP" and c.prospect_type == "PRODUCT_COMPANY"
        assert c.compliance_flag == "APPROVED" and c.is_stub is False and c.validation_status == "VALID"

        score_all(s)
        after = s.get(LeadScore, "tenstorrent.com")
        assert after.tier_mult == 1.0 and after.prospect_mult == 1.0 and after.region_mult == 1.0
        assert after.lead_score > before_score                 # multipliers no longer penalize
        # formula unchanged: base score identical, only multipliers changed
        assert after.rationale["weighted_base"] == before.rationale["weighted_base"]


def test_enrichment_is_idempotent():
    Session = make_session_factory(":memory:")
    with Session() as s:
        s.add(_stub("eliyan.com", "Eliyan"))
        s.flush()
        first = dict(apply_enrichment(s))["eliyan.com"]
        assert first  # something changed
        second = dict(apply_enrichment(s))["eliyan.com"]
        assert second == {}  # nothing left to change
