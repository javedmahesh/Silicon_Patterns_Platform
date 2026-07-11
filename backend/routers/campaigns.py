"""Enterprise CRM Phase 1: Campaign & Sequence endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend import campaign_repo as crepo
from backend import campaign_service as svc
from backend.dependencies import get_session
from backend.security import get_current_user
from backend.schemas import (
    CampaignAnalyticsOut,
    CampaignCreate,
    CampaignDashboardOut,
    CampaignMemberIn,
    CampaignMemberOut,
    CampaignMemberPatch,
    CampaignOut,
    CampaignPatch,
    CrmEnrollmentOut,
    CrmSequenceCreate,
    CrmSequenceOut,
    CrmSequencePatch,
    CrmSequenceStepIn,
    CrmSequenceStepOut,
    CrmSequenceStepPatch,
    Page,
    UnifiedTimelineEvent,
)
from master_db.models import User

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
sequences_router = APIRouter(prefix="/sequences", tags=["campaigns"])
enrollments_router = APIRouter(prefix="/enrollments", tags=["campaigns"])


# ============================================================ campaigns CRUD
@router.get("", response_model=Page)
def list_campaigns(
    owner_id: int | None = Query(None),
    status: str | None = Query(None),
    campaign_type: str | None = Query(None),
    company_domain: str | None = Query(None),
    decision_maker_id: int | None = Query(None),
    tag: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_campaigns(
        session, user,
        owner_id=owner_id, status=status, campaign_type=campaign_type,
        company_domain=company_domain, decision_maker_id=decision_maker_id,
        tag=tag, search=search, limit=limit, offset=offset,
    )


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
def create_campaign(
    data: CampaignCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_campaign(session, data, user)


@router.get("/dashboard", response_model=CampaignDashboardOut)
def get_dashboard(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.campaign_dashboard(session, user)


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(
    campaign_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.get_campaign(session, campaign_id, user)


@router.patch("/{campaign_id}", response_model=CampaignOut)
def patch_campaign(
    campaign_id: int,
    data: CampaignPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_campaign(session, campaign_id, data, user)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.archive_campaign(session, campaign_id, user)


# ============================================================ analytics + timeline
@router.get("/{campaign_id}/analytics", response_model=CampaignAnalyticsOut)
def get_analytics(
    campaign_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.campaign_analytics(session, campaign_id, user)


@router.get("/{campaign_id}/timeline", response_model=list[UnifiedTimelineEvent])
def get_timeline(
    campaign_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.campaign_timeline(session, campaign_id, user, limit=limit, offset=offset)


# ============================================================ members
@router.get("/{campaign_id}/members", response_model=Page)
def list_members(
    campaign_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_members(session, campaign_id, user, limit=limit, offset=offset)


@router.post("/{campaign_id}/members", response_model=CampaignMemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    campaign_id: int,
    data: CampaignMemberIn,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.add_member(session, campaign_id, data, user)


@router.patch("/{campaign_id}/members/{member_id}", response_model=CampaignMemberOut)
def patch_member(
    campaign_id: int,
    member_id: int,
    data: CampaignMemberPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_member(session, campaign_id, member_id, data, user)


@router.delete("/{campaign_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    campaign_id: int,
    member_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.remove_member(session, campaign_id, member_id, user)


@router.post(
    "/{campaign_id}/members/{member_id}/enroll",
    response_model=CrmEnrollmentOut,
    status_code=status.HTTP_201_CREATED,
)
def enroll_member(
    campaign_id: int,
    member_id: int,
    sequence_id: int = Query(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    m = crepo.get_member(session, member_id)
    if not m or m.campaign_id != campaign_id:
        raise HTTPException(404, "member not found")
    if not m.outreach_lead_id:
        raise HTTPException(400, "member has no associated outreach lead; add outreach_lead_id first")
    return svc.enroll_lead(session, m.outreach_lead_id, sequence_id, member_id, user)


# ============================================================ sequences CRUD
@sequences_router.get("", response_model=Page)
def list_sequences(
    active_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_sequences(session, user, active_only=active_only, limit=limit, offset=offset)


@sequences_router.post("", response_model=CrmSequenceOut, status_code=status.HTTP_201_CREATED)
def create_sequence(
    data: CrmSequenceCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_sequence(session, data, user)


@sequences_router.get("/{seq_id}", response_model=CrmSequenceOut)
def get_sequence(
    seq_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.get_sequence(session, seq_id, user)


@sequences_router.patch("/{seq_id}", response_model=CrmSequenceOut)
def patch_sequence(
    seq_id: int,
    data: CrmSequencePatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_sequence(session, seq_id, data, user)


@sequences_router.delete("/{seq_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sequence(
    seq_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_sequence(session, seq_id, user)


@sequences_router.post("/{seq_id}/steps", response_model=CrmSequenceStepOut, status_code=status.HTTP_201_CREATED)
def add_step(
    seq_id: int,
    data: CrmSequenceStepIn,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.add_step(session, seq_id, data, user)


@sequences_router.patch("/{seq_id}/steps/{step_id}", response_model=CrmSequenceStepOut)
def patch_step(
    seq_id: int,
    step_id: int,
    data: CrmSequenceStepPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_step(session, seq_id, step_id, data, user)


@sequences_router.delete("/{seq_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_step(
    seq_id: int,
    step_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_step(session, seq_id, step_id, user)


# ============================================================ enrollments list
@enrollments_router.get("", response_model=Page)
def list_enrollments(
    sequence_id: int | None = Query(None),
    campaign_id: int | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_enrollments(
        session, user,
        sequence_id=sequence_id, campaign_id=campaign_id,
        status=status, search=search, limit=limit, offset=offset,
    )


# ============================================================ enrollment controls
@enrollments_router.post("/{enrollment_id}/pause", response_model=CrmEnrollmentOut)
def pause(
    enrollment_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.control_enrollment(session, enrollment_id, "pause", user)


@enrollments_router.post("/{enrollment_id}/resume", response_model=CrmEnrollmentOut)
def resume(
    enrollment_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.control_enrollment(session, enrollment_id, "resume", user)


@enrollments_router.post("/{enrollment_id}/cancel", response_model=CrmEnrollmentOut)
def cancel(
    enrollment_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.control_enrollment(session, enrollment_id, "cancel", user)


@enrollments_router.post("/{enrollment_id}/advance", response_model=CrmEnrollmentOut)
def advance(
    enrollment_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.advance_enrollment(session, enrollment_id, user)


@enrollments_router.post("/{enrollment_id}/steps/{step_id}/skip", response_model=CrmEnrollmentOut)
def skip_step(
    enrollment_id: int,
    step_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.skip_step(session, enrollment_id, step_id, user)
