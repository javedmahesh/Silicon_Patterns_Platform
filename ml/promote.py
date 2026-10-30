"""Model promotion + rollback — a gated, manual, auditable workflow.

A candidate becomes production ONLY if: evaluation succeeded, it clears the configured
quality thresholds, AND it outperforms the currently deployed model on the primary
metric. Otherwise the existing production model is kept. Promotion is never automatic.
Rollback re-activates a previous version. Every decision is recorded in ml_model_events.

The production LEAD RANKING is unaffected — this only flips which ML model is 'active'
for offline inference; lead_scores stays the dashboard's ranking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ml import registry
from master_db.models import MlModel


@dataclass
class PromotionResult:
    promoted: bool
    version: str
    reason: str
    metrics: dict = field(default_factory=dict)
    previous_version: str | None = None
    checks: dict = field(default_factory=dict)


def _metric(model: MlModel | None, key: str):
    if model is None:
        return None
    v = (model.metrics or {}).get(key)
    return v


def _eval_succeeded(metrics: dict) -> bool:
    return bool(metrics) and "error" not in metrics and metrics.get("n", 0) > 0 \
        and metrics.get("roc_auc") is not None and metrics.get("pr_auc") is not None


def promote(session: Session, settings, *, model_version: str, thresholds: dict | None = None,
            actor_email: str = "") -> PromotionResult:
    """Promote *model_version* to production iff it evaluates, clears thresholds, and beats
    the current production model. Never promotes automatically — this is the explicit call."""
    name = settings.ml_model_name
    thr = thresholds or settings.promote_thresholds()
    primary = settings.ml_primary_metric
    candidate = registry.get_model(session, model_version, name)
    if candidate is None:
        return PromotionResult(False, model_version, "candidate not found")

    metrics = candidate.metrics or {}
    current = registry.active_model(session, name)
    cur_primary = _metric(current, primary)
    cand_primary = metrics.get(primary)

    eval_ok = _eval_succeeded(metrics)
    thresholds_ok = eval_ok and all(
        (metrics.get(k) is not None and metrics.get(k) >= v) for k, v in thr.items())
    outperforms = (current is None) or (
        cand_primary is not None and cur_primary is not None and cand_primary > cur_primary)

    checks = {
        "evaluation_succeeded": eval_ok,
        "thresholds_met": bool(thresholds_ok),
        "outperforms_current": bool(outperforms),
        "primary_metric": primary,
        "candidate_primary": cand_primary,
        "current_primary": cur_primary,
        "thresholds": thr,
    }

    if not (eval_ok and thresholds_ok and outperforms):
        reason = ("evaluation failed" if not eval_ok else
                  "quality thresholds not met" if not thresholds_ok else
                  "does not outperform current production model")
        registry.record_event(session, model=candidate, action="rejected",
                               detail=reason, metrics=checks, actor_email=actor_email)
        session.commit()
        return PromotionResult(False, model_version, reason, metrics=metrics,
                               previous_version=(current.version if current else None), checks=checks)

    # promote: archive the incumbent, activate the candidate.
    prev = current.version if current else None
    if current is not None and current.id != candidate.id:
        current.status = "archived"
    candidate.status = "active"
    candidate.promoted_at = datetime.now(timezone.utc)
    registry.record_event(session, model=candidate, action="promoted",
                          detail=f"promoted over {prev or '(none)'}", metrics=checks,
                          actor_email=actor_email)
    session.commit()
    return PromotionResult(True, model_version, "promoted", metrics=metrics,
                           previous_version=prev, checks=checks)


def rollback(session: Session, settings, *, to_version: str, actor_email: str = "") -> PromotionResult:
    """Re-activate a previous model version (archiving the current production model)."""
    name = settings.ml_model_name
    target = registry.get_model(session, to_version, name)
    if target is None:
        return PromotionResult(False, to_version, "target version not found")
    current = registry.active_model(session, name)
    if current is not None and current.version == to_version:
        return PromotionResult(False, to_version, "already the production model")
    prev = current.version if current else None
    if current is not None:
        current.status = "archived"
    target.status = "active"
    target.promoted_at = datetime.now(timezone.utc)
    registry.record_event(session, model=target, action="rolled_back",
                          detail=f"rolled back from {prev or '(none)'} to {to_version}",
                          actor_email=actor_email)
    session.commit()
    return PromotionResult(True, to_version, "rolled_back", previous_version=prev)

