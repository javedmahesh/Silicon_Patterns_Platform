"""Persistence for the Market Intelligence Layer.

One new table, ``market_intelligence``, and it earns its place: an interpretation is
not a sighting. ``discovery_candidates`` records *what the platform saw*; this
records *what the platform concluded*, and the two change for different reasons — a
rule-pack change re-derives every interpretation while touching no candidate.

Everything else is reused rather than duplicated:

* ``discovery_candidates`` — the input, read-only from here.
* ``companies`` — the canonical record. Intelligence never promotes a candidate;
  that stays a separate, reviewable step.
* ``lead_scores`` — untouched. This layer feeds lead scoring, it does not replace it.

The ORM class lives in :mod:`master_db.models` (one metadata registry, one migration
stream for the whole platform); this module re-exports it and holds the repository
helpers, so callers never reach into ``master_db`` for intelligence concerns.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.market_intelligence.schemas import MarketIntelligence
from master_db.models import DiscoveryCandidateRecord, MarketIntelligenceRecord

__all__ = [
    "MarketIntelligenceRecord",
    "get_record",
    "records_by_key",
    "upsert_record",
    "priority_counts",
    "recent_records",
    "evaluated_at_by_key",
    "candidates_for_intelligence",
    "to_record_values",
]

#: Candidate statuses worth interpreting. A rejected candidate never reached the
#: store, and a duplicate was merged into the row that survives — interpreting it
#: again would produce a second opinion about one company.
INTERPRETABLE_STATUSES: tuple[str, ...] = ("new", "updated", "below_threshold", "promoted")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_record_values(record: MarketIntelligence) -> dict:
    """Flatten an intelligence record into column values.

    Collections are stored as JSON text rather than JSON columns so the table behaves
    identically on SQLite (dev/tests) and Postgres; nothing queries inside them, so a
    native type would buy nothing.
    """
    return {
        "candidate_key": record.candidate_key,
        "company_name": record.company_name[:255],
        "company_domain": record.company_domain[:255],
        "website": record.website[:512],
        "source": record.source[:60],
        "primary_classification": record.primary_classification[:120],
        "classifications": json.dumps([c.as_dict() for c in record.classifications]),
        "technologies": json.dumps([t.as_dict() for t in record.technologies]),
        "signals": json.dumps([s.as_dict() for s in record.signals]),
        "signal_types": json.dumps(list(record.signal_types)),
        "classification_count": len(record.classifications),
        "technology_count": len(record.technologies),
        "signal_count": len(record.signals),
        "priority": record.priority.value,
        "priority_score": float(record.priority_score),
        "confidence": float(record.confidence),
        "factors": json.dumps([f.as_dict() for f in record.factors]),
        "reasons": json.dumps(list(record.reasons)),
        "explanation": record.explanation[:20000],
        "rule_pack": record.rule_pack[:60],
        "rule_pack_version": record.rule_pack_version[:40],
        "enrichment": json.dumps(record.enrichment, default=str)[:20000],
        "run_id": record.run_id[:80],
        "evaluated_at": record.evaluated_at or _utcnow(),
    }


# ------------------------------------------------------------------ queries
def get_record(session: Session, candidate_key: str) -> MarketIntelligenceRecord | None:
    return session.scalar(
        select(MarketIntelligenceRecord)
        .where(MarketIntelligenceRecord.candidate_key == candidate_key)
    )


def records_by_key(session: Session, keys: list[str]) -> dict[str, MarketIntelligenceRecord]:
    """Batch lookup — one query for a whole run's keys, never one per record."""
    if not keys:
        return {}
    rows = session.scalars(
        select(MarketIntelligenceRecord)
        .where(MarketIntelligenceRecord.candidate_key.in_(keys))
    )
    return {r.candidate_key: r for r in rows}


def evaluated_at_by_key(session: Session) -> dict[str, datetime]:
    """When each candidate was last interpreted. One scan of two indexed columns.

    This is what makes an incremental run cheap: the service compares it against each
    candidate's ``last_seen`` and skips everything unchanged, without loading a single
    stored interpretation.
    """
    rows = session.execute(select(
        MarketIntelligenceRecord.candidate_key, MarketIntelligenceRecord.evaluated_at,
    )).all()
    return {key: value for key, value in rows if key}


def candidates_for_intelligence(
    session: Session, *, limit: int = 0,
    statuses: tuple[str, ...] = INTERPRETABLE_STATUSES,
) -> list[DiscoveryCandidateRecord]:
    """Candidates eligible for interpretation, most recently seen first.

    Ordered by ``last_seen`` then ``id`` so a bounded run always takes the freshest
    candidates and, when two share a timestamp, always takes them in the same order —
    a batch limit must not make a run non-reproducible.
    """
    query = (
        select(DiscoveryCandidateRecord)
        .where(DiscoveryCandidateRecord.status.in_(statuses))
        .order_by(DiscoveryCandidateRecord.last_seen.desc(),
                  DiscoveryCandidateRecord.id.desc())
    )
    if limit and limit > 0:
        query = query.limit(limit)
    return list(session.scalars(query))


def priority_counts(session: Session) -> dict[str, int]:
    return dict(session.execute(
        select(MarketIntelligenceRecord.priority, func.count())
        .group_by(MarketIntelligenceRecord.priority)
    ).all())


def recent_records(session: Session, *, limit: int = 50,
                   priority: str | None = None) -> list[MarketIntelligenceRecord]:
    query = (select(MarketIntelligenceRecord)
             .order_by(MarketIntelligenceRecord.priority_score.desc(),
                       MarketIntelligenceRecord.evaluated_at.desc()))
    if priority:
        query = query.where(MarketIntelligenceRecord.priority == priority)
    return list(session.scalars(query.limit(limit)))


# ------------------------------------------------------------------ writes
def upsert_record(
    session: Session,
    record: MarketIntelligence,
    *,
    existing: MarketIntelligenceRecord | None = None,
) -> tuple[MarketIntelligenceRecord, bool]:
    """Insert or replace one interpretation. Returns ``(row, created)``.

    A re-evaluation fully replaces the previous interpretation rather than merging
    into it: rules are deterministic, so the new result IS the answer for the current
    pack, and keeping fragments of an older pack's conclusions alongside it would make
    the row unexplainable.
    """
    values = to_record_values(record)
    row = existing if existing is not None else get_record(session, record.candidate_key)
    if row is None:
        row = MarketIntelligenceRecord(**values)
        session.add(row)
        return row, True
    for key, value in values.items():
        setattr(row, key, value)
    return row, False
