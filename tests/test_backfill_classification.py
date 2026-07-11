"""Backfill UNKNOWN company classification from already-ingested opportunity rows."""
import importlib.util
from pathlib import Path

from master_db.local import make_session_factory
from master_db.models import Company, Opportunity

ROOT = Path(__file__).resolve().parent.parent


def _load_backfill():
    spec = importlib.util.spec_from_file_location(
        "backfill_clf", ROOT / "scripts" / "backfill_classification.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_backfill_fills_unknown_but_never_overwrites_known():
    backfill = _load_backfill().backfill
    Session = make_session_factory(":memory:")
    with Session() as s:
        s.add_all([
            # UNKNOWN classification — should be filled from its opportunity row
            Company(company_domain="gap.com", canonical_company_id="G", company_name="Gap",
                    name_key="gap", validation_status="VALID"),
            # already classified by Industry Discovery — must NOT be overwritten
            Company(company_domain="known.com", canonical_company_id="K", company_name="Known",
                    name_key="known", company_tier="INCUMBENT", prospect_type="PRODUCT_COMPANY",
                    compliance_flag="APPROVED", validation_status="VALID"),
        ])
        s.flush()
        s.add_all([
            Opportunity(opportunity_id="O1", company_domain="gap.com", company_tier="STARTUP",
                        prospect_type="PRODUCT_COMPANY", compliance_flag="APPROVED"),
            Opportunity(opportunity_id="O2", company_domain="known.com", company_tier="STARTUP",
                        prospect_type="EDA_VENDOR", compliance_flag="REVIEW_REQUIRED"),
        ])
        s.commit()

        changes = backfill(s, apply=True)

        assert {d for d, _ in changes} == {"gap.com"}
        gap = s.get(Company, "gap.com")
        assert (gap.company_tier, gap.prospect_type, gap.compliance_flag) == (
            "STARTUP", "PRODUCT_COMPANY", "APPROVED")
        known = s.get(Company, "known.com")
        assert known.company_tier == "INCUMBENT"  # known value left untouched
