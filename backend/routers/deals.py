"""Enterprise CRM Phase 2: Pipeline & Deal Management endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import deal_service as svc
from backend.dependencies import get_session
from backend.security import get_current_user
from backend.schemas import (
    DealAnalyticsOut,
    DealCreate,
    DealDashboardOut,
    DealIntelligenceOut,
    DealMoveIn,
    DealOut,
    DealPatch,
    DealStageHistoryOut,
    ForecastOut,
    KanbanOut,
    Page,
    PipelineCreate,
    PipelineOut,
    PipelinePatch,
    PipelineStageCreate,
    PipelineStageOut,
    PipelineStagePatch,
    UnifiedTimelineEvent,
)
from master_db.models import User

pipelines_router = APIRouter(prefix="/pipelines", tags=["deals"])
deals_router = APIRouter(prefix="/deals", tags=["deals"])


# ============================================================ pipelines CRUD
@pipelines_router.get("", response_model=Page)
def list_pipelines(
    active_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_pipelines(session, user, active_only=active_only, limit=limit, offset=offset)


@pipelines_router.post("", response_model=PipelineOut, status_code=status.HTTP_201_CREATED)
def create_pipeline(
    data: PipelineCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_pipeline(session, data, user)


@pipelines_router.get("/dashboard", response_model=DealDashboardOut)
def get_dashboard(
    pipeline_id: int | None = Query(None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.deal_dashboard(session, user, pipeline_id=pipeline_id)


@pipelines_router.get("/{pipeline_id}", response_model=PipelineOut)
def get_pipeline(
    pipeline_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.get_pipeline(session, pipeline_id, user)


@pipelines_router.patch("/{pipeline_id}", response_model=PipelineOut)
def patch_pipeline(
    pipeline_id: int,
    data: PipelinePatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_pipeline(session, pipeline_id, data, user)


@pipelines_router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pipeline(
    pipeline_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_pipeline(session, pipeline_id, user)


# ============================================================ stages
@pipelines_router.post(
    "/{pipeline_id}/stages",
    response_model=PipelineStageOut,
    status_code=status.HTTP_201_CREATED,
)
def add_stage(
    pipeline_id: int,
    data: PipelineStageCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.add_stage(session, pipeline_id, data, user)


@pipelines_router.patch("/{pipeline_id}/stages/{stage_id}", response_model=PipelineStageOut)
def patch_stage(
    pipeline_id: int,
    stage_id: int,
    data: PipelineStagePatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_stage(session, pipeline_id, stage_id, data, user)


@pipelines_router.delete(
    "/{pipeline_id}/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_stage(
    pipeline_id: int,
    stage_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_stage(session, pipeline_id, stage_id, user)


# ============================================================ kanban
@pipelines_router.get("/{pipeline_id}/kanban", response_model=KanbanOut)
def kanban(
    pipeline_id: int,
    stage_id: int | None = Query(None),
    owner_id: int | None = Query(None),
    search: str | None = Query(None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.kanban(session, pipeline_id, user, stage_id=stage_id, owner_id=owner_id, search=search)


# ============================================================ forecast + analytics
@pipelines_router.get("/{pipeline_id}/forecast", response_model=ForecastOut)
def get_forecast(
    pipeline_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.forecast(session, pipeline_id, user)


@pipelines_router.get("/{pipeline_id}/analytics", response_model=DealAnalyticsOut)
def get_analytics(
    pipeline_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.pipeline_analytics(session, pipeline_id, user)


# ============================================================ deals CRUD
@deals_router.get("", response_model=Page)
def list_deals(
    pipeline_id: int | None = Query(None),
    stage_id: int | None = Query(None),
    owner_id: int | None = Query(None),
    company_domain: str | None = Query(None),
    forecast_category: str | None = Query(None),
    search: str | None = Query(None),
    closing_before: datetime | None = Query(None),
    closing_after: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_deals(
        session, user, pipeline_id=pipeline_id, stage_id=stage_id,
        owner_id=owner_id, company_domain=company_domain, search=search,
        forecast_category=forecast_category,
        closing_before=closing_before, closing_after=closing_after,
        limit=limit, offset=offset,
    )


@deals_router.post("", response_model=DealOut, status_code=status.HTTP_201_CREATED)
def create_deal(
    data: DealCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_deal(session, data, user)


@deals_router.get("/{deal_id}", response_model=DealOut)
def get_deal(
    deal_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.get_deal(session, deal_id, user)


@deals_router.patch("/{deal_id}", response_model=DealOut)
def patch_deal(
    deal_id: int,
    data: DealPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_deal(session, deal_id, data, user)


@deals_router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deal(
    deal_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_deal(session, deal_id, user)


@deals_router.post("/{deal_id}/move", response_model=DealOut)
def move_deal(
    deal_id: int,
    data: DealMoveIn,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.move_deal(session, deal_id, data.stage_id, user)


@deals_router.get("/{deal_id}/history", response_model=list[DealStageHistoryOut])
def deal_history(
    deal_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.deal_stage_history(session, deal_id, user)


@deals_router.get("/{deal_id}/timeline", response_model=list[UnifiedTimelineEvent])
def deal_timeline(
    deal_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.deal_timeline(session, deal_id, user, limit=limit, offset=offset)


@deals_router.get("/{deal_id}/intelligence", response_model=DealIntelligenceOut)
def deal_intelligence(
    deal_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.deal_intelligence(session, deal_id, user)
