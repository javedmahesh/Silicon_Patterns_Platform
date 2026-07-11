"""Endpoint tests for the FastAPI backend (in-process TestClient, temp SQLite)."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import (
    Base, Company, DecisionMaker, DemandSignal, Job, LeadScore, Opportunity, ResolutionReviewQueue,
)


def _seed(s):
    s.add_all([
        Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme Silicon",
                name_key="acme silicon", company_tier="STARTUP", prospect_type="PRODUCT_COMPANY",
                compliance_flag="APPROVED", country="United States", validation_status="VALID"),
        Company(company_domain="beta.io", canonical_company_id="BETA", company_name="Beta Systems",
                name_key="beta", company_tier="INCUMBENT", prospect_type="SERVICE_PROVIDER",
                compliance_flag="APPROVED", validation_status="VALID"),
        Company(company_domain="stub.com", canonical_company_id="STUB", company_name="Stub Co",
                name_key="stub", validation_status="STUB", is_stub=True),
    ])
    s.flush()
    s.add_all([
        LeadScore(company_domain="acme.com", lead_score=80.0, grade="A", priority_rank=1,
                  opportunity_subscore=90, demand_subscore=90, readiness_subscore=70, dm_subscore=50,
                  model_version="test"),
        LeadScore(company_domain="beta.io", lead_score=10.0, grade="C", priority_rank=2,
                  model_version="test"),
        Opportunity(opportunity_id="OPP-1", company_domain="acme.com", company_name="Acme Silicon",
                    opportunity_type="FUNDING", effective_opportunity_score=80, published_date="2026-05-18"),
        Job(job_id="JOB-1", company_domain="acme.com", job_title="ASIC Verification Engineer",
            seniority="senior", engineering_relevance_score=90),
        DemandSignal(company_domain="acme.com", demand_score=90.0, total_engineering_jobs=40,
                     primary_focus="Verification", technologies_detected="UVM, SystemVerilog"),
        DecisionMaker(linkedin_url="https://lnkd.in/a", company_domain="acme.com", first_name="Ada",
                      current_title="VP Engineering", seniority="senior", match_score=88.0),
        DecisionMaker(linkedin_url="https://lnkd.in/u", company_domain=None, first_name="Unresolved",
                      resolved_company_name="Mystery Co", match_score=40.0),
        ResolutionReviewQueue(raw_name="Stub Co", suggested_domain="stub.com", source_engine="career_jobs",
                              match_type="NEW_STUB", status="pending"),
    ])
    s.commit()


@pytest.fixture()
def client(tmp_path):
    db_file = tmp_path / "api_test.db"
    settings = Settings(database_url=f"sqlite:///{db_file.as_posix()}", log_json=False)
    app = create_app(settings)
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


# ------------------------------------------------------------------ health
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["database"] == "ok"


def test_openapi_and_docs(client):
    assert client.get("/openapi.json").status_code == 200
    assert "/companies/{domain}" in client.get("/openapi.json").json()["paths"]
    assert client.get("/docs").status_code == 200
    assert client.get("/", follow_redirects=False).status_code in (307, 308)


# --------------------------------------------------------------- companies
def test_list_companies_and_pagination(client):
    body = client.get("/companies").json()
    assert body["total"] == 3 and len(body["items"]) == 3
    acme = next(i for i in body["items"] if i["company_domain"] == "acme.com")
    assert acme["lead_score"] == 80.0 and acme["grade"] == "A"

    paged = client.get("/companies", params={"page": 1, "page_size": 2}).json()
    assert paged["page_size"] == 2 and paged["pages"] == 2 and len(paged["items"]) == 2


def test_company_search_and_filters(client):
    assert client.get("/companies", params={"q": "acme"}).json()["total"] == 1
    assert client.get("/companies", params={"domain": "beta"}).json()["total"] == 1
    assert client.get("/companies", params={"grade": "A"}).json()["total"] == 1
    assert client.get("/companies", params={"tier": "STARTUP"}).json()["total"] == 1
    top = client.get("/companies", params={"sort": "lead_score", "order": "desc"}).json()
    assert top["items"][0]["company_domain"] == "acme.com"


def test_company_profile_unified(client):
    r = client.get("/companies/acme.com")
    assert r.status_code == 200
    p = r.json()
    assert p["company"]["company_name"] == "Acme Silicon"
    assert p["lead_score"]["grade"] == "A"
    assert len(p["opportunities"]) == 1 and len(p["jobs"]) == 1
    assert p["demand_signal"]["demand_score"] == 90.0
    assert len(p["decision_makers"]) == 1
    assert p["counts"]["jobs"] == 1
    assert p["review_status"]["is_stub"] is False


def test_company_profile_review_status_for_stub(client):
    p = client.get("/companies/stub.com").json()
    assert p["review_status"]["is_stub"] is True
    assert p["review_status"]["pending_review_items"] == 1
    assert "NEW_STUB" in p["review_status"]["match_types"]


def test_company_not_found(client):
    assert client.get("/companies/nope.com").status_code == 404


# ------------------------------------------------------------------- leads
def test_leads_ranked_and_filtered(client):
    body = client.get("/leads").json()
    assert body["items"][0]["company_domain"] == "acme.com"      # ranked by priority
    assert client.get("/leads", params={"grade": "A"}).json()["total"] == 1
    assert client.get("/leads", params={"tier": "INCUMBENT"}).json()["items"][0]["company_domain"] == "beta.io"
    assert client.get("/leads", params={"prospect_type": "PRODUCT_COMPANY"}).json()["total"] == 1


# ----------------------------------------------------------- opportunities
def test_opportunities_filters(client):
    assert client.get("/opportunities").json()["total"] == 1
    assert client.get("/opportunities", params={"opportunity_type": "FUNDING"}).json()["total"] == 1
    assert client.get("/opportunities", params={"company_domain": "acme.com"}).json()["total"] == 1
    assert client.get("/opportunities", params={"date_from": "2026-01-01", "date_to": "2026-12-31"}).json()["total"] == 1
    assert client.get("/opportunities", params={"date_from": "2027-01-01"}).json()["total"] == 0


# --------------------------------------------------------- demand signals
def test_demand_signal_filters(client):
    assert client.get("/demand-signals").json()["total"] == 1
    assert client.get("/demand-signals", params={"min_demand_score": 50}).json()["total"] == 1
    assert client.get("/demand-signals", params={"min_demand_score": 95}).json()["total"] == 0
    assert client.get("/demand-signals", params={"technology_focus": "UVM"}).json()["total"] == 1


# --------------------------------------------------------- decision makers
def test_decision_maker_filters(client):
    assert client.get("/decision-makers").json()["total"] == 2
    assert client.get("/decision-makers", params={"company_domain": "acme.com"}).json()["total"] == 1
    assert client.get("/decision-makers", params={"seniority": "senior"}).json()["total"] == 1


# -------------------------------------------------------------- analytics
def test_analytics_summary(client):
    a = client.get("/analytics/summary").json()
    assert a["total_companies"] == 3
    assert a["total_opportunities"] == 1 and a["total_jobs"] == 1
    assert a["total_decision_makers"] == 2 and a["total_leads"] == 2
    assert a["grade_distribution"] == {"A": 1, "C": 1}
    assert a["top_companies"][0]["company_domain"] == "acme.com"
