"""Cache storage abstraction — a clean extension point for a distributed backend
(Redis/Memcached/etc) without requiring one now.

InMemoryCacheBackend is the default and is what backend/cache.py (the shared analytics
response cache) is built on. The per-service dashboard caches added in later phases
(admin_service._dash_cache, bi_service._dash_cache, integration_service._dash_cache,
revops_service._dash_cache, workflow_service._def_cache) are the same pattern — a plain
dict behind a TTL check — and can adopt this same CacheBackend interface if/when a
distributed cache is actually needed; they were left as-is here to avoid an unrelated,
wide-blast-radius refactor across five files for a need that doesn't exist yet.

ponytail: single-process ceiling (ties to the process it runs in — that's the whole
point of documenting the extension point rather than needing it today). A distributed
implementation just needs to satisfy the same three methods.
"""
from __future__ import annotations

from typing import Protocol


class CacheBackend(Protocol):
    def get(self, key: str) -> object | None: ...
    def set(self, key: str, value: object) -> None: ...
    def clear(self) -> None: ...
    def size(self) -> int: ...


class InMemoryCacheBackend:
    """Plain dict, per-process. The default backend everywhere in this codebase today."""

    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    def get(self, key: str) -> object | None:
        return self._store.get(key)

    def set(self, key: str, value: object) -> None:
        self._store[key] = value

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)
