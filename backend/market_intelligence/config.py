"""Environment-driven configuration for the Market Intelligence Layer.

Every business decision the layer makes — which categories exist, which words mean
what, where the priority bands fall, how much each factor counts — is configuration,
resolved here into an immutable :class:`IntelligenceConfig` plus the
:class:`~backend.market_intelligence.rules.RulePack` it selects.

Resolution order, weakest first:

1. the built-in pack named by ``SP_INTELLIGENCE_RULE_PACK``;
2. a JSON overlay at ``SP_INTELLIGENCE_RULES_PATH`` (adds/replaces rules, and may
   set thresholds and weights);
3. explicit environment overrides (enable/disable lists, extra vocabulary, the
   individual priority thresholds).

An unreadable or malformed overlay degrades to the built-in pack with a loud log
rather than failing the run: shipped rules always beat no intelligence at all.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Mapping

from backend.market_intelligence.rules import RulePack, load_overlay, rules_from_json
from backend.market_intelligence.vocabulary import BUILTIN_PACKS, default_pack

logger = logging.getLogger("market_intelligence.config")


def _split(raw: str) -> tuple[str, ...]:
    """Comma-separated list → normalized, de-duplicated tuple."""
    out: list[str] = []
    for part in (raw or "").split(","):
        name = part.strip().lower()
        if name and name not in out:
            out.append(name)
    return tuple(out)


def _json_object(raw: str, *, what: str) -> dict[str, Any]:
    """Parse a JSON object from an environment value. ``{}`` when absent or broken."""
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except ValueError:
        logger.error("[intelligence] %s is not valid JSON — ignored", what)
        return {}
    if not isinstance(data, dict):
        logger.error("[intelligence] %s must be a JSON object — ignored", what)
        return {}
    return data


def _floats(data: Mapping[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, value in data.items():
        try:
            out[str(key)] = float(value)
        except (TypeError, ValueError):
            logger.error("[intelligence] ignoring non-numeric override %s=%r", key, value)
    return out


@dataclass(frozen=True, slots=True)
class IntelligenceConfig:
    """Runtime knobs. Built from :class:`backend.config.Settings` in production."""

    enabled: bool = True
    pack: RulePack = field(default_factory=default_pack)
    #: Candidates read from the store in one pass. Bounds memory and run time when a
    #: discovery run has just added thousands of rows.
    batch_size: int = 200
    #: Ceiling on candidates evaluated per run. 0 = unbounded.
    max_candidates: int = 2000
    #: Threads used to evaluate a batch. Evaluation is pure CPU string matching, so
    #: >1 helps only when a future enricher does I/O; output order is fixed either way.
    concurrency: int = 1
    #: Re-evaluate every candidate rather than only those changed since last time.
    #: The way to roll out a rule change over existing data.
    reprocess_all: bool = False
    log_level: str = ""

    @property
    def rule_pack_name(self) -> str:
        return self.pack.name

    @classmethod
    def from_settings(cls, settings) -> "IntelligenceConfig":
        return cls(
            enabled=bool(getattr(settings, "intelligence_enabled", True)),
            pack=build_pack(settings),
            batch_size=int(getattr(settings, "intelligence_batch_size", 200)),
            max_candidates=int(getattr(settings, "intelligence_max_candidates", 2000)),
            concurrency=int(getattr(settings, "intelligence_concurrency", 1)),
            reprocess_all=bool(getattr(settings, "intelligence_reprocess_all", False)),
            log_level=str(getattr(settings, "intelligence_log_level", "") or ""),
        )


def build_pack(settings) -> RulePack:
    """Resolve the effective rule pack for this environment."""
    name = str(getattr(settings, "intelligence_rule_pack", "") or "semiconductor").lower()
    factory = BUILTIN_PACKS.get(name)
    if factory is None:
        logger.error("[intelligence] unknown rule pack %r — falling back to 'semiconductor'",
                     name)
        factory = default_pack
    pack = factory()

    overlay_path = str(getattr(settings, "intelligence_rules_path", "") or "").strip()
    if overlay_path:
        pack = apply_overlay(pack, load_overlay(overlay_path))

    thresholds = _floats(_json_object(
        getattr(settings, "intelligence_thresholds_raw", ""), what="SP_INTELLIGENCE_THRESHOLDS"))
    # The individual band settings are the documented way to move a threshold, so
    # they win over the same key supplied through the JSON blob.
    for key, setting in (("priority_critical", "intelligence_priority_critical"),
                         ("priority_high", "intelligence_priority_high"),
                         ("priority_medium", "intelligence_priority_medium"),
                         ("signal_min_confidence", "intelligence_signal_min_confidence")):
        value = getattr(settings, setting, None)
        if value is not None:
            thresholds[key] = float(value)

    weights = _floats(_json_object(
        getattr(settings, "intelligence_weights_raw", ""), what="SP_INTELLIGENCE_WEIGHTS"))
    extra_terms = {
        str(k).lower(): [str(t) for t in (v if isinstance(v, (list, tuple)) else [v])]
        for k, v in _json_object(getattr(settings, "intelligence_extra_terms_raw", ""),
                                 what="SP_INTELLIGENCE_EXTRA_TERMS").items()
    }

    return pack.with_overrides(
        disabled=_split(getattr(settings, "intelligence_disabled_rules_raw", "")),
        enabled=_split(getattr(settings, "intelligence_enabled_rules_raw", "")),
        thresholds=thresholds, weights=weights, extra_terms=extra_terms,
    )


def apply_overlay(pack: RulePack, overlay: Mapping[str, Any]) -> RulePack:
    """Fold a JSON overlay into a pack. An empty overlay returns the pack unchanged."""
    if not overlay:
        return pack
    rules = rules_from_json(overlay.get("rules", ()) or ())
    version = str(overlay.get("version", "") or "")
    out = pack.with_overrides(
        disabled=[str(k) for k in (overlay.get("disable", ()) or ())],
        enabled=[str(k) for k in (overlay.get("enable", ()) or ())],
        thresholds=_floats(overlay.get("thresholds", {}) or {}),
        weights=_floats(overlay.get("weights", {}) or {}),
        extra_terms=overlay.get("extra_terms", {}) or {},
        rules=rules,
        # A pack whose rules changed is a different pack: stored records name the
        # version that produced them, so it must move when the rules do.
        version=version or f"{pack.version}+overlay",
    )
    logger.info("[intelligence] rule pack %s@%s loaded with overlay (%d rule(s) added)",
                out.name, out.version, len(rules))
    return out
