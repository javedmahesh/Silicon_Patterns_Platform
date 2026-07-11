"""Enterprise CRM Phase 5: Revenue Operations, Forecasting & Executive Analytics tests."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import (
    Base,
    Campaign,
    CampaignMember,
    Company,
    CrmDeal,
    CrmPipelineStage,
    CsAccount,
    ForecastSnapshot,
    LeadAssignment,
    LeadScore,
    Opportunity,
)

MGR = {"X-Dev-Role": "manager"}
MEM = {"X-Dev-Role": "member"}

DEFAULT_STAGES = [
    {"name": "Prospect", "stage_type": "open",  "stage_order": 1, "probability": 10},
    {"name": "Qualified", "stage_type": "open", "stage_order": 2, "probability": 25},
    {"name": "Won",       "stage_type": "won",  "stage_order": 3, "probability": 100},
    {"name": "Lost",      "stage_type": "lost", "stage_order": 4, "probability": 0},
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
    s.add(LeadScore(company_domain="acme.com", lead_score=88.0, grade="A", priority_rank=1))
    s.add(LeadScore(company_domain="beta.com", lead_score=70.0, grade="B", priority_rank=2))
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'revops.db').as_posix()}",
        log_json=False, dev_auth_bypass=True,
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _uid(client, headers=MGR) -> int:
    return client.get("/auth/me", headers=headers).json()["id"]


def _make_pipeline(client, name="Sales Pipeline"):
    return client.post("/pipelines", headers=MGR, json={"name": name, "stages": DEFAULT_STAGES}).json()


def _make_deal(client, pipeline_id, stage_id, **kw) -> dict:
    payload = {
        "title": kw.get("title", "Deal"),
        "company_domain": kw.get("company_domain", "acme.com"),
        "pipeline_id": pipeline_id,
        "stage_id": stage_id,
        "value": kw.get("value", 50_000.0),
        "probability": kw.get("probability", 25),
        "forecast_category": kw.get("forecast_category", "pipeline"),
    }
    if "expected_close_date" in kw:
        payload["expected_close_date"] = kw["expected_close_date"]
    if "lost_reason" in kw:
        payload["lost_reason"] = kw["lost_reason"]
    if "won_reason" in kw:
        payload["won_reason"] = kw["won_reason"]
    return client.post("/deals", headers=MGR, json=payload).json()


def _stages(p) -> dict:
    return {s["stage_type"]: s for s in p["stages"]}


# =====================================================================
# Deal lost_reason / won_reason (backward-compat extension)
# =====================================================================
class TestDealReasons:
    def test_create_deal_with_lost_reason(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["lost"]["id"], lost_reason="Bad timing")
        assert d["lost_reason"] == "Bad timing"
        assert d["won_reason"] == ""

    def test_create_deal_with_won_reason(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["won"]["id"], won_reason="Best price")
        assert d["won_reason"] == "Best price"

    def test_patch_deal_lost_reason(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        r = client.patch(f"/deals/{d['id']}", headers=MGR, json={"lost_reason": "Competitor"})
        assert r.status_code == 200
        assert r.json()["lost_reason"] == "Competitor"

    def test_deal_default_empty_reasons(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        assert d["lost_reason"] == ""
        assert d["won_reason"] == ""


# =====================================================================
# Revenue Forecast
# =====================================================================
class TestRevenueForecast:
    def _setup(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        # open deal with expected_close_date in 2030 so month bucket is predictable
        _make_deal(client, p["id"], st["open"]["id"], value=100_000.0, probability=50,
                   forecast_category="pipeline", expected_close_date="2030-06-15T00:00:00Z")
        _make_deal(client, p["id"], st["open"]["id"], value=80_000.0, probability=100,
                   forecast_category="commit", expected_close_date="2030-06-20T00:00:00Z")
        _make_deal(client, p["id"], st["open"]["id"], value=60_000.0, probability=75,
                   forecast_category="best_case", expected_close_date="2030-07-10T00:00:00Z")
        return p

    def test_forecast_monthly_returns_periods(self, client):
        self._setup(client)
        r = client.get("/revops/forecast?period_type=monthly", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert body["period_type"] == "monthly"
        periods = {p["period_key"]: p for p in body["periods"]}
        assert "2030-06" in periods
        assert "2030-07" in periods

    def test_forecast_monthly_values_correct(self, client):
        self._setup(client)
        r = client.get("/revops/forecast?period_type=monthly", headers=MGR)
        periods = {p["period_key"]: p for p in r.json()["periods"]}
        june = periods["2030-06"]
        # 100k + 80k = 180k pipeline; weighted = 100k*0.5 + 80k*1.0 = 130k; commit = 80k
        assert june["pipeline_value"] == 180_000.0
        assert june["weighted_value"] == 130_000.0
        assert june["commit_value"] == 80_000.0
        assert june["deal_count"] == 2

    def test_forecast_best_case_in_july(self, client):
        self._setup(client)
        r = client.get("/revops/forecast?period_type=monthly", headers=MGR)
        periods = {p["period_key"]: p for p in r.json()["periods"]}
        july = periods["2030-07"]
        assert july["best_case_value"] == 60_000.0
        assert july["deal_count"] == 1

    def test_forecast_quarterly(self, client):
        self._setup(client)
        r = client.get("/revops/forecast?period_type=quarterly", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert body["period_type"] == "quarterly"
        keys = [p["period_key"] for p in body["periods"]]
        assert "2030-Q2" in keys
        assert "2030-Q3" in keys

    def test_forecast_annual(self, client):
        self._setup(client)
        r = client.get("/revops/forecast?period_type=annual", headers=MGR)
        assert r.status_code == 200
        keys = [p["period_key"] for p in r.json()["periods"]]
        assert "2030" in keys

    def test_forecast_filtered_by_pipeline(self, client):
        p1 = _make_pipeline(client, "P1")
        p2 = _make_pipeline(client, "P2")
        st1 = _stages(p1)
        st2 = _stages(p2)
        _make_deal(client, p1["id"], st1["open"]["id"], value=10_000.0,
                   expected_close_date="2030-01-01T00:00:00Z")
        _make_deal(client, p2["id"], st2["open"]["id"], value=99_000.0,
                   expected_close_date="2030-01-01T00:00:00Z")
        r = client.get(f"/revops/forecast?pipeline_id={p1['id']}", headers=MGR)
        periods = r.json()["periods"]
        total = sum(p["pipeline_value"] for p in periods)
        assert total == 10_000.0

    def test_forecast_deals_without_close_date_excluded(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"], value=999_999.0)  # no expected_close_date
        r = client.get("/revops/forecast?period_type=monthly", headers=MGR)
        assert r.status_code == 200
        assert r.json()["periods"] == []

    def test_forecast_only_open_stage_deals(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["won"]["id"], value=50_000.0,
                   expected_close_date="2030-01-01T00:00:00Z")
        r = client.get("/revops/forecast?period_type=monthly", headers=MGR)
        assert r.json()["periods"] == []


# =====================================================================
# Forecast Snapshots & Accuracy
# =====================================================================
class TestForecastAccuracy:
    def test_capture_snapshot_returns_four_categories(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"], value=100_000.0,
                   expected_close_date="2099-01-01T00:00:00Z",
                   forecast_category="commit")
        r = client.post("/revops/forecast/snapshots?period_type=monthly", headers=MGR)
        assert r.status_code == 201
        body = r.json()
        assert len(body) == 4
        categories = {item["category"] for item in body}
        assert categories == {"pipeline", "weighted", "best_case", "commit"}

    def test_accuracy_empty_when_no_elapsed_snapshots(self, client):
        # Snapshot for current/future period should not appear in accuracy
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"], value=50_000.0,
                   expected_close_date="2099-01-01T00:00:00Z")
        client.post("/revops/forecast/snapshots?period_type=monthly", headers=MGR)
        r = client.get("/revops/forecast/accuracy?period_type=monthly", headers=MGR)
        assert r.status_code == 200
        assert r.json() == []

    def test_accuracy_for_past_snapshot(self, client):
        # Directly seed a past ForecastSnapshot (period 2020-01) into the DB.
        with client.app.state.db.sessionmaker() as s:
            s.add(ForecastSnapshot(
                pipeline_id=None, period_type="monthly", period_key="2020-01",
                category="commit", forecasted_amount=50_000.0,
                snapshot_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            ))
            s.commit()
        r = client.get("/revops/forecast/accuracy?period_type=monthly", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        a = body[0]
        assert a["period_key"] == "2020-01"
        assert a["forecasted_amount"] == 50_000.0
        assert a["actual_amount"] == 0.0
        assert a["variance"] == -50_000.0
        assert a["accuracy_pct"] == 0.0

    def test_accuracy_100pct_when_both_zero(self, client):
        with client.app.state.db.sessionmaker() as s:
            s.add(ForecastSnapshot(
                pipeline_id=None, period_type="monthly", period_key="2019-01",
                category="weighted", forecasted_amount=0.0,
                snapshot_at=datetime(2019, 1, 1, tzinfo=timezone.utc),
            ))
            s.commit()
        r = client.get("/revops/forecast/accuracy?period_type=monthly", headers=MGR)
        hits = [a for a in r.json() if a["period_key"] == "2019-01"]
        assert len(hits) == 1
        assert hits[0]["accuracy_pct"] == 100.0


# =====================================================================
# Revenue Targets
# =====================================================================
class TestRevenueTargets:
    def _payload(self, **kw):
        return {
            "scope": "company",
            "period_type": "quarterly",
            "period_start": "2030-01-01T00:00:00Z",
            "period_end": "2030-04-01T00:00:00Z",
            "target_amount": 500_000.0,
            "currency": "USD",
            **kw,
        }

    def test_create_target_manager_only(self, client):
        r = client.post("/revops/targets", headers=MEM, json=self._payload())
        assert r.status_code == 403

    def test_create_target(self, client):
        r = client.post("/revops/targets", headers=MGR, json=self._payload())
        assert r.status_code == 201
        body = r.json()
        assert body["scope"] == "company"
        assert body["target_amount"] == 500_000.0
        assert body["period_type"] == "quarterly"
        assert body["id"] > 0

    def test_list_targets_empty_then_populated(self, client):
        r = client.get("/revops/targets", headers=MGR)
        assert r.json()["total"] == 0
        client.post("/revops/targets", headers=MGR, json=self._payload())
        r = client.get("/revops/targets", headers=MGR)
        assert r.json()["total"] == 1

    def test_list_targets_filter_scope(self, client):
        client.post("/revops/targets", headers=MGR, json=self._payload(scope="company"))
        client.post("/revops/targets", headers=MGR, json=self._payload(scope="individual"))
        r = client.get("/revops/targets?scope=individual", headers=MGR)
        assert r.json()["total"] == 1

    def test_get_target(self, client):
        t = client.post("/revops/targets", headers=MGR, json=self._payload()).json()
        r = client.get(f"/revops/targets/{t['id']}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["target_amount"] == 500_000.0

    def test_get_target_not_found(self, client):
        assert client.get("/revops/targets/9999", headers=MGR).status_code == 404

    def test_delete_target_manager_only(self, client):
        t = client.post("/revops/targets", headers=MGR, json=self._payload()).json()
        assert client.delete(f"/revops/targets/{t['id']}", headers=MEM).status_code == 403
        assert client.delete(f"/revops/targets/{t['id']}", headers=MGR).status_code == 204
        assert client.get(f"/revops/targets/{t['id']}", headers=MGR).status_code == 404

    def test_attainment_zero_when_no_won_deals(self, client):
        t = client.post("/revops/targets", headers=MGR, json=self._payload()).json()
        r = client.get(f"/revops/targets/{t['id']}/attainment", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert body["target_amount"] == 500_000.0
        assert body["actual_amount"] == 0.0
        assert body["attainment_pct"] == 0.0
        assert body["target_id"] == t["id"]

    def test_attainment_not_found(self, client):
        assert client.get("/revops/targets/9999/attainment", headers=MGR).status_code == 404

    def test_attainment_is_elapsed_flag(self, client):
        # Past period → is_elapsed = True
        t = client.post("/revops/targets", headers=MGR, json=self._payload(
            period_start="2020-01-01T00:00:00Z", period_end="2020-04-01T00:00:00Z",
        )).json()
        r = client.get(f"/revops/targets/{t['id']}/attainment", headers=MGR)
        assert r.json()["is_elapsed"] is True

    def test_individual_scope_target_filters_by_owner(self, client):
        uid = _uid(client, MGR)
        t = client.post("/revops/targets", headers=MGR, json=self._payload(
            scope="individual", owner_id=uid,
            period_start="2020-01-01T00:00:00Z", period_end="2020-04-01T00:00:00Z",
        )).json()
        r = client.get(f"/revops/targets/{t['id']}/attainment", headers=MGR)
        assert r.status_code == 200
        assert r.json()["attainment_pct"] == 0.0


# =====================================================================
# Executive Dashboard
# =====================================================================
class TestExecutiveDashboard:
    def test_returns_200_with_expected_fields(self, client):
        r = client.get("/revops/executive-dashboard", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert "revenue_ttm" in body
        assert "pipeline_value" in body
        assert "weighted_forecast" in body
        assert "win_rate" in body
        assert "arr" in body
        assert "mrr" in body
        assert "active_customers" in body
        assert "churn_rate" in body
        assert "expansion_accounts" in body
        assert "generated_at" in body

    def test_pipeline_value_reflects_open_deals(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"], value=75_000.0)
        _make_deal(client, p["id"], st["open"]["id"], value=25_000.0)
        r = client.get("/revops/executive-dashboard", headers=MGR)
        assert r.json()["pipeline_value"] == 100_000.0

    def test_active_customers_from_cs_accounts(self, client):
        with client.app.state.db.sessionmaker() as s:
            s.add(CsAccount(
                name="Acme CS", company_domain="acme.com",
                status="active", tier="enterprise", arr=120_000.0, mrr=10_000.0,
                lifecycle_stage="customer",
            ))
            s.commit()
        r = client.get("/revops/executive-dashboard", headers=MGR)
        body = r.json()
        assert body["active_customers"] == 1
        assert body["arr"] == 120_000.0
        assert body["mrr"] == 10_000.0

    def test_win_rate_computed(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["won"]["id"], value=100_000.0)
        _make_deal(client, p["id"], st["lost"]["id"], value=50_000.0)
        r = client.get("/revops/executive-dashboard", headers=MGR)
        assert r.json()["win_rate"] == 0.5

    def test_cache_returns_same_generated_at(self, client):
        r1 = client.get("/revops/executive-dashboard", headers=MGR)
        r2 = client.get("/revops/executive-dashboard", headers=MGR)
        assert r1.json()["generated_at"] == r2.json()["generated_at"]

    def test_member_can_access_dashboard(self, client):
        assert client.get("/revops/executive-dashboard", headers=MEM).status_code == 200


# =====================================================================
# Pipeline Analytics
# =====================================================================
class TestPipelineAnalytics:
    def test_company_wide_analytics(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["won"]["id"], value=100_000.0)
        _make_deal(client, p["id"], st["lost"]["id"])
        _make_deal(client, p["id"], st["open"]["id"])
        r = client.get("/revops/pipeline-analytics", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert body["won_deals"] == 1
        assert body["lost_deals"] == 1
        assert body["open_deals"] == 1
        assert body["total_deals"] == 3
        assert body["win_rate"] == 0.5
        assert body["loss_rate"] == 0.5

    def test_pipeline_specific_analytics_includes_stage_velocity(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        r = client.get(f"/revops/pipeline-analytics?pipeline_id={p['id']}", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert body["pipeline_id"] == p["id"]
        assert isinstance(body["stage_velocity"], list)

    def test_aging_buckets_present(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        r = client.get("/revops/pipeline-analytics", headers=MGR)
        aging = {a["bucket"]: a["deal_count"] for a in r.json()["aging"]}
        assert "0-7d" in aging
        assert "60d+" in aging
        # new deal falls in 0-7d
        assert aging["0-7d"] == 1

    def test_lost_reasons_counted(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["lost"]["id"], lost_reason="Price")
        _make_deal(client, p["id"], st["lost"]["id"], lost_reason="Price", company_domain="beta.com")
        _make_deal(client, p["id"], st["lost"]["id"], lost_reason="Timing")
        r = client.get("/revops/pipeline-analytics", headers=MGR)
        reasons = r.json()["lost_reasons"]
        assert reasons.get("Price", 0) == 2
        assert reasons.get("Timing", 0) == 1

    def test_won_reasons_counted(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["won"]["id"], won_reason="Best ROI")
        r = client.get("/revops/pipeline-analytics", headers=MGR)
        reasons = r.json()["won_reasons"]
        assert reasons.get("Best ROI", 0) == 1

    def test_health_score_range(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["won"]["id"])
        r = client.get("/revops/pipeline-analytics", headers=MGR)
        hs = r.json()["pipeline_health_score"]
        assert 0.0 <= hs <= 100.0

    def test_pipeline_value_only_open_deals(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"], value=40_000.0)
        _make_deal(client, p["id"], st["won"]["id"], value=999_000.0)  # won: not in pipeline_value
        r = client.get("/revops/pipeline-analytics", headers=MGR)
        assert r.json()["pipeline_value"] == 40_000.0


# =====================================================================
# Sales Performance
# =====================================================================
class TestSalesPerformance:
    def test_returns_200_with_expected_shape(self, client):
        r = client.get("/revops/sales-performance", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        for key in ("by_owner", "by_team", "by_region", "by_industry", "by_tier"):
            assert key in body
        assert "avg_deal_size" in body
        assert "close_rate" in body

    def test_by_owner_includes_won_deals(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        uid = _uid(client, MGR)
        _make_deal(client, p["id"], st["won"]["id"], value=100_000.0)
        r = client.get("/revops/sales-performance", headers=MGR)
        by_owner = r.json()["by_owner"]
        assert len(by_owner) >= 1
        revenues = [o["revenue"] for o in by_owner]
        assert 100_000.0 in revenues

    def test_by_region_groups_by_country(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["won"]["id"], company_domain="acme.com", value=80_000.0)
        _make_deal(client, p["id"], st["won"]["id"], company_domain="beta.com", value=20_000.0)
        r = client.get("/revops/sales-performance", headers=MGR)
        by_region = {d["key"]: d["revenue"] for d in r.json()["by_region"]}
        assert by_region.get("US", 0) == 80_000.0
        assert by_region.get("CA", 0) == 20_000.0

    def test_avg_deal_size_computed(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["won"]["id"], value=100_000.0)
        _make_deal(client, p["id"], st["won"]["id"], value=50_000.0, company_domain="beta.com")
        r = client.get("/revops/sales-performance", headers=MGR)
        assert r.json()["avg_deal_size"] == 75_000.0

    def test_close_rate_computed(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["won"]["id"], value=50_000.0)
        _make_deal(client, p["id"], st["won"]["id"], value=50_000.0, company_domain="beta.com")
        _make_deal(client, p["id"], st["lost"]["id"], value=50_000.0)
        r = client.get("/revops/sales-performance", headers=MGR)
        assert r.json()["close_rate"] == pytest.approx(0.6667, abs=0.01)

    def test_by_industry_groups_via_cs_accounts(self, client):
        with client.app.state.db.sessionmaker() as s:
            s.add(CsAccount(
                name="Acme CS", company_domain="acme.com", status="active",
                tier="enterprise", industry="semiconductor", arr=0.0, mrr=0.0,
                lifecycle_stage="customer",
            ))
            s.commit()
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["won"]["id"], value=120_000.0)
        r = client.get("/revops/sales-performance", headers=MGR)
        by_ind = {d["key"]: d["revenue"] for d in r.json()["by_industry"]}
        assert "semiconductor" in by_ind
        assert by_ind["semiconductor"] == 120_000.0


# =====================================================================
# Funnel Analytics
# =====================================================================
class TestFunnelAnalytics:
    def test_returns_200_with_all_funnels(self, client):
        r = client.get("/revops/funnels", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert "lead_funnel" in body
        assert "opportunity_funnel" in body
        assert "deal_funnel" in body
        assert "campaign_funnel" in body

    def test_lead_funnel_counts_by_status(self, client):
        uid = _uid(client, MGR)
        with client.app.state.db.sessionmaker() as s:
            s.add(LeadAssignment(company_domain="acme.com", user_id=uid, status="qualified"))
            s.add(LeadAssignment(company_domain="beta.com", user_id=uid, status="contacted"))
            s.commit()
        r = client.get("/revops/funnels", headers=MGR)
        lead_funnel = {s["stage"]: s["count"] for s in r.json()["lead_funnel"]}
        assert lead_funnel.get("qualified", 0) == 1
        assert lead_funnel.get("contacted", 0) == 1

    def test_opportunity_funnel_counts_total(self, client):
        with client.app.state.db.sessionmaker() as s:
            s.add(Opportunity(opportunity_id="OPP1", company_domain="acme.com"))
            s.add(Opportunity(opportunity_id="OPP2", company_domain="beta.com"))
            s.commit()
        r = client.get("/revops/funnels", headers=MGR)
        opp = {s["stage"]: s["count"] for s in r.json()["opportunity_funnel"]}
        assert opp.get("discovered", 0) == 2

    def test_deal_funnel_reflects_stage_type(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        _make_deal(client, p["id"], st["won"]["id"])
        _make_deal(client, p["id"], st["lost"]["id"])
        r = client.get("/revops/funnels", headers=MGR)
        deal_f = {s["stage"]: s["count"] for s in r.json()["deal_funnel"]}
        assert deal_f["open"] == 1
        assert deal_f["won"] == 1
        assert deal_f["lost"] == 1

    def test_campaign_funnel_reflects_members(self, client):
        uid = _uid(client, MGR)
        with client.app.state.db.sessionmaker() as s:
            c = Campaign(name="Q1 Campaign", owner_id=uid, created_by=uid)
            s.add(c)
            s.flush()
            s.add(CampaignMember(
                campaign_id=c.id, company_domain="acme.com",
                engagement_status="active", campaign_outcome="converted",
            ))
            s.commit()
        r = client.get("/revops/funnels", headers=MGR)
        cf = r.json()["campaign_funnel"]
        status_keys = [item["stage"] for item in cf]
        assert any("active" in k for k in status_keys)
        assert any("converted" in k for k in status_keys)

    def test_lead_funnel_drop_off_computed(self, client):
        uid = _uid(client, MGR)
        with client.app.state.db.sessionmaker() as s:
            s.add(LeadAssignment(company_domain="acme.com", user_id=uid, status="new"))
            s.add(LeadAssignment(company_domain="beta.com", user_id=uid, status="contacted"))
            s.commit()
        r = client.get("/revops/funnels", headers=MGR)
        lead_funnel = r.json()["lead_funnel"]
        contacted = next(s for s in lead_funnel if s["stage"] == "contacted")
        # drop_off_pct should be None for first stage, non-None for later stages
        assert contacted["drop_off_pct"] is not None


# =====================================================================
# Executive Reports
# =====================================================================
class TestExecutiveReports:
    def test_revenue_report(self, client):
        r = client.get("/revops/reports/revenue", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert body["report_type"] == "revenue"
        assert "revenue_ttm" in body["data"]
        assert "arr" in body["data"]

    def test_forecast_report(self, client):
        r = client.get("/revops/reports/forecast", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert body["report_type"] == "forecast"
        assert "periods" in body["data"]

    def test_team_report(self, client):
        r = client.get("/revops/reports/team", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert body["report_type"] == "team"
        assert "by_owner" in body["data"]

    def test_pipeline_report(self, client):
        r = client.get("/revops/reports/pipeline", headers=MGR)
        assert r.status_code == 200
        assert r.json()["report_type"] == "pipeline"

    def test_customer_report(self, client):
        r = client.get("/revops/reports/customer", headers=MGR)
        assert r.status_code == 200
        assert "total_arr" in r.json()["data"]

    def test_campaign_report(self, client):
        r = client.get("/revops/reports/campaign", headers=MGR)
        assert r.status_code == 200
        assert "by_status" in r.json()["data"]

    def test_unknown_report_type_returns_404(self, client):
        r = client.get("/revops/reports/nonexistent", headers=MGR)
        assert r.status_code == 404

    def test_generated_at_present(self, client):
        r = client.get("/revops/reports/revenue", headers=MGR)
        assert r.json()["generated_at"] is not None

    def test_member_can_read_reports(self, client):
        assert client.get("/revops/reports/revenue", headers=MEM).status_code == 200


# =====================================================================
# BI Summary
# =====================================================================
class TestBiSummary:
    def test_bi_summary_returns_all_sections(self, client):
        r = client.get("/revops/bi/summary", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert "executive_dashboard" in body
        assert "funnels" in body
        assert "sales_performance" in body
        assert "revenue_trend" in body

    def test_bi_summary_revenue_trend_is_list(self, client):
        r = client.get("/revops/bi/summary", headers=MGR)
        assert isinstance(r.json()["revenue_trend"], list)

    def test_bi_summary_trend_includes_won_deals(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["won"]["id"], value=50_000.0)
        r = client.get("/revops/bi/summary", headers=MGR)
        trend = r.json()["revenue_trend"]
        total = sum(t["revenue"] for t in trend)
        assert total == 50_000.0

    def test_member_can_access_bi_summary(self, client):
        assert client.get("/revops/bi/summary", headers=MEM).status_code == 200


# =====================================================================
# Backward Compatibility
# =====================================================================
class TestBackwardCompatibility:
    """Existing endpoints must still return 200 after Phase 5 changes."""

    def test_deals_endpoint(self, client):
        p = _make_pipeline(client)
        r = client.get(f"/deals?pipeline_id={p['id']}", headers=MGR)
        assert r.status_code == 200

    def test_pipelines_endpoint(self, client):
        _make_pipeline(client)
        r = client.get("/pipelines", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_forecast_per_pipeline_unaffected(self, client):
        p = _make_pipeline(client)
        r = client.get(f"/pipelines/{p['id']}/forecast", headers=MGR)
        assert r.status_code == 200

    def test_pipeline_analytics_per_pipeline_unaffected(self, client):
        p = _make_pipeline(client)
        r = client.get(f"/pipelines/{p['id']}/analytics", headers=MGR)
        assert r.status_code == 200

    def test_campaigns_endpoint(self, client):
        r = client.get("/campaigns", headers=MGR)
        assert r.status_code == 200

    def test_cs_accounts_endpoint(self, client):
        r = client.get("/cs/accounts", headers=MGR)
        assert r.status_code == 200

    def test_assignments_endpoint(self, client):
        r = client.get("/assignments", headers=MGR)
        assert r.status_code == 200

    def test_deal_create_still_works(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        assert d["id"] > 0
        assert d["lost_reason"] == ""
        assert d["won_reason"] == ""

    def test_deal_patch_backward_compatible(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        r = client.patch(f"/deals/{d['id']}", headers=MGR, json={"notes": "updated"})
        assert r.status_code == 200
        assert r.json()["notes"] == "updated"

    def test_team_work_queue(self, client):
        r = client.get("/team/work-queue", headers=MGR)
        assert r.status_code == 200

    def test_outreach_leads(self, client):
        r = client.get("/outreach/leads", headers=MGR)
        assert r.status_code == 200
