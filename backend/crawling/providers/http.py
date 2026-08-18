"""Plain HTTP crawl provider.

No JavaScript rendering, no API key, no cost. For a static page — a sitemap, a
press release, a careers listing rendered server-side — this is strictly better than
paying a hosted provider.

It also serves an architectural purpose: it is a second, completely different
implementation of :class:`CrawlProvider`, which is what proves the abstraction is
genuinely vendor-neutral rather than Firecrawl's API with a wrapper around it. If
this provider satisfies the same contract and the same tests, so will the next one.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from backend.crawling.base import CrawlProvider
from backend.crawling.extractor import absolute_links, extract
from backend.crawling.schemas import (
    CrawlOptions,
    CrawlTimeout,
    PageContent,
    PermanentCrawlError,
    ProviderCapabilities,
    RateLimited,
    TransientCrawlError,
)

logger = logging.getLogger("crawling.providers.http")

DEFAULT_USER_AGENT = (
    "SiliconPatternsBot/1.0 (+https://siliconpatterns.com/bot; platform crawler)"
)
_SITEMAP_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
#: A response we cannot parse as a page. Fetching a PDF and calling it HTML would
#: produce garbage text that downstream extraction would treat as real content.
_HTML_TYPES = ("text/html", "application/xhtml", "text/plain", "application/xml", "text/xml")


class HttpCrawlProvider(CrawlProvider):
    """Fetches pages over plain HTTP and extracts them locally."""

    name = "http"

    def __init__(
        self,
        *,
        timeout_seconds: int = 30,
        user_agent: str = DEFAULT_USER_AGENT,
        max_bytes: int = 5_000_000,
        client: httpx.Client | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.max_bytes = max_bytes
        self._client = client
        self._owns_client = client is None

    @classmethod
    def from_settings(cls, settings, *, client: httpx.Client | None = None) -> "HttpCrawlProvider":
        return cls(
            timeout_seconds=getattr(settings, "crawl_timeout_seconds", 30),
            user_agent=getattr(settings, "crawl_user_agent", DEFAULT_USER_AGENT),
            client=client,
        )

    # ------------------------------------------------------------------ contract
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name=self.name, renders_javascript=False, supports_crawl=False,
            supports_sitemap=True, supports_markdown=False, supports_screenshot=False,
            requires_credentials=False,
            description="Plain HTTP fetch with local extraction (no JS rendering)",
        )

    def validate(self) -> tuple[bool, str]:
        return True, ""      # nothing to configure

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout_seconds, follow_redirects=True,
                                        headers={"User-Agent": self.user_agent})
            _log_client_config(self._client, self.timeout_seconds, self.user_agent)
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    # ------------------------------------------------------------------ fetch
    def _get(self, url: str, timeout: float) -> httpx.Response:
        if urlparse(url).scheme not in ("http", "https"):
            raise PermanentCrawlError(f"unsupported URL scheme: {url!r}", url=url)
        try:
            response = self.client.get(url, timeout=timeout,
                                       headers={"User-Agent": self.user_agent})
        except httpx.TimeoutException as exc:
            raise CrawlTimeout(f"request timed out: {exc}", url=url) from exc
        except httpx.HTTPError as exc:
            raise TransientCrawlError(f"transport error: {exc}", url=url) from exc

        status = response.status_code
        if status == 429:
            raise RateLimited("rate limited by the site",
                              retry_after=_float(response.headers.get("Retry-After"), 0.0),
                              status_code=status, url=url)
        if status in (401, 403, 404, 410):
            raise PermanentCrawlError(f"HTTP {status}", status_code=status, url=url)
        if status >= 500:
            raise TransientCrawlError(f"HTTP {status}", status_code=status, url=url)
        if status >= 400:
            raise PermanentCrawlError(f"HTTP {status}", status_code=status, url=url)
        return response

    def fetch_page(self, url: str, options: CrawlOptions) -> PageContent:
        response = self._get(url, timeout=options.timeout_seconds or self.timeout_seconds)
        content_type = (response.headers.get("Content-Type") or "").lower()
        if content_type and not any(t in content_type for t in _HTML_TYPES):
            raise PermanentCrawlError(f"unsupported content type: {content_type}", url=url)

        body = response.text
        if len(body) > self.max_bytes:
            logger.info("[crawl] %s truncated at %d bytes", url, self.max_bytes)
            body = body[: self.max_bytes]

        page = extract(body, url=str(response.url), include_html=options.include_html,
                       include_markdown=options.include_markdown, provider=self.name,
                       status_code=response.status_code)
        # Follow redirects: the final URL is the page's real identity.
        page.url = str(response.url)
        page.canonical_url = page.canonical_url or page.url
        return page

    def fetch_sitemap(self, url: str, options: CrawlOptions) -> list[str]:
        """Read ``/sitemap.xml``. Handles a sitemap index one level deep, which is
        how most large sites are laid out."""
        sitemap_url = url if url.rstrip("/").endswith(".xml") else urljoin(url, "/sitemap.xml")
        response = self._get(sitemap_url, timeout=options.timeout_seconds or self.timeout_seconds)
        locs = _SITEMAP_LOC.findall(response.text or "")
        _log_sitemap_response(sitemap_url, response, locs)

        nested = [loc for loc in locs if loc.rstrip("/").endswith(".xml")]
        pages = [loc for loc in locs if not loc.rstrip("/").endswith(".xml")]
        for child in nested[:10]:      # bounded: a pathological index must not fan out
            try:
                child_response = self._get(child, timeout=options.timeout_seconds
                                           or self.timeout_seconds)
                pages.extend(l for l in _SITEMAP_LOC.findall(child_response.text or "")
                             if not l.rstrip("/").endswith(".xml"))
            except Exception:      # noqa: BLE001 - one bad child sitemap is not fatal
                logger.debug("[crawl] nested sitemap %s failed", child, exc_info=True)
        return list(absolute_links(pages, sitemap_url))[: max(1, options.max_pages)]


#: Diagnostics never carry a response body — only shape and provenance. Enough to
#: tell "this host served us something different" from "our parser is wrong", and
#: nothing that could leak page content into a log aggregator.
_SITEMAP_LOC_SAMPLE = 3
_client_config_logged = False


def _proxy_env() -> list[str]:
    """Which proxy variables are SET (names only — a proxy URL can carry credentials)."""
    return sorted(k for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
                              "http_proxy", "https_proxy", "all_proxy", "no_proxy")
                  if os.environ.get(k))


def _log_client_config(client: httpx.Client, timeout_seconds: int, user_agent: str) -> None:
    """Log the effective HTTP client configuration once per process.

    Production and a developer machine can differ in ways that change what a host
    returns — an egress proxy, a different httpx/h2 build, a different UA. Logging it
    once at client construction makes those differences visible without a redeploy.
    """
    global _client_config_logged
    if _client_config_logged:
        return
    _client_config_logged = True
    logger.info(
        "[crawl] http client: httpx=%s follow_redirects=%s timeout=%ss http2=%s "
        "ua=%r proxy_env=%s",
        getattr(httpx, "__version__", "?"), client.follow_redirects, timeout_seconds,
        _http2_enabled(client), user_agent, _proxy_env() or "none",
    )


def _http2_enabled(client: httpx.Client) -> str:
    """Best-effort read of the HTTP/2 switch; never fails over a private attribute."""
    try:
        transport = client._transport            # noqa: SLF001 - diagnostics only
        return str(getattr(transport, "_pool", None).__class__.__name__)
    except Exception:      # noqa: BLE001
        return "?"


def _log_sitemap_response(url: str, response: httpx.Response, locs: list[str]) -> None:
    """One bounded line describing a sitemap response — shape only, never the body.

    Exists because production and local execution disagree about what this URL
    returns: one sees a single self-referencing entry, the other thousands. The
    request/response metadata is what separates "a different body was served" from
    "the same body was parsed differently".
    """
    try:
        body = response.content or b""
        headers = response.headers
        first = locs[:_SITEMAP_LOC_SAMPLE]
        logger.info(
            "[crawl] sitemap %s -> final=%s status=%s ctype=%r cenc=%r clen=%s "
            "bytes=%d sha256=%s locs=%d self_referencing=%s first=%s",
            url, str(response.url), response.status_code,
            headers.get("Content-Type", ""), headers.get("Content-Encoding", ""),
            headers.get("Content-Length", "-"), len(body),
            hashlib.sha256(body).hexdigest()[:12],
            len(locs), bool(locs) and locs[0].rstrip("/") == url.rstrip("/"), first,
        )
    except Exception:      # noqa: BLE001 - diagnostics must never break a crawl
        logger.debug("[crawl] sitemap diagnostics failed for %s", url, exc_info=True)


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
