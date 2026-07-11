"""Enterprise CRM Phase 4: Customer Success & Account Management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import cs_service as svc
from backend.dependencies import get_session
from backend.security import get_current_user
from backend.schemas import (
    CsAccountCreate,
    CsAccountOut,
    CsAccountPatch,
    CsAnalyticsOut,
    CsContactCreate,
    CsContactOut,
    CsContactPatch,
    CsContractCreate,
    CsContractOut,
    CsContractPatch,
    CsDashboardOut,
    CsHealthScoreCreate,
    CsHealthScoreOut,
    CsLifecycleEventOut,
    CsMilestoneCreate,
    CsMilestoneOut,
    CsMilestonePatch,
    CsRiskCreate,
    CsRiskOut,
    CsRiskPatch,
    CsSuccessPlanCreate,
    CsSuccessPlanOut,
    CsSuccessPlanPatch,
    CsTimelineEvent,
    Page,
)
from master_db.models import User

router = APIRouter(prefix="/cs", tags=["customer-success"])


# ============================================================ accounts
@router.get("/accounts", response_model=Page)
def list_accounts(
    status: str | None = Query(None),
    tier: str | None = Query(None),
    lifecycle_stage: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_accounts(session, user, status, tier, lifecycle_stage, limit, offset)


@router.post("/accounts", response_model=CsAccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    data: CsAccountCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_account(session, data, user)


@router.get("/accounts/{account_id}", response_model=CsAccountOut)
def get_account(
    account_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.get_account(session, account_id, user)


@router.patch("/accounts/{account_id}", response_model=CsAccountOut)
def patch_account(
    account_id: int,
    data: CsAccountPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_account(session, account_id, data, user)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_account(session, account_id, user)


# ============================================================ contacts
@router.get("/accounts/{account_id}/contacts", response_model=list[CsContactOut])
def list_contacts(
    account_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_contacts(session, account_id, user)


@router.post("/contacts", response_model=CsContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(
    data: CsContactCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_contact(session, data, user)


@router.patch("/contacts/{contact_id}", response_model=CsContactOut)
def patch_contact(
    contact_id: int,
    data: CsContactPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_contact(session, contact_id, data, user)


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_contact(session, contact_id, user)


# ============================================================ health
@router.post(
    "/accounts/{account_id}/health",
    response_model=CsHealthScoreOut,
    status_code=status.HTTP_201_CREATED,
)
def score_account(
    account_id: int,
    data: CsHealthScoreCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.score_account(session, account_id, data, user)


@router.get("/accounts/{account_id}/health", response_model=CsHealthScoreOut)
def get_health(
    account_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.get_health(session, account_id, user)


@router.get("/accounts/{account_id}/health/history", response_model=list[CsHealthScoreOut])
def health_history(
    account_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.health_history(session, account_id, user)


# ============================================================ lifecycle
@router.get("/accounts/{account_id}/lifecycle", response_model=list[CsLifecycleEventOut])
def lifecycle_history(
    account_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.lifecycle_history(session, account_id, user)


# ============================================================ contracts
@router.get("/contracts", response_model=Page)
def list_contracts(
    account_id: int | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_contracts(session, account_id, status, limit, offset, user)


@router.post("/contracts", response_model=CsContractOut, status_code=status.HTTP_201_CREATED)
def create_contract(
    data: CsContractCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_contract(session, data, user)


@router.patch("/contracts/{contract_id}", response_model=CsContractOut)
def patch_contract(
    contract_id: int,
    data: CsContractPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_contract(session, contract_id, data, user)


@router.delete("/contracts/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(
    contract_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_contract(session, contract_id, user)


# ============================================================ success plans
@router.get("/accounts/{account_id}/plans", response_model=list[CsSuccessPlanOut])
def list_plans(
    account_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_plans(session, account_id, user)


@router.post("/plans", response_model=CsSuccessPlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(
    data: CsSuccessPlanCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_plan(session, data, user)


@router.patch("/plans/{plan_id}", response_model=CsSuccessPlanOut)
def patch_plan(
    plan_id: int,
    data: CsSuccessPlanPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_plan(session, plan_id, data, user)


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(
    plan_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_plan(session, plan_id, user)


# ============================================================ milestones
@router.get("/plans/{plan_id}/milestones", response_model=list[CsMilestoneOut])
def list_milestones(
    plan_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_milestones(session, plan_id, user)


@router.post("/milestones", response_model=CsMilestoneOut, status_code=status.HTTP_201_CREATED)
def create_milestone(
    data: CsMilestoneCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_milestone(session, data, user)


@router.patch("/milestones/{milestone_id}", response_model=CsMilestoneOut)
def patch_milestone(
    milestone_id: int,
    data: CsMilestonePatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_milestone(session, milestone_id, data, user)


@router.delete("/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_milestone(
    milestone_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_milestone(session, milestone_id, user)


# ============================================================ risks
@router.get("/accounts/{account_id}/risks", response_model=list[CsRiskOut])
def list_risks(
    account_id: int,
    status: str | None = Query(None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_risks(session, account_id, status, user)


@router.post("/risks", response_model=CsRiskOut, status_code=status.HTTP_201_CREATED)
def create_risk(
    data: CsRiskCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_risk(session, data, user)


@router.patch("/risks/{risk_id}", response_model=CsRiskOut)
def patch_risk(
    risk_id: int,
    data: CsRiskPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_risk(session, risk_id, data, user)


@router.delete("/risks/{risk_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_risk(
    risk_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_risk(session, risk_id, user)


# ============================================================ timeline
@router.get("/accounts/{account_id}/timeline", response_model=list[CsTimelineEvent])
def account_timeline(
    account_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.account_timeline(session, account_id, user, limit=limit, offset=offset)


# ============================================================ dashboard + analytics
@router.get("/dashboard", response_model=CsDashboardOut)
def cs_dashboard(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.cs_dashboard(session, user)


@router.get("/analytics", response_model=CsAnalyticsOut)
def cs_analytics(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.cs_analytics(session, user)
