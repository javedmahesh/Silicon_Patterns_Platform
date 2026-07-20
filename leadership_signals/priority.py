"""Reusable priority routing for leadership (and future) signals.

Business rule (Task viii / leadership phase 2):

* Startup / emerging companies — relevant movement is HIGH priority globally.
* Large / established companies — HIGH priority primarily when the movement is
  India-relevant (leadership based in India, or an Indian design/R&D/engineering/
  procurement/sourcing site). Unrelated overseas movement at a large company stays
  collectible but ranks lower — never discarded.

Deliberately company-classification-driven (``Company.company_tier``), never
name-hardcoded. Pure functions, no DB access, so callable from any future signal
type (e.g. the New Project Intelligence phase) without new plumbing.
"""
from __future__ import annotations

import re

# City/region -> canonical display label. Extend freely (additive).
_INDIA_LOCATIONS: dict[str, str] = {
    "bengaluru": "Bengaluru", "bangalore": "Bengaluru", "hyderabad": "Hyderabad",
    "noida": "Noida", "chennai": "Chennai", "pune": "Pune", "gujarat": "Gujarat",
    "ahmedabad": "Gujarat", "gandhinagar": "Gujarat", "delhi": "Delhi",
    "gurugram": "Gurugram", "gurgaon": "Gurugram", "mumbai": "Mumbai",
}
_STARTUP_TIERS = frozenset({"STARTUP", "SCALEUP"})
_LARGE_TIERS = frozenset({"ESTABLISHED", "INCUMBENT"})


def extract_geography(text: str | None) -> str:
    """Best-effort location for priority routing (India-city-aware text signal, not
    a geocoder). Empty when nothing recognizable is present — never fabricated."""
    low = (text or "").lower()
    for needle, city in _INDIA_LOCATIONS.items():
        if re.search(rf"\b{re.escape(needle)}\b", low):
            return f"{city}, India"
    if re.search(r"\bindia(n)?\b", low):
        return "India"
    return ""


def is_india_relevant(geography: str | None) -> bool:
    return "india" in (geography or "").lower()


def priority_tier(company_tier: str | None, geography: str | None) -> str:
    """('high'|'medium'|'low') — the reusable priority metadata for a signal.

    startup/scaleup company -> high (globally relevant movement matters early).
    India-relevant movement -> high, regardless of company size.
    established/incumbent company with no India relevance -> low (kept, deprioritized).
    unknown company tier and no India signal -> medium (neither over- nor under-claimed).
    """
    tier = (company_tier or "").upper()
    if tier in _STARTUP_TIERS:
        return "high"
    if is_india_relevant(geography):
        return "high"
    if tier in _LARGE_TIERS:
        return "low"
    return "medium"
