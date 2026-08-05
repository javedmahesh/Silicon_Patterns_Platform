"""The discovery source contract.

A source is a **data provider and nothing else**. It fetches raw records from one
place and hands back :class:`DiscoveryCandidate` objects. It must never:

* open a database session or write a row,
* decide whether a company is a duplicate,
* assign a final confidence score,
* resolve a company to the platform's ``company_domain``,
* filter on business rules (tier, prospect type, competitor exclusion).

All of that belongs to the Market Discovery Engine, which is the single source of
truth for discovery business logic. A source that reaches past this boundary breaks
the guarantee that every provider is treated identically.

Implementing one:

    class MySource(DiscoverySource):
        name = "my_source"

        def capabilities(self):
            return SourceCapabilities(name=self.name, provides=frozenset({"website"}))

        def fetch(self, context):
            yield {...}                     # raw provider records

        def normalize(self, raw, context):
            return DiscoveryCandidate(company_name=raw["name"], source=self.name)

Then register it (``backend/market_discovery/sources/__init__.py``) and enable it in
configuration. No engine, pipeline or scheduler change is required.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Iterable

from backend.market_discovery.schemas import (
    DiscoveryCandidate,
    DiscoveryContext,
    SourceCapabilities,
    SourceHealth,
    SourceStatus,
)

logger = logging.getLogger("market_discovery.source")


class DiscoverySource(ABC):
    """Base class every discovery source inherits.

    Subclasses implement :meth:`fetch` and :meth:`normalize`; :meth:`discover` is
    provided and composes them, so the common path (fetch → normalize → stamp
    provenance) is written once and behaves identically for every provider.
    """

    #: Stable identifier — used in configuration, provenance and the delivery log.
    name: str = ""

    # ------------------------------------------------------------------ contract
    @abstractmethod
    def capabilities(self) -> SourceCapabilities:
        """What this source can provide. Called by the registry, cached per run."""

    @abstractmethod
    def fetch(self, context: DiscoveryContext) -> Iterable[Any]:
        """Yield raw provider records. May be a generator — the engine bounds it."""

    @abstractmethod
    def normalize(self, raw: Any, context: DiscoveryContext) -> DiscoveryCandidate | None:
        """Map ONE raw record to a candidate. Return ``None`` to drop it.

        Field-shape mapping only. Dropping here is for records that aren't companies
        at all (a header row, an empty result); anything that *is* a company but looks
        weak must still be returned — judging it is the engine's job.
        """

    # ------------------------------------------------------------------ provided
    def validate(self) -> tuple[bool, str]:
        """Is this source configured well enough to run? ``(ok, reason_if_not)``.

        Default: usable when it needs no credentials. A source requiring an API key
        overrides this to check for it — and the registry will skip it rather than let
        the run fail.
        """
        caps = self.capabilities()
        if caps.requires_credentials:
            return False, f"{self.name}: credentials required but validate() not implemented"
        return True, ""

    def health(self) -> SourceHealth:
        """Liveness for the registry's health endpoint. Default derives from
        :meth:`validate` and performs no network I/O — override for a real probe."""
        ok, reason = self.validate()
        return SourceHealth(
            name=self.name,
            status=SourceStatus.OK if ok else SourceStatus.UNAVAILABLE,
            detail=reason,
        )

    def discover(self, context: DiscoveryContext) -> list[DiscoveryCandidate]:
        """Fetch + normalize into candidates, with provenance stamped.

        A record that fails to normalize is logged and skipped: one malformed row must
        not cost the whole source's output. Exceptions from :meth:`fetch` propagate —
        the engine records the source as failed and continues with the others.
        """
        out: list[DiscoveryCandidate] = []
        limit = context.limit
        for raw in self.fetch(context):
            if limit is not None and len(out) >= limit:
                logger.info("[discovery] %s: limit %d reached, stopping fetch", self.name, limit)
                break
            try:
                candidate = self.normalize(raw, context)
            except Exception:      # noqa: BLE001 - one bad record, not a failed source
                logger.warning("[discovery] %s: could not normalize a record (skipped)",
                               self.name, exc_info=True)
                continue
            if candidate is None:
                continue
            # Provenance is stamped here, not in the subclass, so it can never be
            # forgotten or faked.
            candidate.source = self.name
            candidate.first_seen = candidate.first_seen or context.now
            candidate.last_seen = context.now
            out.append(candidate)
        return out

    def __repr__(self) -> str:        # pragma: no cover - debugging aid
        return f"<{type(self).__name__} name={self.name!r}>"
