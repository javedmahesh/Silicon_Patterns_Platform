"""Platform notification framework.

    Scheduler → Notification Service → Provider → channel (SMTP/Gmail today)

The scheduler emits structured run information and nothing else: it never builds a
subject line, renders HTML, chooses recipients, or opens a socket. Adding Microsoft
Teams, Slack, a webhook, or in-app delivery is a new provider module plus a
``register()`` call — no scheduler change.

``send_run_notification`` is kept as the public entry point (the name
``backend/standard_run.py`` has always called) so this package is a drop-in
replacement for the Microsoft-Graph module it supersedes.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.config import Settings
from backend.notifications import providers, templates  # noqa: F401 - registers providers
from backend.notifications.models import (
    NotificationDelivery,
    deliveries_for_run,
    delivery_status_counts,
    recent_failures,
)
from backend.notifications.schemas import (
    Audience,
    DeliveryOutcome,
    HealthCheck,
    MetricGroup,
    Recipient,
    RunNotification,
    Severity,
    StageSummary,
)
from backend.notifications.service import (
    build_run_notification,
    notify_run_complete,
    resolve_recipients,
)
from master_db.models import PipelineExecution


def send_run_notification(
    session: Session, settings: Settings, execution: PipelineExecution, *, exception: str = "",
) -> tuple[str, str, int]:
    """Notify all approved active users that a run completed.

    Returns ``(notification_status, detail, notified_count)`` for the execution row.
    Never raises — a delivery problem is recorded, never propagated.
    """
    return notify_run_complete(session, settings, execution, exception=exception)


def build_summary_html(execution: PipelineExecution, *, settings: Settings | None = None) -> str:
    """Render the run-summary HTML without a database or a provider.

    Used by the notification preview endpoint and by tests. When ``settings`` is
    omitted the payload carries no branding overrides and no intelligence blocks —
    those need a session — so this is a pure formatting path over the execution row.
    """
    from backend.notifications.service import StageSummary as _S   # local: keeps import graph flat

    n = RunNotification(
        run_id=execution.run_id,
        status=execution.status,
        trigger=execution.trigger,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        duration_ms=execution.duration_ms or 0,
        records_processed=execution.records_processed or 0,
        scheduled_slot=execution.scheduled_slot,
        stages=[
            _S(
                component=str(s.get("component", "")), status=str(s.get("status", "")),
                processed=int(s.get("processed", 0) or 0), created=int(s.get("created", 0) or 0),
                updated=int(s.get("updated", 0) or 0), review=int(s.get("review", 0) or 0),
                duration_ms=int(s.get("duration_ms", 0) or 0),
                errors=list(s.get("errors", []) or []), notes=str(s.get("notes", "") or ""),
            )
            for s in (execution.stages or [])
        ],
        totals=dict(execution.totals or {}),
        frontend_url=(settings.frontend_url if settings else ""),
        brand_name=(settings.brand_name if settings else "Silicon Patterns"),
        logo_url=(settings.brand_logo_url if settings else ""),
    )
    return templates.render_html(n)


__all__ = [
    "Audience",
    "DeliveryOutcome",
    "HealthCheck",
    "MetricGroup",
    "NotificationDelivery",
    "Recipient",
    "RunNotification",
    "Severity",
    "StageSummary",
    "build_run_notification",
    "build_summary_html",
    "deliveries_for_run",
    "delivery_status_counts",
    "notify_run_complete",
    "providers",
    "recent_failures",
    "resolve_recipients",
    "send_run_notification",
    "templates",
]
