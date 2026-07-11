from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.dependencies import get_session
from backend.schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut, summary="Liveness + DB connectivity")
def health(request: Request, session: Session = Depends(get_session)) -> HealthOut:
    settings = request.app.state.settings
    database = "ok"
    try:
        session.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - exercised only on a broken DB
        database = "error"
    return HealthOut(
        status="ok", app=settings.app_name, version=settings.app_version, database=database
    )


# --------------------------------------------------------------- Phase 13: k8s-style probes
# Deliberately unauthenticated (like /health above) — orchestrator probes can't carry
# app credentials. Kept intentionally trivial: liveness never touches the DB (a slow DB
# must not cause a pod restart loop), readiness does one connectivity check.
@router.get("/health/live", summary="Liveness probe — process is up")
def liveness() -> dict:
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness probe — DB reachable")
def readiness(response: Response, session: Session = Depends(get_session)) -> dict:
    try:
        session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception:  # pragma: no cover - exercised only on a broken DB
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "database": "error"}
