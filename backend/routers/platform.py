"""Enterprise CRM Phase 13: Production Deployment, Authentication & Platform Hardening
endpoints. Manager-gated (internal operational detail), distinct from the public
liveness/readiness probes in routers/health.py."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend import platform_service as svc
from backend.dependencies import get_session
from backend.security import require_manager
from master_db.models import User

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/config/readiness", summary="Production configuration readiness (Phase 13)")
def production_readiness(request: Request, session: Session = Depends(get_session), _: User = Depends(require_manager)):
    return svc.production_readiness(request.app.state.settings, session)


@router.get("/health", summary="Operational health: app/db/scheduler/integrations/auth/cache")
def operational_health(request: Request, session: Session = Depends(get_session), user: User = Depends(require_manager)):
    return svc.operational_health(session, user, request.app.state.settings)


@router.get("/dashboard", summary="Production dashboard: status/sessions/auth/queues/integrations")
def production_dashboard(request: Request, session: Session = Depends(get_session), user: User = Depends(require_manager)):
    return svc.production_dashboard(session, user, request.app.state.settings)


@router.get("/validate", summary="Final platform validation — one reachability check per module")
def platform_validate(request: Request, session: Session = Depends(get_session), user: User = Depends(require_manager)):
    return svc.platform_validate(session, user, request.app.state.settings)
