"""Enterprise CRM Phase 10: Integration Platform & Developer Ecosystem tests."""
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
        database_url=f"sqlite:///{(tmp_path / 'integrations.db').as_posix()}",
        log_json=False, dev_auth_bypass=True,
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _make_integration(client, **kw):
    payload = {"name": "Slack", "provider": "slack", "category": "communication", **kw}
    return client.post("/integrations", headers=MGR, json=payload).json()


def _make_webhook(client, **kw):
    payload = {"name": "Test Hook", "event_type": "deal_created", "target_url": "https://example.com/hook", **kw}
    return client.post("/integrations/webhooks", headers=MGR, json=payload).json()


def _make_connector(client, **kw):
    payload = {"name": "REST Connector", "connector_type": "rest", "config": {"url": "https://example.com/ok"}, **kw}
    return client.post("/integrations/connectors", headers=MGR, json=payload).json()


def _make_plugin(client, **kw):
    payload = {"name": "Audit Plugin", "version": "1.0.0", "execution_hooks": ["after_create"], **kw}
    return client.post("/integrations/plugins", headers=MGR, json=payload).json()


def _make_pipeline(client):
    return client.post("/pipelines", headers=MGR, json={"name": "P", "stages": DEFAULT_STAGES}).json()


def _make_deal(client, pipeline_id, stage_id, **kw):
    payload = {
        "title": kw.get("title", "Deal"), "company_domain": "acme.com",
        "pipeline_id": pipeline_id, "stage_id": stage_id,
        "value": 50_000.0, "probability": 25,
    }
    return client.post("/deals", headers=MGR, json=payload).json()


# =====================================================================
# Integration Registry
# =====================================================================
class TestIntegrationRegistry:
    def test_create_integration_manager_only(self, client):
        r = client.post("/integrations", headers=MEM, json={"name": "X", "category": "crm"})
        assert r.status_code == 403

    def test_create_integration(self, client):
        i = _make_integration(client)
        assert i["id"] > 0
        assert i["status"] == "pending_setup"
        assert i["health_status"] == "unknown"

    def test_list_integrations(self, client):
        _make_integration(client)
        r = client.get("/integrations", headers=MGR)
        assert r.json()["total"] == 1

    def test_get_integration_not_found(self, client):
        assert client.get("/integrations/9999", headers=MGR).status_code == 404

    def test_patch_integration_status_and_health(self, client):
        i = _make_integration(client)
        r = client.patch(f"/integrations/{i['id']}", headers=MGR, json={"status": "active", "health_status": "healthy"})
        assert r.json()["status"] == "active"
        assert r.json()["health_status"] == "healthy"

    def test_delete_integration(self, client):
        i = _make_integration(client)
        assert client.delete(f"/integrations/{i['id']}", headers=MGR).status_code == 204
        assert client.get(f"/integrations/{i['id']}", headers=MGR).status_code == 404

    def test_category_filter(self, client):
        _make_integration(client, name="A", category="crm")
        _make_integration(client, name="B", category="finance")
        r = client.get("/integrations", headers=MGR, params={"category": "finance"})
        assert r.json()["total"] == 1


# =====================================================================
# Webhooks
# =====================================================================
class TestWebhooks:
    def test_create_webhook_shows_secret_once(self, client):
        w = _make_webhook(client)
        assert w["secret"]
        assert len(w["secret"]) > 20

    def test_list_webhooks_excludes_secret(self, client):
        _make_webhook(client)
        r = client.get("/integrations/webhooks", headers=MGR)
        item = r.json()["items"][0]
        assert "secret" not in item

    def test_default_retry_policy_applied(self, client):
        w = _make_webhook(client)
        assert w["retry_policy"]["max_attempts"] == 3

    def test_patch_disable_webhook(self, client):
        w = _make_webhook(client)
        r = client.patch(f"/integrations/webhooks/{w['id']}", headers=MGR, json={"status": "disabled"})
        assert r.json()["status"] == "disabled"

    def test_delete_webhook(self, client):
        w = _make_webhook(client)
        assert client.delete(f"/integrations/webhooks/{w['id']}", headers=MGR).status_code == 204
        assert client.get(f"/integrations/webhooks/{w['id']}", headers=MGR).status_code == 404

    def test_create_webhook_manager_only(self, client):
        r = client.post("/integrations/webhooks", headers=MEM, json={"name": "X", "event_type": "deal_created", "target_url": "https://x"})
        assert r.status_code == 403


# =====================================================================
# Event Bus + delivery
# =====================================================================
class TestEventBusAndDelivery:
    def test_publish_event_creates_log_row(self, client):
        r = client.post("/integrations/events/publish", headers=MEM, json={
            "category": "crm", "event_type": "custom_event", "payload": {"x": 1},
        })
        assert r.status_code == 201
        assert r.json()["category"] == "crm"

    def test_publish_invalid_category_rejected(self, client):
        r = client.post("/integrations/events/publish", headers=MEM, json={
            "category": "bogus", "event_type": "custom_event",
        })
        assert r.status_code == 422

    def test_publish_dispatches_to_matching_webhook(self, client):
        _make_webhook(client, event_type="order_placed", target_url="https://example.com/ok")
        client.post("/integrations/events/publish", headers=MEM, json={
            "category": "crm", "event_type": "order_placed", "payload": {"amount": 10},
        })
        r = client.get("/integrations/webhooks/deliveries/list", headers=MGR)
        assert r.json()["total"] == 1
        d = r.json()["items"][0]
        assert d["status"] == "success"
        assert d["response_code"] == 200

    def test_publish_does_not_dispatch_to_other_event_types(self, client):
        _make_webhook(client, event_type="order_placed", target_url="https://example.com/ok")
        client.post("/integrations/events/publish", headers=MEM, json={
            "category": "crm", "event_type": "unrelated_event",
        })
        r = client.get("/integrations/webhooks/deliveries/list", headers=MGR)
        assert r.json()["total"] == 0

    def test_wildcard_webhook_receives_every_event(self, client):
        _make_webhook(client, event_type="*", target_url="https://example.com/ok")
        client.post("/integrations/events/publish", headers=MEM, json={"category": "ai", "event_type": "insight_generated"})
        client.post("/integrations/events/publish", headers=MEM, json={"category": "revenue", "event_type": "forecast_updated"})
        r = client.get("/integrations/webhooks/deliveries/list", headers=MGR)
        assert r.json()["total"] == 2

    def test_failed_delivery_via_simulate_fail_hook(self, client):
        _make_webhook(client, event_type="order_placed", target_url="https://example.com/simulate-fail", retry_policy={"max_attempts": 1, "backoff_seconds": 0})
        client.post("/integrations/events/publish", headers=MEM, json={"category": "crm", "event_type": "order_placed"})
        r = client.get("/integrations/webhooks/deliveries/list", headers=MGR)
        d = r.json()["items"][0]
        assert d["status"] == "failed"
        assert d["attempt_count"] == 1
        assert d["error_detail"] == "simulated failure"

    def test_retrying_status_before_max_attempts(self, client):
        _make_webhook(client, event_type="order_placed", target_url="https://example.com/simulate-fail", retry_policy={"max_attempts": 3, "backoff_seconds": 0})
        client.post("/integrations/events/publish", headers=MEM, json={"category": "crm", "event_type": "order_placed"})
        r = client.get("/integrations/webhooks/deliveries/list", headers=MGR)
        d = r.json()["items"][0]
        assert d["status"] == "retrying"
        assert d["attempt_count"] == 1

    def test_replay_delivery_reattempts(self, client):
        _make_webhook(client, event_type="order_placed", target_url="https://example.com/simulate-fail", retry_policy={"max_attempts": 1, "backoff_seconds": 0})
        client.post("/integrations/events/publish", headers=MEM, json={"category": "crm", "event_type": "order_placed"})
        delivery_id = client.get("/integrations/webhooks/deliveries/list", headers=MGR).json()["items"][0]["id"]
        r = client.post(f"/integrations/webhooks/deliveries/{delivery_id}/replay", headers=MGR)
        assert r.status_code == 200
        assert r.json()["attempt_count"] == 2

    def test_retry_tick_processes_retrying_deliveries(self, client):
        _make_webhook(client, event_type="order_placed", target_url="https://example.com/simulate-fail", retry_policy={"max_attempts": 3, "backoff_seconds": 0})
        client.post("/integrations/events/publish", headers=MEM, json={"category": "crm", "event_type": "order_placed"})
        r = client.post("/integrations/webhooks/retry-tick", headers=MGR)
        assert r.json()["retried"] == 1
        d = client.get("/integrations/webhooks/deliveries/list", headers=MGR).json()["items"][0]
        assert d["attempt_count"] == 2
        assert d["status"] == "retrying"

    def test_list_events_filter_by_category(self, client):
        client.post("/integrations/events/publish", headers=MEM, json={"category": "ai", "event_type": "insight_generated"})
        client.post("/integrations/events/publish", headers=MEM, json={"category": "revenue", "event_type": "forecast_updated"})
        r = client.get("/integrations/events", headers=MGR, params={"category": "ai"})
        assert r.json()["total"] == 1


# =====================================================================
# OAuth credentials + API key reuse
# =====================================================================
class TestApiCredentials:
    def test_create_oauth_credential_shows_secret_once(self, client):
        r = client.post("/integrations/oauth-credentials", headers=MGR, json={"name": "X", "provider": "google"})
        assert r.status_code == 201
        assert r.json()["client_secret"]

    def test_list_oauth_credentials_excludes_secret(self, client):
        client.post("/integrations/oauth-credentials", headers=MGR, json={"name": "X", "provider": "google"})
        r = client.get("/integrations/oauth-credentials", headers=MGR)
        assert "client_secret" not in r.json()[0]

    def test_revoke_oauth_credential(self, client):
        c = client.post("/integrations/oauth-credentials", headers=MGR, json={"name": "X", "provider": "google"}).json()
        r = client.post(f"/integrations/oauth-credentials/{c['id']}/revoke", headers=MGR)
        assert r.json()["status"] == "revoked"

    def test_rotate_oauth_credential_issues_new_secret(self, client):
        c = client.post("/integrations/oauth-credentials", headers=MGR, json={"name": "X", "provider": "google"}).json()
        r = client.post(f"/integrations/oauth-credentials/{c['id']}/rotate", headers=MGR)
        assert r.json()["client_secret"] != c["client_secret"]

    def test_oauth_credential_manager_only(self, client):
        r = client.post("/integrations/oauth-credentials", headers=MEM, json={"name": "X", "provider": "google"})
        assert r.status_code == 403

    def test_api_keys_reused_from_administration_module(self, client):
        client.post("/governance/api-keys", headers=MGR, json={"name": "K"})
        r = client.get("/integrations/api-keys", headers=MGR)
        assert r.status_code == 200
        assert len(r.json()) == 1


# =====================================================================
# Connector Framework
# =====================================================================
class TestConnectors:
    def test_create_connector_manager_only(self, client):
        r = client.post("/integrations/connectors", headers=MEM, json={"name": "X", "connector_type": "rest"})
        assert r.status_code == 403

    def test_invalid_connector_type_rejected(self, client):
        r = client.post("/integrations/connectors", headers=MGR, json={"name": "X", "connector_type": "bogus"})
        assert r.status_code == 422

    def test_run_connector_success(self, client):
        c = _make_connector(client)
        r = client.post(f"/integrations/connectors/{c['id']}/run", headers=MGR)
        assert r.status_code == 200
        assert r.json()["status"] == "success"

    def test_run_connector_failure(self, client):
        c = _make_connector(client, config={"url": "https://example.com/simulate-fail"})
        r = client.post(f"/integrations/connectors/{c['id']}/run", headers=MGR)
        assert r.json()["status"] == "failed"

    def test_run_inactive_connector_rejected(self, client):
        c = _make_connector(client)
        client.patch(f"/integrations/connectors/{c['id']}", headers=MGR, json={"status": "inactive"})
        r = client.post(f"/integrations/connectors/{c['id']}/run", headers=MGR)
        assert r.status_code == 409

    def test_connector_lifecycle_updates_last_run(self, client):
        c = _make_connector(client)
        client.post(f"/integrations/connectors/{c['id']}/run", headers=MGR)
        runs = client.get(f"/integrations/connectors/{c['id']}/runs", headers=MGR).json()
        assert len(runs) == 1

    def test_delete_connector(self, client):
        c = _make_connector(client)
        assert client.delete(f"/integrations/connectors/{c['id']}", headers=MGR).status_code == 204


# =====================================================================
# Plugin Framework
# =====================================================================
class TestPlugins:
    def test_register_plugin(self, client):
        p = _make_plugin(client)
        assert p["status"] == "enabled"

    def test_register_plugin_invalid_hook_rejected(self, client):
        r = client.post("/integrations/plugins", headers=MGR, json={"name": "X", "execution_hooks": ["bogus_hook"]})
        assert r.status_code == 422

    def test_trigger_hook_executes_matching_enabled_plugins(self, client):
        _make_plugin(client, name="P1", execution_hooks=["after_create"])
        _make_plugin(client, name="P2", execution_hooks=["after_delete"])
        r = client.post("/integrations/plugins/hooks/after_create/trigger", headers=MGR)
        assert len(r.json()) == 1
        assert r.json()[0]["hook_name"] == "after_create"

    def test_disabled_plugin_not_triggered(self, client):
        p = _make_plugin(client)
        client.patch(f"/integrations/plugins/{p['id']}", headers=MGR, json={"status": "disabled"})
        r = client.post("/integrations/plugins/hooks/after_create/trigger", headers=MGR)
        assert r.json() == []

    def test_trigger_invalid_hook_name_rejected(self, client):
        r = client.post("/integrations/plugins/hooks/not_a_real_hook/trigger", headers=MGR)
        assert r.status_code == 422

    def test_list_plugin_executions(self, client):
        _make_plugin(client)
        client.post("/integrations/plugins/hooks/after_create/trigger", headers=MGR)
        r = client.get("/integrations/plugins/executions/list", headers=MGR)
        assert len(r.json()) == 1

    def test_delete_plugin(self, client):
        p = _make_plugin(client)
        assert client.delete(f"/integrations/plugins/{p['id']}", headers=MGR).status_code == 204


# =====================================================================
# Dashboard + Analytics
# =====================================================================
class TestDashboardAndAnalytics:
    def test_dashboard_fields(self, client):
        i = _make_integration(client)
        client.patch(f"/integrations/{i['id']}", headers=MGR, json={"status": "active"})
        _make_connector(client)
        _make_plugin(client)
        r = client.get("/integrations/dashboard/summary", headers=MGR)
        body = r.json()
        assert body["active_integrations"] == 1
        assert body["plugin_status"]["enabled"] == 1
        assert isinstance(body["connector_health"], list)

    def test_analytics_success_and_retry_rate(self, client):
        _make_webhook(client, event_type="ok_event", target_url="https://example.com/ok")
        client.post("/integrations/events/publish", headers=MEM, json={"category": "crm", "event_type": "ok_event"})
        _make_webhook(client, event_type="fail_event", target_url="https://example.com/simulate-fail", retry_policy={"max_attempts": 3, "backoff_seconds": 0})
        client.post("/integrations/events/publish", headers=MEM, json={"category": "crm", "event_type": "fail_event"})
        r = client.get("/integrations/analytics/summary", headers=MGR)
        body = r.json()
        assert body["webhook_success_rate"] == 0.5
        assert body["retry_rate"] == 0.5

    def test_connector_and_plugin_usage_keyed_by_name(self, client):
        c = _make_connector(client, name="Usage Connector")
        client.post(f"/integrations/connectors/{c['id']}/run", headers=MGR)
        p = _make_plugin(client, name="Usage Plugin")
        client.post("/integrations/plugins/hooks/after_create/trigger", headers=MGR)
        r = client.get("/integrations/analytics/summary", headers=MGR).json()
        assert r["connector_usage"]["Usage Connector"] == 1
        assert r["plugin_usage"]["Usage Plugin"] == 1


# =====================================================================
# Cross-phase reuse: Event Bus wired into the existing workflow trigger engine
# =====================================================================
class TestWorkflowTriggerReuse:
    def test_deal_created_workflow_trigger_publishes_event_bus_event(self, client):
        _make_webhook(client, event_type="deal_created", target_url="https://example.com/ok")
        pipeline = _make_pipeline(client)
        open_stage = next(s for s in pipeline["stages"] if s["stage_type"] == "open")
        _make_deal(client, pipeline["id"], open_stage["id"])
        events = client.get("/integrations/events", headers=MGR, params={"category": "crm"}).json()
        assert events["total"] >= 1
        assert any(e["event_type"] == "deal_created" for e in events["items"])
        deliveries = client.get("/integrations/webhooks/deliveries/list", headers=MGR).json()
        assert deliveries["total"] == 1
        assert deliveries["items"][0]["status"] == "success"


# =====================================================================
# Backward compatibility
# =====================================================================
class TestBackwardCompatibility:
    def test_existing_workflow_endpoints_unaffected(self, client):
        assert client.get("/workflows", headers=MGR).status_code == 200

    def test_deal_creation_still_works_with_event_bus_hook_active(self, client):
        pipeline = _make_pipeline(client)
        open_stage = next(s for s in pipeline["stages"] if s["stage_type"] == "open")
        r = client.post("/deals", headers=MGR, json={
            "title": "Deal", "company_domain": "acme.com",
            "pipeline_id": pipeline["id"], "stage_id": open_stage["id"],
            "value": 1000.0, "probability": 10,
        })
        assert r.status_code == 201

    def test_existing_governance_endpoints_unaffected(self, client):
        assert client.get("/governance/organizations", headers=MGR).status_code == 200

    def test_existing_ai_endpoints_unaffected(self, client):
        assert client.get("/ai/insights", headers=MGR).status_code == 200

    def test_existing_custom_objects_endpoints_unaffected(self, client):
        assert client.get("/custom-objects", headers=MGR).status_code == 200


# =====================================================================
# Audit remediation: async webhook delivery (http mode) + single-flight tick locking
# =====================================================================
class TestAsyncWebhookDelivery:
    @pytest.fixture()
    def http_client(self, tmp_path):
        app = create_app(Settings(
            database_url=f"sqlite:///{(tmp_path / 'http_integrations.db').as_posix()}",
            log_json=False, dev_auth_bypass=True, webhook_delivery_mode="http",
        ))
        with TestClient(app) as c:
            Base.metadata.create_all(app.state.db.engine)
            yield c

    def test_http_mode_publish_does_not_block_on_network(self, http_client):
        import time
        http_client.post("/integrations/webhooks", headers=MGR, json={
            "name": "W", "event_type": "e", "target_url": "http://does-not-exist.invalid.test/hook",
            "retry_policy": {"max_attempts": 1, "backoff_seconds": 0},
        })
        t0 = time.time()
        r = http_client.post("/integrations/events/publish", headers=MGR, json={"category": "crm", "event_type": "e"})
        elapsed = time.time() - t0
        assert r.status_code == 201
        assert elapsed < 1.0  # a real DNS failure alone typically takes far longer than this

    def test_http_mode_delivery_eventually_reaches_terminal_state(self, http_client):
        import time
        http_client.post("/integrations/webhooks", headers=MGR, json={
            "name": "W", "event_type": "e", "target_url": "http://does-not-exist.invalid.test/hook",
            "retry_policy": {"max_attempts": 1, "backoff_seconds": 0},
        })
        http_client.post("/integrations/events/publish", headers=MGR, json={"category": "crm", "event_type": "e"})
        delivery = None
        for _ in range(50):
            delivery = http_client.get("/integrations/webhooks/deliveries/list", headers=MGR).json()["items"][0]
            if delivery["status"] != "pending":
                break
            time.sleep(0.2)
        assert delivery["status"] == "failed"
        assert delivery["attempt_count"] == 1
        assert delivery["error_detail"]

    def test_mock_mode_unaffected_by_worker_being_active(self, client):
        """The default test client uses mock mode; the worker still starts (lifespan
        always starts it) but must never be used for mock-mode deliveries."""
        _make_webhook(client, event_type="e2", target_url="https://example.com/ok")
        r = client.post("/integrations/events/publish", headers=MEM, json={"category": "crm", "event_type": "e2"})
        assert r.status_code == 201
        delivery = client.get("/integrations/webhooks/deliveries/list", headers=MGR).json()["items"][0]
        assert delivery["status"] == "success"  # synchronous — no polling needed


class TestSingleFlightTickLocking:
    def test_webhook_retry_tick_rejects_concurrent_call(self, client):
        from backend.tick_lock import _locks
        lock = _locks.setdefault("webhook_retry_tick", __import__("threading").Lock())
        assert lock.acquire(blocking=False)
        try:
            r = client.post("/integrations/webhooks/retry-tick", headers=MGR)
            assert r.status_code == 409
        finally:
            lock.release()

    def test_webhook_retry_tick_succeeds_when_not_locked(self, client):
        r = client.post("/integrations/webhooks/retry-tick", headers=MGR)
        assert r.status_code == 200
