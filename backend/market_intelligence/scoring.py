"""Opportunity priority.

A weighted sum of independent 0..1 factors, normalized by the weight of the factors
that were actually *evaluated*, then banded into CRITICAL / HIGH / MEDIUM / LOW.
The same arithmetic as the discovery engine's confidence model, deliberately: the
platform should have one way of combining evidence, not two.

Two properties this design buys:

* **Reproducible.** No wall clock, no ordering effects, no learned weights. The same
  candidate and the same rule pack always produce the same band, on any machine.
* **Explainable by construction.** Every factor reports its reading, its weight and
  its contribution, so the score can be recomputed by hand from the record alone.
  There is no step a reviewer has to take on trust.

Normalizing by the evaluated total (not the maximum possible) means disabling a
factor — setting its weight to 0 — cannot silently deflate every other company's
score, and adding a factor later does not invalidate stored history.
"""
from __future__ import annotations

import logging

from backend.market_discovery.schemas import DiscoveryCandidate
from backend.market_intelligence import signals as signal_lib
from backend.market_intelligence import technology as technology_lib
from backend.market_intelligence.classifiers import top_confidence
from backend.market_intelligence.rules import RulePack
from backend.market_intelligence.schemas import (
    Classification,
    Priority,
    PriorityAssessment,
    PriorityFactor,
    Signal,
    SignalCategory,
    Technology,
)

logger = logging.getLogger("market_intelligence.scoring")

#: Relevance of a company that matched only an adjacent market (robotics, automotive,
#: industrial). They buy silicon rather than build it, so they are real opportunities
#: — just not the same opportunity as a fabless design house.
ADJACENT_RELEVANCE = 0.6


def _maturity(candidate: DiscoveryCandidate) -> tuple[float, str]:
    """How much is known about the company's stage, 0..1, and what was found.

    A proxy for "is there enough here to open a conversation", not a judgement about
    the company: an unknown founding year is a gap in the platform's data, and this
    factor is weighted low precisely because of that.
    """
    present = {
        "founded year": bool(candidate.founded_year),
        "headcount": bool(candidate.employee_count),
        "funding stage": bool(candidate.funding_stage),
        "location": bool(candidate.headquarters or candidate.country),
    }
    found = [name for name, ok in present.items() if ok]
    return round(len(found) / len(present), 4), ", ".join(found) or "nothing known"


def _relevance(classifications: tuple[Classification, ...]) -> tuple[float, str]:
    core = [c for c in classifications if c.core]
    if core:
        return 1.0, "core semiconductor: " + ", ".join(c.label for c in core)
    if classifications:
        return (ADJACENT_RELEVANCE,
                "adjacent market: " + ", ".join(c.label for c in classifications))
    return 0.0, "no market classification matched"


def assess(
    candidate: DiscoveryCandidate,
    *,
    classifications: tuple[Classification, ...],
    technologies: tuple[Technology, ...],
    signals: tuple[Signal, ...],
    pack: RulePack,
) -> PriorityAssessment:
    """Compute the opportunity priority and the full factor breakdown."""
    relevance, relevance_detail = _relevance(classifications)
    maturity, maturity_detail = _maturity(candidate)
    tech_overlap = technology_lib.overlap_score(
        technologies, target=pack.threshold("technology_target"))
    engineering = signal_lib.strength(signals, SignalCategory.ENGINEERING,
                                      target=pack.threshold("engineering_target"))
    funding = signal_lib.strength(signals, SignalCategory.FUNDING,
                                  target=pack.threshold("funding_target"))
    strategic = signal_lib.strength(signals, SignalCategory.STRATEGIC,
                                    target=pack.threshold("strategic_target"))
    discovery = round(min(1.0, max(0.0, float(candidate.confidence or 0.0))), 4)

    readings: tuple[tuple[str, float, str], ...] = (
        ("semiconductor_relevance", relevance, relevance_detail),
        ("technology_overlap", tech_overlap,
         ", ".join(t.label for t in technologies[:5]) or "none detected"),
        ("engineering_activity", engineering,
         ", ".join(s.label for s in signals if s.category is SignalCategory.ENGINEERING)
         or "none detected"),
        ("strategic_importance", strategic,
         ", ".join(s.label for s in signals if s.category is SignalCategory.STRATEGIC)
         or "none detected"),
        ("funding_activity", funding,
         ", ".join(s.label for s in signals if s.category is SignalCategory.FUNDING)
         or "none detected"),
        ("discovery_confidence", discovery, "confidence carried from discovery"),
        ("company_maturity", maturity, maturity_detail),
    )

    factors: list[PriorityFactor] = []
    total_weight = 0.0
    earned = 0.0
    for name, value, detail in readings:
        weight = pack.weight(name)
        if weight <= 0:
            continue          # disabled: not evaluated, and not in the denominator
        contribution = round(value * weight, 4)
        total_weight += weight
        earned += contribution
        factors.append(PriorityFactor(name=name, value=value, weight=weight,
                                      contribution=contribution, detail=detail))

    score = round(earned / total_weight, 4) if total_weight else 0.0
    priority, floor = band(score, pack=pack)
    return PriorityAssessment(priority=priority, score=score, factors=tuple(factors),
                              threshold=floor)


def band(score: float, *, pack: RulePack) -> tuple[Priority, float]:
    """Map a score onto a priority band, returning the band and the floor it cleared."""
    for priority, key in ((Priority.CRITICAL, "priority_critical"),
                          (Priority.HIGH, "priority_high"),
                          (Priority.MEDIUM, "priority_medium")):
        floor = pack.threshold(key)
        if score >= floor:
            return priority, floor
    return Priority.LOW, 0.0


def confidence(
    candidate: DiscoveryCandidate,
    *,
    classifications: tuple[Classification, ...],
    evidence_count: int,
    pack: RulePack,
) -> float:
    """How well-evidenced the assessment is — distinct from how urgent it is.

    A company can be confidently unimportant (LOW priority, high confidence) or
    promisingly under-documented (HIGH priority, low confidence), and a reviewer needs
    to tell those apart. Blends how surely the company was classified, the discovery
    engine's own confidence, and how much independent evidence was found.
    """
    target = pack.threshold("evidence_target")
    coverage = round(min(1.0, evidence_count / target), 4) if target > 0 else 0.0
    parts = (
        (pack.threshold("confidence_classification"), top_confidence(classifications)),
        (pack.threshold("confidence_discovery"),
         min(1.0, max(0.0, float(candidate.confidence or 0.0)))),
        (pack.threshold("confidence_evidence"), coverage),
    )
    total = sum(w for w, _ in parts if w > 0)
    if total <= 0:
        return 0.0
    return round(sum(w * v for w, v in parts if w > 0) / total, 4)
