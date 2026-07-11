"""Health monitoring: per-component last success, failures, durations, next run."""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from master_db.models import PipelineRun
from orchestrator.stages import PIPELINE_ORDER

_SCHEDULES = Path(__file__).resolve().parent.parent / "config" / "schedules.json"
_CADENCE = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1), "manual": None}


def load_schedules() -> dict[str, str]:
    if _SCHEDULES.exists():
        data = json.loads(_SCHEDULES.read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if not k.startswith("_")}
    return {}


def component_health(session: Session, component: str, schedules: dict[str, str]) -> dict:
    last = session.scalar(
        select(PipelineRun).where(PipelineRun.component == component).order_by(PipelineRun.run_id.desc())
    )
    last_success = session.scalar(
        select(PipelineRun).where(PipelineRun.component == component, PipelineRun.status == "success")
        .order_by(PipelineRun.run_id.desc())
    )
    failed = session.scalar(
        select(func.count()).select_from(PipelineRun)
        .where(PipelineRun.component == component, PipelineRun.status == "failed")
    ) or 0
    avg_ms = session.scalar(
        select(func.avg(PipelineRun.duration_ms))
        .where(PipelineRun.component == component, PipelineRun.status == "success")
    )

    cadence = schedules.get(component, "manual")
    interval = _CADENCE.get(cadence)
    next_run = "on demand"
    if interval is not None:
        if last_success is not None:
            anchor = last_success.finished_at or last_success.started_at
            next_run = (anchor + interval).isoformat(timespec="seconds")
        else:
            next_run = "after first success"

    return {
        "component": component,
        "last_status": last.status if last else "never",
        "last_run": last.started_at.isoformat(timespec="seconds") if last and last.started_at else None,
        "last_success": last_success.finished_at.isoformat(timespec="seconds")
        if last_success and last_success.finished_at else None,
        "failed_runs": failed,
        "last_duration_ms": last.duration_ms if last else 0,
        "avg_duration_ms": round(avg_ms, 1) if avg_ms else 0.0,
        "cadence": cadence,
        "next_scheduled_run": next_run,
    }


def health_report(session: Session) -> list[dict]:
    schedules = load_schedules()
    return [component_health(session, c, schedules) for c in PIPELINE_ORDER]
