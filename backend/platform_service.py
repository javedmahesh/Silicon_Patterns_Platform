"""Enterprise CRM Phase 13: Production Deployment, Authentication & Platform Hardening.

Production authentication: Microsoft Entra ID (backend/security.py's
verify_microsoft_id_token, backend/services.py's login_with_microsoft) — RBAC +
app-issued JWTs on top of an external identity provider.

Everything else in this module is intentionally thin: operational health and the
production dashboard are compositions over admin_service.system_health /
admin_service.admin_dashboard / integration_service.integration_dashboard — Phase 9
and Phase 10's own dashboards — not new computation. Feature flags reuse the existing
Phase 9 SystemSetting store (category="platform") rather than new infrastructure.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend import admin_service
from backend import cache
from backend import integration_service
from backend import platform_repo as repo
from backend import repositories
from backend.config import Settings, get_settings
from backend.security import _bypass_on
from master_db.models import (
    AiInsight,
    Company,
    Connector,
    CrmDeal,
    CustomObject,
    Integration,
    KbArticle,
    Kpi,
    SavedSearch,
    User,
    Workflow,
)


# ================================================================== 3. production configuration
_CRITICAL_CHECKS = (
    "jwt_secret_is_strong", "dev_auth_bypass_disabled",
    "microsoft_auth_configured", "active_super_admin_exists",
)


def production_readiness(settings: Settings | None = None, session: Session | None = None) -> dict:
    """`session` is optional (main.py's startup call has one available a line later via
    app.state.db.sessionmaker(); pass it through) so the DB-dependent access-governance
    checks can run — without one, they fail closed (reported False, not skipped)
    rather than silently passing."""
    settings = settings or get_settings()
    checks = {
        "jwt_secret_is_strong": settings.jwt_secret != "dev-insecure-change-me" and len(settings.jwt_secret) >= 32,
        "dev_auth_bypass_disabled": not settings.dev_auth_bypass,
        "allowed_domain_configured": bool(settings.allowed_email_domain),
        "cors_not_wildcard": settings.cors_origins != ["*"],
        "rate_limit_configured": settings.rate_limit_per_minute > 0,
        "non_default_database": "sqlite" not in settings.database_url.lower(),
        # Restates the actual runtime bypass decision (security._bypass_on already forces
        # this False whenever environment=production) — a direct, single-source-of-truth
        # signal that no fail-open path is reachable, not just an inference from the
        # individual checks above.
        "no_fail_open_bypass": not _bypass_on(settings),
        # Without both, no one could ever sign in in production (there's no other
        # identity path there) — see main.py's matching startup fail-closed check.
        "microsoft_auth_configured": bool(settings.microsoft_tenant_id and settings.microsoft_client_id),
        "active_super_admin_exists": session is not None and repositories.count_active_super_admins(session) > 0,
    }
    return {
        "ready": all(checks[c] for c in _CRITICAL_CHECKS),
        "checks": checks,
        "critical_checks": list(_CRITICAL_CHECKS),
        "environment": settings.environment,
    }


def is_feature_enabled(session: Session, key: str, *, default: bool = False) -> bool:
    """Feature-flag read helper for other modules — writes go through the existing
    PUT /governance/settings (category='platform')."""
    value = admin_service.get_setting_cached(session, "platform", key)
    if value is None:
        return default
    return bool(value.get("enabled", default))


# ================================================================== 6. operational health
def operational_health(session: Session, user, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    sys_health = admin_service.system_health(session, user)
    integ_dash = integration_service.integration_dashboard(session, user)
    db_ok = True
    try:
        session.execute(select(func.count()).select_from(User))
    except Exception:
        db_ok = False
    return {
        "application": {"status": "ok", "app": settings.app_name, "version": settings.app_version},
        "database": {"status": "ok" if db_ok else "error", "pool_size": settings.db_pool_size, "pool_recycle_seconds": settings.db_pool_recycle},
        "scheduler": {"healthy": sys_health.scheduler_healthy, "workflow_executions": sys_health.workflow_executions, "workflow_success_rate": sys_health.workflow_success_rate},
        "integrations": {"active_integrations": integ_dash.active_integrations, "webhook_deliveries_total": integ_dash.webhook_deliveries_total, "failed_deliveries": integ_dash.failed_deliveries},
        "authentication": {
            "bypass_active": _bypass_on(settings),
            "jwt_secret_is_strong": settings.jwt_secret != "dev-insecure-change-me" and len(settings.jwt_secret) >= 32,
            "microsoft_auth_configured": bool(settings.microsoft_tenant_id and settings.microsoft_client_id),
            "allowed_domain": settings.allowed_email_domain,
            "pending_approvals": repositories.count_pending_users(session),
            "active_super_admins": repositories.count_active_super_admins(session),
        },
        "cache": {"response_cache_entries": cache.size()},
    }


# ================================================================== 8. production dashboard
def production_dashboard(session: Session, user, settings: Settings | None = None) -> dict:
    health = operational_health(session, user, settings)
    admin_dash = admin_service.admin_dashboard(session, user)
    integ_dash = integration_service.integration_dashboard(session, user)
    return {
        "system_status": "ok" if health["database"]["status"] == "ok" else "degraded",
        "active_sessions": repo.count_recent_active_sessions(session),
        "authentication_status": health["authentication"],
        "service_health": health,
        "queue_health": admin_dash.system_health.queue_status.model_dump(),
        "integration_status": {
            "active_integrations": integ_dash.active_integrations,
            "webhook_deliveries_total": integ_dash.webhook_deliveries_total,
            "failed_deliveries": integ_dash.failed_deliveries,
            "plugin_status": integ_dash.plugin_status,
        },
    }


# ================================================================== 9. final platform validation
# One representative table per module — a real post-deploy reachability smoke test,
# not a re-implementation of the test suite.
_VALIDATION_MODELS = {
    "crm_companies": Company,
    "authentication_rbac": User,
    "crm_deals": CrmDeal,
    "workflows": Workflow,
    "custom_objects": CustomObject,
    "ai_insights": AiInsight,
    "integrations": Integration,
    "connectors": Connector,
    "search_knowledge": KbArticle,
    "saved_searches": SavedSearch,
    "business_intelligence": Kpi,
}


def platform_validate(session: Session, user, settings: Settings | None = None) -> dict:
    modules = {}
    for name, model in _VALIDATION_MODELS.items():
        try:
            count = session.scalar(select(func.count()).select_from(model))
            modules[name] = {"ok": True, "row_count": count}
        except Exception as exc:  # noqa: BLE001 - a broken module must report, not crash the smoke test
            modules[name] = {"ok": False, "error": str(exc)[:200]}
    readiness = production_readiness(settings, session)
    return {
        "all_ok": all(m["ok"] for m in modules.values()) and readiness["ready"],
        "modules": modules,
        "production_readiness": readiness,
    }
