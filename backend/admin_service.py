"""Enterprise CRM Phase 9: Enterprise Administration, Security & Compliance.

Reuses existing infra wherever a spec bullet is really a read-only view over data another
phase already owns: workflow_repo (execution/SLA stats), outreach_repo (message queue
status), backend.config.Settings (integration configuration), and the existing
user_audit_events table (Phase 0 account-lifecycle log) for the authentication /
user_administration audit categories — see admin_repo.list_user_audit_as_events.
"""
from __future__ import annotations

import hashlib
import secrets
import time
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import admin_repo as repo
from backend import outreach_repo
from backend import workflow_repo
from backend.schemas import (
    AdminAnalyticsOut,
    AdminDashboardOut,
    ApiKeyCreate,
    ApiKeyCreatedOut,
    ApiKeyOut,
    AuditEventOut,
    ComplianceRecordCreate,
    ComplianceRecordOut,
    IntegrationStatusOut,
    OrganizationCreate,
    OrganizationOut,
    OrganizationPatch,
    OrgUnitCreate,
    OrgUnitMemberIn,
    OrgUnitMemberOut,
    OrgUnitOut,
    OrgUnitPatch,
    Page,
    QueueStatusOut,
    SecurityPolicyIn,
    SecurityPolicyOut,
    SystemHealthOut,
    SystemSettingIn,
    SystemSettingOut,
)
from master_db.models import User

from backend.timeutil import utc as _utc, utcnow as _utcnow


def _is_manager(user) -> bool:
    return getattr(user, "role", "member") in ("admin", "manager")


def _is_admin(user) -> bool:
    return getattr(user, "role", "member") == "admin"


def _require_manager(user) -> None:
    if not _is_manager(user):
        raise HTTPException(403, "manager or admin required")


def _require_admin(user) -> None:
    if not _is_admin(user):
        raise HTTPException(403, "admin required")


def _load_user_emails(session: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    from sqlalchemy import select
    rows = session.scalars(select(User).where(User.id.in_(ids))).all()
    return {u.id: u.email for u in rows}


# ================================================================== audit logging (shared utility)
def log_audit_event(
    session: Session, *, category: str, action: str, actor=None,
    entity_type: str = "", entity_id: str = "", detail: dict | None = None, ip_address: str = "",
) -> None:
    """Reusable across every other Phase's mutation code. Does not commit — caller owns the transaction."""
    repo.create_audit_event(
        session, category=category, action=action,
        actor_id=getattr(actor, "id", None), actor_email=getattr(actor, "email", ""),
        entity_type=entity_type, entity_id=str(entity_id), detail=detail or {}, ip_address=ip_address,
    )


def _audit_out(e) -> AuditEventOut:
    return AuditEventOut(
        id=e.id, category=e.category, action=e.action, actor_id=e.actor_id, actor_email=e.actor_email,
        entity_type=e.entity_type, entity_id=e.entity_id, detail=e.detail or {},
        ip_address=e.ip_address, created_at=_utc(e.created_at),
    )


def _user_audit_out(e) -> AuditEventOut:
    category = "authentication" if e.action in ("registered", "login") else "user_administration"
    return AuditEventOut(
        id=e.id, category=category, action=e.action, actor_id=e.actor_user_id, actor_email=e.actor_email,
        entity_type="user", entity_id=str(e.target_user_id or ""), detail={"target_email": e.target_email},
        ip_address="", created_at=_utc(e.created_at),
    )


def list_audit_events(session: Session, user, *, category: str | None = None, search: str | None = None, limit: int = 50, offset: int = 0) -> Page:
    """Unified, filterable audit view. `category=authentication|user_administration` reads the
    existing Phase-0 user_audit_events log; every other category (or no filter) reads the
    native Phase-9 audit_events table. Kept as two separate sources rather than merged so
    pagination stays a single indexed query against whichever table is being filtered."""
    _require_manager(user)
    if category in ("authentication", "user_administration"):
        rows, total = repo.list_user_audit_as_events(session, category=category, limit=limit, offset=offset)
        items = [_user_audit_out(e) for e in rows]
        return Page.build(items, total, max(1, offset // limit + 1) if limit else 1, limit)
    rows, total = repo.list_audit_events(session, category=category, search=search, limit=limit, offset=offset)
    return Page.build([_audit_out(e) for e in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


# ================================================================== organizations
def _org_out(o) -> OrganizationOut:
    return OrganizationOut(
        id=o.id, name=o.name, slug=o.slug, industry=o.industry, size=o.size,
        settings=o.settings or {}, feature_flags=o.feature_flags or {},
        created_at=_utc(o.created_at), updated_at=_utc(o.updated_at),
    )


def create_organization(session: Session, data: OrganizationCreate, user) -> OrganizationOut:
    _require_admin(user)
    if repo.get_organization_by_slug(session, data.slug):
        raise HTTPException(409, "slug already in use")
    o = repo.create_organization(
        session, name=data.name, slug=data.slug, industry=data.industry, size=data.size,
        settings=data.settings, feature_flags=data.feature_flags,
    )
    log_audit_event(session, category="configuration_change", action="organization_created", actor=user, entity_type="organization", entity_id=o.id)
    session.commit()
    return _org_out(o)


def list_organizations(session: Session, user, *, limit: int = 50, offset: int = 0) -> Page:
    rows, total = repo.list_organizations(session, limit=limit, offset=offset)
    return Page.build([_org_out(o) for o in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


def get_organization(session: Session, org_id: int, user) -> OrganizationOut:
    o = repo.get_organization(session, org_id)
    if not o:
        raise HTTPException(404, "organization not found")
    return _org_out(o)


def patch_organization(session: Session, org_id: int, data: OrganizationPatch, user) -> OrganizationOut:
    _require_admin(user)
    o = repo.get_organization(session, org_id)
    if not o:
        raise HTTPException(404, "organization not found")
    for field in ("name", "industry", "size", "settings", "feature_flags"):
        val = getattr(data, field)
        if val is not None:
            setattr(o, field, val)
    log_audit_event(session, category="configuration_change", action="organization_updated", actor=user, entity_type="organization", entity_id=org_id)
    session.commit()
    return _org_out(o)


# ================================================================== org units
def _unit_out(u, member_count: int = 0) -> OrgUnitOut:
    return OrgUnitOut(
        id=u.id, organization_id=u.organization_id, name=u.name, unit_type=u.unit_type,
        parent_id=u.parent_id, lead_user_id=u.lead_user_id, member_count=member_count,
        created_at=_utc(u.created_at), updated_at=_utc(u.updated_at),
    )


def create_unit(session: Session, org_id: int, data: OrgUnitCreate, user) -> OrgUnitOut:
    _require_manager(user)
    if not repo.get_organization(session, org_id):
        raise HTTPException(404, "organization not found")
    u = repo.create_unit(
        session, organization_id=org_id, name=data.name, unit_type=data.unit_type,
        parent_id=data.parent_id, lead_user_id=data.lead_user_id,
    )
    session.commit()
    return _unit_out(u)


def list_units(session: Session, org_id: int, user, *, unit_type: str | None = None) -> list[OrgUnitOut]:
    units = repo.list_units(session, org_id, unit_type=unit_type)
    counts = repo.member_counts(session, [u.id for u in units])
    return [_unit_out(u, counts.get(u.id, 0)) for u in units]


def patch_unit(session: Session, unit_id: int, data: OrgUnitPatch, user) -> OrgUnitOut:
    _require_manager(user)
    u = repo.get_unit(session, unit_id)
    if not u:
        raise HTTPException(404, "unit not found")
    for field in ("name", "parent_id", "lead_user_id"):
        val = getattr(data, field)
        if val is not None:
            setattr(u, field, val)
    session.commit()
    counts = repo.member_counts(session, [u.id])
    return _unit_out(u, counts.get(u.id, 0))


def delete_unit(session: Session, unit_id: int, user) -> None:
    _require_manager(user)
    if not repo.delete_unit(session, unit_id):
        raise HTTPException(404, "unit not found")
    session.commit()


def add_member(session: Session, unit_id: int, data: OrgUnitMemberIn, user) -> OrgUnitMemberOut:
    _require_manager(user)
    if not repo.get_unit(session, unit_id):
        raise HTTPException(404, "unit not found")
    if repo.get_member(session, unit_id, data.user_id):
        raise HTTPException(409, "user already a member of this unit")
    m = repo.add_member(session, unit_id=unit_id, user_id=data.user_id, role=data.role)
    session.commit()
    email_map = _load_user_emails(session, [data.user_id])
    return OrgUnitMemberOut(id=m.id, unit_id=m.unit_id, user_id=m.user_id, user_email=email_map.get(m.user_id, ""), role=m.role, created_at=_utc(m.created_at))


def list_members(session: Session, unit_id: int, user) -> list[OrgUnitMemberOut]:
    if not repo.get_unit(session, unit_id):
        raise HTTPException(404, "unit not found")
    members = repo.list_members(session, unit_id)
    email_map = _load_user_emails(session, [m.user_id for m in members])
    return [OrgUnitMemberOut(id=m.id, unit_id=m.unit_id, user_id=m.user_id, user_email=email_map.get(m.user_id, ""), role=m.role, created_at=_utc(m.created_at)) for m in members]


def remove_member(session: Session, member_id: int, user) -> None:
    _require_manager(user)
    if not repo.remove_member(session, member_id):
        raise HTTPException(404, "member not found")
    session.commit()


# ================================================================== system settings
def _setting_out(s) -> SystemSettingOut:
    return SystemSettingOut(id=s.id, category=s.category, key=s.key, value=s.value or {}, updated_by=s.updated_by, updated_at=_utc(s.updated_at))


def upsert_setting(session: Session, data: SystemSettingIn, user) -> SystemSettingOut:
    _require_manager(user)
    s = repo.upsert_setting(session, data.category, data.key, data.value, user.id)
    log_audit_event(session, category="configuration_change", action="setting_updated", actor=user, entity_type="setting", entity_id=f"{data.category}.{data.key}", detail={"value": data.value})
    session.commit()
    invalidate_config_cache()
    return _setting_out(s)


def list_settings(session: Session, user, *, category: str | None = None) -> list[SystemSettingOut]:
    return [_setting_out(s) for s in repo.list_settings(session, category=category)]


_CONFIG_TTL_SECONDS = 60
_config_cache: dict[str, tuple[float, dict]] = {}


def _config_cache_key(session: Session) -> str:
    try:
        return str(session.get_bind().url)
    except Exception:
        return "default"


def get_setting_cached(session: Session, category: str, key: str) -> dict | None:
    """Cache-fronted read for high-frequency config lookups elsewhere in the platform."""
    cache_key = f"{_config_cache_key(session)}::{category}.{key}"
    cached = _config_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < _CONFIG_TTL_SECONDS:
        return cached[1]
    s = repo.get_setting(session, category, key)
    value = s.value if s else None
    _config_cache[cache_key] = (time.monotonic(), value)
    return value


def invalidate_config_cache() -> None:
    _config_cache.clear()


# ================================================================== security policies
def _policy_out(p) -> SecurityPolicyOut:
    return SecurityPolicyOut(id=p.id, policy_type=p.policy_type, config=p.config or {}, is_enabled=p.is_enabled, updated_by=p.updated_by, updated_at=_utc(p.updated_at))


def upsert_security_policy(session: Session, data: SecurityPolicyIn, user) -> SecurityPolicyOut:
    _require_admin(user)
    p = repo.upsert_policy(session, data.policy_type, data.config, data.is_enabled, user.id)
    log_audit_event(session, category="configuration_change", action="security_policy_updated", actor=user, entity_type="security_policy", entity_id=data.policy_type, detail={"config": data.config})
    session.commit()
    return _policy_out(p)


def list_security_policies(session: Session, user) -> list[SecurityPolicyOut]:
    return [_policy_out(p) for p in repo.list_policies(session)]


# ================================================================== compliance
def _compliance_out(c) -> ComplianceRecordOut:
    return ComplianceRecordOut(
        id=c.id, record_type=c.record_type, entity_type=c.entity_type, entity_id=c.entity_id,
        status=c.status, requested_by=c.requested_by, detail=c.detail or {},
        requested_at=_utc(c.requested_at), resolved_at=_utc(c.resolved_at),
    )


def create_compliance_record(session: Session, data: ComplianceRecordCreate, user) -> ComplianceRecordOut:
    initial_status = "active" if data.record_type == "legal_hold" else "pending"
    c = repo.create_compliance_record(
        session, record_type=data.record_type, entity_type=data.entity_type, entity_id=data.entity_id,
        status=initial_status, requested_by=user.id, detail=data.detail,
    )
    log_audit_event(
        session, category="data_export" if data.record_type == "data_export_request" else "configuration_change",
        action=f"{data.record_type}_created", actor=user, entity_type=data.entity_type, entity_id=data.entity_id,
    )
    session.commit()
    return _compliance_out(c)


def list_compliance_records(session: Session, user, *, record_type: str | None = None, status: str | None = None, limit: int = 50, offset: int = 0) -> Page:
    rows, total = repo.list_compliance_records(session, record_type=record_type, status=status, limit=limit, offset=offset)
    return Page.build([_compliance_out(c) for c in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


def patch_compliance_record(session: Session, record_id: int, new_status: str, user) -> ComplianceRecordOut:
    _require_manager(user)
    c = repo.get_compliance_record(session, record_id)
    if not c:
        raise HTTPException(404, "compliance record not found")
    if new_status not in ("pending", "active", "completed", "rejected"):
        raise HTTPException(422, "invalid status")
    c.status = new_status
    if new_status in ("completed", "rejected"):
        c.resolved_at = _utcnow()
    log_audit_event(session, category="configuration_change", action=f"{c.record_type}_{new_status}", actor=user, entity_type=c.entity_type, entity_id=c.entity_id)
    session.commit()
    return _compliance_out(c)


def apply_soft_delete(session: Session, model_cls, record_id: int, deleted_flag_field: str = "is_deleted") -> None:
    """Reusable soft-delete utility: sets a boolean flag instead of DELETE, if the model has one.

    ponytail: opt-in helper — most existing models don't carry a soft-delete flag column;
    this is available for any model (existing or future) that does, without requiring a
    schema change on every table just to support Phase 9's compliance bullet.
    """
    row = session.get(model_cls, record_id)
    if not row:
        raise HTTPException(404, "record not found")
    if not hasattr(row, deleted_flag_field):
        raise HTTPException(422, f"{model_cls.__name__} does not support soft delete")
    setattr(row, deleted_flag_field, True)
    session.commit()


# entity_type string -> model class, for the soft-delete API. Extend as more models opt in.
def _soft_delete_registry():
    from master_db.models import CustomRecord
    return {"custom_record": CustomRecord}


def soft_delete_entity(session: Session, entity_type: str, entity_id: int, user) -> None:
    _require_manager(user)
    model_cls = _soft_delete_registry().get(entity_type)
    if not model_cls:
        raise HTTPException(422, f"soft delete is not supported for entity_type: {entity_type}")
    apply_soft_delete(session, model_cls, entity_id)
    log_audit_event(session, category="record_crud", action="soft_deleted", actor=user, entity_type=entity_type, entity_id=entity_id)
    session.commit()


# ================================================================== API keys
def create_api_key(session: Session, data: ApiKeyCreate, user) -> ApiKeyCreatedOut:
    raw_key = f"sp_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    k = repo.create_api_key(
        session, name=data.name, key_hash=key_hash, key_prefix=raw_key[:10],
        scopes=data.scopes, owner_id=user.id, expires_at=data.expires_at,
    )
    log_audit_event(session, category="configuration_change", action="api_key_created", actor=user, entity_type="api_key", entity_id=k.id, detail={"scopes": data.scopes})
    session.commit()
    return ApiKeyCreatedOut(
        id=k.id, name=k.name, api_key=raw_key, key_prefix=k.key_prefix, scopes=k.scopes or [],
        status=k.status, expires_at=_utc(k.expires_at), created_at=_utc(k.created_at),
    )


def _api_key_out(k) -> ApiKeyOut:
    return ApiKeyOut(
        id=k.id, name=k.name, key_prefix=k.key_prefix, scopes=k.scopes or [], owner_id=k.owner_id,
        status=k.status, request_count=k.request_count, expires_at=_utc(k.expires_at),
        last_used_at=_utc(k.last_used_at), created_at=_utc(k.created_at), revoked_at=_utc(k.revoked_at),
    )


def list_api_keys(session: Session, user, *, owner_id: int | None = None) -> list[ApiKeyOut]:
    return [_api_key_out(k) for k in repo.list_api_keys(session, owner_id=owner_id)]


def revoke_api_key(session: Session, key_id: int, user) -> ApiKeyOut:
    k = repo.get_api_key(session, key_id)
    if not k:
        raise HTTPException(404, "api key not found")
    if k.owner_id != user.id and not _is_manager(user):
        raise HTTPException(403, "only the owner or a manager may revoke this key")
    k.status = "revoked"
    k.revoked_at = _utcnow()
    log_audit_event(session, category="configuration_change", action="api_key_revoked", actor=user, entity_type="api_key", entity_id=key_id)
    session.commit()
    return _api_key_out(k)


def rotate_api_key(session: Session, key_id: int, user) -> ApiKeyCreatedOut:
    old = repo.get_api_key(session, key_id)
    if not old:
        raise HTTPException(404, "api key not found")
    if old.owner_id != user.id and not _is_manager(user):
        raise HTTPException(403, "only the owner or a manager may rotate this key")
    old.status = "revoked"
    old.revoked_at = _utcnow()
    raw_key = f"sp_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    new = repo.create_api_key(
        session, name=old.name, key_hash=key_hash, key_prefix=raw_key[:10],
        scopes=old.scopes, owner_id=old.owner_id, expires_at=old.expires_at,
    )
    log_audit_event(session, category="configuration_change", action="api_key_rotated", actor=user, entity_type="api_key", entity_id=new.id, detail={"replaced_key_id": key_id})
    session.commit()
    return ApiKeyCreatedOut(
        id=new.id, name=new.name, api_key=raw_key, key_prefix=new.key_prefix, scopes=new.scopes or [],
        status=new.status, expires_at=_utc(new.expires_at), created_at=_utc(new.created_at),
    )


# ================================================================== monitoring & system health
def _queue_status(session: Session) -> QueueStatusOut:
    counts = outreach_repo.message_status_counts(session)
    return QueueStatusOut(
        scheduled=counts.get("scheduled", 0), queued=counts.get("queued", 0),
        sending=counts.get("sending", 0), failed=counts.get("failed", 0),
    )


def _integration_statuses() -> list[IntegrationStatusOut]:
    from backend.config import get_settings
    s = get_settings()
    return [
        IntegrationStatusOut(name="microsoft_auth", configured=(
            bool(s.microsoft_tenant_id and s.microsoft_client_id)
        )),
        IntegrationStatusOut(name="gmail", configured=bool(s.gmail_client_id and s.gmail_client_secret)),
        IntegrationStatusOut(name="api_key_gate", configured=bool(s.api_key)),
    ]


def system_health(session: Session, user) -> SystemHealthOut:
    wf_stats = workflow_repo.execution_stats(session)
    success_rate = round(wf_stats["success"] / wf_stats["total"], 4) if wf_stats["total"] else 1.0
    queue = _queue_status(session)
    return SystemHealthOut(
        api_usage_total=repo.total_api_usage(session),
        workflow_executions=wf_stats["total"],
        workflow_success_rate=success_rate,
        queue_status=queue,
        scheduler_healthy=queue.failed < 10,
        integrations=_integration_statuses(),
    )


# ================================================================== dashboard + analytics (cached)
_DASH_TTL_SECONDS = 30
_dash_cache: dict[str, tuple[float, AdminDashboardOut]] = {}


def admin_dashboard(session: Session, user) -> AdminDashboardOut:
    key = _config_cache_key(session)
    cached = _dash_cache.get(key)
    if cached and time.monotonic() - cached[0] < _DASH_TTL_SECONDS:
        return cached[1]

    since = _utcnow() - timedelta(hours=24)
    out = AdminDashboardOut(
        active_users=repo.count_active_users(session),
        total_organizations=repo.count_organizations(session),
        api_usage_total=repo.total_api_usage(session),
        security_events_24h=repo.security_events_since(session, since),
        audit_events_24h=repo.count_audit_events_since(session, since),
        pending_compliance_requests=repo.count_pending_compliance(session),
        system_health=system_health(session, user),
    )
    _dash_cache[key] = (time.monotonic(), out)
    return out


def admin_analytics(session: Session, user) -> AdminAnalyticsOut:
    since = _utcnow() - timedelta(days=30)
    return AdminAnalyticsOut(
        user_growth_by_period=repo.user_growth_by_day(session, since),
        login_activity_by_period=repo.login_activity_by_day(session, since),
        audit_volume_by_category=repo.audit_volume_by_category(session),
        api_utilization=repo.api_usage_by_key(session),
        workflow_utilization=repo.workflow_execution_stats(session),
        security_events_by_type={},  # ponytail: user_audit_events doesn't yet tag a security "type" beyond action; upgrade path: widen UserAuditEvent if finer-grained security-event typing is needed
        compliance_stats=repo.compliance_stats(session),
    )
