"""HTTP-surface tests for the Run Details drill-down endpoint
(GET /scheduler/runs/{run_id}/engines/{engine}/records) — routing, auth, 404,
run isolation, and pagination through the real FastAPI app."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company, PipelineExecution, RunEngineRecord


def _seed(s):
    # Two runs; two companies discovered by "industry" in run-A, one in run-B.
    s.add_all([
        Company(company_domain="groq.com", canonical_company_id="GROQ", company_name="Groq",
                name_key="groq", company_tier="SCALEUP", prospect_type="PRODUCT_COMPANY",
                compliance_flag="APPROVED", country="United States", validation_status="VALID",
                industry_category="AI Accelerators"),
        Company(company_domain="tenstorrent.com", canonical_company_id="TT", company_name="Tenstorrent",
                name_key="tenstorrent", company_tier="SCALEUP", prospect_type="PRODUCT_COMPANY",
                compliance_flag="APPROVED", country="Canada", validation_status="VALID"),
    ])
    for rid in ("run-A", "run-B"):
        s.add(PipelineExecution(run_id=rid, trigger="manual", status="success"))
    s.add_all([
        RunEngineRecord(run_id="run-A", engine="industry", entity_table="companies",
                        entity_id="groq.com", operation="created", detail={}),
        RunEngineRecord(run_id="run-A", engine="industry", entity_table="companies",
                        entity_id="tenstorrent.com", operation="created", detail={}),
        RunEngineRecord(run_id="run-B", engine="industry", entity_table="companies",
                        entity_id="groq.com", operation="updated", detail={}),
    ])
    s.commit()


@pytest.fixture()
def client(tmp_path):
    settings = Settings(database_url=f"sqlite:///{(tmp_path / 'rr.db').as_posix()}", log_json=False)
    app = create_app(settings)
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def test_drilldown_returns_only_this_runs_records(client):
    a = client.get("/scheduler/runs/run-A/engines/industry/records").json()
    assert a["available"] is True and a["total"] == 2
    assert a["breakdown"] == {"created": 2}
    ids = {i["entity_id"] for i in a["items"]}
    assert ids == {"groq.com", "tenstorrent.com"}
    groq = next(i for i in a["items"] if i["entity_id"] == "groq.com")
    assert groq["title"] == "Groq" and groq["link"] == "/companies/groq.com"


def test_run_isolation_across_runs(client):
    b = client.get("/scheduler/runs/run-B/engines/industry/records").json()
    assert b["total"] == 1 and b["breakdown"] == {"updated": 1}
    assert {i["entity_id"] for i in b["items"]} == {"groq.com"}   # never sees run-A's tenstorrent


def test_unknown_run_is_404(client):
    assert client.get("/scheduler/runs/run-NOPE/engines/industry/records").status_code == 404


def test_engine_with_no_records_is_empty_not_unavailable(client):
    # run-A exists and has provenance, but nothing was recorded for "career".
    r = client.get("/scheduler/runs/run-A/engines/career/records").json()
    assert r["available"] is True and r["total"] == 0 and r["items"] == []


def test_pagination(client):
    r = client.get("/scheduler/runs/run-A/engines/industry/records",
                   params={"page": 1, "page_size": 1}).json()
    assert r["total"] == 2 and len(r["items"]) == 1        # full total, one page of items
