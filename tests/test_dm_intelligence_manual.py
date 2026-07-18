"""Manual Decision Maker Intelligence jobs + Leadership as a first-class signal category.

Covers the refactor that took decision_maker_intelligence OUT of the automatic
pipeline and made it a manual, per-company job, plus the LEADERSHIP/NEWS signal-
category split.
"""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import (
    Base,
    Company,
    DmIntelligenceJob,
    DmIntelligenceJobItem,
    Opportunity,
    PipelineRun,
)


@pytest.fixture()
def app_db(tmp_path):
    db = tmp_path / "dm.db"
    app = create_app(Settings(database_url=f"sqlite:///{db.as_posix()}", log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add_all([
                Company(company_domain="nvidia.com", canonical_company_id="NV", company_name="NVIDIA",
                        name_key="nvidia", validation_status="VALID"),
                Company(company_domain="amd.com", canonical_company_id="AMD", company_name="AMD",
                        name_key="amd", validation_status="VALID"),
            ])
            s.flush()
            s.add_all([
                Opportunity(opportunity_id="L1", company_domain="nvidia.com", opportunity_type="EXECUTIVE_HIRE"),
                Opportunity(opportunity_id="L2", company_domain="nvidia.com", opportunity_type="LEADERSHIP_CHANGE"),
                Opportunity(opportunity_id="N1", company_domain="nvidia.com", opportunity_type="FUNDING"),
                Opportunity(opportunity_id="N2", company_domain="amd.com", opportunity_type="PRODUCT_LAUNCH"),
            ])
            s.commit()
        yield app, c


# ---------------------------------------------------------- pipeline removal
def test_dm_intelligence_is_manual_only():
    """decision_maker_intelligence is out of the AUTOMATIC pipeline but still a
    registered stage that can be run on demand."""
    from orchestrator.stages import PIPELINE_ORDER, STAGES

    assert "decision_maker_intelligence" not in PIPELINE_ORDER
    assert "decision_maker_intelligence" in STAGES


# ---------------------------------------------------- signal category split
def test_signal_category_listener_sets_category(app_db):
    app, _ = app_db
    with app.state.db.sessionmaker() as s:
        assert s.get(Opportunity, "L1").signal_category == "LEADERSHIP"
        assert s.get(Opportunity, "N1").signal_category == "NEWS"


def test_opportunities_filtered_by_signal_category(app_db):
    _, c = app_db
    lead = c.get("/opportunities", params={"signal_category": "LEADERSHIP"}).json()
    assert lead["total"] == 2
    assert {o["opportunity_type"] for o in lead["items"]} == {"EXECUTIVE_HIRE", "LEADERSHIP_CHANGE"}
    assert all(o["signal_category"] == "LEADERSHIP" for o in lead["items"])

    news = c.get("/opportunities", params={"signal_category": "NEWS"}).json()
    assert news["total"] == 2  # leadership events no longer appear under NEWS
    assert {o["opportunity_type"] for o in news["items"]} == {"FUNDING", "PRODUCT_LAUNCH"}


def test_analytics_signal_category_counts(app_db):
    _, c = app_db
    d = c.get("/analytics/summary").json()
    assert d["signal_category_counts"] == {"LEADERSHIP": 2, "NEWS": 2}


# ----------------------------------------------------- manual job lifecycle
def test_create_job_validation(app_db):
    app, _ = app_db
    from backend import dm_intelligence_jobs as dm

    with app.state.db.sessionmaker() as s:
        with pytest.raises(dm.JobValidationError):
            dm.create_job(s, items=[], requested_by_id=1, requested_by_email="a@b.c")
        with pytest.raises(dm.JobValidationError):
            dm.create_job(s, items=[_Item("ghost.com", 10)], requested_by_id=1, requested_by_email="a@b.c")


def test_create_job_dedups_and_clamps(app_db):
    app, _ = app_db
    from backend import dm_intelligence_jobs as dm

    with app.state.db.sessionmaker() as s:
        job = dm.create_job(
            s,
            items=[_Item("nvidia.com", 50), _Item("nvidia.com", 10), _Item("amd.com", 99999)],
            requested_by_id=7, requested_by_email="mgr@sp.com",
        )
        assert job.total_companies == 2  # nvidia deduped (last count wins)
        counts = {i.company_domain: i.requested_count for i in job.items}
        assert counts["nvidia.com"] == 10
        assert counts["amd.com"] == dm.MAX_REQUESTED_PER_COMPANY  # clamped
        assert job.total_requested == 10 + dm.MAX_REQUESTED_PER_COMPANY


def test_run_job_progress_and_history(app_db, monkeypatch):
    """_run_job drives per-company progress, records found, and a pipeline_runs row —
    with the real Apify call replaced by a fake so no network/cost is incurred."""
    app, _ = app_db
    from backend import dm_intelligence_jobs as dm
    from integration.ingestors import apify_source

    monkeypatch.setenv("APIFY_API_TOKEN", "test-token")

    def fake_company(session, *, company, requested_count, actor_id=None, api_token=None, pipeline_run_id=None):
        return apify_source.CompanyDmResult(
            company_domain=company.company_domain, records_returned=requested_count,
            inserted=requested_count, updated=0, apify_run_id="apify-run-1", status="success",
        )

    monkeypatch.setattr(apify_source, "import_decision_makers_for_company", fake_company)
    monkeypatch.setattr(apify_source, "_capture_decision_maker_snapshots", lambda s: None)

    with app.state.db.sessionmaker() as s:
        job = dm.create_job(s, items=[_Item("nvidia.com", 5), _Item("amd.com", 3)],
                            requested_by_id=1, requested_by_email="mgr@sp.com")
        job_id = job.id
        dm._run_job(s, app.state.settings, job_id)

        done = s.get(DmIntelligenceJob, job_id)
        assert done.status == "completed"
        assert done.total_found == 8
        items = {i.company_domain: i for i in done.items}
        assert items["nvidia.com"].status == "completed" and items["nvidia.com"].records_found == 5
        assert items["amd.com"].records_found == 3
        # manual execution recorded in the pipeline run history
        run = s.get(PipelineRun, done.pipeline_run_id)
        assert run is not None and run.component == "decision_maker_intelligence"
        assert run.trigger == "manual" and run.status == "success"


def test_run_job_without_credentials_fails_clearly(app_db, monkeypatch):
    app, _ = app_db
    from backend import dm_intelligence_jobs as dm

    monkeypatch.setenv("APIFY_API_TOKEN", "")
    with app.state.db.sessionmaker() as s:
        job = dm.create_job(s, items=[_Item("nvidia.com", 5)], requested_by_id=1, requested_by_email="m@sp.com")
        dm._run_job(s, app.state.settings, job.id)
        done = s.get(DmIntelligenceJob, job.id)
        assert done.status == "failed"
        assert "Apify" in done.error
        assert s.query(DmIntelligenceJobItem).filter_by(job_id=job.id).one().status == "failed"


# ---------------------------------------------------------------- RBAC
def test_run_endpoint_requires_manager(app_db, monkeypatch):
    app, c = app_db
    from backend import dm_intelligence_jobs as dm

    # Don't actually spawn the background worker in this API test.
    monkeypatch.setattr(dm, "start_job_async", lambda app, job_id: None)

    body = {"items": [{"company_domain": "nvidia.com", "requested_count": 5}]}
    # members can't run intelligence jobs
    assert c.post("/decision-makers/intelligence-runs", json=body,
                  headers={"X-Dev-Role": "member"}).status_code == 403
    # managers can
    r = c.post("/decision-makers/intelligence-runs", json=body, headers={"X-Dev-Role": "manager"})
    assert r.status_code == 201
    assert r.json()["total_companies"] == 1 and r.json()["status"] == "queued"


class _Item:
    """Minimal stand-in for DmIntelligenceRunItemIn (create_job reads attributes)."""

    def __init__(self, company_domain: str, requested_count: int) -> None:
        self.company_domain = company_domain
        self.requested_count = requested_count
