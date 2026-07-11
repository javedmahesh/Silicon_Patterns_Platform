"""Data access for the Enterprise CRM Campaign & Sequence module.

Scoped to campaigns / campaign_members / outreach_sequences / sequence_steps /
sequence_enrollments / sequence_step_executions. Platform data (companies,
decision_makers, lead_scores, users) is read through backend.repositories.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from master_db.models import (
    Campaign,
    CampaignMember,
    OutreachMessage,
    OutreachMeeting,
    OutreachSequence,
    SequenceEnrollment,
    SequenceStep,
    SequenceStepExecution,
)

from backend.timeutil import utcnow as _utcnow


# ----------------------------------------------------------------- campaigns
def get_campaign(session: Session, campaign_id: int) -> Campaign | None:
    return session.get(Campaign, campaign_id)


def list_campaigns(
    session: Session, *,
    owner_id: int | None = None,
    status: str | None = None,
    campaign_type: str | None = None,
    company_domain: str | None = None,
    decision_maker_id: int | None = None,
    tag: str | None = None,
    search: str | None = None,
    start_after: datetime | None = None,
    end_before: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Campaign], int]:
    q = select(Campaign)
    filters = []
    if owner_id is not None:
        filters.append(Campaign.owner_id == owner_id)
    if status:
        filters.append(Campaign.status == status)
    if campaign_type:
        filters.append(Campaign.campaign_type == campaign_type)
    if search:
        pat = f"%{search}%"
        filters.append(or_(Campaign.name.ilike(pat), Campaign.description.ilike(pat)))
    if start_after:
        filters.append(Campaign.start_date >= start_after)
    if end_before:
        filters.append(Campaign.end_date <= end_before)
    if company_domain:
        sub = select(CampaignMember.campaign_id).where(
            CampaignMember.company_domain == company_domain
        )
        filters.append(Campaign.id.in_(sub))
    if decision_maker_id is not None:
        sub = select(CampaignMember.campaign_id).where(
            CampaignMember.decision_maker_id == decision_maker_id
        )
        filters.append(Campaign.id.in_(sub))
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(
        q.order_by(Campaign.created_at.desc()).limit(limit).offset(offset)
    ))
    return rows, total


def create_campaign(session: Session, **kw) -> Campaign:
    c = Campaign(**kw)
    session.add(c)
    session.flush()
    return c


# ----------------------------------------------------------------- members
def get_member(session: Session, member_id: int) -> CampaignMember | None:
    return session.get(CampaignMember, member_id)


def get_member_by_campaign_domain(
    session: Session, campaign_id: int, domain: str
) -> CampaignMember | None:
    return session.scalar(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.company_domain == domain,
        )
    )


def list_members(
    session: Session, campaign_id: int, *, limit: int = 200, offset: int = 0
) -> tuple[list[CampaignMember], int]:
    q = select(CampaignMember).where(CampaignMember.campaign_id == campaign_id)
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(CampaignMember.joined_at.desc()).limit(limit).offset(offset)))
    return rows, total


def add_member(session: Session, **kw) -> CampaignMember:
    m = CampaignMember(**kw)
    session.add(m)
    session.flush()
    return m


# ----------------------------------------------------------------- sequences
def get_sequence(session: Session, seq_id: int) -> OutreachSequence | None:
    return session.get(OutreachSequence, seq_id)


def list_sequences(
    session: Session, *, active_only: bool = False, limit: int = 50, offset: int = 0
) -> tuple[list[OutreachSequence], int]:
    q = select(OutreachSequence)
    if active_only:
        q = q.where(OutreachSequence.is_active.is_(True))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(OutreachSequence.name).limit(limit).offset(offset)))
    return rows, total


def create_sequence(session: Session, **kw) -> OutreachSequence:
    s = OutreachSequence(**kw)
    session.add(s)
    session.flush()
    return s


# ----------------------------------------------------------------- steps
def get_step(session: Session, step_id: int) -> SequenceStep | None:
    return session.get(SequenceStep, step_id)


def list_steps(session: Session, seq_id: int) -> list[SequenceStep]:
    return list(session.scalars(
        select(SequenceStep)
        .where(SequenceStep.sequence_id == seq_id)
        .order_by(SequenceStep.step_order)
    ))


def list_steps_batch(session: Session, seq_ids: list[int]) -> dict[int, list[SequenceStep]]:
    """Steps for every given sequence, 1 query — avoids N+1 across list_sequences()."""
    if not seq_ids:
        return {}
    rows = session.scalars(
        select(SequenceStep)
        .where(SequenceStep.sequence_id.in_(seq_ids))
        .order_by(SequenceStep.sequence_id, SequenceStep.step_order)
    )
    by_seq: dict[int, list[SequenceStep]] = {}
    for s in rows:
        by_seq.setdefault(s.sequence_id, []).append(s)
    return by_seq


def add_step(session: Session, **kw) -> SequenceStep:
    st = SequenceStep(**kw)
    session.add(st)
    session.flush()
    return st


def delete_step(session: Session, step_id: int) -> bool:
    st = session.get(SequenceStep, step_id)
    if not st:
        return False
    session.delete(st)
    return True


# ----------------------------------------------------------------- enrollments
def get_enrollment(session: Session, enrollment_id: int) -> SequenceEnrollment | None:
    return session.get(SequenceEnrollment, enrollment_id)


def get_active_enrollment(
    session: Session, lead_id: int, seq_id: int
) -> SequenceEnrollment | None:
    return session.scalar(
        select(SequenceEnrollment).where(
            SequenceEnrollment.outreach_lead_id == lead_id,
            SequenceEnrollment.sequence_id == seq_id,
            SequenceEnrollment.status == "active",
        )
    )


def create_enrollment(session: Session, **kw) -> SequenceEnrollment:
    e = SequenceEnrollment(**kw)
    session.add(e)
    session.flush()
    return e


def list_enrollments(
    session: Session, *,
    sequence_id: int | None = None,
    lead_id: int | None = None,
    member_ids: list[int] | None = None,
    status: str | None = None,
    limit: int = 200,
) -> list[SequenceEnrollment]:
    q = select(SequenceEnrollment)
    if sequence_id is not None:
        q = q.where(SequenceEnrollment.sequence_id == sequence_id)
    if lead_id is not None:
        q = q.where(SequenceEnrollment.outreach_lead_id == lead_id)
    if member_ids is not None:
        q = q.where(SequenceEnrollment.campaign_member_id.in_(member_ids))
    if status:
        q = q.where(SequenceEnrollment.status == status)
    return list(session.scalars(q.order_by(SequenceEnrollment.created_at.desc()).limit(limit)))


def pending_step_executions(
    session: Session, *, now: datetime | None = None
) -> list[SequenceStepExecution]:
    """Return pending executions whose scheduled_at has passed (or is null = immediate)."""
    cutoff = now or _utcnow()
    return list(session.scalars(
        select(SequenceStepExecution)
        .where(SequenceStepExecution.status == "pending")
        .where(
            or_(
                SequenceStepExecution.scheduled_at.is_(None),
                SequenceStepExecution.scheduled_at <= cutoff,
            )
        )
        .limit(500)
    ))


# ----------------------------------------------------------------- batch stats
def campaign_stats_batch(session: Session, campaign_ids: list[int]) -> dict[int, dict]:
    """Fetch per-campaign stats in 3 queries (no N+1).

    Returns dict keyed by campaign_id with keys:
    member_count, active_count, converted_count, emails_sent, replies, meetings.
    """
    if not campaign_ids:
        return {}

    member_rows = session.execute(
        select(
            CampaignMember.campaign_id,
            func.count(CampaignMember.id).label("member_count"),
            func.count(CampaignMember.id).filter(
                CampaignMember.engagement_status == "active"
            ).label("active_count"),
            func.count(CampaignMember.id).filter(
                CampaignMember.campaign_outcome == "converted"
            ).label("converted_count"),
        )
        .where(CampaignMember.campaign_id.in_(campaign_ids))
        .group_by(CampaignMember.campaign_id)
    ).all()

    email_rows = session.execute(
        select(
            CampaignMember.campaign_id,
            func.count(OutreachMessage.id).label("emails_sent"),
            func.count(OutreachMessage.id).filter(
                OutreachMessage.status == "replied"
            ).label("replies"),
        )
        .join(OutreachMessage, OutreachMessage.outreach_lead_id == CampaignMember.outreach_lead_id)
        .where(CampaignMember.campaign_id.in_(campaign_ids))
        .where(CampaignMember.outreach_lead_id.isnot(None))
        .where(OutreachMessage.direction == "outbound")
        .group_by(CampaignMember.campaign_id)
    ).all()

    meeting_rows = session.execute(
        select(
            CampaignMember.campaign_id,
            func.count(OutreachMeeting.id).label("meetings"),
        )
        .join(OutreachMeeting, OutreachMeeting.outreach_lead_id == CampaignMember.outreach_lead_id)
        .where(CampaignMember.campaign_id.in_(campaign_ids))
        .where(CampaignMember.outreach_lead_id.isnot(None))
        .group_by(CampaignMember.campaign_id)
    ).all()

    stats: dict[int, dict] = {
        cid: {"member_count": 0, "active_count": 0, "converted_count": 0,
              "emails_sent": 0, "replies": 0, "meetings": 0}
        for cid in campaign_ids
    }
    for r in member_rows:
        stats[r.campaign_id].update(
            member_count=r.member_count,
            active_count=r.active_count,
            converted_count=r.converted_count,
        )
    for r in email_rows:
        stats[r.campaign_id].update(emails_sent=r.emails_sent, replies=r.replies)
    for r in meeting_rows:
        stats[r.campaign_id]["meetings"] = r.meetings
    return stats
