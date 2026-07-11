from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import services
from backend.dependencies import get_session
from backend.schemas import PipelineComponentHealth, PipelineRunOut, PipelineStatusOut

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get("/runs", response_model=list[PipelineRunOut], summary="Recent pipeline runs")
def runs(
    session: Session = Depends(get_session),
    limit: int = Query(20, ge=1, le=200, description="how many recent runs"),
):
    return services.pipeline_runs(session, limit)


@router.get("/health", response_model=list[PipelineComponentHealth], summary="Per-component freshness")
def health(session: Session = Depends(get_session)):
    return services.pipeline_health(session)


@router.get("/status", response_model=PipelineStatusOut, summary="Data freshness + latest run status")
def status(session: Session = Depends(get_session)):
    return services.pipeline_status(session)
