"""Admin-only delete of opportunities ('blogs') + leadership signals."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import (
    Base,
    Company,
    LeadershipSignal,
    Opportunity,
    OpportunityReview,
)

ADMIN = {"X-Dev-Role": "admin"}
MGR = {"X-Dev-Role": "manager"}
MEMBER = {"X-Dev-Role": "member"}


@pytest.fixture()
def app_db(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'del.db').as_posix()}", log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(Company(company_domain="nvidia.com", canonical_company_id="NV", company_name="NVIDIA",
                          name_key="nvidia", validation_status="VALID"))
            s.flush()
            s.add(Opportunity(opportunity_id="O1", company_domain="nvidia.com", opportunity_type="FUNDING"))
            s.add(OpportunityReview(opportunity_id="O1", action="note", actor_email="a@b.c", detail="x"))
            s.add(LeadershipSignal(signal_id="S1", company_domain="nvidia.com", company_name="NVIDIA",
                                   movement_type="promotion", seniority_band="vp", source="linkedin_history",
                                   confidence="high", person_name="Jane Doe", to_title="VP Engineering"))
            s.commit()
        yield app, c


def test_delete_opportunity_admin_cascades(app_db):
    app, c = app_db
    assert c.delete("/opportunities/O1", headers=ADMIN).status_code == 204
    with app.state.db.sessionmaker() as s:
        assert s.get(Opportunity, "O1") is None
        # review history was cascaded away with the opportunity
        assert s.query(OpportunityReview).filter_by(opportunity_id="O1").count() == 0


def test_delete_opportunity_requires_admin(app_db):
    _, c = app_db
    assert c.delete("/opportunities/O1", headers=MEMBER).status_code == 403
    assert c.delete("/opportunities/O1", headers=MGR).status_code == 403   # manager is NOT admin
    assert c.delete("/opportunities/O1", headers=ADMIN).status_code == 204


def test_delete_opportunity_404(app_db):
    _, c = app_db
    assert c.delete("/opportunities/does-not-exist", headers=ADMIN).status_code == 404


def test_delete_leadership_signal_admin(app_db):
    app, c = app_db
    assert c.delete("/leadership-signals/S1", headers=ADMIN).status_code == 204
    with app.state.db.sessionmaker() as s:
        assert s.get(LeadershipSignal, "S1") is None


def test_delete_leadership_signal_requires_admin(app_db):
    _, c = app_db
    assert c.delete("/leadership-signals/S1", headers=MEMBER).status_code == 403
    assert c.delete("/leadership-signals/S1", headers=MGR).status_code == 403
    assert c.delete("/leadership-signals/S1", headers=ADMIN).status_code == 204
