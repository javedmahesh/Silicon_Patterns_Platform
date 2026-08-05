"""Turning an assessment into an explanation a human can act on.

Every number the layer produces has to be defensible in a sentence. This module is
where that sentence is written — and deliberately nowhere else, so the wording of an
explanation can change without touching a rule, a score or a threshold.

The rule the whole module follows: an explanation may only restate evidence that was
actually matched. It never adds a claim, never softens a missing value into a
plausible one, and when nothing was found it says so.
"""
from __future__ import annotations

from backend.market_intelligence.schemas import (
    Classification,
    Evidence,
    MarketIntelligence,
    PriorityFactor,
    Signal,
    SignalCategory,
    Technology,
)

__all__ = ["build_explanation", "build_reasons", "describe_factor", "evidence_terms"]

#: Factors worth naming in the narrative when they contributed. The rest still
#: appear in `factors`, which is the full, auditable breakdown.
_HEADLINE_FACTORS = ("semiconductor_relevance", "technology_overlap",
                     "engineering_activity", "strategic_importance", "funding_activity")


def evidence_terms(evidence: tuple[Evidence, ...], *, limit: int = 4) -> str:
    """The distinct matched terms, in first-seen order — "ASIC, SoC, PCIe"."""
    terms: list[str] = []
    for item in evidence:
        if item.term not in terms:
            terms.append(item.term)
    shown = terms[:limit]
    text = ", ".join(shown)
    return f"{text} (+{len(terms) - len(shown)} more)" if len(terms) > len(shown) else text


def describe_factor(factor: PriorityFactor) -> str:
    return (f"{factor.name.replace('_', ' ')} {factor.value:.2f} "
            f"× weight {factor.weight:g}"
            + (f" ({factor.detail})" if factor.detail else ""))


def build_reasons(
    *,
    classifications: tuple[Classification, ...],
    technologies: tuple[Technology, ...],
    signals: tuple[Signal, ...],
    factors: tuple[PriorityFactor, ...],
    website: str = "",
) -> tuple[str, ...]:
    """The ordered, human-readable reasons behind a priority.

    Ordered strongest-first: what the company *is*, what it *builds*, what it is
    *doing*, then the corroborating facts. That is the order a reviewer reads in.
    """
    reasons: list[str] = []

    if classifications:
        labels = ", ".join(c.label for c in classifications[:3])
        terms = evidence_terms(classifications[0].evidence)
        reasons.append(f"Classified as {labels}"
                       + (f" from published text referencing {terms}." if terms else "."))
    else:
        # Said plainly rather than omitted: "we could not place this company" is
        # itself the finding a reviewer needs.
        reasons.append("No classification matched — the company could not be placed "
                       "in a known market from published text.")

    if technologies:
        labels = ", ".join(t.label for t in technologies[:5])
        more = f" (+{len(technologies) - 5} more)" if len(technologies) > 5 else ""
        reasons.append(f"Technology stack overlaps Silicon Patterns' services: "
                       f"{labels}{more}.")

    for category, phrase in ((SignalCategory.ENGINEERING, "Engineering activity"),
                             (SignalCategory.FUNDING, "Funding activity"),
                             (SignalCategory.STRATEGIC, "Strategic context")):
        found = [s for s in signals if s.category is category]
        if found:
            reasons.append(f"{phrase}: " + ", ".join(s.label for s in found[:4])
                           + (f" (+{len(found) - 4} more)" if len(found) > 4 else "") + ".")

    if website:
        reasons.append("Verified company website.")

    missing = [f.name.replace("_", " ") for f in factors
               if f.name in _HEADLINE_FACTORS and f.value <= 0]
    if missing:
        # Naming what was NOT found is what stops a low priority from looking like a
        # verdict on the company rather than on the available evidence.
        reasons.append("No evidence found for: " + ", ".join(missing) + ".")
    return tuple(reasons)


def build_explanation(record: MarketIntelligence) -> str:
    """One block of prose stating the priority, the score and why."""
    head = (f"Priority {record.priority.value.upper()} "
            f"(score {record.priority_score:.2f}, confidence {record.confidence:.2f})")
    body = " ".join(record.reasons)
    contributions = ", ".join(
        describe_factor(f) for f in record.factors if f.contribution > 0
    ) or "no factor contributed"
    return f"{head}. {body} Score composition: {contributions}."
