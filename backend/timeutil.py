"""Shared UTC datetime helpers.

Every service/repo module in backend/ independently defined its own `_utcnow()` /
`_utc()` — a deliberate no-shared-utils convention early in this codebase's growth, to
avoid coupling unrelated modules through a common import. At 20+ duplicate copies of a
two-line function that has never varied, the coupling risk that convention was avoiding
no longer outweighs the maintenance cost. This module is the single implementation;
each call site now imports it under its old local name (`_utcnow`/`_utc`) so no call
site itself needed to change.
"""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utc(dt: datetime | None) -> datetime | None:
    """Coerce a naive datetime (e.g. from SQLite, which drops tzinfo) to UTC-aware."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
