"""Canonical normalization + validation of discovery candidates.

Everything a source returns passes through here before any decision is made about
it, so two providers reporting the same company in different shapes ("Acme Semi,
Inc." / "https://ACME-SEMI.com/about") converge on identical values. That
convergence is what makes duplicate detection work without fuzzy matching.

Reuses :mod:`integration.normalizer` — the platform already defines what a
registrable domain and a ``name_key`` are, and discovery must not invent a second
answer.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import replace

from integration.competitors import is_excluded_domain
from integration.normalizer import domain_from_url, is_valid_domain, normalize_domain
from backend.market_discovery.schemas import DiscoveryCandidate, ValidationIssue

# Suffixes stripped when building a comparison key. Legal form differs between
# registries for the same company ("Acme Inc" vs "Acme B.V."), so it cannot be part
# of identity. Kept separate from integration.normalizer.name_key, which is the
# platform-wide key — this is only used for candidate-level grouping.
_LEGAL_SUFFIXES = (
    "incorporated", "corporation", "limited", "holdings", "group",
    "inc", "llc", "ltd", "plc", "gmbh", "bv", "nv", "ab", "as", "oy", "sa", "srl",
    "spa", "pte", "pty", "kk", "co", "corp", "kft", "sas", "sarl", "ag", "aps",
    "pvt", "private", "public", "technologies", "technology",
)
_LINKEDIN_COMPANY = re.compile(r"linkedin\.com/(?:company|school)/([^/?#]+)", re.I)
_YEAR = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
_WS = re.compile(r"\s+")


def clean_text(value: str | None, *, limit: int = 0) -> str:
    out = _WS.sub(" ", (value or "").replace(" ", " ")).strip()
    return out[:limit] if limit and len(out) > limit else out


def normalize_website(value: str | None) -> str:
    """A bare ``https://<registrable-domain>`` or empty.

    Reducing to the registrable domain is what lets "acme.com/about",
    "www.acme.com" and "http://ACME.com" collapse to one identity.
    """
    domain = normalize_domain(value) or domain_from_url(value)
    return f"https://{domain}" if domain and is_valid_domain(domain) else ""


def normalize_linkedin(value: str | None) -> str:
    """Canonical ``https://www.linkedin.com/company/<slug>`` or empty."""
    m = _LINKEDIN_COMPANY.search(value or "")
    if not m:
        return ""
    slug = m.group(1).strip().lower().rstrip("/")
    return f"https://www.linkedin.com/company/{slug}" if slug else ""


def normalize_founded_year(value: str | int | None) -> str:
    m = _YEAR.search(str(value or ""))
    return m.group(1) if m else ""


def normalize_tokens(values) -> tuple[str, ...]:
    """De-duplicated, lower-cased, order-preserving token tuple."""
    out: list[str] = []
    for v in values or ():
        for part in re.split(r"[,;|/]", str(v)):
            token = clean_text(part).lower()
            if token and token not in out:
                out.append(token)
    return tuple(out)


def comparison_name(company_name: str | None) -> str:
    """Name reduced for comparison: lower-cased, punctuation and legal form removed.

    ``"Acme Semiconductor, Inc."`` and ``"acme semiconductor"`` produce the same key,
    which is what the resolver groups on when no domain is available.
    """
    flat = re.sub(r"[^a-z0-9 ]+", " ", (company_name or "").lower())
    words = [w for w in flat.split() if w]
    while words and words[-1] in _LEGAL_SUFFIXES:
        words.pop()
    return " ".join(words)


def candidate_key(candidate: DiscoveryCandidate) -> str:
    """Stable identity for a candidate, in descending order of trust.

    Domain first (strongest), then the LinkedIn company slug, then the comparison
    name. Hashing keeps the key a fixed width for storage and indexing while staying
    deterministic — the same candidate always produces the same key, on any machine,
    in any run. That determinism is what makes the pipeline reproducible.
    """
    domain = normalize_domain(candidate.website) or normalize_domain(candidate.company_domain)
    if domain:
        basis = f"domain:{domain}"
    elif candidate.linkedin_url:
        basis = f"linkedin:{normalize_linkedin(candidate.linkedin_url)}"
    else:
        name = comparison_name(candidate.company_name)
        basis = f"name:{name}" if name else ""
    if not basis:
        return ""
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:32]


def normalize_candidate(candidate: DiscoveryCandidate) -> DiscoveryCandidate:
    """Return a canonical copy. Pure — the input is never mutated."""
    website = normalize_website(candidate.website)
    domain = normalize_domain(website) or normalize_domain(candidate.company_domain)
    out = replace(
        candidate,
        company_name=clean_text(candidate.company_name, limit=255),
        website=website,
        company_domain=domain,
        linkedin_url=normalize_linkedin(candidate.linkedin_url),
        description=clean_text(candidate.description, limit=4000),
        industry=clean_text(candidate.industry, limit=120),
        headquarters=clean_text(candidate.headquarters, limit=255),
        country=clean_text(candidate.country, limit=120),
        founded_year=normalize_founded_year(candidate.founded_year),
        employee_count=clean_text(candidate.employee_count, limit=40),
        funding_stage=clean_text(candidate.funding_stage, limit=60).lower(),
        technologies=normalize_tokens(candidate.technologies),
        markets=normalize_tokens(candidate.markets),
        source=clean_text(candidate.source, limit=60).lower(),
        source_id=clean_text(candidate.source_id, limit=255),
        source_url=clean_text(candidate.source_url, limit=512),
    )
    out.candidate_key = candidate_key(out)
    return out


def validate_candidate(candidate: DiscoveryCandidate) -> list[ValidationIssue]:
    """Business-rule validation. Empty list means the candidate may proceed.

    This is engine policy, deliberately not a source's decision — every provider is
    held to exactly the same bar.
    """
    issues: list[ValidationIssue] = []
    if not candidate.company_name:
        issues.append(ValidationIssue("company_name", "missing"))
    elif len(comparison_name(candidate.company_name)) < 2:
        issues.append(ValidationIssue("company_name", "too short to identify a company"))
    if not candidate.candidate_key:
        issues.append(ValidationIssue("candidate_key",
                                      "no usable identity (needs a domain, LinkedIn URL or name)"))
    if candidate.website and not is_valid_domain(normalize_domain(candidate.website)):
        issues.append(ValidationIssue("website", "not a valid registrable domain"))
    # The platform must never ingest a competitor, whatever surfaced it.
    if candidate.company_domain and is_excluded_domain(candidate.company_domain):
        issues.append(ValidationIssue("company_domain", "excluded competitor domain"))
    if not candidate.source:
        issues.append(ValidationIssue("source", "missing provenance"))
    return issues
