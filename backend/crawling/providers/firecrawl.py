"""Firecrawl provider.

Firecrawl is infrastructure: it renders JavaScript, crawls sites, and returns
content. It makes no decision about what that content means.

This is the only module in the platform that knows Firecrawl's API shape. Everything
above it speaks :class:`CrawlProvider` and the vendor-neutral schemas, so replacing
Firecrawl means writing a sibling of this file and changing one setting.

API surface used (v1):
    POST /v1/scrape   — one URL, rendered, returns markdown + html + metadata
    POST /v1/crawl    — start a recursive crawl; returns a job id
    GET  /v1/crawl/id — poll that job
    POST /v1/map      — enumerate a site's URLs (sitemap-equivalent)

No official SDK is used: it would add a dependency whose upgrade cadence we do not
control, for a handful of JSON calls the platform already has an HTTP client for.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from backend.crawling.base import CrawlProvider
from backend.crawling.extractor import absolute_links, extract
from backend.crawling.schemas import (
    CrawlOptions,
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

logger = logging.getLogger("crawling.providers.firecrawl")

DEFAULT_BASE_URL = "https://api.firecrawl.dev"
#: Recursive crawls are asynchronous; these bound the poll loop so a stuck job cannot
#: hold a scheduled run open indefinitely.
_POLL_INTERVAL_SECONDS = 2.0
_POLL_MAX_SECONDS = 600


class FirecrawlProvider(CrawlProvider):
    """Hosted crawling with JavaScript rendering."""

    name = "firecrawl"

    def __init__(
        self,
        *,
        api_key: str = "",
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: int = 30,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds
        # An injected client is how tests exercise this against a transport mock, and
        # how a caller supplies its own pooling/proxy configuration.
        self._client = client
        self._owns_client = client is None

    @classmethod
    def from_settings(cls, settings, *, client: httpx.Client | None = None) -> "FirecrawlProvider":
        return cls(
            api_key=getattr(settings, "firecrawl_api_key", ""),
            base_url=getattr(settings, "firecrawl_base_url", DEFAULT_BASE_URL),
            timeout_seconds=getattr(settings, "crawl_timeout_seconds", 30),
            client=client,
        )

    # ------------------------------------------------------------------ contract
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name=self.name, renders_javascript=True, supports_crawl=True,
            supports_sitemap=True, supports_markdown=True, supports_screenshot=True,
            requires_credentials=True, max_concurrency=0,
            description="Hosted crawling with JavaScript rendering (firecrawl.dev)",
        )

    def validate(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "FIRECRAWL_API_KEY is not set"
        if not self.base_url.startswith(("http://", "https://")):
            return False, f"invalid FIRECRAWL_BASE_URL: {self.base_url!r}"
        return True, ""

    def health(self) -> ProviderHealth:
        ok, reason = self.validate()
        if not ok:
            return ProviderHealth(self.name, ProviderStatus.UNAVAILABLE, reason)
        # Credentials present; a real probe would spend quota, so report configured
        # and let the first real request surface an auth problem.
        return ProviderHealth(self.name, ProviderStatus.OK, "configured")

    # ------------------------------------------------------------------ transport
    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout_seconds)
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _request(self, method: str, path: str, *, json_body: dict | None = None,
                 timeout: float | None = None) -> dict[str, Any]:
        """One API call, with provider errors mapped onto the platform's taxonomy.

        The mapping is the point: callers and the retry policy reason about
        transient-vs-permanent, never about Firecrawl's status codes.
        """
        ok, reason = self.validate()
        if not ok:
            raise ProviderNotConfigured(reason)
        url = f"{self.base_url}{path}"
        try:
            response = self.client.request(
                method, url, headers=self._headers(), json=json_body,
                timeout=timeout or self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise CrawlTimeout(f"firecrawl timed out: {exc}", url=url) from exc
        except httpx.HTTPError as exc:
            raise TransientCrawlError(f"firecrawl transport error: {exc}", url=url) from exc

        status = response.status_code
        if status == 429:
            retry_after = _float(response.headers.get("Retry-After"), 0.0)
            raise RateLimited("firecrawl rate limit", retry_after=retry_after,
                              status_code=status, url=url)
        if status in (401, 403):
            # Never echo the response body here — it can carry the key back.
            raise PermanentCrawlError(f"firecrawl authentication failed ({status})",
                                      status_code=status, url=url)
        if status in (400, 404, 422):
            raise PermanentCrawlError(f"firecrawl rejected the request ({status}): "
                                      f"{response.text[:200]}", status_code=status, url=url)
        if status >= 500:
            raise TransientCrawlError(f"firecrawl server error ({status})",
                                      status_code=status, url=url)
        if status >= 300:
            raise TransientCrawlError(f"unexpected firecrawl status {status}",
                                      status_code=status, url=url)
        try:
            return response.json() or {}
        except ValueError as exc:
            raise TransientCrawlError(f"firecrawl returned non-JSON: {exc}", url=url) from exc

    # ------------------------------------------------------------------ page
    def _scrape_body(self, url: str, options: CrawlOptions) -> dict[str, Any]:
        formats = ["markdown"] if options.include_markdown else []
        if options.include_html:
            formats.append("html")
        return {
            "url": url,
            "formats": formats or ["markdown"],
            "onlyMainContent": True,
            "timeout": max(1, options.timeout_seconds) * 1000,      # provider wants ms
            **options.extra,
        }

    def fetch_page(self, url: str, options: CrawlOptions) -> PageContent:
        payload = self._request("POST", "/v1/scrape", json_body=self._scrape_body(url, options),
                                timeout=options.timeout_seconds)
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        return self._to_page(data or {}, fallback_url=url, options=options)

    # ------------------------------------------------------------------ crawl
    def crawl_site(self, url: str, options: CrawlOptions) -> list[PageContent]:
        """Server-side recursive crawl: one billed job instead of N page requests."""
        body: dict[str, Any] = {
            "url": url,
            "limit": max(1, options.max_pages),
            "maxDepth": max(1, options.max_depth),
            "scrapeOptions": {"formats": ["markdown"] + (["html"] if options.include_html else [])},
        }
        if options.only_paths:
            body["includePaths"] = list(options.only_paths)
        if options.exclude_paths:
            body["excludePaths"] = list(options.exclude_paths)
        body.update(options.extra)

        started = self._request("POST", "/v1/crawl", json_body=body)
        job_id = started.get("id") or started.get("jobId")
        if not job_id:
            # Some deployments answer synchronously; take the data if it is there.
            if started.get("data"):
                return self._pages_from(started, url, options)
            raise TransientCrawlError("firecrawl crawl returned no job id", url=url)

        deadline = time.monotonic() + _POLL_MAX_SECONDS
        while True:
            payload = self._request("GET", f"/v1/crawl/{job_id}")
            status = (payload.get("status") or "").lower()
            if status in ("completed", "complete", "success"):
                return self._pages_from(payload, url, options)
            if status in ("failed", "cancelled", "error"):
                raise TransientCrawlError(
                    f"firecrawl crawl {status}: {payload.get('error', '')[:200]}", url=url)
            if time.monotonic() >= deadline:
                raise CrawlTimeout(
                    f"firecrawl crawl did not finish within {_POLL_MAX_SECONDS}s", url=url)
            time.sleep(_POLL_INTERVAL_SECONDS)

    def fetch_sitemap(self, url: str, options: CrawlOptions) -> list[str]:
        payload = self._request("POST", "/v1/map",
                                json_body={"url": url, "limit": max(1, options.max_pages),
                                           **options.extra})
        links = payload.get("links") or payload.get("data") or []
        raw = [item if isinstance(item, str) else (item or {}).get("url", "") for item in links]
        return list(absolute_links([r for r in raw if r], url))

    # ------------------------------------------------------------------ mapping
    def _pages_from(self, payload: dict[str, Any], fallback_url: str,
                    options: CrawlOptions) -> list[PageContent]:
        data = payload.get("data")
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        return [self._to_page(item or {}, fallback_url=fallback_url, options=options)
                for item in items]

    def _to_page(self, data: dict[str, Any], *, fallback_url: str,
                 options: CrawlOptions) -> PageContent:
        """Firecrawl's response → the platform's PageContent.

        Prefers the provider's own markdown (it strips chrome better than a local
        conversion), but falls back to extracting from HTML so a response missing a
        format still yields the same shape as every other provider.
        """
        meta = data.get("metadata") or {}
        html = data.get("html") or data.get("rawHtml") or ""
        markdown = data.get("markdown") or ""
        url = (meta.get("sourceURL") or meta.get("url") or data.get("url") or fallback_url)

        if html:
            page = extract(html, url=url, include_html=options.include_html,
                           include_markdown=not markdown and options.include_markdown,
                           provider=self.name,
                           status_code=_int(meta.get("statusCode"), 200))
            if markdown and options.include_markdown:
                page.markdown = markdown
        else:
            page = PageContent(
                url=url,
                canonical_url=meta.get("canonical") or meta.get("og:url") or url,
                status_code=_int(meta.get("statusCode"), 200),
                markdown=markdown if options.include_markdown else "",
                text=markdown,
                provider=self.name,
            )
            page.links = absolute_links(data.get("links") or [], url)

        page.title = page.title or str(meta.get("title") or meta.get("og:title") or "")[:500]
        page.description = page.description or str(
            meta.get("description") or meta.get("og:description") or "")[:2000]
        page.language = page.language or str(meta.get("language") or "")[:20]
        # Provider metadata is merged UNDER locally extracted values so a page's own
        # markup stays authoritative.
        page.metadata = {**{k: v for k, v in meta.items() if v not in (None, "")},
                         **page.metadata}
        return page


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
