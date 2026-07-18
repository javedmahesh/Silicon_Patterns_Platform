"""Scheduler & run-history endpoints (Phase: Standard Scheduled Runs).

Reuses the existing auth (get_current_user / require_manager) and pagination
dependencies — no changes to authentication, RBAC, or the approval workflow.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend import run_records, scheduler_service as svc
from backend.dependencies import Pagination, get_session, pagination
from backend.schemas import (
    ExecutionOut,
    Page,
    RunEngineRecordsOut,
    RunNowResult,
    SchedulerConfigIn,
    SchedulerStatusOut,
)
from backend.security import get_current_user, require_manager
from master_db.models import User

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("/status", response_model=SchedulerStatusOut, summary="Scheduler status + next run + last run")
def get_status(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    scheduler = getattr(request.app.state, "scheduler", None)
    return svc.scheduler_status(session, request.app.state.settings, scheduler)


@router.put("/config", response_model=SchedulerStatusOut,
            summary="Update the Standard Run schedule — times / enabled / grace (manager+)")
def update_config(
    body: SchedulerConfigIn,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(require_manager),
):
    try:
        svc.update_scheduler_config(session, request.app.state.settings, payload=body, actor=user)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    scheduler = getattr(request.app.state, "scheduler", None)
    return svc.scheduler_status(session, request.app.state.settings, scheduler)


@router.get("/runs", response_model=Page[ExecutionOut], summary="Run history (most recent first)")
def list_runs(
    session: Session = Depends(get_session),
    page: Pagination = Depends(pagination),
    user: User = Depends(get_current_user),
):
    return svc.list_executions(session, page)


@router.get("/runs/{run_id}", response_model=ExecutionOut, summary="One run's full detail")
def get_run(
    run_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    out = svc.get_execution(session, run_id)
    if out is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "run not found")
    return out


@router.get("/runs/{run_id}/engines/{engine}/records", response_model=RunEngineRecordsOut,
            summary="Records a specific engine touched during a specific run (drill-down, paginated)")
def get_run_engine_records(
    run_id: str,
    engine: str,
    session: Session = Depends(get_session),
    page: Pagination = Depends(pagination),
    user: User = Depends(get_current_user),
):
    """Exactly the records THIS run's *engine* processed — created/updated/derived/…,
    joined to their canonical rows for display. Loaded on demand (not in the run list),
    strictly isolated to *run_id*. Returns ``available=False`` for historical runs with
    no per-record provenance."""
    if svc.get_execution(session, run_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "run not found")
    return run_records.engine_records(session, run_id, engine, limit=page.limit, offset=page.offset)


@router.post("/run-now", response_model=RunNowResult, summary="Trigger a Standard Run now (manager+)")
def run_now(
    request: Request,
    user: User = Depends(require_manager),
):
    result = svc.trigger_run_now(request.app)
    if result.status == "busy":
        raise HTTPException(status.HTTP_409_CONFLICT, result.detail)
    return result
