"""Crawling support for discovery sources.

The bridge between two layers that must not know each other's internals: the
crawling infrastructure (:mod:`backend.crawling`) retrieves content, the Market
Discovery Engine decides what it means. This module gives a connector a crawler
without letting the crawler learn anything about discovery.

A connector inherits :class:`CrawlingDiscoverySource` instead of
:class:`~backend.market_discovery.base_source.DiscoverySource` and gets ``self.crawl``
— a :class:`~backend.crawling.service.CrawlService`. Everything else is unchanged: it
still only returns candidates, still cannot reach a database, and is still processed
by the same pipeline as every other source.

    class WellfoundSource(CrawlingDiscoverySource):
        name = "wellfound"

        def capabilities(self):
            return SourceCapabilities(name=self.name, provides=frozenset({"website"}))

        def fetch(self, context):
            result = self.crawl.fetch_page("https://wellfound.com/startups")
            if result.ok:
                yield from self.parse(result.page)

        def normalize(self, raw, context):
            return DiscoveryCandidate(company_name=raw["name"], website=raw["site"])

No production connector is registered — this is the plumbing the next phases use.
"""
from __future__ import annotations

import logging

from backend.market_discovery.base_source import DiscoverySource
from backend.market_discovery.schemas import SourceHealth, SourceStatus

logger = logging.getLogger("market_discovery.crawling")


class CrawlingDiscoverySource(DiscoverySource):
    """A discovery source that retrieves its data by crawling the web.

    The crawl service is injected (or lazily built from settings), never constructed
    per request — that way one rate limiter and one cache are shared across every
    connector in a run, so ten sources hitting the same host still respect one
    per-host budget.
    """

    def __init__(self, *, crawl_service=None, settings=None) -> None:
        self._crawl_service = crawl_service
        self._settings = settings

    @property
    def crawl(self):
        """The shared :class:`CrawlService`. Built on first use."""
        if self._crawl_service is None:
            from backend.config import get_settings
            from backend.crawling import CrawlService, register_default_providers

            settings = self._settings if self._settings is not None else get_settings()
            register_default_providers(settings)
            self._crawl_service = CrawlService.from_settings(settings)
        return self._crawl_service

    # ------------------------------------------------------------------ health
    def validate(self) -> tuple[bool, str]:
        """A crawling source is runnable when some crawl provider is usable.

        Reported as a source-level problem rather than raising mid-run, so a missing
        provider credential skips this connector and lets the others proceed.
        """
        try:
            provider = self.crawl.select_provider()
        except Exception as exc:      # noqa: BLE001
            return False, f"no usable crawl provider: {exc}"
        return True, f"using crawl provider {provider.name}"

    def health(self) -> SourceHealth:
        ok, detail = self.validate()
        return SourceHealth(
            name=self.name,
            status=SourceStatus.OK if ok else SourceStatus.UNAVAILABLE,
            detail=detail,
        )
