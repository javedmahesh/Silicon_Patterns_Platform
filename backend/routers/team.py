"""Enterprise CRM Phase 3: Team Collaboration & Work Management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import collab_service as svc
from backend.dependencies import get_session
from backend.security import get_current_user
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
    TeamDashboardOut,
    UnifiedTimelineEvent,
    WorkQueueOut,
)
from master_db.models import User

router = APIRouter(prefix="/team", tags=["team"])


# ============================================================ assignments
@router.get("/assignments/{entity_type}/{entity_id}", response_model=list[AssignmentOut])
def list_entity_assignments(
    entity_type: str,
    entity_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_entity_assignments(session, entity_type, entity_id, user)


@router.post(
    "/assignments",
    response_model=AssignmentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    data: AssignmentCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_assignment(session, data, user)


@router.patch("/assignments/{assignment_id}", response_model=AssignmentOut)
def patch_assignment(
    assignment_id: int,
    data: AssignmentPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_assignment(session, assignment_id, data, user)


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_assignment(session, assignment_id, user)


@router.get(
    "/assignments/{entity_type}/{entity_id}/history",
    response_model=list[AssignmentHistoryOut],
)
def assignment_history(
    entity_type: str,
    entity_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_assignment_history(session, entity_type, entity_id, user)


# ============================================================ work queue
@router.get("/work-queue", response_model=WorkQueueOut)
def work_queue(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.work_queue(session, user)


# ============================================================ comments
@router.get("/comments/{entity_type}/{entity_id}", response_model=Page)
def list_comments(
    entity_type: str,
    entity_id: str,
    top_level_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_comments(
        session, entity_type, entity_id, user,
        top_level_only=top_level_only, limit=limit, offset=offset,
    )


@router.post(
    "/comments/{entity_type}/{entity_id}",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    entity_type: str,
    entity_id: str,
    data: CommentCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_comment(session, entity_type, entity_id, data, user)


@router.patch("/comments/{comment_id}", response_model=CommentOut)
def patch_comment(
    comment_id: int,
    data: CommentPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_comment(session, comment_id, data, user)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_comment(session, comment_id, user)


# ============================================================ notifications
@router.get("/notifications", response_model=Page)
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_notifications(session, user, unread_only=unread_only, limit=limit, offset=offset)


@router.post("/notifications/{notif_id}/read", response_model=NotificationOut)
def mark_read(
    notif_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.mark_read(session, notif_id, user)


@router.post("/notifications/read-all")
def mark_all_read(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    count = svc.mark_all_read(session, user)
    return {"marked_read": count}


# ============================================================ saved views
@router.get("/saved-views", response_model=list[SavedViewOut])
def list_saved_views(
    entity_type: str | None = Query(None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.list_saved_views(session, user, entity_type=entity_type)


@router.post(
    "/saved-views",
    response_model=SavedViewOut,
    status_code=status.HTTP_201_CREATED,
)
def create_saved_view(
    data: SavedViewCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.create_saved_view(session, data, user)


@router.patch("/saved-views/{view_id}", response_model=SavedViewOut)
def patch_saved_view(
    view_id: int,
    data: SavedViewPatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.patch_saved_view(session, view_id, data, user)


@router.delete("/saved-views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_view(
    view_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    svc.delete_saved_view(session, view_id, user)


# ============================================================ dashboard + analytics
@router.get("/dashboard", response_model=TeamDashboardOut)
def team_dashboard(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.team_dashboard(session, user)


@router.get("/analytics", response_model=TeamAnalyticsOut)
def workload_analytics(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.workload_analytics(session, user)


# ============================================================ activity feed
@router.get("/feed", response_model=list[UnifiedTimelineEvent])
def activity_feed(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return svc.activity_feed(session, user, limit=limit, offset=offset)
