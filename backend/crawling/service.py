"""The crawl service — the API every engine uses.

    service = CrawlService.from_settings(settings)
    result  = service.fetch_page("https://example.com")
    result  = service.crawl_site("https://example.com", CrawlOptions(max_depth=2))
    urls    = service.sitemap_urls("https://example.com")

This is the seam that makes the provider pluggable. Callers name a URL and options,
never a vendor; the service picks a provider from configuration, applies caching,
rate limiting and retries around it, and returns the same
:class:`~backend.crawling.schemas.CrawlResult` whichever provider ran.

It contains no business logic and touches no database. Market Discovery, News
Collection, Career Intelligence and any future crawler can all depend on it without
depending on each other.

Provider selection is capability-based, not name-based: a caller that needs
JavaScript rendering asks for it, and the service picks a provider that offers it,
falling back to a cheaper one when it is not required. That is what lets a plain
HTTP fetch serve a static page while Firecrawl handles a SPA, with no caller change.
"""
from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from urllib.parse import urlparse

from backend.crawling import base
from backend.crawling.cache import CrawlCache, InMemoryCrawlCache, NullCrawlCache, cache_key
from backend.crawling.extractor import absolute_links
from backend.crawling.rate_limit import RateLimitConfig, RateLimiter
from backend.crawling.retry import RetryOutcome, RetryPolicy, with_retries
from backend.crawling.schemas import (
    CrawlError,
    CrawlMode,
    CrawlOptions,
    CrawlResult,
    CrawlStatus,
    CrawlTimeout,
    PageContent,
    ProviderNotConfigured,
    RateLimited,
)

logger = logging.getLogger("crawling.service")


@dataclass(slots=True)
class CrawlConfig:
    """Service-level configuration, built from settings in production."""

    provider: str = ""                   # "" = choose by capability
    fallback_provider: str = "http"      # used when the preferred one is unusable
    cache_ttl_seconds: int = 3600
    cache_max_entries: int = 512
    default_options: CrawlOptions = field(default_factory=CrawlOptions)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    retry: RetryPolicy = field(default_factory=RetryPolicy)

    @classmethod
    def from_settings(cls, settings) -> "CrawlConfig":
        return cls(
            provider=getattr(settings, "crawl_provider", ""),
            fallback_provider=getattr(settings, "crawl_fallback_provider", "http"),
            cache_ttl_seconds=getattr(settings, "crawl_cache_ttl_seconds", 3600),
            cache_max_entries=getattr(settings, "crawl_cache_max_entries", 512),
            default_options=CrawlOptions(
                max_depth=getattr(settings, "crawl_max_depth", 1),
                max_pages=getattr(settings, "crawl_max_pages", 20),
                timeout_seconds=getattr(settings, "crawl_timeout_seconds", 30),
            ),
            rate_limit=RateLimitConfig(
                requests_per_minute=getattr(settings, "crawl_rate_limit_per_minute", 60),
                per_host_requests_per_minute=getattr(
                    settings, "crawl_per_host_rate_limit_per_minute", 30),
                max_concurrency=getattr(settings, "crawl_concurrency", 4),
                max_per_host_concurrency=getattr(settings, "crawl_per_host_concurrency", 2),
            ),
            retry=RetryPolicy.from_settings(settings),
        )


class CrawlService:
    """Caching, rate-limited, retrying access to whichever provider is configured."""

    def __init__(
        self,
        *,
        config: CrawlConfig | None = None,
        cache: CrawlCache | None = None,
        limiter: RateLimiter | None = None,
        providers: dict[str, base.CrawlProvider] | None = None,
    ) -> None:
        self.config = config or CrawlConfig()
        self.cache = cache if cache is not None else InMemoryCrawlCache(
            max_entries=self.config.cache_max_entries)
        self.limiter = limiter or RateLimiter(self.config.rate_limit)
        # An explicit map is how a caller (or a test) supplies providers without
        # touching the process-wide registry.
        self._providers = providers
        self.requests = 0

    @classmethod
    def from_settings(cls, settings, **kw) -> "CrawlService":
        config = CrawlConfig.from_settings(settings)
        if config.cache_ttl_seconds <= 0:
            kw.setdefault("cache", NullCrawlCache())
        return cls(config=config, **kw)

    # ------------------------------------------------------------- providers
    def _lookup(self, name: str) -> base.CrawlProvider | None:
        if self._providers is not None:
            return self._providers.get((name or "").strip().lower())
        return base.get_provider(name)

    def _available(self) -> list[base.CrawlProvider]:
        if self._providers is not None:
            return [self._providers[n] for n in sorted(self._providers)]
        return [p for p in (base.get_provider(n) for n in base.list_providers()) if p]

    def select_provider(self, options: CrawlOptions | None = None) -> base.CrawlProvider:
        """Pick a usable provider for this request.

        Order: the explicitly configured one, then any provider whose capabilities
        satisfy the request, then the configured fallback. Only providers that pass
        ``validate()`` are considered, so a missing API key degrades to the next
        option instead of failing the crawl.
        """
        o = options or self.config.default_options
        wanted_js = o.render_javascript

        def usable(provider: base.CrawlProvider | None) -> bool:
            if provider is None:
                return False
            try:
                ok, reason = provider.validate()
            except Exception:      # noqa: BLE001
                logger.error("[crawl] %s.validate() raised", provider.name, exc_info=True)
                return False
            if not ok:
                logger.debug("[crawl] provider %s unusable: %s", provider.name, reason)
            return ok

        preferred = self._lookup(self.config.provider) if self.config.provider else None
        if usable(preferred):
            return preferred                                   # type: ignore[return-value]
        if self.config.provider:
            logger.info("[crawl] configured provider %r is unusable — selecting by capability",
                        self.config.provider)

        usable_providers = [p for p in self._available() if usable(p)]
        if wanted_js:
            for provider in usable_providers:
                if provider.capabilities().renders_javascript:
                    return provider
        if usable_providers:
            return usable_providers[0]

        fallback = self._lookup(self.config.fallback_provider)
        if usable(fallback):
            return fallback                                    # type: ignore[return-value]
        raise ProviderNotConfigured(
            "no usable crawl provider is registered "
            f"(known: {', '.join(base.list_providers()) or 'none'})")

    # ------------------------------------------------------------- public API
    def fetch_page(self, url: str, options: CrawlOptions | None = None) -> CrawlResult:
        """Retrieve one page."""
        return self._run(url, CrawlMode.PAGE, options)

    def crawl_site(self, url: str, options: CrawlOptions | None = None) -> CrawlResult:
        """Crawl a site from ``url``, bounded by ``max_depth`` and ``max_pages``."""
        return self._run(url, CrawlMode.CRAWL, options)

    def sitemap(self, url: str, options: CrawlOptions | None = None) -> CrawlResult:
        """Enumerate a site's sitemap. Pages carry only URLs, not bodies."""
        return self._run(url, CrawlMode.SITEMAP, options)

    def sitemap_urls(self, url: str, options: CrawlOptions | None = None) -> list[str]:
        return [p.url for p in self.sitemap(url, options).pages]

    def invalidate(self, url: str, *, mode: CrawlMode = CrawlMode.PAGE,
                   options: CrawlOptions | None = None) -> bool:
        """Drop one cached crawl so the next call re-fetches."""
        provider = self.select_provider(options)
        key = cache_key(url, mode.value, provider.name, options or self.config.default_options)
        return bool(self.cache.invalidate(key))

    def clear_cache(self) -> int:
        return self.cache.clear()

    def health(self) -> dict:
        providers = ({n: p.health() for n, p in self._providers.items()}
                     if self._providers is not None else base.provider_health())
        try:
            selected = self.select_provider().name
        except CrawlError as exc:
            selected = f"none ({exc})"
        return {
            "selected_provider": selected,
            "providers": {
                name: {
                    "status": h.status.value, "detail": h.detail,
                    "renders_javascript": self._capabilities(name),
                }
                for name, h in providers.items()
            },
            "cache": getattr(self.cache, "stats", lambda: {})(),
            "rate_limit": self.limiter.stats(),
            "requests": self.requests,
        }

    def _capabilities(self, name: str) -> bool:
        provider = self._lookup(name)
        try:
            return bool(provider and provider.capabilities().renders_javascript)
        except Exception:      # noqa: BLE001
            return False

    def close(self) -> None:
        for provider in self._available():
            try:
                provider.close()
            except Exception:      # noqa: BLE001
                logger.debug("[crawl] %s.close() raised", provider.name, exc_info=True)

    # ------------------------------------------------------------- execution
    def _run(self, url: str, mode: CrawlMode, options: CrawlOptions | None) -> CrawlResult:
        """Cache → rate limit → retry → provider. Never raises."""
        o = options or self.config.default_options
        started = time.monotonic()
        result = CrawlResult(url=url, mode=mode, requested_at=datetime.now(timezone.utc))

        try:
            provider = self.select_provider(o)
        except CrawlError as exc:
            logger.warning("[crawl] %s %s: %s", mode.value, url, exc)
            return replace(result, status=CrawlStatus.FAILED, error=str(exc),
                           duration_ms=int((time.monotonic() - started) * 1000))
        result.provider = provider.name

        key = cache_key(url, mode.value, provider.name, o)
        if not o.bypass_cache:
            cached = self.cache.get(key)
            if cached is not None:
                logger.info("[crawl] cache HIT %s %s provider=%s", mode.value, url, provider.name)
                return replace(cached, from_cache=True,
                               duration_ms=int((time.monotonic() - started) * 1000))
        logger.info("[crawl] cache MISS %s %s provider=%s", mode.value, url, provider.name)

        logger.info("[crawl] started %s %s provider=%s depth=%d pages=%d",
                    mode.value, url, provider.name, o.max_depth, o.max_pages)
        outcome = RetryOutcome()
        try:
            with self.limiter.slot(url):
                self.requests += 1
                pages = with_retries(
                    lambda: self._dispatch(provider, url, mode, o),
                    self.config.retry, label=f"{mode.value} {url}", outcome=outcome,
                )
        except BaseException as exc:      # noqa: BLE001 - reported, never propagated
            status = (CrawlStatus.TIMEOUT if isinstance(exc, CrawlTimeout)
                      else CrawlStatus.RATE_LIMITED if isinstance(exc, RateLimited)
                      else CrawlStatus.FAILED)
            duration = int((time.monotonic() - started) * 1000)
            logger.warning("[crawl] failed %s %s provider=%s attempts=%d in %dms: %s",
                           mode.value, url, provider.name, outcome.attempts, duration,
                           str(exc)[:300])
            return replace(result, status=status, error=str(exc)[:500],
                           attempts=outcome.attempts, duration_ms=duration)

        result.pages = pages
        result.attempts = outcome.attempts
        result.duration_ms = int((time.monotonic() - started) * 1000)
        logger.info("[crawl] completed %s %s provider=%s pages=%d attempts=%d in %dms",
                    mode.value, url, provider.name, len(pages), outcome.attempts,
                    result.duration_ms)
        if self.config.cache_ttl_seconds > 0:
            self.cache.set(key, result, ttl_seconds=self.config.cache_ttl_seconds)
        return result

    def _dispatch(self, provider: base.CrawlProvider, url: str, mode: CrawlMode,
                  options: CrawlOptions) -> list[PageContent]:
        if mode is CrawlMode.PAGE:
            return [provider.fetch_page(url, options)]
        if mode is CrawlMode.SITEMAP:
            return [PageContent(url=u, provider=provider.name)
                    for u in self._sitemap_urls(provider, url, options)]
        return self._crawl(provider, url, options)

    def _sitemap_urls(self, provider: base.CrawlProvider, url: str,
                      options: CrawlOptions) -> list[str]:
        try:
            return provider.fetch_sitemap(url, options)
        except NotImplementedError:
            # Fall back to the plain-HTTP provider, which always can — the caller
            # asked for a sitemap, not for a specific provider to produce it.
            fallback = self._lookup(self.config.fallback_provider)
            if fallback is None or fallback is provider:
                raise
            logger.info("[crawl] %s cannot enumerate sitemaps — using %s",
                        provider.name, fallback.name)
            return fallback.fetch_sitemap(url, options)

    def _crawl(self, provider: base.CrawlProvider, url: str,
               options: CrawlOptions) -> list[PageContent]:
        """Recursive crawl, server-side when the provider supports it.

        The local fallback is breadth-first and same-host only: following off-site
        links would turn a bounded crawl of one company's site into an unbounded walk
        of the web.
        """
        if provider.capabilities().supports_crawl:
            return provider.crawl_site(url, options)

        root_host = (urlparse(url).hostname or "").lower()
        seen: set[str] = {url}
        queue: deque[tuple[str, int]] = deque([(url, 0)])
        pages: list[PageContent] = []

        while queue and len(pages) < options.max_pages:
            current, depth = queue.popleft()
            try:
                page = provider.fetch_page(current, options)
            except CrawlError as exc:
                # One unreachable page must not abort the crawl; the root failing is
                # a real failure and is re-raised so the caller sees it.
                logger.info("[crawl] skipping %s: %s", current, str(exc)[:200])
                if current == url:
                    raise
                continue
            pages.append(page)
            if depth >= options.max_depth - 1:
                continue
            for link in absolute_links(page.links, current):
                if len(seen) >= options.max_pages * 4:      # bound the frontier
                    break
                if link in seen or (urlparse(link).hostname or "").lower() != root_host:
                    continue
                if not _path_allowed(link, options):
                    continue
                seen.add(link)
                queue.append((link, depth + 1))
        return pages


def _path_allowed(url: str, options: CrawlOptions) -> bool:
    path = urlparse(url).path or "/"
    if options.exclude_paths and any(path.startswith(p) for p in options.exclude_paths):
        return False
    if options.only_paths:
        return any(path.startswith(p) for p in options.only_paths)
    return True
