"""Rate limiter abstraction — a clean extension point for a distributed backend
(e.g. Redis INCR+EXPIRE) without requiring one now.

InMemoryRateLimiter is the default and reproduces exactly the fixed-window-per-key
counter that used to live inline in backend/main.py's middleware.
"""
from __future__ import annotations

import time
from typing import Protocol


class RateLimiter(Protocol):
    def check(self, key: str, *, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        """Returns (allowed, retry_after_seconds). retry_after_seconds is only meaningful
        when allowed is False."""
        ...


class InMemoryRateLimiter:
    """Fixed-window counter per key, per-process.

    ponytail: same ceiling as this platform's other in-memory state (dashboard caches) —
    behind >1 instance, each process enforces its own window, so the *effective* limit
    across a fleet is roughly (instance_count x limit). Upgrade path: a RateLimiter
    implementing the same .check() signature backed by a shared store — no caller
    changes needed (backend/main.py only calls .check()).
    """

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = {}

    def check(self, key: str, *, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        now = time.time()
        count, start = self._windows.get(key, [0.0, now])
        if now - start >= window_seconds:
            count, start = 0.0, now
        count += 1
        self._windows[key] = [count, start]
        if count > limit:
            return False, max(1, int(window_seconds - (now - start)))
        return True, 0

    def clear(self) -> None:
        self._windows.clear()
