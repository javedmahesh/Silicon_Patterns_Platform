"""Pure logic for the human lead-review system (P-task viii + reconciled Change_05).

The human assessment *complements* the model score — it never overwrites it. The
model ``lead_score``/``grade`` stay pristine; this derives a SEPARATE **adjusted**
score/grade from the company's current review status (only when the feature is
enabled in config). All DB-free + deterministic, so it unit-tests in isolation and
is reused by both the scorer (``lead_scoring/service.py``) and the API.
"""
from __future__ import annotations

from config.enums import LEAD_GRADES, LEAD_REVIEW_STATUSES

__all__ = ["adjusted_score", "disagreement", "LEAD_GRADES", "LEAD_REVIEW_STATUSES"]


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def adjusted_score(model_score: float | None, model_grade: str | None,
                   review_status: str | None, cfg, *, expired: bool = False):
    """Derive ``(adjusted_score, adjusted_grade, rationale)`` from the PRISTINE model
    score + the company's current review status.

    The model score is never mutated. **Anti-stacking:** the adjustment is always
    computed from ``model_score`` (never a previous adjusted value), so it is
    idempotent and cannot compound across re-scores or repeated submits. When the
    feature is off, there is no status, the status has no effect, or the review has
    **expired**, the model values are returned unchanged (adjusted == model).
    """
    base = float(model_score or 0.0)
    grade = (model_grade or "").strip() or cfg.grade_for(base)

    if expired:
        return base, grade, {"status": review_status or "", "expired": True}
    if not cfg.review_feedback_enabled or not review_status:
        return base, grade, {}
    effect = cfg.review_effect(review_status)
    if not effect:
        return base, grade, {}

    adj = base
    rationale: dict = {"status": review_status, "model_score": round(base, 2), "model_grade": grade}
    if effect.get("boost"):
        adj *= float(effect["boost"])
        rationale["boost"] = float(effect["boost"])
    if effect.get("penalty"):
        adj *= float(effect["penalty"])
        rationale["penalty"] = float(effect["penalty"])
    adj = _clamp(adj)

    floor_grade = effect.get("floor_grade")
    if floor_grade:
        floor = cfg.grade_threshold(floor_grade)
        if adj < floor:
            rationale["floor_grade"] = floor_grade
            rationale["floor_lifted_from"] = round(adj, 2)
            adj = floor
    adj = _clamp(adj)

    adj_grade = cfg.grade_for(adj)
    rationale["adjusted_score"] = round(adj, 2)
    rationale["adjusted_grade"] = adj_grade
    return adj, adj_grade, rationale


# Grade tiers used to detect model/human disagreement (for the review reports).
_HIGH_GRADES = frozenset({"A+", "A"})
_LOW_GRADES = frozenset({"B", "C"})


def disagreement(model_grade: str | None, human_status: str | None) -> str | None:
    """Classify a model/human mismatch for the review reports, else ``None``.

    * ``false_positive`` — the model rated the lead highly (A+/A) but a human
      **disqualified** it (the model over-valued it).
    * ``false_negative`` — the model rated it low (B/C) but a human flagged it as
      a **strategic_account** or **approved** it (the model under-valued it).
    """
    grade = (model_grade or "").strip()
    status = (human_status or "").strip()
    if grade in _HIGH_GRADES and status == "disqualified":
        return "false_positive"
    if grade in _LOW_GRADES and status in ("strategic_account", "approved"):
        return "false_negative"
    return None
