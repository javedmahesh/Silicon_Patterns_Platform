"""Data access for Enterprise CRM Phase 9: Enterprise Administration, Security & Compliance."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from master_db.models import (
    ApiKey,
    AuditEvent,
    ComplianceRecord,
    Organization,
    OrgUnit,
    OrgUnitMember,
    SecurityPolicy,
    SystemSetting,
    User,
    UserAuditEvent,
    WorkflowExecution,
)


# ----------------------------------------------------------------- organizations
def create_organization(session: Session, **kw) -> Organization:
    o = Organization(**kw)
    session.add(o)
    session.flush()
    return o


def get_organization(session: Session, org_id: int) -> Organization | None:
    return session.get(Organization, org_id)


def get_organization_by_slug(session: Session, slug: str) -> Organization | None:
    return session.scalar(select(Organization).where(Organization.slug == slug))


def list_organizations(session: Session, *, limit: int = 50, offset: int = 0) -> tuple[list[Organization], int]:
    total = session.scalar(select(func.count()).select_from(Organization)) or 0
    rows = list(session.scalars(select(Organization).order_by(Organization.id).limit(limit).offset(offset)))
    return rows, total


def count_organizations(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Organization)) or 0


# ----------------------------------------------------------------- org units
def create_unit(session: Session, **kw) -> OrgUnit:
    u = OrgUnit(**kw)
    session.add(u)
    session.flush()
    return u


def get_unit(session: Session, unit_id: int) -> OrgUnit | None:
    return session.get(OrgUnit, unit_id)


def list_units(session: Session, organization_id: int, *, unit_type: str | None = None) -> list[OrgUnit]:
    q = select(OrgUnit).where(OrgUnit.organization_id == organization_id)
    if unit_type:
        q = q.where(OrgUnit.unit_type == unit_type)
    return list(session.scalars(q.order_by(OrgUnit.id)))


def delete_unit(session: Session, unit_id: int) -> bool:
    u = session.get(OrgUnit, unit_id)
    if not u:
        return False
    session.delete(u)
    return True


def member_counts(session: Session, unit_ids: list[int]) -> dict[int, int]:
    """1-query batch member count per unit — no N+1."""
    if not unit_ids:
        return {}
    rows = session.execute(
        select(OrgUnitMember.unit_id, func.count(OrgUnitMember.id))
        .where(OrgUnitMember.unit_id.in_(unit_ids))
        .group_by(OrgUnitMember.unit_id)
    ).all()
    return {r[0]: r[1] for r in rows}


# ----------------------------------------------------------------- org unit members
def add_member(session: Session, **kw) -> OrgUnitMember:
    m = OrgUnitMember(**kw)
    session.add(m)
    session.flush()
    return m


def get_member(session: Session, unit_id: int, user_id: int) -> OrgUnitMember | None:
    return session.scalar(
        select(OrgUnitMember).where(OrgUnitMember.unit_id == unit_id, OrgUnitMember.user_id == user_id)
    )


def list_members(session: Session, unit_id: int) -> list[OrgUnitMember]:
    return list(session.scalars(select(OrgUnitMember).where(OrgUnitMember.unit_id == unit_id)))


def remove_member(session: Session, member_id: int) -> bool:
    m = session.get(OrgUnitMember, member_id)
    if not m:
        return False
    session.delete(m)
    return True


# ----------------------------------------------------------------- system settings
def upsert_setting(session: Session, category: str, key: str, value: dict, updated_by: int | None) -> SystemSetting:
    existing = session.scalar(
        select(SystemSetting).where(SystemSetting.category == category, SystemSetting.key == key)
    )
    if existing:
        existing.value = value
        existing.updated_by = updated_by
        session.flush()
        return existing
    s = SystemSetting(category=category, key=key, value=value, updated_by=updated_by)
    session.add(s)
    session.flush()
    return s


def list_settings(session: Session, *, category: str | None = None) -> list[SystemSetting]:
    q = select(SystemSetting)
    if category:
        q = q.where(SystemSetting.category == category)
    return list(session.scalars(q.order_by(SystemSetting.category, SystemSetting.key)))


def get_setting(session: Session, category: str, key: str) -> SystemSetting | None:
    return session.scalar(select(SystemSetting).where(SystemSetting.category == category, SystemSetting.key == key))


# ----------------------------------------------------------------- security policies
def upsert_policy(session: Session, policy_type: str, config: dict, is_enabled: bool, updated_by: int | None) -> SecurityPolicy:
    existing = session.scalar(select(SecurityPolicy).where(SecurityPolicy.policy_type == policy_type))
    if existing:
        existing.config = config
        existing.is_enabled = is_enabled
        existing.updated_by = updated_by
        session.flush()
        return existing
    p = SecurityPolicy(policy_type=policy_type, config=config, is_enabled=is_enabled, updated_by=updated_by)
    session.add(p)
    session.flush()
    return p


def list_policies(session: Session) -> list[SecurityPolicy]:
    return list(session.scalars(select(SecurityPolicy).order_by(SecurityPolicy.policy_type)))


def get_policy(session: Session, policy_type: str) -> SecurityPolicy | None:
    return session.scalar(select(SecurityPolicy).where(SecurityPolicy.policy_type == policy_type))


# ----------------------------------------------------------------- audit events (native, Phase 9)
def create_audit_event(session: Session, **kw) -> AuditEvent:
    e = AuditEvent(**kw)
    session.add(e)
    session.flush()
    return e


def list_audit_events(
    session: Session, *, category: str | None = None, actor_id: int | None = None,
    search: str | None = None, limit: int = 50, offset: int = 0,
) -> tuple[list[AuditEvent], int]:
    q = select(AuditEvent)
    filters = []
    if category:
        filters.append(AuditEvent.category == category)
    if actor_id:
        filters.append(AuditEvent.actor_id == actor_id)
    if search:
        filters.append(AuditEvent.action.ilike(f"%{search}%"))
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(AuditEvent.id.desc()).limit(limit).offset(offset)))
    return rows, total


def audit_volume_by_category(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(AuditEvent.category, func.count(AuditEvent.id)).group_by(AuditEvent.category)
    ).all()
    return {r[0]: r[1] for r in rows}


def count_audit_events_since(session: Session, since: datetime) -> int:
    return session.scalar(
        select(func.count()).select_from(AuditEvent).where(AuditEvent.created_at >= since)
    ) or 0


# ----------------------------------------------------------------- unified read over user_audit_events
_USER_AUDIT_AUTH_ACTIONS = ("registered", "login")


def list_user_audit_as_events(
    session: Session, *, category: str | None = None, limit: int = 50, offset: int = 0,
) -> tuple[list[UserAuditEvent], int]:
    """Existing Phase-0 account-lifecycle audit rows, filterable by the same category taxonomy
    (authentication vs user_administration) without duplicating that data into audit_events."""
    q = select(UserAuditEvent)
    if category == "authentication":
        q = q.where(UserAuditEvent.action.in_(_USER_AUDIT_AUTH_ACTIONS))
    elif category == "user_administration":
        q = q.where(UserAuditEvent.action.notin_(_USER_AUDIT_AUTH_ACTIONS))
    elif category not in (None, "authentication", "user_administration"):
        return [], 0
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(UserAuditEvent.id.desc()).limit(limit).offset(offset)))
    return rows, total


def security_events_since(session: Session, since: datetime) -> int:
    """Login/account-lockout style events from the existing user_audit_events table."""
    return session.scalar(
        select(func.count()).select_from(UserAuditEvent)
        .where(UserAuditEvent.created_at >= since, UserAuditEvent.action.in_(("login", "disabled", "rejected")))
    ) or 0


def login_activity_by_day(session: Session, since: datetime) -> dict[str, int]:
    rows = session.execute(
        select(func.date(UserAuditEvent.created_at), func.count(UserAuditEvent.id))
        .where(UserAuditEvent.action == "login", UserAuditEvent.created_at >= since)
        .group_by(func.date(UserAuditEvent.created_at))
    ).all()
    return {str(r[0]): r[1] for r in rows}


# ----------------------------------------------------------------- compliance
def create_compliance_record(session: Session, **kw) -> ComplianceRecord:
    c = ComplianceRecord(**kw)
    session.add(c)
    session.flush()
    return c


def get_compliance_record(session: Session, record_id: int) -> ComplianceRecord | None:
    return session.get(ComplianceRecord, record_id)


def list_compliance_records(
    session: Session, *, record_type: str | None = None, status: str | None = None,
    limit: int = 50, offset: int = 0,
) -> tuple[list[ComplianceRecord], int]:
    q = select(ComplianceRecord)
    filters = []
    if record_type:
        filters.append(ComplianceRecord.record_type == record_type)
    if status:
        filters.append(ComplianceRecord.status == status)
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(ComplianceRecord.id.desc()).limit(limit).offset(offset)))
    return rows, total


def count_pending_compliance(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(ComplianceRecord).where(ComplianceRecord.status == "pending")
    ) or 0


def compliance_stats(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(ComplianceRecord.record_type, func.count(ComplianceRecord.id)).group_by(ComplianceRecord.record_type)
    ).all()
    return {r[0]: r[1] for r in rows}


# ----------------------------------------------------------------- API keys
def create_api_key(session: Session, **kw) -> ApiKey:
    k = ApiKey(**kw)
    session.add(k)
    session.flush()
    return k


def get_api_key(session: Session, key_id: int) -> ApiKey | None:
    return session.get(ApiKey, key_id)


def list_api_keys(session: Session, *, owner_id: int | None = None, status: str | None = None) -> list[ApiKey]:
    q = select(ApiKey)
    if owner_id is not None:
        q = q.where(ApiKey.owner_id == owner_id)
    if status:
        q = q.where(ApiKey.status == status)
    return list(session.scalars(q.order_by(ApiKey.id.desc())))


def total_api_usage(session: Session) -> int:
    return session.scalar(select(func.coalesce(func.sum(ApiKey.request_count), 0))) or 0


def api_usage_by_key(session: Session) -> dict[str, int]:
    rows = session.execute(select(ApiKey.name, ApiKey.request_count)).all()
    return {r[0]: r[1] for r in rows}


# ----------------------------------------------------------------- users (read-only reuse for admin dashboard/analytics)
def count_active_users(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(User).where(User.status == "active")) or 0


def user_growth_by_day(session: Session, since: datetime) -> dict[str, int]:
    rows = session.execute(
        select(func.date(User.created_at), func.count(User.id))
        .where(User.created_at >= since)
        .group_by(func.date(User.created_at))
    ).all()
    return {str(r[0]): r[1] for r in rows}


# ----------------------------------------------------------------- workflow reuse (monitoring)
def workflow_execution_stats(session: Session) -> dict:
    row = session.execute(
        select(
            func.count(WorkflowExecution.id),
            func.count(WorkflowExecution.id).filter(WorkflowExecution.status == "success"),
        )
    ).one()
    total, success = row
    return {"total": total, "success": success}
