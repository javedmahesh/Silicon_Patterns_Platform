"""Email scheduler — advances scheduled→queued, handles retries and deadline cancellations.

Designed to be called from a periodic job (e.g. a cron tick) or manually via the
``POST /outreach/scheduler/tick`` endpoint.  All mutations happen inside the caller's
session; the caller is responsible for committing.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from master_db.models import OutreachMessage

logger = logging.getLogger(__name__)

_RETRY_DELAYS_MINUTES = [5, 15, 60]

from backend.timeutil import utcnow as _utcnow


class EmailScheduler:
    """Stateless scheduler — every method is a pure transformation of DB rows."""

    @staticmethod
    def schedule_failure(msg: OutreachMessage) -> None:
        """Update msg after a send failure — schedules a retry or permanently fails it.

        Does NOT commit; caller owns the session.
        """
        msg.retry_count = (msg.retry_count or 0) + 1
        max_r = msg.max_retries if msg.max_retries is not None else 3
        if msg.retry_count >= max_r:
            msg.status = "failed"
            msg.retry_at = None
        else:
            delay = _RETRY_DELAYS_MINUTES[min(msg.retry_count - 1, len(_RETRY_DELAYS_MINUTES) - 1)]
            msg.retry_at = _utcnow() + timedelta(minutes=delay)
            msg.status = "queued"

    @staticmethod
    def process_scheduled(session: Session) -> int:
        """Advance messages whose scheduled_at has passed from 'scheduled' to 'queued'."""
        now = _utcnow()
        msgs = list(session.scalars(
            select(OutreachMessage)
            .where(OutreachMessage.status == "scheduled")
            .where(OutreachMessage.scheduled_at <= now)
        ))
        for msg in msgs:
            msg.status = "queued"
        return len(msgs)

    @staticmethod
    def cancel_overdue(session: Session) -> int:
        """Cancel scheduled/queued messages that have passed their cancel_at deadline."""
        now = _utcnow()
        msgs = list(session.scalars(
            select(OutreachMessage)
            .where(OutreachMessage.cancel_at.isnot(None))
            .where(OutreachMessage.cancel_at <= now)
            .where(OutreachMessage.status.in_(["scheduled", "queued"]))
        ))
        for msg in msgs:
            msg.status = "cancelled"
            msg.retry_at = None
        return len(msgs)

    @staticmethod
    def sync_gmail(session: Session) -> int:
        """Sync all connected Gmail accounts. Returns total messages ingested."""
        try:
            from backend.gmail_sync import sync_all_connected_accounts
            result = sync_all_connected_accounts(session)
            return result.get("ingested", 0)
        except Exception as exc:
            logger.warning("Gmail sync failed: %s", exc)
            return 0

    @staticmethod
    def refresh_gmail_tokens(session: Session) -> int:
        """Refresh near-expiry Gmail tokens. Returns count refreshed."""
        try:
            from backend.gmail_sync import refresh_expiring_tokens
            return refresh_expiring_tokens(session)
        except Exception as exc:
            logger.warning("Gmail token refresh failed: %s", exc)
            return 0

    @staticmethod
    def advance_sequences(session: Session) -> int:
        """Advance overdue sequence step executions. Returns count advanced."""
        try:
            from backend.campaign_service import advance_sequences
            return advance_sequences(session)
        except Exception as exc:
            logger.warning("Sequence advancement failed: %s", exc)
            return 0

    @staticmethod
    def tick(session: Session) -> dict[str, int]:
        """One scheduler cycle. Caller must commit after this returns."""
        cancelled = EmailScheduler.cancel_overdue(session)
        scheduled = EmailScheduler.process_scheduled(session)
        gmail_synced = EmailScheduler.sync_gmail(session)
        tokens_refreshed = EmailScheduler.refresh_gmail_tokens(session)
        sequences_advanced = EmailScheduler.advance_sequences(session)
        return {
            "scheduled_to_queued": scheduled,
            "cancelled_by_deadline": cancelled,
            "gmail_synced": gmail_synced,
            "gmail_tokens_refreshed": tokens_refreshed,
            "sequences_advanced": sequences_advanced,
        }
