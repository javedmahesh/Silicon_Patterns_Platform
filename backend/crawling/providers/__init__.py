"""Crawl providers.

Importing this package registers every built-in provider. Adding another (Playwright,
ScrapingBee, Browserless, an internal renderer) is one module here plus a
``register()`` call — the service, the cache, the limiter and every caller are
untouched.
"""
from __future__ import annotations

from backend.crawling.base import register
from backend.crawling.providers.firecrawl import FirecrawlProvider
from backend.crawling.providers.http import HttpCrawlProvider

__all__ = ["FirecrawlProvider", "HttpCrawlProvider", "register_defaults"]


def register_defaults(settings=None, *, replace: bool = True) -> list[str]:
    """Register the built-in providers, configured from settings.

    Called once at startup. ``replace=True`` because re-registering with fresh
    settings (a reload, a test) must not raise — the registry is a lookup table, not
    a ledger.
    """
    from backend.config import get_settings

    s = settings if settings is not None else get_settings()
    register(FirecrawlProvider.from_settings(s), replace=replace)
    register(HttpCrawlProvider.from_settings(s), replace=replace)
    return ["firecrawl", "http"]
