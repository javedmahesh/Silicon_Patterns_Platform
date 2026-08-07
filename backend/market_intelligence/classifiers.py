"""Company classification.

Places a company in one or more markets from what it publishes about itself, and
records the words that put it there. Multiple classifications are normal and
expected: a fabless AI-accelerator startup is both, and collapsing that to one label
would throw away exactly the detail that makes it interesting.

Nothing is inferred beyond the vocabulary. A company whose text supports no category
returns an empty tuple — not "Other". An absence of evidence is reportable; a
manufactured label is not.
"""
from __future__ import annotations

import logging

from backend.market_intelligence import rules as rules_engine
from backend.market_intelligence.explainability import evidence_terms
from backend.market_intelligence.rules import MatchContext, RulePack
from backend.market_intelligence.schemas import Classification, RuleKind

logger = logging.getLogger("market_intelligence.classifiers")


def classify(context: MatchContext, *, pack: RulePack) -> tuple[Classification, ...]:
    """Every category the candidate's own text supports, most specific first.

    Order is the pack's declared rule priority, so the first entry is the primary
    classification: "Fabless Semiconductor" outranks the generic "Semiconductor" for a
    company whose text supports both, because the pack says so — not because of the
    order the rules happen to appear in a file.
    """
    out: list[Classification] = []
    for match in rules_engine.evaluate_kind(pack, RuleKind.CLASSIFICATION, context):
        rule = match.rule
        terms = evidence_terms(match.evidence)
        out.append(Classification(
            key=rule.key,
            label=rule.label,
            confidence=match.confidence,
            core=rule.core,
            evidence=match.evidence,
            explanation=rule.explanation or (f"Text references {terms}." if terms else ""),
        ))
    if out:
        logger.debug("[intelligence] classified as %s", [c.key for c in out])
    return tuple(out)


def core_classifications(items: tuple[Classification, ...]) -> tuple[Classification, ...]:
    """Only the categories inside the semiconductor market itself."""
    return tuple(c for c in items if c.core)


def top_confidence(items: tuple[Classification, ...]) -> float:
    """The strongest classification confidence, or 0.0 when unclassified."""
    return max((c.confidence for c in items), default=0.0)
