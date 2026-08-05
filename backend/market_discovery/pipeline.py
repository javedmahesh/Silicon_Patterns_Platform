"""The discovery pipeline.

    sources → normalize → validate → resolve → confidence → DiscoveryResult

Deterministic by construction: the same candidates in, the same result out, every
time. Sources are fetched in name order (and, when run concurrently, their outputs
are re-ordered by source name before processing), grouping preserves first-sighting
order, and every downstream step is a pure function. Nothing depends on wall-clock
timing, dict iteration order, or which thread finished first.

The pipeline computes; it does not persist. Turning a result into rows is
:mod:`backend.market_discovery.service`, which keeps every database write in one
place — and keeps this module testable with no session at all.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.market_discovery import events
from backend.market_discovery.base_source import DiscoverySource
from backend.market_discovery.confidence import ConfidenceConfig, ConfidenceEngine
from backend.market_discovery.normalize import normalize_candidate, validate_candidate
from backend.market_discovery.registry import SourceRegistry, registry as default_registry
from backend.market_discovery.resolver import DiscoveryResolver
from backend.market_discovery.schemas import (
    CandidateStatus,
    DiscoveryCandidate,
    DiscoveryContext,
    DiscoveryResult,
    ProcessedCandidate,
    SourceOutcome,
    SourceStatus,
)

logger = logging.getLogger("market_discovery.pipeline")


@dataclass(slots=True)
class PipelineConfig:
    """Runtime knobs. Built from :class:`backend.config.Settings` in production."""

    enabled_sources: tuple[str, ...] = ()
    source_limit: int | None = 500
    concurrency: int = 4
    retry_count: int = 2
    retry_backoff_seconds: float = 2.0
    rate_limit_per_minute: int = 60
    source_timeout_seconds: int = 300
    confidence: ConfidenceConfig = None            # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.confidence is None:
            self.confidence = ConfidenceConfig()

    @classmethod
    def from_settings(cls, settings) -> "PipelineConfig":
        limit = getattr(settings, "discovery_source_limit", 500)
        return cls(
            enabled_sources=tuple(getattr(settings, "discovery_sources", ()) or ()),
            source_limit=limit or None,
            concurrency=getattr(settings, "discovery_concurrency", 4),
            retry_count=getattr(settings, "discovery_retry_count", 2),
            retry_backoff_seconds=getattr(settings, "discovery_retry_backoff_seconds", 2.0),
            rate_limit_per_minute=getattr(settings, "discovery_rate_limit_per_minute", 60),
            source_timeout_seconds=getattr(settings, "discovery_source_timeout_seconds", 300),
            confidence=ConfidenceConfig.from_settings(settings),
        )


class DiscoveryPipeline:
    """Runs one discovery pass over the enabled sources."""

    def __init__(
        self,
        *,
        config: PipelineConfig | None = None,
        registry: SourceRegistry | None = None,
        session: Session | None = None,
        resolver: DiscoveryResolver | None = None,
        confidence: ConfidenceEngine | None = None,
    ) -> None:
        self.config = config or PipelineConfig()
        self.registry = registry if registry is not None else default_registry
        self.session = session
        self.resolver = resolver or DiscoveryResolver(session)
        self.confidence = confidence or ConfidenceEngine(self.config.confidence)

    # ------------------------------------------------------------------ run
    def run(self, *, run_id: str = "", now: datetime | None = None,
            since: datetime | None = None) -> DiscoveryResult:
        """Execute the pipeline. Never raises — a failed source is recorded, not fatal."""
        started = now or datetime.now(timezone.utc)
        result = DiscoveryResult(run_id=run_id, started_at=started)
        clock = time.monotonic()

        runnable, skipped = self.registry.runnable_sources(self.config.enabled_sources)
        for health in skipped:
            result.sources.append(SourceOutcome(name=health.name, status=SourceStatus.UNAVAILABLE,
                                                error=health.detail))
        events.pipeline_started(run_id, len(runnable))

        if not runnable:
            # A run with zero sources is a valid, successful no-op — this is exactly
            # the state the framework ships in, before any connector exists.
            logger.info("[discovery] no runnable sources — nothing to do")
            result.finished_at = datetime.now(timezone.utc)
            result.duration_ms = int((time.monotonic() - clock) * 1000)
            events.pipeline_completed(run_id, result)
            return result

        known_keys, known_source_ids = self._known_identities()
        context = DiscoveryContext(run_id=run_id, since=since, now=started,
                                   limit=self.config.source_limit,
                                   known_candidate_keys=known_keys,
                                   known_source_ids=known_source_ids)
        candidates, outcomes = self._collect(runnable, context)
        result.sources.extend(outcomes)
        result.processed = self._process(candidates, run_id)

        result.finished_at = datetime.now(timezone.utc)
        result.duration_ms = int((time.monotonic() - clock) * 1000)
        logger.info("[discovery] pipeline %s finished in %dms: %s",
                    run_id or "-", result.duration_ms, result.summary())
        events.pipeline_completed(run_id, result)
        return result

    def _known_identities(self) -> tuple[frozenset[str], dict[str, frozenset[str]]]:
        """Already-stored identities, so a source can skip re-fetching them.

        Delegated to the persistence layer — the pipeline stays free of queries. Empty
        when there is no session or the read fails, which only costs a source its
        shortcut and never fails a run.
        """
        if self.session is None:
            return frozenset(), {}
        try:
            from backend.market_discovery import models

            return models.known_identities(self.session)
        except Exception:      # noqa: BLE001 - an optimisation, never a hard dependency
            logger.warning("[discovery] could not load known candidates", exc_info=True)
            return frozenset(), {}

    def _known_keys(self) -> frozenset[str]:
        """Backward-compatible accessor for the candidate-key index alone."""
        return self._known_identities()[0]

    # ------------------------------------------------------------------ collect
    def _collect(self, sources: list[DiscoverySource],
                 context: DiscoveryContext) -> tuple[list[DiscoveryCandidate], list[SourceOutcome]]:
        """Fetch from every source. Output is ordered by source name regardless of
        completion order, which is what keeps a concurrent run deterministic."""
        by_source: dict[str, list[DiscoveryCandidate]] = {}
        outcomes: dict[str, SourceOutcome] = {}

        if self.config.concurrency <= 1 or len(sources) == 1:
            for source in sources:
                cands, outcome = self._run_source(source, context)
                by_source[source.name] = cands
                outcomes[source.name] = outcome
        else:
            workers = min(self.config.concurrency, len(sources))
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="discovery") as pool:
                futures = {pool.submit(self._run_source, s, context): s for s in sources}
                for future in as_completed(futures):
                    source = futures[future]
                    try:
                        cands, outcome = future.result(timeout=self.config.source_timeout_seconds)
                    except Exception as exc:      # noqa: BLE001 - incl. timeout
                        cands = []
                        outcome = SourceOutcome(name=source.name, status=SourceStatus.UNAVAILABLE,
                                                error=str(exc)[:500])
                        events.source_failed(context.run_id, source.name, str(exc))
                    by_source[source.name] = cands
                    outcomes[source.name] = outcome

        ordered_names = sorted(by_source)
        candidates = [c for name in ordered_names for c in by_source[name]]
        return candidates, [outcomes[name] for name in ordered_names]

    def _run_source(self, source: DiscoverySource,
                    context: DiscoveryContext) -> tuple[list[DiscoveryCandidate], SourceOutcome]:
        """One source, with retries. Returns its candidates and how it went."""
        events.source_started(context.run_id, source.name)
        clock = time.monotonic()
        attempts = max(1, self.config.retry_count)
        last_error = ""
        for attempt in range(1, attempts + 1):
            try:
                candidates = source.discover(context)
                duration = int((time.monotonic() - clock) * 1000)
                events.source_completed(context.run_id, source.name, len(candidates), duration)
                return candidates, SourceOutcome(name=source.name, status=SourceStatus.OK,
                                                 fetched=len(candidates), duration_ms=duration)
            except Exception as exc:      # noqa: BLE001
                last_error = str(exc)[:500]
                logger.warning("[discovery] source %s attempt %d/%d failed: %s",
                               source.name, attempt, attempts, last_error, exc_info=True)
                if attempt < attempts and self.config.retry_backoff_seconds > 0:
                    time.sleep(self.config.retry_backoff_seconds)
        duration = int((time.monotonic() - clock) * 1000)
        events.source_failed(context.run_id, source.name, last_error)
        return [], SourceOutcome(name=source.name, status=SourceStatus.UNAVAILABLE,
                                 duration_ms=duration, error=last_error)

    # ------------------------------------------------------------------ process
    def _process(self, raw_candidates: list[DiscoveryCandidate],
                 run_id: str) -> list[ProcessedCandidate]:
        """normalize → validate → group → resolve → score. Pure and order-stable."""
        processed: list[ProcessedCandidate] = []
        valid: list[DiscoveryCandidate] = []

        for raw in raw_candidates:
            candidate = normalize_candidate(raw)
            issues = validate_candidate(candidate)
            if issues:
                events.candidate_rejected(run_id, candidate, issues)
                processed.append(ProcessedCandidate(candidate, CandidateStatus.REJECTED,
                                                    issues=issues))
                continue
            valid.append(candidate)

        for group in self.resolver.group(valid):
            candidate = group.candidate
            domain, note = self.resolver.resolve_to_company(candidate)
            if domain:
                candidate.company_domain = domain

            score = self.confidence.evaluate(candidate)
            candidate.confidence = score.value

            if group.is_duplicate:
                events.duplicate_detected(run_id, group)
                # Every sighting after the first is reported as a duplicate, so the
                # counts reconcile with what the sources actually returned.
                for member in group.members[1:]:
                    processed.append(ProcessedCandidate(
                        member, CandidateStatus.DUPLICATE, duplicate_of=group.key,
                        resolution_notes=f"merged into {group.key}",
                    ))

            if not self.confidence.meets_threshold(score.value):
                processed.append(ProcessedCandidate(
                    candidate, CandidateStatus.BELOW_THRESHOLD,
                    resolved_company_domain=domain or "",
                    confidence_factors=score.factors,
                    resolution_notes=f"{note}; confidence {score.value:.2f} < "
                                     f"{self.config.confidence.threshold:.2f}",
                ))
                continue

            status = CandidateStatus.UPDATED if domain else CandidateStatus.NEW
            if status is CandidateStatus.NEW:
                events.company_discovered(run_id, candidate, score.value)
            else:
                events.company_updated(run_id, candidate, score.value)
            processed.append(ProcessedCandidate(
                candidate, status, confidence_factors=score.factors, resolution_notes=note,
                resolved_company_domain=domain or "",
            ))
        return processed
