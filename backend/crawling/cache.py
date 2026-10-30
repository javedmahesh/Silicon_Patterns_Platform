"""Provider-agnostic crawl cache.

Crawling is the expensive part of every engine that uses it — network latency, API
cost, and politeness budget against the target site. Caching identical requests is
what makes a re-run cheap and what keeps a retry from re-billing.

The cache is keyed on the *request*, not the provider, so switching providers does
not silently serve content produced by the old one: the provider name is part of the
key. It stores :class:`CrawlResult` objects verbatim.

:class:`CrawlCache` is a Protocol, so a Redis or database-backed cache drops in
without touching a caller. The default is in-process, which matches the platform's
other caches (dashboard, config) and their known ceiling: behind >1 instance each
process keeps its own, so the effective hit rate is lower but never wrong.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import replace
from typing import Protocol, runtime_checkable

from backend.crawling.schemas import CrawlOptions, CrawlResult

logger = logging.getLogger("crawling.cache")


def cache_key(url: str, mode: str, provider: str, options: CrawlOptions | None = None) -> str:
    """Deterministic key for one crawl request.

    Only the options that change the *content* participate: depth, page budget,
    rendering, body formats and path filters. ``bypass_cache`` and
    ``timeout_seconds`` are excluded — they change how the request is made, not what
    comes back, and including them would fragment the cache pointlessly.
    """
    o = options or CrawlOptions()
    payload = {
        "url": (url or "").strip().lower(),
        "mode": mode,
        "provider": provider,
        "depth": o.max_depth,
        "pages": o.max_pages,
        "html": o.include_html,
        "markdown": o.include_markdown,
        "js": o.render_javascript,
        "only": sorted(o.only_paths),
        "exclude": sorted(o.exclude_paths),
        "extra": {k: o.extra[k] for k in sorted(o.extra)} if o.extra else {},
    }
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


@runtime_checkable
class CrawlCache(Protocol):
    """Swap in Redis/DB by implementing these four methods."""

    def get(self, key: str) -> CrawlResult | None: ...

    def set(self, key: str, result: CrawlResult, *, ttl_seconds: int) -> None: ...

    def invalidate(self, key: str) -> bool: ...

    def clear(self) -> int: ...


class InMemoryCrawlCache:
    """TTL cache with a bounded size, safe for concurrent crawlers.

    Eviction is oldest-first once ``max_entries`` is reached. Crawl results are large
    (a page's markdown plus optionally its HTML), so an unbounded cache is a memory
    leak in a long-running process, not a performance win.
    """

    def __init__(self, *, max_entries: int = 512) -> None:
        self._entries: dict[str, tuple[float, CrawlResult]] = {}
        self._lock = threading.Lock()
        self._max_entries = max(1, max_entries)
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> CrawlResult | None:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self.misses += 1
                return None
            expires_at, result = entry
            if expires_at <= now:
                del self._entries[key]
                self.misses += 1
                logger.debug("[crawl] cache entry expired key=%s", key)
                return None
            self.hits += 1
        # Flagged as a hit for the caller's logs/metrics without mutating the stored
        # copy, which other callers may still be reading.
        return replace(result, from_cache=True)

    def set(self, key: str, result: CrawlResult, *, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return          # caching disabled
        with self._lock:
            if len(self._entries) >= self._max_entries and key not in self._entries:
                oldest = min(self._entries, key=lambda k: self._entries[k][0])
                del self._entries[oldest]
            self._entries[key] = (time.monotonic() + ttl_seconds, result)

    def invalidate(self, key: str) -> bool:
        with self._lock:
            return self._entries.pop(key, None) is not None

    def clear(self) -> int:
        with self._lock:
            n = len(self._entries)
            self._entries.clear()
            return n

    def stats(self) -> dict[str, int | float]:
        total = self.hits + self.misses
        with self._lock:
            size = len(self._entries)
        return {
            "entries": size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 4) if total else 0.0,
        }

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


class NullCrawlCache:
    """Caches nothing. For tests, and for callers that must always see live content."""

    def get(self, key: str) -> CrawlResult | None:
        return None

    def set(self, key: str, result: CrawlResult, *, ttl_seconds: int) -> None:
        return None

    def invalidate(self, key: str) -> bool:
        return False

    def clear(self) -> int:
        return 0

    def stats(self) -> dict[str, int | float]:
        return {"entries": 0, "hits": 0, "misses": 0, "hit_rate": 0.0}
