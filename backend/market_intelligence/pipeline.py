"""The intelligence pipeline.

    candidate → classify → technologies → engineering → funding → strategic
              → priority → explanation → MarketIntelligence

Deterministic by construction. Every stage is a pure function of the candidate and
the rule pack: no wall clock, no database, no dict-iteration order, no dependence on
which thread finished first. The same candidate and pack always produce a
byte-identical record, which is what makes a stored priority auditable months later.

The pipeline computes; it does not persist. Turning records into rows is
:mod:`backend.market_intelligence.service`, which keeps every database write in one
place and keeps this module testable with no session at all.

**Forward compatibility.** :func:`register_enricher` is where a future embedding,
semantic match or LLM summary plugs in. An enricher may only contribute to
``record.enrichment``; the deterministic fields are snapshotted and restored around
it, so the rule-based result stays the source of truth by construction rather than
by convention.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Sequence

from backend.market_discovery.schemas import DiscoveryCandidate
from backend.market_intelligence import classifiers, events, scoring, signals, technology
from backend.market_intelligence.config import IntelligenceConfig
from backend.market_intelligence.explainability import build_explanation, build_reasons
from backend.market_intelligence.rules import build_context
from backend.market_intelligence.schemas import IntelligenceResult, MarketIntelligence

logger = logging.getLogger("market_intelligence.pipeline")

#: An enricher takes the finished deterministic record plus its candidate and returns
#: values to record under ``enrichment`` (or None). It must not mutate the record.
Enricher = Callable[[MarketIntelligence, DiscoveryCandidate], Mapping[str, Any] | None]

_enrichers: list[Enricher] = []


def register_enricher(enricher: Enricher) -> Enricher:
    """Register an optional enrichment pass. Usable as a decorator.

    Enrichers run after the deterministic pipeline, never instead of it, and cannot
    change a classification, a signal or a priority. That boundary is what lets AI be
    added later without making the platform's intelligence unreproducible.
    """
    _enrichers.append(enricher)
    return enricher


def unregister_enricher(enricher: Enricher) -> None:
    try:
        _enrichers.remove(enricher)
    except ValueError:
        pass


def clear_enrichers() -> None:
    _enrichers.clear()


class IntelligencePipeline:
    """Evaluates candidates against a rule pack. Stateless and safe to share."""

    def __init__(self, config: IntelligenceConfig | None = None) -> None:
        self.config = config or IntelligenceConfig()

    @property
    def pack(self):
        return self.config.pack

    # ------------------------------------------------------------------ single
    def evaluate(self, candidate: DiscoveryCandidate, *, run_id: str = "",
                 now: datetime | None = None) -> MarketIntelligence:
        """One candidate → one intelligence record. Pure; the input is never mutated."""
        started = time.monotonic()
        moment = now or datetime.now(timezone.utc)
        pack = self.pack

        context = build_context(candidate, pack=pack, now_year=moment.year)
        found_classifications = classifiers.classify(context, pack=pack)
        found_technologies = technology.detect_technologies(context, pack=pack)
        found_signals = signals.detect_signals(context, pack=pack)

        assessment = scoring.assess(
            candidate, classifications=found_classifications,
            technologies=found_technologies, signals=found_signals, pack=pack,
        )
        record = MarketIntelligence(
            candidate_key=candidate.candidate_key,
            company_name=candidate.company_name,
            company_domain=candidate.company_domain,
            website=candidate.website,
            source=candidate.source,
            sources=tuple(candidate.sources),
            classifications=found_classifications,
            technologies=found_technologies,
            signals=found_signals,
            priority=assessment.priority,
            priority_score=assessment.score,
            factors=assessment.factors,
            rule_pack=pack.name,
            rule_pack_version=pack.version,
            run_id=run_id,
            evaluated_at=moment,
        )
        record.confidence = scoring.confidence(
            candidate, classifications=found_classifications,
            evidence_count=record.evidence_count, pack=pack,
        )
        record.reasons = build_reasons(
            classifications=found_classifications, technologies=found_technologies,
            signals=found_signals, factors=assessment.factors, website=candidate.website,
        )
        record.explanation = build_explanation(record)
        record.duration_ms = int((time.monotonic() - started) * 1000)

        self._emit(record)
        self._enrich(record, candidate)
        logger.info(
            "[intelligence] %s → %s score=%.2f confidence=%.2f classifications=%s "
            "technologies=%d signals=%d in %dms",
            candidate.company_name or candidate.candidate_key, record.priority.value,
            record.priority_score, record.confidence,
            list(record.classification_labels) or ["unclassified"],
            len(record.technologies), len(record.signals), record.duration_ms,
        )
        return record

    def _emit(self, record: MarketIntelligence) -> None:
        events.company_classified(record)
        if record.technologies:
            events.technology_identified(record)
        for signal in record.signals:
            events.signal_generated(record, signal)
        events.priority_assigned(record)

    def _enrich(self, record: MarketIntelligence, candidate: DiscoveryCandidate) -> None:
        """Run optional enrichers, protecting every deterministic field.

        The snapshot/restore is not defensive programming for its own sake: it is the
        mechanism that keeps the guarantee true even if an enricher is written badly,
        which is exactly the risk a future AI integration carries.
        """
        if not _enrichers:
            return
        snapshot = replace(record)
        for enricher in list(_enrichers):
            try:
                extra = enricher(record, candidate)
            except Exception:      # noqa: BLE001 - enrichment is never load-bearing
                logger.error("[intelligence] enricher %r raised (ignored)",
                             getattr(enricher, "__name__", enricher), exc_info=True)
                continue
            if extra:
                record.enrichment.update(dict(extra))
        enrichment = record.enrichment
        for name in (
            "classifications", "technologies", "signals", "priority", "priority_score",
            "confidence", "factors", "reasons", "explanation", "rule_pack",
            "rule_pack_version",
        ):
            setattr(record, name, getattr(snapshot, name))
        record.enrichment = enrichment

    # ------------------------------------------------------------------ batch
    def run(self, candidates: Sequence[DiscoveryCandidate] | Iterable[DiscoveryCandidate],
            *, run_id: str = "", now: datetime | None = None,
            skipped: int = 0) -> IntelligenceResult:
        """Evaluate a batch. Never raises — one bad candidate costs only itself.

        Output order always matches input order, whether or not the batch ran
        concurrently, so a run is reproducible regardless of thread scheduling.

        ``skipped`` is how many candidates the caller filtered out as already current.
        Seeded here rather than set afterwards so the completion event and the run log
        report the true totals.
        """
        items = list(candidates)
        moment = now or datetime.now(timezone.utc)
        result = IntelligenceResult(run_id=run_id, started_at=moment, skipped=skipped)
        clock = time.monotonic()
        events.pipeline_started(run_id, len(items), self.pack.name)

        usable: list[DiscoveryCandidate] = []
        for candidate in items:
            reason = _unusable(candidate)
            if reason:
                result.rejected += 1
                events.candidate_rejected(run_id, candidate.candidate_key,
                                          candidate.company_name, reason)
                continue
            usable.append(candidate)

        for candidate, record, error in self._evaluate_all(usable, run_id, moment):
            if record is not None:
                result.records.append(record)
                continue
            result.failed += 1
            message = f"{candidate.candidate_key or candidate.company_name}: {error}"
            result.errors.append(message[:500])

        result.finished_at = datetime.now(timezone.utc)
        result.duration_ms = int((time.monotonic() - clock) * 1000)
        logger.info("[intelligence] run %s finished in %dms: %s",
                    run_id or "-", result.duration_ms, result.summary())
        events.pipeline_completed(run_id, result)
        return result

    def _evaluate_all(self, candidates: list[DiscoveryCandidate], run_id: str,
                      moment: datetime):
        """Evaluate every candidate, yielding ``(candidate, record, error)`` in order.

        Evaluation is pure CPU string matching, so threads buy nothing today and the
        default is 1. The pool exists because the enrichment seam above is where
        network-bound work will land, and `map` preserves input order, so raising
        concurrency can never change a result.
        """
        def one(candidate: DiscoveryCandidate):
            try:
                return candidate, self.evaluate(candidate, run_id=run_id, now=moment), ""
            except Exception as exc:      # noqa: BLE001
                logger.error("[intelligence] evaluating %s failed",
                             candidate.candidate_key or candidate.company_name,
                             exc_info=True)
                return candidate, None, str(exc)[:500]

        workers = max(1, min(self.config.concurrency, len(candidates) or 1))
        if workers == 1 or len(candidates) <= 1:
            return [one(c) for c in candidates]
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="intel") as pool:
            return list(pool.map(one, candidates))


def _unusable(candidate: DiscoveryCandidate) -> str:
    """Why this candidate cannot be interpreted, or "" when it can.

    Only identity is required. A candidate with nothing but a name still produces a
    valid record — an honest LOW with "no classification matched" is information, and
    dropping it would hide a discovered company from review entirely.
    """
    if not candidate.candidate_key:
        return "no candidate identity"
    if not (candidate.company_name or candidate.company_domain):
        return "no company name or domain"
    return ""


def evaluate_candidate(candidate: DiscoveryCandidate, *,
                       config: IntelligenceConfig | None = None,
                       run_id: str = "") -> MarketIntelligence:
    """Convenience for one-off evaluation (scripts, tests, an API preview)."""
    return IntelligencePipeline(config).evaluate(candidate, run_id=run_id)
