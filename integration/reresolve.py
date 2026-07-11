"""Re-resolve already-imported decision makers against the current alias layer.

After seeding employer companies/aliases, the 246 decision makers already in the
master DB (imported with a NULL ``company_domain``) can be matched without going
back to Supabase. This is the local, credential-free equivalent of re-running the
LinkedIn import: it re-resolves each unmatched person by their stored
``resolved_company_name`` and, on a hit, attaches the domain and closes the
person's pending review-queue entry (status -> 'merged').

Resolution here is **read-only against the alias/company tables** (direct
``company_aliases`` lookup, then the resolver's read-only fuzzy fallback) so it
never adds new review rows — it only resolves and closes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from integration.normalizer import name_key
from integration.resolver import CompanyResolver
from master_db.models import CompanyAlias, DecisionMaker, ResolutionReviewQueue


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class ReresolveStats:
    total: int
    matched_before: int
    matched_after: int
    newly_matched: int
    still_unresolved: int
    review_closed: int


def _lookup_domain(session: Session, resolver: CompanyResolver, employer: str, enable_fuzzy: bool) -> str | None:
    """Resolve an employer name to a company_domain with NO side effects."""
    key = name_key(employer)
    if not key:
        return None
    alias = session.scalar(select(CompanyAlias).where(CompanyAlias.name_key == key))
    if alias is not None:
        return alias.company_domain
    if enable_fuzzy:
        hit = resolver._fuzzy_find(key)  # read-only similarity search
        if hit is not None:
            return hit[0]
    return None


def reresolve_decision_makers(
    session: Session, *, resolver: CompanyResolver | None = None, enable_fuzzy: bool = True
) -> ReresolveStats:
    resolver = resolver or CompanyResolver(session)
    dms = session.scalars(select(DecisionMaker)).all()
    total = len(dms)
    matched_before = sum(1 for d in dms if d.company_domain)

    newly = 0
    closed = 0
    for dm in dms:
        if dm.company_domain or not dm.resolved_company_name:
            continue
        domain = _lookup_domain(session, resolver, dm.resolved_company_name, enable_fuzzy)
        if not domain:
            continue
        dm.company_domain = domain
        newly += 1
        # Close this person's stale pending review item (matched on the contact's url).
        item = session.scalar(
            select(ResolutionReviewQueue).where(
                ResolutionReviewQueue.source_engine == "linkedin",
                ResolutionReviewQueue.source_record_ref == dm.linkedin_url,
                ResolutionReviewQueue.status == "pending",
            )
        )
        if item is not None:
            item.status = "merged"
            item.resolved_domain = domain
            item.reviewed_at = _utcnow()
            closed += 1

    session.commit()
    matched_after = matched_before + newly
    return ReresolveStats(
        total=total,
        matched_before=matched_before,
        matched_after=matched_after,
        newly_matched=newly,
        still_unresolved=total - matched_after,
        review_closed=closed,
    )
