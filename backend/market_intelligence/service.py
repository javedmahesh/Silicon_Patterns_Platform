"""Market Intelligence Layer — the public entry point and the only writer.

    run_market_intelligence(session, settings) -> IntelligenceResult

The layer reads discovery candidates, interprets them, and writes what it concluded.
It is the *only* module in the intelligence subsystem that touches the database; the
pipeline below it is a pure function, which is what keeps every conclusion
reproducible from the candidate and the rule pack alone.

What it deliberately does not do: create companies, change lead scores, or write back
to ``discovery_candidates``. Interpretation is additive. Promotion from candidate to
``companies`` row remains a separate, reviewable step, and lead scoring keeps its own
model — this layer supplies intelligence to it rather than overriding it.

Incremental by default: a candidate whose ``last_seen`` predates its stored
``evaluated_at`` is already interpreted and is skipped, so a nightly run costs almost
nothing after the first. ``SP_INTELLIGENCE_REPROCESS_ALL`` is the way to roll a rule
change over existing data.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.market_discovery.models import from_record as candidate_from_record
from backend.market_discovery.schemas import DiscoveryCandidate
from backend.market_intelligence import models
from backend.market_intelligence.config import IntelligenceConfig
from backend.market_intelligence.pipeline import IntelligencePipeline
from backend.market_intelligence.schemas import IntelligenceResult, PRIORITY_ORDER, RuleKind

logger = logging.getLogger("market_intelligence.service")


def _run_id(now: datetime) -> str:
    return now.strftime("intelligence-%Y%m%d-%H%M%S-") + f"{now.microsecond:06d}"


def run_market_intelligence(
    session: Session,
    settings,
    *,
    run_id: str = "",
    config: IntelligenceConfig | None = None,
    candidates: list[DiscoveryCandidate] | None = None,
    persist: bool = True,
) -> IntelligenceResult:
    """Interpret pending discovery candidates and persist the result.

    Never raises: an evaluation failure is recorded on the result, and a write failure
    is logged without discarding the (already computed) intelligence. The scheduler
    treats this as a normal pipeline stage.
    """
    now = datetime.now(timezone.utc)
    rid = run_id or _run_id(now)
    cfg = config or IntelligenceConfig.from_settings(settings)

    if not cfg.enabled:
        logger.info("[intelligence] disabled (SP_INTELLIGENCE_ENABLED=false)")
        return IntelligenceResult(run_id=rid, started_at=now, finished_at=now)

    if cfg.log_level:
        _apply_log_level(cfg.log_level)

    pending, skipped = ((candidates, 0) if candidates is not None
                        else _pending(session, cfg))
    result = IntelligencePipeline(cfg).run(pending, run_id=rid, now=now, skipped=skipped)

    if persist and result.records:
        try:
            _persist(session, result)
        except Exception:      # noqa: BLE001 - findings survive a write failure
            logger.error("[intelligence] persisting run %s failed", rid, exc_info=True)
            session.rollback()
    return result


def _pending(session: Session, config: IntelligenceConfig) -> tuple[list[DiscoveryCandidate], int]:
    """Candidates needing interpretation, plus how many were already up to date.

    Two queries for the whole run: one for the candidate rows, one for the stored
    evaluation timestamps. The comparison itself happens in memory, so adding a
    thousand candidates does not add a thousand round trips.
    """
    limit = config.max_candidates if config.max_candidates > 0 else 0
    rows = models.candidates_for_intelligence(session, limit=limit)
    if not rows:
        return [], 0

    evaluated = {} if config.reprocess_all else models.evaluated_at_by_key(session)
    pending: list[DiscoveryCandidate] = []
    skipped = 0
    for row in rows:
        previous = evaluated.get(row.candidate_key)
        if previous is not None and not _changed_since(row.last_seen, previous):
            skipped += 1
            continue
        pending.append(candidate_from_record(row))
        if config.batch_size > 0 and len(pending) >= config.batch_size:
            break
    logger.info("[intelligence] %d candidate(s) pending, %d already current",
                len(pending), skipped)
    return pending, skipped


def _changed_since(last_seen: datetime | None, evaluated_at: datetime | None) -> bool:
    """Has the candidate been seen since it was last interpreted?

    Naive timestamps come back from SQLite; comparing them to an aware value raises,
    so both sides are normalized to UTC first. An unreadable pair is treated as
    changed — re-interpreting costs a few milliseconds, whereas skipping wrongly means
    an interpretation silently never updates.
    """
    if last_seen is None or evaluated_at is None:
        return True
    def aware(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return aware(last_seen) > aware(evaluated_at)


def _persist(session: Session, result: IntelligenceResult) -> None:
    """Write the run's interpretations. One batched lookup, then inserts/updates."""
    keys = [r.candidate_key for r in result.records if r.candidate_key]
    existing = models.records_by_key(session, keys)      # 1 query, not 1 per record

    created = updated = 0
    for record in result.records:
        if not record.candidate_key:
            continue
        _row, was_created = models.upsert_record(
            session, record, existing=existing.get(record.candidate_key))
        created += was_created
        updated += not was_created
    session.commit()
    logger.info("[intelligence] run %s persisted: %d created, %d refreshed",
                result.run_id, created, updated)


def _apply_log_level(level: str) -> None:
    """Set the layer's log level from configuration, ignoring an unknown value."""
    resolved = logging.getLevelName(level.strip().upper())
    if isinstance(resolved, int):
        logging.getLogger("market_intelligence").setLevel(resolved)
    else:
        logger.warning("[intelligence] unknown log level %r (ignored)", level)


def intelligence_health(session: Session, settings,
                        config: IntelligenceConfig | None = None) -> dict:
    """Layer configuration and stored-record counts, for status endpoints."""
    cfg = config or IntelligenceConfig.from_settings(settings)
    pack = cfg.pack
    counts = models.priority_counts(session)
    return {
        "enabled": cfg.enabled,
        "rule_pack": pack.name,
        "rule_pack_version": pack.version,
        "rules": {
            "total": len(pack.rules),
            "enabled": len(pack.enabled_keys),
            "classifications": len(pack.of_kind(RuleKind.CLASSIFICATION)),
            "technologies": len(pack.of_kind(RuleKind.TECHNOLOGY)),
            "signals": len(pack.of_kind(RuleKind.SIGNAL)),
        },
        "thresholds": dict(pack.thresholds),
        "weights": dict(pack.weights),
        "batch_size": cfg.batch_size,
        "max_candidates": cfg.max_candidates,
        "concurrency": cfg.concurrency,
        "records": {p.value: counts.get(p.value, 0) for p in PRIORITY_ORDER},
    }
