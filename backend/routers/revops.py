"""Enterprise CRM Phase 5: Revenue Operations, Forecasting & Executive Analytics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import revops_service as svc
from backend.schemas import (
    BiSummaryOut,
    ExecutiveDashboardOut,
    ExecutiveReportOut,
    ForecastAccuracyOut,
    ForecastSnapshotOut,
    FunnelAnalyticsOut,
    Page,
    RevenueForecastOut,
    RevenueTargetCreate,
    RevenueTargetOut,
    RevopsPipelineAnalyticsOut,
    SalesPerformanceOut,
    TargetAttainmentOut,
)
from backend.dependencies import get_session
from backend.security import get_current_user
from master_db.models import User

router = APIRouter(prefix="/revops", tags=["revenue-operations"])


# ============================================================ forecasting
@router.get("/forecast", response_model=RevenueForecastOut)
def get_revenue_forecast(
    period_type: str = Query("monthly", pattern="^(monthly|quarterly|annual)$"),
    pipeline_id: int | None = Query(None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.revenue_forecast(session, user, period_type=period_type, pipeline_id=pipeline_id)


@router.post("/forecast/snapshots", response_model=list[ForecastSnapshotOut], status_code=status.HTTP_201_CREATED)
def post_forecast_snapshot(
    period_type: str = Query("monthly", pattern="^(monthly|quarterly|annual)$"),
    pipeline_id: int | None = Query(None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.capture_forecast_snapshot(session, user, period_type=period_type, pipeline_id=pipeline_id)


@router.get("/forecast/accuracy", response_model=list[ForecastAccuracyOut])
def get_forecast_accuracy(
    period_type: str | None = Query(None),
    pipeline_id: int | None = Query(None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.forecast_accuracy(session, user, period_type=period_type, pipeline_id=pipeline_id)


# ============================================================ revenue targets
@router.get("/targets", response_model=Page)
def list_revenue_targets(
    scope: str | None = Query(None),
    owner_id: int | None = Query(None),
    period_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_targets(session, user, scope=scope, owner_id=owner_id, period_type=period_type, limit=limit, offset=offset)


@router.post("/targets", response_model=RevenueTargetOut, status_code=status.HTTP_201_CREATED)
def create_revenue_target(
    data: RevenueTargetCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_target(session, data, user)


@router.get("/targets/{target_id}", response_model=RevenueTargetOut)
def get_revenue_target(
    target_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.get_target(session, target_id, user)


@router.delete("/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_revenue_target(
    target_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_target(session, target_id, user)


@router.get("/targets/{target_id}/attainment", response_model=TargetAttainmentOut)
def get_target_attainment(
    target_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.target_attainment(session, target_id, user)


# ============================================================ executive dashboard + analytics
@router.get("/executive-dashboard", response_model=ExecutiveDashboardOut)
def get_executive_dashboard(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.executive_dashboard(session, user)


@router.get("/pipeline-analytics", response_model=RevopsPipelineAnalyticsOut)
def get_pipeline_analytics(
    pipeline_id: int | None = Query(None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.pipeline_analytics(session, user, pipeline_id=pipeline_id)


@router.get("/sales-performance", response_model=SalesPerformanceOut)
def get_sales_performance(
    pipeline_id: int | None = Query(None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.sales_performance(session, user, pipeline_id=pipeline_id)


@router.get("/funnels", response_model=FunnelAnalyticsOut)
def get_funnel_analytics(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.funnel_analytics(session, user)


@router.get("/reports/{report_type}", response_model=ExecutiveReportOut)
def get_executive_report(
    report_type: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.executive_report(session, user, report_type)


@router.get("/bi/summary", response_model=BiSummaryOut)
def get_bi_summary(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.bi_summary(session, user)
