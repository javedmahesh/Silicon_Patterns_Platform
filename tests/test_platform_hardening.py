"""Enterprise CRM Phase 13: Production Deployment, Authentication & Platform Hardening tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company

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
        database_url=f"sqlite:///{(tmp_path / 'platform.db').as_posix()}",
        log_json=False, dev_auth_bypass=True,
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _fake_verify_microsoft(id_token: str, settings: Settings) -> dict:
    return {"email": id_token, "name": "Test User", "oid": f"oid-{id_token}"}


@pytest.fixture(autouse=True)
def _stub_microsoft_verification(monkeypatch):
    from backend import security
    monkeypatch.setattr(security, "verify_microsoft_id_token", _fake_verify_microsoft)


@pytest.fixture()
def prod_client(tmp_path):
    """A client configured as if for production: bypass off, strong JWT secret, and
    Microsoft Entra + the initial administrator bootstrap configured — so
    dev_auth_bypass is genuinely disabled and requests need a real Bearer token."""
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'platform_prod.db').as_posix()}",
        log_json=False, dev_auth_bypass=False,
        jwt_secret="a" * 40,
        allowed_email_domain="siliconpatterns.com",
        cors_origins=["https://app.siliconpatterns.com"],
        rate_limit_per_minute=60,
        bootstrap_admin_email="admin@siliconpatterns.com",
        microsoft_tenant_id="test-tenant", microsoft_client_id="test-client",
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        yield c, app


# =====================================================================
# Production Authentication
# =====================================================================
class TestProductionAuthentication:
    def test_refresh_issues_new_token(self, client):
        r = client.post("/auth/refresh", headers=MGR)
        assert r.status_code == 200
        assert r.json()["token"]
        assert r.json()["user"]["role"] == "manager"

    def test_logout_returns_ok(self, client):
        r = client.post("/auth/logout", headers=MGR)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_refresh_and_logout_are_audited(self, client):
        client.post("/auth/refresh", headers=MGR)
        client.post("/auth/logout", headers=MGR)
        r = client.get("/admin/users/audit", headers=ADMIN)
        actions = {e["action"] for e in r.json()}
        assert "session_refreshed" in actions
        assert "logout" in actions

    def test_me_endpoint_unaffected(self, client):
        r = client.get("/auth/me", headers=MGR)
        assert r.status_code == 200
        assert r.json()["role"] == "manager"

    def test_domain_restriction_still_only_siliconpatterns(self, prod_client):
        c, app = prod_client
        r = c.post("/auth/microsoft", json={"id_token": "someone@gmail.com"})
        assert r.status_code == 403
        assert r.json()["detail"]["code"] == "forbidden_domain"

    def test_valid_domain_first_sign_in_is_pending(self, prod_client):
        c, app = prod_client
        r = c.post("/auth/microsoft", json={"id_token": "newperson@siliconpatterns.com"})
        assert r.status_code == 403
        assert r.json()["detail"]["code"] == "account_pending"

    def test_bypass_disabled_requires_real_token(self, prod_client):
        c, app = prod_client
        r = c.get("/auth/me")
        assert r.status_code == 401


# =====================================================================
# User Administration (existing module — Phase 13 reuses it, verify unaffected)
# =====================================================================
class TestUserAdministration:
    def test_list_users_still_works(self, client):
        r = client.get("/admin/users", headers=ADMIN)
        assert r.status_code == 200

    def test_user_audit_history_still_works(self, client):
        client.post("/auth/refresh", headers=MGR)
        r = client.get("/admin/users/audit", headers=ADMIN)
        assert r.status_code == 200
        assert len(r.json()) >= 1


# =====================================================================
# Production Configuration
# =====================================================================
class TestProductionConfiguration:
    def test_readiness_not_ready_in_dev(self, client):
        r = client.get("/platform/config/readiness", headers=MGR)
        assert r.status_code == 200
        assert r.json()["ready"] is False

    def test_readiness_ready_with_prod_settings(self, prod_client):
        # prod_client disables the dev bypass (as real prod would); sign in as the
        # bootstrap admin via the real endpoint (the autouse fixture stubs Microsoft
        # token verification) so an active super_admin genuinely exists, the same way
        # a real deploy satisfies this check on its first sign-in.
        from backend import platform_service
        c, app = prod_client
        r = c.post("/auth/microsoft", json={"id_token": "admin@siliconpatterns.com"})
        assert r.status_code == 200 and r.json()["user"]["role"] == "super_admin"
        with app.state.db.sessionmaker() as session:
            result = platform_service.production_readiness(app.state.settings, session)
        assert result["ready"] is True
        assert all(result["checks"][k] for k in result["critical_checks"])

    def test_readiness_not_ready_without_active_super_admin_yet(self, prod_client):
        from backend import platform_service
        c, app = prod_client
        with app.state.db.sessionmaker() as session:
            result = platform_service.production_readiness(app.state.settings, session)
        assert result["ready"] is False
        assert result["checks"]["active_super_admin_exists"] is False

    def test_readiness_manager_only(self, client):
        r = client.get("/platform/config/readiness", headers=MEM)
        assert r.status_code == 403

    def test_feature_flags_reuse_governance_settings(self, client):
        client.put("/governance/settings", headers=MGR, json={"category": "platform", "key": "new_ui", "value": {"enabled": True}})
        r = client.get("/governance/settings", headers=MGR, params={"category": "platform"})
        assert r.json()[0]["key"] == "new_ui"
        assert r.json()[0]["value"]["enabled"] is True


# =====================================================================
# Operational Health
# =====================================================================
class TestOperationalHealth:
    def test_liveness_probe(self, client):
        r = client.get("/health/live")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_readiness_probe(self, client):
        r = client.get("/health/ready")
        assert r.status_code == 200
        assert r.json()["database"] == "ok"

    def test_liveness_and_readiness_unauthenticated(self, prod_client):
        c, app = prod_client
        assert c.get("/health/live").status_code == 200
        assert c.get("/health/ready").status_code == 200

    def test_operational_health_sections(self, client):
        r = client.get("/platform/health", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        for section in ("application", "database", "scheduler", "integrations", "authentication", "cache"):
            assert section in body

    def test_operational_health_manager_only(self, client):
        assert client.get("/platform/health", headers=MEM).status_code == 403

    def test_operational_health_reflects_bypass_state(self, client):
        r = client.get("/platform/health", headers=MGR)
        assert r.json()["authentication"]["bypass_active"] is True


# =====================================================================
# Production Dashboard
# =====================================================================
class TestProductionDashboard:
    def test_dashboard_fields(self, client):
        r = client.get("/platform/dashboard", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        for field in ("system_status", "active_sessions", "authentication_status", "service_health", "queue_health", "integration_status"):
            assert field in body

    def test_system_status_ok_when_db_healthy(self, client):
        r = client.get("/platform/dashboard", headers=MGR)
        assert r.json()["system_status"] == "ok"


# =====================================================================
# Final Platform Validation
# =====================================================================
class TestFinalPlatformValidation:
    def test_validate_all_modules_ok(self, client):
        r = client.get("/platform/validate", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert body["all_ok"] is False  # readiness fails in dev (no active super_admin / Microsoft config), by design
        assert all(m["ok"] for m in body["modules"].values())

    def test_validate_covers_expected_modules(self, client):
        r = client.get("/platform/validate", headers=MGR)
        modules = r.json()["modules"]
        for name in ("crm_companies", "workflows", "custom_objects", "ai_insights", "integrations", "search_knowledge", "business_intelligence"):
            assert name in modules

    def test_validate_ready_true_with_prod_settings(self, prod_client):
        from backend import platform_service
        c, app = prod_client
        c.post("/auth/microsoft", json={"id_token": "admin@siliconpatterns.com"})
        with app.state.db.sessionmaker() as session:
            result = platform_service.platform_validate(session, None, app.state.settings)
        assert result["production_readiness"]["ready"] is True


# =====================================================================
# Backward compatibility (spot check across all prior phases)
# =====================================================================
class TestBackwardCompatibility:
    def test_existing_health_endpoint_unaffected(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_existing_companies_endpoint_unaffected(self, client):
        assert client.get("/companies", headers=MGR).status_code == 200

    def test_existing_workflows_endpoint_unaffected(self, client):
        assert client.get("/workflows", headers=MGR).status_code == 200

    def test_existing_governance_endpoint_unaffected(self, client):
        assert client.get("/governance/organizations", headers=MGR).status_code == 200

    def test_existing_integrations_endpoint_unaffected(self, client):
        assert client.get("/integrations", headers=MGR).status_code == 200

    def test_existing_search_endpoint_unaffected(self, client):
        assert client.get("/search", headers=MGR, params={"q": "acme"}).status_code == 200

    def test_existing_bi_endpoint_unaffected(self, client):
        assert client.get("/bi/kpis", headers=MGR).status_code == 200
