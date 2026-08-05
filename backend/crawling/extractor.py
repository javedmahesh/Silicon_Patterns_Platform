"""HTML → normalized page content.

Deliberately generic: title, description, headings, links, metadata, canonical URL,
markdown, text. Nothing semiconductor-specific, nothing discovery-specific — this is
infrastructure, and the engine that requested the crawl decides what any of it means.

Uses the standard library's HTML parser rather than adding a dependency. It is
tolerant by design: real pages are malformed, and an extractor that raises on bad
markup is useless for crawling the open web.
"""
from __future__ import annotations

import json
import logging
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlparse

logger = logging.getLogger("crawling.extractor")

#: Elements whose text is never page content.
_SKIP_TEXT = frozenset({"script", "style", "noscript", "template", "svg", "canvas"})
_HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_BLOCK = frozenset({
    "p", "div", "section", "article", "header", "footer", "li", "tr", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol", "blockquote", "pre",
})
_WS = re.compile(r"[ \t ]+")
_BLANKS = re.compile(r"\n{3,}")


class _PageParser(HTMLParser):
    """Single pass over the document collecting everything the platform needs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.canonical = ""
        self.language = ""
        self.meta: dict[str, str] = {}
        self.headings: list[tuple[int, str]] = []      # (level, text)
        self.links: list[str] = []
        self.json_ld: list[dict] = []
        self._chunks: list[str] = []
        self._skip_depth = 0
        self._in_title = False
        self._heading_level = 0
        self._heading_buf: list[str] = []
        self._in_json_ld = False
        self._json_ld_buf: list[str] = []

    # ------------------------------------------------------------------ tags
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = {k.lower(): (v or "") for k, v in attrs}

        if tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_buf = []
            return
        if tag in _SKIP_TEXT:
            self._skip_depth += 1
            return
        if tag == "html" and a.get("lang"):
            self.language = a["lang"].strip()[:20]
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            self._meta(a)
        elif tag == "link" and "canonical" in a.get("rel", "").lower():
            self.canonical = a.get("href", "").strip()
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"].strip())
        elif tag in _HEADINGS:
            self._heading_level = int(tag[1])
            self._heading_buf = []
        if tag in _BLOCK:
            self._chunks.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self._in_json_ld and tag == "script":
            self._flush_json_ld()
            return
        if tag in _SKIP_TEXT:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag == "title":
            self._in_title = False
        elif tag in _HEADINGS and self._heading_level:
            text = _clean(" ".join(self._heading_buf))
            if text:
                self.headings.append((self._heading_level, text))
            self._heading_level = 0
            self._heading_buf = []
        if tag in _BLOCK:
            self._chunks.append("\n")

    def handle_data(self, data):
        if self._in_json_ld:
            self._json_ld_buf.append(data)
            return
        if self._skip_depth:
            return
        if self._in_title:
            self.title += data
        if self._heading_level:
            self._heading_buf.append(data)
        self._chunks.append(data)

    # ------------------------------------------------------------------ helpers
    def _meta(self, a: dict[str, str]) -> None:
        # name= (standard), property= (OpenGraph), itemprop= (microdata) all map to
        # one flat dict — callers should not care which convention a site chose.
        key = (a.get("name") or a.get("property") or a.get("itemprop") or "").strip().lower()
        content = a.get("content", "").strip()
        if key and content:
            self.meta.setdefault(key, content[:2000])
        if a.get("http-equiv", "").lower() == "content-language" and content:
            self.language = self.language or content[:20]

    def _flush_json_ld(self) -> None:
        self._in_json_ld = False
        raw = "".join(self._json_ld_buf).strip()
        self._json_ld_buf = []
        if not raw:
            return
        try:
            parsed = json.loads(raw)
        except ValueError:
            return          # malformed structured data is common; ignore it
        for item in (parsed if isinstance(parsed, list) else [parsed]):
            if isinstance(item, dict):
                self.json_ld.append(item)

    @property
    def text(self) -> str:
        return _clean_block("".join(self._chunks))


def _clean(value: str) -> str:
    return _WS.sub(" ", unescape(value or "")).strip()


def _clean_block(value: str) -> str:
    lines = [_clean(line) for line in (value or "").splitlines()]
    return _BLANKS.sub("\n\n", "\n".join(lines)).strip()


def absolute_links(links, base_url: str) -> tuple[str, ...]:
    """Resolve hrefs against the page URL, de-duplicated, http(s) only.

    Fragments are stripped: ``/pricing#faq`` and ``/pricing`` are the same page, and
    a crawler that treats them as two wastes half its budget.
    """
    out: list[str] = []
    seen: set[str] = set()
    for href in links or ():
        href = (href or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            continue
        try:
            resolved, _frag = urldefrag(urljoin(base_url, href))
        except ValueError:
            continue
        if urlparse(resolved).scheme not in ("http", "https"):
            continue
        if resolved not in seen:
            seen.add(resolved)
            out.append(resolved)
    return tuple(out)


def to_markdown(html: str, *, base_url: str = "") -> str:
    """A readable markdown approximation of a page.

    Not a full HTML→MD converter — headings, paragraphs and list items, which is what
    downstream text processing actually consumes. A provider that returns native
    markdown is always preferred; this is the fallback so every provider yields the
    same shape.
    """
    parser = _PageParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:      # noqa: BLE001 - malformed markup must not raise
        logger.debug("markdown conversion hit malformed HTML", exc_info=True)

    lines: list[str] = []
    if parser.title:
        lines.append(f"# {_clean(parser.title)}\n")
    for level, text in parser.headings:
        lines.append(f"{'#' * min(level + 1, 6)} {text}")
    body = parser.text
    if body:
        lines.append("")
        lines.append(body)
    return _BLANKS.sub("\n\n", "\n".join(lines)).strip()


def extract(
    html: str,
    *,
    url: str = "",
    include_html: bool = False,
    include_markdown: bool = True,
    provider: str = "",
    status_code: int = 200,
) -> "PageContent":
    """Parse HTML into a :class:`PageContent`. Never raises on malformed markup."""
    from backend.crawling.schemas import PageContent

    parser = _PageParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:      # noqa: BLE001
        logger.debug("extraction hit malformed HTML for %s", url, exc_info=True)

    meta = dict(parser.meta)
    description = (meta.get("description") or meta.get("og:description")
                   or meta.get("twitter:description") or "")
    title = _clean(parser.title) or _clean(meta.get("og:title", ""))
    canonical = parser.canonical or meta.get("og:url", "")
    if canonical and url:
        canonical = urljoin(url, canonical)
    if parser.json_ld:
        meta["json_ld"] = parser.json_ld

    return PageContent(
        url=url,
        canonical_url=canonical or url,
        status_code=status_code,
        title=title[:500],
        description=_clean(description)[:2000],
        markdown=to_markdown(html, base_url=url) if include_markdown else "",
        html=html if include_html else "",
        text=parser.text,
        headings=tuple(text for _level, text in parser.headings),
        links=absolute_links(parser.links, url or ""),
        metadata=meta,
        language=parser.language,
        provider=provider,
    )
