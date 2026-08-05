"""Enterprise CRM Phase 2: pipeline analytics.

Only the analytics read-path survives: the deal/pipeline CRUD routers were removed
(commit "deals/CS removal"), leaving :func:`pipeline_analytics` as the single entry
point, reached from ``revops_service.pipeline_analytics`` for its stage-velocity
breakdown. Deal and pipeline rows are read through :mod:`backend.deal_repo`.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend import deal_repo as repo
from backend.schemas import DealAnalyticsOut, StageVelocityOut
from master_db.models import CrmDeal, CrmDealStageHistory


def pipeline_analytics(session: Session, pipeline_id: int, user) -> DealAnalyticsOut:
    p = repo.get_pipeline(session, pipeline_id)
    if not p:
        raise HTTPException(404, "pipeline not found")

    stages = repo.list_stages(session, pipeline_id)
    stage_ids = [s.id for s in stages]
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

    return DealAnalyticsOut(
        pipeline_id=pipeline_id,
        total_deals=counts["open"] + counts["won"] + counts["lost"],
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
