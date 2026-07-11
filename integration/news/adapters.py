"""News source adapters — pluggable ingestion for the News Collection Engine.

Each adapter turns one configured source into a list of *normalized article dicts*
carrying source metadata (type, publisher, url, collected/published timestamps).
Adapters never touch the database — the engine persists what they return.

Adding a future source = one new subclass + one ``register`` line; the engine and
the rest of the pipeline are untouched (open/closed).

    articles = fetch_articles(source)            # live fetch (rss / google_alerts)
    articles = fetch_articles(source, raw=xml)   # parse supplied content (tests/offline)

Normalized article dict keys:
    title, url, body, publisher, source_name, source_type, adapter_type,
    published_at, company_name, company_domain
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Any, Iterable
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

logger = logging.getLogger("integration.news.adapters")


def _http_date(value: Any) -> str:
    """RFC-7231 HTTP-date for an ``If-Modified-Since`` header, or "" if not a datetime."""
    if not isinstance(value, datetime):
        return ""
    dt = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return format_datetime(dt, usegmt=True)

_UA = "SiliconPatterns-NewsCollector/1.0"
_FETCH_TIMEOUT = 15  # seconds; a slow/dead feed must never hang the pipeline

# RSS/Atom namespaces we care about.
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def _text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None and el.text else ""


def _strip_html(value: str) -> str:
    """Crude tag strip — feeds embed HTML in descriptions. Good enough for a summary."""
    if "<" not in value:
        return value.strip()
    out, depth = [], 0
    for ch in value:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return "".join(out).replace("&nbsp;", " ").replace("&amp;", "&").strip()


class NewsSourceAdapter:
    """Base adapter. Subclasses set ``adapter_type`` and implement ``parse``."""

    adapter_type: str = "base"

    def fetch(self, source: Any, *, raw: str | bytes | None = None,
              if_modified_since: Any = None) -> list[dict[str, Any]]:
        """Return normalized articles for *source*.

        *source* is a ``NewsSource`` row (or any object with ``.url``/``.publisher``/
        ``.name``/``.credibility``). ``raw`` short-circuits the network fetch with
        supplied feed content (used by tests and offline replays). ``if_modified_since``
        (a datetime, typically the source's ``last_collected_at``) enables a conditional
        GET so an unchanged feed returns nothing (HTTP 304) — incremental, no re-parse.
        """
        content = raw if raw is not None else self._download(
            getattr(source, "url", ""), if_modified_since=if_modified_since)
        if not content:
            return []
        try:
            articles = self.parse(content)
        except ET.ParseError as exc:
            logger.warning("[news:%s] parse error for %s: %s", self.adapter_type,
                           getattr(source, "url", "?"), exc)
            return []
        publisher = getattr(source, "publisher", "") or ""
        name = getattr(source, "name", "") or publisher
        for a in articles:
            a.setdefault("adapter_type", self.adapter_type)
            a.setdefault("source_type", self.adapter_type)
            a["publisher"] = a.get("publisher") or publisher
            a["source_name"] = a.get("source_name") or name
            a.setdefault("collected_at", datetime.now(timezone.utc).isoformat())
        return articles

    def _download(self, url: str, *, if_modified_since: Any = None) -> str:
        if not url:
            return ""
        headers = {"User-Agent": _UA}
        if if_modified_since is not None:
            stamp = _http_date(if_modified_since)
            if stamp:
                headers["If-Modified-Since"] = stamp
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=_FETCH_TIMEOUT) as resp:  # noqa: S310 (trusted config URL)
                return resp.read().decode("utf-8", "replace")
        except HTTPError as exc:
            if exc.code == 304:  # Not Modified — incremental: nothing new since last run
                logger.info("[news:%s] 304 Not Modified: %s", self.adapter_type, url)
            else:
                logger.warning("[news:%s] HTTP %s for %s", self.adapter_type, exc.code, url)
            return ""
        except Exception as exc:  # network/DNS/timeout — never fail the pipeline
            logger.warning("[news:%s] fetch failed for %s: %s", self.adapter_type, url, exc)
            return ""

    def parse(self, content: str | bytes) -> list[dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError


class RssAdapter(NewsSourceAdapter):
    """RSS 2.0 / Atom feed parser (stdlib only). Handles both ``<item>`` (RSS) and
    ``<entry>`` (Atom) so most publisher feeds work with one adapter."""

    adapter_type = "rss"

    def parse(self, content: str | bytes) -> list[dict[str, Any]]:
        root = ET.fromstring(content)
        items: list[dict[str, Any]] = []
        for item in root.iter():
            tag = item.tag.split("}")[-1]
            if tag not in ("item", "entry"):
                continue
            items.append(self._article(item))
        return [a for a in items if a.get("title") or a.get("url")]

    def _article(self, item: ET.Element) -> dict[str, Any]:
        title = _text(item.find("title")) or _text(item.find("atom:title", _NS))
        link = _text(item.find("link"))
        if not link:  # Atom: <link href="..."/> is childless (falsy) -> use explicit is-None
            link_el = item.find("atom:link", _NS)
            if link_el is None:
                link_el = item.find("link")
            if link_el is not None:
                link = link_el.get("href", "") or _text(link_el)
        body = (
            _text(item.find("content:encoded", _NS))
            or _text(item.find("description"))
            or _text(item.find("atom:summary", _NS))
            or _text(item.find("atom:content", _NS))
        )
        published = (
            _text(item.find("pubDate"))
            or _text(item.find("atom:published", _NS))
            or _text(item.find("atom:updated", _NS))
            or _text(item.find("dc:date", _NS))
        )
        return {
            "title": _strip_html(title),
            "url": link.strip(),
            "body": _strip_html(body),
            "published_at": published,
            "publisher": _text(item.find("dc:creator", _NS)),
        }


class GoogleAlertsAdapter(RssAdapter):
    """Google Alerts delivers an Atom feed whose entry titles/links are the alerted
    articles. Parsing is identical to Atom; we only relabel the source type and
    unwrap Google's redirect ``url?...&url=<real>`` links."""

    adapter_type = "google_alerts"

    def parse(self, content: str | bytes) -> list[dict[str, Any]]:
        from urllib.parse import parse_qs, urlparse

        articles = super().parse(content)
        for a in articles:
            u = a.get("url", "")
            if "google.com" in u and "url=" in u:
                real = parse_qs(urlparse(u).query).get("url", [])
                if real:
                    a["url"] = real[0]
            a["source_type"] = "google_alerts"
        return articles


class FileAdapter(NewsSourceAdapter):
    """Adapts already-collected feed rows (e.g. the Blog Crawler's
    ``blog_opportunities.jsonl`` / ``company_news.jsonl``) into normalized articles,
    so the existing file feeds flow through the same engine as live sources."""

    adapter_type = "file"

    def fetch(self, source: Any, *, raw: str | bytes | None = None,
              rows: Iterable[dict[str, Any]] | None = None,
              if_modified_since: Any = None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in (rows or []):
            title = (row.get("article_title") or row.get("headline") or row.get("title") or "").strip()
            url = (row.get("article_url") or row.get("url") or "").strip()
            if not title and not url:
                continue
            out.append({
                "title": title,
                "url": url,
                "body": (row.get("summary") or row.get("body") or "").strip(),
                "published_at": (row.get("published_date") or row.get("published_at") or "").strip(),
                "publisher": (row.get("source") or row.get("publisher") or "").strip(),
                "source_name": (row.get("source") or "").strip(),
                "source_type": (row.get("source_type") or "file").strip(),
                "adapter_type": "file",
                "company_name": (row.get("company_name") or "").strip(),
                "company_domain": (row.get("company_domain") or row.get("website") or "").strip(),
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "_feed_row": row,  # keep the raw row so the engine can honor pre-extracted fields
            })
        return out

    def parse(self, content: str | bytes) -> list[dict[str, Any]]:  # pragma: no cover
        return []


# ------------------------------------------------------------------ registry
_REGISTRY: dict[str, NewsSourceAdapter] = {}


def register(adapter: NewsSourceAdapter) -> None:
    _REGISTRY[adapter.adapter_type] = adapter


register(RssAdapter())
register(GoogleAlertsAdapter())
register(FileAdapter())


def get_adapter(adapter_type: str) -> NewsSourceAdapter:
    """Adapter for *adapter_type*; falls back to RSS for unknown live feeds."""
    return _REGISTRY.get(adapter_type) or _REGISTRY["rss"]


def fetch_articles(source: Any, *, raw: str | bytes | None = None,
                   rows: Iterable[dict[str, Any]] | None = None,
                   incremental: bool = True) -> list[dict[str, Any]]:
    """Fetch + normalize articles for a configured *source* using its adapter.

    When ``incremental`` (default), a live adapter sends the source's
    ``last_collected_at`` as ``If-Modified-Since`` so an unchanged feed is skipped.
    """
    adapter = get_adapter(getattr(source, "adapter_type", "rss"))
    ims = getattr(source, "last_collected_at", None) if incremental else None
    if isinstance(adapter, FileAdapter):
        return adapter.fetch(source, raw=raw, rows=rows)
    return adapter.fetch(source, raw=raw, if_modified_since=ims)


# Production-quality semiconductor / industry feeds used to seed ``news_sources``.
# All are configuration/DB-driven once seeded (enable/disable, add more, or paste a
# Google Alerts RSS URL — see ``adapter_type='google_alerts'``, url left blank until
# the analyst creates the alert). ``enabled`` gates whether the scheduler fetches it.
#
# Semiconductor-industry publications (verified public RSS/Atom endpoints):
DEFAULT_SEMI_FEEDS: tuple[dict[str, Any], ...] = (
    # --- publications (enabled) ---
    {"name": "EE Times", "adapter_type": "rss", "url": "https://www.eetimes.com/feed/",
     "publisher": "EE Times", "credibility": 78, "enabled": True},
    {"name": "Semiconductor Engineering", "adapter_type": "rss",
     "url": "https://semiengineering.com/feed/", "publisher": "Semiconductor Engineering",
     "credibility": 82, "enabled": True},
    {"name": "Tom's Hardware", "adapter_type": "rss", "url": "https://www.tomshardware.com/feeds/all",
     "publisher": "Tom's Hardware", "credibility": 68, "enabled": True},
    {"name": "The Register — Systems", "adapter_type": "rss",
     "url": "https://www.theregister.com/headlines.atom", "publisher": "The Register",
     "credibility": 66, "enabled": True},
    {"name": "WikiChip Fuse", "adapter_type": "rss", "url": "https://fuse.wikichip.org/feed/",
     "publisher": "WikiChip Fuse", "credibility": 70, "enabled": True},
    # --- official company newsrooms (enabled) ---
    {"name": "NVIDIA Newsroom", "adapter_type": "rss",
     "url": "https://nvidianews.nvidia.com/releases.xml", "publisher": "NVIDIA",
     "credibility": 85, "enabled": True},
    # --- Google Alerts (disabled until the analyst pastes an RSS-delivery URL) ---
    {"name": "Google Alerts — Semiconductor", "adapter_type": "google_alerts",
     "url": "", "publisher": "Google Alerts", "credibility": 55, "enabled": False},
    {"name": "Google Alerts — RISC-V", "adapter_type": "google_alerts",
     "url": "", "publisher": "Google Alerts", "credibility": 55, "enabled": False},
    {"name": "Google Alerts — chip funding", "adapter_type": "google_alerts",
     "url": "", "publisher": "Google Alerts", "credibility": 55, "enabled": False},
)
