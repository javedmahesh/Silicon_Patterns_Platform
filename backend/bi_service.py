"""Enterprise CRM Phase 12: Data Warehouse & Advanced Business Intelligence.

The warehouse is a snapshot layer, not a separate ETL pipeline: refresh_warehouse()
reuses one existing aggregate per metric_type (revops_service.executive_dashboard,
cs_repo.arr_mrr_totals/churn_renewal_rates, revops_repo.company_wide_deal_counts/
campaign_funnel_counts, workflow_repo.execution_stats, ai_repo.insight_counts_by_type)
and persists the result as one WarehouseSnapshot row per type per call — the existing
per-phase dashboards stay the live source of truth; the warehouse is their point-in-time
history. Executive Dashboards (section 3) work the same way: they slice the SAME
existing aggregates rather than recomputing anything.

Scheduled report delivery reuses the existing mock/gmail email provider registry
(backend.email_providers) — the same infra Outreach uses — instead of a new mailer.
"""
from __future__ import annotations

import time

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import admin_repo
from backend import ai_repo
from backend import bi_repo as repo
from backend import campaign_repo
from backend import cs_repo
from backend import deal_repo
from backend import revops_repo
from backend import revops_service
from backend import workflow_repo
from backend.config import get_settings
from backend.email_providers.registry import get_provider
from backend.tick_lock import single_flight
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
    ReportScheduleCreate,
    ReportSchedulePatch,
    ReportScheduleOut,
    ScheduledReportRunOut,
    TrendOut,
    TrendPointOut,
    WarehouseRefreshResultOut,
    WarehouseSnapshotOut,
)
from config.enums import BI_DASHBOARD_TYPES, WAREHOUSE_METRIC_TYPES

from backend.timeutil import utc as _utc, utcnow as _utcnow


def _is_manager(user) -> bool:
    return getattr(user, "role", "member") in ("admin", "manager")


def _require_manager(user) -> None:
    if not _is_manager(user):
        raise HTTPException(403, "manager or admin required")


# ================================================================== 1. historical data warehouse
def _collect_metrics(session: Session, user) -> dict[str, dict]:
    ed = revops_service.executive_dashboard(session, user)
    deal_counts = revops_repo.company_wide_deal_counts(session)
    customer_metrics = {**cs_repo.arr_mrr_totals(session), **cs_repo.churn_renewal_rates(session)}
    campaign_metrics = revops_repo.campaign_funnel_counts(session)
    campaign_metrics["total_members"] = sum(campaign_metrics.get("by_status", {}).values())
    activity_metrics = {"by_type": repo.activity_counts_by_type(session)}
    wf_stats = workflow_repo.execution_stats(session)
    ai_metrics = {
        "insight_counts": ai_repo.insight_counts_by_type(session),
        "avg_engagement": ai_repo.avg_engagement_score(session) or 0.0,
    }
    return {
        "revenue": {"revenue_ttm": ed.revenue_ttm, "pipeline_value": ed.pipeline_value, "weighted_forecast": ed.weighted_forecast, "win_rate": ed.win_rate},
        "deals": deal_counts,
        "customers": customer_metrics,
        "campaigns": campaign_metrics,
        "activities": activity_metrics,
        "ai_metrics": ai_metrics,
        "workflow_metrics": wf_stats,
    }


def refresh_warehouse(session: Session, user) -> WarehouseRefreshResultOut:
    _require_manager(user)
    now = _utcnow()
    metrics_by_type = _collect_metrics(session, user)
    for metric_type in WAREHOUSE_METRIC_TYPES:
        repo.create_snapshot(session, metric_type=metric_type, snapshot_date=now, metrics=metrics_by_type[metric_type])
    session.commit()
    return WarehouseRefreshResultOut(snapshots_created=len(WAREHOUSE_METRIC_TYPES))


def _snapshot_out(s) -> WarehouseSnapshotOut:
    return WarehouseSnapshotOut(id=s.id, metric_type=s.metric_type, snapshot_date=_utc(s.snapshot_date), metrics=s.metrics or {}, created_at=_utc(s.created_at))


def list_snapshots(session: Session, user, *, metric_type: str | None = None, limit: int = 50, offset: int = 0):
    from backend.schemas import Page
    rows, total = repo.list_snapshots(session, metric_type=metric_type, limit=limit, offset=offset)
    return Page.build([_snapshot_out(s) for s in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


# ================================================================== 4. trend analysis (reads warehouse history)
_TREND_FIELD_MAP = {
    "revenue": ("revenue", "revenue_ttm"),
    "pipeline": ("revenue", "pipeline_value"),
    "customer_growth": ("customers", "active_count"),
    "churn": ("customers", "churn_rate"),
    # ponytail: no dedicated "expansion" aggregate exists yet; renewal_rate is the closest
    # available proxy from cs_repo.churn_renewal_rates. Upgrade path: a real expansion-MRR
    # aggregate if this proves too coarse.
    "expansion": ("customers", "renewal_rate"),
    "campaign_performance": ("campaigns", "total_members"),
    "workflow_usage": ("workflow_metrics", "total"),
    "ai_usage": ("ai_metrics", "avg_engagement"),
}


def get_trend(session: Session, user, metric: str) -> TrendOut:
    mapping = _TREND_FIELD_MAP.get(metric)
    if not mapping:
        raise HTTPException(422, f"unknown trend metric: {metric}")
    metric_type, field = mapping
    rows, _total = repo.list_snapshots(session, metric_type=metric_type, limit=50)
    rows = list(reversed(rows))
    points = [TrendPointOut(period=_utc(r.snapshot_date).date().isoformat(), value=float((r.metrics or {}).get(field, 0) or 0)) for r in rows]
    growth = None
    if len(points) >= 2 and points[0].value:
        growth = round((points[-1].value - points[0].value) / abs(points[0].value), 4)
    return TrendOut(metric=metric, points=points, growth_rate=growth)


# ================================================================== 2. KPI framework
def _kpi_status(current: float | None, target: float | None) -> str:
    if target is None:
        return "no_target"
    if current is None:
        return "off_track"
    ratio = current / target if target else 0.0
    if ratio >= 0.9:
        return "on_track"
    if ratio >= 0.7:
        return "at_risk"
    return "off_track"


def _kpi_out(k, current_value: float | None) -> KpiOut:
    return KpiOut(
        id=k.id, name=k.name, category=k.category, target_value=k.target_value, unit=k.unit,
        current_value=current_value, status=_kpi_status(current_value, k.target_value),
        created_at=_utc(k.created_at), updated_at=_utc(k.updated_at),
    )


def create_kpi(session: Session, data: KpiCreate, user) -> KpiOut:
    _require_manager(user)
    if repo.get_kpi_by_name(session, data.name):
        raise HTTPException(409, "a KPI with this name already exists")
    k = repo.create_kpi(session, name=data.name, category=data.category, target_value=data.target_value, unit=data.unit, created_by=user.id)
    session.commit()
    return _kpi_out(k, None)


def list_kpis(session: Session, user, *, category: str | None = None) -> list[KpiOut]:
    kpis = repo.list_kpis(session, category=category)
    latest = repo.latest_kpi_values(session, [k.id for k in kpis])
    return [_kpi_out(k, latest.get(k.id)) for k in kpis]


def patch_kpi(session: Session, kpi_id: int, data: KpiPatch, user) -> KpiOut:
    _require_manager(user)
    k = repo.get_kpi(session, kpi_id)
    if not k:
        raise HTTPException(404, "KPI not found")
    for field in ("target_value", "unit"):
        val = getattr(data, field)
        if val is not None:
            setattr(k, field, val)
    session.commit()
    latest = repo.latest_kpi_values(session, [k.id])
    return _kpi_out(k, latest.get(k.id))


def delete_kpi(session: Session, kpi_id: int, user) -> None:
    _require_manager(user)
    if not repo.delete_kpi(session, kpi_id):
        raise HTTPException(404, "KPI not found")
    session.commit()


def record_kpi_value(session: Session, kpi_id: int, data: KpiValueIn, user) -> KpiValueOut:
    k = repo.get_kpi(session, kpi_id)
    if not k:
        raise HTTPException(404, "KPI not found")
    v = repo.create_kpi_value(session, kpi_id=kpi_id, value=data.value)
    session.commit()
    return KpiValueOut(id=v.id, kpi_id=v.kpi_id, value=v.value, recorded_at=_utc(v.recorded_at))


def kpi_history(session: Session, kpi_id: int, user, *, limit: int = 50) -> list[KpiValueOut]:
    if not repo.get_kpi(session, kpi_id):
        raise HTTPException(404, "KPI not found")
    return [KpiValueOut(id=v.id, kpi_id=v.kpi_id, value=v.value, recorded_at=_utc(v.recorded_at)) for v in repo.kpi_value_history(session, kpi_id, limit=limit)]


# ================================================================== 3. executive dashboards (reuse-only)
def executive_dashboard(session: Session, user, dashboard_type: str) -> BiExecutiveDashboardOut:
    if dashboard_type not in BI_DASHBOARD_TYPES:
        raise HTTPException(422, f"invalid dashboard_type: {dashboard_type}")
    if dashboard_type in ("revenue_overview", "pipeline_overview", "customer_overview"):
        ed = revops_service.executive_dashboard(session, user)
        if dashboard_type == "revenue_overview":
            metrics = {"revenue_ttm": ed.revenue_ttm, "pipeline_value": ed.pipeline_value, "weighted_forecast": ed.weighted_forecast, "win_rate": ed.win_rate}
        elif dashboard_type == "pipeline_overview":
            metrics = {"pipeline_value": ed.pipeline_value, "win_rate": ed.win_rate, "avg_sales_cycle_days": ed.avg_sales_cycle_days, "sales_velocity": ed.sales_velocity}
        else:
            metrics = {"arr": ed.arr, "mrr": ed.mrr, "active_customers": ed.active_customers, "churn_rate": ed.churn_rate, "expansion_accounts": ed.expansion_accounts}
    elif dashboard_type == "operations_overview":
        wf = workflow_repo.execution_stats(session)
        metrics = {"workflow_executions": wf["total"], "workflow_success": wf["success"], "active_workflows": workflow_repo.count_active_workflows(session)}
    elif dashboard_type == "ai_overview":
        metrics = {"insight_counts": ai_repo.insight_counts_by_type(session), "avg_engagement_score": ai_repo.avg_engagement_score(session) or 0.0, "active_risks": ai_repo.count_risks(session)}
    else:  # organization_overview
        metrics = {"active_users": admin_repo.count_active_users(session), "total_organizations": admin_repo.count_organizations(session)}
    return BiExecutiveDashboardOut(dashboard_type=dashboard_type, metrics=metrics, generated_at=_utcnow())


# ================================================================== 5/6. custom reports + scheduling
_REPORT_FILTER_ALLOWLIST = {
    "deal": {"pipeline_id", "stage_id", "owner_id", "forecast_category", "company_domain"},
    "customer": {"status", "tier", "owner_id", "lifecycle_stage"},
    "campaign": {"owner_id", "status", "campaign_type"},
}


def _deal_report_rows(session, filters):
    kwargs = {k: v for k, v in filters.items() if k in _REPORT_FILTER_ALLOWLIST["deal"]}
    rows, _ = deal_repo.list_deals(session, limit=500, **kwargs)
    return [{"id": r.id, "title": r.title, "value": r.value or 0.0, "stage_id": r.stage_id, "forecast_category": r.forecast_category, "owner_id": r.owner_id} for r in rows]


def _customer_report_rows(session, filters):
    kwargs = {k: v for k, v in filters.items() if k in _REPORT_FILTER_ALLOWLIST["customer"]}
    rows, _ = cs_repo.list_accounts(session, limit=500, **kwargs)
    return [{"id": r.id, "name": r.name, "arr": r.arr or 0.0, "status": r.status, "tier": r.tier, "lifecycle_stage": r.lifecycle_stage, "owner_id": r.owner_id} for r in rows]


def _campaign_report_rows(session, filters):
    kwargs = {k: v for k, v in filters.items() if k in _REPORT_FILTER_ALLOWLIST["campaign"]}
    rows, _ = campaign_repo.list_campaigns(session, limit=500, **kwargs)
    return [{"id": r.id, "name": r.name, "status": r.status, "campaign_type": r.campaign_type, "owner_id": r.owner_id} for r in rows]


_REPORT_ROW_SOURCES = {"deal": _deal_report_rows, "customer": _customer_report_rows, "campaign": _campaign_report_rows}


def _report_out(r) -> CustomReportOut:
    return CustomReportOut(
        id=r.id, name=r.name, entity_type=r.entity_type, filters=r.filters or {}, group_by=r.group_by,
        status=r.status, owner_id=r.owner_id, created_at=_utc(r.created_at), updated_at=_utc(r.updated_at),
    )


def create_report(session: Session, data: CustomReportCreate, user) -> CustomReportOut:
    if data.entity_type not in _REPORT_ROW_SOURCES:
        raise HTTPException(422, f"unsupported entity_type for reports: {data.entity_type}")
    r = repo.create_report(session, name=data.name, entity_type=data.entity_type, filters=data.filters, group_by=data.group_by, status="draft", owner_id=user.id)
    session.commit()
    return _report_out(r)


def list_reports(session: Session, user, *, owner_id: int | None = None, status: str | None = None) -> list[CustomReportOut]:
    return [_report_out(r) for r in repo.list_reports(session, owner_id=owner_id, status=status)]


def patch_report(session: Session, report_id: int, data: CustomReportPatch, user) -> CustomReportOut:
    r = repo.get_report(session, report_id)
    if not r:
        raise HTTPException(404, "report not found")
    if r.owner_id != user.id and not _is_manager(user):
        raise HTTPException(403, "only the report owner or a manager may edit this report")
    for field in ("name", "filters", "group_by", "status"):
        val = getattr(data, field)
        if val is not None:
            setattr(r, field, val)
    session.commit()
    return _report_out(r)


def delete_report(session: Session, report_id: int, user) -> None:
    r = repo.get_report(session, report_id)
    if not r:
        raise HTTPException(404, "report not found")
    if r.owner_id != user.id and not _is_manager(user):
        raise HTTPException(403, "only the report owner or a manager may delete this report")
    repo.delete_report(session, report_id)
    session.commit()


def run_report(session: Session, report_id: int, user) -> CustomReportResultOut:
    r = repo.get_report(session, report_id)
    if not r:
        raise HTTPException(404, "report not found")
    rows = _REPORT_ROW_SOURCES[r.entity_type](session, r.filters or {})
    if r.group_by and rows and r.group_by in rows[0]:
        grouped: dict = {}
        for row in rows:
            key = str(row.get(r.group_by))
            grouped[key] = grouped.get(key, 0) + 1
        return CustomReportResultOut(
            report_id=r.id, columns=[r.group_by, "count"],
            rows=[{r.group_by: k, "count": v} for k, v in grouped.items()], total_rows=len(rows),
        )
    columns = list(rows[0].keys()) if rows else []
    return CustomReportResultOut(report_id=r.id, columns=columns, rows=rows, total_rows=len(rows))


def _schedule_out(s) -> ReportScheduleOut:
    return ReportScheduleOut(
        id=s.id, report_id=s.report_id, frequency=s.frequency, recipient_emails=s.recipient_emails or [],
        is_enabled=s.is_enabled, last_run_at=_utc(s.last_run_at), created_at=_utc(s.created_at),
    )


def create_schedule(session: Session, report_id: int, data: ReportScheduleCreate, user) -> ReportScheduleOut:
    if not repo.get_report(session, report_id):
        raise HTTPException(404, "report not found")
    s = repo.create_schedule(session, report_id=report_id, frequency=data.frequency, recipient_emails=data.recipient_emails, is_enabled=data.is_enabled)
    session.commit()
    return _schedule_out(s)


def list_schedules(session: Session, user, *, report_id: int | None = None) -> list[ReportScheduleOut]:
    return [_schedule_out(s) for s in repo.list_schedules(session, report_id=report_id)]


def patch_schedule(session: Session, schedule_id: int, data: ReportSchedulePatch, user) -> ReportScheduleOut:
    s = repo.get_schedule(session, schedule_id)
    if not s:
        raise HTTPException(404, "schedule not found")
    for field in ("frequency", "recipient_emails", "is_enabled"):
        val = getattr(data, field)
        if val is not None:
            setattr(s, field, val)
    session.commit()
    return _schedule_out(s)


def delete_schedule(session: Session, schedule_id: int, user) -> None:
    if not repo.delete_schedule(session, schedule_id):
        raise HTTPException(404, "schedule not found")
    session.commit()


def _run_out(r) -> ScheduledReportRunOut:
    return ScheduledReportRunOut(id=r.id, schedule_id=r.schedule_id, status=r.status, row_count=r.row_count, detail=r.detail, run_at=_utc(r.run_at))


def deliver_schedule(session: Session, schedule_id: int, user) -> ScheduledReportRunOut:
    """Runs the schedule's report now and 'sends' it to every recipient via the existing
    mock/gmail email provider registry (Outreach's infra) — same pattern as webhook/
    connector delivery in Phase 10."""
    s = repo.get_schedule(session, schedule_id)
    if not s:
        raise HTTPException(404, "schedule not found")
    report = repo.get_report(session, s.report_id)
    if not report:
        raise HTTPException(404, "report not found")
    result = run_report(session, report.id, user)
    settings = get_settings()
    provider = get_provider(settings.outreach_mail_mode) or get_provider("mock")
    ok = True
    for email in (s.recipient_emails or []):
        send_result = provider.send(
            to_email=email, from_email=settings.outreach_from_email,
            subject=f"Scheduled Report: {report.name}", body=f"{result.total_rows} rows. Columns: {', '.join(result.columns)}",
        )
        ok = ok and send_result.ok
    run_status = "sent" if (ok and s.recipient_emails) else ("failed" if s.recipient_emails else "sent")
    run = repo.create_run(session, schedule_id=s.id, status=run_status, row_count=result.total_rows, detail=f"delivered to {len(s.recipient_emails or [])} recipients")
    s.last_run_at = _utcnow()
    session.commit()
    return _run_out(run)


def list_runs(session: Session, user, *, schedule_id: int | None = None, limit: int = 50) -> list[ScheduledReportRunOut]:
    return [_run_out(r) for r in repo.list_runs(session, schedule_id=schedule_id, limit=limit)]


@single_flight("report_schedule_tick")
def run_due_schedules(session: Session, user) -> dict:
    """Manual or cron-tick sweep of every enabled schedule — same pattern as
    workflow_service.run_sla_tick / integration_service.run_retry_tick. single_flight
    prevents two overlapping cron pokes from sending duplicate report emails."""
    results = [deliver_schedule(session, s.id, user) for s in repo.due_schedules(session)]
    return {"delivered": len(results)}


# ================================================================== 7/8. BI dashboard + analytics (cached)
_DASH_TTL_SECONDS = 60
_dash_cache: dict[str, tuple[float, BiDashboardOut]] = {}


def _cache_key(session: Session) -> str:
    try:
        return str(session.get_bind().url)
    except Exception:
        return "default"


def bi_dashboard(session: Session, user) -> BiDashboardOut:
    key = _cache_key(session)
    cached = _dash_cache.get(key)
    if cached and time.monotonic() - cached[0] < _DASH_TTL_SECONDS:
        return cached[1]

    kpis = list_kpis(session, user)
    trends = [get_trend(session, user, m) for m in ("revenue", "pipeline", "customer_growth")]
    exec_metrics = {dt: executive_dashboard(session, user, dt).metrics for dt in BI_DASHBOARD_TYPES}
    latest_snapshots = [repo.latest_snapshot(session, mt) for mt in WAREHOUSE_METRIC_TYPES]
    freshness_dates = [_utc(s.snapshot_date) for s in latest_snapshots if s]
    out = BiDashboardOut(
        kpis=kpis, trends=trends, executive_metrics=exec_metrics,
        scheduled_reports_count=repo.count_active_schedules(session),
        warehouse_snapshots_count=repo.total_snapshots(session),
        data_freshness=max(freshness_dates) if freshness_dates else None,
    )
    _dash_cache[key] = (time.monotonic(), out)
    return out


def bi_analytics(session: Session, user) -> BiAnalyticsOut:
    kpis = list_kpis(session, user)
    kpi_achievement = {k.name: round(k.current_value / k.target_value, 4) for k in kpis if k.target_value and k.current_value is not None}
    growth_rates = {}
    for m in _TREND_FIELD_MAP:
        t = get_trend(session, user, m)
        if t.growth_rate is not None:
            growth_rates[m] = t.growth_rate
    return BiAnalyticsOut(
        kpi_achievement=kpi_achievement,
        growth_rates=growth_rates,
        forecast_trends={m: t for m, t in growth_rates.items() if m in ("revenue", "pipeline")},
        report_usage=repo.report_status_counts(session),
        dashboard_usage=repo.snapshot_counts_by_type(session),
        warehouse_statistics=repo.snapshot_counts_by_type(session),
    )
