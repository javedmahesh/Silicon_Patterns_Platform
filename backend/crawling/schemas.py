"""Vendor-neutral crawl types.

These are the contract between the platform and whichever crawling provider is
configured. Nothing here mentions Firecrawl, or any other vendor: a consumer that
imports only this module keeps working when the provider is swapped.

A crawl result carries content and metadata. It carries no judgement — whether a
page describes an interesting company, a duplicate, or anything else is a decision
for the engine that asked for the crawl, never for the crawler.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CrawlStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"
    SKIPPED = "skipped"          # robots/depth/limit — not an error
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"


class CrawlMode(str, Enum):
    """What kind of retrieval was asked for."""

    PAGE = "page"                # one URL
    CRAWL = "crawl"              # follow links from a root, bounded by depth/limit
    SITEMAP = "sitemap"          # enumerate a site's sitemap.xml


class ProviderStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"  # unreachable or unconfigured


@dataclass(slots=True, frozen=True)
class ProviderCapabilities:
    """What a provider can do, so callers can pick one without naming it.

    ``renders_javascript`` is the reason a hosted provider exists at all: a plain
    HTTP fetch cannot see content a SPA renders client-side.
    """

    name: str
    renders_javascript: bool = False
    supports_crawl: bool = False        # recursive link-following
    supports_sitemap: bool = False
    supports_markdown: bool = False     # native markdown, vs. locally derived
    supports_screenshot: bool = False
    requires_credentials: bool = True
    max_concurrency: int = 0            # 0 = provider imposes no limit of its own
    description: str = ""


@dataclass(slots=True)
class ProviderHealth:
    name: str
    status: ProviderStatus = ProviderStatus.OK
    detail: str = ""
    checked_at: datetime = field(default_factory=_utcnow)

    @property
    def usable(self) -> bool:
        return self.status in (ProviderStatus.OK, ProviderStatus.DEGRADED)


@dataclass(slots=True)
class CrawlOptions:
    """Per-request knobs. Defaults come from settings; a caller overrides what it
    needs. A provider that cannot honour an option ignores it rather than failing —
    the caller gets content either way, and ``PageContent.provider`` records who
    produced it."""

    max_depth: int = 1
    max_pages: int = 20
    include_html: bool = False          # raw HTML is large; off unless asked for
    include_markdown: bool = True
    render_javascript: bool = True
    timeout_seconds: int = 30
    only_paths: tuple[str, ...] = ()    # path prefixes to include, e.g. ("/careers",)
    exclude_paths: tuple[str, ...] = ()
    bypass_cache: bool = False
    extra: dict[str, Any] = field(default_factory=dict)   # provider-specific passthrough


@dataclass(slots=True)
class PageContent:
    """One retrieved page, normalized. Identical shape from every provider."""

    url: str = ""
    canonical_url: str = ""
    status_code: int = 0
    title: str = ""
    description: str = ""
    markdown: str = ""
    html: str = ""
    text: str = ""
    headings: tuple[str, ...] = ()
    links: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)   # og:*, meta name/content, JSON-LD
    language: str = ""
    fetched_at: datetime = field(default_factory=_utcnow)
    provider: str = ""
    from_cache: bool = False

    @property
    def empty(self) -> bool:
        return not (self.markdown or self.html or self.text or self.title)

    def best_text(self) -> str:
        """Whichever body representation is present, preferring the cleanest."""
        return self.markdown or self.text or self.html


@dataclass(slots=True)
class CrawlResult:
    """The outcome of one crawl request, however many pages it covered."""

    url: str = ""
    mode: CrawlMode = CrawlMode.PAGE
    status: CrawlStatus = CrawlStatus.OK
    pages: list[PageContent] = field(default_factory=list)
    provider: str = ""
    duration_ms: int = 0
    attempts: int = 1
    from_cache: bool = False
    error: str = ""
    requested_at: datetime = field(default_factory=_utcnow)

    @property
    def ok(self) -> bool:
        return self.status is CrawlStatus.OK

    @property
    def failed(self) -> bool:
        return self.status in (CrawlStatus.FAILED, CrawlStatus.TIMEOUT, CrawlStatus.RATE_LIMITED)

    @property
    def page(self) -> PageContent | None:
        """The primary page — the common case for a single-page crawl."""
        return self.pages[0] if self.pages else None

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def summary(self) -> str:
        return (f"{self.mode.value} {self.url} -> {self.status.value} "
                f"pages={self.page_count} provider={self.provider or '-'} "
                f"cache={'hit' if self.from_cache else 'miss'} {self.duration_ms}ms")


class CrawlError(Exception):
    """Base for crawl failures.

    ``retryable`` is what the retry policy keys on, so the decision lives with the
    error that knows the cause rather than in a status-code table far away.
    """

    retryable = False

    def __init__(self, message: str, *, status_code: int = 0, url: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.url = url


class TransientCrawlError(CrawlError):
    """Server error, connection reset, upstream hiccup — worth retrying."""

    retryable = True


class CrawlTimeout(TransientCrawlError):
    """The provider did not answer in time."""


class RateLimited(TransientCrawlError):
    """Provider throttled us. ``retry_after`` is honoured when supplied."""

    def __init__(self, message: str, *, retry_after: float = 0.0, **kw) -> None:
        super().__init__(message, **kw)
        self.retry_after = retry_after


class PermanentCrawlError(CrawlError):
    """404, 401, malformed URL, unsupported scheme — retrying cannot help."""

    retryable = False


class ProviderNotConfigured(PermanentCrawlError):
    """No API key / no provider registered. A configuration problem, not a failure."""
