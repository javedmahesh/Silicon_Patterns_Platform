"""Reusable LinkedIn URL canonicalization.

Two LinkedIn URLs that point at the same profile must compare equal regardless of
protocol, ``www``/``m.``/country subdomain, locale path, trailing slash, query string
or fragment, or percent-encoding case. Phase-1 audit showed the platform stored only
lightly-normalized URLs (``split('?')[0].lower()``), which is why an exact-string match
found zero overlap; the sync engine canonicalizes *both* sides through this one
function at match time.

    >>> canonical_linkedin_url("https://www.LinkedIn.com/in/John-Doe/?locale=en_US")
    'linkedin.com/in/john-doe'
    >>> canonical_linkedin_url("http://m.linkedin.com/in/john-doe")
    'linkedin.com/in/john-doe'
    >>> canonical_linkedin_url("https://de.linkedin.com/in/john-doe/en")
    'linkedin.com/in/john-doe'
"""
from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

# path segment that introduces the identifying slug -> its normalized marker
_PROFILE_MARKERS = {"in": "in", "pub": "in", "profile": "in",
                    "company": "company", "school": "school"}
_LOCALE_SEG = re.compile(r"^[a-z]{2}(?:-[a-z]{2})?$")   # e.g. "en", "en-us", "de"


def linkedin_slug(raw: str | None) -> tuple[str, str] | None:
    """Return ``(marker, slug)`` for a LinkedIn URL, or ``None`` if it isn't one."""
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if "//" not in s:
        s = "//" + s                       # let urlsplit find the host on a bare URL
    parts = urlsplit(s)
    host = parts.netloc.split("@")[-1].split(":")[0].lower().strip(".")
    if not host.endswith("linkedin.com"):
        return None
    segments = [seg for seg in parts.path.split("/") if seg]
    # drop a leading locale segment ("/de/in/..." or "/en/...")
    if segments and _LOCALE_SEG.match(segments[0].lower()) and segments[0].lower() not in _PROFILE_MARKERS:
        segments = segments[1:]
    for i, seg in enumerate(segments):
        marker = _PROFILE_MARKERS.get(seg.lower())
        if marker and i + 1 < len(segments):
            slug = unquote(segments[i + 1]).strip().lower()
            slug = re.sub(r"\s+", "-", slug)
            return (marker, slug) if slug else None
    return None


def canonical_linkedin_url(raw: str | None) -> str:
    """Canonical ``linkedin.com/<marker>/<slug>`` form, or ``""`` if not a profile URL."""
    parsed = linkedin_slug(raw)
    if parsed is None:
        return ""
    marker, slug = parsed
    return f"linkedin.com/{marker}/{slug}"
