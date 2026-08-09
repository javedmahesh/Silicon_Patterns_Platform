"""Market Discovery Engine — the public entry point and the only writer.

The engine is the single source of truth for discovery business logic. Sources
provide data; this module decides what any of it means and is the *only* place in
the discovery subsystem that touches the database.

    run_discovery(session, settings) -> DiscoveryResult

What it does, in order: run the pipeline (pure), persist what the pipeline decided,
and record provenance for anything that maps onto a known company. What it
deliberately does not do: create companies. Promotion from candidate to
``companies`` row is a separate, reviewable step — an automatic discovery run must
not be able to silently expand the canonical company table.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.market_discovery import models
from backend.market_discovery.pipeline import DiscoveryPipeline, PipelineConfig
from backend.market_discovery.registry import SourceRegistry, registry as default_registry
from backend.market_discovery.resolver import DiscoveryResolver
from backend.market_discovery.schemas import CandidateStatus, DiscoveryResult

logger = logging.getLogger("market_discovery.service")

#: Candidate statuses worth remembering between runs. A rejected candidate is not
#: persisted — it failed validation, carries no usable identity, and storing it would
#: only grow the table with noise the engine already knows to discard.
_PERSISTED = (
    CandidateStatus.NEW, CandidateStatus.UPDATED, CandidateStatus.BELOW_THRESHOLD,
)


def _run_id(now: datetime) -> str:
    return now.strftime("discovery-%Y%m%d-%H%M%S-") + f"{now.microsecond:06d}"


def run_discovery(
    session: Session,
    settings,
    *,
    run_id: str = "",
    since: datetime | None = None,
    registry: SourceRegistry | None = None,
    persist: bool = True,
) -> DiscoveryResult:
    """Execute one discovery pass and persist its outcome.

    Never raises: a failing source is recorded on the result, and a persistence error
    is logged without discarding the (already computed) result. The scheduler treats
    this as a normal pipeline stage.
    """
    now = datetime.now(timezone.utc)
    rid = run_id or _run_id(now)

    if not getattr(settings, "discovery_enabled", True):
        logger.info("[discovery] disabled (SP_DISCOVERY_ENABLED=false)")
        return DiscoveryResult(run_id=rid, started_at=now, finished_at=now)

    config = PipelineConfig.from_settings(settings)
    reg = registry if registry is not None else default_registry
    pipeline = DiscoveryPipeline(
        config=config, registry=reg, session=session,
        resolver=DiscoveryResolver(session),
    )
    result = pipeline.run(run_id=rid, now=now, since=since)

    if persist:
        try:
            _persist(session, result)
        except Exception:      # noqa: BLE001 - the run's findings survive a write failure
            logger.error("[discovery] persisting run %s failed", rid, exc_info=True)
            session.rollback()
    return result


def _persist(session: Session, result: DiscoveryResult) -> None:
    """Write the run's candidates. One batched lookup, then inserts/updates.

    Duplicates are not written as their own rows — they were merged into the group's
    surviving candidate, which is the row that gets refreshed.
    """
    persistable = [p for p in result.processed if p.status in _PERSISTED]
    if not persistable:
        logger.info("[discovery] run %s: nothing to persist", result.run_id)
        return

    keys = [p.candidate.candidate_key for p in persistable if p.candidate.candidate_key]
    existing = models.candidates_by_key(session, keys)      # 1 query, not 1 per candidate

    created = updated = 0
    for processed in persistable:
        candidate = processed.candidate
        if not candidate.candidate_key:
            continue
        _record, was_created = models.upsert_candidate(
            session, candidate,
            status=processed.status.value,
            run_id=result.run_id,
            existing=existing.get(candidate.candidate_key),
        )
        created += was_created
        updated += not was_created
        # Provenance only for a candidate the resolver matched to an EXISTING company:
        # company_sources FKs to companies, and a candidate's own company_domain is
        # merely what its website claims, not proof a company row exists.
        if processed.resolved_company_domain and processed.accepted:
            for source_name in candidate.sources:
                models.record_company_source(
                    session, company_domain=processed.resolved_company_domain,
                    source_name=source_name, source_url=candidate.source_url,
                )
    session.commit()
    logger.info("[discovery] run %s persisted: %d created, %d refreshed",
                result.run_id, created, updated)


def discovery_health(session: Session, settings, *, registry: SourceRegistry | None = None) -> dict:
    """Registry + engine health for the scheduler status endpoint and diagnostics."""
    reg = registry if registry is not None else default_registry
    enabled = getattr(settings, "discovery_sources", []) or []
    health = reg.health(enabled)
    missing = reg.missing_sources(enabled)
    return {
        "enabled": bool(getattr(settings, "discovery_enabled", True)),
        "registered_sources": reg.names(),
        "enabled_sources": [s.name for s in reg.enabled_sources(enabled)],
        # Configured names no connector answers to. Non-empty here is the reason a run
        # reports zero sources, and the one thing an operator cannot infer from the rest.
        "misconfigured_sources": {name: reg.suggest(name) for name in missing},
        "sources": {
            name: {"status": h.status.value, "detail": h.detail} for name, h in health.items()
        },
        "capabilities": {
            name: {
                "provides": sorted(caps.provides),
                "supports_incremental": caps.supports_incremental,
                "requires_credentials": caps.requires_credentials,
                "rate_limit_per_minute": caps.rate_limit_per_minute,
                "description": caps.description,
            }
            for name, caps in reg.capabilities().items()
        },
        "confidence_threshold": getattr(settings, "discovery_confidence_threshold", 0.45),
        "candidates": models.status_counts(session),
    }
