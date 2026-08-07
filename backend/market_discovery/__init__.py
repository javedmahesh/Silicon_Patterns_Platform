"""Market Discovery Engine.

The platform's single source of truth for discovering new market entrants.

    sources → normalize → validate → resolve → confidence → DiscoveryResult

**Architectural contract.** External services (Firecrawl, Wellfound, Dealroom,
Crunchbase, LinkedIn, RSS, conference sites, VC portfolios, government registries)
are *data providers only*. Their entire responsibility is to return raw discovery
data as :class:`DiscoveryCandidate` objects. This engine owns everything else:
business logic, normalization, validation, duplicate detection, company resolution,
confidence scoring, event generation, scheduler integration, persistence and
platform integration.

No connector may write to the database or implement a business rule. That boundary
is enforced structurally: :class:`DiscoverySource` has no session, the pipeline is a
pure function over candidates, and :mod:`backend.market_discovery.service` is the
only module that commits.

Adding a source is one module under ``sources/`` plus a ``register()`` call — no
change to the engine, pipeline, resolver, confidence model or scheduler.
"""
from __future__ import annotations

from backend.market_discovery.base_source import DiscoverySource
from backend.market_discovery.crawling import CrawlingDiscoverySource
from backend.market_discovery.confidence import (
    ConfidenceConfig,
    ConfidenceEngine,
    ConfidenceScore,
    SEMICONDUCTOR_KEYWORDS,
)
from backend.market_discovery.events import (
    DiscoveryEvent,
    EventType,
    clear_subscribers,
    emit,
    subscribe,
    unsubscribe,
)
from backend.market_discovery.models import DiscoveryCandidateRecord
from backend.market_discovery.normalize import (
    candidate_key,
    comparison_name,
    normalize_candidate,
    validate_candidate,
)
from backend.market_discovery.pipeline import DiscoveryPipeline, PipelineConfig
from backend.market_discovery.registry import SourceRegistry, register, registry
from backend.market_discovery.resolver import (
    DiscoveryResolver,
    DuplicateStrategy,
    FieldConflict,
    MergeGroup,
)
from backend.market_discovery.schemas import (
    CandidateStatus,
    DiscoveryCandidate,
    DiscoveryContext,
    DiscoveryResult,
    ProcessedCandidate,
    SourceCapabilities,
    SourceHealth,
    SourceOutcome,
    SourceStatus,
    ValidationIssue,
)
from backend.market_discovery.service import discovery_health, run_discovery

__all__ = [
    "CandidateStatus",
    "ConfidenceConfig",
    "ConfidenceEngine",
    "ConfidenceScore",
    "CrawlingDiscoverySource",
    "DiscoveryCandidate",
    "DiscoveryCandidateRecord",
    "DiscoveryContext",
    "DiscoveryEvent",
    "DiscoveryPipeline",
    "DiscoveryResolver",
    "DiscoveryResult",
    "DiscoverySource",
    "DuplicateStrategy",
    "EventType",
    "FieldConflict",
    "MergeGroup",
    "PipelineConfig",
    "ProcessedCandidate",
    "SEMICONDUCTOR_KEYWORDS",
    "SourceCapabilities",
    "SourceHealth",
    "SourceOutcome",
    "SourceRegistry",
    "SourceStatus",
    "ValidationIssue",
    "candidate_key",
    "clear_subscribers",
    "comparison_name",
    "discovery_health",
    "emit",
    "normalize_candidate",
    "register",
    "registry",
    "run_discovery",
    "subscribe",
    "unsubscribe",
    "validate_candidate",
]
