"""Persistence for the notification framework.

The ORM table itself lives in :mod:`master_db.models` (one metadata registry for the
whole platform, one migration stream) — this module re-exports it under the package's
own namespace and holds the read helpers that back the delivery-log queries, so
callers never reach across into ``master_db`` for notification concerns.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from master_db.models import NotificationDelivery

__all__ = ["NotificationDelivery", "deliveries_for_run", "delivery_status_counts", "recent_failures"]


def deliveries_for_run(session: Session, run_id: str) -> list[NotificationDelivery]:
    return list(session.scalars(
        select(NotificationDelivery)
        .where(NotificationDelivery.run_id == run_id)
        .order_by(NotificationDelivery.id)
    ))


def delivery_status_counts(session: Session, *, run_id: str | None = None) -> dict[str, int]:
    q = select(NotificationDelivery.status, func.count()).group_by(NotificationDelivery.status)
    if run_id is not None:
        q = q.where(NotificationDelivery.run_id == run_id)
    return {status: n for status, n in session.execute(q).all()}


def recent_failures(session: Session, *, limit: int = 20) -> list[NotificationDelivery]:
    """Most recent failed deliveries — what an operator checks after a silent run."""
    return list(session.scalars(
        select(NotificationDelivery)
        .where(NotificationDelivery.status == "failed")
        .order_by(NotificationDelivery.id.desc())
        .limit(limit)
    ))
