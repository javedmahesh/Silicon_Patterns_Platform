"""Tests for the pipeline + coverage endpoints and the rate-limit middleware."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import (
    Base,
    Company,
    DecisionMaker,
    DemandSignal,
    LeadScore,
    Opportunity,
    PipelineRun,
)


@pytest.fixture()
def client(tmp_path):
    db = tmp_path / "cov.db"
    app = create_app(Settings(database_url=f"sqlite:///{db.as_posix()}", log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add_all([
                Company(company_domain="a.com", canonical_company_id="A", company_name="A",
                        name_key="a", validation_status="VALID"),
                Company(company_domain="b.com", canonical_company_id="B", company_name="B",
                        name_key="b", validation_status="VALID"),
            ])
            s.flush()
            s.add_all([
                Opportunity(opportunity_id="O1", company_domain="a.com"),
                DemandSignal(company_domain="a.com", demand_score=50.0),
                DecisionMaker(linkedin_url="https://l/1", company_domain="a.com", match_score=10.0),
                LeadScore(company_domain="a.com", lead_score=50.0, grade="A", priority_rank=1,
                          model_version="t"),
            ])
            s.commit()
        yield c


def test_analytics_coverage(client):
    d = client.get("/analytics/coverage").json()
    assert d["total_companies"] == 2
    assert d["with_opportunities"] == 1
    assert d["with_demand"] == 1
    assert d["with_decision_makers"] == 1
    assert d["with_lead_score"] == 1
    assert d["with_all_three"] == 1  # a.com has opp + demand + dm
    assert d["signal_distribution"]["3"] == 1
    assert d["signal_distribution"]["0"] == 1  # b.com has none


def test_decision_maker_companies(client):
    d = client.get("/decision-makers/companies").json()
    assert d["unresolved"] == 0
    assert any(c["company_domain"] == "a.com" and c["total"] == 1 for c in d["companies"])
    assert all(c["company_name"] for c in d["companies"])  # name filled (falls back to domain)


def test_pipeline_endpoints(client):
    assert client.get("/pipeline/runs").json() == []
    comps = [h["component"] for h in client.get("/pipeline/health").json()]
    # decision_maker_intelligence is intentionally absent — it is manual-only (paid
    # Apify actor), so it is not one of the automatic pipeline components whose
    # freshness the health strip reports.
    assert comps == ["industry", "blog", "news", "annual_list", "company_news", "career",
                     "market_discovery", "market_intelligence", "scoring", "leadership",
                     "engagement"]
    assert all(h["last_status"] == "never" for h in client.get("/pipeline/health").json())


def test_pipeline_status(tmp_path):
    from datetime import datetime, timedelta, timezone

    db = tmp_path / "status.db"
    app = create_app(Settings(database_url=f"sqlite:///{db.as_posix()}", log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)

        s0 = c.get("/pipeline/status").json()
        assert s0["last_successful_refresh"] is None
        assert s0["latest_run_status"] == "none"
        assert s0["in_progress"] is False

        with app.state.db.sessionmaker() as s:
            s.add(PipelineRun(pipeline_id="run-1", component="scoring", status="success",
                              finished_at=datetime(2026, 6, 14, 9, 0, tzinfo=timezone.utc)))
            s.commit()

        s1 = c.get("/pipeline/status").json()
        assert s1["last_successful_refresh"] is not None
        assert s1["latest_run_status"] == "success"
        assert s1["latest_run_component"] == "scoring"

        # a long-dead "running" row (crashed run) must NOT count as in-progress
        with app.state.db.sessionmaker() as s:
            s.add(PipelineRun(pipeline_id="run-2", component="industry", status="running",
                              started_at=datetime.now(timezone.utc) - timedelta(hours=3)))
            s.commit()
        assert c.get("/pipeline/status").json()["in_progress"] is False

        # a fresh "running" row IS in-progress
        with app.state.db.sessionmaker() as s:
            s.add(PipelineRun(pipeline_id="run-3", component="career", status="running",
                              started_at=datetime.now(timezone.utc)))
            s.commit()
        assert c.get("/pipeline/status").json()["in_progress"] is True


def test_analytics_cache_etag_and_revalidation(tmp_path):
    """Analytics responses carry an ETag; an unchanged request 304s, and a completed
    refresh advances the version so the ETag changes and clients revalidate to 200."""
    from datetime import datetime, timezone

    db = tmp_path / "cache.db"
    app = create_app(Settings(database_url=f"sqlite:///{db.as_posix()}", log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(Company(company_domain="a.com", canonical_company_id="A", company_name="A",
                          name_key="a", validation_status="VALID"))
            s.commit()

        r1 = c.get("/analytics/summary")
        assert r1.status_code == 200
        etag = r1.headers.get("etag")
        assert etag
        assert r1.headers.get("cache-control", "").startswith("private, max-age=")

        # Same ETag -> 304 Not Modified, no body.
        r2 = c.get("/analytics/summary", headers={"If-None-Match": etag})
        assert r2.status_code == 304
        assert r2.headers.get("etag") == etag
        assert r2.content == b""

        # /coverage is cached independently with its own ETag.
        cov = c.get("/analytics/coverage")
        assert cov.headers.get("etag") and cov.headers["etag"] != etag

        # A completed refresh advances last_successful_refresh -> new ETag -> 200.
        with app.state.db.sessionmaker() as s:
            s.add(PipelineRun(pipeline_id="r1", component="scoring", status="success",
                              finished_at=datetime(2026, 6, 15, 9, 0, tzinfo=timezone.utc)))
            s.commit()
        r3 = c.get("/analytics/summary", headers={"If-None-Match": etag})
        assert r3.status_code == 200
        assert r3.headers.get("etag") != etag


def test_analytics_cache_invalidates_on_rescore(tmp_path):
    """A direct re-score (advancing lead_scores.scored_at, no new pipeline run) must
    still advance the analytics cache version -> new ETag -> clients revalidate to 200."""
    from datetime import datetime, timezone

    db = tmp_path / "rescore.db"
    app = create_app(Settings(database_url=f"sqlite:///{db.as_posix()}", log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(Company(company_domain="a.com", canonical_company_id="A", company_name="A",
                          name_key="a", validation_status="VALID"))
            s.add(LeadScore(company_domain="a.com", lead_score=40.0, grade="B", priority_rank=1,
                            scored_at=datetime(2026, 6, 18, 9, 0, tzinfo=timezone.utc)))
            s.commit()

        etag = c.get("/analytics/summary").headers["etag"]
        assert c.get("/analytics/summary", headers={"If-None-Match": etag}).status_code == 304

        # Re-score in place: same row, newer scored_at, NO PipelineRun logged.
        with app.state.db.sessionmaker() as s:
            score = s.get(LeadScore, "a.com")
            score.lead_score, score.grade = 90.0, "A+"
            score.scored_at = datetime(2026, 6, 20, 9, 0, tzinfo=timezone.utc)
            s.commit()

        r = c.get("/analytics/summary", headers={"If-None-Match": etag})
        assert r.status_code == 200 and r.headers["etag"] != etag


def test_rate_limit():
    app = create_app(Settings(database_url="sqlite:///:memory:", rate_limit_per_minute=3, log_json=False))
    with TestClient(app) as c:
        for _ in range(4):
            assert c.get("/health").status_code == 200  # /health is exempt
        codes = [c.get("/nope").status_code for _ in range(5)]  # limit 3/min
        assert 429 in codes
        assert 404 in codes  # first requests under the limit fall through to routing
