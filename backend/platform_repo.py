"""Data access for Enterprise CRM Phase 13: Production Deployment, Authentication &
Platform Hardening. Deliberately tiny — almost everything this phase needs already
exists in admin_repo/integration_repo/repositories; this module holds only the couple
of queries that don't."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from master_db.models import User


def count_recent_active_sessions(session: Session, *, minutes: int = 15) -> int:
    """Proxy for 'active sessions': active users seen in the last N minutes.

    ponytail: app JWTs are stateless (see backend.services.logout) — there is no real
    session table to count rows from. last_seen_at (touched on every authenticated
    request, throttled to once/5min) is the best available signal. Upgrade path: a real
    session/token store if concurrent-session limits or forced-logout become a requirement.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return session.scalar(
        select(func.count()).select_from(User).where(User.status == "active", User.last_seen_at >= cutoff)
    ) or 0
