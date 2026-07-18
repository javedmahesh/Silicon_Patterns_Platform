"""Cached normalization + the company-owned field policy for historical sync.

Two responsibilities, both about *not doing work twice*:

1. **Cached canonicalization.** A historical export carries one company across
   dozens of contact rows, so :func:`normalize_domain` / :func:`name_key` would be
   recomputed dozens of times. These pure functions are wrapped in a process-level
   LRU cache here (never on the shared ``integration.normalizer`` hot path, whose
   purity we don't want to change). Call :func:`clear_caches` in tests.

2. **The company-owned field allowlist.** Historical Excel may only ever touch
   *company-owned descriptive* columns. Everything the platform derives or earns —
   lead scores, signals, ML features, review state, tiers, confidence — is off
   limits and lives in other tables or in :data:`PLATFORM_OWNED_FIELDS`.
"""
from __future__ import annotations

import re
from functools import lru_cache

from integration.normalizer import (
    canonical_company_id as _canonical_company_id,
    name_key as _name_key,
    normalize_domain as _normalize_domain,
)

_WS_RE = re.compile(r"\s+")

# Domains that must never be used as a company join key (PK). A website of
# ``linkedin.com/company/x`` or a personal mailbox is not a company identity.
JUNK_DOMAINS: frozenset[str] = frozenset({
    "linkedin.com", "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "icloud.com", "aol.com", "protonmail.com", "live.com", "me.com",
    "facebook.com", "twitter.com", "x.com", "crunchbase.com",
})

# Descriptive, company-owned columns that a historical import is allowed to write.
# These are the ONLY fields the sync engine will ever propose changing on an
# existing company row.
COMPANY_OWNED_FIELDS: tuple[str, ...] = (
    "company_name", "website", "company_linkedin", "country", "city",
    "headquarters", "industry_category", "sub_category", "technology_focus",
    "company_type", "founded_year", "description",
)

# Platform-owned / derived / earned — NEVER touched by an import. Listed explicitly
# so the guard is auditable (and a test can assert none of these ever appear in a
# proposed change). Lead scores, signals, ML features and reviews live in separate
# tables and are likewise never referenced by the engine.
PLATFORM_OWNED_FIELDS: frozenset[str] = frozenset({
    "canonical_company_id", "name_key", "compliance_flag", "prospect_type",
    "company_tier", "company_status", "confidence_score", "validation_status",
    "is_stub", "created_at", "updated_at", "source", "source_type",
    "discovery_date",
})

# Descriptive, decision-maker-owned columns a historical import may write. Everything
# the platform earns or a human curates is excluded (see DM_PRESERVED_FIELDS) — plus
# all of a DM's outreach/engagement/lead-score/ML/AI data lives in OTHER tables the
# engine never references, so it is preserved by construction.
DM_OWNED_FIELDS: tuple[str, ...] = (
    "first_name", "last_name", "full_name", "current_title", "seniority",
    "functional_area", "work_email", "work_phone", "city", "state_region",
    "country", "headline", "location", "organization_website", "organization_linkedin",
)

# DM columns the platform sets/earns — never overwritten by an import (auditable guard).
DM_PRESERVED_FIELDS: frozenset[str] = frozenset({
    "match_score", "agent_score", "agent_reasoning", "status", "profile_data",
    "source", "captured_at", "ingested_at", "email_status", "resolved_company_name",
})

# Sentinels that mean "no value" (see company_sync); shared by both engines.
VALUE_SENTINELS: frozenset[str] = frozenset({"", "unknown", "pending", "n/a", "na", "none"})


def canonical_email(raw) -> str:
    """Lower-cased, trimmed email — or ``""`` if it isn't a plausible address."""
    s = clean_text(raw).lower()
    if "@" not in s:
        return ""
    local, _, domain = s.rpartition("@")
    return s if (local and "." in domain) else ""


@lru_cache(maxsize=8192)
def norm_person_name(raw: str | None) -> str:
    """Match key for a person's name: lower-case, punctuation→space, collapse, trim."""
    if not raw:
        return ""
    import re as _re
    return _WS_RE.sub(" ", _re.sub(r"[^a-z0-9]+", " ", str(raw).lower())).strip()


@lru_cache(maxsize=8192)
def norm_title(raw: str | None) -> str:
    """Match key for a job title: lower-case, punctuation→space, collapse, trim."""
    return norm_person_name(raw)


def clean_text(value) -> str:
    """Whitespace-normalize a cell: strip nbsp/newline/tab, collapse runs, trim."""
    if value is None:
        return ""
    s = str(value).replace("\xa0", " ").replace("​", "")
    return _WS_RE.sub(" ", s).strip()


@lru_cache(maxsize=8192)
def cached_normalize_domain(raw: str | None) -> str:
    return _normalize_domain(raw)


@lru_cache(maxsize=8192)
def cached_name_key(name: str | None) -> str:
    return _name_key(name)


@lru_cache(maxsize=8192)
def cached_canonical_id(domain: str | None, name: str | None = "") -> str:
    return _canonical_company_id(domain, name)


def usable_domain(raw: str | None) -> str:
    """Normalized registrable domain, or ``""`` when it is missing/junk (a
    LinkedIn URL, a personal mailbox, a social profile) — i.e. not a company PK."""
    d = cached_normalize_domain(raw)
    return "" if (not d or d in JUNK_DOMAINS) else d


def clear_caches() -> None:
    cached_normalize_domain.cache_clear()
    cached_name_key.cache_clear()
    cached_canonical_id.cache_clear()
    norm_person_name.cache_clear()
    norm_title.cache_clear()
