"""Data access for the native Outreach module's own tables.

Scoped to outreach_leads / outreach_templates / outreach_messages /
outreach_activities. Intelligence (companies, decision_makers, lead_scores,
engagement_recommendations, users) is read through ``backend.repositories`` — this
module never duplicates that data.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from config.enums import OUTREACH_OPEN_STAGES
from master_db.models import (
    Company,
    ConversationLabel,
    EmailAttachment,
    EmailConversation,
    EmailLabel,
    EmailProviderAccount,
    LeadScore,
    OutreachActivity,
    OutreachLead,
    OutreachMeeting,
    OutreachMessage,
    OutreachTask,
    OutreachTemplate,
)

from backend.timeutil import utcnow as _utcnow


# ----------------------------------------------------------------- leads
def get_lead(session: Session, lead_id: int) -> OutreachLead | None:
    return session.get(OutreachLead, lead_id)


def get_lead_by_domain(session: Session, domain: str) -> OutreachLead | None:
    return session.scalar(select(OutreachLead).where(OutreachLead.company_domain == domain))


def list_leads(session: Session, *, stage: str | None = None, owner_id: int | None = None,
               open_only: bool = False, search: str | None = None,
               limit: int = 50, offset: int = 0) -> tuple[list[tuple], int]:
    """Return ``(rows, total)`` where each row is (OutreachLead, Company, LeadScore|None),
    ranked by lead priority_rank then most-recent activity."""
    base = (
        select(OutreachLead, Company, LeadScore)
        .join(Company, Company.company_domain == OutreachLead.company_domain)
        .join(LeadScore, LeadScore.company_domain == OutreachLead.company_domain, isouter=True)
    )
    filters = []
    if stage:
        filters.append(OutreachLead.stage == stage)
    if owner_id is not None:
        filters.append(OutreachLead.owner_id == owner_id)
    if open_only:
        filters.append(OutreachLead.stage.in_(OUTREACH_OPEN_STAGES))
    if search:
        like = f"%{search.lower()}%"
        filters.append(or_(func.lower(Company.company_name).like(like),
                           func.lower(OutreachLead.company_domain).like(like)))
    if filters:
        base = base.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = session.execute(
        base.order_by(LeadScore.priority_rank.is_(None), LeadScore.priority_rank.asc(),
                      OutreachLead.last_activity_at.desc().nullslast())
        .limit(limit).offset(offset)
    ).all()
    return list(rows), total


def create_lead(session: Session, **kw) -> OutreachLead:
    lead = OutreachLead(**kw)
    session.add(lead)
    session.flush()
    return lead


def touch_lead(session: Session, lead: OutreachLead) -> None:
    lead.last_activity_at = _utcnow()


# ----------------------------------------------------------------- templates
def list_templates(session: Session, *, active_only: bool = False) -> list[OutreachTemplate]:
    stmt = select(OutreachTemplate)
    if active_only:
        stmt = stmt.where(OutreachTemplate.is_active.is_(True))
    return list(session.scalars(stmt.order_by(OutreachTemplate.name.asc())))


def get_template(session: Session, template_id: int) -> OutreachTemplate | None:
    return session.get(OutreachTemplate, template_id)


def create_template(session: Session, **kw) -> OutreachTemplate:
    tpl = OutreachTemplate(**kw)
    session.add(tpl)
    session.flush()
    return tpl


def delete_template(session: Session, tpl: OutreachTemplate) -> None:
    session.delete(tpl)


# ----------------------------------------------------------------- messages
def get_message(session: Session, message_id: int) -> OutreachMessage | None:
    return session.get(OutreachMessage, message_id)


def list_messages_for_lead(session: Session, lead_id: int) -> list[OutreachMessage]:
    return list(session.scalars(
        select(OutreachMessage)
        .where(OutreachMessage.outreach_lead_id == lead_id)
        .order_by(OutreachMessage.created_at.asc())
    ))


def create_message(session: Session, **kw) -> OutreachMessage:
    msg = OutreachMessage(**kw)
    session.add(msg)
    session.flush()
    return msg


def list_messages_by_status(session: Session, status: str) -> list[tuple]:
    """(OutreachMessage, OutreachLead, Company) for a status — used by approvals."""
    return list(session.execute(
        select(OutreachMessage, OutreachLead, Company)
        .join(OutreachLead, OutreachLead.id == OutreachMessage.outreach_lead_id)
        .join(Company, Company.company_domain == OutreachLead.company_domain)
        .where(OutreachMessage.status == status)
        .order_by(OutreachMessage.created_at.asc())
    ).all())


def list_threaded_messages(session: Session) -> list[tuple]:
    """All messages that have been sent or are inbound replies, with lead+company —
    used to assemble the Inbox threads. Ordered oldest→newest within the query."""
    return list(session.execute(
        select(OutreachMessage, OutreachLead, Company)
        .join(OutreachLead, OutreachLead.id == OutreachMessage.outreach_lead_id)
        .join(Company, Company.company_domain == OutreachLead.company_domain)
        .where(OutreachMessage.thread_id != "")
        .order_by(OutreachMessage.created_at.asc())
    ).all())


# ----------------------------------------------------------------- activities
def add_activity(session: Session, *, lead_id: int, actor_id: int | None, actor_email: str,
                 type: str, detail: str = "") -> OutreachActivity:
    act = OutreachActivity(
        outreach_lead_id=lead_id, actor_id=actor_id, actor_email=actor_email,
        type=type, detail=detail,
    )
    session.add(act)
    return act


def list_activities(session: Session, lead_id: int, limit: int = 50) -> list[OutreachActivity]:
    return list(session.scalars(
        select(OutreachActivity)
        .where(OutreachActivity.outreach_lead_id == lead_id)
        .order_by(OutreachActivity.created_at.desc())
        .limit(limit)
    ))


def recent_activities(session: Session, limit: int = 20) -> list[tuple]:
    """(OutreachActivity, Company) most-recent across all leads — for the dashboard."""
    return list(session.execute(
        select(OutreachActivity, Company)
        .join(OutreachLead, OutreachLead.id == OutreachActivity.outreach_lead_id)
        .join(Company, Company.company_domain == OutreachLead.company_domain)
        .order_by(OutreachActivity.created_at.desc())
        .limit(limit)
    ).all())


# ----------------------------------------------------------------- analytics
def stage_counts(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(OutreachLead.stage, func.count()).group_by(OutreachLead.stage)
    ).all()
    return {stage: n for stage, n in rows}


def message_status_counts(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(OutreachMessage.status, func.count()).group_by(OutreachMessage.status)
    ).all()
    return {status: n for status, n in rows}


def reply_count_for_lead(session: Session, lead_id: int) -> int:
    return session.scalar(
        select(func.count()).select_from(OutreachMessage)
        .where(OutreachMessage.outreach_lead_id == lead_id,
               OutreachMessage.direction == "inbound")
    ) or 0


# ----------------------------------------------------------------- tasks
def get_task(session: Session, task_id: int) -> OutreachTask | None:
    return session.get(OutreachTask, task_id)


def create_task(session: Session, **kw) -> OutreachTask:
    task = OutreachTask(**kw)
    session.add(task)
    session.flush()
    return task


def list_tasks(
    session: Session,
    *,
    outreach_lead_id: int | None = None,
    company_domain: str | None = None,
    decision_maker_id: int | None = None,
    assigned_to: int | None = None,
    status: str | None = None,
    overdue_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[OutreachTask], int]:
    stmt = select(OutreachTask)
    filters = []
    if outreach_lead_id is not None:
        filters.append(OutreachTask.outreach_lead_id == outreach_lead_id)
    if company_domain:
        filters.append(OutreachTask.company_domain == company_domain)
    if decision_maker_id is not None:
        filters.append(OutreachTask.decision_maker_id == decision_maker_id)
    if assigned_to is not None:
        filters.append(OutreachTask.assigned_to == assigned_to)
    if status:
        filters.append(OutreachTask.status == status)
    if overdue_only:
        now = _utcnow()
        filters.append(OutreachTask.due_at < now)
        filters.append(OutreachTask.status.in_(["pending", "in_progress"]))
    if filters:
        stmt = stmt.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(session.scalars(
        stmt.order_by(OutreachTask.due_at.is_(None), OutreachTask.due_at.asc(), OutreachTask.created_at.desc())
        .limit(limit).offset(offset)
    ))
    return rows, total


def tasks_due_today(session: Session, limit: int = 20) -> list[OutreachTask]:
    now = _utcnow()
    today_end = now.replace(hour=23, minute=59, second=59)
    return list(session.scalars(
        select(OutreachTask)
        .where(
            OutreachTask.due_at.between(now.replace(hour=0, minute=0, second=0), today_end),
            OutreachTask.status.in_(["pending", "in_progress"]),
        )
        .order_by(OutreachTask.due_at.asc())
        .limit(limit)
    ))


def overdue_tasks(session: Session, limit: int = 20) -> list[OutreachTask]:
    now = _utcnow()
    return list(session.scalars(
        select(OutreachTask)
        .where(
            OutreachTask.due_at < now,
            OutreachTask.status.in_(["pending", "in_progress"]),
        )
        .order_by(OutreachTask.due_at.asc())
        .limit(limit)
    ))


def open_task_count(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(OutreachTask)
        .where(OutreachTask.status.in_(["pending", "in_progress"]))
    ) or 0


# ----------------------------------------------------------------- meetings
def get_meeting(session: Session, meeting_id: int) -> OutreachMeeting | None:
    return session.get(OutreachMeeting, meeting_id)


def create_meeting(session: Session, **kw) -> OutreachMeeting:
    meeting = OutreachMeeting(**kw)
    session.add(meeting)
    session.flush()
    return meeting


def list_meetings(
    session: Session,
    *,
    outreach_lead_id: int | None = None,
    company_domain: str | None = None,
    decision_maker_id: int | None = None,
    upcoming_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[OutreachMeeting], int]:
    stmt = select(OutreachMeeting)
    filters = []
    if outreach_lead_id is not None:
        filters.append(OutreachMeeting.outreach_lead_id == outreach_lead_id)
    if company_domain:
        filters.append(OutreachMeeting.company_domain == company_domain)
    if decision_maker_id is not None:
        filters.append(OutreachMeeting.decision_maker_id == decision_maker_id)
    if upcoming_only:
        filters.append(OutreachMeeting.scheduled_at >= _utcnow())
    if filters:
        stmt = stmt.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(session.scalars(
        stmt.order_by(OutreachMeeting.scheduled_at.desc()).limit(limit).offset(offset)
    ))
    return rows, total


def upcoming_meetings(session: Session, limit: int = 10) -> list[OutreachMeeting]:
    now = _utcnow()
    return list(session.scalars(
        select(OutreachMeeting)
        .where(OutreachMeeting.scheduled_at >= now)
        .order_by(OutreachMeeting.scheduled_at.asc())
        .limit(limit)
    ))


def meetings_this_week(session: Session) -> int:
    now = _utcnow()
    week_end = now.replace(hour=23, minute=59, second=59)
    # Monday of this week
    week_start = now.replace(hour=0, minute=0, second=0) - __import__("datetime").timedelta(days=now.weekday())
    return session.scalar(
        select(func.count()).select_from(OutreachMeeting)
        .where(OutreachMeeting.scheduled_at.between(week_start, week_end))
    ) or 0


# ----------------------------------------------------------------- follow-ups
def upcoming_follow_ups(session: Session, limit: int = 20) -> list[tuple]:
    """(OutreachLead, Company) ordered by next_action_at asc — newest due first."""
    return list(session.execute(
        select(OutreachLead, Company)
        .join(Company, Company.company_domain == OutreachLead.company_domain)
        .where(OutreachLead.next_action_at.is_not(None))
        .order_by(OutreachLead.next_action_at.asc())
        .limit(limit)
    ).all())


def overdue_follow_up_count(session: Session) -> int:
    now = _utcnow()
    return session.scalar(
        select(func.count()).select_from(OutreachLead)
        .where(OutreachLead.next_action_at < now)
    ) or 0


def message_counts_for_leads(session: Session, lead_ids: list[int]) -> dict[int, dict[str, int]]:
    """Per-lead {open, sent, replied} message counts in ONE grouped query (avoids the
    N+1 of fetching messages per lead when rendering the pipeline list)."""
    out: dict[int, dict[str, int]] = {i: {"open": 0, "sent": 0, "replied": 0} for i in lead_ids}
    if not lead_ids:
        return out
    rows = session.execute(
        select(OutreachMessage.outreach_lead_id, OutreachMessage.direction,
               OutreachMessage.status, func.count())
        .where(OutreachMessage.outreach_lead_id.in_(lead_ids))
        .group_by(OutreachMessage.outreach_lead_id, OutreachMessage.direction, OutreachMessage.status)
    ).all()
    for lead_id, direction, status, n in rows:
        b = out.setdefault(lead_id, {"open": 0, "sent": 0, "replied": 0})
        if status in ("draft", "pending_approval", "approved"):
            b["open"] += n
        if direction == "outbound" and status in ("sent", "replied"):
            b["sent"] += n
        if direction == "inbound":
            b["replied"] += n
    return out


# ----------------------------------------------------------------- attachments
def list_attachments(session: Session, message_id: int) -> list[EmailAttachment]:
    return list(session.scalars(
        select(EmailAttachment)
        .where(EmailAttachment.outreach_message_id == message_id)
        .order_by(EmailAttachment.created_at.asc())
    ))


def count_attachments(session: Session, message_id: int) -> int:
    return session.scalar(
        select(func.count()).select_from(EmailAttachment)
        .where(EmailAttachment.outreach_message_id == message_id)
    ) or 0


def get_attachment(session: Session, attachment_id: int) -> EmailAttachment | None:
    return session.get(EmailAttachment, attachment_id)


def create_attachment(session: Session, **kw) -> EmailAttachment:
    att = EmailAttachment(**kw)
    session.add(att)
    session.flush()
    return att


# ----------------------------------------------------------------- messages: dedup by provider ID
def get_message_by_provider_id(session: Session, provider_message_id: str) -> OutreachMessage | None:
    """Fetch a message by its provider-assigned ID (for deduplication during sync)."""
    if not provider_message_id:
        return None
    return session.scalar(
        select(OutreachMessage).where(OutreachMessage.provider_message_id == provider_message_id)
    )


# ----------------------------------------------------------------- provider accounts
def get_provider_account(session: Session, user_id: int | None) -> EmailProviderAccount | None:
    return session.scalar(
        select(EmailProviderAccount).where(EmailProviderAccount.user_id == user_id)
    )


def create_provider_account(session: Session, **kw) -> EmailProviderAccount:
    acct = EmailProviderAccount(**kw)
    session.add(acct)
    session.flush()
    return acct


def upsert_provider_account(session: Session, user_id: int | None, **kw) -> EmailProviderAccount:
    """Get or create an EmailProviderAccount for user_id, applying **kw as updates."""
    acct = get_provider_account(session, user_id=user_id)
    if acct is None:
        acct = create_provider_account(session, user_id=user_id, **kw)
    else:
        for k, v in kw.items():
            setattr(acct, k, v)
    session.flush()
    return acct


# ----------------------------------------------------------------- conversations (Phase 3)
def get_conversation(session: Session, conv_id: int) -> EmailConversation | None:
    return session.get(EmailConversation, conv_id)


def get_conversation_by_thread(session: Session, thread_id: str) -> EmailConversation | None:
    if not thread_id:
        return None
    return session.scalar(
        select(EmailConversation).where(EmailConversation.thread_id == thread_id)
    )


def create_conversation(session: Session, **kw) -> EmailConversation:
    conv = EmailConversation(**kw)
    session.add(conv)
    session.flush()
    return conv


def list_conversations(
    session: Session,
    *,
    folder: str | None = None,
    outreach_lead_id: int | None = None,
    company_domain: str | None = None,
    decision_maker_id: int | None = None,
    label_id: int | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[tuple], int]:
    """Returns (rows, total) where each row is (EmailConversation, Company|None)."""
    base = (
        select(EmailConversation, Company)
        .join(Company, Company.company_domain == EmailConversation.company_domain, isouter=True)
    )
    filters = []
    if folder == "archived":
        filters.append(EmailConversation.is_archived.is_(True))
        filters.append(EmailConversation.is_trashed.is_(False))
    elif folder == "trash":
        filters.append(EmailConversation.is_trashed.is_(True))
    else:
        filters.append(EmailConversation.is_trashed.is_(False))
        filters.append(EmailConversation.is_archived.is_(False))
        if folder:
            filters.append(EmailConversation.folder == folder)
    if outreach_lead_id is not None:
        filters.append(EmailConversation.outreach_lead_id == outreach_lead_id)
    if company_domain:
        filters.append(EmailConversation.company_domain == company_domain)
    if decision_maker_id is not None:
        filters.append(EmailConversation.decision_maker_id == decision_maker_id)
    if label_id is not None:
        filters.append(
            EmailConversation.id.in_(
                select(ConversationLabel.conversation_id)
                .where(ConversationLabel.label_id == label_id)
            )
        )
    if search:
        like = f"%{search.lower()}%"
        filters.append(
            or_(func.lower(EmailConversation.subject).like(like),
                func.lower(Company.company_name).like(like))
        )
    if filters:
        base = base.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = session.execute(
        base.order_by(EmailConversation.last_message_at.desc().nullslast())
        .limit(limit).offset(offset)
    ).all()
    return list(rows), total


def get_conversation_messages(session: Session, conv_id: int) -> list[OutreachMessage]:
    return list(session.scalars(
        select(OutreachMessage)
        .where(OutreachMessage.conversation_id == conv_id)
        .order_by(OutreachMessage.created_at.asc())
    ))


def _coerce_utc(dt) -> datetime:
    """Ensure datetime is UTC-aware — SQLite returns naive datetimes."""
    if dt is None:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    if getattr(dt, "tzinfo", None) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def update_conversation_stats(session: Session, conv_id: int) -> None:
    """Recompute message_count, unread_count, last_message_at, and folder from messages."""
    msgs = list(session.scalars(
        select(OutreachMessage).where(OutreachMessage.conversation_id == conv_id)
    ))
    if not msgs:
        return
    conv = session.get(EmailConversation, conv_id)
    if conv is None:
        return
    conv.message_count = len(msgs)
    conv.unread_count = sum(1 for m in msgs if not m.is_read and m.direction == "inbound")
    latest = max(msgs, key=lambda m: _coerce_utc(m.created_at))
    conv.last_message_at = latest.created_at
    conv.folder = _derive_folder(latest)


def _derive_folder(msg: OutreachMessage) -> str:
    if msg.is_trashed:
        return "trash"
    if msg.is_archived:
        return "archived"
    if msg.status in ("draft", "pending_approval"):
        return "drafts"
    if msg.status == "scheduled":
        return "scheduled"
    if msg.status in ("failed", "bounced", "cancelled"):
        return "failed"
    if msg.direction == "inbound":
        return "inbox"
    if msg.status in ("sent", "delivered", "replied"):
        return "sent"
    return "inbox"


def get_conversation_labels(session: Session, conv_id: int) -> list[EmailLabel]:
    return list(session.scalars(
        select(EmailLabel)
        .join(ConversationLabel, ConversationLabel.label_id == EmailLabel.id)
        .where(ConversationLabel.conversation_id == conv_id)
    ))


def get_label(session: Session, label_id: int) -> EmailLabel | None:
    return session.get(EmailLabel, label_id)


def get_label_by_name(session: Session, name: str) -> EmailLabel | None:
    return session.scalar(select(EmailLabel).where(EmailLabel.name == name))


def list_labels(session: Session) -> list[EmailLabel]:
    return list(session.scalars(
        select(EmailLabel).order_by(EmailLabel.is_system.desc(), EmailLabel.name.asc())
    ))


def create_label(session: Session, **kw) -> EmailLabel:
    lbl = EmailLabel(**kw)
    session.add(lbl)
    session.flush()
    return lbl


def add_label_to_conversation(session: Session, conv_id: int, label_id: int) -> None:
    existing = session.scalar(
        select(ConversationLabel)
        .where(ConversationLabel.conversation_id == conv_id,
               ConversationLabel.label_id == label_id)
    )
    if existing is None:
        session.add(ConversationLabel(conversation_id=conv_id, label_id=label_id))
        session.flush()


def remove_label_from_conversation(session: Session, conv_id: int, label_id: int) -> None:
    cl = session.scalar(
        select(ConversationLabel)
        .where(ConversationLabel.conversation_id == conv_id,
               ConversationLabel.label_id == label_id)
    )
    if cl:
        session.delete(cl)


# ----------------------------------------------------------------- message search (Phase 3)
def search_messages(
    session: Session,
    *,
    q: str | None = None,
    company_domain: str | None = None,
    decision_maker_id: int | None = None,
    status: str | None = None,
    folder: str | None = None,
    date_from=None,
    date_to=None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[OutreachMessage], int]:
    stmt = select(OutreachMessage)
    filters = []
    if q:
        like = f"%{q.lower()}%"
        filters.append(
            or_(func.lower(OutreachMessage.subject).like(like),
                func.lower(OutreachMessage.body).like(like),
                func.lower(OutreachMessage.to_email).like(like),
                func.lower(OutreachMessage.from_email).like(like))
        )
    if company_domain:
        lead_ids = select(OutreachLead.id).where(OutreachLead.company_domain == company_domain)
        filters.append(OutreachMessage.outreach_lead_id.in_(lead_ids))
    if decision_maker_id is not None:
        filters.append(OutreachMessage.decision_maker_id == decision_maker_id)
    if status:
        filters.append(OutreachMessage.status == status)
    if folder:
        filters.append(OutreachMessage.folder == folder)
    if date_from:
        filters.append(OutreachMessage.created_at >= date_from)
    if date_to:
        filters.append(OutreachMessage.created_at <= date_to)
    if filters:
        stmt = stmt.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(session.scalars(stmt.order_by(OutreachMessage.created_at.desc()).limit(limit).offset(offset)))
    return rows, total


# ----------------------------------------------------------------- bulk ops (Phase 3)
def bulk_update_messages(session: Session, message_ids: list[int], **kw) -> int:
    from sqlalchemy import update as sa_update
    if not message_ids:
        return 0
    result = session.execute(
        sa_update(OutreachMessage)
        .where(OutreachMessage.id.in_(message_ids))
        .values(**kw)
    )
    return result.rowcount


def bulk_update_conversations(session: Session, conv_ids: list[int], **kw) -> int:
    from sqlalchemy import update as sa_update
    if not conv_ids:
        return 0
    result = session.execute(
        sa_update(EmailConversation)
        .where(EmailConversation.id.in_(conv_ids))
        .values(**kw)
    )
    return result.rowcount


def seed_system_labels(session: Session) -> None:
    """Ensure system labels exist — idempotent, called on startup."""
    from config.enums import SYSTEM_LABEL_NAMES
    colors = {"follow-up": "yellow", "prospect": "blue", "customer": "green",
              "internal": "purple", "important": "red"}
    for name in SYSTEM_LABEL_NAMES:
        if get_label_by_name(session, name) is None:
            session.add(EmailLabel(name=name, color=colors.get(name, "gray"), is_system=True))
    session.flush()
