"""Enterprise CRM Phase 12: Data Warehouse & Advanced Business Intelligence endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import bi_service as svc
from backend.dependencies import get_session
from backend.schemas import (
    BiAnalyticsOut,
    BiDashboardOut,
    BiExecutiveDashboardOut,
    CustomReportCreate,
    CustomReportOut,
    CustomReportPatch,
    CustomReportResultOut,
    KpiCreate,
    KpiOut,
    KpiPatch,
    KpiValueIn,
    KpiValueOut,
    Page,
    ReportScheduleCreate,
    ReportSchedulePatch,
    ReportScheduleOut,
    ScheduledReportRunOut,
    TrendOut,
    WarehouseRefreshResultOut,
)
from backend.security import get_current_user
from master_db.models import User

router = APIRouter(prefix="/bi", tags=["business-intelligence"])


# ============================================================ historical data warehouse
@router.post("/warehouse/refresh", response_model=WarehouseRefreshResultOut)
def refresh_warehouse(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.refresh_warehouse(session, user)


@router.get("/warehouse/snapshots", response_model=Page)
def list_snapshots(
    metric_type: str | None = Query(None), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_snapshots(session, user, metric_type=metric_type, limit=limit, offset=offset)


# ============================================================ trend analysis
@router.get("/trends/{metric}", response_model=TrendOut)
def get_trend(
    metric: str,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.get_trend(session, user, metric)


# ============================================================ KPI framework
@router.get("/kpis", response_model=list[KpiOut])
def list_kpis(
    category: str | None = Query(None),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_kpis(session, user, category=category)


@router.post("/kpis", response_model=KpiOut, status_code=status.HTTP_201_CREATED)
def create_kpi(
    data: KpiCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.create_kpi(session, data, user)


@router.patch("/kpis/{kpi_id}", response_model=KpiOut)
def patch_kpi(
    kpi_id: int, data: KpiPatch,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.patch_kpi(session, kpi_id, data, user)


@router.delete("/kpis/{kpi_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kpi(
    kpi_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    svc.delete_kpi(session, kpi_id, user)


@router.post("/kpis/{kpi_id}/values", response_model=KpiValueOut, status_code=status.HTTP_201_CREATED)
def record_kpi_value(
    kpi_id: int, data: KpiValueIn,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.record_kpi_value(session, kpi_id, data, user)


@router.get("/kpis/{kpi_id}/values", response_model=list[KpiValueOut])
def kpi_history(
    kpi_id: int, limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.kpi_history(session, kpi_id, user, limit=limit)


# ============================================================ executive dashboards
@router.get("/dashboards/{dashboard_type}", response_model=BiExecutiveDashboardOut)
def executive_dashboard(
    dashboard_type: str,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.executive_dashboard(session, user, dashboard_type)


# ============================================================ custom reports
@router.get("/reports", response_model=list[CustomReportOut])
def list_reports(
    owner_id: int | None = Query(None), status_: str | None = Query(None, alias="status"),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_reports(session, user, owner_id=owner_id, status=status_)


@router.post("/reports", response_model=CustomReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    data: CustomReportCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.create_report(session, data, user)


@router.patch("/reports/{report_id}", response_model=CustomReportOut)
def patch_report(
    report_id: int, data: CustomReportPatch,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.patch_report(session, report_id, data, user)


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    svc.delete_report(session, report_id, user)


@router.get("/reports/{report_id}/run", response_model=CustomReportResultOut)
def run_report(
    report_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.run_report(session, report_id, user)


@router.post("/reports/{report_id}/schedules", response_model=ReportScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule(
    report_id: int, data: ReportScheduleCreate,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.create_schedule(session, report_id, data, user)


# ============================================================ scheduled reporting
@router.get("/schedules", response_model=list[ReportScheduleOut])
def list_schedules(
    report_id: int | None = Query(None),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_schedules(session, user, report_id=report_id)


@router.patch("/schedules/{schedule_id}", response_model=ReportScheduleOut)
def patch_schedule(
    schedule_id: int, data: ReportSchedulePatch,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.patch_schedule(session, schedule_id, data, user)


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    svc.delete_schedule(session, schedule_id, user)


@router.post("/schedules/{schedule_id}/deliver", response_model=ScheduledReportRunOut)
def deliver_schedule(
    schedule_id: int,
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.deliver_schedule(session, schedule_id, user)


@router.get("/schedules/{schedule_id}/runs", response_model=list[ScheduledReportRunOut])
def list_runs(
    schedule_id: int, limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.list_runs(session, user, schedule_id=schedule_id, limit=limit)


@router.post("/schedules/tick")
def run_due_schedules(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.run_due_schedules(session, user)


# ============================================================ BI dashboard + analytics
@router.get("/dashboard/summary", response_model=BiDashboardOut)
def bi_dashboard(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.bi_dashboard(session, user)


@router.get("/analytics/summary", response_model=BiAnalyticsOut)
def bi_analytics(
    session: Session = Depends(get_session), user: User = Depends(get_current_user),
):
    return svc.bi_analytics(session, user)
