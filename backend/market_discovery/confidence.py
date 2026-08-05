"""Deterministic confidence scoring.

No machine learning, no heuristics that drift: the same candidate always scores the
same, on any machine, in any run. That is a hard requirement — confidence gates
whether a candidate is promoted, and a non-reproducible gate is not auditable.

The score is a weighted sum of independent boolean factors, normalized to 0..1 by
the total weight of the factors that were *evaluated*. Normalizing by the evaluated
total (not the maximum possible) means adding a new factor doesn't silently deflate
every historical score.

Weights are configuration, not code — :class:`ConfidenceConfig` is built from
settings, so tuning the model is an environment change.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.market_discovery.schemas import DiscoveryCandidate

# Domain vocabulary. Deliberately explicit and inspectable rather than learned —
# an analyst can read this list and predict the score.
SEMICONDUCTOR_KEYWORDS: frozenset[str] = frozenset({
    "semiconductor", "silicon", "chip", "chipset", "asic", "soc", "fpga", "rtl",
    "vlsi", "eda", "ip core", "tapeout", "foundry", "fab", "wafer", "lithography",
    "packaging", "osat", "atmp", "analog", "mixed signal", "rf", "photonics",
    "mems", "sensor", "processor", "cpu", "gpu", "npu", "dsp", "microcontroller",
    "mcu", "risc-v", "riscv", "arm", "hbm", "dram", "nand", "sram", "flash",
    "interconnect", "chiplet", "substrate", "verification", "physical design",
    "place and route", "signal integrity", "power management", "pmic", "sic",
    "gan", "compound semiconductor", "epitaxy", "yield", "test and measurement",
})

_FUNDING_STAGES: frozenset[str] = frozenset({
    "pre-seed", "preseed", "seed", "angel", "series a", "series b", "series c",
    "series d", "series e", "series f", "growth", "late stage", "ipo", "acquired",
    "grant", "debt", "bridge", "strategic",
})

_CAREERS_HINT = re.compile(r"/(careers?|jobs?|join-us|work-with-us|opportunities)\b", re.I)
_WORD = re.compile(r"[a-z0-9+#.-]+")


@dataclass(slots=True)
class ConfidenceConfig:
    """Factor weights and the promotion threshold.

    A weight of 0 disables a factor entirely — it is not evaluated and does not
    contribute to the normalizing total, so zeroing one cannot shift the others.
    """

    website: float = 2.0
    company_domain: float = 2.0
    linkedin_url: float = 1.5
    multiple_sources: float = 2.5        # strongest single signal: independent corroboration
    semiconductor_keywords: float = 2.0
    careers_page: float = 1.0
    funding_information: float = 1.0
    description: float = 0.5
    headquarters: float = 0.5
    founded_year: float = 0.5

    #: Minimum score for a candidate to be promoted rather than parked for review.
    #: Calibrated against single-source candidates, which is the normal case: the
    #: corroboration, careers and funding factors are usually unavailable at
    #: discovery time, so a well-identified in-market company scores ~0.48 and a
    #: company that cannot be placed in the market scores ~0.30. 0.45 separates
    #: those two; raise it once several connectors are live and corroboration is real.
    threshold: float = 0.45

    def weights(self) -> dict[str, float]:
        return {
            "website": self.website,
            "company_domain": self.company_domain,
            "linkedin_url": self.linkedin_url,
            "multiple_sources": self.multiple_sources,
            "semiconductor_keywords": self.semiconductor_keywords,
            "careers_page": self.careers_page,
            "funding_information": self.funding_information,
            "description": self.description,
            "headquarters": self.headquarters,
            "founded_year": self.founded_year,
        }

    @classmethod
    def from_settings(cls, settings) -> "ConfidenceConfig":
        """Build from :class:`backend.config.Settings`, falling back to defaults."""
        return cls(threshold=getattr(settings, "discovery_confidence_threshold", cls.threshold))


@dataclass(slots=True)
class ConfidenceScore:
    value: float
    factors: dict[str, float] = field(default_factory=dict)   # factor -> weight earned

    @property
    def matched(self) -> tuple[str, ...]:
        return tuple(sorted(k for k, v in self.factors.items() if v > 0))


def has_semiconductor_signal(candidate: DiscoveryCandidate) -> bool:
    """True when the candidate's own text places it in the semiconductor market.

    Matched against a word-boundary tokenization so "chipotle" never matches "chip",
    while multi-word phrases ("physical design") are checked as substrings of the
    normalized haystack.
    """
    haystack = " ".join([
        candidate.company_name, candidate.description, candidate.industry,
        " ".join(candidate.technologies), " ".join(candidate.markets),
    ]).lower()
    if not haystack.strip():
        return False
    tokens = set(_WORD.findall(haystack))
    for keyword in SEMICONDUCTOR_KEYWORDS:
        if " " in keyword or "-" in keyword:
            if keyword in haystack:
                return True
        elif keyword in tokens:
            return True
    return False


def has_careers_page(candidate: DiscoveryCandidate) -> bool:
    """A careers page means the company is hiring — the platform's core demand signal."""
    if _CAREERS_HINT.search(candidate.source_url or ""):
        return True
    for value in candidate.metadata.get("links", ()) or ():
        if _CAREERS_HINT.search(str(value)):
            return True
    return bool(candidate.metadata.get("careers_url"))


def has_funding_information(candidate: DiscoveryCandidate) -> bool:
    stage = (candidate.funding_stage or "").strip().lower()
    if stage and (stage in _FUNDING_STAGES or any(s in stage for s in _FUNDING_STAGES)):
        return True
    return bool(candidate.metadata.get("funding_amount") or candidate.metadata.get("investors"))


class ConfidenceEngine:
    """Scores candidates. Stateless and pure — safe to share across threads."""

    def __init__(self, config: ConfidenceConfig | None = None) -> None:
        self.config = config or ConfidenceConfig()

    def evaluate(self, candidate: DiscoveryCandidate) -> ConfidenceScore:
        checks: dict[str, bool] = {
            "website": bool(candidate.website),
            "company_domain": bool(candidate.company_domain),
            "linkedin_url": bool(candidate.linkedin_url),
            "multiple_sources": len(set(candidate.sources)) > 1,
            "semiconductor_keywords": has_semiconductor_signal(candidate),
            "careers_page": has_careers_page(candidate),
            "funding_information": has_funding_information(candidate),
            "description": len(candidate.description) >= 40,
            "headquarters": bool(candidate.headquarters or candidate.country),
            "founded_year": bool(candidate.founded_year),
        }
        weights = self.config.weights()
        total = 0.0
        earned = 0.0
        factors: dict[str, float] = {}
        for name, passed in checks.items():
            weight = weights.get(name, 0.0)
            if weight <= 0:
                continue          # disabled: not evaluated, not in the denominator
            total += weight
            gained = weight if passed else 0.0
            earned += gained
            factors[name] = gained
        value = round(earned / total, 4) if total else 0.0
        return ConfidenceScore(value=value, factors=factors)

    def score(self, candidate: DiscoveryCandidate) -> float:
        return self.evaluate(candidate).value

    def meets_threshold(self, value: float) -> bool:
        return value >= self.config.threshold
