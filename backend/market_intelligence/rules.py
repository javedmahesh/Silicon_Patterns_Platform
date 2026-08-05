"""The rules engine.

Business rules are *data*, not code. A rule is a row of configuration — vocabulary,
weight, priority, prerequisites, an explanation — and this module is the small
deterministic machine that evaluates them. Adding a category, a technology or a
signal means editing a rule pack, never editing a classifier.

Three things live here:

* :class:`Rule` / :class:`RulePack` — the configuration model, including
  enable/disable, weighting, ordering, thresholds and pack overlays.
* :class:`MatchContext` — a candidate decomposed once into fields, tokens and facts,
  so twenty rules do not re-tokenize the same description twenty times.
* :func:`evaluate_rule` — the single matching primitive every stage uses, which is
  why classification, technology detection and signal detection behave identically.

Matching is exact and inspectable. A single-word term must appear as a whole token
("chip" never matches "chipotle"); a multi-word or punctuated term is matched with
explicit boundaries ("2.5d" never matches "12.5db"). No stemming, no fuzzy distance,
no learned weights — an analyst can read a rule and predict the outcome, which is
what makes every downstream score auditable.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.market_discovery.schemas import DiscoveryCandidate
from backend.market_intelligence.schemas import Evidence, RuleKind

logger = logging.getLogger("market_intelligence.rules")

#: Tokenization for whole-word matching. Splits on punctuation *including* hyphens
#: and dots, so "ai-accelerator" yields "ai" and "accelerator" — a term written as
#: one word still matches text that hyphenates it.
_TOKEN = re.compile(r"[a-z0-9+#]+")
_WS = re.compile(r"\s+")


@lru_cache(maxsize=4096)
def _phrase_pattern(term: str) -> re.Pattern[str]:
    """Boundary-anchored pattern for a multi-word or punctuated term."""
    return re.compile(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])")


def _is_phrase(term: str) -> bool:
    """True for a term that is not a single bare token ("risc-v", "physical design")."""
    return _TOKEN.fullmatch(term) is None


# --------------------------------------------------------------------- rules
@dataclass(frozen=True, slots=True)
class Rule:
    """One business rule.

    ``terms`` is the vocabulary that satisfies it from published text. A rule with no
    terms is *derived*: it is satisfied by its prerequisites alone (a startup is a
    semiconductor company that is also early-stage — no sentence says so directly).

    ``requires`` is an AND list; ``requires_any`` is an AND of OR-groups. Both may
    name another rule's key or a ``fact:<name>``. That is the whole dependency
    language, and it is enough to express every rule in the shipped pack.
    """

    key: str
    label: str
    kind: RuleKind
    terms: tuple[str, ...] = ()
    weight: float = 1.0
    #: Lower sorts first — controls both evaluation order and how ties are ranked.
    priority: int = 100
    enabled: bool = True
    category: str = ""                    # signal category, or technology group
    base_confidence: float = 0.6
    max_confidence: float = 1.0
    min_matches: int = 1
    requires: tuple[str, ...] = ()
    requires_any: tuple[tuple[str, ...], ...] = ()
    excludes: tuple[str, ...] = ()        # satisfied only if none of these matched
    sources: tuple[str, ...] = ()         # only for candidates from these sources
    fields: tuple[str, ...] = ()          # restrict where terms are looked for
    core: bool = False                    # classification: a core semiconductor market
    signal_type: str = ""                 # signal: stable machine-readable type
    explanation: str = ""

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("a rule needs a key")
        if not self.terms and not (self.requires or self.requires_any or self.sources):
            raise ValueError(f"rule {self.key!r} matches nothing: give it terms, "
                             f"prerequisites or sources")

    @property
    def type_name(self) -> str:
        return self.signal_type or self.key

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "label": self.label, "kind": self.kind.value,
            "terms": list(self.terms), "weight": self.weight, "priority": self.priority,
            "enabled": self.enabled, "category": self.category,
            "base_confidence": self.base_confidence, "min_matches": self.min_matches,
            "requires": list(self.requires),
            "requires_any": [list(g) for g in self.requires_any],
            "excludes": list(self.excludes), "sources": list(self.sources),
            "fields": list(self.fields), "core": self.core,
            "signal_type": self.signal_type, "explanation": self.explanation,
        }


#: Tunables a pack may override. Every one is read by name, so an overlay that sets
#: an unknown key is a warning rather than a crash.
DEFAULT_THRESHOLDS: dict[str, float] = {
    # Priority band floors, checked most-urgent first.
    "priority_critical": 0.75,
    "priority_high": 0.55,
    "priority_medium": 0.35,
    # A signal below this is detected but not reported — it is noise, not evidence.
    "signal_min_confidence": 0.3,
    # Extra confidence per additional distinct piece of evidence for one rule.
    "match_step": 0.1,
    # Saturation points for the priority factors: the amount of evidence at which a
    # factor reads 1.0. Summed signal confidence for the signal factors, distinct
    # technologies for the overlap factor.
    "technology_target": 3.0,
    "engineering_target": 2.0,
    "funding_target": 1.5,
    "strategic_target": 2.0,
    # "Recently founded" window, in years, for the startup facts.
    "recent_years": 6.0,
    # Distinct evidence items at which evidence coverage reaches 1.0.
    "evidence_target": 8.0,
    # How the record's own confidence is composed. Sums to 1.0 by convention;
    # the calculation normalizes anyway, so a partial override cannot skew it.
    "confidence_classification": 0.4,
    "confidence_discovery": 0.3,
    "confidence_evidence": 0.3,
}

#: Priority factor weights. 0 disables a factor entirely — it is not evaluated and
#: does not enter the normalizing total, so zeroing one cannot shift the others.
DEFAULT_WEIGHTS: dict[str, float] = {
    "semiconductor_relevance": 3.0,
    "technology_overlap": 2.5,
    "engineering_activity": 2.0,
    "strategic_importance": 1.5,
    "funding_activity": 1.0,
    "discovery_confidence": 1.0,
    "company_maturity": 0.5,
}


@dataclass(frozen=True, slots=True)
class RulePack:
    """A named, versioned set of rules plus its thresholds and weights.

    Versioned because a stored intelligence record is only reproducible against the
    pack that produced it — a dashboard showing "HIGH" must be able to say which
    rules said so.
    """

    name: str = "semiconductor"
    version: str = "1.0"
    rules: tuple[Rule, ...] = ()
    thresholds: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_THRESHOLDS))
    weights: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    # ------------------------------------------------------------- lookup
    def of_kind(self, kind: RuleKind) -> tuple[Rule, ...]:
        """Enabled rules of one kind, in deterministic (priority, key) order."""
        return tuple(sorted((r for r in self.rules if r.enabled and r.kind is kind),
                            key=lambda r: (r.priority, r.key)))

    def rule(self, key: str) -> Rule | None:
        for r in self.rules:
            if r.key == key:
                return r
        return None

    def threshold(self, name: str) -> float:
        return float(self.thresholds.get(name, DEFAULT_THRESHOLDS.get(name, 0.0)))

    def weight(self, name: str) -> float:
        return float(self.weights.get(name, DEFAULT_WEIGHTS.get(name, 0.0)))

    @property
    def enabled_keys(self) -> tuple[str, ...]:
        return tuple(sorted(r.key for r in self.rules if r.enabled))

    # ------------------------------------------------------------- overlays
    def with_overrides(
        self,
        *,
        disabled: Iterable[str] = (),
        enabled: Iterable[str] = (),
        thresholds: Mapping[str, float] | None = None,
        weights: Mapping[str, float] | None = None,
        extra_terms: Mapping[str, Iterable[str]] | None = None,
        rules: Iterable[Rule] = (),
        version: str = "",
    ) -> "RulePack":
        """A new pack with configuration applied. Never mutates — packs are shared."""
        off = {k.strip().lower() for k in disabled if k and k.strip()}
        on = {k.strip().lower() for k in enabled if k and k.strip()}
        extra = {k.strip().lower(): tuple(v) for k, v in (extra_terms or {}).items()}

        merged: dict[str, Rule] = {r.key: r for r in self.rules}
        for rule in rules:      # an overlay rule replaces a built-in of the same key
            merged[rule.key] = rule

        out: list[Rule] = []
        for rule in merged.values():
            changed: dict[str, Any] = {}
            if rule.key in off:
                changed["enabled"] = False
            elif on and rule.key in on:
                changed["enabled"] = True
            added = tuple(t for t in _clean_terms(extra.get(rule.key, ()))
                          if t not in rule.terms)
            if added:
                changed["terms"] = rule.terms + added
            out.append(replace(rule, **changed) if changed else rule)

        return RulePack(
            name=self.name,
            version=version or self.version,
            rules=tuple(sorted(out, key=lambda r: (r.priority, r.key))),
            thresholds={**self.thresholds, **(thresholds or {})},
            weights={**self.weights, **(weights or {})},
        )

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "version": self.version,
                "thresholds": dict(self.thresholds), "weights": dict(self.weights),
                "rules": [r.as_dict() for r in self.rules]}


def _clean_terms(values: Iterable[str]) -> tuple[str, ...]:
    """Lower-cased, whitespace-collapsed, de-duplicated, order preserved."""
    out: list[str] = []
    for value in values or ():
        term = _WS.sub(" ", str(value or "").strip().lower())
        if term and term not in out:
            out.append(term)
    return tuple(out)


# --------------------------------------------------------------- match context
@dataclass(slots=True)
class MatchContext:
    """A candidate decomposed once, for every rule to reuse.

    Building this is the only text processing in the whole layer; the stages below
    do set lookups. That is what keeps a batch of hundreds of candidates cheap
    without any caching machinery.
    """

    fields: tuple[tuple[str, str], ...] = ()          # (name, normalized text)
    tokens: dict[str, frozenset[str]] = field(default_factory=dict)
    facts: frozenset[str] = frozenset()
    sources: frozenset[str] = frozenset()
    #: Keys satisfied so far this evaluation, so later rules can depend on earlier
    #: ones. Populated by the pipeline as each stage completes.
    matched: dict[str, tuple[Evidence, ...]] = field(default_factory=dict)

    def satisfied(self, key: str) -> bool:
        if key.startswith("fact:"):
            return key[5:] in self.facts
        if key.startswith("source:"):
            return key[7:] in self.sources
        return key in self.matched

    def evidence_for(self, key: str) -> tuple[Evidence, ...]:
        if key.startswith("fact:"):
            name = key[5:]
            return (Evidence("candidate", name),) if name in self.facts else ()
        if key.startswith("source:"):
            name = key[7:]
            return (Evidence("source", name),) if name in self.sources else ()
        return self.matched.get(key, ())

    def record(self, key: str, evidence: tuple[Evidence, ...]) -> None:
        self.matched[key] = evidence


_EARLY_STAGES = ("pre-seed", "preseed", "seed", "angel", "series a", "grant",
                 "accelerator", "incubator", "pre seed")

#: How far ``last_seen`` may sit from ``first_seen`` and still count as one sighting.
#: Both are stamped during the same discovery run but not on the same instruction, so
#: they differ by microseconds; a second sighting is a separate run, minutes or days
#: later. Anything inside this window is the first sighting.
_FIRST_SIGHTING_WINDOW_SECONDS = 60.0


def _first_sighting(candidate: DiscoveryCandidate) -> bool:
    """True when the platform has seen this company exactly once."""
    first, last = candidate.first_seen, candidate.last_seen
    if first is None or last is None:
        return False
    try:
        return abs((last - first).total_seconds()) <= _FIRST_SIGHTING_WINDOW_SECONDS
    except TypeError:      # one naive, one aware — not comparable, so claim nothing
        return False


def build_context(candidate: DiscoveryCandidate, *, pack: RulePack,
                  now_year: int) -> MatchContext:
    """Decompose a candidate into the fields, tokens and facts rules evaluate against.

    Facts are the non-textual truths a rule may depend on — that the company is a
    first sighting, that it is early-stage, that more than one provider reported it.
    They are derived from the candidate alone, so they are as reproducible as the
    text matching.
    """
    meta = candidate.metadata or {}
    raw_fields: list[tuple[str, str]] = [
        ("company_name", candidate.company_name),
        ("description", candidate.description),
        ("industry", candidate.industry),
        ("technologies", " , ".join(candidate.technologies)),
        ("markets", " , ".join(candidate.markets)),
        ("headquarters", candidate.headquarters),
        ("country", candidate.country),
        ("funding_stage", candidate.funding_stage),
        ("employee_count", candidate.employee_count),
        ("source_url", candidate.source_url),
        ("headline", str(meta.get("headline") or "")),
        ("programme", str(meta.get("programme") or "")),
    ]
    fields: list[tuple[str, str]] = []
    tokens: dict[str, frozenset[str]] = {}
    for name, value in raw_fields:
        text = _WS.sub(" ", str(value or "").lower()).strip()
        if not text:
            continue
        fields.append((name, text))
        tokens[name] = frozenset(_TOKEN.findall(text))

    facts: set[str] = set()
    if candidate.website:
        facts.add("has_website")
    if len(candidate.description or "") >= 40:
        facts.add("has_description")
    if len(set(candidate.sources)) > 1:
        facts.add("multi_source")
    if candidate.company_domain:
        facts.add("has_domain")
    if _first_sighting(candidate):
        facts.add("first_sighting")
    stage = (candidate.funding_stage or "").strip().lower()
    if stage:
        facts.add("has_funding_stage")
        if any(s in stage for s in _EARLY_STAGES):
            facts.add("early_stage")
    year = str(candidate.founded_year or "").strip()
    if year.isdigit():
        facts.add("has_founded_year")
        if 0 <= now_year - int(year) <= int(pack.threshold("recent_years")):
            facts.add("recently_founded")

    return MatchContext(
        fields=tuple(fields), tokens=tokens, facts=frozenset(facts),
        sources=frozenset(s for s in candidate.sources if s),
    )


# ------------------------------------------------------------------ evaluation
def match_terms(context: MatchContext, terms: Iterable[str],
                *, fields: Iterable[str] = ()) -> tuple[Evidence, ...]:
    """Every (field, term) pair the candidate's text supports, in stable order.

    Order is field order then term order — never dict or set order — so the same
    candidate always produces byte-identical evidence.
    """
    wanted = {f for f in fields} if fields else None
    terms = tuple(terms)
    out: list[Evidence] = []
    for name, text in context.fields:
        if wanted is not None and name not in wanted:
            continue
        field_tokens = context.tokens.get(name, frozenset())
        for term in terms:
            hit = (_phrase_pattern(term).search(text) if _is_phrase(term)
                   else term in field_tokens)
            if hit:
                out.append(Evidence(name, term))
    return tuple(out)


@dataclass(frozen=True, slots=True)
class RuleMatch:
    rule: Rule
    confidence: float
    evidence: tuple[Evidence, ...]

    @property
    def key(self) -> str:
        return self.rule.key


def evaluate_rule(rule: Rule, context: MatchContext, *, pack: RulePack) -> RuleMatch | None:
    """Evaluate one rule against one candidate. ``None`` when it is not satisfied.

    Confidence rises with corroboration: the rule's base, plus a configured step for
    each additional distinct piece of evidence, capped by the rule's own ceiling. Two
    independent mentions of "ASIC" are worth more than one, and neither is worth more
    than certainty.
    """
    if not rule.enabled:
        return None
    if rule.sources and not (context.sources & set(rule.sources)):
        return None
    for key in rule.excludes:
        if context.satisfied(key):
            return None
    for key in rule.requires:
        if not context.satisfied(key):
            return None
    for group in rule.requires_any:
        if not any(context.satisfied(k) for k in group):
            return None

    evidence = match_terms(context, rule.terms, fields=rule.fields) if rule.terms else ()
    if rule.terms and len(evidence) < max(1, rule.min_matches):
        return None

    if not rule.terms:
        # Derived rule: it borrows the evidence of everything it depended on, so the
        # explanation still points at published facts rather than at other rules.
        inherited: list[Evidence] = []
        for key in (*rule.requires, *(k for g in rule.requires_any for k in g)):
            if context.satisfied(key):
                inherited.extend(context.evidence_for(key))
        for name in rule.sources:
            if name in context.sources:
                inherited.append(Evidence("source", name))
        evidence = tuple(dict.fromkeys(inherited))

    step = pack.threshold("match_step")
    distinct = len({(e.field, e.term) for e in evidence}) or 1
    confidence = min(rule.max_confidence,
                     round(rule.base_confidence + step * (distinct - 1), 4))
    return RuleMatch(rule=rule, confidence=confidence, evidence=evidence)


def evaluate_kind(pack: RulePack, kind: RuleKind, context: MatchContext) -> list[RuleMatch]:
    """Every satisfied rule of one kind, recorded into the context as it goes.

    Recording as it goes is what lets a later rule in the same pass depend on an
    earlier one — evaluation order is the pack's declared priority, which is why that
    ordering is configuration rather than an accident of file layout.
    """
    matches: list[RuleMatch] = []
    for rule in pack.of_kind(kind):
        match = evaluate_rule(rule, context, pack=pack)
        if match is None:
            continue
        context.record(rule.key, match.evidence)
        matches.append(match)
    return matches


# --------------------------------------------------------------------- loading
def load_overlay(path: str | Path) -> dict[str, Any]:
    """Read a rule-pack overlay from JSON. Empty dict when unreadable.

    An unreadable overlay must not take the platform down: it falls back to the
    built-in pack and logs loudly, because running with the shipped rules is always
    better than not running.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
        data = json.loads(raw)
    except FileNotFoundError:
        logger.error("[intelligence] rule pack %s not found — using built-in rules", path)
        return {}
    except (OSError, ValueError):
        logger.error("[intelligence] rule pack %s is unreadable — using built-in rules",
                     path, exc_info=True)
        return {}
    if not isinstance(data, dict):
        logger.error("[intelligence] rule pack %s is not a JSON object — ignored", path)
        return {}
    return data


def rules_from_json(entries: Iterable[Mapping[str, Any]]) -> tuple[Rule, ...]:
    """Build rules from overlay JSON, skipping (and logging) malformed entries."""
    out: list[Rule] = []
    for entry in entries or ():
        try:
            kind = RuleKind(str(entry.get("kind", "signal")).lower())
            out.append(Rule(
                key=str(entry["key"]).strip().lower(),
                label=str(entry.get("label") or entry["key"]),
                kind=kind,
                terms=_clean_terms(entry.get("terms", ())),
                weight=float(entry.get("weight", 1.0)),
                priority=int(entry.get("priority", 100)),
                enabled=bool(entry.get("enabled", True)),
                category=str(entry.get("category", "")),
                base_confidence=float(entry.get("base_confidence", 0.6)),
                max_confidence=float(entry.get("max_confidence", 1.0)),
                min_matches=int(entry.get("min_matches", 1)),
                requires=tuple(entry.get("requires", ()) or ()),
                requires_any=tuple(tuple(g) for g in (entry.get("requires_any", ()) or ())),
                excludes=tuple(entry.get("excludes", ()) or ()),
                sources=tuple(str(s).lower() for s in (entry.get("sources", ()) or ())),
                fields=tuple(entry.get("fields", ()) or ()),
                core=bool(entry.get("core", False)),
                signal_type=str(entry.get("signal_type", "")),
                explanation=str(entry.get("explanation", "")),
            ))
        except (KeyError, TypeError, ValueError):
            logger.error("[intelligence] skipping malformed rule %r", entry, exc_info=True)
    return tuple(out)
