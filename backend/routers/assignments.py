from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend import services
from backend.dependencies import get_session
from backend.schemas import AssignmentCreate, AssignmentOut, AssignmentPatch, UserOut, WorkloadOut
from backend.security import get_current_user, require_manager
from master_db.models import User

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("", response_model=list[AssignmentOut], summary="All assignments (manager+)")
def list_all(
    user_id: int | None = Query(None), status: str | None = Query(None),
    session: Session = Depends(get_session), _: User = Depends(require_manager),
):
    return services.list_assignments(session, user_id=user_id, status=status)


@router.get("/mine", response_model=list[AssignmentOut], summary="The current user's assigned leads")
def list_mine(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return services.my_assignments(session, user.id)


@router.get("/workload", response_model=WorkloadOut,
            summary="Per-user workload + unassigned high-grade count (manager+)")
def workload(session: Session = Depends(get_session), _: User = Depends(require_manager)):
    return services.workload(session)


@router.get("/users", response_model=list[UserOut], summary="Assignable users (manager+)")
def assignable_users(session: Session = Depends(get_session), _: User = Depends(require_manager)):
    return services.list_users(session)


@router.post("", response_model=AssignmentOut, summary="Assign a lead to a user (manager+)")
def create(payload: AssignmentCreate, session: Session = Depends(get_session),
           actor: User = Depends(require_manager)):
    return services.create_assignment(session, payload, actor)


@router.patch("/{assignment_id}", response_model=AssignmentOut,
              summary="Update status/note (the assignee, or a manager+)")
def patch(assignment_id: int, payload: AssignmentPatch, session: Session = Depends(get_session),
          actor: User = Depends(get_current_user)):
    return services.patch_assignment(session, assignment_id, payload, actor)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Unassign a lead (manager+) — logs an audit event")
def unassign(assignment_id: int, session: Session = Depends(get_session),
             actor: User = Depends(require_manager)):
    services.unassign(session, assignment_id, actor)
