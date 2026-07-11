"""Competitor exclusion policy — domains/prospect-types the platform must never store.

Service providers (IT / design-services firms) are the team's competitors; the
platform neither ingests nor keeps them. The excluded *domains* are derived from the
``SERVICE_PROVIDER`` entries in ``config/employer_seeds.json`` so that seed file stays
the single source of truth (no second list to maintain).

Used by the resolver (refuse to stub a competitor domain), the Industry ingestor
(skip competitor rows), the employer-seed loader (skip competitor seeds), and the
purge script.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

from config.enums import EXCLUDED_PROSPECT_TYPES, normalize_prospect_type
from integration.normalizer import normalize_domain

_SEEDS = Path(__file__).resolve().parent.parent / "config" / "employer_seeds.json"


@functools.lru_cache(maxsize=1)
def excluded_domains() -> frozenset[str]:
    """Normalized domains of known competitor (excluded prospect_type) employers."""
    try:
        data = json.loads(_SEEDS.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return frozenset()
    out: set[str] = set()
    for entry in data.get("companies", []):
        if normalize_prospect_type(entry.get("prospect_type")) in EXCLUDED_PROSPECT_TYPES:
            domain = normalize_domain(entry.get("domain", ""))
            if domain:
                out.add(domain)
    return frozenset(out)


def is_excluded_domain(domain: str | None) -> bool:
    """True if *domain* is a known competitor domain (never store it)."""
    return bool(domain) and normalize_domain(domain) in excluded_domains()
