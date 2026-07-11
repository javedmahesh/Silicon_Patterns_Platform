"""Safe HTML sanitization for email preview — stdlib only, no extra dependencies."""
from __future__ import annotations

import re
from html.parser import HTMLParser

_VOID = frozenset(["area", "base", "br", "col", "hr", "img", "input", "link", "meta", "param",
                   "source", "track", "wbr"])
_ALLOWED_TAGS = frozenset([
    "a", "abbr", "b", "blockquote", "br", "caption", "code", "col", "colgroup", "del",
    "details", "div", "em", "figcaption", "figure", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "img", "ins", "li", "mark", "ol", "p", "pre", "s", "span", "strong",
    "sub", "summary", "sup", "table", "tbody", "td", "th", "thead", "tr", "u", "ul",
])
_ALLOWED_ATTRS: dict[str, set[str]] = {
    "a": {"href", "title", "target", "rel"},
    "img": {"src", "alt", "width", "height", "title"},
    "td": {"colspan", "rowspan", "align", "valign"},
    "th": {"colspan", "rowspan", "align", "valign", "scope"},
    "col": {"span", "width"},
    "colgroup": {"span"},
    "*": {"class", "id", "style", "dir", "lang"},
}
_BLOCKED_SCHEMES = re.compile(r"^\s*(javascript|vbscript|data)\s*:", re.I)
_STYLE_URL = re.compile(r"url\s*\(", re.I)
_EVENT_ATTR = re.compile(r"^on\w+", re.I)


def _allowed_url(url: str) -> bool:
    return not bool(_BLOCKED_SCHEMES.match(url))


def _safe_style(value: str) -> str:
    return "" if _STYLE_URL.search(value) else value


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._out: list[str] = []
        self._stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag not in _ALLOWED_TAGS:
            return
        safe_attrs: list[str] = []
        allowed = _ALLOWED_ATTRS.get(tag, set()) | _ALLOWED_ATTRS.get("*", set())
        for name, value in attrs:
            name = name.lower()
            if _EVENT_ATTR.match(name):
                continue
            if name not in allowed:
                continue
            val = value or ""
            if name == "href" and not _allowed_url(val):
                continue
            if name == "src" and not _allowed_url(val):
                continue
            if name == "style":
                val = _safe_style(val)
                if not val:
                    continue
            if name == "target" and val not in ("_blank", "_self", "_parent", "_top"):
                val = "_blank"
            safe_attrs.append(f' {name}="{val}"')
        self._out.append(f"<{tag}{''.join(safe_attrs)}>")
        if tag not in _VOID:
            self._stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag not in _ALLOWED_TAGS or tag in _VOID:
            return
        if tag in self._stack:
            # Close open children first
            while self._stack and self._stack[-1] != tag:
                self._out.append(f"</{self._stack.pop()}>")
            if self._stack:
                self._out.append(f"</{self._stack.pop()}>")

    def handle_data(self, data: str) -> None:
        self._out.append(data)

    def handle_entityref(self, name: str) -> None:
        self._out.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._out.append(f"&#{name};")

    def result(self) -> str:
        while self._stack:
            self._out.append(f"</{self._stack.pop()}>")
        return "".join(self._out)


def sanitize_html(html: str) -> str:
    """Strip unsafe HTML tags/attributes. Safe for rendering in an iframe sandbox."""
    if not html or not html.strip():
        return ""
    s = _Sanitizer()
    s.feed(html)
    return s.result()


def html_to_plain(html: str) -> str:
    """Strip all tags to produce a plain-text preview (no sanitization needed)."""
    if not html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
