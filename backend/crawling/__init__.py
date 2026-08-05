"""Web crawling infrastructure.

Shared, vendor-neutral retrieval of web content for the whole platform: Market
Discovery, News Collection, Career Intelligence, Decision Maker Intelligence, and any
future crawler.

**This layer is infrastructure, not business logic.** It retrieves content, renders
JavaScript, crawls sites, extracts structure, and returns normalized results. It
never resolves companies, detects duplicates, assigns confidence, scores anything,
writes to the database, emits discovery events, or decides whether a company belongs
in Silicon Patterns. The engine that requested the crawl owns every one of those.

**Firecrawl is a provider, not the architecture.** ``backend/crawling/providers/``
holds one module per vendor, each implementing :class:`CrawlProvider`. Callers depend
on :class:`CrawlService` and the schemas here — never on a vendor SDK — so replacing
Firecrawl, or running several providers together, is a settings change plus one new
provider module. A plain-HTTP provider ships alongside it precisely to keep that
abstraction honest.

    from backend.crawling import CrawlOptions, CrawlService

    service = CrawlService.from_settings(settings)
    result = service.fetch_page("https://example.com")
    if result.ok:
        page = result.page                     # title, description, markdown, links, metadata
"""
from __future__ import annotations

from backend.crawling.base import (
    CrawlProvider,
    clear_providers,
    get_provider,
    list_providers,
    provider_health,
    register,
    unregister,
)
from backend.crawling.cache import (
    CrawlCache,
    InMemoryCrawlCache,
    NullCrawlCache,
    cache_key,
)
from backend.crawling.extractor import absolute_links, extract, to_markdown
from backend.crawling.rate_limit import RateLimitConfig, RateLimiter, TokenBucket
from backend.crawling.retry import RetryPolicy, is_retryable, with_retries
from backend.crawling.schemas import (
    CrawlError,
    CrawlMode,
    CrawlOptions,
    CrawlResult,
    CrawlStatus,
    CrawlTimeout,
    PageContent,
    PermanentCrawlError,
    ProviderCapabilities,
    ProviderHealth,
    ProviderNotConfigured,
    ProviderStatus,
    RateLimited,
    TransientCrawlError,
)
from backend.crawling.service import CrawlConfig, CrawlService

__all__ = [
    "CrawlCache",
    "CrawlConfig",
    "CrawlError",
    "CrawlMode",
    "CrawlOptions",
    "CrawlProvider",
    "CrawlResult",
    "CrawlService",
    "CrawlStatus",
    "CrawlTimeout",
    "InMemoryCrawlCache",
    "NullCrawlCache",
    "PageContent",
    "PermanentCrawlError",
    "ProviderCapabilities",
    "ProviderHealth",
    "ProviderNotConfigured",
    "ProviderStatus",
    "RateLimitConfig",
    "RateLimited",
    "RateLimiter",
    "RetryPolicy",
    "TokenBucket",
    "TransientCrawlError",
    "absolute_links",
    "cache_key",
    "clear_providers",
    "extract",
    "get_provider",
    "is_retryable",
    "list_providers",
    "provider_health",
    "register",
    "register_default_providers",
    "to_markdown",
    "unregister",
    "with_retries",
]


def register_default_providers(settings=None, *, replace: bool = True) -> list[str]:
    """Register the built-in providers. Imported lazily so that merely importing
    this package does not construct HTTP clients."""
    from backend.crawling.providers import register_defaults

    return register_defaults(settings, replace=replace)
