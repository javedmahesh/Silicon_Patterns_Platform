"""NVIDIA Inception discovery source.

A data source and nothing more: it enumerates NVIDIA's public case studies through
the platform's crawl service, parses the server-rendered pages, and returns
:class:`DiscoveryCandidate` objects. Whether a candidate is a duplicate, confident,
or worth storing belongs entirely to the Market Discovery Engine.

It never calls a crawl provider directly — everything goes through
:class:`~backend.crawling.service.CrawlService`, so caching, rate limiting, retries
and provider selection stay the platform's.

Enumeration prefers the **locale sitemap**: static XML, complete in one request, and
the method a site publishes specifically for crawlers. Public index pages are a
secondary source for whatever they render server-side. ``?page=`` pagination is
never used — ``www.nvidia.com/robots.txt`` disallows it, and the sitemap makes it
unnecessary. Every URL is checked against
:func:`~backend.market_discovery.sources.nvidia_inception.config.robots_allows`
before it is requested.

Only public information is used: no sign-in, no gated resources, no paid endpoints.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Iterable

from backend.crawling.schemas import CrawlOptions, CrawlResult
from backend.market_discovery.crawling import CrawlingDiscoverySource
from backend.market_discovery.normalize import candidate_key, normalize_candidate
from backend.market_discovery.schemas import (
    DiscoveryCandidate,
    DiscoveryContext,
    SourceCapabilities,
)
from backend.market_discovery.sources.nvidia_inception import parser
from backend.market_discovery.sources.nvidia_inception.config import (
    NvidiaInceptionConfig,
    robots_allows,
)

logger = logging.getLogger("market_discovery.nvidia_inception")

#: Upper bound on URLs read from one sitemap. nvidia.com's locale sitemap carries a
#: few thousand entries, of which ~200 are case studies; this only guards against a
#: pathologically large index, never against normal operation.
_SITEMAP_URL_CEILING = 20_000


class NvidiaInceptionSource(CrawlingDiscoverySource):
    """Discovers companies from NVIDIA's public Inception / customer-story pages."""

    name = "nvidia_inception"

    def __init__(self, *, config: NvidiaInceptionConfig | None = None, crawl_service=None,
                 settings=None) -> None:
        super().__init__(crawl_service=crawl_service, settings=settings)
        self._config = config

    @property
    def config(self) -> NvidiaInceptionConfig:
        if self._config is None:
            from backend.config import get_settings

            self._config = NvidiaInceptionConfig.from_settings(
                self._settings if self._settings is not None else get_settings())
        return self._config

    # ------------------------------------------------------------------ contract
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            name=self.name,
            provides=frozenset({
                "company_name", "website", "description", "technologies", "headquarters",
                "country",
            }),
            supports_incremental=True,
            supports_pagination=True,
            requires_credentials=False,
            description="Public NVIDIA Inception / customer-story pages on nvidia.com",
        )

    # ------------------------------------------------------------------ fetch
    def fetch(self, context: DiscoveryContext) -> Iterable[dict[str, Any]]:
        """Enumerate case studies, then optionally fetch each one for detail.

        Never raises for a page-level problem: a missing page, a layout change or a
        crawl failure is logged and skipped, so one bad URL cannot cost the run its
        other companies.
        """
        config = self.config
        started = time.monotonic()
        budget = self._budget(context)
        logger.info(
            "[nvidia_inception] started run=%s sitemap=%s indexes<=%d companies<=%d "
            "incremental=%s",
            context.run_id or "-", config.use_sitemap, config.max_pages, budget,
            config.incremental,
        )

        urls: list[str] = []
        pages_crawled = 0

        if config.use_sitemap:
            found, crawled = self._from_sitemap(context)
            urls.extend(found)
            pages_crawled += crawled

        if len(urls) < budget:
            found, crawled = self._from_indexes(context, exclude=set(urls))
            urls.extend(found)
            pages_crawled += crawled

        records: list[dict[str, Any]] = []
        skipped_known = 0
        for url in urls:
            if len(records) >= budget:
                break
            slug = parser.case_study_slug(url)
            if not slug:
                continue
            entry = {"slug": slug, "source_url": url}
            if config.incremental and self._is_known(entry, context):
                skipped_known += 1
                continue
            records.append(entry)

        detailed, detail_pages, failed = (
            self._enrich(records, context) if config.fetch_company_pages else (records, 0, 0))
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "[nvidia_inception] completed run=%s pages_crawled=%d companies=%d "
            "skipped_known=%d failed_pages=%d in %dms",
            context.run_id or "-", pages_crawled + detail_pages, len(detailed),
            skipped_known, failed, duration_ms,
        )
        return detailed

    # ------------------------------------------------------------------ sources
    def _from_sitemap(self, context: DiscoveryContext) -> tuple[list[str], int]:
        """Case-study URLs from the locale sitemap — one request for the whole set."""
        url = self.config.sitemap_url
        if not robots_allows(url):
            logger.warning("[nvidia_inception] sitemap %s is disallowed by robots.txt", url)
            return [], 0
        try:
            found = self.crawl.sitemap_urls(url, self._sitemap_options())
        except Exception:      # noqa: BLE001 - the service already contains failures
            logger.warning("[nvidia_inception] sitemap %s unavailable", url, exc_info=True)
            return [], 1
        urls = [u for u in parser.filter_case_study_urls(found, base_url=self.config.base_url)
                if robots_allows(u)]
        logger.info("[nvidia_inception] sitemap yielded %d case study url(s) from %d entries",
                    len(urls), len(found))
        return urls, 1

    def _from_indexes(self, context: DiscoveryContext,
                      *, exclude: set[str]) -> tuple[list[str], int]:
        """Case-study links rendered server-side on the public index pages.

        Secondary to the sitemap: these pages load most of their listing client-side,
        so they contribute whatever is in the static HTML and nothing more. That is a
        supplement, not a failure.
        """
        out: list[str] = []
        crawled = 0
        for path in self.config.index_paths[: max(1, self.config.max_pages)]:
            url = self.config.index_url(path)
            if not robots_allows(url):
                logger.warning("[nvidia_inception] index %s is disallowed by robots.txt", url)
                continue
            result = self._crawl_page(url, context)
            crawled += 1
            if result is None:
                continue
            for entry in parser.parse_index_page(result.page):
                link = entry.get("source_url", "")
                if link and link not in exclude and link not in out and robots_allows(link):
                    out.append(link)
        if out:
            logger.info("[nvidia_inception] index pages yielded %d additional url(s)", len(out))
        return out, crawled

    def _enrich(self, records: list[dict[str, Any]],
                context: DiscoveryContext) -> tuple[list[dict[str, Any]], int, int]:
        """Fetch each case study and merge in what the page publishes.

        A page that fails or parses to nothing keeps its enumeration-level record —
        a thin candidate is still real, and the engine scores it accordingly.
        """
        out: list[dict[str, Any]] = []
        crawled = failed = 0
        for record in records:
            url = record.get("source_url", "")
            if not url:
                out.append(record)
                continue
            result = self._crawl_page(url, context)
            crawled += 1
            if result is None or result.page is None:
                failed += 1
                out.append(record)
                continue
            parsed = parser.parse_case_study(result.page)
            if not parsed:
                # A layout change shows up here: the page loaded but published nothing
                # recognizable. Kept as a thin record so the run degrades, not breaks.
                logger.info("[nvidia_inception] %s parsed to no fields (layout change?)", url)
                out.append(record)
                continue
            out.append({**record, **parsed})
        return out, crawled, failed

    # ------------------------------------------------------------------ helpers
    def _budget(self, context: DiscoveryContext) -> int:
        """The smaller of the connector's own cap and the engine's per-source limit."""
        limits = [self.config.max_companies]
        if context.limit is not None:
            limits.append(context.limit)
        return max(1, min(limits))

    def _is_known(self, entry: dict[str, Any], context: DiscoveryContext) -> bool:
        """Has the platform already stored this case study?

        Checked on the NVIDIA slug — the identity available at enumeration time, and
        what a previous run stored as ``source_id``. The engine supplies the index;
        the connector never runs a database query.
        """
        slug = entry.get("slug", "")
        if slug and context.already_seen(self.name, slug):
            return True
        if not context.known_candidate_keys:
            return False
        probe = normalize_candidate(DiscoveryCandidate(
            company_name=entry.get("company_name", "") or slug,
            website=entry.get("website", ""),
            source=self.name,
        ))
        return context.already_known(probe.candidate_key or candidate_key(probe))

    def _sitemap_options(self) -> CrawlOptions:
        """Options for the one sitemap request.

        ``max_pages`` bounds how many URLs a provider returns from a sitemap, which is
        a different quantity from how many pages this connector then fetches. Left
        generous so the whole index is seen; the company budget is applied afterwards,
        once non-case-study URLs have been filtered out.
        """
        options = self._options()
        options.max_pages = _SITEMAP_URL_CEILING
        return options

    def _options(self) -> CrawlOptions:
        return CrawlOptions(
            max_depth=self.config.crawl_depth,
            max_pages=max(1, self.config.max_companies),
            include_markdown=True,
            # These pages are server-rendered, so rendering is not required. Asking
            # for it anyway would push provider selection at a paid JS renderer for
            # no benefit.
            render_javascript=False,
            timeout_seconds=self.config.request_timeout_seconds,
            extra=dict(self.config.extra),
        )

    def _crawl_page(self, url: str, context: DiscoveryContext) -> CrawlResult | None:
        """One page via the crawl service. ``None`` when it could not be retrieved."""
        if not robots_allows(url):
            logger.warning("[nvidia_inception] refusing %s — disallowed by robots.txt", url)
            return None
        try:
            result = self.crawl.fetch_page(url, self._options())
        except Exception:      # noqa: BLE001
            logger.warning("[nvidia_inception] crawl raised for %s", url, exc_info=True)
            return None
        if not result.ok or result.page is None:
            logger.info("[nvidia_inception] %s unavailable: %s",
                        url, result.error or result.status.value)
            return None
        return result

    # ------------------------------------------------------------------ normalize
    def normalize(self, raw: Any, context: DiscoveryContext) -> DiscoveryCandidate | None:
        """One raw record → a discovery candidate.

        Field-shape mapping only. Nothing is inferred or defaulted: a value NVIDIA did
        not publish stays empty, because a fabricated one would reach the engine's
        confidence model as if it were evidence.
        """
        if not isinstance(raw, dict):
            return None
        name = str(raw.get("company_name") or "").strip()
        slug = str(raw.get("slug") or "").strip()
        if not name and not slug:
            return None

        technologies = tuple(str(t).strip() for t in (raw.get("technologies") or ())
                             if str(t).strip())
        metadata: dict[str, Any] = {}
        headline = str(raw.get("headline") or "").strip()
        if headline:
            metadata["headline"] = headline
        # Inception membership is the reason this source exists; record it as context
        # for a human reviewing the candidate, not as a scored field.
        metadata["programme"] = "NVIDIA Inception / customer story"
        if raw.get("name_uncertain"):
            # NVIDIA published a headline rather than a company name for this study.
            # Surfaced so a reviewer can see the name is weak; never silently hidden.
            metadata["name_uncertain"] = True

        return DiscoveryCandidate(
            company_name=name or slug.replace("-", " ").strip(),
            website=str(raw.get("website") or "").strip(),
            description=str(raw.get("description") or "").strip(),
            industry=str(raw.get("industry") or "").strip(),
            headquarters=str(raw.get("headquarters") or "").strip(),
            country=str(raw.get("country") or "").strip(),
            technologies=technologies[:10],
            source_id=slug,
            source_url=str(raw.get("source_url") or "").strip(),
            raw_payload=dict(raw),
            metadata=metadata,
        )
