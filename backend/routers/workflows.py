"""Enterprise CRM Phase 6: Workflow Automation & Business Process Engine endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import workflow_service as svc
from backend.dependencies import get_session
from backend.schemas import (
    ApprovalDecisionIn,
    ApprovalRequestCreate,
    ApprovalRequestOut,
    Page,
    RenewalScanResultOut,
    SlaPolicyCreate,
    SlaPolicyOut,
    SlaPolicyPatch,
    SlaTickResultOut,
    SlaTrackerCreate,
    SlaTrackerOut,
    WorkflowAnalyticsOut,
    WorkflowCreate,
    WorkflowDashboardOut,
    WorkflowOut,
    WorkflowPatch,
)
from backend.security import get_current_user
from master_db.models import User

router = APIRouter(prefix="/workflows", tags=["workflow-automation"])


# ============================================================ workflow CRUD
@router.get("", response_model=Page)
def list_workflows(
    status_: str | None = Query(None, alias="status"),
    trigger_event: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_workflows(session, user, status=status_, trigger_event=trigger_event, limit=limit, offset=offset)


@router.post("", response_model=WorkflowOut, status_code=status.HTTP_201_CREATED)
def create_workflow(
    data: WorkflowCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_workflow(session, data, user)


@router.get("/{workflow_id}", response_model=WorkflowOut)
def get_workflow(
    workflow_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.get_workflow(session, workflow_id, user)


@router.patch("/{workflow_id}", response_model=WorkflowOut)
def patch_workflow(
    workflow_id: int, data: WorkflowPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_workflow(session, workflow_id, data, user)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_workflow(session, workflow_id, user)


# ============================================================ automation history
@router.get("/executions/list", response_model=Page)
def list_executions(
    workflow_id: int | None = Query(None),
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_executions(session, user, workflow_id=workflow_id, entity_type=entity_type, entity_id=entity_id, limit=limit, offset=offset)


# ============================================================ approvals
@router.get("/approvals/list", response_model=Page)
def list_approvals(
    status_: str | None = Query(None, alias="status"),
    approval_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_approvals(session, user, status=status_, approval_type=approval_type, limit=limit, offset=offset)


@router.post("/approvals", response_model=ApprovalRequestOut, status_code=status.HTTP_201_CREATED)
def create_approval(
    data: ApprovalRequestCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_approval(session, data, user)


@router.get("/approvals/{approval_id}", response_model=ApprovalRequestOut)
def get_approval(
    approval_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.get_approval(session, approval_id, user)


@router.post("/approvals/{approval_id}/decide", response_model=ApprovalRequestOut)
def decide_approval(
    approval_id: int, data: ApprovalDecisionIn,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.decide_approval(session, approval_id, data, user)


# ============================================================ SLA management
@router.get("/sla/policies", response_model=list[SlaPolicyOut])
def list_sla_policies(
    entity_type: str | None = Query(None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_sla_policies(session, user, entity_type=entity_type)


@router.post("/sla/policies", response_model=SlaPolicyOut, status_code=status.HTTP_201_CREATED)
def create_sla_policy(
    data: SlaPolicyCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_sla_policy(session, data, user)


@router.patch("/sla/policies/{policy_id}", response_model=SlaPolicyOut)
def patch_sla_policy(
    policy_id: int, data: SlaPolicyPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_sla_policy(session, policy_id, data, user)


@router.get("/sla/trackers", response_model=Page)
def list_sla_trackers(
    status_: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_sla_trackers(session, user, status=status_, limit=limit, offset=offset)


@router.post("/sla/trackers", response_model=SlaTrackerOut, status_code=status.HTTP_201_CREATED)
def create_sla_tracker(
    data: SlaTrackerCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_sla_tracker(session, data, user)


@router.post("/sla/trackers/{tracker_id}/resolve", response_model=SlaTrackerOut)
def resolve_sla_tracker(
    tracker_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.resolve_sla_tracker(session, tracker_id, user)


@router.post("/sla/tick", response_model=SlaTickResultOut,
             summary="Run one SLA sweep — mark at_risk/breached/escalated (manual or cron-tick)")
def sla_tick(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.run_sla_tick(session, user)


@router.post("/scan/renewals", response_model=RenewalScanResultOut,
             summary="Fire contract_renewal_window workflows for contracts nearing expiry (manual or cron-tick)")
def scan_renewals(
    window_days: int = Query(90, ge=1, le=365),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.scan_renewal_windows(session, user, window_days=window_days)


# ============================================================ dashboard + analytics
@router.get("/dashboard/summary", response_model=WorkflowDashboardOut)
def workflow_dashboard(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.workflow_dashboard(session, user)


@router.get("/analytics/summary", response_model=WorkflowAnalyticsOut)
def workflow_analytics(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.workflow_analytics(session, user)
