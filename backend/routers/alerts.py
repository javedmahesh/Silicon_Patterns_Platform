"""Smart alerts (Phase 3) — cross-company relationship-intelligence alerts for the
Dashboard. Read-only; guarded by ``require_principal`` at registration."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import relationship_intelligence as reli
from backend.dependencies import get_session
from backend.schemas import AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut], summary="Cross-company smart alerts (Dashboard)")
def list_alerts(session: Session = Depends(get_session), limit: int = Query(25, ge=1, le=100)):
    return reli.smart_alerts(session, limit=limit)
