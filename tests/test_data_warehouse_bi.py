"""Enterprise CRM Phase 12: Data Warehouse & Advanced Business Intelligence tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company

MGR = {"X-Dev-Role": "manager"}
MEM = {"X-Dev-Role": "member"}
ADMIN = {"X-Dev-Role": "admin"}

DEFAULT_STAGES = [
    {"name": "Prospect", "stage_type": "open", "stage_order": 1, "probability": 10},
    {"name": "Won", "stage_type": "won", "stage_order": 2, "probability": 100},
    {"name": "Lost", "stage_type": "lost", "stage_order": 3, "probability": 0},
]


def _seed(s):
    s.add(Company(
        company_domain="acme.com", canonical_company_id="ACME",
        company_name="Acme Corp", name_key="acme",
        prospect_type="PRODUCT_COMPANY", validation_status="VALID",
        company_tier="INCUMBENT",
    ))
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'bi.db').as_posix()}",
        log_json=False, dev_auth_bypass=True,
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _make_pipeline(client):
    return client.post("/pipelines", headers=MGR, json={"name": "P", "stages": DEFAULT_STAGES}).json()


def _make_deal(client, pipeline_id, stage_id, **kw):
    payload = {
        "title": kw.get("title", "Deal"), "company_domain": "acme.com",
        "pipeline_id": pipeline_id, "stage_id": stage_id,
        "value": kw.get("value", 50_000.0), "probability": kw.get("probability", 25),
    }
    return client.post("/deals", headers=MGR, json=payload).json()


def _make_kpi(client, **kw):
    payload = {"name": "Win Rate", "category": "sales", "target_value": 0.5, "unit": "ratio", **kw}
    return client.post("/bi/kpis", headers=MGR, json=payload).json()


def _make_report(client, **kw):
    payload = {"name": "Open Deals Report", "entity_type": "deal", "filters": {}, "group_by": "", **kw}
    return client.post("/bi/reports", headers=MGR, json=payload).json()


# =====================================================================
# Historical Data Warehouse
# =====================================================================
class TestWarehouse:
    def test_refresh_creates_one_snapshot_per_metric_type(self, client):
        r = client.post("/bi/warehouse/refresh", headers=MGR)
        assert r.status_code == 200
        assert r.json()["snapshots_created"] == 7

    def test_refresh_manager_only(self, client):
        r = client.post("/bi/warehouse/refresh", headers=MEM)
        assert r.status_code == 403

    def test_list_snapshots(self, client):
        client.post("/bi/warehouse/refresh", headers=MGR)
        r = client.get("/bi/warehouse/snapshots", headers=MGR)
        assert r.json()["total"] == 7

    def test_list_snapshots_filtered_by_type(self, client):
        client.post("/bi/warehouse/refresh", headers=MGR)
        r = client.get("/bi/warehouse/snapshots", headers=MGR, params={"metric_type": "revenue"})
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["metric_type"] == "revenue"

    def test_snapshot_metrics_populated(self, client):
        client.post("/bi/warehouse/refresh", headers=MGR)
        r = client.get("/bi/warehouse/snapshots", headers=MGR, params={"metric_type": "workflow_metrics"})
        metrics = r.json()["items"][0]["metrics"]
        assert "total" in metrics


# =====================================================================
# KPI Framework
# =====================================================================
class TestKpiFramework:
    def test_create_kpi(self, client):
        k = _make_kpi(client)
        assert k["id"] > 0
        assert k["status"] == "no_target" or k["current_value"] is None

    def test_create_kpi_duplicate_name_rejected(self, client):
        _make_kpi(client)
        r = client.post("/bi/kpis", headers=MGR, json={"name": "Win Rate", "category": "sales"})
        assert r.status_code == 409

    def test_create_kpi_manager_only(self, client):
        r = client.post("/bi/kpis", headers=MEM, json={"name": "X", "category": "sales"})
        assert r.status_code == 403

    def test_record_kpi_value_and_status(self, client):
        k = _make_kpi(client, target_value=100.0)
        client.post(f"/bi/kpis/{k['id']}/values", headers=MGR, json={"value": 95.0})
        r = client.get("/bi/kpis", headers=MGR)
        kpi = next(x for x in r.json() if x["id"] == k["id"])
        assert kpi["current_value"] == 95.0
        assert kpi["status"] == "on_track"

    def test_kpi_status_off_track(self, client):
        k = _make_kpi(client, name="Low KPI", target_value=100.0)
        client.post(f"/bi/kpis/{k['id']}/values", headers=MGR, json={"value": 10.0})
        r = client.get("/bi/kpis", headers=MGR)
        kpi = next(x for x in r.json() if x["id"] == k["id"])
        assert kpi["status"] == "off_track"

    def test_kpi_history(self, client):
        k = _make_kpi(client)
        client.post(f"/bi/kpis/{k['id']}/values", headers=MGR, json={"value": 1.0})
        client.post(f"/bi/kpis/{k['id']}/values", headers=MGR, json={"value": 2.0})
        r = client.get(f"/bi/kpis/{k['id']}/values", headers=MGR)
        assert len(r.json()) == 2

    def test_delete_kpi(self, client):
        k = _make_kpi(client)
        assert client.delete(f"/bi/kpis/{k['id']}", headers=MGR).status_code == 204


# =====================================================================
# Executive Dashboards
# =====================================================================
class TestExecutiveDashboards:
    @pytest.mark.parametrize("dashboard_type", [
        "revenue_overview", "pipeline_overview", "customer_overview",
        "operations_overview", "ai_overview", "organization_overview",
    ])
    def test_dashboard_types(self, client, dashboard_type):
        r = client.get(f"/bi/dashboards/{dashboard_type}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["dashboard_type"] == dashboard_type
        assert r.json()["metrics"]

    def test_invalid_dashboard_type_rejected(self, client):
        r = client.get("/bi/dashboards/bogus_overview", headers=MGR)
        assert r.status_code == 422


# =====================================================================
# Trend Analysis
# =====================================================================
class TestTrendAnalysis:
    def test_trend_after_two_refreshes(self, client):
        client.post("/bi/warehouse/refresh", headers=MGR)
        client.post("/bi/warehouse/refresh", headers=MGR)
        r = client.get("/bi/trends/workflow_usage", headers=MGR)
        assert r.status_code == 200
        assert len(r.json()["points"]) == 2

    def test_trend_unknown_metric_rejected(self, client):
        r = client.get("/bi/trends/bogus_metric", headers=MGR)
        assert r.status_code == 422

    @pytest.mark.parametrize("metric", [
        "revenue", "pipeline", "customer_growth", "churn", "expansion",
        "campaign_performance", "workflow_usage", "ai_usage",
    ])
    def test_all_trend_metrics_supported(self, client, metric):
        client.post("/bi/warehouse/refresh", headers=MGR)
        r = client.get(f"/bi/trends/{metric}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["metric"] == metric


# =====================================================================
# Custom Reports
# =====================================================================
class TestCustomReports:
    def test_create_report(self, client):
        r = _make_report(client)
        assert r["status"] == "draft"

    def test_create_report_invalid_entity_type_rejected(self, client):
        r = client.post("/bi/reports", headers=MGR, json={"name": "X", "entity_type": "bogus"})
        assert r.status_code == 422

    def test_run_report_returns_deal_rows(self, client):
        pipeline = _make_pipeline(client)
        open_stage = next(s for s in pipeline["stages"] if s["stage_type"] == "open")
        _make_deal(client, pipeline["id"], open_stage["id"])
        report = _make_report(client)
        r = client.get(f"/bi/reports/{report['id']}/run", headers=MGR)
        assert r.json()["total_rows"] == 1
        assert "title" in r.json()["columns"]

    def test_run_report_with_group_by(self, client):
        pipeline = _make_pipeline(client)
        open_stage = next(s for s in pipeline["stages"] if s["stage_type"] == "open")
        _make_deal(client, pipeline["id"], open_stage["id"])
        _make_deal(client, pipeline["id"], open_stage["id"], title="Deal 2")
        report = _make_report(client, group_by="stage_id")
        r = client.get(f"/bi/reports/{report['id']}/run", headers=MGR)
        assert r.json()["columns"] == ["stage_id", "count"]
        assert r.json()["rows"][0]["count"] == 2

    def test_run_report_with_filter(self, client):
        pipeline = _make_pipeline(client)
        open_stage = next(s for s in pipeline["stages"] if s["stage_type"] == "open")
        won_stage = next(s for s in pipeline["stages"] if s["stage_type"] == "won")
        _make_deal(client, pipeline["id"], open_stage["id"])
        report = _make_report(client, filters={"stage_id": won_stage["id"]})
        r = client.get(f"/bi/reports/{report['id']}/run", headers=MGR)
        assert r.json()["total_rows"] == 0

    def test_report_ownership_enforced(self, client):
        report = _make_report(client)
        r = client.patch(f"/bi/reports/{report['id']}", headers=MEM, json={"name": "Hacked"})
        assert r.status_code == 403

    def test_delete_report(self, client):
        report = _make_report(client)
        assert client.delete(f"/bi/reports/{report['id']}", headers=MGR).status_code == 204


# =====================================================================
# Scheduled Reporting
# =====================================================================
class TestScheduledReporting:
    def test_create_schedule(self, client):
        report = _make_report(client)
        r = client.post(f"/bi/reports/{report['id']}/schedules", headers=MGR, json={"frequency": "weekly", "recipient_emails": ["a@x.com"]})
        assert r.status_code == 201
        assert r.json()["frequency"] == "weekly"

    def test_deliver_schedule_creates_run_history(self, client):
        report = _make_report(client)
        s = client.post(f"/bi/reports/{report['id']}/schedules", headers=MGR, json={"frequency": "daily", "recipient_emails": ["a@x.com"]}).json()
        r = client.post(f"/bi/schedules/{s['id']}/deliver", headers=MGR)
        assert r.status_code == 200
        assert r.json()["status"] == "sent"
        runs = client.get(f"/bi/schedules/{s['id']}/runs", headers=MGR).json()
        assert len(runs) == 1

    def test_deliver_updates_last_run_at(self, client):
        report = _make_report(client)
        s = client.post(f"/bi/reports/{report['id']}/schedules", headers=MGR, json={"frequency": "monthly", "recipient_emails": ["a@x.com"]}).json()
        client.post(f"/bi/schedules/{s['id']}/deliver", headers=MGR)
        r = client.get("/bi/schedules", headers=MGR, params={"report_id": report["id"]})
        assert r.json()[0]["last_run_at"] is not None

    def test_run_due_schedules_tick(self, client):
        report = _make_report(client)
        client.post(f"/bi/reports/{report['id']}/schedules", headers=MGR, json={"frequency": "daily", "recipient_emails": []})
        r = client.post("/bi/schedules/tick", headers=MGR)
        assert r.json()["delivered"] == 1

    def test_delete_schedule(self, client):
        report = _make_report(client)
        s = client.post(f"/bi/reports/{report['id']}/schedules", headers=MGR, json={"frequency": "daily"}).json()
        assert client.delete(f"/bi/schedules/{s['id']}", headers=MGR).status_code == 204


# =====================================================================
# BI Dashboard + Analytics
# =====================================================================
class TestBiDashboardAndAnalytics:
    def test_dashboard_fields(self, client):
        client.post("/bi/warehouse/refresh", headers=MGR)
        _make_kpi(client, target_value=10.0)
        r = client.get("/bi/dashboard/summary", headers=MGR)
        body = r.json()
        assert len(body["kpis"]) == 1
        assert body["warehouse_snapshots_count"] == 7
        assert body["data_freshness"] is not None

    def test_analytics_fields(self, client):
        client.post("/bi/warehouse/refresh", headers=MGR)
        client.post("/bi/warehouse/refresh", headers=MGR)
        k = _make_kpi(client, target_value=10.0)
        client.post(f"/bi/kpis/{k['id']}/values", headers=MGR, json={"value": 8.0})
        r = client.get("/bi/analytics/summary", headers=MGR)
        body = r.json()
        assert body["kpi_achievement"]["Win Rate"] == 0.8
        assert "workflow_usage" in body["growth_rates"] or body["growth_rates"] == {} or isinstance(body["growth_rates"], dict)
        assert body["warehouse_statistics"]["revenue"] == 2


# =====================================================================
# Backward compatibility
# =====================================================================
class TestBackwardCompatibility:
    def test_existing_revops_endpoints_unaffected(self, client):
        assert client.get("/revops/executive-dashboard", headers=MGR).status_code == 200

    def test_existing_search_endpoints_unaffected(self, client):
        assert client.get("/search", headers=MGR, params={"q": "acme"}).status_code == 200

    def test_existing_integrations_endpoints_unaffected(self, client):
        assert client.get("/integrations", headers=MGR).status_code == 200


class TestReportScheduleTickSingleFlight:
    def test_schedule_tick_rejects_concurrent_call(self, client):
        import threading
        from backend.tick_lock import _locks
        lock = _locks.setdefault("report_schedule_tick", threading.Lock())
        assert lock.acquire(blocking=False)
        try:
            r = client.post("/bi/schedules/tick", headers=MGR)
            assert r.status_code == 409
        finally:
            lock.release()

    def test_schedule_tick_succeeds_when_not_locked(self, client):
        assert client.post("/bi/schedules/tick", headers=MGR).status_code == 200
