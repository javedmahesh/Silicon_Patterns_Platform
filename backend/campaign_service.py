"""Enterprise CRM Phase 1: Campaign & Sequence business logic.

Composes campaign_repo (campaign/sequence/enrollment data) with the existing
platform's outreach_repo and repositories (leads, companies, users).
No platform data is duplicated here.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from backend import campaign_repo as crepo
from backend import outreach_repo as orepo
from backend import workflow_service
from backend.schemas import (
    CampaignAnalyticsOut,
    CampaignCreate,
    CampaignDashboardOut,
    CampaignMemberIn,
    CampaignMemberOut,
    CampaignMemberPatch,
    CampaignOut,
    CampaignPatch,
    CrmEnrollmentOut,
    CrmSequenceCreate,
    CrmSequenceOut,
    CrmSequencePatch,
    CrmSequenceStepIn,
    CrmSequenceStepOut,
    CrmSequenceStepPatch,
    Page,
    UnifiedTimelineEvent,
)
from master_db.models import (
    Campaign,
    CampaignMember,
    Company,
    OutreachActivity,
    OutreachLead,
    OutreachMeeting,
    OutreachMessage,
    OutreachSequence,
    SequenceEnrollment,
    SequenceStep,
    SequenceStepExecution,
    User,
)

from backend.timeutil import utc as _utc, utcnow as _utcnow


def _is_manager(user) -> bool:
    return getattr(user, "role", None) in ("admin", "manager")


def _require_manager(user) -> None:
    if not _is_manager(user):
        raise HTTPException(status_code=403, detail="admin or manager role required")


# ----------------------------------------------------------------- out helpers
def _campaign_out(
    c: Campaign, *,
    stats: dict | None = None,
    owner_email: str = "",
    created_by_email: str = "",
) -> CampaignOut:
    s = stats or {}
    return CampaignOut(
        id=c.id, name=c.name, description=c.description,
        campaign_type=c.campaign_type, status=c.status,
        owner_id=c.owner_id, owner_email=owner_email,
        created_by=c.created_by, created_by_email=created_by_email,
        start_date=_utc(c.start_date), end_date=_utc(c.end_date),
        goal=c.goal, budget=c.budget, tags=list(c.tags or []),
        member_count=s.get("member_count", 0),
        active_count=s.get("active_count", 0),
        converted_count=s.get("converted_count", 0),
        emails_sent=s.get("emails_sent", 0),
        replies=s.get("replies", 0),
        meetings=s.get("meetings", 0),
        created_at=_utc(c.created_at), updated_at=_utc(c.updated_at),
    )


def _member_out(m: CampaignMember, *, company_name: str = "", dm_name: str = "") -> CampaignMemberOut:
    return CampaignMemberOut(
        id=m.id, campaign_id=m.campaign_id,
        company_domain=m.company_domain or "",
        company_name=company_name,
        decision_maker_id=m.decision_maker_id,
        decision_maker_name=dm_name,
        opportunity_id=m.opportunity_id,
        outreach_lead_id=m.outreach_lead_id,
        joined_at=_utc(m.joined_at),
        current_stage=m.current_stage,
        last_activity_at=_utc(m.last_activity_at),
        engagement_status=m.engagement_status,
        campaign_outcome=m.campaign_outcome,
        notes=m.notes,
        created_at=_utc(m.created_at), updated_at=_utc(m.updated_at),
    )


def _step_out(st: SequenceStep) -> CrmSequenceStepOut:
    return CrmSequenceStepOut(
        id=st.id, sequence_id=st.sequence_id, step_order=st.step_order,
        action=st.action, name=st.name, description=st.description,
        delay_days=st.delay_days, template_id=st.template_id,
        config=dict(st.config or {}), created_at=_utc(st.created_at),
    )


def _sequence_out(s: OutreachSequence, steps: list[SequenceStep]) -> CrmSequenceOut:
    return CrmSequenceOut(
        id=s.id, name=s.name, description=s.description,
        is_active=s.is_active, created_by=s.created_by,
        step_count=len(steps), steps=[_step_out(st) for st in steps],
        created_at=_utc(s.created_at), updated_at=_utc(s.updated_at),
    )


def _enrollment_out(e: SequenceEnrollment) -> CrmEnrollmentOut:
    return CrmEnrollmentOut(
        id=e.id, sequence_id=e.sequence_id,
        outreach_lead_id=e.outreach_lead_id,
        campaign_member_id=e.campaign_member_id,
        status=e.status, current_step=e.current_step,
        next_step_at=_utc(e.next_step_at),
        completed_at=_utc(e.completed_at),
        created_at=_utc(e.created_at),
    )


def _load_users_map(session: Session, ids: set[int | None]) -> dict[int, User]:
    uid_set = {i for i in ids if i}
    if not uid_set:
        return {}
    return {u.id: u for u in session.scalars(select(User).where(User.id.in_(uid_set)))}


# ================================================================== campaigns
def list_campaigns(session: Session, user, **kw) -> Page:
    limit = kw.pop("limit", 50)
    offset = kw.pop("offset", 0)
    campaigns, total = crepo.list_campaigns(session, limit=limit, offset=offset, **kw)
    if not campaigns:
        return Page.build([], total, max(1, offset // limit + 1), limit)

    cids = [c.id for c in campaigns]
    stats = crepo.campaign_stats_batch(session, cids)

    uids: set[int | None] = set()
    for c in campaigns:
        uids.add(c.owner_id)
        uids.add(c.created_by)
    users_map = _load_users_map(session, uids)

    items = [
        _campaign_out(
            c, stats=stats.get(c.id),
            owner_email=getattr(users_map.get(c.owner_id), "email", ""),
            created_by_email=getattr(users_map.get(c.created_by), "email", ""),
        )
        for c in campaigns
    ]
    return Page.build(items, total, max(1, offset // limit + 1), limit)


def get_campaign(session: Session, campaign_id: int, user) -> CampaignOut:
    c = crepo.get_campaign(session, campaign_id)
    if not c:
        raise HTTPException(404, "campaign not found")
    stats = crepo.campaign_stats_batch(session, [campaign_id])
    return _campaign_out(c, stats=stats.get(campaign_id))


def create_campaign(session: Session, data: CampaignCreate, user) -> CampaignOut:
    c = crepo.create_campaign(
        session,
        name=data.name, description=data.description,
        campaign_type=data.campaign_type, status="draft",
        owner_id=data.owner_id or user.id, created_by=user.id,
        start_date=data.start_date, end_date=data.end_date,
        goal=data.goal, budget=data.budget, tags=data.tags or [],
    )
    session.commit()
    return _campaign_out(c)


def patch_campaign(session: Session, campaign_id: int, data: CampaignPatch, user) -> CampaignOut:
    c = crepo.get_campaign(session, campaign_id)
    if not c:
        raise HTTPException(404, "campaign not found")
    old_status = c.status
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(c, k, v)
    if data.status is not None and data.status != old_status:
        workflow_service.fire_event(
            session, "campaign_status_changed", "campaign", c.id,
            {"owner_id": c.owner_id, "status": c.status, "old_status": old_status, "name": c.name},
            actor=user,
        )
    session.commit()
    stats = crepo.campaign_stats_batch(session, [campaign_id])
    return _campaign_out(c, stats=stats.get(campaign_id))


def archive_campaign(session: Session, campaign_id: int, user) -> None:
    _require_manager(user)
    c = crepo.get_campaign(session, campaign_id)
    if not c:
        raise HTTPException(404, "campaign not found")
    old_status = c.status
    c.status = "archived"
    if old_status != "archived":
        workflow_service.fire_event(
            session, "campaign_status_changed", "campaign", c.id,
            {"owner_id": c.owner_id, "status": "archived", "old_status": old_status, "name": c.name},
            actor=user,
        )
    session.commit()


# ================================================================== members
def list_members(
    session: Session, campaign_id: int, user, *, limit: int = 100, offset: int = 0
) -> Page:
    if not crepo.get_campaign(session, campaign_id):
        raise HTTPException(404, "campaign not found")
    members, total = crepo.list_members(session, campaign_id, limit=limit, offset=offset)
    if not members:
        return Page.build([], total, 1, limit)

    from master_db.models import Company, DecisionMaker
    domains = {m.company_domain for m in members if m.company_domain}
    dm_ids = {m.decision_maker_id for m in members if m.decision_maker_id}
    companies_map: dict[str, str] = {}
    dm_map: dict[int, str] = {}
    if domains:
        companies_map = {
            c.company_domain: c.company_name
            for c in session.scalars(select(Company).where(Company.company_domain.in_(domains)))
        }
    if dm_ids:
        dm_map = {
            d.id: (d.full_name or f"{d.first_name or ''} {d.last_name or ''}".strip())
            for d in session.scalars(select(DecisionMaker).where(DecisionMaker.id.in_(dm_ids)))
        }

    items = [
        _member_out(m,
                    company_name=companies_map.get(m.company_domain or "", ""),
                    dm_name=dm_map.get(m.decision_maker_id or 0, ""))
        for m in members
    ]
    return Page.build(items, total, max(1, offset // limit + 1), limit)


def add_member(session: Session, campaign_id: int, data: CampaignMemberIn, user) -> CampaignMemberOut:
    if not crepo.get_campaign(session, campaign_id):
        raise HTTPException(404, "campaign not found")
    if data.company_domain:
        if crepo.get_member_by_campaign_domain(session, campaign_id, data.company_domain):
            raise HTTPException(409, "company already a member of this campaign")
    m = crepo.add_member(
        session, campaign_id=campaign_id,
        company_domain=data.company_domain,
        decision_maker_id=data.decision_maker_id,
        opportunity_id=data.opportunity_id,
        outreach_lead_id=data.outreach_lead_id,
    )
    session.commit()
    return _member_out(m)


def patch_member(
    session: Session, campaign_id: int, member_id: int, data: CampaignMemberPatch, user
) -> CampaignMemberOut:
    m = crepo.get_member(session, member_id)
    if not m or m.campaign_id != campaign_id:
        raise HTTPException(404, "member not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(m, k, v)
    m.last_activity_at = _utcnow()
    session.commit()
    return _member_out(m)


def remove_member(session: Session, campaign_id: int, member_id: int, user) -> None:
    m = crepo.get_member(session, member_id)
    if not m or m.campaign_id != campaign_id:
        raise HTTPException(404, "member not found")
    m.engagement_status = "removed"
    session.commit()


# ================================================================== sequences
def list_sequences(
    session: Session, user, *, active_only: bool = False, limit: int = 50, offset: int = 0
) -> Page:
    seqs, total = crepo.list_sequences(session, active_only=active_only, limit=limit, offset=offset)
    steps_by_seq = crepo.list_steps_batch(session, [s.id for s in seqs])
    items = [_sequence_out(s, steps_by_seq.get(s.id, [])) for s in seqs]
    return Page.build(items, total, max(1, offset // limit + 1), limit)


def get_sequence(session: Session, seq_id: int, user) -> CrmSequenceOut:
    s = crepo.get_sequence(session, seq_id)
    if not s:
        raise HTTPException(404, "sequence not found")
    return _sequence_out(s, crepo.list_steps(session, seq_id))


def create_sequence(session: Session, data: CrmSequenceCreate, user) -> CrmSequenceOut:
    s = crepo.create_sequence(
        session, name=data.name, description=data.description,
        is_active=True, created_by=user.id,
    )
    session.commit()
    return _sequence_out(s, [])


def patch_sequence(session: Session, seq_id: int, data: CrmSequencePatch, user) -> CrmSequenceOut:
    s = crepo.get_sequence(session, seq_id)
    if not s:
        raise HTTPException(404, "sequence not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(s, k, v)
    session.commit()
    return _sequence_out(s, crepo.list_steps(session, seq_id))


def delete_sequence(session: Session, seq_id: int, user) -> None:
    _require_manager(user)
    s = crepo.get_sequence(session, seq_id)
    if not s:
        raise HTTPException(404, "sequence not found")
    s.is_active = False
    session.commit()


# ================================================================== steps
def add_step(session: Session, seq_id: int, data: CrmSequenceStepIn, user) -> CrmSequenceStepOut:
    if not crepo.get_sequence(session, seq_id):
        raise HTTPException(404, "sequence not found")
    st = crepo.add_step(
        session, sequence_id=seq_id, step_order=data.step_order,
        action=data.action, name=data.name, description=data.description,
        delay_days=data.delay_days, template_id=data.template_id,
        config=data.config or {},
    )
    session.commit()
    return _step_out(st)


def patch_step(
    session: Session, seq_id: int, step_id: int, data: CrmSequenceStepPatch, user
) -> CrmSequenceStepOut:
    st = crepo.get_step(session, step_id)
    if not st or st.sequence_id != seq_id:
        raise HTTPException(404, "step not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(st, k, v)
    session.commit()
    return _step_out(st)


def delete_step(session: Session, seq_id: int, step_id: int, user) -> None:
    st = crepo.get_step(session, step_id)
    if not st or st.sequence_id != seq_id:
        raise HTTPException(404, "step not found")
    crepo.delete_step(session, step_id)
    session.commit()


# ================================================================== enrollment
def enroll_lead(
    session: Session, lead_id: int, seq_id: int, member_id: int | None, user
) -> CrmEnrollmentOut:
    lead = orepo.get_lead(session, lead_id)
    if not lead:
        raise HTTPException(404, "lead not found")
    seq = crepo.get_sequence(session, seq_id)
    if not seq or not seq.is_active:
        raise HTTPException(404, "sequence not found or inactive")
    if crepo.get_active_enrollment(session, lead_id, seq_id):
        raise HTTPException(409, "lead already actively enrolled in this sequence")

    steps = crepo.list_steps(session, seq_id)
    first_delay = steps[0].delay_days if steps else 0
    # ponytail: null scheduled_at = "immediately due"; avoids SQLite tz-string comparison edge case
    next_at = None if first_delay == 0 else _utcnow() + timedelta(days=first_delay)

    e = crepo.create_enrollment(
        session,
        sequence_id=seq_id,
        outreach_lead_id=lead_id,
        campaign_member_id=member_id,
        enrolled_by=user.id,
        status="active",
        current_step=steps[0].step_order if steps else 0,
        next_step_at=next_at,
    )
    if steps:
        session.add(SequenceStepExecution(
            enrollment_id=e.id, step_id=steps[0].id,
            status="pending", scheduled_at=next_at,
        ))
    session.commit()
    return _enrollment_out(e)


def control_enrollment(
    session: Session, enrollment_id: int, action: str, user
) -> CrmEnrollmentOut:
    e = crepo.get_enrollment(session, enrollment_id)
    if not e:
        raise HTTPException(404, "enrollment not found")
    if action == "pause":
        e.status = "paused"
    elif action == "resume":
        if e.status != "paused":
            raise HTTPException(400, "enrollment is not paused")
        e.status = "active"
    elif action == "cancel":
        e.status = "cancelled"
        e.completed_at = _utcnow()
    else:
        raise HTTPException(400, f"unknown action: {action}")
    session.commit()
    return _enrollment_out(e)


def skip_step(session: Session, enrollment_id: int, step_id: int, user) -> CrmEnrollmentOut:
    e = crepo.get_enrollment(session, enrollment_id)
    if not e:
        raise HTTPException(404, "enrollment not found")
    ex = session.scalar(
        select(SequenceStepExecution).where(
            SequenceStepExecution.enrollment_id == enrollment_id,
            SequenceStepExecution.step_id == step_id,
            SequenceStepExecution.status == "pending",
        )
    )
    if ex:
        ex.status = "skipped"
    session.commit()
    return _enrollment_out(e)


def advance_enrollment(session: Session, enrollment_id: int, user) -> CrmEnrollmentOut:
    e = crepo.get_enrollment(session, enrollment_id)
    if not e:
        raise HTTPException(404, "enrollment not found")
    _advance_one(session, e)
    session.commit()
    return _enrollment_out(e)


def _advance_one(session: Session, e: SequenceEnrollment) -> None:
    """Advance an active enrollment to its next step. Mutates e in place."""
    steps = crepo.list_steps(session, e.sequence_id)
    next_steps = [st for st in steps if st.step_order > e.current_step]
    if not next_steps:
        e.status = "completed"
        e.completed_at = _utcnow()
        return
    nxt = next_steps[0]
    e.current_step = nxt.step_order
    # null = immediately due (avoids SQLite tz-string comparison edge case)
    next_at = None if nxt.delay_days == 0 else _utcnow() + timedelta(days=nxt.delay_days)
    e.next_step_at = next_at
    session.add(SequenceStepExecution(
        enrollment_id=e.id, step_id=nxt.id,
        status="pending", scheduled_at=next_at,
    ))


def list_enrollments(
    session: Session, user, *,
    sequence_id: int | None = None,
    campaign_id: int | None = None,
    status: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page:
    """Cross-sequence enrollment list — the one view with no natural single-table
    owner (an enrollment's campaign is reached via its member). Joins OutreachLead +
    Company (both NOT NULL/CASCADE FKs off SequenceEnrollment, so INNER JOIN never
    drops a legitimate row) so status/sequence/company filters and pagination all
    apply server-side in one query."""
    member_ids: list[int] | None = None
    if campaign_id is not None:
        if not crepo.get_campaign(session, campaign_id):
            raise HTTPException(404, "campaign not found")
        members, _ = crepo.list_members(session, campaign_id, limit=5000)
        member_ids = [m.id for m in members]
        if not member_ids:
            return Page.build([], 0, 1, limit)

    q = (
        select(SequenceEnrollment)
        .join(OutreachLead, OutreachLead.id == SequenceEnrollment.outreach_lead_id)
        .join(Company, Company.company_domain == OutreachLead.company_domain)
    )
    filters = []
    if sequence_id is not None:
        filters.append(SequenceEnrollment.sequence_id == sequence_id)
    if member_ids is not None:
        filters.append(SequenceEnrollment.campaign_member_id.in_(member_ids))
    if status:
        filters.append(SequenceEnrollment.status == status)
    if search:
        pat = f"%{search}%"
        filters.append(or_(Company.company_name.ilike(pat), Company.company_domain.ilike(pat)))
    if filters:
        q = q.where(and_(*filters))

    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(
        q.order_by(SequenceEnrollment.created_at.desc()).limit(limit).offset(offset)
    ))
    if not rows:
        return Page.build([], total, max(1, offset // limit + 1), limit)

    seq_ids = {e.sequence_id for e in rows}
    seqs_map = {s.id: s for s in session.scalars(select(OutreachSequence).where(OutreachSequence.id.in_(seq_ids)))}
    steps_by_seq = crepo.list_steps_batch(session, list(seq_ids))

    needed_member_ids = {e.campaign_member_id for e in rows if e.campaign_member_id}
    members_map: dict[int, CampaignMember] = {}
    if needed_member_ids:
        members_map = {
            m.id: m for m in session.scalars(select(CampaignMember).where(CampaignMember.id.in_(needed_member_ids)))
        }
    needed_campaign_ids = {m.campaign_id for m in members_map.values()}
    campaigns_map = {
        c.id: c for c in session.scalars(select(Campaign).where(Campaign.id.in_(needed_campaign_ids)))
    } if needed_campaign_ids else {}

    lead_ids = {e.outreach_lead_id for e in rows}
    leads_map = {ld.id: ld for ld in session.scalars(select(OutreachLead).where(OutreachLead.id.in_(lead_ids)))}
    domains = {ld.company_domain for ld in leads_map.values()}
    companies_map = {
        c.company_domain: c.company_name for c in session.scalars(select(Company).where(Company.company_domain.in_(domains)))
    } if domains else {}

    items = []
    for e in rows:
        seq = seqs_map.get(e.sequence_id)
        member = members_map.get(e.campaign_member_id) if e.campaign_member_id else None
        campaign = campaigns_map.get(member.campaign_id) if member else None
        lead = leads_map.get(e.outreach_lead_id)
        domain = lead.company_domain if lead else ""
        out = _enrollment_out(e)
        out.sequence_name = seq.name if seq else ""
        out.step_count = len(steps_by_seq.get(e.sequence_id, []))
        out.campaign_id = member.campaign_id if member else None
        out.campaign_name = campaign.name if campaign else ""
        out.company_domain = domain
        out.company_name = companies_map.get(domain, "")
        items.append(out)

    return Page.build(items, total, max(1, offset // limit + 1), limit)


# ================================================================== scheduler hook
def advance_sequences(session: Session) -> int:
    """Process overdue sequence step executions. Called from the scheduler tick."""
    now = _utcnow()
    executions = crepo.pending_step_executions(session, now=now)
    advanced = 0
    for ex in executions:
        e = session.get(SequenceEnrollment, ex.enrollment_id)
        if not e or e.status != "active":
            ex.status = "skipped"
            continue
        ex.status = "completed"
        ex.executed_at = now
        _advance_one(session, e)
        advanced += 1
    return advanced


# ================================================================== analytics
def campaign_analytics(session: Session, campaign_id: int, user) -> CampaignAnalyticsOut:
    c = crepo.get_campaign(session, campaign_id)
    if not c:
        raise HTTPException(404, "campaign not found")
    members, _ = crepo.list_members(session, campaign_id, limit=5000)

    company_domains = {m.company_domain for m in members if m.company_domain}
    dm_ids = {m.decision_maker_id for m in members if m.decision_maker_id}
    lead_ids = {m.outreach_lead_id for m in members if m.outreach_lead_id}

    emails_sent = replies = meetings = 0
    if lead_ids:
        row = session.execute(
            select(
                func.count(OutreachMessage.id).label("sent"),
                func.count(OutreachMessage.id).filter(
                    OutreachMessage.status == "replied"
                ).label("replied"),
            )
            .where(OutreachMessage.outreach_lead_id.in_(lead_ids))
            .where(OutreachMessage.direction == "outbound")
        ).one()
        emails_sent = row.sent or 0
        replies = row.replied or 0
        meetings = session.scalar(
            select(func.count(OutreachMeeting.id))
            .where(OutreachMeeting.outreach_lead_id.in_(lead_ids))
        ) or 0

    active_members = sum(1 for m in members if m.engagement_status == "active")
    converted = sum(1 for m in members if m.campaign_outcome == "converted")
    total_members = len(members)

    member_ids = [m.id for m in members]
    enrollments = crepo.list_enrollments(session, member_ids=member_ids) if member_ids else []
    seq_completed = sum(1 for e in enrollments if e.status == "completed")
    seq_total = len(enrollments)

    return CampaignAnalyticsOut(
        campaign_id=campaign_id,
        campaign_name=c.name,
        companies_contacted=len(company_domains),
        decision_makers_contacted=len(dm_ids),
        emails_sent=emails_sent,
        replies=replies,
        meetings=meetings,
        reply_rate=round(replies / emails_sent, 4) if emails_sent else 0.0,
        meeting_rate=round(meetings / total_members, 4) if total_members else 0.0,
        conversion_rate=round(converted / total_members, 4) if total_members else 0.0,
        active_members=active_members,
        total_members=total_members,
        converted=converted,
        sequence_completion_rate=round(seq_completed / seq_total, 4) if seq_total else 0.0,
    )


# ================================================================== timeline
def campaign_timeline(
    session: Session, campaign_id: int, user, *, limit: int = 50, offset: int = 0
) -> list[UnifiedTimelineEvent]:
    c = crepo.get_campaign(session, campaign_id)
    if not c:
        raise HTTPException(404, "campaign not found")
    members, _ = crepo.list_members(session, campaign_id, limit=5000)
    lead_ids = {m.outreach_lead_id for m in members if m.outreach_lead_id}
    if not lead_ids:
        return []

    activities = list(session.scalars(
        select(OutreachActivity)
        .where(OutreachActivity.outreach_lead_id.in_(lead_ids))
        .order_by(OutreachActivity.created_at.desc())
        .limit(limit + offset)
    ))
    events = [
        UnifiedTimelineEvent(
            event_id=f"activity-{a.id}",
            event_type="activity",
            type=a.type,
            label=a.type.replace("_", " ").title(),
            detail=a.detail,
            actor=a.actor_email,
            timestamp=_utc(a.created_at) or _utcnow(),
        )
        for a in activities
    ]
    events.sort(key=lambda e: e.timestamp, reverse=True)
    return events[offset: offset + limit]


# ================================================================== dashboard
def campaign_dashboard(session: Session, user) -> CampaignDashboardOut:
    active_campaigns, total_active = crepo.list_campaigns(session, status="active", limit=20)
    cids = [c.id for c in active_campaigns]
    stats = crepo.campaign_stats_batch(session, cids) if cids else {}

    total_emails = total_replies = total_meetings = total_members = 0
    campaign_items = []
    for c in active_campaigns:
        s = stats.get(c.id, {})
        campaign_items.append(_campaign_out(c, stats=s))
        total_emails += s.get("emails_sent", 0)
        total_replies += s.get("replies", 0)
        total_meetings += s.get("meetings", 0)
        total_members += s.get("member_count", 0)

    return CampaignDashboardOut(
        active_campaigns=total_active,
        total_members=total_members,
        emails_sent=total_emails,
        replies=total_replies,
        meetings=total_meetings,
        overall_reply_rate=round(total_replies / total_emails, 4) if total_emails else 0.0,
        campaigns=campaign_items,
    )
