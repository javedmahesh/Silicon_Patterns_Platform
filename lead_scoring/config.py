"""Lead Scoring configuration — the single tunable surface for the formula.

Loaded from ``config/lead_scoring.json`` (falls back to :meth:`ScoringConfig.default`).
Nothing in the formula is hardcoded in the scorer; change weights / multipliers /
grade bands here and re-run, no code edits.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config" / "lead_scoring.json"
# v2: adds the optional, separate human-review score adjustment (model score unchanged).
MODEL_VERSION = "lead-scoring-v2"


@dataclass(slots=True)
class ScoringConfig:
    weights: dict[str, float]
    region_mult: dict[str, float]
    prospect_mult: dict[str, float]
    tier_mult: dict[str, float]
    grade_bands: dict[str, float]
    confidence_bands: dict[str, int] = field(default_factory=lambda: {"high": 3, "medium": 2})
    coverage_normalization: float = 1.0
    demand_reference: float = 100.0
    opportunity_multi_bonus: float = 5.0
    dm_points_senior: float = 25.0
    dm_points_other: float = 12.0
    dm_cap: float = 100.0
    # Optional human-review → score adjustment (P-task viii / reconciled Change_05). OFF by
    # default: the model score is NEVER changed; a SEPARATE adjusted score is derived from the
    # company's current lead_reviews.review_status. See lead_scoring/human_review.adjusted_score.
    review_feedback: dict = field(default_factory=dict)
    model_version: str = MODEL_VERSION

    @classmethod
    def default(cls) -> "ScoringConfig":
        return cls(
            weights={"opportunity": 0.30, "demand": 0.30, "readiness": 0.20, "decision_maker": 0.20},
            region_mult={"APPROVED": 1.0, "REVIEW_REQUIRED": 0.85, "EXCLUDED_REGION": 0.3, "UNKNOWN": 0.9},
            prospect_mult={"PRODUCT_COMPANY": 1.0, "SERVICE_PROVIDER": 0.7, "EDA_VENDOR": 0.6,
                           "FOUNDRY": 0.6, "INVESTOR": 0.4, "PUBLISHER": 0.2, "ACADEMIC": 0.3, "UNKNOWN": 0.9},
            tier_mult={"STARTUP": 1.0, "SCALEUP": 1.0, "ESTABLISHED": 0.8, "INCUMBENT": 0.85, "UNKNOWN": 0.9},
            grade_bands={"A+": 70.0, "A": 50.0, "B": 30.0},
            confidence_bands={"high": 3, "medium": 2},
            coverage_normalization=1.0,
            review_feedback={
                "enabled": False,
                "status_effects": {
                    "strategic_account": {"boost": 1.15, "floor_grade": "A"},
                    "approved": {"boost": 1.05},
                    "disqualified": {"penalty": 0.6},
                    "watchlist": {},
                    "needs_review": {},
                },
            },
        )

    @classmethod
    def load(cls, path: str | Path = _DEFAULT_PATH) -> "ScoringConfig":
        p = Path(path)
        if not p.exists():
            return cls.default()
        d = json.loads(p.read_text(encoding="utf-8"))
        base = cls.default()
        return cls(
            weights=d.get("weights", base.weights),
            region_mult=d.get("region_mult", base.region_mult),
            prospect_mult=d.get("prospect_mult", base.prospect_mult),
            tier_mult=d.get("tier_mult", base.tier_mult),
            grade_bands=d.get("grade_bands", base.grade_bands),
            confidence_bands=d.get("confidence_bands", base.confidence_bands),
            coverage_normalization=float(d.get("coverage_normalization", base.coverage_normalization)),
            demand_reference=float(d.get("demand_reference", base.demand_reference)),
            opportunity_multi_bonus=float(d.get("opportunity_multi_bonus", base.opportunity_multi_bonus)),
            dm_points_senior=float(d.get("dm_points_senior", base.dm_points_senior)),
            dm_points_other=float(d.get("dm_points_other", base.dm_points_other)),
            dm_cap=float(d.get("dm_cap", base.dm_cap)),
            review_feedback=d.get("review_feedback", base.review_feedback),
            model_version=d.get("model_version", base.model_version),
        )

    # --- multiplier lookups (default to the UNKNOWN bucket) ---
    def region_for(self, flag: str | None) -> float:
        return float(self.region_mult.get(flag or "UNKNOWN", self.region_mult.get("UNKNOWN", 0.9)))

    def prospect_for(self, prospect: str | None) -> float:
        return float(self.prospect_mult.get(prospect or "UNKNOWN", self.prospect_mult.get("UNKNOWN", 0.9)))

    def tier_for(self, tier: str | None) -> float:
        return float(self.tier_mult.get(tier or "UNKNOWN", self.tier_mult.get("UNKNOWN", 0.9)))

    def grade_for(self, score: float) -> str:
        if score >= self.grade_bands["A+"]:
            return "A+"
        if score >= self.grade_bands["A"]:
            return "A"
        if score >= self.grade_bands["B"]:
            return "B"
        return "C"

    def confidence_for(self, coverage: int) -> str:
        """Map the count of present engine signals (0-3) to a confidence label."""
        if coverage >= self.confidence_bands.get("high", 3):
            return "high"
        if coverage >= self.confidence_bands.get("medium", 2):
            return "medium"
        return "low"

    # --- human-review → score adjustment (reconciled Change_05) ---
    @property
    def review_feedback_enabled(self) -> bool:
        return bool(self.review_feedback.get("enabled", False))

    def review_effect(self, status: str | None) -> dict:
        """The configured score effect for a review status (``{}`` if none)."""
        return self.review_feedback.get("status_effects", {}).get(status or "", {}) or {}

    def status_affects_score(self, status: str | None) -> bool:
        """True if this review status has a real configured effect (boost/penalty/floor).
        Drives the mandatory-reason + RBAC gates (only meaningful when enabled)."""
        e = self.review_effect(status)
        return bool(e.get("boost") or e.get("penalty") or e.get("floor_grade"))

    def grade_threshold(self, grade: str | None) -> float:
        """The minimum score for a grade (C → 0.0)."""
        return float(self.grade_bands.get(grade or "", 0.0))
