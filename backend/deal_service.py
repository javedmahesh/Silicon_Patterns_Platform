"""Enterprise CRM Phase 2: Pipeline & Deal Management business logic."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import deal_repo as repo
from backend import workflow_service
from backend.schemas import (
    DealAnalyticsOut,
    DealCreate,
    DealDashboardOut,
    DealIntelligenceOut,
    DealOut,
    DealPatch,
    DealStageHistoryOut,
    ForecastByOwnerOut,
    ForecastByQuarterOut,
    ForecastOut,
    KanbanColumnOut,
    KanbanOut,
    Page,
    PipelineCreate,
    PipelineOut,
    PipelinePatch,
    PipelineStageCreate,
    PipelineStageOut,
    PipelineStagePatch,
    StageVelocityOut,
    UnifiedTimelineEvent,
)
from master_db.models import (
    CrmDeal,
    CrmDealStageHistory,
    CrmPipeline,
    CrmPipelineStage,
    User,
)

from backend.timeutil import utc as _utc, utcnow as _utcnow


def _is_manager(user) -> bool:
    return getattr(user, "role", "member") in ("admin", "manager")


def _require_manager(user) -> None:
    if not _is_manager(user):
        raise HTTPException(403, "manager or admin required")


# ----------------------------------------------------------------- serializers
def _pipeline_out(p: CrmPipeline, stages: list[CrmPipelineStage] | None = None) -> PipelineOut:
    return PipelineOut(
        id=p.id, name=p.name, description=p.description,
        is_default=p.is_default, is_active=p.is_active,
        created_by=p.created_by,
        stage_count=len(stages) if stages is not None else 0,
        stages=[_stage_out(s) for s in (stages or [])],
        created_at=_utc(p.created_at), updated_at=_utc(p.updated_at),
    )


def _stage_out(s: CrmPipelineStage) -> PipelineStageOut:
    return PipelineStageOut(
        id=s.id, pipeline_id=s.pipeline_id, name=s.name,
        stage_type=s.stage_type, stage_order=s.stage_order,
        probability=s.probability, created_at=_utc(s.created_at),
    )


def _deal_out(d: CrmDeal, stage_name: str = "", owner_email: str = "") -> DealOut:
    return DealOut(
        id=d.id, title=d.title, company_domain=d.company_domain,
        opportunity_id=d.opportunity_id, pipeline_id=d.pipeline_id,
        stage_id=d.stage_id, stage_name=stage_name,
        owner_id=d.owner_id, owner_email=owner_email,
        created_by=d.created_by,
        value=d.value, currency=d.currency, probability=d.probability,
        forecast_category=d.forecast_category,
        expected_close_date=_utc(d.expected_close_date),
        last_activity_at=_utc(d.last_activity_at),
        tags=list(d.tags or []), notes=d.notes,
        lost_reason=d.lost_reason, won_reason=d.won_reason,
        created_at=_utc(d.created_at), updated_at=_utc(d.updated_at),
    )


def _history_out(h: CrmDealStageHistory) -> DealStageHistoryOut:
    return DealStageHistoryOut(
        id=h.id, deal_id=h.deal_id,
        from_stage_id=h.from_stage_id, to_stage_id=h.to_stage_id,
        entered_at=_utc(h.entered_at), exited_at=_utc(h.exited_at),
        time_in_stage_seconds=h.time_in_stage_seconds,
        changed_by=h.changed_by, created_at=_utc(h.created_at),
    )


def _load_stage_map(session: Session, stage_ids: list[int]) -> dict[int, CrmPipelineStage]:
    if not stage_ids:
        return {}
    from sqlalchemy import select
    rows = session.scalars(
        select(CrmPipelineStage).where(CrmPipelineStage.id.in_(stage_ids))
    ).all()
    return {s.id: s for s in rows}


def _load_user_emails(session: Session, user_ids: list[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    from sqlalchemy import select
    rows = session.scalars(select(User).where(User.id.in_(user_ids))).all()
    return {u.id: u.email for u in rows}


# ================================================================== pipelines
def list_pipelines(
    session: Session, user, *, active_only: bool = False,
    limit: int = 50, offset: int = 0,
) -> Page:
    pipelines, total = repo.list_pipelines(session, active_only=active_only, limit=limit, offset=offset)
    stages_by_pipeline = repo.list_stages_batch(session, [p.id for p in pipelines])
    items = [_pipeline_out(p, stages_by_pipeline.get(p.id, [])) for p in pipelines]
    return Page.build(items, total, max(1, offset // limit + 1), limit)


def create_pipeline(session: Session, data: PipelineCreate, user) -> PipelineOut:
    p = repo.create_pipeline(
        session, name=data.name, description=data.description or "",
        is_default=data.is_default, created_by=user.id,
    )
    # Seed stages if provided
    for i, s in enumerate(data.stages or []):
        repo.add_stage(
            session, pipeline_id=p.id, name=s.name,
            stage_type=s.stage_type, stage_order=s.stage_order if s.stage_order else i + 1,
            probability=s.probability,
        )
    session.commit()
    stages = repo.list_stages(session, p.id)
    return _pipeline_out(p, stages)


def get_pipeline(session: Session, pipeline_id: int, user) -> PipelineOut:
    p = repo.get_pipeline(session, pipeline_id)
    if not p:
        raise HTTPException(404, "pipeline not found")
    stages = repo.list_stages(session, pipeline_id)
    return _pipeline_out(p, stages)


def patch_pipeline(session: Session, pipeline_id: int, data: PipelinePatch, user) -> PipelineOut:
    p = repo.get_pipeline(session, pipeline_id)
    if not p:
        raise HTTPException(404, "pipeline not found")
    if data.name is not None:
        p.name = data.name
    if data.description is not None:
        p.description = data.description
    if data.is_default is not None:
        p.is_default = data.is_default
    if data.is_active is not None:
        p.is_active = data.is_active
    session.commit()
    stages = repo.list_stages(session, pipeline_id)
    return _pipeline_out(p, stages)


def delete_pipeline(session: Session, pipeline_id: int, user) -> None:
    _require_manager(user)
    p = repo.get_pipeline(session, pipeline_id)
    if not p:
        raise HTTPException(404, "pipeline not found")
    session.delete(p)
    session.commit()


# ================================================================== stages
def add_stage(session: Session, pipeline_id: int, data: PipelineStageCreate, user) -> PipelineStageOut:
    p = repo.get_pipeline(session, pipeline_id)
    if not p:
        raise HTTPException(404, "pipeline not found")
    s = repo.add_stage(
        session, pipeline_id=pipeline_id, name=data.name,
        stage_type=data.stage_type, stage_order=data.stage_order,
        probability=data.probability,
    )
    session.commit()
    return _stage_out(s)


def patch_stage(
    session: Session, pipeline_id: int, stage_id: int, data: PipelineStagePatch, user
) -> PipelineStageOut:
    s = repo.get_stage(session, stage_id)
    if not s or s.pipeline_id != pipeline_id:
        raise HTTPException(404, "stage not found")
    if data.name is not None:
        s.name = data.name
    if data.stage_type is not None:
        s.stage_type = data.stage_type
    if data.stage_order is not None:
        s.stage_order = data.stage_order
    if data.probability is not None:
        s.probability = data.probability
    session.commit()
    return _stage_out(s)


def delete_stage(session: Session, pipeline_id: int, stage_id: int, user) -> None:
    _require_manager(user)
    s = repo.get_stage(session, stage_id)
    if not s or s.pipeline_id != pipeline_id:
        raise HTTPException(404, "stage not found")
    repo.delete_stage(session, stage_id)
    session.commit()


# ================================================================== deals
def list_deals(
    session: Session, user, *,
    pipeline_id: int | None = None,
    stage_id: int | None = None,
    owner_id: int | None = None,
    company_domain: str | None = None,
    search: str | None = None,
    forecast_category: str | None = None,
    closing_before: datetime | None = None,
    closing_after: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> Page:
    deals, total = repo.list_deals(
        session, pipeline_id=pipeline_id, stage_id=stage_id,
        owner_id=owner_id, company_domain=company_domain, search=search,
        forecast_category=forecast_category,
        closing_before=closing_before, closing_after=closing_after,
        limit=limit, offset=offset,
    )
    stage_ids = list({d.stage_id for d in deals})
    owner_ids = list({d.owner_id for d in deals if d.owner_id})
    stage_map = _load_stage_map(session, stage_ids)
    user_map = _load_user_emails(session, owner_ids)
    items = [
        _deal_out(d, stage_name=stage_map[d.stage_id].name if d.stage_id in stage_map else "",
                  owner_email=user_map.get(d.owner_id, "") if d.owner_id else "")
        for d in deals
    ]
    return Page.build(items, total, max(1, offset // limit + 1), limit)


def create_deal(session: Session, data: DealCreate, user) -> DealOut:
    # Validate pipeline + stage belong together
    stage = repo.get_stage(session, data.stage_id)
    if not stage:
        raise HTTPException(400, "stage not found")
    if stage.pipeline_id != data.pipeline_id:
        raise HTTPException(400, "stage does not belong to pipeline")

    now = _utcnow()
    d = repo.create_deal(
        session,
        title=data.title, company_domain=data.company_domain,
        opportunity_id=data.opportunity_id,
        pipeline_id=data.pipeline_id, stage_id=data.stage_id,
        owner_id=data.owner_id or user.id, created_by=user.id,
        value=data.value, currency=data.currency,
        probability=data.probability if data.probability is not None else stage.probability,
        forecast_category=data.forecast_category,
        expected_close_date=data.expected_close_date,
        tags=data.tags, notes=data.notes or "",
        lost_reason=data.lost_reason or "", won_reason=data.won_reason or "",
        last_activity_at=now,
    )
    # Initial stage history entry
    repo.add_stage_history(
        session, deal_id=d.id, from_stage_id=None, to_stage_id=data.stage_id,
        entered_at=now, changed_by=user.id,
    )
    workflow_service.fire_event(
        session, "deal_created", "deal", d.id,
        {"value": d.value, "owner_id": d.owner_id, "company_domain": d.company_domain,
         "pipeline_id": d.pipeline_id, "stage_type": stage.stage_type, "title": d.title},
        actor=user,
    )
    session.commit()
    owner_email = _load_user_emails(session, [d.owner_id] if d.owner_id else []).get(d.owner_id, "")
    return _deal_out(d, stage_name=stage.name, owner_email=owner_email)


def get_deal(session: Session, deal_id: int, user) -> DealOut:
    d = repo.get_deal(session, deal_id)
    if not d:
        raise HTTPException(404, "deal not found")
    stage = repo.get_stage(session, d.stage_id)
    owner_email = _load_user_emails(session, [d.owner_id] if d.owner_id else []).get(d.owner_id, "")
    return _deal_out(d, stage_name=stage.name if stage else "", owner_email=owner_email)


def patch_deal(session: Session, deal_id: int, data: DealPatch, user) -> DealOut:
    d = repo.get_deal(session, deal_id)
    if not d:
        raise HTTPException(404, "deal not found")
    if data.title is not None:
        d.title = data.title
    if data.value is not None:
        d.value = data.value
    if data.currency is not None:
        d.currency = data.currency
    if data.probability is not None:
        d.probability = data.probability
    if data.forecast_category is not None:
        d.forecast_category = data.forecast_category
    if data.expected_close_date is not None:
        d.expected_close_date = data.expected_close_date
    if data.owner_id is not None:
        d.owner_id = data.owner_id
    if data.tags is not None:
        d.tags = data.tags
    if data.lost_reason is not None:
        d.lost_reason = data.lost_reason
    if data.won_reason is not None:
        d.won_reason = data.won_reason
    if data.notes is not None:
        d.notes = data.notes
    if data.opportunity_id is not None:
        d.opportunity_id = data.opportunity_id
    d.last_activity_at = _utcnow()
    session.commit()
    stage = repo.get_stage(session, d.stage_id)
    owner_email = _load_user_emails(session, [d.owner_id] if d.owner_id else []).get(d.owner_id, "")
    return _deal_out(d, stage_name=stage.name if stage else "", owner_email=owner_email)


def delete_deal(session: Session, deal_id: int, user) -> None:
    _require_manager(user)
    d = repo.get_deal(session, deal_id)
    if not d:
        raise HTTPException(404, "deal not found")
    session.delete(d)
    session.commit()


def move_deal(session: Session, deal_id: int, stage_id: int, user) -> DealOut:
    """Move a deal to a new stage (Kanban drag & drop). Logs stage history."""
    d = repo.get_deal(session, deal_id)
    if not d:
        raise HTTPException(404, "deal not found")
    new_stage = repo.get_stage(session, stage_id)
    if not new_stage:
        raise HTTPException(400, "target stage not found")
    if new_stage.pipeline_id != d.pipeline_id:
        raise HTTPException(400, "stage belongs to a different pipeline")

    owner_email = _load_user_emails(session, [d.owner_id] if d.owner_id else []).get(d.owner_id, "")

    if d.stage_id == stage_id:
        return _deal_out(d, stage_name=new_stage.name, owner_email=owner_email)

    old_stage = repo.get_stage(session, d.stage_id)
    now = _utcnow()
    # Close current open history entry
    old_hist = repo.get_open_history(session, deal_id)
    if old_hist:
        old_hist.exited_at = now
        entered = _utc(old_hist.entered_at) or now
        old_hist.time_in_stage_seconds = max(0, int((now - entered).total_seconds()))

    # New history entry
    repo.add_stage_history(
        session, deal_id=deal_id,
        from_stage_id=d.stage_id, to_stage_id=stage_id,
        entered_at=now, changed_by=user.id,
    )

    d.stage_id = stage_id
    d.probability = new_stage.probability
    d.last_activity_at = now

    fields = {"value": d.value, "owner_id": d.owner_id, "company_domain": d.company_domain,
              "pipeline_id": d.pipeline_id, "stage_type": new_stage.stage_type,
              "old_stage_type": old_stage.stage_type if old_stage else "", "title": d.title}
    workflow_service.fire_event(session, "deal_stage_changed", "deal", d.id, fields, actor=user)
    if new_stage.stage_type == "won":
        workflow_service.fire_event(session, "deal_won", "deal", d.id, fields, actor=user)
    elif new_stage.stage_type == "lost":
        workflow_service.fire_event(session, "deal_lost", "deal", d.id, fields, actor=user)

    session.commit()
    return _deal_out(d, stage_name=new_stage.name, owner_email=owner_email)


def deal_stage_history(session: Session, deal_id: int, user) -> list[DealStageHistoryOut]:
    if not repo.get_deal(session, deal_id):
        raise HTTPException(404, "deal not found")
    return [_history_out(h) for h in repo.list_stage_history(session, deal_id)]


# ================================================================== kanban
def kanban(
    session: Session, pipeline_id: int, user, *,
    stage_id: int | None = None,
    owner_id: int | None = None,
    search: str | None = None,
) -> KanbanOut:
    p = repo.get_pipeline(session, pipeline_id)
    if not p:
        raise HTTPException(404, "pipeline not found")
    all_stages = repo.list_stages(session, pipeline_id)
    stages = [s for s in all_stages if stage_id is None or s.id == stage_id]
    stage_ids = [s.id for s in stages]

    deals = repo.list_deals_for_stages(session, stage_ids, owner_id=owner_id, search=search)
    owner_ids = list({d.owner_id for d in deals if d.owner_id})
    user_map = _load_user_emails(session, owner_ids)

    deals_by_stage: dict[int, list[CrmDeal]] = defaultdict(list)
    for d in deals:
        deals_by_stage[d.stage_id].append(d)

    columns = [
        KanbanColumnOut(
            stage_id=s.id, stage_name=s.name, stage_type=s.stage_type,
            stage_order=s.stage_order,
            deal_count=len(deals_by_stage[s.id]),
            total_value=sum(d.value for d in deals_by_stage[s.id] if d.value),
            deals=[
                _deal_out(d, stage_name=s.name,
                          owner_email=user_map.get(d.owner_id, "") if d.owner_id else "")
                for d in deals_by_stage[s.id]
            ],
        )
        for s in stages
    ]

    return KanbanOut(
        pipeline_id=pipeline_id, pipeline_name=p.name,
        columns=columns,
        total_deals=sum(c.deal_count for c in columns),
        total_value=sum(c.total_value for c in columns),
    )


# ================================================================== forecast
def forecast(session: Session, pipeline_id: int, user) -> ForecastOut:
    p = repo.get_pipeline(session, pipeline_id)
    if not p:
        raise HTTPException(404, "pipeline not found")

    stages = repo.list_stages(session, pipeline_id)
    won_ids = {s.id for s in stages if s.stage_type == "won"}
    lost_ids = {s.id for s in stages if s.stage_type == "lost"}
    open_ids = {s.id for s in stages if s.stage_type == "open"}

    all_deals, _ = repo.list_deals(session, pipeline_id=pipeline_id, limit=10_000)
    open_deals = [d for d in all_deals if d.stage_id in open_ids]
    won_deals = [d for d in all_deals if d.stage_id in won_ids]
    lost_deals = [d for d in all_deals if d.stage_id in lost_ids]
    closed = won_deals + lost_deals

    pipeline_value = sum(d.value or 0 for d in open_deals)
    weighted_pipeline = sum((d.value or 0) * d.probability / 100.0 for d in open_deals)
    expected_revenue = sum(
        (d.value or 0) * d.probability / 100.0
        for d in open_deals
        if d.forecast_category in ("commit", "best_case")
    )
    win_probability = round(len(won_deals) / len(closed) * 100, 1) if closed else 0.0
    avg_deal_size = (
        sum(d.value or 0 for d in won_deals) / len(won_deals) if won_deals else 0.0
    )

    # Forecast by quarter (weighted value of open deals)
    by_quarter: dict[str, float] = defaultdict(float)
    for d in open_deals:
        if d.expected_close_date and d.value:
            ecd = _utc(d.expected_close_date)
            if ecd:
                q = f"Q{(ecd.month - 1) // 3 + 1} {ecd.year}"
                by_quarter[q] += d.value * d.probability / 100.0

    # Forecast by owner (weighted value of open deals)
    by_owner_val: dict[int, float] = defaultdict(float)
    for d in open_deals:
        if d.owner_id and d.value:
            by_owner_val[d.owner_id] += d.value * d.probability / 100.0
    owner_ids = list(by_owner_val.keys())
    user_map = _load_user_emails(session, owner_ids)

    # Average sales cycle: mean days from deal created_at to exited_at of won stage
    cycle_days: list[float] = []
    for d in won_deals:
        hist = repo.list_stage_history(session, d.id)
        won_exit = next(
            (h for h in reversed(hist) if h.to_stage_id in won_ids and h.exited_at), None
        )
        entered_won = next(
            (h for h in hist if h.to_stage_id in won_ids), None
        )
        if entered_won:
            ref_exit = _utc(entered_won.entered_at)
            ref_start = _utc(d.created_at)
            if ref_exit and ref_start:
                cycle_days.append((ref_exit - ref_start).total_seconds() / 86400)

    avg_sales_cycle_days = round(sum(cycle_days) / len(cycle_days), 1) if cycle_days else None
    pipeline_velocity = (
        round(pipeline_value / avg_sales_cycle_days, 2)
        if avg_sales_cycle_days and avg_sales_cycle_days > 0
        else None
    )

    return ForecastOut(
        pipeline_id=pipeline_id,
        pipeline_value=round(pipeline_value, 2),
        weighted_pipeline=round(weighted_pipeline, 2),
        expected_revenue=round(expected_revenue, 2),
        win_probability=win_probability,
        avg_deal_size=round(avg_deal_size, 2),
        avg_sales_cycle_days=avg_sales_cycle_days,
        pipeline_velocity=pipeline_velocity,
        open_deals=len(open_deals),
        won_deals=len(won_deals),
        lost_deals=len(lost_deals),
        forecast_by_quarter=[
            ForecastByQuarterOut(quarter=q, weighted_value=round(v, 2))
            for q, v in sorted(by_quarter.items())
        ],
        forecast_by_owner=[
            ForecastByOwnerOut(
                owner_id=uid, owner_email=user_map.get(uid, ""),
                weighted_value=round(v, 2),
            )
            for uid, v in sorted(by_owner_val.items(), key=lambda x: -x[1])
        ],
    )


# ================================================================== analytics
def pipeline_analytics(session: Session, pipeline_id: int, user) -> DealAnalyticsOut:
    p = repo.get_pipeline(session, pipeline_id)
    if not p:
        raise HTTPException(404, "pipeline not found")

    stages = repo.list_stages(session, pipeline_id)
    stage_ids = [s.id for s in stages]
    won_ids = {s.id for s in stages if s.stage_type == "won"}
    lost_ids = {s.id for s in stages if s.stage_type == "lost"}
    open_ids = {s.id for s in stages if s.stage_type == "open"}
    stage_name_map = {s.id: s.name for s in stages}

    counts = repo.pipeline_deal_counts(session, pipeline_id)
    closed = counts["won"] + counts["lost"]
    win_rate = round(counts["won"] / closed, 4) if closed else 0.0
    loss_rate = round(counts["lost"] / closed, 4) if closed else 0.0

    # Average time per stage
    avg_times = repo.avg_time_per_stage(session, pipeline_id)

    # Stage conversion matrix (how many deals moved from each stage to the next)
    # We approximate: deals that exited a stage (time_in_stage_seconds is set) / deals that entered
    from sqlalchemy import func, select
    from master_db.models import CrmDealStageHistory
    entered_rows = session.execute(
        select(
            CrmDealStageHistory.to_stage_id,
            func.count(CrmDealStageHistory.id).label("entered"),
            func.count(CrmDealStageHistory.id).filter(
                CrmDealStageHistory.exited_at.isnot(None)
            ).label("exited"),
        )
        .join(CrmDeal, CrmDeal.id == CrmDealStageHistory.deal_id)
        .where(CrmDeal.pipeline_id == pipeline_id)
        .group_by(CrmDealStageHistory.to_stage_id)
    ).all()
    entered_map = {r.to_stage_id: (r.entered, r.exited) for r in entered_rows}

    stage_velocity = [
        StageVelocityOut(
            stage_id=s.id,
            stage_name=stage_name_map[s.id],
            stage_type=s.stage_type,
            stage_order=s.stage_order,
            avg_time_days=round(avg_times.get(s.id, 0) / 86400, 1),
            deals_entered=entered_map.get(s.id, (0, 0))[0],
            deals_exited=entered_map.get(s.id, (0, 0))[1],
            conversion_rate=round(
                entered_map.get(s.id, (0, 0))[1] / entered_map.get(s.id, (1, 0))[0], 4
            ) if entered_map.get(s.id, (0, 0))[0] else 0.0,
        )
        for s in stages
    ]

    stalled = repo.stalled_deals(session, pipeline_id)
    stats = repo.deal_stats_batch(session, pipeline_id, stage_ids)
    total_pipeline_value = sum(stats[sid]["total_value"] for sid in open_ids if sid in stats)
    total_weighted = sum(stats[sid]["weighted_value"] for sid in open_ids if sid in stats)

    all_deals_count = counts["open"] + counts["won"] + counts["lost"]
    return DealAnalyticsOut(
        pipeline_id=pipeline_id,
        total_deals=all_deals_count,
        open_deals=counts["open"],
        won_deals=counts["won"],
        lost_deals=counts["lost"],
        win_rate=win_rate,
        loss_rate=loss_rate,
        pipeline_value=round(total_pipeline_value, 2),
        weighted_pipeline=round(total_weighted, 2),
        stalled_deal_count=len(stalled),
        stage_velocity=stage_velocity,
    )


# ================================================================== deal timeline
def deal_timeline(
    session: Session, deal_id: int, user, *, limit: int = 50, offset: int = 0
) -> list[UnifiedTimelineEvent]:
    if not repo.get_deal(session, deal_id):
        raise HTTPException(404, "deal not found")

    msgs, meetings, activities, history = repo.deal_timeline_events(session, deal_id)

    events: list[UnifiedTimelineEvent] = []

    for a in activities:
        events.append(UnifiedTimelineEvent(
            event_id=f"activity-{a.id}", event_type="activity",
            type=a.type, label=a.type.replace("_", " ").title(),
            detail=a.detail, actor=a.actor_email,
            timestamp=_utc(a.created_at) or _utcnow(),
        ))

    for m in msgs:
        events.append(UnifiedTimelineEvent(
            event_id=f"message-{m.id}", event_type="message",
            type=m.direction, label=f"Email {m.direction}",
            detail=m.subject or "", actor="",
            timestamp=_utc(m.created_at) or _utcnow(),
        ))

    for mtg in meetings:
        events.append(UnifiedTimelineEvent(
            event_id=f"meeting-{mtg.id}", event_type="meeting",
            type=mtg.meeting_type, label=f"Meeting: {mtg.title}",
            detail=mtg.outcome or "", actor="",
            timestamp=_utc(mtg.scheduled_at) or _utcnow(),
        ))

    for h in history:
        events.append(UnifiedTimelineEvent(
            event_id=f"stage-{h.id}", event_type="stage_change",
            type="stage_moved",
            label=f"Stage change → {h.to_stage_id}",
            detail="", actor="",
            timestamp=_utc(h.entered_at) or _utcnow(),
        ))

    events.sort(key=lambda e: e.timestamp, reverse=True)
    return events[offset: offset + limit]


# ================================================================== dashboard
def deal_dashboard(session: Session, user, *, pipeline_id: int | None = None) -> DealDashboardOut:
    # Find pipelines to summarize
    pipelines, _ = repo.list_pipelines(session, active_only=True, limit=10)
    target = [p for p in pipelines if pipeline_id is None or p.id == pipeline_id]
    if not target:
        return DealDashboardOut()

    # Use first pipeline for dashboard widgets (or the specified one)
    pid = target[0].id

    closing_soon = repo.closing_soon_deals(session, pid, days=30)
    stalled = repo.stalled_deals(session, pid, threshold_days=14)
    recently_won = repo.recent_won_lost(session, pid, "won", limit=5)
    recently_lost = repo.recent_won_lost(session, pid, "lost", limit=5)

    stages = repo.list_stages(session, pid)
    stage_ids = [s.id for s in stages]
    open_ids = {s.id for s in stages if s.stage_type == "open"}
    stats = repo.deal_stats_batch(session, pid, stage_ids)
    stage_name_map = {s.id: s.name for s in stages}

    high_value_threshold = 100_000.0
    all_open_deals = repo.list_deals_for_stages(session, list(open_ids))
    high_value = sorted(
        (d for d in all_open_deals if (d.value or 0) >= high_value_threshold),
        key=lambda d: d.value or 0, reverse=True,
    )[:10]

    owner_ids = list({d.owner_id for d in closing_soon + stalled + recently_won + recently_lost + high_value if d.owner_id})
    user_map = _load_user_emails(session, owner_ids)
    own_stage_map = _load_stage_map(session, stage_ids)

    def _d(d: CrmDeal) -> DealOut:
        sname = own_stage_map[d.stage_id].name if d.stage_id in own_stage_map else ""
        return _deal_out(d, stage_name=sname, owner_email=user_map.get(d.owner_id, "") if d.owner_id else "")

    total_pipeline_value = sum(stats[sid]["total_value"] for sid in open_ids if sid in stats)
    total_weighted = sum(stats[sid]["weighted_value"] for sid in open_ids if sid in stats)
    counts = repo.pipeline_deal_counts(session, pid)
    closed = counts["won"] + counts["lost"]

    return DealDashboardOut(
        pipeline_id=pid,
        total_open_deals=counts["open"],
        total_won_deals=counts["won"],
        total_lost_deals=counts["lost"],
        pipeline_value=round(total_pipeline_value, 2),
        weighted_pipeline=round(total_weighted, 2),
        win_rate=round(counts["won"] / closed, 4) if closed else 0.0,
        closing_soon=[_d(d) for d in closing_soon],
        stalled_deals=[_d(d) for d in stalled],
        high_value_deals=[_d(d) for d in high_value],
        recently_won=[_d(d) for d in recently_won],
        recently_lost=[_d(d) for d in recently_lost],
    )


# ================================================================== deal intelligence
def deal_intelligence(session: Session, deal_id: int, user) -> DealIntelligenceOut:
    """Surface existing intelligence engines for a deal's company. No LLM."""
    d = repo.get_deal(session, deal_id)
    if not d:
        raise HTTPException(404, "deal not found")
    domain = d.company_domain

    try:
        from backend.outreach_intelligence import (
            classify_priority,
            estimate_success_probability,
            recommend_contacts,
            recommend_sequence,
        )
        contacts = recommend_contacts(session, domain, limit=3)
        best_raw = contacts[0] if contacts else None
        backups_raw = contacts[1:] if len(contacts) > 1 else []
        success_raw = estimate_success_probability(session, domain)
        priority_raw = classify_priority(session, domain)
        seq_steps = recommend_sequence(session, domain)
    except Exception:
        contacts = best_raw = backups_raw = success_raw = priority_raw = seq_steps = None

    try:
        from backend.company_intelligence import company_intelligence
        ci = company_intelligence(session, domain)
        buying_committee = ci.buying_committee
    except Exception:
        buying_committee = None

    try:
        from backend.relationship_intelligence import company_relationships
        rels = company_relationships(session, domain)
        next_action = rels.next_best_contacts[0].next_action if rels.next_best_contacts else None
    except Exception:
        next_action = None

    from backend.schemas import (
        ContactRecommendationOut,
        OutreachPriorityOut,
        SequenceStepOut,
        SuccessProbabilityOut,
    )

    def _contact_out(rc):
        if not rc:
            return None
        return ContactRecommendationOut(
            decision_maker_id=rc.decision_maker_id,
            full_name=rc.full_name, title=rc.title, email=rc.email,
            influence_score=rc.influence_score,
            confidence_score=rc.confidence_score,
            confidence_level=rc.confidence_level,
            relationship_strength=rc.relationship_strength,
            company_engagement=rc.company_engagement,
            recommendation_reason=rc.recommendation_reason,
        )

    best_contact = _contact_out(best_raw)
    backup_contacts = [_contact_out(r) for r in (backups_raw or []) if r]
    relationship_strength = best_contact.relationship_strength if best_contact else 0

    success = None
    if success_raw:
        success = SuccessProbabilityOut(
            probability=success_raw.probability,
            confidence_level=success_raw.confidence_level,
            factors=success_raw.factors,
        )

    priority = None
    if priority_raw:
        priority = OutreachPriorityOut(
            priority=priority_raw.priority,
            score=priority_raw.score,
            factors=priority_raw.factors,
        )

    recommended_sequence = [
        SequenceStepOut(
            order=s.order, action=s.action,
            description=s.description, rationale=s.rationale,
        )
        for s in (seq_steps or [])
    ]

    return DealIntelligenceOut(
        deal_id=deal_id,
        company_domain=domain,
        best_contact=best_contact,
        backup_contacts=backup_contacts,
        buying_committee=buying_committee,
        relationship_strength=relationship_strength,
        success_probability=success,
        next_action=next_action,
        recommended_sequence=recommended_sequence,
        outreach_priority=priority,
    )
