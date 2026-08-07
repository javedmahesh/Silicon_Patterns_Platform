"""Market signal detection.

Three independent passes, in a fixed order, because the later ones legitimately
depend on the earlier: a "Chip Startup" is a company that is *both* developing
silicon (engineering) *and* early-stage (funding). Running them as one pass would
make that dependency an accident of rule ordering instead of a stated one.

    engineering → funding → strategic

Each pass is a pure function of the match context and the rule pack, so each can be
tested on its own, and each records what it found so the next can build on it.

Every signal carries its type, its confidence, the evidence behind it and an
explanation. A signal that cannot say why it fired is not shipped.
"""
from __future__ import annotations

import logging

from backend.market_intelligence import rules as rules_engine
from backend.market_intelligence.explainability import evidence_terms
from backend.market_intelligence.rules import MatchContext, RulePack
from backend.market_intelligence.schemas import RuleKind, Signal, SignalCategory

logger = logging.getLogger("market_intelligence.signals")


def _detect(context: MatchContext, *, pack: RulePack,
            category: SignalCategory) -> tuple[Signal, ...]:
    """Every satisfied signal rule in one category, in the pack's declared order."""
    out: list[Signal] = []
    for rule in pack.of_kind(RuleKind.SIGNAL):
        if rule.category != category.value:
            continue
        match = rules_engine.evaluate_rule(rule, context, pack=pack)
        if match is None:
            continue
        # Recorded even when it later falls below the reporting threshold: a weak
        # signal is still a true prerequisite, and hiding it from dependent rules
        # would make a reported signal depend on an unreported one silently.
        context.record(rule.key, match.evidence)
        terms = evidence_terms(match.evidence)
        out.append(Signal(
            key=rule.key,
            type=rule.type_name,
            label=rule.label,
            category=category,
            confidence=match.confidence,
            evidence=match.evidence,
            explanation=rule.explanation or (f"Text references {terms}." if terms else
                                             f"{rule.label} detected."),
        ))
    return tuple(out)


def detect_engineering(context: MatchContext, *, pack: RulePack) -> tuple[Signal, ...]:
    """Evidence of engineering work: hiring, expansion, design, verification, silicon."""
    return _detect(context, pack=pack, category=SignalCategory.ENGINEERING)


def detect_funding(context: MatchContext, *, pack: RulePack) -> tuple[Signal, ...]:
    """Evidence of capital: rounds, IPO, grants, public programmes, accelerators."""
    return _detect(context, pack=pack, category=SignalCategory.FUNDING)


def detect_strategic(context: MatchContext, *, pack: RulePack) -> tuple[Signal, ...]:
    """Business interpretations built on classification, technology and the passes above.

    Must run last. Most strategic rules are derived — they carry no vocabulary and
    inherit the evidence of their prerequisites, which is how "Semiconductor Startup"
    stays traceable to the sentences that made it true.
    """
    return _detect(context, pack=pack, category=SignalCategory.STRATEGIC)


def detect_signals(context: MatchContext, *, pack: RulePack) -> tuple[Signal, ...]:
    """All three passes, filtered to the signals worth reporting.

    The confidence floor is applied once, at the end, so a rule's reporting status
    never changes what other rules can depend on.
    """
    found = (detect_engineering(context, pack=pack)
             + detect_funding(context, pack=pack)
             + detect_strategic(context, pack=pack))
    floor = pack.threshold("signal_min_confidence")
    kept = tuple(s for s in found if s.confidence >= floor)
    if len(kept) != len(found):
        logger.debug("[intelligence] %d signal(s) below the %.2f reporting floor",
                     len(found) - len(kept), floor)
    return kept


def strength(signals: tuple[Signal, ...], category: SignalCategory, *,
             target: float = 2.0) -> float:
    """0..1 strength of one category: summed confidence, saturating at ``target``.

    Summing confidence rather than counting means two well-evidenced signals outrank
    four weak ones — corroboration, not volume.
    """
    total = sum(s.confidence for s in signals if s.category is category)
    if target <= 0:
        return 1.0 if total else 0.0
    return round(min(1.0, total / target), 4)
