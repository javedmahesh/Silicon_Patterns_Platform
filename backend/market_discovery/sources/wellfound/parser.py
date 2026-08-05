"""Wellfound page parsing.

Pure functions over :class:`~backend.crawling.schemas.PageContent`. Given a page,
return raw field dicts. No database, no crawling, no judgement about whether a
company is interesting — the connector maps these onto the discovery schema and the
Market Discovery Engine decides everything else.

Parsing is defensive by construction. A third-party site's markup changes without
notice, so every extractor returns whatever it can and omits what it cannot find.
A missing field is left absent rather than guessed: an invented value would flow
into confidence scoring and corrupt a decision the engine is supposed to make from
evidence.
"""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

from backend.crawling.schemas import PageContent

logger = logging.getLogger("market_discovery.wellfound.parser")

_COMPANY_HREF = re.compile(r"/company/([A-Za-z0-9][A-Za-z0-9._-]*)/?$")
#: Wellfound renders sizes as "11-50 employees", "1001-5000", "51-200 people".
_EMPLOYEES = re.compile(r"\b(\d[\d,]*(?:\s*[-–]\s*\d[\d,]*)?|\d[\d,]*\+)\s*(?:employees|people)\b", re.I)
_FUNDING = re.compile(
    r"\b(pre-?seed|seed|series\s+[a-k]|angel|growth|late\s+stage|ipo|acquired|bootstrapped)\b", re.I)
_FOUNDED = re.compile(r"\bfounded\s+(?:in\s+)?((?:19|20)\d{2})\b", re.I)
#: Bot-protection interstitials. Detected so the connector can report an honest
#: "blocked" failure instead of parsing a challenge page into empty companies.
_CHALLENGE_MARKERS = (
    "captcha-delivery", "datadome", "please enable js", "just a moment",
    "enable javascript and cookies", "cf-browser-verification", "access denied",
)


def looks_blocked(page: PageContent | None) -> bool:
    """True when a page is a bot-protection challenge rather than real content.

    Worth detecting explicitly: a challenge page is HTTP 200-or-403 with a title and
    a body, so naive parsing yields "zero companies found" and hides the real cause
    from whoever is debugging an empty run.
    """
    if page is None:
        return False
    haystack = " ".join([page.title or "", page.text or "", page.html or ""]).lower()
    if not haystack.strip():
        return False
    return any(marker in haystack for marker in _CHALLENGE_MARKERS)


def company_slug(url: str) -> str:
    """``https://wellfound.com/company/acme`` → ``acme``; ``""`` when not a company URL."""
    try:
        path = urlparse(url).path
    except ValueError:
        return ""
    match = _COMPANY_HREF.match(path.rstrip("/") or "/")
    return match.group(1) if match else ""


def company_links(page: PageContent) -> list[str]:
    """Company-page URLs on a listing, de-duplicated, first-seen order preserved."""
    out: list[str] = []
    seen: set[str] = set()
    for link in page.links or ():
        slug = company_slug(link)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        out.append(link)
    return out


def _json_ld_organizations(page: PageContent) -> list[dict[str, Any]]:
    """Schema.org Organization blocks. The most reliable signal when present —
    it is structured data the site publishes deliberately."""
    blocks = page.metadata.get("json_ld") or []
    out: list[dict[str, Any]] = []
    for block in blocks if isinstance(blocks, list) else [blocks]:
        if not isinstance(block, dict):
            continue
        types = block.get("@type") or block.get("type") or ""
        types = types if isinstance(types, list) else [types]
        if any(str(t).lower() in ("organization", "corporation", "localbusiness")
               for t in types):
            out.append(block)
    return out


def _first(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _address(node: Any) -> str:
    """Flatten a schema.org PostalAddress (or a plain string) to one line."""
    if isinstance(node, str):
        return node.strip()
    if isinstance(node, dict):
        parts = [str(node.get(k, "") or "").strip()
                 for k in ("streetAddress", "addressLocality", "addressRegion",
                           "addressCountry", "postalCode")]
        return ", ".join(p for p in parts if p)
    return ""


def _country(node: Any) -> str:
    if isinstance(node, dict):
        country = node.get("addressCountry")
        if isinstance(country, dict):
            return str(country.get("name", "") or "").strip()
        return str(country or "").strip()
    return ""


def parse_company_page(page: PageContent) -> dict[str, Any]:
    """One company page → raw fields.

    Structured data first (JSON-LD, then OpenGraph, then meta), falling back to the
    page's own text only for values Wellfound renders as prose (size, stage, founding
    year). Anything not found is simply absent from the returned dict.
    """
    raw: dict[str, Any] = {}
    meta = page.metadata or {}
    slug = company_slug(page.canonical_url or page.url)
    if slug:
        raw["slug"] = slug
        raw["source_url"] = page.canonical_url or page.url

    orgs = _json_ld_organizations(page)
    org = orgs[0] if orgs else {}

    name = _first(org.get("name"), meta.get("og:site_name"), meta.get("og:title"), page.title)
    # Wellfound titles read "Acme — Jobs | Wellfound"; keep only the company part.
    name = re.split(r"\s+[—–|]\s+", name)[0].strip() if name else ""
    if name:
        raw["company_name"] = name

    website = _first(org.get("url"), meta.get("og:url"))
    # og:url on a Wellfound page points back at Wellfound, which is provenance, not
    # the company's own site — never report it as the company website.
    if website and "wellfound.com" not in website.lower():
        raw["website"] = website

    for link in page.links or ():
        host = (urlparse(link).hostname or "").lower()
        if "linkedin.com/company/" in link.lower():
            raw.setdefault("linkedin_url", link)
        elif ("wellfound.com" not in host and host and "website" not in raw
              and _looks_like_homepage(link)):
            raw["website"] = link

    description = _first(org.get("description"), meta.get("og:description"),
                         meta.get("description"), page.description)
    if description:
        raw["description"] = description

    location = _first(_address(org.get("address")), meta.get("og:locality"))
    if location:
        raw["headquarters"] = location
    country = _country(org.get("address"))
    if country:
        raw["country"] = country

    body = " ".join([page.title or "", page.description or "", page.text or ""])
    employees = _EMPLOYEES.search(body)
    if employees:
        raw["employee_count"] = employees.group(1).strip()
    funding = _FUNDING.search(body)
    if funding:
        raw["funding_stage"] = funding.group(1).strip().lower()
    founded = _FOUNDED.search(body)
    if founded:
        raw["founded_year"] = founded.group(1)

    industry = _first(org.get("industry"), meta.get("article:section"))
    if industry:
        raw["industry"] = industry
    # Headings are the section labels a company page uses for its own markets/tech.
    if page.headings:
        raw["headings"] = list(page.headings[:20])
    return raw


def _looks_like_homepage(url: str) -> bool:
    """A bare domain (or one shallow path) — a company's site, not a deep link."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host or host.endswith((
        "twitter.com", "x.com", "facebook.com", "instagram.com", "youtube.com",
        "github.com", "medium.com", "crunchbase.com", "angel.co", "linkedin.com",
    )):
        return False
    return len([p for p in (parsed.path or "/").split("/") if p]) <= 1


def parse_listing_page(page: PageContent) -> list[dict[str, Any]]:
    """A startup listing → one raw record per company link found.

    Listings are a discovery surface, not a data surface: they yield the slug and
    whatever the card shows. The connector optionally fetches each company page for
    the rest.
    """
    out: list[dict[str, Any]] = []
    for link in company_links(page):
        slug = company_slug(link)
        record: dict[str, Any] = {"slug": slug, "source_url": link}
        # A listing card's anchor text is usually the company name. Only trust it
        # when it looks like one — never fabricate from a slug.
        label = _label_for(page, link)
        if label:
            record["company_name"] = label
        out.append(record)
    return out


def _label_for(page: PageContent, link: str) -> str:
    """Best-effort company name for a listing entry, from a matching heading."""
    slug = company_slug(link)
    if not slug:
        return ""
    normalized = slug.replace("-", " ").replace("_", " ").strip().lower()
    for heading in page.headings or ():
        if heading.strip().lower() == normalized:
            return heading.strip()
    return ""
