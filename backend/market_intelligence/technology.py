"""Technology detection.

Finds the technologies a company's published text references, using the configurable
vocabulary in the active rule pack. This is what "technology overlap with Silicon
Patterns' services" is measured from downstream, which is why the vocabulary is
configuration: the services change, and the platform must track them without a code
change.

Matching is whole-token or boundary-anchored (see
:mod:`backend.market_intelligence.rules`), so "SoC" never matches "soccer" and
"2.5D" never matches "12.5dB".
"""
from __future__ import annotations

import logging

from backend.market_intelligence import rules as rules_engine
from backend.market_intelligence.rules import MatchContext, RulePack
from backend.market_intelligence.schemas import RuleKind, Technology

logger = logging.getLogger("market_intelligence.technology")


def detect_technologies(context: MatchContext, *, pack: RulePack) -> tuple[Technology, ...]:
    """Every technology the candidate's text references, in pack order."""
    out = tuple(
        Technology(key=m.rule.key, label=m.rule.label, category=m.rule.category,
                   evidence=m.evidence)
        for m in rules_engine.evaluate_kind(pack, RuleKind.TECHNOLOGY, context)
    )
    if out:
        logger.debug("[intelligence] technologies %s", [t.key for t in out])
    return out


def categories(items: tuple[Technology, ...]) -> tuple[str, ...]:
    """Distinct technology groups covered, in first-seen order.

    Breadth across groups (design + packaging + interface) says more about a
    prospective engagement than depth in one, so the priority model counts groups
    as well as individual technologies.
    """
    out: list[str] = []
    for item in items:
        if item.category and item.category not in out:
            out.append(item.category)
    return tuple(out)


def overlap_score(items: tuple[Technology, ...], *, target: float) -> float:
    """0..1 technology overlap: how much of a full stack the company shows.

    ``target`` technologies is treated as complete overlap; a company matching more
    is already unambiguously in scope and gains nothing further from the factor.
    """
    if target <= 0:
        return 1.0 if items else 0.0
    return round(min(1.0, len(items) / target), 4)
