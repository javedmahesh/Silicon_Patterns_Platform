"""Enterprise CRM Phase 9: Enterprise Administration, Security & Compliance endpoints.

Prefix is /governance (not /admin) — the existing /admin router already owns
user-approval/lifecycle endpoints from the Phase-0 auth-hardening epic.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import admin_service as svc
from backend.dependencies import get_session
from backend.schemas import (
    AdminAnalyticsOut,
    AdminDashboardOut,
    ApiKeyCreate,
    ApiKeyCreatedOut,
    ApiKeyOut,
    ComplianceRecordCreate,
    ComplianceRecordOut,
    ComplianceRecordPatch,
    OrganizationCreate,
    OrganizationOut,
    OrganizationPatch,
    OrgUnitCreate,
    OrgUnitMemberIn,
    OrgUnitMemberOut,
    OrgUnitOut,
    OrgUnitPatch,
    Page,
    SecurityPolicyIn,
    SecurityPolicyOut,
    SystemHealthOut,
    SystemSettingIn,
    SystemSettingOut,
)
from backend.security import get_current_user
from master_db.models import User

router = APIRouter(prefix="/governance", tags=["administration"])


# ============================================================ organizations
@router.get("/organizations", response_model=Page)
def list_organizations(
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_organizations(session, user, limit=limit, offset=offset)


@router.post("/organizations", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def create_organization(
    data: OrganizationCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.create_organization(session, data, user)


@router.get("/organizations/{org_id}", response_model=OrganizationOut)
def get_organization(
    org_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.get_organization(session, org_id, user)


@router.patch("/organizations/{org_id}", response_model=OrganizationOut)
def patch_organization(
    org_id: int, data: OrganizationPatch,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.patch_organization(session, org_id, data, user)


# ============================================================ org units (business units / departments / teams)
@router.get("/organizations/{org_id}/units", response_model=list[OrgUnitOut])
def list_units(
    org_id: int, unit_type: str | None = Query(None),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_units(session, org_id, user, unit_type=unit_type)


@router.post("/organizations/{org_id}/units", response_model=OrgUnitOut, status_code=status.HTTP_201_CREATED)
def create_unit(
    org_id: int, data: OrgUnitCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.create_unit(session, org_id, data, user)


@router.patch("/units/{unit_id}", response_model=OrgUnitOut)
def patch_unit(
    unit_id: int, data: OrgUnitPatch,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.patch_unit(session, unit_id, data, user)


@router.delete("/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit(
    unit_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    svc.delete_unit(session, unit_id, user)


@router.get("/units/{unit_id}/members", response_model=list[OrgUnitMemberOut])
def list_members(
    unit_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_members(session, unit_id, user)


@router.post("/units/{unit_id}/members", response_model=OrgUnitMemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    unit_id: int, data: OrgUnitMemberIn,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.add_member(session, unit_id, data, user)


@router.delete("/units/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    member_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    svc.remove_member(session, member_id, user)


# ============================================================ system configuration
@router.get("/settings", response_model=list[SystemSettingOut])
def list_settings(
    category: str | None = Query(None),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_settings(session, user, category=category)


@router.put("/settings", response_model=SystemSettingOut)
def upsert_setting(
    data: SystemSettingIn,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.upsert_setting(session, data, user)


# ============================================================ security policies
@router.get("/security/policies", response_model=list[SecurityPolicyOut])
def list_security_policies(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_security_policies(session, user)


@router.put("/security/policies", response_model=SecurityPolicyOut)
def upsert_security_policy(
    data: SecurityPolicyIn,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.upsert_security_policy(session, data, user)


# ============================================================ audit logging
@router.get("/audit", response_model=Page)
def list_audit_events(
    category: str | None = Query(None), search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_audit_events(session, user, category=category, search=search, limit=limit, offset=offset)


# ============================================================ compliance
@router.get("/compliance", response_model=Page)
def list_compliance_records(
    record_type: str | None = Query(None), status_: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_compliance_records(session, user, record_type=record_type, status=status_, limit=limit, offset=offset)


@router.post("/compliance", response_model=ComplianceRecordOut, status_code=status.HTTP_201_CREATED)
def create_compliance_record(
    data: ComplianceRecordCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.create_compliance_record(session, data, user)


@router.patch("/compliance/{record_id}", response_model=ComplianceRecordOut)
def patch_compliance_record(
    record_id: int, data: ComplianceRecordPatch,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.patch_compliance_record(session, record_id, data.status, user)


@router.post("/compliance/soft-delete/{entity_type}/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def soft_delete_entity(
    entity_type: str, entity_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    svc.soft_delete_entity(session, entity_type, entity_id, user)


# ============================================================ API keys
@router.get("/api-keys", response_model=list[ApiKeyOut])
def list_api_keys(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_api_keys(session, user, owner_id=user.id)


@router.post("/api-keys", response_model=ApiKeyCreatedOut, status_code=status.HTTP_201_CREATED)
def create_api_key(
    data: ApiKeyCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.create_api_key(session, data, user)


@router.post("/api-keys/{key_id}/revoke", response_model=ApiKeyOut)
def revoke_api_key(
    key_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.revoke_api_key(session, key_id, user)


@router.post("/api-keys/{key_id}/rotate", response_model=ApiKeyCreatedOut)
def rotate_api_key(
    key_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.rotate_api_key(session, key_id, user)


# ============================================================ monitoring & system health
@router.get("/health", response_model=SystemHealthOut)
def system_health(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.system_health(session, user)


# ============================================================ dashboard + analytics
@router.get("/dashboard/summary", response_model=AdminDashboardOut)
def admin_dashboard(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.admin_dashboard(session, user)


@router.get("/analytics/summary", response_model=AdminAnalyticsOut)
def admin_analytics(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.admin_analytics(session, user)
