from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import services
from backend.dependencies import Pagination, get_session, pagination
from backend.schemas import DemandSignalOut, Page

router = APIRouter(prefix="/demand-signals", tags=["demand-signals"])


@router.get("", response_model=Page[DemandSignalOut], summary="List/filter demand signals")
def list_demand_signals(
    session: Session = Depends(get_session),
    page: Pagination = Depends(pagination),
    min_demand_score: float | None = Query(None, description="demand_score >= this value"),
    technology_focus: str | None = Query(None, description="Match technologies_detected / primary_focus"),
):
    return services.list_demand_signals(
        session, pagination=page, min_demand_score=min_demand_score, technology_focus=technology_focus
    )
