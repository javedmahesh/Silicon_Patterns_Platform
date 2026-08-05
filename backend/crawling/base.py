"""The crawl provider contract + registry.

A provider retrieves web content and returns :class:`PageContent`. That is its
entire responsibility. A provider must never:

* resolve companies, detect duplicates, or assign confidence,
* open a database session or write a row,
* emit discovery events,
* apply any business rule about what the content means.

Those belong to the engine that requested the crawl. This boundary is what lets
Firecrawl be swapped for another provider — or several used together — without the
rest of the platform changing: callers depend on :class:`CrawlProvider` and the
vendor-neutral schemas, never on a vendor SDK.

Adding a provider is one subclass plus a ``register()`` call.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from backend.crawling.schemas import (
    CrawlOptions,
    PageContent,
    ProviderCapabilities,
    ProviderHealth,
    ProviderStatus,
)

logger = logging.getLogger("crawling.provider")


class CrawlProvider(ABC):
    """One way of retrieving web content."""

    #: Stable identifier used in configuration, cache keys and logs.
    name: str = ""

    # ------------------------------------------------------------------ contract
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """What this provider supports. Cached by the service per request batch."""

    @abstractmethod
    def fetch_page(self, url: str, options: CrawlOptions) -> PageContent:
        """Retrieve ONE page. Raise a :class:`CrawlError` subclass on failure —
        the retry policy keys on which one."""

    # ------------------------------------------------------------------ optional
    def crawl_site(self, url: str, options: CrawlOptions) -> list[PageContent]:
        """Recursive crawl from ``url``.

        Default raises :class:`NotImplementedError`; the service checks
        ``capabilities().supports_crawl`` first and falls back to its own
        breadth-first walk over :meth:`fetch_page`, so a provider only implements
        this when it can do it better (server-side, one billed request).
        """
        raise NotImplementedError(f"{self.name} does not support recursive crawling")

    def fetch_sitemap(self, url: str, options: CrawlOptions) -> list[str]:
        """Return the URLs a site's sitemap advertises.

        Default raises :class:`NotImplementedError`; the service falls back to
        fetching and parsing ``/sitemap.xml`` itself.
        """
        raise NotImplementedError(f"{self.name} does not support sitemap enumeration")

    def validate(self) -> tuple[bool, str]:
        """``(ok, reason_if_not)`` — is this provider configured well enough to use?

        Checked before any request, so a missing API key surfaces as a clear
        configuration message instead of an authentication failure mid-crawl.
        """
        if self.capabilities().requires_credentials:
            return False, f"{self.name}: credentials required but validate() not implemented"
        return True, ""

    def health(self) -> ProviderHealth:
        """Liveness. Default derives from :meth:`validate` and performs no network
        I/O — override for a real probe against the provider's status endpoint."""
        ok, reason = self.validate()
        return ProviderHealth(
            name=self.name,
            status=ProviderStatus.OK if ok else ProviderStatus.UNAVAILABLE,
            detail=reason,
        )

    def close(self) -> None:
        """Release sockets/pools. Called on service shutdown; safe to no-op."""

    def __repr__(self) -> str:      # pragma: no cover - debugging aid
        return f"<{type(self).__name__} name={self.name!r}>"


# --------------------------------------------------------------------- registry
_PROVIDERS: dict[str, CrawlProvider] = {}


def register(provider: CrawlProvider, *, replace: bool = False) -> None:
    name = (provider.name or "").strip().lower()
    if not name:
        raise ValueError(f"{type(provider).__name__} must define a non-empty `name`")
    if name in _PROVIDERS and not replace:
        raise ValueError(f"crawl provider {name!r} is already registered")
    _PROVIDERS[name] = provider
    logger.debug("[crawl] registered provider %s", name)


def unregister(name: str) -> None:
    _PROVIDERS.pop((name or "").strip().lower(), None)


def get_provider(name: str) -> CrawlProvider | None:
    return _PROVIDERS.get((name or "").strip().lower())


def list_providers() -> list[str]:
    return sorted(_PROVIDERS)


def provider_health() -> dict[str, ProviderHealth]:
    out: dict[str, ProviderHealth] = {}
    for name in list_providers():
        provider = _PROVIDERS[name]
        try:
            out[name] = provider.health()
        except Exception as exc:      # noqa: BLE001 - health must never raise
            out[name] = ProviderHealth(name, ProviderStatus.UNAVAILABLE,
                                       f"health() raised: {exc}")
            logger.error("[crawl] %s.health() raised", name, exc_info=True)
    return out


def clear_providers() -> None:
    """Drop every registration. For tests; not part of the runtime path."""
    _PROVIDERS.clear()
