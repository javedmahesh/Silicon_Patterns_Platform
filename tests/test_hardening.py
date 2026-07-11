"""P5.5: API-key auth gate + bulk ingestion behaviour."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.config import Settings
from backend.main import create_app
from integration.ingestors.career import JobsIngestor
from master_db.local import make_session_factory
from master_db.models import Base, Company, Job


# ----------------------------------------------------------------- auth
@pytest.fixture()
def secured_client(tmp_path):
    settings = Settings(database_url=f"sqlite:///{(tmp_path / 'sec.db').as_posix()}",
                        log_json=False, api_key="topsecret")
    app = create_app(settings)
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(Company(company_domain="acme.com", canonical_company_id="ACME",
                          company_name="Acme", name_key="acme", validation_status="VALID"))
            s.commit()
        yield c


def test_health_is_open(secured_client):
    assert secured_client.get("/health").status_code == 200


def test_data_endpoints_require_key(secured_client):
    assert secured_client.get("/companies").status_code == 401
    assert secured_client.get("/analytics/summary").status_code == 401
    ok = secured_client.get("/companies", headers={"X-API-Key": "topsecret"})
    assert ok.status_code == 200 and ok.json()["total"] == 1
    assert secured_client.get("/companies", headers={"X-API-Key": "wrong"}).status_code == 401


# ----------------------------------------------------------------- bulk
JOB_ROWS = [
    {"company_name": "Tenstorrent", "company_domain": "tenstorrent.com",
     "job_title": "ASIC Engineer", "job_url": "https://tenstorrent.com/j/1", "seniority": "senior"},
    {"company_name": "Tenstorrent", "company_domain": "tenstorrent.com",
     "job_title": "RTL Engineer", "job_url": "https://tenstorrent.com/j/2"},
    {"company_name": "Ambiq", "company_domain": "ambiq.com",
     "job_title": "DFT Engineer", "job_url": "https://ambiq.com/j/9"},
]


def test_jobs_bulk_ingest_and_idempotency():
    Session = make_session_factory(":memory:")
    with Session() as s:
        first = JobsIngestor(s, mode="pipeline").ingest_rows(JOB_ROWS, "test")
        assert first.rows_upserted == 3 and first.rows_rejected == 0
        assert s.scalar(select(func.count()).select_from(Job)) == 3
        # stub companies were created for the two domains
        assert s.get(Company, "tenstorrent.com") is not None

        second = JobsIngestor(s, mode="pipeline").ingest_rows(JOB_ROWS, "test")
        assert second.rows_upserted == 3 and second.rows_duplicate == 3   # all updates, no new rows
        assert s.scalar(select(func.count()).select_from(Job)) == 3
