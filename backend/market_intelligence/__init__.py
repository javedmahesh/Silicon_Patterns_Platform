"""Market Intelligence Layer.

Turns discovered companies into business intelligence: what a company *is*, what it
*builds*, what it is *doing*, how urgently Silicon Patterns should act — and why.

    candidate → classify → technologies → engineering → funding → strategic
              → priority → explanation → MarketIntelligence

**Architectural contract.** The platform is strictly layered:

    discovery sources → Market Discovery Engine → Market Intelligence Layer
                      → lead scoring → dashboard → notifications

A discovery source retrieves public information. The discovery engine normalizes,
resolves and de-duplicates it. *This* layer is the only place that interprets it —
no source and no crawler contains a business rule, and no intelligence rule lives
outside this package. The boundary is structural: this package imports discovery's
schemas and nothing else from it, and :mod:`backend.market_intelligence.service` is
the only module here that opens a session.

**Deterministic, not learned.** Every conclusion is a configured rule over published
text. No machine learning, no LLM, no external AI service, no network call. The same
candidate and rule pack always produce the same record, so a priority assigned months
ago can still be explained from the row that stored it.

**Extensible without being rewritten.** Rules are data
(:mod:`backend.market_intelligence.vocabulary`, overridable by environment and by
JSON rule packs), and :func:`~backend.market_intelligence.pipeline.register_enricher`
is where embeddings, semantic search or LLM enrichment plug in later. An enricher may
only add to ``record.enrichment``; the deterministic engine remains the source of
truth.
"""
from __future__ import annotations

from backend.market_intelligence.classifiers import classify
from backend.market_intelligence.config import IntelligenceConfig, build_pack
from backend.market_intelligence.events import (
    EventType,
    IntelligenceEvent,
    clear_subscribers,
    emit,
    subscribe,
    unsubscribe,
)
from backend.market_intelligence.models import MarketIntelligenceRecord
from backend.market_intelligence.pipeline import (
    IntelligencePipeline,
    clear_enrichers,
    evaluate_candidate,
    register_enricher,
    unregister_enricher,
)
from backend.market_intelligence.rules import (
    MatchContext,
    Rule,
    RulePack,
    build_context,
    evaluate_rule,
    match_terms,
)
from backend.market_intelligence.schemas import (
    Classification,
    Evidence,
    IntelligenceResult,
    MarketIntelligence,
    PRIORITY_ORDER,
    Priority,
    PriorityAssessment,
    PriorityFactor,
    RuleKind,
    Signal,
    SignalCategory,
    Technology,
)
from backend.market_intelligence.scoring import assess, band
from backend.market_intelligence.service import intelligence_health, run_market_intelligence
from backend.market_intelligence.signals import (
    detect_engineering,
    detect_funding,
    detect_signals,
    detect_strategic,
)
from backend.market_intelligence.technology import detect_technologies
from backend.market_intelligence.vocabulary import (
    ADJACENT_CLASSIFICATIONS,
    CORE_CLASSIFICATIONS,
    default_pack,
)

__all__ = [
    "ADJACENT_CLASSIFICATIONS",
    "CORE_CLASSIFICATIONS",
    "Classification",
    "EventType",
    "Evidence",
    "IntelligenceConfig",
    "IntelligenceEvent",
    "IntelligencePipeline",
    "IntelligenceResult",
    "MarketIntelligence",
    "MarketIntelligenceRecord",
    "MatchContext",
    "PRIORITY_ORDER",
    "Priority",
    "PriorityAssessment",
    "PriorityFactor",
    "Rule",
    "RuleKind",
    "RulePack",
    "Signal",
    "SignalCategory",
    "Technology",
    "assess",
    "band",
    "build_context",
    "build_pack",
    "classify",
    "clear_enrichers",
    "clear_subscribers",
    "default_pack",
    "detect_engineering",
    "detect_funding",
    "detect_signals",
    "detect_strategic",
    "detect_technologies",
    "emit",
    "evaluate_candidate",
    "evaluate_rule",
    "intelligence_health",
    "match_terms",
    "register_enricher",
    "run_market_intelligence",
    "subscribe",
    "unregister_enricher",
    "unsubscribe",
]
