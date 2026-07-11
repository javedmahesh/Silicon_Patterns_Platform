"""Enterprise CRM Phase 5: Revenue Operations, Forecasting & Executive Analytics."""
from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import cs_repo
from backend import deal_service
from backend import revops_repo as repo
from backend.schemas import (
    BiSummaryOut,
    ExecutiveDashboardOut,
    ExecutiveReportOut,
    ForecastAccuracyOut,
    ForecastPeriodOut,
    ForecastSnapshotOut,
    FunnelAnalyticsOut,
    FunnelStageOut,
    Page,
    PipelineAgingOut,
    RevenueByDimensionOut,
    RevenueForecastOut,
    RevenueTargetCreate,
    RevenueTargetOut,
    RevopsPipelineAnalyticsOut,
    SalesPerformanceOut,
    TargetAttainmentOut,
)
from master_db.models import User

from backend.timeutil import utc as _utc, utcnow as _utcnow


def _is_manager(user) -> bool:
    return getattr(user, "role", "member") in ("admin", "manager")


def _require_manager(user) -> None:
    if not _is_manager(user):
        raise HTTPException(403, "manager or admin required")


def _load_user_emails(session: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = session.scalars(select(User).where(User.id.in_(ids))).all()
    return {u.id: u.email for u in rows}


def _period_key(dt: datetime, period_type: str) -> str:
    if period_type == "monthly":
        return f"{dt.year}-{dt.month:02d}"
    if period_type == "quarterly":
        return f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"
    return str(dt.year)


def _period_bounds(period_key: str, period_type: str) -> tuple[datetime, datetime]:
    if period_type == "monthly":
        year_s, month_s = period_key.split("-")
        year, month = int(year_s), int(month_s)
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        end_year = year + (month // 12)
        end_month = (month % 12) + 1
        end = datetime(end_year, end_month, 1, tzinfo=timezone.utc)
    elif period_type == "quarterly":
        year_s, q_s = period_key.split("-Q")
        year, q = int(year_s), int(q_s)
        start_month = (q - 1) * 3 + 1
        start = datetime(year, start_month, 1, tzinfo=timezone.utc)
        end_month = start_month + 3
        end_year = year + (end_month - 1) // 12
        end_month = ((end_month - 1) % 12) + 1
        end = datetime(end_year, end_month, 1, tzinfo=timezone.utc)
    else:
        year = int(period_key)
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    return start, end


# ================================================================== forecasting
def revenue_forecast(
    session: Session, user, *, period_type: str = "monthly", pipeline_id: int | None = None,
) -> RevenueForecastOut:
    deals = repo.open_deals(session, pipeline_id=pipeline_id)
    buckets: dict[str, dict] = defaultdict(lambda: {
        "pipeline_value": 0.0, "weighted_value": 0.0, "best_case_value": 0.0,
        "commit_value": 0.0, "deal_count": 0,
    })
    for d in deals:
        ecd = _utc(d.expected_close_date)
        if not ecd:
            continue
        b = buckets[_period_key(ecd, period_type)]
        value = d.value or 0.0
        b["pipeline_value"] += value
        b["weighted_value"] += value * (d.probability or 0) / 100.0
        b["deal_count"] += 1
        if d.forecast_category == "best_case":
            b["best_case_value"] += value
        elif d.forecast_category == "commit":
            b["commit_value"] += value

    periods = [
        ForecastPeriodOut(
            period_key=k, period_type=period_type,
            pipeline_value=round(b["pipeline_value"], 2),
            weighted_value=round(b["weighted_value"], 2),
            best_case_value=round(b["best_case_value"], 2),
            commit_value=round(b["commit_value"], 2),
            deal_count=b["deal_count"],
        )
        for k, b in sorted(buckets.items())
    ]
    return RevenueForecastOut(period_type=period_type, pipeline_id=pipeline_id, periods=periods)


def _snapshot_out(s) -> ForecastSnapshotOut:
    return ForecastSnapshotOut(
        id=s.id, pipeline_id=s.pipeline_id, period_type=s.period_type,
        period_key=s.period_key, category=s.category,
        forecasted_amount=s.forecasted_amount, snapshot_at=_utc(s.snapshot_at),
    )


def capture_forecast_snapshot(
    session: Session, user, *, period_type: str = "monthly", pipeline_id: int | None = None,
) -> list[ForecastSnapshotOut]:
    forecast = revenue_forecast(session, user, period_type=period_type, pipeline_id=pipeline_id)
    now_key = _period_key(_utcnow(), period_type)
    bucket = next((p for p in forecast.periods if p.period_key == now_key), None)
    if bucket is None:
        bucket = ForecastPeriodOut(period_key=now_key, period_type=period_type)

    amounts = {
        "pipeline": bucket.pipeline_value, "weighted": bucket.weighted_value,
        "best_case": bucket.best_case_value, "commit": bucket.commit_value,
    }
    out = []
    for category, amount in amounts.items():
        s = repo.create_snapshot(
            session, pipeline_id=pipeline_id, period_type=period_type,
            period_key=now_key, category=category, forecasted_amount=amount,
            created_by=user.id,
        )
        out.append(s)
    session.commit()
    return [_snapshot_out(s) for s in out]


def forecast_accuracy(
    session: Session, user, *, period_type: str | None = None, pipeline_id: int | None = None,
) -> list[ForecastAccuracyOut]:
    snapshots = repo.list_snapshots(session, pipeline_id=pipeline_id, period_type=period_type)
    now = _utcnow()
    out = []
    for s in snapshots:
        start, end = _period_bounds(s.period_key, s.period_type)
        if end > now:
            continue  # period hasn't elapsed yet — nothing to compare against
        actual = repo.closed_value_in_period(
            session, stage_type="won", start=start, end=end, pipeline_id=s.pipeline_id,
        )
        variance = actual - s.forecasted_amount
        if s.forecasted_amount:
            accuracy_pct = max(0.0, round(100 - abs(variance) / s.forecasted_amount * 100, 1))
        else:
            accuracy_pct = 100.0 if actual == 0 else 0.0
        out.append(ForecastAccuracyOut(
            snapshot_id=s.id, pipeline_id=s.pipeline_id, period_type=s.period_type,
            period_key=s.period_key, category=s.category,
            forecasted_amount=round(s.forecasted_amount, 2), actual_amount=round(actual, 2),
            variance=round(variance, 2), accuracy_pct=accuracy_pct,
        ))
    return out


# ================================================================== revenue targets
def _target_out(t, owner_email: str = "") -> RevenueTargetOut:
    return RevenueTargetOut(
        id=t.id, scope=t.scope, owner_id=t.owner_id, owner_email=owner_email,
        pipeline_id=t.pipeline_id, period_type=t.period_type,
        period_start=_utc(t.period_start), period_end=_utc(t.period_end),
        target_amount=t.target_amount, currency=t.currency, notes=t.notes,
        created_by=t.created_by, created_at=_utc(t.created_at), updated_at=_utc(t.updated_at),
    )


def list_targets(
    session: Session, user, *, scope: str | None = None, owner_id: int | None = None,
    period_type: str | None = None, limit: int = 50, offset: int = 0,
) -> Page:
    targets, total = repo.list_targets(
        session, scope=scope, owner_id=owner_id, period_type=period_type, limit=limit, offset=offset,
    )
    email_map = _load_user_emails(session, [t.owner_id for t in targets if t.owner_id])
    items = [_target_out(t, email_map.get(t.owner_id, "")) for t in targets]
    return Page.build(items, total, max(1, offset // limit + 1) if limit else 1, limit)


def create_target(session: Session, data: RevenueTargetCreate, user) -> RevenueTargetOut:
    _require_manager(user)
    t = repo.create_target(
        session, scope=data.scope, owner_id=data.owner_id, pipeline_id=data.pipeline_id,
        period_type=data.period_type, period_start=data.period_start, period_end=data.period_end,
        target_amount=data.target_amount, currency=data.currency, notes=data.notes,
        created_by=user.id,
    )
    session.commit()
    email_map = _load_user_emails(session, [t.owner_id] if t.owner_id else [])
    return _target_out(t, email_map.get(t.owner_id, ""))


def get_target(session: Session, target_id: int, user) -> RevenueTargetOut:
    t = repo.get_target(session, target_id)
    if not t:
        raise HTTPException(404, "target not found")
    email_map = _load_user_emails(session, [t.owner_id] if t.owner_id else [])
    return _target_out(t, email_map.get(t.owner_id, ""))


def delete_target(session: Session, target_id: int, user) -> None:
    _require_manager(user)
    if not repo.delete_target(session, target_id):
        raise HTTPException(404, "target not found")
    session.commit()


def target_attainment(session: Session, target_id: int, user) -> TargetAttainmentOut:
    t = repo.get_target(session, target_id)
    if not t:
        raise HTTPException(404, "target not found")
    start, end = _utc(t.period_start), _utc(t.period_end)
    actual = repo.closed_value_in_period(
        session, stage_type="won", start=start, end=end,
        owner_id=t.owner_id if t.scope == "individual" else None,
        pipeline_id=t.pipeline_id,
    )
    pct = round(actual / t.target_amount * 100, 1) if t.target_amount else 0.0
    return TargetAttainmentOut(
        target_id=t.id, target_amount=t.target_amount, actual_amount=round(actual, 2),
        attainment_pct=pct, period_start=start, period_end=end, is_elapsed=end <= _utcnow(),
    )


# ================================================================== executive dashboard (cached)
_DASH_TTL_SECONDS = 60
_dash_cache: dict[str, tuple[float, ExecutiveDashboardOut]] = {}


def _dash_cache_key(session: Session) -> str:
    try:
        return str(session.get_bind().url)
    except Exception:
        return "default"


def executive_dashboard(session: Session, user) -> ExecutiveDashboardOut:
    cache_key = _dash_cache_key(session)
    cached = _dash_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < _DASH_TTL_SECONDS:
        return cached[1]

    now = _utcnow()
    revenue_ttm = repo.closed_value_in_period(
        session, stage_type="won", start=now - timedelta(days=365), end=now,
    )

    counts = repo.company_wide_deal_counts(session)
    closed = counts["won"] + counts["lost"]
    win_rate = round(counts["won"] / closed, 4) if closed else 0.0

    open_deals = repo.open_deals(session)
    pipeline_value = round(sum(d.value or 0 for d in open_deals), 2)
    weighted_forecast = round(sum((d.value or 0) * (d.probability or 0) / 100.0 for d in open_deals), 2)

    cycle_seconds = repo.won_deal_cycle_seconds(session)
    avg_cycle = round(sum(cycle_seconds) / len(cycle_seconds) / 86400, 1) if cycle_seconds else None
    sales_velocity = round(pipeline_value / avg_cycle, 2) if avg_cycle else None

    cs_totals = cs_repo.arr_mrr_totals(session)
    cs_churn = cs_repo.churn_renewal_rates(session)
    expansion = cs_repo.expansion_pipeline(session)

    out = ExecutiveDashboardOut(
        revenue_ttm=round(revenue_ttm, 2), pipeline_value=pipeline_value,
        weighted_forecast=weighted_forecast, win_rate=win_rate, conversion_rate=win_rate,
        sales_velocity=sales_velocity, avg_sales_cycle_days=avg_cycle,
        arr=cs_totals["total_arr"], mrr=cs_totals["total_mrr"],
        active_customers=cs_totals["active_count"], churn_rate=cs_churn["churn_rate"],
        expansion_accounts=len(expansion), generated_at=now,
    )
    _dash_cache[cache_key] = (time.monotonic(), out)
    return out


# ================================================================== pipeline analytics (aging/health/reasons)
_AGE_BUCKETS = (("0-7d", 7), ("8-14d", 14), ("15-30d", 30), ("31-60d", 60), ("60d+", None))


def pipeline_analytics(session: Session, user, *, pipeline_id: int | None = None) -> RevopsPipelineAnalyticsOut:
    counts = repo.company_wide_deal_counts(session, pipeline_id=pipeline_id)
    closed = counts["won"] + counts["lost"]
    win_rate = round(counts["won"] / closed, 4) if closed else 0.0
    loss_rate = round(counts["lost"] / closed, 4) if closed else 0.0

    open_deals = repo.open_deals(session, pipeline_id=pipeline_id)
    pipeline_value = round(sum(d.value or 0 for d in open_deals), 2)
    weighted_pipeline = round(sum((d.value or 0) * (d.probability or 0) / 100.0 for d in open_deals), 2)

    ages = repo.open_deal_ages_days(session, pipeline_id=pipeline_id)
    bucket_counts = {label: 0 for label, _ in _AGE_BUCKETS}
    for age in ages:
        for label, ceiling in _AGE_BUCKETS:
            if ceiling is None or age <= ceiling:
                bucket_counts[label] += 1
                break
    aging = [PipelineAgingOut(bucket=label, deal_count=cnt) for label, cnt in bucket_counts.items()]

    stalled_ratio = bucket_counts["31-60d"] + bucket_counts["60d+"]
    open_n = max(1, counts["open"])
    health_score = round(max(0.0, min(100.0, win_rate * 60 + (1 - stalled_ratio / open_n) * 40)), 1)

    stage_velocity = []
    if pipeline_id is not None:
        # Reuse the existing per-pipeline stage-velocity/conversion logic verbatim.
        base = deal_service.pipeline_analytics(session, pipeline_id, user)
        stage_velocity = base.stage_velocity

    return RevopsPipelineAnalyticsOut(
        pipeline_id=pipeline_id,
        total_deals=counts["open"] + counts["won"] + counts["lost"],
        open_deals=counts["open"], won_deals=counts["won"], lost_deals=counts["lost"],
        win_rate=win_rate, loss_rate=loss_rate,
        pipeline_value=pipeline_value, weighted_pipeline=weighted_pipeline,
        pipeline_health_score=health_score, aging=aging,
        lost_reasons=repo.lost_reason_counts(session, pipeline_id=pipeline_id),
        won_reasons=repo.won_reason_counts(session, pipeline_id=pipeline_id),
        stage_velocity=stage_velocity,
    )


# ================================================================== sales performance
def _dim_out(rows, fallback: str = "unknown") -> list[RevenueByDimensionOut]:
    return [
        RevenueByDimensionOut(key=str(key) if key else fallback, deal_count=cnt, revenue=round(float(val), 2))
        for key, cnt, val in rows
    ]


def sales_performance(session: Session, user, *, pipeline_id: int | None = None) -> SalesPerformanceOut:
    owner_rows = repo.revenue_by_owner(session, pipeline_id=pipeline_id)
    email_map = _load_user_emails(session, [r[0] for r in owner_rows if r[0]])
    by_owner = [
        RevenueByDimensionOut(
            key=email_map.get(oid, "unassigned") if oid else "unassigned",
            deal_count=cnt, revenue=round(float(val), 2),
        )
        for oid, cnt, val in owner_rows
    ]

    counts = repo.company_wide_deal_counts(session, pipeline_id=pipeline_id)
    closed = counts["won"] + counts["lost"]
    cycle_seconds = repo.won_deal_cycle_seconds(session, pipeline_id=pipeline_id)

    return SalesPerformanceOut(
        by_owner=by_owner,
        by_team=_dim_out(repo.revenue_by_role(session, pipeline_id=pipeline_id), "unassigned"),
        by_region=_dim_out(repo.revenue_by_country(session, pipeline_id=pipeline_id)),
        by_industry=_dim_out(repo.revenue_by_cs_dimension(session, "industry", pipeline_id=pipeline_id)),
        by_tier=_dim_out(repo.revenue_by_cs_dimension(session, "tier", pipeline_id=pipeline_id)),
        avg_deal_size=round(counts["won_val"] / counts["won"], 2) if counts["won"] else 0.0,
        avg_sales_cycle_days=round(sum(cycle_seconds) / len(cycle_seconds) / 86400, 1) if cycle_seconds else None,
        close_rate=round(counts["won"] / closed, 4) if closed else 0.0,
    )


# ================================================================== funnel analytics
def _funnel_stages(pairs: list[tuple[str, int]]) -> list[FunnelStageOut]:
    stages, prev = [], None
    for name, count in pairs:
        drop = round((1 - count / prev) * 100, 1) if prev else None
        stages.append(FunnelStageOut(stage=name, count=count, drop_off_pct=drop))
        prev = count if count else prev
    return stages


_LEAD_FUNNEL_ORDER = ("new", "assigned", "contacted", "qualified", "proposal", "won")
_DEAL_FUNNEL_ORDER = ("open", "won", "lost")


def funnel_analytics(session: Session, user) -> FunnelAnalyticsOut:
    lead_counts = repo.lead_funnel_counts(session)
    lead_funnel = _funnel_stages([(name, lead_counts.get(name, 0)) for name in _LEAD_FUNNEL_ORDER])

    opp = repo.opportunity_funnel_counts(session)
    opp_funnel = _funnel_stages([
        ("discovered", opp["total_opportunities"]),
        ("linked_to_deal", opp["linked_to_deal"]),
        ("won", opp["won"]),
    ])

    deal_counts = repo.company_wide_deal_counts(session)
    deal_funnel = _funnel_stages([(name, deal_counts[name]) for name in _DEAL_FUNNEL_ORDER])

    camp = repo.campaign_funnel_counts(session)
    campaign_funnel = (
        [FunnelStageOut(stage=f"status:{k}", count=v) for k, v in camp["by_status"].items()]
        + [FunnelStageOut(stage=f"outcome:{k or 'pending'}", count=v) for k, v in camp["by_outcome"].items()]
    )

    return FunnelAnalyticsOut(
        lead_funnel=lead_funnel, opportunity_funnel=opp_funnel,
        deal_funnel=deal_funnel, campaign_funnel=campaign_funnel,
    )


# ================================================================== executive reports + BI
_REPORT_TYPES = ("revenue", "forecast", "team", "pipeline", "customer", "campaign")


def executive_report(session: Session, user, report_type: str) -> ExecutiveReportOut:
    if report_type not in _REPORT_TYPES:
        raise HTTPException(404, f"unknown report type: {report_type}")

    if report_type == "revenue":
        dash = executive_dashboard(session, user)
        data = {
            "revenue_ttm": dash.revenue_ttm, "arr": dash.arr, "mrr": dash.mrr,
            "pipeline_value": dash.pipeline_value, "weighted_forecast": dash.weighted_forecast,
        }
    elif report_type == "forecast":
        data = revenue_forecast(session, user, period_type="quarterly").model_dump()
    elif report_type == "team":
        perf = sales_performance(session, user)
        data = {
            "by_owner": [r.model_dump() for r in perf.by_owner],
            "by_team": [r.model_dump() for r in perf.by_team],
        }
    elif report_type == "pipeline":
        data = pipeline_analytics(session, user).model_dump()
    elif report_type == "customer":
        data = cs_repo.arr_mrr_totals(session) | cs_repo.churn_renewal_rates(session)
    else:  # campaign
        data = repo.campaign_funnel_counts(session)

    return ExecutiveReportOut(report_type=report_type, generated_at=_utcnow(), data=data)


def bi_summary(session: Session, user) -> BiSummaryOut:
    since = _utcnow() - timedelta(days=180)
    monthly: dict[str, float] = defaultdict(float)
    for updated_at, value in repo.won_deals_with_value(session, since=since):
        monthly[_period_key(_utc(updated_at), "monthly")] += value or 0.0
    trend = [{"period": k, "revenue": round(v, 2)} for k, v in sorted(monthly.items())]

    return BiSummaryOut(
        executive_dashboard=executive_dashboard(session, user),
        funnels=funnel_analytics(session, user),
        sales_performance=sales_performance(session, user),
        revenue_trend=trend,
    )
