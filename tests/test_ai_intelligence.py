"""Enterprise CRM Phase 8: AI Intelligence & Copilot tests (deterministic, no LLM)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company, CsContract, ForecastSnapshot, SlaPolicy, SlaTracker

MGR = {"X-Dev-Role": "manager"}
MEM = {"X-Dev-Role": "member"}

DEFAULT_STAGES = [
    {"name": "Prospect", "stage_type": "open",  "stage_order": 1, "probability": 10},
    {"name": "Won",       "stage_type": "won",  "stage_order": 2, "probability": 100},
    {"name": "Lost",      "stage_type": "lost", "stage_order": 3, "probability": 0},
]


def _seed(s):
    s.add(Company(
        company_domain="acme.com", canonical_company_id="ACME",
        company_name="Acme Corp", name_key="acme",
        prospect_type="PRODUCT_COMPANY", validation_status="VALID",
        company_tier="INCUMBENT", country="US",
    ))
    s.add(Company(
        company_domain="beta.com", canonical_company_id="BETA",
        company_name="Beta Inc", name_key="beta",
        prospect_type="PRODUCT_COMPANY", validation_status="VALID",
        company_tier="SCALEUP", country="CA",
    ))
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'ai.db').as_posix()}",
        log_json=False, dev_auth_bypass=True,
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _uid(client, headers=MGR) -> int:
    return client.get("/auth/me", headers=headers).json()["id"]


def _make_pipeline(client):
    return client.post("/pipelines", headers=MGR, json={"name": "P", "stages": DEFAULT_STAGES}).json()


def _stages(p):
    return {s["stage_type"]: s for s in p["stages"]}


def _make_deal(client, pipeline_id, stage_id, **kw):
    payload = {
        "title": kw.get("title", "Deal"),
        "company_domain": kw.get("company_domain", "acme.com"),
        "pipeline_id": pipeline_id,
        "stage_id": stage_id,
        "value": kw.get("value", 50_000.0),
        "probability": kw.get("probability", 25),
    }
    return client.post("/deals", headers=MGR, json=payload).json()


def _backdate_deal_activity(client, deal_id, days_ago):
    with client.app.state.db.sessionmaker() as s:
        from master_db.models import CrmDeal
        d = s.get(CrmDeal, deal_id)
        d.last_activity_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
        s.commit()


def _make_cs_account(client, **kw):
    payload = {"name": "Acme CS", "company_domain": "acme.com", "tier": "enterprise", **kw}
    return client.post("/cs/accounts", headers=MGR, json=payload).json()


# =====================================================================
# Insight Generation
# =====================================================================
class TestInsightGeneration:
    def test_stalled_deal_insight(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        _backdate_deal_activity(client, d["id"], 20)
        r = client.post("/ai/insights/generate", headers=MGR)
        assert r.status_code == 201
        assert r.json()["generated"] >= 1
        insights = client.get("/ai/insights?insight_type=deal", headers=MGR).json()
        assert insights["total"] >= 1
        assert "stalled" in insights["items"][0]["title"].lower()

    def test_generate_is_idempotent(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        _backdate_deal_activity(client, d["id"], 20)
        client.post("/ai/insights/generate", headers=MGR)
        r2 = client.post("/ai/insights/generate", headers=MGR)
        assert r2.json()["generated"] == 0  # no duplicate active insight

    def test_customer_at_risk_insight(self, client):
        _make_cs_account(client, status="at_risk")
        r = client.post("/ai/insights/generate", headers=MGR)
        assert r.status_code == 201
        insights = client.get("/ai/insights?insight_type=customer", headers=MGR).json()
        assert insights["total"] >= 1

    def test_no_insights_when_data_is_healthy(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])  # fresh, not stalled
        r = client.post("/ai/insights/generate", headers=MGR)
        assert r.json()["generated"] == 0

    def test_list_insights_filter_by_severity(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        _backdate_deal_activity(client, d["id"], 40)
        client.post("/ai/insights/generate", headers=MGR)
        r = client.get("/ai/insights?severity=high", headers=MGR)
        assert r.json()["total"] >= 1

    def test_dismiss_insight(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        _backdate_deal_activity(client, d["id"], 20)
        client.post("/ai/insights/generate", headers=MGR)
        insight_id = client.get("/ai/insights", headers=MGR).json()["items"][0]["id"]
        r = client.patch(f"/ai/insights/{insight_id}", headers=MGR, json={"status": "dismissed"})
        assert r.json()["status"] == "dismissed"

    def test_patch_insight_invalid_status(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        _backdate_deal_activity(client, d["id"], 20)
        client.post("/ai/insights/generate", headers=MGR)
        insight_id = client.get("/ai/insights", headers=MGR).json()["items"][0]["id"]
        r = client.patch(f"/ai/insights/{insight_id}", headers=MGR, json={"status": "bogus"})
        assert r.status_code == 422

    def test_patch_insight_not_found(self, client):
        assert client.patch("/ai/insights/9999", headers=MGR, json={"status": "resolved"}).status_code == 404

    def test_revenue_insight_from_forecast_variance(self, client):
        with client.app.state.db.sessionmaker() as s:
            s.add(ForecastSnapshot(
                pipeline_id=None, period_type="monthly", period_key="2020-01",
                category="commit", forecasted_amount=100_000.0,
                snapshot_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            ))
            s.commit()
        r = client.post("/ai/insights/generate", headers=MGR)
        insights = client.get("/ai/insights?insight_type=revenue", headers=MGR).json()
        assert insights["total"] >= 1


# =====================================================================
# Recommendation Engine
# =====================================================================
class TestRecommendationEngine:
    def test_next_best_action_recommendation(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        _backdate_deal_activity(client, d["id"], 10)
        r = client.post("/ai/recommendations/generate", headers=MGR)
        assert r.status_code == 201
        assert r.json()["generated"] >= 1
        recs = client.get("/ai/recommendations?recommendation_type=next_best_action", headers=MGR).json()
        assert recs["total"] >= 1

    def test_customer_retention_recommendation(self, client):
        _make_cs_account(client, status="at_risk")
        r = client.post("/ai/recommendations/generate", headers=MGR)
        recs = client.get("/ai/recommendations?recommendation_type=customer_retention", headers=MGR).json()
        assert recs["total"] >= 1

    def test_renewal_action_recommendation(self, client):
        acct = _make_cs_account(client)
        with client.app.state.db.sessionmaker() as s:
            s.add(CsContract(
                account_id=acct["id"], name="Renewal", status="active", value=1000.0,
                end_date=datetime.now(timezone.utc) + timedelta(days=10),
            ))
            s.commit()
        client.post("/ai/recommendations/generate", headers=MGR)
        recs = client.get("/ai/recommendations?recommendation_type=renewal_action", headers=MGR).json()
        assert recs["total"] >= 1

    def test_dismiss_recommendation(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        _backdate_deal_activity(client, d["id"], 10)
        client.post("/ai/recommendations/generate", headers=MGR)
        rec_id = client.get("/ai/recommendations", headers=MGR).json()["items"][0]["id"]
        r = client.post(f"/ai/recommendations/{rec_id}/dismiss", headers=MGR)
        assert r.json()["status"] == "dismissed"
        assert r.json()["dismissed_at"] is not None

    def test_complete_recommendation(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        _backdate_deal_activity(client, d["id"], 10)
        client.post("/ai/recommendations/generate", headers=MGR)
        rec_id = client.get("/ai/recommendations", headers=MGR).json()["items"][0]["id"]
        r = client.post(f"/ai/recommendations/{rec_id}/complete", headers=MGR)
        assert r.json()["status"] == "completed"
        assert r.json()["completed_at"] is not None
        assert r.json()["completed_by"] is not None

    def test_dismiss_not_found(self, client):
        assert client.post("/ai/recommendations/9999/dismiss", headers=MGR).status_code == 404

    def test_recommendation_generate_idempotent(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        _backdate_deal_activity(client, d["id"], 10)
        client.post("/ai/recommendations/generate", headers=MGR)
        r2 = client.post("/ai/recommendations/generate", headers=MGR)
        assert r2.json()["generated"] == 0


# =====================================================================
# Risk Detection
# =====================================================================
class TestRiskDetection:
    def test_stalled_deal_risk(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        _backdate_deal_activity(client, d["id"], 20)
        r = client.post("/ai/risks/detect", headers=MGR)
        assert r.status_code == 201
        risks = client.get("/ai/risks?risk_type=stalled_deal", headers=MGR).json()
        assert risks["total"] >= 1
        assert risks["items"][0]["score"] > 0

    def test_at_risk_customer_risk(self, client):
        _make_cs_account(client, status="at_risk")
        client.post("/ai/risks/detect", headers=MGR)
        risks = client.get("/ai/risks?risk_type=at_risk_customer", headers=MGR).json()
        assert risks["total"] >= 1

    def test_missed_sla_risk(self, client):
        policy = client.post("/workflows/sla/policies", headers=MGR, json={
            "name": "Test SLA", "entity_type": "deal", "due_hours": 1,
        }).json()
        past = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        client.post("/workflows/sla/trackers", headers=MGR, json={
            "policy_id": policy["id"], "entity_type": "deal", "entity_id": "1", "due_at": past,
        })
        client.post("/workflows/sla/tick", headers=MGR)
        r = client.post("/ai/risks/detect", headers=MGR)
        risks = client.get("/ai/risks?risk_type=missed_sla", headers=MGR).json()
        assert risks["total"] >= 1

    def test_forecast_variance_risk(self, client):
        with client.app.state.db.sessionmaker() as s:
            s.add(ForecastSnapshot(
                pipeline_id=None, period_type="monthly", period_key="2020-01",
                category="commit", forecasted_amount=100_000.0,
                snapshot_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            ))
            s.commit()
        client.post("/ai/risks/detect", headers=MGR)
        risks = client.get("/ai/risks?risk_type=forecast_variance", headers=MGR).json()
        assert risks["total"] >= 1

    def test_detect_risks_clears_prior_snapshot(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        _backdate_deal_activity(client, d["id"], 20)
        client.post("/ai/risks/detect", headers=MGR)
        first_count = client.get("/ai/risks?risk_type=stalled_deal", headers=MGR).json()["total"]
        client.post("/ai/risks/detect", headers=MGR)
        second_count = client.get("/ai/risks?risk_type=stalled_deal", headers=MGR).json()["total"]
        assert first_count == second_count == 1  # not doubled


# =====================================================================
# Engagement / Activity Intelligence
# =====================================================================
class TestEngagementIntelligence:
    def test_compute_engagement_scores(self, client):
        _make_cs_account(client)
        r = client.post("/ai/engagement/compute", headers=MGR)
        assert r.status_code == 201
        assert r.json()["generated"] >= 1
        scores = client.get("/ai/engagement/scores", headers=MGR).json()
        assert scores["total"] >= 1
        assert "trend" in scores["items"][0]

    def test_engagement_score_reflects_task_completion(self, client):
        _make_cs_account(client)
        client.post("/outreach/tasks", headers=MGR, json={"title": "T1", "company_domain": "acme.com"})
        task = client.post("/outreach/tasks", headers=MGR, json={"title": "T2", "company_domain": "acme.com"}).json()
        client.patch(f"/outreach/tasks/{task['id']}", headers=MGR, json={"status": "completed"})
        client.post("/ai/engagement/compute", headers=MGR)
        scores = client.get("/ai/engagement/scores", headers=MGR).json()
        item = scores["items"][0]
        assert item["task_completion_score"] == 50.0

    def test_activity_summary_endpoint(self, client):
        acct = _make_cs_account(client)
        r = client.get(f"/ai/activity/customer/{acct['id']}", headers=MGR)
        assert r.status_code == 200
        assert "task(s)" in r.json()["summary"]

    def test_activity_summary_not_found(self, client):
        assert client.get("/ai/activity/customer/9999", headers=MGR).status_code == 404


# =====================================================================
# AI Copilot
# =====================================================================
class TestCopilot:
    def test_customer_summary(self, client):
        acct = _make_cs_account(client)
        r = client.get(f"/ai/copilot/customer/{acct['id']}", headers=MGR)
        assert r.status_code == 200
        assert acct["name"] in r.json()["summary"]

    def test_customer_summary_not_found(self, client):
        assert client.get("/ai/copilot/customer/9999", headers=MGR).status_code == 404

    def test_deal_summary(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        r = client.get(f"/ai/copilot/deal/{d['id']}", headers=MGR)
        assert r.status_code == 200
        assert d["title"] in r.json()["summary"]

    def test_pipeline_summary(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        r = client.get(f"/ai/copilot/pipeline/{p['id']}", headers=MGR)
        assert r.status_code == 200
        assert "Win rate" in r.json()["summary"]

    def test_executive_summary(self, client):
        r = client.get("/ai/copilot/executive", headers=MGR)
        assert r.status_code == 200
        assert "revenue" in r.json()["summary"].lower()

    def test_entity_summary_dispatch(self, client):
        acct = _make_cs_account(client)
        r = client.get(f"/ai/copilot/summary/customer/{acct['id']}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["query_type"] == "customer_summary"

    def test_entity_summary_unsupported_type(self, client):
        r = client.get("/ai/copilot/summary/campaign/1", headers=MGR)
        assert r.status_code == 422

    def test_copilot_calls_are_deterministic(self, client):
        acct = _make_cs_account(client)
        r1 = client.get(f"/ai/copilot/customer/{acct['id']}", headers=MGR)
        r2 = client.get(f"/ai/copilot/customer/{acct['id']}", headers=MGR)
        assert r1.json()["summary"] == r2.json()["summary"]


# =====================================================================
# Executive Briefings
# =====================================================================
class TestExecutiveBriefings:
    def test_generate_briefing(self, client):
        r = client.post("/ai/briefings/generate", headers=MGR)
        assert r.status_code == 201
        body = r.json()
        for key in ("revenue_highlights", "pipeline_changes", "customer_risks",
                    "expansion_opportunities", "renewal_outlook", "workflow_alerts"):
            assert key in body["sections"]

    def test_briefing_includes_customer_risks(self, client):
        _make_cs_account(client, status="at_risk")
        r = client.post("/ai/briefings/generate", headers=MGR)
        assert len(r.json()["sections"]["customer_risks"]) >= 1

    def test_list_briefings(self, client):
        client.post("/ai/briefings/generate", headers=MGR)
        client.post("/ai/briefings/generate", headers=MGR)
        r = client.get("/ai/briefings", headers=MGR)
        assert len(r.json()) == 2

    def test_latest_briefing(self, client):
        client.post("/ai/briefings/generate", headers=MGR)
        r = client.get("/ai/briefings/latest", headers=MGR)
        assert r.status_code == 200
        assert r.json() is not None

    def test_latest_briefing_none_when_empty(self, client):
        r = client.get("/ai/briefings/latest", headers=MGR)
        assert r.status_code == 200
        assert r.json() is None


# =====================================================================
# AI Dashboard
# =====================================================================
class TestAiDashboard:
    def test_dashboard_returns_200(self, client):
        r = client.get("/ai/dashboard/summary", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        for key in ("active_insights", "pending_recommendations", "active_risks",
                    "latest_briefing", "avg_engagement_score", "recent_ai_activity"):
            assert key in body

    def test_dashboard_reflects_generated_insights(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        _backdate_deal_activity(client, d["id"], 20)
        client.post("/ai/insights/generate", headers=MGR)
        r = client.get("/ai/dashboard/summary", headers=MGR)
        assert r.json()["active_insights"] >= 1

    def test_member_can_view_dashboard(self, client):
        assert client.get("/ai/dashboard/summary", headers=MEM).status_code == 200


# =====================================================================
# AI Analytics
# =====================================================================
class TestAiAnalytics:
    def test_analytics_returns_200(self, client):
        r = client.get("/ai/analytics/summary", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        for key in ("insight_counts", "recommendation_acceptance", "risk_distribution",
                    "avg_engagement_score", "engagement_trend_counts", "copilot_usage_by_type",
                    "executive_briefings_generated"):
            assert key in body

    def test_insight_counts_by_type(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        _backdate_deal_activity(client, d["id"], 20)
        client.post("/ai/insights/generate", headers=MGR)
        r = client.get("/ai/analytics/summary", headers=MGR)
        assert r.json()["insight_counts"].get("deal", 0) >= 1

    def test_recommendation_acceptance_rate(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        _backdate_deal_activity(client, d["id"], 10)
        client.post("/ai/recommendations/generate", headers=MGR)
        rec_id = client.get("/ai/recommendations", headers=MGR).json()["items"][0]["id"]
        client.post(f"/ai/recommendations/{rec_id}/complete", headers=MGR)
        r = client.get("/ai/analytics/summary", headers=MGR)
        acceptance = r.json()["recommendation_acceptance"]
        assert any(a["completed"] >= 1 for a in acceptance)

    def test_copilot_usage_tracked(self, client):
        acct = _make_cs_account(client)
        client.get(f"/ai/copilot/customer/{acct['id']}", headers=MGR)
        client.get(f"/ai/copilot/customer/{acct['id']}", headers=MGR)
        r = client.get("/ai/analytics/summary", headers=MGR)
        assert r.json()["copilot_usage_by_type"].get("customer_summary", 0) == 2

    def test_briefings_generated_count(self, client):
        client.post("/ai/briefings/generate", headers=MGR)
        r = client.get("/ai/analytics/summary", headers=MGR)
        assert r.json()["executive_briefings_generated"] == 1


# =====================================================================
# Backward Compatibility
# =====================================================================
class TestBackwardCompatibility:
    def test_deals_endpoint(self, client):
        assert client.get("/deals", headers=MGR).status_code == 200

    def test_workflows_endpoint(self, client):
        assert client.get("/workflows", headers=MGR).status_code == 200

    def test_custom_objects_endpoint(self, client):
        assert client.get("/custom-objects", headers=MGR).status_code == 200

    def test_revops_dashboard(self, client):
        assert client.get("/revops/executive-dashboard", headers=MGR).status_code == 200

    def test_cs_accounts_endpoint(self, client):
        assert client.get("/cs/accounts", headers=MGR).status_code == 200

    def test_campaigns_endpoint(self, client):
        assert client.get("/campaigns", headers=MGR).status_code == 200

    def test_pipelines_endpoint(self, client):
        assert client.get("/pipelines", headers=MGR).status_code == 200

    def test_team_work_queue(self, client):
        assert client.get("/team/work-queue", headers=MGR).status_code == 200

    def test_outreach_leads(self, client):
        assert client.get("/outreach/leads", headers=MGR).status_code == 200
