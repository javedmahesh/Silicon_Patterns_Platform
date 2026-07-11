"""Dynamic time decay — configurable exponential decay for opportunity strength.

An opportunity's value fades with age, at a rate that depends on WHAT it is: a layoff
signal is stale in weeks, a funding round stays relevant for months. This module turns
that into a *generated feature* — it never modifies the stored opportunity.

    weight = 0.5 ** (age_days / half_life_days[category])

Half-lives are configurable (backend.config.Settings.decay_half_lives) so profiles for
layoffs / hiring / projects / funding are tuned without code changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Opportunity type (upper-cased) -> decay category. Unknown types fall to 'default'.
_CATEGORY_MAP: dict[str, str] = {
    # layoffs / contraction — fade fastest
    "LAYOFF": "layoffs", "LAYOFFS": "layoffs", "DOWNSIZING": "layoffs",
    "RESTRUCTURING": "layoffs", "SHUTDOWN": "layoffs",
    # hiring / people growth
    "HIRING": "hiring", "EXECUTIVE_HIRE": "hiring", "LEADERSHIP_CHANGE": "hiring",
    "ROLE_CHANGE": "hiring",
    # funding / capital events — fade slowest
    "FUNDING": "funding", "IPO": "funding", "ACQUISITION": "funding",
    # projects / product / engineering programs
    "PRODUCT_LAUNCH": "projects", "TAPEOUT": "projects", "ENGINEERING_PROGRAM": "projects",
    "EXPANSION": "projects", "PARTNERSHIP": "projects", "CONTRACT_WIN": "projects",
}

DEFAULT_HALF_LIVES: dict[str, int] = {
    "layoffs": 30, "hiring": 45, "projects": 90, "funding": 120, "default": 60,
}


def decay_category(opportunity_type: str | None) -> str:
    return _CATEGORY_MAP.get((opportunity_type or "").strip().upper(), "default")


def exp_decay(age_days: float, half_life_days: float) -> float:
    """Exponential decay factor in (0, 1]. Negative/zero age clamps to 1.0."""
    if half_life_days <= 0:
        return 1.0
    if age_days <= 0:
        return 1.0
    return float(0.5 ** (age_days / half_life_days))


def decayed_strength(base_score: float, age_days: float, category: str,
                     half_lives: dict[str, int] | None = None) -> float:
    hl = (half_lives or DEFAULT_HALF_LIVES).get(category, (half_lives or DEFAULT_HALF_LIVES)["default"])
    return float(base_score) * exp_decay(age_days, hl)


@dataclass
class DecayFeatures:
    """Per-category decayed opportunity strength + overall summary (a feature bundle)."""

    per_category: dict[str, float] = field(default_factory=dict)   # max decayed strength / category
    overall_max: float = 0.0
    overall_mean: float = 0.0
    active_count: int = 0                                          # decayed strength >= 1.0


def decay_features(items: list[tuple[str, float, float]],
                   half_lives: dict[str, int] | None = None) -> DecayFeatures:
    """Aggregate decayed strength over ``items`` = [(opportunity_type, base_score, age_days)].

    Deterministic. Returns per-category max decayed strength (0 for absent categories),
    plus overall max/mean and a count of still-'active' signals (decayed strength >= 1).
    """
    hl = half_lives or DEFAULT_HALF_LIVES
    per: dict[str, float] = {c: 0.0 for c in ("layoffs", "hiring", "projects", "funding", "default")}
    decayed: list[float] = []
    active = 0
    for opp_type, base, age in items:
        cat = decay_category(opp_type)
        d = decayed_strength(base, age, cat, hl)
        per[cat] = max(per[cat], round(d, 4))
        decayed.append(d)
        if d >= 1.0:
            active += 1
    overall_max = round(max(decayed), 4) if decayed else 0.0
    overall_mean = round(sum(decayed) / len(decayed), 4) if decayed else 0.0
    return DecayFeatures(per_category=per, overall_max=overall_max,
                         overall_mean=overall_mean, active_count=active)


def demo() -> None:
    """Self-check: newer + slower-decaying signals score higher. Run: python -m ml.decay"""
    assert exp_decay(0, 30) == 1.0
    assert abs(exp_decay(30, 30) - 0.5) < 1e-9        # one half-life -> 0.5
    # a 60-day-old funding round (hl=120) outlasts a 60-day-old layoff (hl=30)
    fund = decayed_strength(80, 60, "funding")
    lay = decayed_strength(80, 60, "layoffs")
    assert fund > lay, (fund, lay)
    f = decay_features([("FUNDING", 80, 10), ("LAYOFF", 70, 120), ("PRODUCT_LAUNCH", 60, 0)])
    assert f.per_category["funding"] > 0 and f.per_category["projects"] == 60.0
    assert f.active_count >= 1
    print(f"OK — funding@60d={fund:.1f} > layoff@60d={lay:.1f}; features={f.per_category}")


if __name__ == "__main__":  # pragma: no cover
    demo()
