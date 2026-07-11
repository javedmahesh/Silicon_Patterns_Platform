"""Prevents overlapping scheduled 'tick' sweeps (SLA sweep, webhook retry sweep,
report-schedule sweep) from double-processing the same rows if two cron pokes overlap.

ponytail: in-process only (threading.Lock, non-blocking try-acquire) — the same
documented ceiling as this platform's other in-memory state (dashboard caches, the
rate limiter). A genuinely distributed multi-instance deployment needs a real
distributed lock (e.g. a Postgres advisory lock) instead; this closes the single-
process double-execution race without adding new infrastructure.
"""
from __future__ import annotations

import threading
from functools import wraps

from fastapi import HTTPException

_locks: dict[str, threading.Lock] = {}


def single_flight(name: str):
    """Decorator for a tick entry point: if `name`'s tick is already running in this
    process, the second concurrent caller gets HTTP 409 instead of overlapping work."""
    lock = _locks.setdefault(name, threading.Lock())

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not lock.acquire(blocking=False):
                raise HTTPException(409, f"{name} is already running — try again shortly")
            try:
                return fn(*args, **kwargs)
            finally:
                lock.release()
        return wrapper
    return decorator
