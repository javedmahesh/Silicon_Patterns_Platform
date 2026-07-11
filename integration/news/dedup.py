"""Intelligent deduplication for the News Collection Engine.

Replaces URL-only dedup with a multi-signal match:

  * **canonical URL**   — scheme/host normalized, tracking params + fragment stripped,
  * **normalized title**— lowercased, de-punctuated, publisher suffix removed,
  * **semantic similarity** — ``difflib`` ratio over normalized titles (stdlib, no deps),
  * **company resolution** — same resolved ``company_domain``,
  * **publication time** — within a day window,
  * **extracted entities**— an entity/type/company/time-bucket fingerprint.

Rule: *different business events for the same company stay separate* (the fingerprint
includes the opportunity type + salient entities), while *the same event reported by
several outlets collapses to one opportunity* (all reporting sources are attached to it).
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from urllib.parse import urlparse, urlunparse

_TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "mc_", "ref", "ref_", "cmpid", "spm")
_PUBLISHER_SPLIT = re.compile(r"\s+[\|–—>-]\s+")   # " - ", " | ", " – ", " — "
_WORD = re.compile(r"[a-z0-9]+")
_TITLE_SIM_THRESHOLD = 0.82        # normalized-title similarity that counts as "same story"
_DUP_WINDOW_DAYS = 4               # same company + type within N days = same event


def canonical_url(url: str) -> str:
    """Normalize a URL for dedup: lowercase scheme+host, drop ``www.``, strip tracking
    query params + fragment, drop a trailing slash. Empty in -> empty out."""
    url = (url or "").strip()
    if not url:
        return ""
    if "://" not in url:
        url = "http://" + url
    try:
        p = urlparse(url)
    except ValueError:
        return url.lower()
    host = (p.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    kept = []
    for pair in (p.query or "").split("&"):
        if not pair:
            continue
        key = pair.split("=", 1)[0].lower()
        if any(key == pfx or key.startswith(pfx) for pfx in _TRACKING_PREFIXES):
            continue
        kept.append(pair)
    path = p.path.rstrip("/") or ""
    return urlunparse(("https", host, path, "", "&".join(sorted(kept)), "")).lower()


def normalize_title(title: str) -> str:
    """Lowercase, drop a trailing publisher segment, keep alnum words only."""
    t = (title or "").strip()
    if not t:
        return ""
    parts = _PUBLISHER_SPLIT.split(t)
    if len(parts) > 1 and len(parts[-1]) <= 40:  # "... - EE Times" -> drop the outlet
        t = " ".join(parts[:-1])
    return " ".join(_WORD.findall(t.lower()))


def title_similarity(a: str, b: str) -> float:
    """0..1 similarity of two *normalized* titles (semantic-ish, token-order aware)."""
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def _time_bucket(published_at: str, *, days: int = _DUP_WINDOW_DAYS) -> str:
    """Coarse time bucket so the same event dated a day apart shares a fingerprint."""
    dt = _parse_date(published_at)
    if dt is None:
        return "na"
    epoch_days = int(dt.timestamp() // 86400)
    return str(epoch_days // max(1, days))


def _parse_date(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    # RFC-822 (RSS pubDate), ISO-8601 (Atom), plus common long/short human dates.
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y/%m/%d",
                "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", value)
    if m:
        return datetime(int(m[1]), int(m[2]), int(m[3]), tzinfo=timezone.utc)
    return None


def entity_fingerprint(company_domain: str, opportunity_type: str,
                       entities: list[str], published_at: str = "") -> str:
    """Stable fingerprint of a *business event*: company + type + salient entities +
    coarse time bucket. Two articles about the same event hash equal; two different
    events for the same company (different type/entities) do not."""
    ents = sorted({e.strip().lower() for e in (entities or []) if e and e.strip()})[:6]
    base = "|".join([
        (company_domain or "").lower(),
        (opportunity_type or "").upper(),
        ",".join(ents),
        _time_bucket(published_at),
    ])
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:24]


def content_hash(canonical: str, normalized_title: str) -> str:
    """Article-level dedup key (one row per distinct canonical-url+title)."""
    return hashlib.sha1(f"{canonical}|{normalized_title}".encode("utf-8")).hexdigest()[:32]


def is_same_event(*, company_domain: str, opportunity_type: str, title: str,
                  published_at: str, other_title: str, other_published_at: str,
                  same_company: bool) -> bool:
    """True when two candidate events should collapse into one opportunity.

    Same company + same type is required; then EITHER the titles are semantically
    similar OR they fall in the same publication-time window (co-reporting of one
    event). Different type or different company -> always separate.
    """
    if not same_company:
        return False
    if title_similarity(title, other_title) >= _TITLE_SIM_THRESHOLD:
        return True
    a, b = _parse_date(published_at), _parse_date(other_published_at)
    if a is not None and b is not None:
        return abs((a - b).days) <= _DUP_WINDOW_DAYS and title_similarity(title, other_title) >= 0.6
    return False
