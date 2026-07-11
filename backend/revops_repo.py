"""Data access for Enterprise CRM Phase 5: Revenue Operations, Forecasting & Executive Analytics.

Reuses Phase 2 deal infra (deal_repo, Company/CsAccount/User joins) rather than
duplicating queries. Every function here is a single SQL statement.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from master_db.models import (
    CampaignMember,
    Company,
    CrmDeal,
    CrmPipelineStage,
    CsAccount,
    ForecastSnapshot,
    LeadAssignment,
    Opportunity,
    RevenueTarget,
    User,
)

from backend.timeutil import utcnow as _utcnow


# ----------------------------------------------------------------- revenue targets
def get_target(session: Session, target_id: int) -> RevenueTarget | None:
    return session.get(RevenueTarget, target_id)


def list_targets(
    session: Session, *, scope: str | None = None, owner_id: int | None = None,
    period_type: str | None = None, limit: int = 50, offset: int = 0,
) -> tuple[list[RevenueTarget], int]:
    q = select(RevenueTarget)
    filters = []
    if scope:
        filters.append(RevenueTarget.scope == scope)
    if owner_id is not None:
        filters.append(RevenueTarget.owner_id == owner_id)
    if period_type:
        filters.append(RevenueTarget.period_type == period_type)
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(
        session.scalars(q.order_by(RevenueTarget.period_start.desc()).limit(limit).offset(offset))
    )
    return rows, total


def create_target(session: Session, **kw) -> RevenueTarget:
    t = RevenueTarget(**kw)
    session.add(t)
    session.flush()
    return t


def delete_target(session: Session, target_id: int) -> bool:
    t = session.get(RevenueTarget, target_id)
    if not t:
        return False
    session.delete(t)
    return True


# ----------------------------------------------------------------- forecast snapshots
def create_snapshot(session: Session, **kw) -> ForecastSnapshot:
    s = ForecastSnapshot(**kw)
    session.add(s)
    session.flush()
    return s


def list_snapshots(
    session: Session, *, pipeline_id: int | None = None, period_type: str | None = None, limit: int = 200,
) -> list[ForecastSnapshot]:
    q = select(ForecastSnapshot)
    filters = []
    if pipeline_id is not None:
        filters.append(ForecastSnapshot.pipeline_id == pipeline_id)
    if period_type:
        filters.append(ForecastSnapshot.period_type == period_type)
    if filters:
        q = q.where(and_(*filters))
    return list(session.scalars(q.order_by(ForecastSnapshot.snapshot_at.desc()).limit(limit)))


# ----------------------------------------------------------------- deals (cross-pipeline)
def open_deals(session: Session, *, pipeline_id: int | None = None) -> list[CrmDeal]:
    q = (
        select(CrmDeal)
        .join(CrmPipelineStage, CrmPipelineStage.id == CrmDeal.stage_id)
        .where(CrmPipelineStage.stage_type == "open")
    )
    if pipeline_id is not None:
        q = q.where(CrmDeal.pipeline_id == pipeline_id)
    return list(session.scalars(q))


def company_wide_deal_counts(session: Session, *, pipeline_id: int | None = None) -> dict:
    """Deal count + value per stage_type, across all pipelines (or one). 1 query."""
    q = (
        select(
            CrmPipelineStage.stage_type,
            func.count(CrmDeal.id),
            func.coalesce(func.sum(CrmDeal.value), 0),
        )
        .select_from(CrmPipelineStage)
        .outerjoin(CrmDeal, CrmDeal.stage_id == CrmPipelineStage.id)
    )
    if pipeline_id is not None:
        q = q.where(CrmPipelineStage.pipeline_id == pipeline_id)
    rows = session.execute(q.group_by(CrmPipelineStage.stage_type)).all()
    counts = {"open": 0, "won": 0, "lost": 0, "open_val": 0.0, "won_val": 0.0}
    for stage_type, cnt, val in rows:
        if stage_type == "open":
            counts["open"], counts["open_val"] = cnt, float(val)
        elif stage_type == "won":
            counts["won"], counts["won_val"] = cnt, float(val)
        elif stage_type == "lost":
            counts["lost"] = cnt
    return counts


def closed_value_in_period(
    session: Session, *, stage_type: str, start: datetime, end: datetime,
    owner_id: int | None = None, pipeline_id: int | None = None,
) -> float:
    """Sum of CrmDeal.value for deals in `stage_type`, closed (updated_at) within [start, end). 1 query."""
    q = (
        select(func.coalesce(func.sum(CrmDeal.value), 0))
        .join(CrmPipelineStage, CrmPipelineStage.id == CrmDeal.stage_id)
        .where(CrmPipelineStage.stage_type == stage_type)
        .where(CrmDeal.updated_at >= start, CrmDeal.updated_at < end)
    )
    if owner_id is not None:
        q = q.where(CrmDeal.owner_id == owner_id)
    if pipeline_id is not None:
        q = q.where(CrmDeal.pipeline_id == pipeline_id)
    return float(session.scalar(q) or 0)


def won_deal_cycle_seconds(session: Session, *, pipeline_id: int | None = None) -> list[float]:
    """created_at -> updated_at gap for won deals (updated_at is the closed-at proxy). 1 query."""
    q = (
        select(CrmDeal.created_at, CrmDeal.updated_at)
        .join(CrmPipelineStage, CrmPipelineStage.id == CrmDeal.stage_id)
        .where(CrmPipelineStage.stage_type == "won")
    )
    if pipeline_id is not None:
        q = q.where(CrmDeal.pipeline_id == pipeline_id)
    out = []
    for created, updated in session.execute(q).all():
        c = created if created.tzinfo else created.replace(tzinfo=timezone.utc)
        u = updated if updated.tzinfo else updated.replace(tzinfo=timezone.utc)
        out.append((u - c).total_seconds())
    return out


def open_deal_ages_days(session: Session, *, pipeline_id: int | None = None) -> list[float]:
    q = (
        select(CrmDeal.last_activity_at)
        .join(CrmPipelineStage, CrmPipelineStage.id == CrmDeal.stage_id)
        .where(CrmPipelineStage.stage_type == "open")
    )
    if pipeline_id is not None:
        q = q.where(CrmDeal.pipeline_id == pipeline_id)
    now = _utcnow()
    out = []
    for la in session.scalars(q):
        la2 = la if la.tzinfo else la.replace(tzinfo=timezone.utc)
        out.append((now - la2).total_seconds() / 86400)
    return out


def lost_reason_counts(session: Session, *, pipeline_id: int | None = None) -> dict[str, int]:
    q = (
        select(CrmDeal.lost_reason, func.count(CrmDeal.id))
        .join(CrmPipelineStage, CrmPipelineStage.id == CrmDeal.stage_id)
        .where(CrmPipelineStage.stage_type == "lost")
    )
    if pipeline_id is not None:
        q = q.where(CrmDeal.pipeline_id == pipeline_id)
    rows = session.execute(q.group_by(CrmDeal.lost_reason)).all()
    return {(r[0] or "unspecified"): r[1] for r in rows}


def won_reason_counts(session: Session, *, pipeline_id: int | None = None) -> dict[str, int]:
    q = (
        select(CrmDeal.won_reason, func.count(CrmDeal.id))
        .join(CrmPipelineStage, CrmPipelineStage.id == CrmDeal.stage_id)
        .where(CrmPipelineStage.stage_type == "won")
    )
    if pipeline_id is not None:
        q = q.where(CrmDeal.pipeline_id == pipeline_id)
    rows = session.execute(q.group_by(CrmDeal.won_reason)).all()
    return {(r[0] or "unspecified"): r[1] for r in rows}


def won_deals_with_value(
    session: Session, *, pipeline_id: int | None = None, since: datetime | None = None,
) -> list[tuple[datetime, float]]:
    q = (
        select(CrmDeal.updated_at, CrmDeal.value)
        .join(CrmPipelineStage, CrmPipelineStage.id == CrmDeal.stage_id)
        .where(CrmPipelineStage.stage_type == "won")
    )
    if pipeline_id is not None:
        q = q.where(CrmDeal.pipeline_id == pipeline_id)
    if since is not None:
        q = q.where(CrmDeal.updated_at >= since)
    return session.execute(q).all()


# ----------------------------------------------------------------- sales performance dimensions
def revenue_by_owner(session: Session, *, pipeline_id: int | None = None):
    q = (
        select(CrmDeal.owner_id, func.count(CrmDeal.id), func.coalesce(func.sum(CrmDeal.value), 0))
        .join(CrmPipelineStage, CrmPipelineStage.id == CrmDeal.stage_id)
        .where(CrmPipelineStage.stage_type == "won")
    )
    if pipeline_id is not None:
        q = q.where(CrmDeal.pipeline_id == pipeline_id)
    return session.execute(q.group_by(CrmDeal.owner_id)).all()


def revenue_by_role(session: Session, *, pipeline_id: int | None = None):
    q = (
        select(User.role, func.count(CrmDeal.id), func.coalesce(func.sum(CrmDeal.value), 0))
        .join(CrmPipelineStage, CrmPipelineStage.id == CrmDeal.stage_id)
        .join(User, User.id == CrmDeal.owner_id)
        .where(CrmPipelineStage.stage_type == "won")
    )
    if pipeline_id is not None:
        q = q.where(CrmDeal.pipeline_id == pipeline_id)
    return session.execute(q.group_by(User.role)).all()


def revenue_by_country(session: Session, *, pipeline_id: int | None = None):
    q = (
        select(Company.country, func.count(CrmDeal.id), func.coalesce(func.sum(CrmDeal.value), 0))
        .join(CrmPipelineStage, CrmPipelineStage.id == CrmDeal.stage_id)
        .join(Company, Company.company_domain == CrmDeal.company_domain)
        .where(CrmPipelineStage.stage_type == "won")
    )
    if pipeline_id is not None:
        q = q.where(CrmDeal.pipeline_id == pipeline_id)
    return session.execute(q.group_by(Company.country)).all()


def revenue_by_cs_dimension(session: Session, dimension: str, *, pipeline_id: int | None = None):
    """dimension: 'industry' or 'tier' on CsAccount, joined via company_domain."""
    col = CsAccount.industry if dimension == "industry" else CsAccount.tier
    q = (
        select(col, func.count(CrmDeal.id), func.coalesce(func.sum(CrmDeal.value), 0))
        .join(CrmPipelineStage, CrmPipelineStage.id == CrmDeal.stage_id)
        .join(CsAccount, CsAccount.company_domain == CrmDeal.company_domain)
        .where(CrmPipelineStage.stage_type == "won")
    )
    if pipeline_id is not None:
        q = q.where(CrmDeal.pipeline_id == pipeline_id)
    return session.execute(q.group_by(col)).all()


# ----------------------------------------------------------------- funnels
def lead_funnel_counts(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(LeadAssignment.status, func.count(LeadAssignment.id)).group_by(LeadAssignment.status)
    ).all()
    return {r[0]: r[1] for r in rows}


def opportunity_funnel_counts(session: Session) -> dict[str, int]:
    total_opps = session.scalar(select(func.count(Opportunity.opportunity_id))) or 0
    linked = session.scalar(
        select(func.count(func.distinct(CrmDeal.opportunity_id))).where(CrmDeal.opportunity_id.isnot(None))
    ) or 0
    won = session.scalar(
        select(func.count(func.distinct(CrmDeal.opportunity_id)))
        .join(CrmPipelineStage, CrmPipelineStage.id == CrmDeal.stage_id)
        .where(CrmDeal.opportunity_id.isnot(None), CrmPipelineStage.stage_type == "won")
    ) or 0
    return {"total_opportunities": total_opps, "linked_to_deal": linked, "won": won}


def campaign_funnel_counts(session: Session) -> dict:
    by_status = dict(session.execute(
        select(CampaignMember.engagement_status, func.count(CampaignMember.id))
        .group_by(CampaignMember.engagement_status)
    ).all())
    by_outcome = dict(session.execute(
        select(CampaignMember.campaign_outcome, func.count(CampaignMember.id))
        .group_by(CampaignMember.campaign_outcome)
    ).all())
    return {"by_status": by_status, "by_outcome": by_outcome}
