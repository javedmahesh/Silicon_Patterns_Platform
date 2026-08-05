"""NVIDIA case-study page parsing.

Pure functions over :class:`~backend.crawling.schemas.PageContent`. Given a page,
return raw field dicts. No database, no crawling, no judgement about whether a
company matters — the connector maps these onto the discovery schema and the Market
Discovery Engine decides everything else.

The selectors here were verified against live pages rather than assumed. NVIDIA
case studies are server-rendered and publish, consistently:

* ``<title>`` — either ``"<Company> | NVIDIA Customer Stories"`` or
  ``"<Company> <headline> | NVIDIA"``;
* ``meta[name=description]`` — a real one-line description;
* ``meta[name=keywords]`` — the technology areas, plus boilerplate to strip;
* one external link to the company's own site (absent on older studies).

A missing value is left absent rather than guessed: an invented one would reach the
engine's confidence model as if it were evidence.
"""
from __future__ import annotations

import logging
import re
from html import unescape
from typing import Any
from urllib.parse import urlparse

from backend.crawling.schemas import PageContent
from backend.market_discovery.sources.nvidia_inception.config import CASE_STUDY_PREFIX

logger = logging.getLogger("market_discovery.nvidia_inception.parser")

_CASE_STUDY_SLUG = re.compile(r"/case-studies/([A-Za-z0-9][A-Za-z0-9._-]*)/?$")
#: Boilerplate NVIDIA appends to titles and keyword lists. Stripping it is what
#: separates the company's own vocabulary from the publisher's.
_TITLE_SUFFIXES = re.compile(
    r"(?i)\s*\|\s*(?:nvidia(?:\s+customer\s+stories)?|customer\s+stories)\s*$")
_BOILERPLATE_KEYWORDS = frozenset({
    "nvidia customer stories", "customer stories", "case study", "case studies",
    "nvidia", "customer story",
})
#: Hosts that are never a company's own website.
_NON_COMPANY_HOSTS = (
    "nvidia.com", "nvidia.cn", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "youtube.com", "youtu.be", "linkedin.com", "github.com", "spotify.com",
    "enable-javascript.com", "a16z.com", "medium.com", "reddit.com", "tiktok.com",
)
#: A company name is short. Longer pre-pipe text is a headline, not a name, so the
#: slug becomes the better source.
_MAX_NAME_WORDS = 4
_WS = re.compile(r"\s+")


def _clean(value: str | None) -> str:
    """Collapse whitespace and decode HTML entities.

    Meta attribute values arrive escaped ("R&amp;D"), unlike element text, so this
    has to happen explicitly or the entity reaches the database verbatim.
    """
    return _WS.sub(" ", unescape(value or "")).strip()


def case_study_slug(url: str) -> str:
    """``.../case-studies/baseten/`` → ``baseten``; ``""`` when not a case study."""
    try:
        path = urlparse(url).path
    except ValueError:
        return ""
    match = _CASE_STUDY_SLUG.search(path.rstrip("/") or "/")
    slug = match.group(1) if match else ""
    # The index itself matches the pattern's shape; it is not a company.
    return "" if slug in ("case-studies",) else slug


def case_study_links(page: PageContent) -> list[str]:
    """Case-study URLs on an index page, de-duplicated, first-seen order kept."""
    out: list[str] = []
    seen: set[str] = set()
    for link in page.links or ():
        slug = case_study_slug(link)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        out.append(link)
    return out


def filter_case_study_urls(urls, *, base_url: str = "") -> list[str]:
    """Keep only case-study detail URLs (used against a sitemap's full URL list)."""
    out: list[str] = []
    seen: set[str] = set()
    for url in urls or ():
        if CASE_STUDY_PREFIX not in (url or ""):
            continue
        slug = case_study_slug(url)
        if not slug or slug in seen:
            continue
        if base_url and not url.startswith(base_url):
            continue
        seen.add(slug)
        out.append(url)
    return out


def _company_name(title: str, slug: str) -> tuple[str, bool]:
    """``(name, is_certain)`` from published values only.

    Titles come in two shapes. ``"Lightwheel | NVIDIA Customer Stories"`` puts the
    name first, so the pre-pipe text is the name. ``"Serve Robotics Autonomous
    Sidewalk Delivery | NVIDIA"`` puts a headline there — too long to be a name, so
    the URL slug is the better published signal.

    On some studies BOTH are headlines ("Virtual Human Meets Virtual Studio..."), and
    NVIDIA simply does not publish the company's name anywhere on the page. Those
    return ``is_certain=False`` so the connector can flag the candidate instead of
    presenting a headline as though it were a name.
    """
    head = _clean(_TITLE_SUFFIXES.sub("", title or "")).split("|")[0].strip()
    if head and len(head.split()) <= _MAX_NAME_WORDS:
        return head, True
    from_slug = " ".join(word.capitalize()
                         for word in (slug or "").replace("_", "-").split("-") if word)
    if from_slug and len(from_slug.split()) <= _MAX_NAME_WORDS:
        return from_slug, True
    return (from_slug or head), False


def _technologies(keywords: str, *, company_name: str, slug: str = "") -> tuple[str, ...]:
    """Technology areas from the keywords meta, minus everything that is not one.

    Three kinds of non-technology routinely appear in this field and are removed:

    * publisher boilerplate ("NVIDIA Customer Stories");
    * the company's own name — identity, not a technology;
    * the page's URL slug. Some studies put ONLY the slug here
      ("paving-the-future-of-factories-with-nvidia-omniverse-enterprise"), which
      would otherwise land in the candidate as if it were a technology area.
    """
    out: list[str] = []
    name_key = _clean(company_name).lower()
    slug_key = (slug or "").strip().lower()
    slug_words = slug_key.replace("-", " ").replace("_", " ").strip()
    for part in (keywords or "").split(","):
        token = _clean(part)
        low = token.lower()
        if not token or low in _BOILERPLATE_KEYWORDS or low == name_key:
            continue
        if low.startswith("nvidia customer"):
            continue
        # The slug, in either its hyphenated or spaced form.
        if slug_key and (low == slug_key or low == slug_words):
            continue
        # A hyphenated multi-word token is a URL fragment, not a keyword a human wrote.
        if "-" in low and " " not in low and len(low.split("-")) >= 3:
            continue
        if token not in out:
            out.append(token)
    return tuple(out)


def _company_website(page: PageContent, *, company_name: str, slug: str) -> str:
    """The company's own site, when the study links to it.

    Only accepted when the host echoes the company's name or slug. NVIDIA case
    studies link to plenty of third parties — a partner's product page, an unrelated
    research demo — and the first external link is regularly one of those. A wrong
    website is worse than none: it would resolve the candidate to another company
    entirely.
    """
    tokens = {t for t in re.split(r"[^a-z0-9]+", (company_name or "").lower()) if len(t) > 2}
    tokens |= {t for t in re.split(r"[^a-z0-9]+", (slug or "").lower()) if len(t) > 2}
    if not tokens:
        return ""
    best = ""
    for link in page.links or ():
        try:
            parsed = urlparse(link)
        except ValueError:
            continue
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in ("http", "https") or not host:
            continue
        if any(host == bad or host.endswith("." + bad) for bad in _NON_COMPANY_HOSTS):
            continue
        label = host.split(":")[0]
        for prefix in ("www.",):
            label = label[len(prefix):] if label.startswith(prefix) else label
        registrable = label.split(".")[0]
        # The domain must actually correspond to the company — "serverobotics" for
        # "Serve Robotics", "lightwheel" for "Lightwheel".
        collapsed = re.sub(r"[^a-z0-9]", "", (company_name or "").lower())
        matches_name = bool(collapsed) and (
            collapsed.startswith(registrable) or registrable.startswith(collapsed))
        if not (registrable in tokens or matches_name):
            continue
        depth = len([p for p in (parsed.path or "/").split("/") if p])
        if depth == 0:
            return link                      # a bare homepage is the ideal answer
        best = best or f"{parsed.scheme}://{parsed.netloc}/"
    return best


def parse_case_study(page: PageContent) -> dict[str, Any]:
    """One case-study page → raw fields. Absent when not published."""
    raw: dict[str, Any] = {}
    meta = page.metadata or {}
    slug = case_study_slug(page.canonical_url) or case_study_slug(page.url)
    if slug:
        raw["slug"] = slug
        raw["source_url"] = page.canonical_url or page.url

    title = page.title or str(meta.get("og:title") or "")
    name, name_certain = _company_name(title, slug)
    if name:
        raw["company_name"] = name
    if name and not name_certain:
        # The page published a headline, not a name. Recorded so a reviewer (and any
        # later enrichment) knows this field is weak rather than authoritative.
        raw["name_uncertain"] = True

    description = _clean(str(meta.get("description") or page.description
                             or meta.get("og:description") or ""))
    # NVIDIA uses a generic og:description ("Read this customer story and more.") on
    # some studies; that describes the page, not the company.
    if description and description.lower() != "read this customer story and more.":
        raw["description"] = description

    website = _company_website(page, company_name=name, slug=slug)
    if website:
        raw["website"] = website

    technologies = _technologies(str(meta.get("keywords") or ""),
                                 company_name=name, slug=slug)
    if technologies:
        raw["technologies"] = list(technologies)
    # Deliberately NO industry: the keyword list is dominated by NVIDIA product names
    # ("NVIDIA Omniverse", "Google Cloud"), which are not industries. Labelling those
    # as one would be a fabricated value flowing into the engine as evidence.

    headline = _clean(_TITLE_SUFFIXES.sub("", str(meta.get("og:title") or "")))
    if headline and headline != name:
        raw["headline"] = headline
    if page.headings:
        raw["headings"] = list(page.headings[:20])
    return raw


def parse_index_page(page: PageContent) -> list[dict[str, Any]]:
    """An index/showcase page → one raw record per case study linked from it."""
    return [{"slug": case_study_slug(link), "source_url": link}
            for link in case_study_links(page)]
