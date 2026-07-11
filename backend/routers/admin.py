from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import services
from backend.dependencies import get_session
from backend.schemas import Page, UserAuditOut, UserOut, UserPatch
from backend.security import require_admin
from master_db.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=Page,
            summary="List/search/filter user accounts (admin)")
def list_users(
    session: Session = Depends(get_session), _: User = Depends(require_admin),
    status: str | None = Query(None, description="pending|active|disabled|rejected|deleted"),
    q: str | None = Query(None, description="search by email or name"),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    return services.list_users(session, status=status, q=q, limit=limit, offset=offset)


@router.get("/users/audit", response_model=list[UserAuditOut],
            summary="User-management audit trail (admin)")
def user_audit(session: Session = Depends(get_session), _: User = Depends(require_admin),
               user_id: int | None = Query(None), limit: int = Query(100, ge=1, le=500)):
    return services.list_user_audit(session, limit=limit, user_id=user_id)


@router.post("/users/{user_id}/approve", response_model=UserOut,
             summary="Approve a pending account (admin)")
def approve_user(user_id: int, session: Session = Depends(get_session),
                 actor: User = Depends(require_admin)):
    return services.approve_user(session, user_id, actor)


@router.post("/users/{user_id}/reject", response_model=UserOut,
             summary="Reject a pending account (admin)")
def reject_user(user_id: int, session: Session = Depends(get_session),
                actor: User = Depends(require_admin)):
    return services.reject_user(session, user_id, actor)


@router.patch("/users/{user_id}", response_model=UserOut,
              summary="Promote/demote role and/or enable/disable an account (admin)")
def update_user(user_id: int, patch: UserPatch, session: Session = Depends(get_session),
                actor: User = Depends(require_admin)):
    return services.update_user(session, user_id, patch, actor)


@router.delete("/users/{user_id}", response_model=UserOut,
               summary="Soft-delete an account — anonymize + retain for audit (admin)")
def delete_user(user_id: int, session: Session = Depends(get_session),
                actor: User = Depends(require_admin)):
    return services.delete_user(session, user_id, actor)
