"""Canonical normalization — the single source of truth for the master join key.

Every record entering the master database is keyed on ``company_domain``. The
four engines each compute this differently:

  * Industry Discovery  -> ``core.utils.get_domain``
  * Blog Crawler        -> ``silicon_patterns_blogcrawler.utils.get_domain``
  * Career Scraper      -> ``core.enrichment.company_domain``

and they disagree on edge cases (``www`` stripping, ports, multi-label TLDs such
as ``.co.uk``). They also compute ``canonical_company_id`` two different ways
(Industry/Blog emit the token ``GROQ``; Career emits the bare domain ``groq.com``).

This module replaces all of that with ONE implementation so the join key never
fragments. It is pure (no I/O, no DB, no network, no third-party deps) and is
safe to import and run offline.

    >>> normalize_domain("https://www.Groq.com/careers?utm=x")
    'groq.com'
    >>> normalize_domain("careers.acme.co.uk")
    'acme.co.uk'
    >>> canonical_company_id("groq.com", "Groq Inc.")
    'GROQ'
    >>> name_key("Groq, Inc.")
    'groq'
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from config.public_suffixes import MULTI_LABEL_SUFFIXES

# Legal/structural suffix words stripped when building a name key so that
# "Groq", "Groq Inc.", "GROQ" and "Groq Technologies" all collapse to "groq".
_LEGAL_SUFFIX_RE = re.compile(
    r"\b(?:inc|incorporated|corp|corporation|co|company|ltd|limited|llc|lp|llp|"
    r"gmbh|plc|sa|sas|ag|nv|bv|oy|ab|srl|spa|pte|pvt|private|holdings|group|"
    r"technologies|technology|labs|laboratories|systems|solutions|"
    r"semiconductors?|semi|microelectronics|electronics)\b"
)
_WS_RE = re.compile(r"\s+")
_HOST_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$")
# Subdomains that are never part of the registrable identity of a company site.
_STRIP_SUBDOMAINS = ("www", "www2", "m", "careers", "jobs", "blog", "news", "investors")


def normalize_domain(raw: str | None) -> str:
    """Reduce any company signal (URL, host, bare domain, or email) to its
    canonical registrable domain — the platform-wide join key.

    Returns ``""`` when *raw* yields no plausible domain (callers treat an empty
    domain as "no key", never as a wildcard match).
    """
    if not raw:
        return ""
    s = raw.strip().lower()
    if not s:
        return ""

    # Email address -> take the part after the last "@".
    if "@" in s and "//" not in s:
        s = s.rsplit("@", 1)[-1]

    # urlsplit needs a scheme to populate netloc; synthesize one if absent so a
    # bare "groq.com/careers" still parses to host "groq.com".
    netloc = urlsplit(s if "//" in s else f"//{s}").netloc
    host = netloc.split("@")[-1].split(":")[0].strip().strip(".")
    if not host or "." not in host:
        return ""

    host = _strip_known_subdomains(host)
    reg = registrable_domain(host)
    return reg if is_valid_domain(reg) else ""


def _strip_known_subdomains(host: str) -> str:
    """Drop a single leading boilerplate subdomain (``www.``/``careers.``/…).

    Only one level is removed; ``registrable_domain`` does the rest. We never
    strip a label that would leave fewer than two labels.
    """
    parts = host.split(".")
    if len(parts) > 2 and parts[0] in _STRIP_SUBDOMAINS:
        parts = parts[1:]
    return ".".join(parts)


def registrable_domain(host: str) -> str:
    """Return the registrable domain for *host*, honoring multi-label public
    suffixes (``acme.co.uk`` -> ``acme.co.uk``, not ``co.uk``).

    Swap this single function for a full-PSL implementation later without
    touching any caller.
    """
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    last_two = ".".join(labels[-2:])
    if last_two in MULTI_LABEL_SUFFIXES:
        return ".".join(labels[-3:])
    return last_two


def is_valid_domain(domain: str) -> bool:
    """True when *domain* looks like a real lowercase host (``a.b`` form, valid
    label chars, has a dot). Used as a guard before persisting a join key and as
    the basis for the DB ``CHECK`` constraint on ``companies.company_domain``."""
    return bool(domain) and bool(_HOST_RE.match(domain))


def domain_from_url(url: str | None) -> str:
    """Explicit alias for URL inputs (delegates to :func:`normalize_domain`)."""
    return normalize_domain(url)


def domain_from_email(email: str | None) -> str:
    """Registrable domain of an email address, or ``""``."""
    if not email or "@" not in email:
        return ""
    return normalize_domain(email.rsplit("@", 1)[-1])


def name_key(company_name: str | None) -> str:
    """Normalized matching key for a company name.

    Lower-cases, strips legal/structural suffix words, drops punctuation and
    collapses whitespace, so "Groq", "Groq Inc." and "GROQ" share the key
    ``"groq"``. This is what :mod:`integration.resolver` matches aliases on.
    """
    if not company_name:
        return ""
    low = company_name.lower()
    low = re.sub(r"[.,/&]+", " ", low)
    low = _LEGAL_SUFFIX_RE.sub(" ", low)
    low = re.sub(r"[^a-z0-9 ]+", " ", low)
    return _WS_RE.sub(" ", low).strip()


def canonical_company_id(company_domain: str | None, company_name: str | None = "") -> str:
    """The ONE canonical id used across the platform.

    Reconciles the engines' two implementations by always preferring the
    domain-derived uppercase token (Industry/Blog style): ``groq.com`` ->
    ``GROQ``. Falls back to the name key (upper-cased, de-spaced) only when there
    is no usable domain. Deterministic and stable across runs.
    """
    domain = normalize_domain(company_domain) if company_domain else ""
    if domain:
        core = domain.split(".")[0]
        token = re.sub(r"[^a-z0-9]", "", core.lower()).upper()
        if token:
            return token
    return re.sub(r"[^A-Z0-9]", "", name_key(company_name).upper())
