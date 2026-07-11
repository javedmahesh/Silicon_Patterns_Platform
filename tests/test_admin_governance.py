"""Enterprise CRM Phase 9: Enterprise Administration, Security & Compliance tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company, UserAuditEvent

MGR = {"X-Dev-Role": "manager"}
MEM = {"X-Dev-Role": "member"}
ADMIN = {"X-Dev-Role": "admin"}


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
        database_url=f"sqlite:///{(tmp_path / 'governance.db').as_posix()}",
        log_json=False, dev_auth_bypass=True,
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _uid(client, headers=MGR) -> int:
    return client.get("/auth/me", headers=headers).json()["id"]


def _make_org(client, **kw):
    payload = {"name": "Silicon Patterns", "slug": "silicon-patterns", **kw}
    return client.post("/governance/organizations", headers=ADMIN, json=payload).json()


# =====================================================================
# Organization Administration
# =====================================================================
class TestOrganizationAdministration:
    def test_create_organization_admin_only(self, client):
        r = client.post("/governance/organizations", headers=MGR, json={"name": "X", "slug": "x"})
        assert r.status_code == 403

    def test_create_organization(self, client):
        o = _make_org(client)
        assert o["id"] > 0
        assert o["slug"] == "silicon-patterns"

    def test_create_duplicate_slug_rejected(self, client):
        _make_org(client)
        r = client.post("/governance/organizations", headers=ADMIN, json={"name": "Y", "slug": "silicon-patterns"})
        assert r.status_code == 409

    def test_list_organizations(self, client):
        _make_org(client)
        r = client.get("/governance/organizations", headers=MGR)
        assert r.json()["total"] == 1

    def test_get_organization(self, client):
        o = _make_org(client)
        r = client.get(f"/governance/organizations/{o['id']}", headers=MGR)
        assert r.status_code == 200

    def test_get_organization_not_found(self, client):
        assert client.get("/governance/organizations/9999", headers=MGR).status_code == 404

    def test_patch_organization_feature_flags(self, client):
        o = _make_org(client)
        r = client.patch(f"/governance/organizations/{o['id']}", headers=ADMIN, json={
            "feature_flags": {"new_ui": True},
        })
        assert r.json()["feature_flags"] == {"new_ui": True}

    def test_patch_organization_admin_only(self, client):
        o = _make_org(client)
        assert client.patch(f"/governance/organizations/{o['id']}", headers=MGR, json={"name": "Y"}).status_code == 403

    def test_create_business_unit(self, client):
        o = _make_org(client)
        r = client.post(f"/governance/organizations/{o['id']}/units", headers=MGR, json={
            "name": "Sales", "unit_type": "business_unit",
        })
        assert r.status_code == 201
        assert r.json()["unit_type"] == "business_unit"

    def test_create_nested_department_and_team(self, client):
        o = _make_org(client)
        bu = client.post(f"/governance/organizations/{o['id']}/units", headers=MGR, json={
            "name": "Sales", "unit_type": "business_unit",
        }).json()
        dept = client.post(f"/governance/organizations/{o['id']}/units", headers=MGR, json={
            "name": "Enterprise Sales", "unit_type": "department", "parent_id": bu["id"],
        }).json()
        assert dept["parent_id"] == bu["id"]
        team = client.post(f"/governance/organizations/{o['id']}/units", headers=MGR, json={
            "name": "West Team", "unit_type": "team", "parent_id": dept["id"],
        }).json()
        assert team["parent_id"] == dept["id"]

    def test_list_units_filter_by_type(self, client):
        o = _make_org(client)
        client.post(f"/governance/organizations/{o['id']}/units", headers=MGR, json={"name": "Sales", "unit_type": "business_unit"})
        client.post(f"/governance/organizations/{o['id']}/units", headers=MGR, json={"name": "Team A", "unit_type": "team"})
        r = client.get(f"/governance/organizations/{o['id']}/units?unit_type=team", headers=MGR)
        assert len(r.json()) == 1

    def test_patch_unit(self, client):
        o = _make_org(client)
        u = client.post(f"/governance/organizations/{o['id']}/units", headers=MGR, json={"name": "Sales", "unit_type": "business_unit"}).json()
        r = client.patch(f"/governance/units/{u['id']}", headers=MGR, json={"name": "Sales EMEA"})
        assert r.json()["name"] == "Sales EMEA"

    def test_delete_unit(self, client):
        o = _make_org(client)
        u = client.post(f"/governance/organizations/{o['id']}/units", headers=MGR, json={"name": "Sales", "unit_type": "business_unit"}).json()
        assert client.delete(f"/governance/units/{u['id']}", headers=MGR).status_code == 204

    def test_add_and_list_unit_members(self, client):
        o = _make_org(client)
        uid = _uid(client, MGR)
        u = client.post(f"/governance/organizations/{o['id']}/units", headers=MGR, json={"name": "Team A", "unit_type": "team"}).json()
        r = client.post(f"/governance/units/{u['id']}/members", headers=MGR, json={"user_id": uid, "role": "lead"})
        assert r.status_code == 201
        members = client.get(f"/governance/units/{u['id']}/members", headers=MGR).json()
        assert len(members) == 1
        assert members[0]["role"] == "lead"

    def test_member_count_reflected_in_unit_listing(self, client):
        o = _make_org(client)
        uid = _uid(client, MGR)
        u = client.post(f"/governance/organizations/{o['id']}/units", headers=MGR, json={"name": "Team A", "unit_type": "team"}).json()
        client.post(f"/governance/units/{u['id']}/members", headers=MGR, json={"user_id": uid})
        units = client.get(f"/governance/organizations/{o['id']}/units", headers=MGR).json()
        assert units[0]["member_count"] == 1

    def test_duplicate_membership_rejected(self, client):
        o = _make_org(client)
        uid = _uid(client, MGR)
        u = client.post(f"/governance/organizations/{o['id']}/units", headers=MGR, json={"name": "Team A", "unit_type": "team"}).json()
        client.post(f"/governance/units/{u['id']}/members", headers=MGR, json={"user_id": uid})
        r = client.post(f"/governance/units/{u['id']}/members", headers=MGR, json={"user_id": uid})
        assert r.status_code == 409

    def test_remove_member(self, client):
        o = _make_org(client)
        uid = _uid(client, MGR)
        u = client.post(f"/governance/organizations/{o['id']}/units", headers=MGR, json={"name": "Team A", "unit_type": "team"}).json()
        m = client.post(f"/governance/units/{u['id']}/members", headers=MGR, json={"user_id": uid}).json()
        assert client.delete(f"/governance/units/members/{m['id']}", headers=MGR).status_code == 204


# =====================================================================
# System Configuration
# =====================================================================
class TestSystemConfiguration:
    def test_upsert_setting(self, client):
        r = client.put("/governance/settings", headers=MGR, json={
            "category": "workflow", "key": "max_actions_per_workflow", "value": {"limit": 10},
        })
        assert r.status_code == 200
        assert r.json()["value"] == {"limit": 10}

    def test_upsert_setting_manager_only(self, client):
        r = client.put("/governance/settings", headers=MEM, json={"category": "ai", "key": "x", "value": {}})
        assert r.status_code == 403

    def test_upsert_setting_is_idempotent_update(self, client):
        client.put("/governance/settings", headers=MGR, json={"category": "email", "key": "daily_send_cap", "value": {"cap": 100}})
        r = client.put("/governance/settings", headers=MGR, json={"category": "email", "key": "daily_send_cap", "value": {"cap": 200}})
        assert r.json()["value"] == {"cap": 200}
        listing = client.get("/governance/settings?category=email", headers=MGR).json()
        assert len(listing) == 1

    def test_list_settings_filter_by_category(self, client):
        client.put("/governance/settings", headers=MGR, json={"category": "crm", "key": "a", "value": {}})
        client.put("/governance/settings", headers=MGR, json={"category": "ai", "key": "b", "value": {}})
        r = client.get("/governance/settings?category=crm", headers=MGR)
        assert len(r.json()) == 1

    def test_setting_covers_retention_category(self, client):
        r = client.put("/governance/settings", headers=MGR, json={
            "category": "retention", "key": "audit_log_days", "value": {"days": 365},
        })
        assert r.status_code == 200


# =====================================================================
# Security Policies
# =====================================================================
class TestSecurityPolicies:
    def test_upsert_password_policy_admin_only(self, client):
        r = client.put("/governance/security/policies", headers=MGR, json={
            "policy_type": "password", "config": {"min_length": 12},
        })
        assert r.status_code == 403

    def test_upsert_password_policy(self, client):
        r = client.put("/governance/security/policies", headers=ADMIN, json={
            "policy_type": "password", "config": {"min_length": 12, "require_symbol": True},
        })
        assert r.status_code == 200
        assert r.json()["config"]["min_length"] == 12

    def test_upsert_is_idempotent_per_type(self, client):
        client.put("/governance/security/policies", headers=ADMIN, json={"policy_type": "session", "config": {"timeout_minutes": 30}})
        client.put("/governance/security/policies", headers=ADMIN, json={"policy_type": "session", "config": {"timeout_minutes": 60}})
        policies = client.get("/governance/security/policies", headers=MGR).json()
        session_policies = [p for p in policies if p["policy_type"] == "session"]
        assert len(session_policies) == 1
        assert session_policies[0]["config"]["timeout_minutes"] == 60

    def test_mfa_and_ip_allowlist_policies(self, client):
        client.put("/governance/security/policies", headers=ADMIN, json={"policy_type": "mfa", "config": {"required": True}})
        client.put("/governance/security/policies", headers=ADMIN, json={"policy_type": "ip_allowlist", "config": {"cidrs": ["10.0.0.0/8"]}})
        policies = {p["policy_type"]: p for p in client.get("/governance/security/policies", headers=MGR).json()}
        assert policies["mfa"]["config"]["required"] is True
        assert policies["ip_allowlist"]["config"]["cidrs"] == ["10.0.0.0/8"]

    def test_account_lockout_policy(self, client):
        r = client.put("/governance/security/policies", headers=ADMIN, json={
            "policy_type": "account_lockout", "config": {"max_attempts": 5, "lockout_minutes": 15},
        })
        assert r.status_code == 200


# =====================================================================
# Audit Logging
# =====================================================================
class TestAuditLogging:
    def test_configuration_change_creates_audit_event(self, client):
        client.put("/governance/settings", headers=MGR, json={"category": "crm", "key": "a", "value": {}})
        r = client.get("/governance/audit?category=configuration_change", headers=MGR)
        assert r.json()["total"] >= 1

    def test_workflow_change_creates_audit_event(self, client):
        client.post("/workflows", headers=MGR, json={
            "name": "W1", "trigger_event": "deal_created", "conditions": {}, "actions": [],
        })
        r = client.get("/governance/audit?category=workflow_change", headers=MGR)
        assert r.json()["total"] >= 1
        assert "workflow_created" in r.json()["items"][0]["action"]

    def test_record_crud_creates_audit_event(self, client):
        obj = client.post("/custom-objects", headers=MGR, json={"name": "Project", "api_name": "project", "status": "active"}).json()
        client.post(f"/custom-objects/{obj['id']}/records", headers=MGR, json={"data": {}})
        r = client.get("/governance/audit?category=record_crud", headers=MGR)
        assert r.json()["total"] >= 1

    def test_ai_action_creates_audit_event(self, client):
        client.post("/ai/insights/generate", headers=MGR)
        r = client.get("/governance/audit?category=ai_action", headers=MGR)
        assert r.json()["total"] >= 1

    def test_authentication_category_reads_legacy_user_audit(self, client):
        with client.app.state.db.sessionmaker() as s:
            s.add(UserAuditEvent(target_email="a@b.com", actor_email="a@b.com", action="login"))
            s.commit()
        r = client.get("/governance/audit?category=authentication", headers=MGR)
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["category"] == "authentication"

    def test_user_administration_category_reads_legacy_user_audit(self, client):
        with client.app.state.db.sessionmaker() as s:
            s.add(UserAuditEvent(target_email="a@b.com", actor_email="admin@b.com", action="role_changed"))
            s.commit()
        r = client.get("/governance/audit?category=user_administration", headers=MGR)
        assert r.json()["total"] == 1

    def test_audit_search(self, client):
        client.post("/workflows", headers=MGR, json={
            "name": "W1", "trigger_event": "deal_created", "conditions": {}, "actions": [],
        })
        r = client.get("/governance/audit?search=workflow_created", headers=MGR)
        assert r.json()["total"] >= 1

    def test_audit_list_manager_only(self, client):
        assert client.get("/governance/audit", headers=MEM).status_code == 403

    def test_api_key_creation_creates_audit_event(self, client):
        client.post("/governance/api-keys", headers=MGR, json={"name": "Key 1"})
        r = client.get("/governance/audit?category=configuration_change", headers=MGR)
        actions = [i["action"] for i in r.json()["items"]]
        assert "api_key_created" in actions


# =====================================================================
# Compliance
# =====================================================================
class TestCompliance:
    def test_create_legal_hold_starts_active(self, client):
        r = client.post("/governance/compliance", headers=MGR, json={
            "record_type": "legal_hold", "entity_type": "deal", "entity_id": "1",
        })
        assert r.status_code == 201
        assert r.json()["status"] == "active"

    def test_create_export_request_starts_pending(self, client):
        r = client.post("/governance/compliance", headers=MGR, json={
            "record_type": "data_export_request", "entity_type": "customer", "entity_id": "1",
        })
        assert r.json()["status"] == "pending"

    def test_create_deletion_request(self, client):
        r = client.post("/governance/compliance", headers=MGR, json={
            "record_type": "data_deletion_request", "entity_type": "customer", "entity_id": "1",
        })
        assert r.status_code == 201

    def test_create_consent_record(self, client):
        r = client.post("/governance/compliance", headers=MGR, json={
            "record_type": "consent", "entity_type": "contact", "entity_id": "1", "detail": {"marketing": True},
        })
        assert r.status_code == 201

    def test_list_compliance_filter_by_type(self, client):
        client.post("/governance/compliance", headers=MGR, json={"record_type": "legal_hold", "entity_type": "deal", "entity_id": "1"})
        client.post("/governance/compliance", headers=MGR, json={"record_type": "consent", "entity_type": "contact", "entity_id": "1"})
        r = client.get("/governance/compliance?record_type=legal_hold", headers=MGR)
        assert r.json()["total"] == 1

    def test_patch_compliance_record_resolves(self, client):
        c = client.post("/governance/compliance", headers=MGR, json={
            "record_type": "data_export_request", "entity_type": "customer", "entity_id": "1",
        }).json()
        r = client.patch(f"/governance/compliance/{c['id']}", headers=MGR, json={"status": "completed"})
        assert r.json()["status"] == "completed"
        assert r.json()["resolved_at"] is not None

    def test_soft_delete_custom_record(self, client):
        obj = client.post("/custom-objects", headers=MGR, json={"name": "Project", "api_name": "project", "status": "active"}).json()
        rec = client.post(f"/custom-objects/{obj['id']}/records", headers=MGR, json={"data": {}}).json()
        r = client.post(f"/governance/compliance/soft-delete/custom_record/{rec['id']}", headers=MGR)
        assert r.status_code == 204
        listing = client.get(f"/custom-objects/{obj['id']}/records", headers=MGR).json()
        assert listing["total"] == 0
        # The record still exists (soft-deleted, not hard-deleted) — GET by id still works.
        assert client.get(f"/custom-objects/{obj['id']}/records/{rec['id']}", headers=MGR).status_code == 200

    def test_soft_delete_unsupported_entity_type(self, client):
        r = client.post("/governance/compliance/soft-delete/deal/1", headers=MGR)
        assert r.status_code == 422


# =====================================================================
# API Keys & Integrations
# =====================================================================
class TestApiKeys:
    def test_create_api_key_returns_raw_key_once(self, client):
        r = client.post("/governance/api-keys", headers=MGR, json={"name": "CI Key", "scopes": ["read"]})
        assert r.status_code == 201
        body = r.json()
        assert body["api_key"].startswith("sp_")
        assert body["key_prefix"] == body["api_key"][:10]
        assert body["status"] == "active"

    def test_list_api_keys_does_not_expose_raw_key(self, client):
        client.post("/governance/api-keys", headers=MGR, json={"name": "CI Key"})
        r = client.get("/governance/api-keys", headers=MGR)
        assert "api_key" not in r.json()[0]
        assert "key_prefix" in r.json()[0]

    def test_revoke_api_key(self, client):
        k = client.post("/governance/api-keys", headers=MGR, json={"name": "CI Key"}).json()
        r = client.post(f"/governance/api-keys/{k['id']}/revoke", headers=MGR)
        assert r.json()["status"] == "revoked"
        assert r.json()["revoked_at"] is not None

    def test_rotate_api_key_issues_new_key(self, client):
        k = client.post("/governance/api-keys", headers=MGR, json={"name": "CI Key"}).json()
        r = client.post(f"/governance/api-keys/{k['id']}/rotate", headers=MGR)
        assert r.status_code == 200
        assert r.json()["api_key"] != k["api_key"]
        old = client.get("/governance/api-keys", headers=MGR).json()
        old_key = next(x for x in old if x["id"] == k["id"])
        assert old_key["status"] == "revoked"

    def test_expiring_api_key(self, client):
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        r = client.post("/governance/api-keys", headers=MGR, json={"name": "Temp Key", "expires_at": expires})
        assert r.json()["expires_at"] is not None


# =====================================================================
# Monitoring & System Health
# =====================================================================
class TestMonitoring:
    def test_system_health_returns_200(self, client):
        r = client.get("/governance/health", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        for key in ("api_usage_total", "workflow_executions", "workflow_success_rate",
                    "queue_status", "scheduler_healthy", "integrations"):
            assert key in body

    def test_system_health_reflects_workflow_executions(self, client):
        client.post("/workflows", headers=MGR, json={
            "name": "W1", "trigger_event": "deal_created", "conditions": {}, "actions": [], "status": "active",
        })
        p = client.post("/pipelines", headers=MGR, json={"name": "P", "stages": [
            {"name": "Open", "stage_type": "open", "stage_order": 1, "probability": 10},
        ]}).json()
        client.post("/deals", headers=MGR, json={
            "title": "D1", "company_domain": "acme.com", "pipeline_id": p["id"], "stage_id": p["stages"][0]["id"],
        })
        r = client.get("/governance/health", headers=MGR)
        assert r.json()["workflow_executions"] >= 1

    def test_integrations_reported(self, client):
        r = client.get("/governance/health", headers=MGR)
        names = {i["name"] for i in r.json()["integrations"]}
        assert "microsoft_auth" in names
        assert "gmail" in names

    def test_queue_status_shape(self, client):
        r = client.get("/governance/health", headers=MGR)
        qs = r.json()["queue_status"]
        for key in ("scheduled", "queued", "sending", "failed"):
            assert key in qs


# =====================================================================
# Administration Dashboard
# =====================================================================
class TestAdminDashboard:
    def test_dashboard_returns_200(self, client):
        r = client.get("/governance/dashboard/summary", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        for key in ("active_users", "total_organizations", "api_usage_total", "security_events_24h",
                    "audit_events_24h", "pending_compliance_requests", "system_health"):
            assert key in body

    def test_dashboard_reflects_organizations(self, client):
        _make_org(client)
        r = client.get("/governance/dashboard/summary", headers=MGR)
        assert r.json()["total_organizations"] == 1

    def test_dashboard_reflects_pending_compliance(self, client):
        client.post("/governance/compliance", headers=MGR, json={
            "record_type": "data_export_request", "entity_type": "customer", "entity_id": "1",
        })
        r = client.get("/governance/dashboard/summary", headers=MGR)
        assert r.json()["pending_compliance_requests"] == 1

    def test_member_can_view_dashboard(self, client):
        assert client.get("/governance/dashboard/summary", headers=MEM).status_code == 200


# =====================================================================
# Administration Analytics
# =====================================================================
class TestAdminAnalytics:
    def test_analytics_returns_200(self, client):
        r = client.get("/governance/analytics/summary", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        for key in ("user_growth_by_period", "login_activity_by_period", "audit_volume_by_category",
                    "api_utilization", "workflow_utilization", "security_events_by_type", "compliance_stats"):
            assert key in body

    def test_audit_volume_by_category(self, client):
        client.put("/governance/settings", headers=MGR, json={"category": "crm", "key": "a", "value": {}})
        r = client.get("/governance/analytics/summary", headers=MGR)
        assert r.json()["audit_volume_by_category"].get("configuration_change", 0) >= 1

    def test_compliance_stats(self, client):
        client.post("/governance/compliance", headers=MGR, json={"record_type": "legal_hold", "entity_type": "deal", "entity_id": "1"})
        r = client.get("/governance/analytics/summary", headers=MGR)
        assert r.json()["compliance_stats"].get("legal_hold", 0) == 1

    def test_api_utilization(self, client):
        client.post("/governance/api-keys", headers=MGR, json={"name": "Key1"})
        r = client.get("/governance/analytics/summary", headers=MGR)
        assert "Key1" in r.json()["api_utilization"]

    def test_workflow_utilization(self, client):
        client.post("/workflows", headers=MGR, json={
            "name": "W1", "trigger_event": "deal_created", "conditions": {}, "actions": [],
        })
        r = client.get("/governance/analytics/summary", headers=MGR)
        assert "total" in r.json()["workflow_utilization"]


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

    def test_ai_dashboard_endpoint(self, client):
        assert client.get("/ai/dashboard/summary", headers=MGR).status_code == 200

    def test_revops_dashboard(self, client):
        assert client.get("/revops/executive-dashboard", headers=MGR).status_code == 200

    def test_cs_accounts_endpoint(self, client):
        assert client.get("/cs/accounts", headers=MGR).status_code == 200

    def test_existing_admin_router_unaffected(self, client):
        assert client.get("/admin/users", headers=ADMIN).status_code == 200

    def test_pipelines_endpoint(self, client):
        assert client.get("/pipelines", headers=MGR).status_code == 200

    def test_team_work_queue(self, client):
        assert client.get("/team/work-queue", headers=MGR).status_code == 200

    def test_custom_record_create_still_works_after_audit_hook(self, client):
        obj = client.post("/custom-objects", headers=MGR, json={"name": "Project", "api_name": "project", "status": "active"}).json()
        r = client.post(f"/custom-objects/{obj['id']}/records", headers=MGR, json={"data": {}})
        assert r.status_code == 201

    def test_workflow_create_still_works_after_audit_hook(self, client):
        r = client.post("/workflows", headers=MGR, json={
            "name": "W1", "trigger_event": "deal_created", "conditions": {}, "actions": [],
        })
        assert r.status_code == 201
