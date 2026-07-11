"""Data access for Enterprise CRM Phase 2: Pipeline & Deal Management."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from master_db.models import (
    CrmDeal,
    CrmDealStageHistory,
    CrmPipeline,
    CrmPipelineStage,
    OutreachActivity,
    OutreachMeeting,
    OutreachMessage,
)

from backend.timeutil import utcnow as _utcnow


# ----------------------------------------------------------------- pipelines
def get_pipeline(session: Session, pipeline_id: int) -> CrmPipeline | None:
    return session.get(CrmPipeline, pipeline_id)


def list_pipelines(
    session: Session, *, active_only: bool = False, limit: int = 50, offset: int = 0
) -> tuple[list[CrmPipeline], int]:
    q = select(CrmPipeline)
    if active_only:
        q = q.where(CrmPipeline.is_active.is_(True))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(CrmPipeline.created_at.desc()).limit(limit).offset(offset)))
    return rows, total


def create_pipeline(session: Session, **kw) -> CrmPipeline:
    p = CrmPipeline(**kw)
    session.add(p)
    session.flush()
    return p


# ----------------------------------------------------------------- stages
def get_stage(session: Session, stage_id: int) -> CrmPipelineStage | None:
    return session.get(CrmPipelineStage, stage_id)


def list_stages(session: Session, pipeline_id: int) -> list[CrmPipelineStage]:
    return list(session.scalars(
        select(CrmPipelineStage)
        .where(CrmPipelineStage.pipeline_id == pipeline_id)
        .order_by(CrmPipelineStage.stage_order)
    ))


def list_stages_batch(session: Session, pipeline_ids: list[int]) -> dict[int, list[CrmPipelineStage]]:
    """Stages for every given pipeline, 1 query — avoids N+1 across list_pipelines()."""
    if not pipeline_ids:
        return {}
    rows = session.scalars(
        select(CrmPipelineStage)
        .where(CrmPipelineStage.pipeline_id.in_(pipeline_ids))
        .order_by(CrmPipelineStage.pipeline_id, CrmPipelineStage.stage_order)
    )
    by_pipeline: dict[int, list[CrmPipelineStage]] = {}
    for s in rows:
        by_pipeline.setdefault(s.pipeline_id, []).append(s)
    return by_pipeline


def add_stage(session: Session, **kw) -> CrmPipelineStage:
    s = CrmPipelineStage(**kw)
    session.add(s)
    session.flush()
    return s


def delete_stage(session: Session, stage_id: int) -> bool:
    s = session.get(CrmPipelineStage, stage_id)
    if not s:
        return False
    session.delete(s)
    return True


# ----------------------------------------------------------------- deals
def get_deal(session: Session, deal_id: int) -> CrmDeal | None:
    return session.get(CrmDeal, deal_id)


def list_deals(
    session: Session, *,
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
) -> tuple[list[CrmDeal], int]:
    q = select(CrmDeal)
    filters = []
    if pipeline_id is not None:
        filters.append(CrmDeal.pipeline_id == pipeline_id)
    if stage_id is not None:
        filters.append(CrmDeal.stage_id == stage_id)
    if owner_id is not None:
        filters.append(CrmDeal.owner_id == owner_id)
    if company_domain:
        filters.append(CrmDeal.company_domain == company_domain)
    if forecast_category:
        filters.append(CrmDeal.forecast_category == forecast_category)
    if search:
        pat = f"%{search}%"
        filters.append(or_(CrmDeal.title.ilike(pat), CrmDeal.notes.ilike(pat)))
    if closing_before:
        filters.append(CrmDeal.expected_close_date <= closing_before)
    if closing_after:
        filters.append(CrmDeal.expected_close_date >= closing_after)
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(
        q.order_by(CrmDeal.last_activity_at.desc()).limit(limit).offset(offset)
    ))
    return rows, total


def list_deals_for_stages(
    session: Session, stage_ids: list[int], *,
    owner_id: int | None = None,
    search: str | None = None,
) -> list[CrmDeal]:
    """Batch-load all deals across a set of stage_ids (Kanban). No N+1."""
    if not stage_ids:
        return []
    q = select(CrmDeal).where(CrmDeal.stage_id.in_(stage_ids))
    if owner_id is not None:
        q = q.where(CrmDeal.owner_id == owner_id)
    if search:
        pat = f"%{search}%"
        q = q.where(or_(CrmDeal.title.ilike(pat), CrmDeal.notes.ilike(pat)))
    return list(session.scalars(q.order_by(CrmDeal.value.desc().nullslast())))


def create_deal(session: Session, **kw) -> CrmDeal:
    d = CrmDeal(**kw)
    session.add(d)
    session.flush()
    return d


# ----------------------------------------------------------------- stage history
def get_open_history(session: Session, deal_id: int) -> CrmDealStageHistory | None:
    """The current (not yet exited) stage history entry for a deal."""
    return session.scalar(
        select(CrmDealStageHistory).where(
            CrmDealStageHistory.deal_id == deal_id,
            CrmDealStageHistory.exited_at.is_(None),
        )
    )


def list_stage_history(session: Session, deal_id: int) -> list[CrmDealStageHistory]:
    return list(session.scalars(
        select(CrmDealStageHistory)
        .where(CrmDealStageHistory.deal_id == deal_id)
        .order_by(CrmDealStageHistory.entered_at)
    ))


def add_stage_history(session: Session, **kw) -> CrmDealStageHistory:
    h = CrmDealStageHistory(**kw)
    session.add(h)
    session.flush()
    return h


# ----------------------------------------------------------------- batch stats
def deal_stats_batch(session: Session, pipeline_id: int, stage_ids: list[int]) -> dict[int, dict]:
    """Per-stage deal counts and value totals in 1 query (no N+1).

    Returns dict keyed by stage_id:
      deal_count, total_value, weighted_value.
    """
    if not stage_ids:
        return {}

    rows = session.execute(
        select(
            CrmDeal.stage_id,
            func.count(CrmDeal.id).label("deal_count"),
            func.coalesce(func.sum(CrmDeal.value), 0).label("total_value"),
            func.coalesce(
                func.sum(CrmDeal.value * CrmDeal.probability / 100.0), 0
            ).label("weighted_value"),
        )
        .where(CrmDeal.pipeline_id == pipeline_id)
        .where(CrmDeal.stage_id.in_(stage_ids))
        .group_by(CrmDeal.stage_id)
    ).all()

    stats: dict[int, dict] = {sid: {"deal_count": 0, "total_value": 0.0, "weighted_value": 0.0}
                               for sid in stage_ids}
    for r in rows:
        stats[r.stage_id].update(
            deal_count=r.deal_count,
            total_value=float(r.total_value),
            weighted_value=float(r.weighted_value),
        )
    return stats


def avg_time_per_stage(session: Session, pipeline_id: int) -> dict[int, float]:
    """Average time_in_stage_seconds per stage for all completed transitions (1 query)."""
    rows = session.execute(
        select(
            CrmDealStageHistory.to_stage_id,
            func.avg(CrmDealStageHistory.time_in_stage_seconds).label("avg_secs"),
        )
        .join(CrmDeal, CrmDeal.id == CrmDealStageHistory.deal_id)
        .where(CrmDeal.pipeline_id == pipeline_id)
        .where(CrmDealStageHistory.time_in_stage_seconds.isnot(None))
        .group_by(CrmDealStageHistory.to_stage_id)
    ).all()
    return {r.to_stage_id: float(r.avg_secs or 0) for r in rows}


def pipeline_deal_counts(session: Session, pipeline_id: int) -> dict:
    """Total, won, lost, and open deal counts for a pipeline (1 query via join)."""
    rows = session.execute(
        select(
            CrmPipelineStage.stage_type,
            func.count(CrmDeal.id).label("cnt"),
            func.coalesce(func.sum(CrmDeal.value), 0).label("total_val"),
        )
        .join(CrmDeal, CrmDeal.stage_id == CrmPipelineStage.id, isouter=True)
        .where(CrmPipelineStage.pipeline_id == pipeline_id)
        .group_by(CrmPipelineStage.stage_type)
    ).all()
    counts = {"open": 0, "won": 0, "lost": 0, "open_val": 0.0, "won_val": 0.0}
    for r in rows:
        if r.stage_type == "open":
            counts["open"] = r.cnt
            counts["open_val"] = float(r.total_val)
        elif r.stage_type == "won":
            counts["won"] = r.cnt
            counts["won_val"] = float(r.total_val)
        elif r.stage_type == "lost":
            counts["lost"] = r.cnt
    return counts


def stalled_deals(
    session: Session, pipeline_id: int, threshold_days: int = 14
) -> list[CrmDeal]:
    """Open-stage deals with no activity for > threshold_days."""
    from datetime import timedelta
    cutoff = _utcnow() - timedelta(days=threshold_days)
    open_stage_ids = session.scalars(
        select(CrmPipelineStage.id).where(
            CrmPipelineStage.pipeline_id == pipeline_id,
            CrmPipelineStage.stage_type == "open",
        )
    ).all()
    if not open_stage_ids:
        return []
    return list(session.scalars(
        select(CrmDeal)
        .where(CrmDeal.stage_id.in_(open_stage_ids))
        .where(CrmDeal.last_activity_at <= cutoff)
        .order_by(CrmDeal.last_activity_at)
        .limit(50)
    ))


def closing_soon_deals(session: Session, pipeline_id: int, days: int = 30) -> list[CrmDeal]:
    """Open-stage deals closing within *days* days."""
    from datetime import timedelta
    cutoff = _utcnow() + timedelta(days=days)
    open_stage_ids = session.scalars(
        select(CrmPipelineStage.id).where(
            CrmPipelineStage.pipeline_id == pipeline_id,
            CrmPipelineStage.stage_type == "open",
        )
    ).all()
    if not open_stage_ids:
        return []
    return list(session.scalars(
        select(CrmDeal)
        .where(CrmDeal.stage_id.in_(open_stage_ids))
        .where(CrmDeal.expected_close_date.isnot(None))
        .where(CrmDeal.expected_close_date <= cutoff)
        .order_by(CrmDeal.expected_close_date)
        .limit(20)
    ))


def recent_won_lost(
    session: Session, pipeline_id: int, stage_type: str, limit: int = 10
) -> list[CrmDeal]:
    stage_ids = session.scalars(
        select(CrmPipelineStage.id).where(
            CrmPipelineStage.pipeline_id == pipeline_id,
            CrmPipelineStage.stage_type == stage_type,
        )
    ).all()
    if not stage_ids:
        return []
    return list(session.scalars(
        select(CrmDeal)
        .where(CrmDeal.stage_id.in_(stage_ids))
        .order_by(CrmDeal.updated_at.desc())
        .limit(limit)
    ))


def deal_timeline_events(
    session: Session, deal_id: int, *, limit: int = 50, offset: int = 0
) -> tuple[list, list, list, list[CrmDealStageHistory]]:
    """Batch-load all timeline sources for a deal in 4 queries."""
    deal = session.get(CrmDeal, deal_id)
    if not deal:
        return [], [], [], []

    # Find the outreach lead for this company to join messages/meetings/activities
    from master_db.models import OutreachLead
    lead = session.scalar(
        select(OutreachLead).where(OutreachLead.company_domain == deal.company_domain)
    )
    lead_id = lead.id if lead else None

    if lead_id:
        msgs = list(session.scalars(
            select(OutreachMessage)
            .where(OutreachMessage.outreach_lead_id == lead_id)
            .order_by(OutreachMessage.created_at.desc())
            .limit(limit)
        ))
        meetings = list(session.scalars(
            select(OutreachMeeting)
            .where(OutreachMeeting.outreach_lead_id == lead_id)
            .order_by(OutreachMeeting.scheduled_at.desc())
            .limit(limit)
        ))
        activities = list(session.scalars(
            select(OutreachActivity)
            .where(OutreachActivity.outreach_lead_id == lead_id)
            .order_by(OutreachActivity.created_at.desc())
            .limit(limit)
        ))
    else:
        msgs, meetings, activities = [], [], []

    history = list_stage_history(session, deal_id)
    return msgs, meetings, activities, history
