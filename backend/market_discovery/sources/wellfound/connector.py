"""Wellfound discovery source.

A data source and nothing more: it walks Wellfound's public startup listings through
the platform's crawl service, parses public company pages, and returns
:class:`DiscoveryCandidate` objects. Every decision about what those candidates mean
— duplicate or not, confident or not, worth storing or not — belongs to the Market
Discovery Engine.

It never calls Firecrawl (or any provider) directly. All retrieval goes through
:class:`~backend.crawling.service.CrawlService`, so caching, rate limiting, retries
and provider selection are the platform's, not this connector's.

Only public information is used. No sign-in, no paid endpoints, and no attempt to
work around bot protection: when Wellfound answers with a challenge page, the
connector reports that as a clear source failure rather than evading it.
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
    SourceHealth,
    SourceStatus,
)
from backend.market_discovery.sources.wellfound import parser
from backend.market_discovery.sources.wellfound.config import WellfoundConfig

logger = logging.getLogger("market_discovery.wellfound")


class BlockedByProvider(RuntimeError):
    """Wellfound served a bot-protection challenge instead of content.

    Raised so the pipeline records this source as failed with an actionable reason.
    Deliberately not handled by retrying or by disguising the request: working around
    bot detection is not something this platform does.
    """


class WellfoundSource(CrawlingDiscoverySource):
    """Discovers companies from Wellfound's public startup listings."""

    name = "wellfound"

    def __init__(self, *, config: WellfoundConfig | None = None, crawl_service=None,
                 settings=None) -> None:
        super().__init__(crawl_service=crawl_service, settings=settings)
        self._config = config

    @property
    def config(self) -> WellfoundConfig:
        if self._config is None:
            from backend.config import get_settings

            self._config = WellfoundConfig.from_settings(
                self._settings if self._settings is not None else get_settings())
        return self._config

    # ------------------------------------------------------------------ contract
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            name=self.name,
            provides=frozenset({
                "company_name", "website", "linkedin_url", "description", "headquarters",
                "country", "employee_count", "funding_stage", "founded_year", "industry",
            }),
            supports_incremental=True,
            supports_pagination=True,
            requires_credentials=False,
            description="Public startup listings and company pages on wellfound.com",
        )

    def validate(self) -> tuple[bool, str]:
        """Runnable when a crawl provider is available.

        Wellfound serves its company pages only to JavaScript-capable clients behind
        bot protection, so a plain-HTTP provider will be challenged. That is surfaced
        as a warning here rather than a hard stop: the run should attempt the fetch
        and report what actually happened, not guess in advance.
        """
        ok, reason = super().validate()
        if not ok:
            return False, reason
        try:
            provider = self.crawl.select_provider(CrawlOptions(render_javascript=True))
        except Exception as exc:      # noqa: BLE001
            return False, f"no usable crawl provider: {exc}"
        if not provider.capabilities().renders_javascript:
            return True, (f"using {provider.name}, which cannot render JavaScript — "
                          f"wellfound.com is likely to answer with a bot challenge")
        return True, f"using crawl provider {provider.name}"

    def health(self) -> SourceHealth:
        ok, detail = self.validate()
        degraded = ok and "bot challenge" in detail
        return SourceHealth(
            name=self.name,
            status=(SourceStatus.DEGRADED if degraded
                    else SourceStatus.OK if ok else SourceStatus.UNAVAILABLE),
            detail=detail,
        )

    # ------------------------------------------------------------------ fetch
    def fetch(self, context: DiscoveryContext) -> Iterable[dict[str, Any]]:
        """Walk the listings, then optionally each company page.

        Yields raw records; :meth:`normalize` maps them onto the discovery schema.
        Raises :class:`BlockedByProvider` when Wellfound challenges the crawler —
        the pipeline records a failed source and continues with the others.
        """
        config = self.config
        started = time.monotonic()
        budget = self._budget(context)
        logger.info("[wellfound] started run=%s pages<=%d companies<=%d incremental=%s",
                    context.run_id or "-", config.max_pages, budget, config.incremental)

        records: list[dict[str, Any]] = []
        seen_slugs: set[str] = set()
        pages_crawled = 0
        skipped_known = 0
        blocked_pages = 0

        for path in config.listing_paths:
            if len(records) >= budget:
                break
            for page_number in range(1, config.max_pages + 1):
                if len(records) >= budget:
                    break
                url = config.listing_url(path, page_number)
                result = self._crawl_page(url, context)
                pages_crawled += 1
                if result is None:
                    break                      # listing unavailable; try the next path
                if parser.looks_blocked(result.page):
                    blocked_pages += 1
                    logger.warning("[wellfound] listing %s returned a bot challenge", url)
                    break
                entries = parser.parse_listing_page(result.page)
                if not entries:
                    # A listing with no company links is the natural end of pagination.
                    logger.info("[wellfound] no companies on %s — stopping this path", url)
                    break
                for entry in entries:
                    slug = entry.get("slug", "")
                    if not slug or slug in seen_slugs:
                        continue
                    seen_slugs.add(slug)
                    if config.incremental and self._is_known(entry, context):
                        skipped_known += 1
                        continue
                    records.append(entry)
                    if len(records) >= budget:
                        break

        if blocked_pages and not records:
            raise BlockedByProvider(
                f"wellfound.com served a bot-protection challenge on {blocked_pages} listing "
                f"page(s); no public company data could be retrieved. This needs a crawl "
                f"provider that renders JavaScript and that Wellfound permits — configure one "
                f"in the crawling layer (CRAWL_PROVIDER and its credentials). The platform "
                f"does not work around bot detection."
            )

        detailed = self._enrich(records, context) if self.config.fetch_company_pages else records
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "[wellfound] completed run=%s pages_crawled=%d companies=%d skipped_known=%d "
            "blocked_pages=%d in %dms",
            context.run_id or "-", pages_crawled, len(detailed), skipped_known,
            blocked_pages, duration_ms,
        )
        return detailed

    def _budget(self, context: DiscoveryContext) -> int:
        """The smaller of the connector's own cap and the engine's per-source limit."""
        limits = [self.config.max_companies]
        if context.limit is not None:
            limits.append(context.limit)
        return max(1, min(limits))

    def _is_known(self, entry: dict[str, Any], context: DiscoveryContext) -> bool:
        """Has the platform already stored this company?

        Checked on the Wellfound slug first: that is the only identity available from
        a listing card, and it is what a previous run stored as ``source_id``. The
        content key is a second chance for the rare listing that already carries a
        website. Either way the engine supplies the index — the connector never runs
        a database query.
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

    def _enrich(self, records: list[dict[str, Any]],
                context: DiscoveryContext) -> list[dict[str, Any]]:
        """Fetch each company's public page and merge in what it exposes.

        A page that fails or is challenged leaves the listing-level record intact —
        a thin candidate is still useful, and the engine will score it accordingly.
        """
        out: list[dict[str, Any]] = []
        blocked = 0
        for record in records:
            slug = record.get("slug", "")
            if not slug:
                out.append(record)
                continue
            result = self._crawl_page(self.config.company_url(slug), context)
            if result is None or result.page is None:
                out.append(record)
                continue
            if parser.looks_blocked(result.page):
                blocked += 1
                out.append(record)
                continue
            # Listing values win over page values only where the listing is more
            # specific; here the company's own page is authoritative, so it merges over.
            out.append({**record, **parser.parse_company_page(result.page)})
        if blocked:
            logger.warning("[wellfound] %d company page(s) returned a bot challenge", blocked)
        return out

    def _crawl_page(self, url: str, context: DiscoveryContext) -> CrawlResult | None:
        """One page via the crawl service. ``None`` when it could not be retrieved.

        Never raises: a missing or failing page is a normal outcome of crawling the
        open web, and it must not abort the whole source.
        """
        options = CrawlOptions(
            max_depth=self.config.crawl_depth,
            max_pages=1,
            include_markdown=True,
            render_javascript=True,
            timeout_seconds=self.config.request_timeout_seconds,
            extra=dict(self.config.extra),
        )
        try:
            result = self.crawl.fetch_page(url, options)
        except Exception:      # noqa: BLE001 - the service already contains failures
            logger.warning("[wellfound] crawl raised for %s", url, exc_info=True)
            return None
        if not result.ok or result.page is None:
            logger.info("[wellfound] %s unavailable: %s", url, result.error or result.status.value)
            return None
        return result

    # ------------------------------------------------------------------ normalize
    def normalize(self, raw: Any, context: DiscoveryContext) -> DiscoveryCandidate | None:
        """One raw record → a discovery candidate.

        Field-shape mapping only. Nothing is inferred, defaulted or invented: a value
        Wellfound did not publish stays empty, because a fabricated one would feed
        the engine's confidence model as if it were evidence.
        """
        if not isinstance(raw, dict):
            return None
        name = str(raw.get("company_name") or "").strip()
        slug = str(raw.get("slug") or "").strip()
        if not name and not slug:
            return None

        technologies = tuple(str(h).strip() for h in (raw.get("headings") or ())
                             if str(h).strip())
        return DiscoveryCandidate(
            # The slug is a last-resort identifier, not a name: it is what Wellfound
            # calls the company in a URL, which is the only public label available
            # when a listing card renders no text.
            company_name=name or slug.replace("-", " ").strip(),
            website=str(raw.get("website") or "").strip(),
            linkedin_url=str(raw.get("linkedin_url") or "").strip(),
            description=str(raw.get("description") or "").strip(),
            industry=str(raw.get("industry") or "").strip(),
            headquarters=str(raw.get("headquarters") or "").strip(),
            country=str(raw.get("country") or "").strip(),
            founded_year=str(raw.get("founded_year") or "").strip(),
            employee_count=str(raw.get("employee_count") or "").strip(),
            funding_stage=str(raw.get("funding_stage") or "").strip(),
            technologies=technologies[:10],
            source_id=slug,
            source_url=str(raw.get("source_url") or "").strip(),
            raw_payload=dict(raw),
        )
