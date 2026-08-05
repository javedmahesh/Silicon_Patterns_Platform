"""Enterprise CRM Phase 3: Team Collaboration business logic."""
from __future__ import annotations


from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import collab_repo as repo
from backend.schemas import (
    CrmAssignmentCreate as AssignmentCreate,
    CrmAssignmentHistoryOut as AssignmentHistoryOut,
    CrmAssignmentOut as AssignmentOut,
    CrmAssignmentPatch as AssignmentPatch,
    CommentCreate,
    CommentOut,
    CommentPatch,
    NotificationOut,
    Page,
    SavedViewCreate,
    SavedViewOut,
    SavedViewPatch,
    TeamAnalyticsOut,
    TeamAssignmentDistRow,
    TeamDashboardOut,
    UnifiedTimelineEvent,
    WorkQueueOut,
)
from master_db.models import (
    Campaign,
    CrmAssignment,
    CrmAssignmentHistory,
    CrmComment,
    CrmDeal,
    CrmNotification,
    CrmSavedView,
    OutreachMeeting,
    OutreachTask,
    User,
)

from backend.timeutil import utc as _utc, utcnow as _utcnow


def _is_manager(user) -> bool:
    return getattr(user, "role", "member") in ("admin", "manager")


def _load_user_emails(session: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = session.scalars(select(User).where(User.id.in_(ids))).all()
    return {u.id: u.email for u in rows}


# ----------------------------------------------------------------- serializers
def _assign_out(a: CrmAssignment, user_email: str = "") -> AssignmentOut:
    return AssignmentOut(
        id=a.id, entity_type=a.entity_type, entity_id=a.entity_id,
        user_id=a.user_id, user_email=user_email,
        role=a.role, assigned_by=a.assigned_by, note=a.note,
        created_at=_utc(a.created_at), updated_at=_utc(a.updated_at),
    )


def _history_out(h: CrmAssignmentHistory, user_email: str = "") -> AssignmentHistoryOut:
    return AssignmentHistoryOut(
        id=h.id, entity_type=h.entity_type, entity_id=h.entity_id,
        user_id=h.user_id, user_email=user_email,
        role=h.role, action=h.action, changed_by=h.changed_by,
        detail=h.detail, created_at=_utc(h.created_at),
    )


def _comment_out(c: CrmComment, author_email: str = "") -> CommentOut:
    return CommentOut(
        id=c.id, entity_type=c.entity_type, entity_id=c.entity_id,
        author_id=c.author_id, author_email=author_email,
        body=c.body, mentions=list(c.mentions or []),
        parent_id=c.parent_id, is_edited=c.is_edited,
        created_at=_utc(c.created_at), updated_at=_utc(c.updated_at),
    )


def _notif_out(n: CrmNotification) -> NotificationOut:
    return NotificationOut(
        id=n.id, user_id=n.user_id, notif_type=n.notif_type,
        title=n.title, body=n.body,
        entity_type=n.entity_type, entity_id=n.entity_id,
        is_read=n.is_read, created_at=_utc(n.created_at),
    )


def _view_out(v: CrmSavedView, owner_email: str = "") -> SavedViewOut:
    return SavedViewOut(
        id=v.id, name=v.name, entity_type=v.entity_type,
        owner_id=v.owner_id, owner_email=owner_email, is_shared=v.is_shared,
        filters=dict(v.filters or {}), sort_by=v.sort_by, sort_dir=v.sort_dir,
        columns=list(v.columns or []), grouping=v.grouping, search=v.search,
        created_at=_utc(v.created_at), updated_at=_utc(v.updated_at),
    )


# ================================================================== assignments
def list_entity_assignments(
    session: Session, entity_type: str, entity_id: str, user
) -> list[AssignmentOut]:
    assignments = repo.list_entity_assignments(session, entity_type, entity_id)
    user_ids = [a.user_id for a in assignments]
    email_map = _load_user_emails(session, user_ids)
    return [_assign_out(a, email_map.get(a.user_id, "")) for a in assignments]


def create_assignment(
    session: Session, data: AssignmentCreate, user
) -> AssignmentOut:
    existing = repo.get_existing_assignment(
        session, data.entity_type, data.entity_id, data.user_id, data.role
    )
    if existing:
        raise HTTPException(409, "assignment already exists")

    a = repo.create_assignment(
        session,
        entity_type=data.entity_type, entity_id=data.entity_id,
        user_id=data.user_id, role=data.role,
        assigned_by=user.id, note=data.note or "",
    )
    repo.add_assignment_history(
        session, entity_type=data.entity_type, entity_id=data.entity_id,
        user_id=data.user_id, role=data.role, action="assigned",
        changed_by=user.id, detail=data.note or "",
    )
    # Notify the assignee (skip self-notify)
    if data.user_id != user.id and data.role in ("owner", "assignee", "reviewer", "manager"):
        repo.notify(
            session, user_id=data.user_id, notif_type="assignment",
            title=f"You were assigned as {data.role}",
            body=f"On {data.entity_type} #{data.entity_id}",
            entity_type=data.entity_type, entity_id=data.entity_id,
        )
    session.commit()
    email_map = _load_user_emails(session, [data.user_id])
    return _assign_out(a, email_map.get(data.user_id, ""))


def patch_assignment(
    session: Session, assignment_id: int, data: AssignmentPatch, user
) -> AssignmentOut:
    a = repo.get_assignment(session, assignment_id)
    if not a:
        raise HTTPException(404, "assignment not found")
    old_role = a.role
    if data.role is not None:
        a.role = data.role
    if data.note is not None:
        a.note = data.note
    repo.add_assignment_history(
        session, entity_type=a.entity_type, entity_id=a.entity_id,
        user_id=a.user_id, role=a.role, action="role_changed",
        changed_by=user.id, detail=f"{old_role} → {a.role}",
    )
    session.commit()
    email_map = _load_user_emails(session, [a.user_id])
    return _assign_out(a, email_map.get(a.user_id, ""))


def delete_assignment(session: Session, assignment_id: int, user) -> None:
    a = repo.get_assignment(session, assignment_id)
    if not a:
        raise HTTPException(404, "assignment not found")
    repo.add_assignment_history(
        session, entity_type=a.entity_type, entity_id=a.entity_id,
        user_id=a.user_id, role=a.role, action="removed",
        changed_by=user.id,
    )
    session.delete(a)
    session.commit()


def list_assignment_history(
    session: Session, entity_type: str, entity_id: str, user
) -> list[AssignmentHistoryOut]:
    history = repo.list_assignment_history(session, entity_type, entity_id)
    user_ids = [h.user_id for h in history if h.user_id]
    email_map = _load_user_emails(session, user_ids)
    return [_history_out(h, email_map.get(h.user_id, "")) for h in history]


# ================================================================== work queue
def work_queue(session: Session, user) -> WorkQueueOut:
    uid = user.id

    deal_ids = repo.user_assigned_deal_ids(session, uid)
    my_deals: list[CrmDeal] = []
    if deal_ids:
        my_deals = list(session.scalars(
            select(CrmDeal).where(CrmDeal.id.in_(deal_ids)).limit(20)
        ))

    campaign_ids = repo.user_assigned_campaign_ids(session, uid)
    my_campaigns: list[Campaign] = []
    if campaign_ids:
        my_campaigns = list(session.scalars(
            select(Campaign).where(Campaign.id.in_(campaign_ids)).limit(20)
        ))

    tasks_due = repo.user_tasks(session, uid, limit=20)
    overdue_tasks = repo.user_tasks(session, uid, overdue_only=True, limit=10)
    upcoming_meetings = repo.user_upcoming_meetings(session, uid, days=7)
    unread = repo.unread_count(session, uid)
    pending_approvals = repo.pending_approvals_count(session, uid)

    from backend.schemas import CampaignOut, DealOut, OutreachMeetingOut, OutreachTaskOut

    def _task_out(t: OutreachTask) -> OutreachTaskOut:
        now = _utcnow()
        return OutreachTaskOut(
            id=t.id, title=t.title, description=t.description,
            company_domain=t.company_domain, decision_maker_id=t.decision_maker_id,
            outreach_lead_id=t.outreach_lead_id,
            assigned_to=t.assigned_to, created_by=t.created_by,
            due_at=_utc(t.due_at), priority=t.priority, status=t.status,
            completed_by=t.completed_by, completed_at=_utc(t.completed_at),
            created_at=_utc(t.created_at), updated_at=_utc(t.updated_at),
            is_overdue=bool(t.due_at and _utc(t.due_at) < now),
        )

    def _mtg_out(m: OutreachMeeting) -> OutreachMeetingOut:
        return OutreachMeetingOut(
            id=m.id, outreach_lead_id=m.outreach_lead_id,
            company_domain=m.company_domain, decision_maker_id=m.decision_maker_id,
            meeting_type=m.meeting_type, title=m.title,
            scheduled_at=_utc(m.scheduled_at) or _utcnow(),
            duration_minutes=m.duration_minutes, participants=list(m.participants or []),
            notes=m.notes, outcome=m.outcome, next_action=m.next_action,
            created_by=m.created_by, created_at=_utc(m.created_at), updated_at=_utc(m.updated_at),
            is_upcoming=True,
        )

    def _deal_simple(d: CrmDeal) -> DealOut:
        return DealOut(
            id=d.id, title=d.title, company_domain=d.company_domain,
            pipeline_id=d.pipeline_id, stage_id=d.stage_id,
            owner_id=d.owner_id, value=d.value, currency=d.currency,
            probability=d.probability, forecast_category=d.forecast_category,
            tags=list(d.tags or []), notes=d.notes,
            created_at=_utc(d.created_at), updated_at=_utc(d.updated_at),
        )

    def _camp_simple(c: Campaign) -> CampaignOut:
        return CampaignOut(
            id=c.id, name=c.name, description=c.description,
            campaign_type=c.campaign_type, status=c.status,
            owner_id=c.owner_id, created_by=c.created_by,
            tags=list(c.tags or []),
            created_at=_utc(c.created_at), updated_at=_utc(c.updated_at),
        )

    return WorkQueueOut(
        my_deals=[_deal_simple(d) for d in my_deals],
        my_campaigns=[_camp_simple(c) for c in my_campaigns],
        tasks_due=[_task_out(t) for t in tasks_due],
        overdue_tasks=[_task_out(t) for t in overdue_tasks],
        upcoming_meetings=[_mtg_out(m) for m in upcoming_meetings],
        unread_notifications=unread,
        pending_approvals=pending_approvals,
    )


# ================================================================== comments
def list_comments(
    session: Session, entity_type: str, entity_id: str, user,
    *, top_level_only: bool = False, limit: int = 50, offset: int = 0,
) -> Page:
    comments, total = repo.list_comments(
        session, entity_type, entity_id,
        top_level_only=top_level_only, limit=limit, offset=offset
    )
    author_ids = [c.author_id for c in comments if c.author_id]
    email_map = _load_user_emails(session, author_ids)
    items = [_comment_out(c, email_map.get(c.author_id, "")) for c in comments]
    return Page.build(items, total, max(1, offset // limit + 1) if limit else 1, limit)


def create_comment(
    session: Session, entity_type: str, entity_id: str,
    data: CommentCreate, user
) -> CommentOut:
    # Parse @user_id mentions from body (format: @123)
    import re
    raw_mentions = [int(m) for m in re.findall(r"@(\d+)", data.body)]
    # If explicit mentions provided, merge with parsed
    mentions = list({*raw_mentions, *(data.mentions or [])})

    c = repo.create_comment(
        session, entity_type=entity_type, entity_id=entity_id,
        author_id=user.id, body=data.body, mentions=mentions,
        parent_id=data.parent_id,
    )

    # Notify each mentioned user
    for uid in mentions:
        if uid != user.id:
            repo.notify(
                session, user_id=uid, notif_type="mention",
                title=f"{user.email} mentioned you",
                body=data.body[:200],
                entity_type=entity_type, entity_id=entity_id,
            )

    # Notify entity assignees (for comment notification, not mentions)
    assignees = repo.list_entity_assignments(session, entity_type, entity_id)
    notified = set(mentions)
    for a in assignees:
        if a.user_id not in notified and a.user_id != user.id:
            repo.notify(
                session, user_id=a.user_id, notif_type="comment",
                title=f"New comment on {entity_type} #{entity_id}",
                body=data.body[:200],
                entity_type=entity_type, entity_id=entity_id,
            )
            notified.add(a.user_id)

    session.commit()
    return _comment_out(c, user.email)


def patch_comment(
    session: Session, comment_id: int, data: CommentPatch, user
) -> CommentOut:
    c = repo.get_comment(session, comment_id)
    if not c:
        raise HTTPException(404, "comment not found")
    if c.author_id != user.id and not _is_manager(user):
        raise HTTPException(403, "can only edit your own comments")
    if data.body is not None:
        c.body = data.body
        c.is_edited = True
    session.commit()
    return _comment_out(c, user.email)


def delete_comment(session: Session, comment_id: int, user) -> None:
    c = repo.get_comment(session, comment_id)
    if not c:
        raise HTTPException(404, "comment not found")
    if c.author_id != user.id and not _is_manager(user):
        raise HTTPException(403, "can only delete your own comments")
    session.delete(c)
    session.commit()


# ================================================================== notifications
def list_notifications(
    session: Session, user, *, unread_only: bool = False,
    limit: int = 50, offset: int = 0,
) -> Page:
    notifs, total = repo.list_notifications(
        session, user.id, unread_only=unread_only, limit=limit, offset=offset
    )
    items = [_notif_out(n) for n in notifs]
    return Page.build(items, total, max(1, offset // limit + 1) if limit else 1, limit)


def mark_read(session: Session, notif_id: int, user) -> NotificationOut:
    n = repo.get_notification(session, notif_id)
    if not n:
        raise HTTPException(404, "notification not found")
    if n.user_id != user.id:
        raise HTTPException(403, "not your notification")
    n.is_read = True
    session.commit()
    return _notif_out(n)


def mark_all_read(session: Session, user) -> int:
    from sqlalchemy import update
    from master_db.models import CrmNotification as N
    result = session.execute(
        update(N).where(N.user_id == user.id, N.is_read.is_(False))
        .values(is_read=True)
    )
    session.commit()
    return result.rowcount


# ================================================================== saved views
def list_saved_views(
    session: Session, user, *, entity_type: str | None = None
) -> list[SavedViewOut]:
    views = repo.list_saved_views(session, user.id, entity_type=entity_type)
    owner_ids = [v.owner_id for v in views if v.owner_id]
    email_map = _load_user_emails(session, owner_ids)
    return [_view_out(v, email_map.get(v.owner_id, "")) for v in views]


def create_saved_view(session: Session, data: SavedViewCreate, user) -> SavedViewOut:
    v = repo.create_saved_view(
        session, name=data.name, entity_type=data.entity_type,
        owner_id=user.id, is_shared=data.is_shared,
        filters=data.filters or {}, sort_by=data.sort_by or "",
        sort_dir=data.sort_dir, columns=data.columns or [],
        grouping=data.grouping or "", search=data.search or "",
    )
    session.commit()
    return _view_out(v, user.email)


def patch_saved_view(
    session: Session, view_id: int, data: SavedViewPatch, user
) -> SavedViewOut:
    v = repo.get_saved_view(session, view_id)
    if not v:
        raise HTTPException(404, "saved view not found")
    if v.owner_id != user.id and not _is_manager(user):
        raise HTTPException(403, "can only edit your own views")
    if data.name is not None:
        v.name = data.name
    if data.is_shared is not None:
        v.is_shared = data.is_shared
    if data.filters is not None:
        v.filters = data.filters
    if data.sort_by is not None:
        v.sort_by = data.sort_by
    if data.sort_dir is not None:
        v.sort_dir = data.sort_dir
    if data.columns is not None:
        v.columns = data.columns
    if data.grouping is not None:
        v.grouping = data.grouping
    if data.search is not None:
        v.search = data.search
    session.commit()
    return _view_out(v, user.email)


def delete_saved_view(session: Session, view_id: int, user) -> None:
    v = repo.get_saved_view(session, view_id)
    if not v:
        raise HTTPException(404, "saved view not found")
    if v.owner_id != user.id and not _is_manager(user):
        raise HTTPException(403, "can only delete your own views")
    session.delete(v)
    session.commit()


# ================================================================== team dashboard
def team_dashboard(session: Session, user) -> TeamDashboardOut:
    uid = user.id
    unread = repo.unread_count(session, uid)
    pending_approvals = repo.pending_approvals_count(session, uid)

    deal_ids = repo.user_assigned_deal_ids(session, uid)
    active_deals = len(deal_ids)

    campaign_ids = repo.user_assigned_campaign_ids(session, uid)
    active_campaigns = len(campaign_ids)

    tasks_due = repo.user_tasks(session, uid, limit=5)
    overdue_tasks = repo.user_tasks(session, uid, overdue_only=True, limit=5)
    upcoming_meetings = repo.user_upcoming_meetings(session, uid, days=7)

    task_stats = repo.team_task_stats(session)
    dist = repo.assignment_distribution(session)

    return TeamDashboardOut(
        unread_notifications=unread,
        pending_approvals=pending_approvals,
        my_active_deals=active_deals,
        my_active_campaigns=active_campaigns,
        tasks_due_count=len(tasks_due),
        overdue_tasks_count=len(overdue_tasks),
        upcoming_meetings_count=len(upcoming_meetings),
        team_open_tasks=task_stats.get("open", 0),
        team_overdue_tasks=task_stats.get("overdue", 0),
        team_completed_tasks=task_stats.get("completed", 0),
        total_assignments=sum(d.get("total", 0) for d in dist),
    )


# ================================================================== workload analytics
def workload_analytics(session: Session, user) -> TeamAnalyticsOut:
    task_stats = repo.team_task_stats(session)
    dist = repo.assignment_distribution(session)
    avg_secs = repo.avg_completion_time_seconds(session)

    user_ids = [d["user_id"] for d in dist]
    email_map = _load_user_emails(session, user_ids)

    distribution = [
        TeamAssignmentDistRow(
            user_id=d["user_id"],
            user_email=email_map.get(d["user_id"], ""),
            total=d.get("total", 0),
            deals=d.get("deal", 0),
            campaigns=d.get("campaign", 0),
            tasks=d.get("task", 0),
            meetings=d.get("meeting", 0),
        )
        for d in sorted(dist, key=lambda x: -x.get("total", 0))
    ]

    return TeamAnalyticsOut(
        open_work=task_stats.get("open", 0),
        completed_work=task_stats.get("completed", 0),
        overdue_work=task_stats.get("overdue", 0),
        avg_completion_time_hours=(
            round(avg_secs / 3600, 1) if avg_secs is not None else None
        ),
        assignment_distribution=distribution,
        total_assignments=sum(d.get("total", 0) for d in dist),
    )


# ================================================================== activity feed
def activity_feed(
    session: Session, user, *, limit: int = 50, offset: int = 0
) -> list[UnifiedTimelineEvent]:
    hist = repo.global_feed_events(session, limit=limit // 2, offset=offset)
    comments = repo.feed_comments(session, limit=limit // 2, offset=offset)

    events: list[UnifiedTimelineEvent] = []

    for h in hist:
        events.append(UnifiedTimelineEvent(
            event_id=f"assign-{h.id}", event_type="assignment",
            type=h.action,
            label=f"{h.action.title()} on {h.entity_type} #{h.entity_id}",
            detail=h.detail, actor="",
            timestamp=_utc(h.created_at) or _utcnow(),
        ))

    for c in comments:
        events.append(UnifiedTimelineEvent(
            event_id=f"comment-{c.id}", event_type="comment",
            type="comment",
            label=f"Comment on {c.entity_type} #{c.entity_id}",
            detail=c.body[:100], actor="",
            timestamp=_utc(c.created_at) or _utcnow(),
        ))

    events.sort(key=lambda e: e.timestamp, reverse=True)
    return events[:limit]
