"""Engagement / sales-pitch recommendation engine (P-task 9): the rules + the API."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from engagement.recommend import rebuild, recommend_for_company
from master_db.models import Base, Company, DemandSignal, LeadershipSignal, Opportunity


# ----------------------------------------------------------------- the rules
def test_verification_need_from_hiring_mix():
    company = Company(company_domain="acme.com", prospect_type="PRODUCT_COMPANY",
                      company_tier="SCALEUP", technology_focus="AI Accelerator")
    demand = DemandSignal(company_domain="acme.com", verification_jobs=12, total_engineering_jobs=12,
                          primary_focus="Verification", hiring_trend="GROWING")
    rec = recommend_for_company(company=company, opportunities=[], demand=demand,
                                leadership=[], dm_count=3, dm_senior_count=1)
    assert rec["offering"] == "Verification engineering services"
    assert "verification" in rec["business_need"].lower()
    assert rec["confidence_label"] in ("medium", "high") and rec["confidence"] > 0
    assert rec["pitch"].startswith("Silicon Patterns")
    assert any("Hiring activity" in r for r in rec["rationale"])
    assert rec["signals_used"] >= 2  # demand + decision makers


def test_physical_design_need():
    company = Company(company_domain="pd.com")
    demand = DemandSignal(company_domain="pd.com", physical_design_jobs=8, sta_jobs=2,
                          total_engineering_jobs=10, primary_focus="Physical Design")
    rec = recommend_for_company(company=company, opportunities=[], demand=demand, leadership=[], dm_count=0)
    assert rec["offering"] == "Physical design & timing-closure services"


def test_funding_event_frames_the_need():
    company = Company(company_domain="b.com")
    opp = Opportunity(opportunity_id="o1", company_domain="b.com", opportunity_type="Funding", funding_stage="Series B")
    demand = DemandSignal(company_domain="b.com", rtl_jobs=5, total_engineering_jobs=5, primary_focus="RTL")
    rec = recommend_for_company(company=company, opportunities=[opp], demand=demand, leadership=[], dm_count=0)
    assert rec["offering"] == "RTL / front-end design services"
    assert "Series B" in rec["business_need"]
    assert any("Funding" in r for r in rec["rationale"])


def test_staffing_fallback_when_growth_but_no_discipline():
    company = Company(company_domain="c.com")
    opp = Opportunity(opportunity_id="o2", company_domain="c.com", opportunity_type="Funding", funding_stage="Seed")
    rec = recommend_for_company(company=company, opportunities=[opp], demand=None, leadership=[], dm_count=0)
    assert rec["offering"] == "Engineering staff augmentation"
    assert "Seed" in rec["business_need"]


def test_leadership_hire_drives_recommendation():
    company = Company(company_domain="d.com")
    sig = LeadershipSignal(signal_id="s1", company_domain="d.com", movement_type="new_executive_hire",
                           seniority_band="vp", role_function="engineering", to_title="VP Engineering")
    rec = recommend_for_company(company=company, opportunities=[], demand=None, leadership=[sig], dm_count=0)
    assert rec is not None and rec["offering"] == "Engineering staff augmentation"
    assert "engineering leadership" in rec["business_need"]


def test_no_signals_yields_no_pitch():
    assert recommend_for_company(company=Company(company_domain="empty.com"),
                                 opportunities=[], demand=None, leadership=[], dm_count=0) is None


# --------------------------------------------------------------------- API
@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'eng.db').as_posix()}", log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme Silicon",
                          name_key="acme silicon", company_tier="SCALEUP", prospect_type="PRODUCT_COMPANY",
                          compliance_flag="APPROVED", validation_status="VALID", technology_focus="AI Accelerator"))
            s.add(Company(company_domain="empty.com", canonical_company_id="E", company_name="Empty",
                          name_key="empty", validation_status="STUB", is_stub=True))
            s.flush()
            s.add(DemandSignal(company_domain="acme.com", verification_jobs=10, total_engineering_jobs=10,
                               primary_focus="Verification", hiring_trend="GROWING"))
            s.commit()
            rebuild(s)
        yield c


def test_company_bundle_includes_engagement(client):
    eng = client.get("/companies/acme.com").json()["engagement"]
    assert eng is not None
    assert eng["offering"] == "Verification engineering services"
    assert eng["pitch"].startswith("Silicon Patterns")
    assert eng["confidence"] > 0 and eng["confidence_label"] in ("low", "medium", "high")
    assert isinstance(eng["rationale"], list) and eng["rationale"]


def test_company_with_no_signals_has_no_engagement(client):
    assert client.get("/companies/empty.com").json()["engagement"] is None
