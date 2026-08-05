"""Persistence for the Market Discovery Engine.

One new table, ``discovery_candidates``, and it earns its place: a candidate is not
a company. It may never become one (unresolved, below threshold, later rejected),
and writing every sighting into ``companies`` would fill the canonical table with
speculative rows. The engine needs somewhere to remember what it has already seen so
a nightly run can tell "new" from "seen yesterday" — that is cross-run state no
existing table holds.

Everything else is reused rather than duplicated:

* ``companies`` — the canonical record, written only via the existing resolver when
  a candidate is promoted. Discovery never writes company fields directly.
* ``company_sources`` — per-source provenance, already modelled and indexed.
* ``resolution_review_queue`` — the existing home for "a human should look at this".

The ORM class itself lives in :mod:`master_db.models` (one metadata registry, one
migration stream for the whole platform); this module re-exports it and holds the
repository helpers so callers never reach into ``master_db`` for discovery concerns.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.market_discovery.schemas import DiscoveryCandidate
from master_db.models import CompanySource, DiscoveryCandidateRecord

__all__ = [
    "CompanySource",
    "DiscoveryCandidateRecord",
    "get_candidate",
    "candidates_by_key",
    "upsert_candidate",
    "record_company_source",
    "status_counts",
    "known_identities",
    "recent_candidates",
    "to_record_values",
    "from_record",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_record_values(candidate: DiscoveryCandidate, *, confidence: float | None = None) -> dict:
    """Flatten a candidate into column values.

    Collections are stored as JSON text rather than a JSON column so the table
    behaves identically on SQLite (dev/tests) and Postgres (production) — the engine
    never queries inside them, so there is nothing to gain from a native type.
    """
    return {
        "candidate_key": candidate.candidate_key,
        "company_name": candidate.company_name[:255],
        "company_domain": candidate.company_domain[:255],
        "website": candidate.website[:512],
        "linkedin_url": candidate.linkedin_url[:512],
        "description": candidate.description,
        "industry": candidate.industry[:120],
        "headquarters": candidate.headquarters[:255],
        "country": candidate.country[:120],
        "founded_year": candidate.founded_year[:8],
        "employee_count": candidate.employee_count[:40],
        "funding_stage": candidate.funding_stage[:60],
        "technologies": json.dumps(list(candidate.technologies)),
        "markets": json.dumps(list(candidate.markets)),
        "source": candidate.source[:60],
        "source_id": candidate.source_id[:255],
        "source_url": candidate.source_url[:512],
        "sources": json.dumps(list(candidate.sources)),
        "confidence": float(candidate.confidence if confidence is None else confidence),
        "raw_payload": json.dumps(candidate.raw_payload, default=str)[:60000],
        "metadata_json": json.dumps(
            {k: v for k, v in candidate.metadata.items() if k != "sources"}, default=str
        )[:20000],
    }


def from_record(record: DiscoveryCandidateRecord) -> DiscoveryCandidate:
    """Rebuild a candidate from its row (for re-scoring without re-fetching)."""
    def loads(value, fallback):
        try:
            return json.loads(value) if value else fallback
        except (TypeError, ValueError):
            return fallback

    metadata = loads(record.metadata_json, {})
    metadata["sources"] = tuple(loads(record.sources, []))
    return DiscoveryCandidate(
        company_name=record.company_name, website=record.website,
        linkedin_url=record.linkedin_url, description=record.description,
        industry=record.industry, headquarters=record.headquarters, country=record.country,
        founded_year=record.founded_year, employee_count=record.employee_count,
        funding_stage=record.funding_stage,
        technologies=tuple(loads(record.technologies, [])),
        markets=tuple(loads(record.markets, [])),
        source=record.source, source_id=record.source_id, source_url=record.source_url,
        first_seen=record.first_seen, last_seen=record.last_seen,
        confidence=record.confidence, raw_payload=loads(record.raw_payload, {}),
        metadata=metadata, company_domain=record.company_domain,
        candidate_key=record.candidate_key,
    )


# ------------------------------------------------------------------ queries
def get_candidate(session: Session, candidate_key: str) -> DiscoveryCandidateRecord | None:
    return session.scalar(
        select(DiscoveryCandidateRecord)
        .where(DiscoveryCandidateRecord.candidate_key == candidate_key)
    )


def candidates_by_key(session: Session, keys: list[str]) -> dict[str, DiscoveryCandidateRecord]:
    """Batch lookup — one query for a whole run's keys, never one per candidate."""
    if not keys:
        return {}
    rows = session.scalars(
        select(DiscoveryCandidateRecord)
        .where(DiscoveryCandidateRecord.candidate_key.in_(keys))
    )
    return {r.candidate_key: r for r in rows}


def known_identities(session: Session) -> tuple[frozenset[str], dict[str, frozenset[str]]]:
    """Everything already stored, in both forms a source might hold up front.

    Returns ``(candidate_keys, {source: source_ids})``. A connector usually knows only
    the provider's own id at listing time (a Wellfound slug); the candidate key is
    derived from the company's domain, which is learned later from a detail page — so
    both indexes are needed for incremental discovery to actually skip anything.

    One scan of three indexed columns per run. The engine passes the result to sources
    through the context, which is what keeps a source from ever running a query.
    """
    rows = session.execute(select(
        DiscoveryCandidateRecord.candidate_key,
        DiscoveryCandidateRecord.source,
        DiscoveryCandidateRecord.source_id,
    )).all()
    keys: set[str] = set()
    by_source: dict[str, set[str]] = {}
    for candidate_key, source, source_id in rows:
        if candidate_key:
            keys.add(candidate_key)
        if source and source_id:
            by_source.setdefault(source, set()).add(source_id)
    return frozenset(keys), {k: frozenset(v) for k, v in by_source.items()}


def status_counts(session: Session) -> dict[str, int]:
    return dict(session.execute(
        select(DiscoveryCandidateRecord.status, func.count())
        .group_by(DiscoveryCandidateRecord.status)
    ).all())


def recent_candidates(session: Session, *, limit: int = 50,
                      status: str | None = None) -> list[DiscoveryCandidateRecord]:
    q = select(DiscoveryCandidateRecord).order_by(DiscoveryCandidateRecord.last_seen.desc())
    if status:
        q = q.where(DiscoveryCandidateRecord.status == status)
    return list(session.scalars(q.limit(limit)))


# ------------------------------------------------------------------ writes
def upsert_candidate(
    session: Session,
    candidate: DiscoveryCandidate,
    *,
    status: str,
    run_id: str = "",
    existing: DiscoveryCandidateRecord | None = None,
) -> tuple[DiscoveryCandidateRecord, bool]:
    """Insert or refresh one candidate row. Returns ``(record, created)``.

    ``first_seen`` is never overwritten — it is the answer to "when did the platform
    first hear about this company", which a later sighting must not rewrite.
    """
    values = to_record_values(candidate)
    record = existing if existing is not None else get_candidate(session, candidate.candidate_key)
    if record is None:
        record = DiscoveryCandidateRecord(
            **values, status=status, run_id=run_id,
            first_seen=candidate.first_seen or _utcnow(),
            last_seen=candidate.last_seen or _utcnow(),
            times_seen=1,
        )
        session.add(record)
        return record, True

    for key, value in values.items():
        setattr(record, key, value)
    record.status = status
    record.run_id = run_id
    record.last_seen = candidate.last_seen or _utcnow()
    record.times_seen = (record.times_seen or 0) + 1
    return record, False


def record_company_source(
    session: Session, *, company_domain: str, source_name: str,
    source_type: str = "market_discovery", source_url: str = "", source_tier: int = 50,
) -> CompanySource | None:
    """Provenance for a promoted candidate, idempotent on (domain, source).

    Reuses the existing ``company_sources`` table — the platform already models
    "which source surfaced this company", and discovery must not invent a parallel one.
    """
    if not company_domain or not source_name:
        return None
    existing = session.scalar(
        select(CompanySource).where(
            CompanySource.company_domain == company_domain,
            CompanySource.source_name == source_name,
        )
    )
    if existing is not None:
        return existing
    row = CompanySource(
        company_domain=company_domain, source_name=source_name[:255],
        source_type=source_type[:60], source_url=(source_url or "")[:512],
        source_tier=source_tier,
    )
    session.add(row)
    return row
