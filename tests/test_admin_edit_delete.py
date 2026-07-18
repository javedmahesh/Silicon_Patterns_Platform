"""Admin edit + delete for the core business records (companies, decision makers,
opportunities, leadership signals). Admin-only (RBAC), 404s, cascade, enum validation."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from integration.normalizer import name_key
from master_db.models import (Base, Company, DecisionMaker, LeadershipSignal, Opportunity)

ADMIN = {"X-Dev-Role": "admin"}
MGR = {"X-Dev-Role": "manager"}
MEMBER = {"X-Dev-Role": "member"}


@pytest.fixture()
def app_db(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'ed.db').as_posix()}", log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(Company(company_domain="nvidia.com", canonical_company_id="NVIDIA", company_name="NVIDIA",
                          name_key="nvidia", validation_status="VALID", company_tier="INCUMBENT",
                          industry_category="Semiconductors"))
            s.add(Opportunity(opportunity_id="O1", company_domain="nvidia.com", opportunity_type="FUNDING",
                              article_title="NVIDIA raises money"))
            s.add(LeadershipSignal(signal_id="S1", company_domain="nvidia.com", company_name="NVIDIA",
                                   movement_type="promotion", seniority_band="vp", source="linkedin_history",
                                   confidence="high", person_name="Jane Doe", to_title="VP Eng"))
            s.add(DecisionMaker(linkedin_url="https://linkedin.com/in/jensen", company_domain="nvidia.com",
                                first_name="Jensen", last_name="Huang", full_name="Jensen Huang",
                                current_title="CEO"))
            s.commit()
            dm_id = s.query(DecisionMaker).one().id
        yield app, c, dm_id


# --------------------------------------------------------------- company
def test_company_edit(app_db):
    app, c, _ = app_db
    r = c.patch("/companies/nvidia.com", headers=ADMIN,
                json={"company_name": "Nvidia Corp", "country": "US", "company_tier": "SCALEUP"})
    assert r.status_code == 200 and r.json()["company_name"] == "Nvidia Corp"
    with app.state.db.sessionmaker() as s:
        co = s.get(Company, "nvidia.com")
        assert co.country == "US" and co.company_tier == "SCALEUP"
        assert co.name_key == name_key("Nvidia Corp")   # derived key recomputed on rename


def test_company_edit_bad_enum_422(app_db):
    _, c, _ = app_db
    assert c.patch("/companies/nvidia.com", headers=ADMIN, json={"company_tier": "BOGUS"}).status_code == 422


def test_company_edit_requires_admin(app_db):
    _, c, _ = app_db
    assert c.patch("/companies/nvidia.com", headers=MEMBER, json={"city": "x"}).status_code == 403
    assert c.patch("/companies/nvidia.com", headers=MGR, json={"city": "x"}).status_code == 403


def test_company_delete_cascades(app_db):
    app, c, dm_id = app_db
    assert c.delete("/companies/nvidia.com", headers=ADMIN).status_code == 204
    with app.state.db.sessionmaker() as s:
        assert s.get(Company, "nvidia.com") is None
        assert s.get(Opportunity, "O1") is None            # ON DELETE CASCADE
        assert s.get(LeadershipSignal, "S1") is None        # ON DELETE CASCADE
        assert s.get(DecisionMaker, dm_id).company_domain is None   # ON DELETE SET NULL


def test_company_delete_rbac_and_404(app_db):
    _, c, _ = app_db
    assert c.delete("/companies/nvidia.com", headers=MGR).status_code == 403
    assert c.delete("/companies/does-not-exist.com", headers=ADMIN).status_code == 404


# --------------------------------------------------------- decision maker
def test_decision_maker_edit(app_db):
    app, c, dm_id = app_db
    r = c.patch(f"/decision-makers/{dm_id}", headers=ADMIN,
                json={"current_title": "Founder & CEO", "city": "Santa Clara"})
    assert r.status_code == 200 and r.json()["current_title"] == "Founder & CEO"
    with app.state.db.sessionmaker() as s:
        assert s.get(DecisionMaker, dm_id).city == "Santa Clara"


def test_decision_maker_delete_and_rbac(app_db):
    app, c, dm_id = app_db
    assert c.patch(f"/decision-makers/{dm_id}", headers=MEMBER, json={"city": "x"}).status_code == 403
    assert c.delete(f"/decision-makers/{dm_id}", headers=MGR).status_code == 403
    assert c.delete(f"/decision-makers/{dm_id}", headers=ADMIN).status_code == 204
    assert c.delete(f"/decision-makers/{dm_id}", headers=ADMIN).status_code == 404
    with app.state.db.sessionmaker() as s:
        assert s.get(DecisionMaker, dm_id) is None


# ------------------------------------------------------------ opportunity
def test_opportunity_edit_rederives_signal_category(app_db):
    app, c, _ = app_db
    # change to a leadership type -> the ORM listener flips signal_category to LEADERSHIP
    r = c.patch("/opportunities/O1", headers=ADMIN,
                json={"article_title": "New CEO", "opportunity_type": "EXECUTIVE_HIRE"})
    assert r.status_code == 200 and r.json()["article_title"] == "New CEO"
    with app.state.db.sessionmaker() as s:
        assert s.get(Opportunity, "O1").signal_category == "LEADERSHIP"
    assert c.patch("/opportunities/O1", headers=MGR, json={"summary": "x"}).status_code == 403


# ------------------------------------------------------ leadership signal
def test_leadership_signal_edit(app_db):
    app, c, _ = app_db
    r = c.patch("/leadership-signals/S1", headers=ADMIN,
                json={"person_name": "Jane A. Doe", "to_title": "SVP Engineering"})
    assert r.status_code == 200 and r.json()["person_name"] == "Jane A. Doe"
    # bad enum rejected
    assert c.patch("/leadership-signals/S1", headers=ADMIN,
                   json={"movement_type": "nonsense"}).status_code == 422
    assert c.patch("/leadership-signals/S1", headers=MEMBER, json={"to_title": "x"}).status_code == 403
