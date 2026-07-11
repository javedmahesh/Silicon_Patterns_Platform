"""Scheduler & run-history endpoints (Phase: Standard Scheduled Runs).

Reuses the existing auth (get_current_user / require_manager) and pagination
dependencies — no changes to authentication, RBAC, or the approval workflow.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend import scheduler_service as svc
from backend.dependencies import Pagination, get_session, pagination
from backend.schemas import ExecutionOut, Page, RunNowResult, SchedulerStatusOut
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


@router.post("/run-now", response_model=RunNowResult, summary="Trigger a Standard Run now (manager+)")
def run_now(
    request: Request,
    user: User = Depends(require_manager),
):
    result = svc.trigger_run_now(request.app)
    if result.status == "busy":
        raise HTTPException(status.HTTP_409_CONFLICT, result.detail)
    return result
