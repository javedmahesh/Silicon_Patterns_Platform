"""Tiny in-process response cache + ETag helpers for the analytics endpoints.

The master DB only changes when a scheduled refresh completes (twice daily), so
analytics responses are safe to reuse until the *last successful refresh* advances.
Both the server-side memo and the client ETag are keyed on that timestamp:

- Between refreshes, a repeated request is served from memory (no re-aggregation),
  and a conditional request (``If-None-Match``) gets a cheap **304 Not Modified**.
- When a new refresh finishes, ``last_successful_refresh`` advances, the key
  changes, the old memo entry is ignored, and every client revalidates to fresh data.

Scope: per-process, best-effort. No lock (last write wins with identical data);
behind multiple API instances each keeps its own copy — fine for a read cache. The
store holds one entry per cached endpoint (latest version only), so it stays tiny.
Cleared between tests via the autouse fixture in ``tests/conftest.py``.

Storage is delegated to a CacheBackend (backend.cache_backend) — an InMemoryCacheBackend
by default — so a distributed backend can be swapped in later without touching this
module's public API (refresh_version/etag_for/not_modified/memoize/clear/size).
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import TypeVar

from fastapi import Request
from sqlalchemy.orm import Session

from backend import repositories as repo
from backend.cache_backend import CacheBackend, InMemoryCacheBackend

T = TypeVar("T")

# Sentinel version used before any refresh has succeeded. We never memoize it: an
# empty DB and a freshly-loaded DB would otherwise share this one ambiguous key.
_COLD = "cold"

# Values stored are (version, value) tuples; only the latest version per key is retained.
_backend: CacheBackend = InMemoryCacheBackend()


def refresh_version(session: Session) -> str:
    """A token identifying the current data: the latest of the last successful refresh
    (ingestion) and the last scoring run, so a direct re-score also advances the version
    and invalidates cached analytics — not only an orchestrator-tracked refresh."""
    stamps = [t for t in (repo.last_successful_refresh(session), repo.last_scored_at(session))
              if t is not None]
    return max(stamps).isoformat() if stamps else _COLD


def etag_for(key: str, version: str) -> str:
    """A weak ETag for (endpoint, data-version). Changes iff the data changes."""
    digest = hashlib.sha1(f"{key}@{version}".encode()).hexdigest()[:16]
    return f'W/"{digest}"'


def _normalize(tag: str) -> str:
    tag = tag.strip()
    return tag[2:] if tag.startswith("W/") else tag


def not_modified(request: Request, etag: str) -> bool:
    """True when the client's ``If-None-Match`` already holds this ETag (-> 304)."""
    header = request.headers.get("if-none-match")
    if not header:
        return False
    wanted = _normalize(etag)
    return any(_normalize(part) == wanted for part in header.split(","))


def memoize(key: str, version: str, build: Callable[[], T]) -> T:
    """Return the cached value for (key, version), computing + storing it on a miss."""
    if version == _COLD:
        return build()  # ambiguous key — always recompute, never share
    hit = _backend.get(key)
    if hit is not None and hit[0] == version:
        return hit[1]  # type: ignore[return-value]
    value = build()
    _backend.set(key, (version, value))
    return value


def clear() -> None:
    """Drop all cached entries (used by tests for isolation)."""
    _backend.clear()


def size() -> int:
    """Entry count — surfaced on the Phase 13 operational-health/cache-health check."""
    return _backend.size()
