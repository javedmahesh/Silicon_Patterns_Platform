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


def get_stage(session: Session, stage_id: int) -> CrmPipelineStage | None:
    return session.get(CrmPipelineStage, stage_id)


def list_stages(session: Session, pipeline_id: int) -> list[CrmPipelineStage]:
    return list(session.scalars(
        select(CrmPipelineStage)
        .where(CrmPipelineStage.pipeline_id == pipeline_id)
        .order_by(CrmPipelineStage.stage_order)
    ))


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


def create_deal(session: Session, **kw) -> CrmDeal:
    d = CrmDeal(**kw)
    session.add(d)
    session.flush()
    return d


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


