"""Enterprise CRM Phase 8: AI Intelligence & Copilot endpoints (deterministic, no LLM)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import ai_service as svc
from backend.dependencies import get_session
from backend.schemas import (
    AiAnalyticsOut,
    AiBriefingOut,
    AiCopilotSummaryOut,
    AiDashboardOut,
    AiEngagementScoreOut,
    AiGenerationResultOut,
    AiInsightOut,
    AiInsightPatch,
    AiRecommendationOut,
    AiRiskScoreOut,
    Page,
)
from backend.security import get_current_user
from master_db.models import User

router = APIRouter(prefix="/ai", tags=["ai-intelligence"])


# ============================================================ insights
@router.post("/insights/generate", response_model=AiGenerationResultOut, status_code=status.HTTP_201_CREATED)
def generate_insights(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.generate_insights(session, user)


@router.get("/insights", response_model=Page)
def list_insights(
    insight_type: str | None = Query(None),
    severity: str | None = Query(None),
    status_: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_insights(session, user, insight_type=insight_type, severity=severity, status=status_, limit=limit, offset=offset)


@router.patch("/insights/{insight_id}", response_model=AiInsightOut)
def patch_insight(
    insight_id: int, data: AiInsightPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_insight_status(session, insight_id, data.status, user)


# ============================================================ recommendations
@router.post("/recommendations/generate", response_model=AiGenerationResultOut, status_code=status.HTTP_201_CREATED)
def generate_recommendations(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.generate_recommendations(session, user)


@router.get("/recommendations", response_model=Page)
def list_recommendations(
    recommendation_type: str | None = Query(None),
    status_: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_recommendations(session, user, recommendation_type=recommendation_type, status=status_, limit=limit, offset=offset)


@router.post("/recommendations/{rec_id}/dismiss", response_model=AiRecommendationOut)
def dismiss_recommendation(
    rec_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.dismiss_recommendation(session, rec_id, user)


@router.post("/recommendations/{rec_id}/complete", response_model=AiRecommendationOut)
def complete_recommendation(
    rec_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.complete_recommendation(session, rec_id, user)


# ============================================================ risks
@router.post("/risks/detect", response_model=AiGenerationResultOut, status_code=status.HTTP_201_CREATED)
def detect_risks(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.detect_risks(session, user)


@router.get("/risks", response_model=Page)
def list_risks(
    risk_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_risks(session, user, risk_type=risk_type, limit=limit, offset=offset)


# ============================================================ engagement / activity intelligence
@router.post("/engagement/compute", response_model=AiGenerationResultOut, status_code=status.HTTP_201_CREATED)
def compute_engagement(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.compute_engagement_scores(session, user)


@router.get("/engagement/scores", response_model=Page)
def list_engagement_scores(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_engagement_scores(session, user, limit=limit, offset=offset)


@router.get("/activity/{entity_type}/{entity_id}", response_model=AiCopilotSummaryOut)
def activity_summary(
    entity_type: str, entity_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.activity_summary(session, entity_type, entity_id, user)


# ============================================================ copilot
@router.get("/copilot/summary/{entity_type}/{entity_id}", response_model=AiCopilotSummaryOut)
def entity_summary(
    entity_type: str, entity_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.entity_summary(session, entity_type, entity_id, user)


@router.get("/copilot/customer/{account_id}", response_model=AiCopilotSummaryOut)
def customer_summary(
    account_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.customer_summary(session, account_id, user)


@router.get("/copilot/deal/{deal_id}", response_model=AiCopilotSummaryOut)
def deal_summary(
    deal_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.deal_summary(session, deal_id, user)


@router.get("/copilot/pipeline/{pipeline_id}", response_model=AiCopilotSummaryOut)
def pipeline_summary(
    pipeline_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.pipeline_summary(session, pipeline_id, user)


@router.get("/copilot/executive", response_model=AiCopilotSummaryOut)
def executive_summary(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.executive_summary(session, user)


# ============================================================ executive briefings
@router.post("/briefings/generate", response_model=AiBriefingOut, status_code=status.HTTP_201_CREATED)
def generate_briefing(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.generate_briefing(session, user)


@router.get("/briefings", response_model=list[AiBriefingOut])
def list_briefings(
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_briefings(session, user, limit=limit)


@router.get("/briefings/latest", response_model=AiBriefingOut | None)
def latest_briefing(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.latest_briefing(session, user)


# ============================================================ dashboard + analytics
@router.get("/dashboard/summary", response_model=AiDashboardOut)
def ai_dashboard(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.ai_dashboard(session, user)


@router.get("/analytics/summary", response_model=AiAnalyticsOut)
def ai_analytics(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.ai_analytics(session, user)
