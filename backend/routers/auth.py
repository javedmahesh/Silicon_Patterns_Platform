from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend import services
from backend.dependencies import get_session
from backend.schemas import AuthResult, MicrosoftAuthBody, UserOut
from backend.security import get_current_user
from master_db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/microsoft", response_model=AuthResult, summary="Sign in with Microsoft Entra ID")
def microsoft(body: MicrosoftAuthBody, request: Request, session: Session = Depends(get_session)):
    return services.login_with_microsoft(session, body.id_token, request.app.state.settings)


@router.get("/me", response_model=UserOut, summary="Current signed-in user")
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.post("/refresh", response_model=AuthResult, summary="Refresh the session (issue a new app JWT)")
def refresh(request: Request, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return services.refresh_session(session, user, request.app.state.settings)


@router.post("/logout", summary="Sign out (audit-only — app JWTs are stateless)")
def logout(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return services.logout(session, user)
