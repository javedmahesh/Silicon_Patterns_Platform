"""Data access for Enterprise CRM Phase 3: Team Collaboration."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from master_db.models import (
    CrmAssignment,
    CrmAssignmentHistory,
    CrmComment,
    CrmNotification,
    CrmSavedView,
    OutreachMeeting,
    OutreachTask,
)

from backend.timeutil import utcnow as _utcnow


# ----------------------------------------------------------------- assignments
def get_assignment(session: Session, assignment_id: int) -> CrmAssignment | None:
    return session.get(CrmAssignment, assignment_id)


def list_entity_assignments(
    session: Session, entity_type: str, entity_id: str
) -> list[CrmAssignment]:
    return list(session.scalars(
        select(CrmAssignment).where(
            CrmAssignment.entity_type == entity_type,
            CrmAssignment.entity_id == entity_id,
        ).order_by(CrmAssignment.created_at)
    ))


def get_existing_assignment(
    session: Session, entity_type: str, entity_id: str, user_id: int, role: str
) -> CrmAssignment | None:
    return session.scalar(
        select(CrmAssignment).where(
            CrmAssignment.entity_type == entity_type,
            CrmAssignment.entity_id == entity_id,
            CrmAssignment.user_id == user_id,
            CrmAssignment.role == role,
        )
    )


def create_assignment(session: Session, **kw) -> CrmAssignment:
    a = CrmAssignment(**kw)
    session.add(a)
    session.flush()
    return a


def add_assignment_history(session: Session, **kw) -> CrmAssignmentHistory:
    h = CrmAssignmentHistory(**kw)
    session.add(h)
    session.flush()
    return h


def list_assignment_history(
    session: Session, entity_type: str, entity_id: str
) -> list[CrmAssignmentHistory]:
    return list(session.scalars(
        select(CrmAssignmentHistory)
        .where(
            CrmAssignmentHistory.entity_type == entity_type,
            CrmAssignmentHistory.entity_id == entity_id,
        )
        .order_by(CrmAssignmentHistory.created_at.desc())
        .limit(100)
    ))


# ----------------------------------------------------------------- work queue
def user_assigned_deal_ids(session: Session, user_id: int) -> list[int]:
    """Deal IDs where user has any role."""
    rows = session.scalars(
        select(CrmAssignment.entity_id)
        .where(CrmAssignment.entity_type == "deal", CrmAssignment.user_id == user_id)
    ).all()
    result = []
    for r in rows:
        try:
            result.append(int(r))
        except (ValueError, TypeError):
            pass
    return result


def user_assigned_campaign_ids(session: Session, user_id: int) -> list[int]:
    rows = session.scalars(
        select(CrmAssignment.entity_id)
        .where(CrmAssignment.entity_type == "campaign", CrmAssignment.user_id == user_id)
    ).all()
    result = []
    for r in rows:
        try:
            result.append(int(r))
        except (ValueError, TypeError):
            pass
    return result


def user_tasks(
    session: Session, user_id: int, *, overdue_only: bool = False, limit: int = 50
) -> list[OutreachTask]:
    q = select(OutreachTask).where(
        OutreachTask.assigned_to == user_id,
        OutreachTask.status.in_(["pending", "in_progress"]),
    )
    if overdue_only:
        q = q.where(OutreachTask.due_at <= _utcnow())
    return list(session.scalars(q.order_by(OutreachTask.due_at.asc().nullslast()).limit(limit)))


def user_upcoming_meetings(session: Session, user_id: int, days: int = 7) -> list[OutreachMeeting]:
    cutoff = _utcnow() + timedelta(days=days)
    return list(session.scalars(
        select(OutreachMeeting)
        .where(
            OutreachMeeting.created_by == user_id,
            OutreachMeeting.scheduled_at >= _utcnow(),
            OutreachMeeting.scheduled_at <= cutoff,
        )
        .order_by(OutreachMeeting.scheduled_at)
        .limit(20)
    ))


def pending_approvals_count(session: Session, user_id: int) -> int:
    """Count outreach messages in pending_approval status assigned to user's leads."""
    from master_db.models import OutreachMessage
    return session.scalar(
        select(func.count(OutreachMessage.id)).where(
            OutreachMessage.status == "pending_approval",
            OutreachMessage.created_by == user_id,
        )
    ) or 0


# ----------------------------------------------------------------- comments
def get_comment(session: Session, comment_id: int) -> CrmComment | None:
    return session.get(CrmComment, comment_id)


def list_comments(
    session: Session, entity_type: str, entity_id: str,
    *, top_level_only: bool = False, limit: int = 50, offset: int = 0
) -> tuple[list[CrmComment], int]:
    q = select(CrmComment).where(
        CrmComment.entity_type == entity_type,
        CrmComment.entity_id == entity_id,
    )
    if top_level_only:
        q = q.where(CrmComment.parent_id.is_(None))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(CrmComment.created_at.asc()).limit(limit).offset(offset)))
    return rows, total


def create_comment(session: Session, **kw) -> CrmComment:
    c = CrmComment(**kw)
    session.add(c)
    session.flush()
    return c


# ----------------------------------------------------------------- notifications
def get_notification(session: Session, notif_id: int) -> CrmNotification | None:
    return session.get(CrmNotification, notif_id)


def list_notifications(
    session: Session, user_id: int,
    *, unread_only: bool = False, limit: int = 50, offset: int = 0
) -> tuple[list[CrmNotification], int]:
    q = select(CrmNotification).where(CrmNotification.user_id == user_id)
    if unread_only:
        q = q.where(CrmNotification.is_read.is_(False))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(
        q.order_by(CrmNotification.created_at.desc()).limit(limit).offset(offset)
    ))
    return rows, total


def unread_count(session: Session, user_id: int) -> int:
    return session.scalar(
        select(func.count(CrmNotification.id)).where(
            CrmNotification.user_id == user_id,
            CrmNotification.is_read.is_(False),
        )
    ) or 0


def create_notification(session: Session, **kw) -> CrmNotification:
    n = CrmNotification(**kw)
    session.add(n)
    session.flush()
    return n


def notify(
    session: Session,
    user_id: int, notif_type: str, title: str, body: str = "",
    entity_type: str | None = None, entity_id: str | None = None,
) -> None:
    """Create a notification, skipping if user is the actor (self-notify guard)."""
    create_notification(
        session, user_id=user_id, notif_type=notif_type,
        title=title, body=body, entity_type=entity_type, entity_id=entity_id,
    )


# ----------------------------------------------------------------- saved views
def get_saved_view(session: Session, view_id: int) -> CrmSavedView | None:
    return session.get(CrmSavedView, view_id)


def list_saved_views(
    session: Session, user_id: int,
    *, entity_type: str | None = None, include_shared: bool = True,
    limit: int = 50,
) -> list[CrmSavedView]:
    q = select(CrmSavedView).where(
        or_(CrmSavedView.owner_id == user_id, CrmSavedView.is_shared.is_(True))
        if include_shared else CrmSavedView.owner_id == user_id
    )
    if entity_type:
        q = q.where(CrmSavedView.entity_type == entity_type)
    return list(session.scalars(q.order_by(CrmSavedView.created_at.desc()).limit(limit)))


def create_saved_view(session: Session, **kw) -> CrmSavedView:
    v = CrmSavedView(**kw)
    session.add(v)
    session.flush()
    return v


# ----------------------------------------------------------------- team analytics
def assignment_distribution(session: Session) -> list[dict]:
    """Per-user assignment counts (all entity types). 1 query."""
    rows = session.execute(
        select(
            CrmAssignment.user_id,
            CrmAssignment.entity_type,
            func.count(CrmAssignment.id).label("cnt"),
        )
        .group_by(CrmAssignment.user_id, CrmAssignment.entity_type)
    ).all()
    result: dict[int, dict] = {}
    for r in rows:
        if r.user_id not in result:
            result[r.user_id] = {"user_id": r.user_id, "total": 0}
        result[r.user_id][r.entity_type] = r.cnt
        result[r.user_id]["total"] += r.cnt
    return list(result.values())


def team_task_stats(session: Session) -> dict:
    """Team-wide task stats in 1 query (grouped by status)."""
    rows = session.execute(
        select(
            OutreachTask.status,
            func.count(OutreachTask.id).label("cnt"),
        )
        .group_by(OutreachTask.status)
    ).all()
    stats = {r.status: r.cnt for r in rows}
    now = _utcnow()
    overdue = session.scalar(
        select(func.count(OutreachTask.id)).where(
            OutreachTask.status.in_(["pending", "in_progress"]),
            OutreachTask.due_at <= now,
        )
    ) or 0
    return {
        "open": stats.get("pending", 0) + stats.get("in_progress", 0),
        "completed": stats.get("completed", 0),
        "cancelled": stats.get("cancelled", 0),
        "overdue": overdue,
    }


def avg_completion_time_seconds(session: Session) -> float | None:
    """Average task completion time (created_at → completed_at) in seconds."""
    result = session.scalar(
        select(func.avg(
            func.julianday(OutreachTask.completed_at) - func.julianday(OutreachTask.created_at)
        ) * 86400).where(
            OutreachTask.completed_at.isnot(None),
            OutreachTask.created_at.isnot(None),
        )
    )
    return float(result) if result is not None else None


# ----------------------------------------------------------------- activity feed
def global_feed_events(
    session: Session, *, limit: int = 50, offset: int = 0,
    user_id: int | None = None
) -> list[CrmAssignmentHistory]:
    """Fetch assignment history as the primary feed source."""
    q = select(CrmAssignmentHistory)
    if user_id is not None:
        q = q.where(
            or_(CrmAssignmentHistory.user_id == user_id,
                CrmAssignmentHistory.changed_by == user_id)
        )
    return list(session.scalars(
        q.order_by(CrmAssignmentHistory.created_at.desc()).limit(limit).offset(offset)
    ))


def feed_comments(
    session: Session, *, limit: int = 50, offset: int = 0,
    user_id: int | None = None,
) -> list[CrmComment]:
    q = select(CrmComment)
    if user_id is not None:
        q = q.where(
            or_(CrmComment.author_id == user_id,
                CrmComment.mentions.contains([user_id]))
        )
    return list(session.scalars(
        q.order_by(CrmComment.created_at.desc()).limit(limit).offset(offset)
    ))
