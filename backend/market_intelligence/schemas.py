"""Market Intelligence types.

The contract between the Market Discovery Engine (which produces
:class:`~backend.market_discovery.schemas.DiscoveryCandidate`) and everything that
consumes interpreted intelligence — lead scoring, the executive dashboard,
notifications.

Nothing here imports a rule, a classifier, a session or a crawler. A record must be
constructible, comparable and serializable on its own, which is what keeps the
intelligence pipeline a pure function and its output reproducible.

Every interpreted value carries its evidence. That is not decoration: an opportunity
priority an analyst cannot trace back to a published sentence is not actionable, and
the platform's rule is that no score is a black box.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Priority(str, Enum):
    """How urgently Silicon Patterns should act on a discovered company."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def rank(self) -> int:
        """Sort order, most urgent first. Lets callers rank without a lookup table."""
        return _PRIORITY_RANK[self.value]


_PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}

#: Descending urgency. The single place the band order is written down.
PRIORITY_ORDER: tuple[Priority, ...] = (
    Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW,
)


class SignalCategory(str, Enum):
    ENGINEERING = "engineering"
    FUNDING = "funding"
    STRATEGIC = "strategic"


class RuleKind(str, Enum):
    CLASSIFICATION = "classification"
    TECHNOLOGY = "technology"
    SIGNAL = "signal"


@dataclass(frozen=True, slots=True, order=True)
class Evidence:
    """One published fact that supports one interpretation.

    ``field`` is where it was found ("description", "technologies", "source"), ``term``
    the vocabulary entry that matched. Ordered so evidence lists are stable across
    runs without the caller having to sort them.
    """

    field: str
    term: str
    excerpt: str = ""

    def describe(self) -> str:
        return f"{self.term!r} in {self.field}"

    def as_dict(self) -> dict[str, str]:
        out = {"field": self.field, "term": self.term}
        if self.excerpt:
            out["excerpt"] = self.excerpt
        return out


@dataclass(frozen=True, slots=True)
class Classification:
    """A category the company belongs to, with the evidence that placed it there."""

    key: str
    label: str
    confidence: float
    core: bool = False            # a semiconductor category, vs an adjacent market
    evidence: tuple[Evidence, ...] = ()
    explanation: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "label": self.label, "confidence": self.confidence,
            "core": self.core, "explanation": self.explanation,
            "evidence": [e.as_dict() for e in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class Technology:
    """A technology the company's own text references."""

    key: str
    label: str
    category: str = ""
    evidence: tuple[Evidence, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "label": self.label, "category": self.category,
            "evidence": [e.as_dict() for e in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class Signal:
    """A market signal: what happened, how sure the platform is, and why."""

    key: str
    type: str
    label: str
    category: SignalCategory
    confidence: float
    evidence: tuple[Evidence, ...] = ()
    explanation: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "type": self.type, "label": self.label,
            "category": self.category.value, "confidence": self.confidence,
            "explanation": self.explanation,
            "evidence": [e.as_dict() for e in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class PriorityFactor:
    """One input to the priority calculation, and exactly what it contributed.

    ``value`` is the factor's own 0..1 reading, ``weight`` its configured importance,
    ``contribution`` the product. Summing contributions and dividing by the evaluated
    weight reproduces the score by hand — which is the point.
    """

    name: str
    value: float
    weight: float
    contribution: float
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value, "weight": self.weight,
                "contribution": self.contribution, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class PriorityAssessment:
    """The priority band, the score behind it, and every factor that produced it."""

    priority: Priority
    score: float
    factors: tuple[PriorityFactor, ...] = ()
    threshold: float = 0.0        # the band boundary this score cleared

    def as_dict(self) -> dict[str, Any]:
        return {"priority": self.priority.value, "score": self.score,
                "threshold": self.threshold,
                "factors": [f.as_dict() for f in self.factors]}


@dataclass(slots=True)
class MarketIntelligence:
    """Everything the platform concluded about one discovered company.

    ``enrichment`` is the forward-compatibility seam: a future embedding, semantic
    match or LLM summary writes there and nowhere else. Deterministic fields are
    never overwritten by an enricher, so the rule-based result stays the source of
    truth and remains reproducible from the candidate alone.
    """

    candidate_key: str = ""
    company_name: str = ""
    company_domain: str = ""
    website: str = ""
    source: str = ""
    sources: tuple[str, ...] = ()

    classifications: tuple[Classification, ...] = ()
    technologies: tuple[Technology, ...] = ()
    signals: tuple[Signal, ...] = ()

    priority: Priority = Priority.LOW
    priority_score: float = 0.0
    confidence: float = 0.0
    factors: tuple[PriorityFactor, ...] = ()
    reasons: tuple[str, ...] = ()
    explanation: str = ""

    rule_pack: str = ""
    rule_pack_version: str = ""
    run_id: str = ""
    evaluated_at: datetime = field(default_factory=_utcnow)
    duration_ms: int = 0
    enrichment: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ views
    @property
    def primary_classification(self) -> str:
        """The strongest category, or "" when the company could not be placed.

        Deliberately not defaulted to "Other": an unclassifiable company is a real,
        reportable state, and labelling it would hide that from a reviewer.
        """
        return self.classifications[0].label if self.classifications else ""

    @property
    def classification_labels(self) -> tuple[str, ...]:
        return tuple(c.label for c in self.classifications)

    @property
    def technology_labels(self) -> tuple[str, ...]:
        return tuple(t.label for t in self.technologies)

    @property
    def signal_types(self) -> tuple[str, ...]:
        return tuple(s.type for s in self.signals)

    @property
    def is_core_semiconductor(self) -> bool:
        return any(c.core for c in self.classifications)

    @property
    def evidence_count(self) -> int:
        """Distinct supporting facts across every interpretation."""
        seen = {e for c in self.classifications for e in c.evidence}
        seen |= {e for t in self.technologies for e in t.evidence}
        seen |= {e for s in self.signals for e in s.evidence}
        return len(seen)

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_key": self.candidate_key,
            "company_name": self.company_name,
            "company_domain": self.company_domain,
            "website": self.website,
            "source": self.source,
            "sources": list(self.sources),
            "classifications": [c.as_dict() for c in self.classifications],
            "technologies": [t.as_dict() for t in self.technologies],
            "signals": [s.as_dict() for s in self.signals],
            "priority": self.priority.value,
            "priority_score": self.priority_score,
            "confidence": self.confidence,
            "factors": [f.as_dict() for f in self.factors],
            "reasons": list(self.reasons),
            "explanation": self.explanation,
            "rule_pack": self.rule_pack,
            "rule_pack_version": self.rule_pack_version,
            "run_id": self.run_id,
            "evaluated_at": self.evaluated_at.isoformat(),
            "enrichment": dict(self.enrichment),
        }


@dataclass(slots=True)
class IntelligenceResult:
    """The outcome of one intelligence pass."""

    run_id: str = ""
    started_at: datetime = field(default_factory=_utcnow)
    finished_at: datetime | None = None
    duration_ms: int = 0
    records: list[MarketIntelligence] = field(default_factory=list)
    skipped: int = 0              # already up to date
    rejected: int = 0             # no usable identity — nothing to interpret
    failed: int = 0               # evaluation raised; candidate left untouched
    errors: list[str] = field(default_factory=list)

    @property
    def evaluated(self) -> int:
        return len(self.records)

    def count(self, priority: Priority) -> int:
        return sum(1 for r in self.records if r.priority is priority)

    @property
    def by_priority(self) -> dict[str, int]:
        return {p.value: self.count(p) for p in PRIORITY_ORDER}

    @property
    def actionable(self) -> list[MarketIntelligence]:
        """Critical and high — the records worth a human's attention today."""
        return [r for r in self.records
                if r.priority in (Priority.CRITICAL, Priority.HIGH)]

    @property
    def status(self) -> str:
        """success | partial | failed — matches the orchestrator's stage vocabulary."""
        if not self.failed:
            return "success"
        return "failed" if not self.records else "partial"

    def summary(self) -> str:
        counts = " ".join(f"{k}={v}" for k, v in self.by_priority.items())
        return (f"evaluated={self.evaluated} skipped={self.skipped} "
                f"rejected={self.rejected} failed={self.failed} {counts}")
