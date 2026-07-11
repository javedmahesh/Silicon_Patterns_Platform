"""User feedback dataset — capture interactions for future model training.

Stores thumbs up/down, export, contact, ignore against any entity, SEPARATELY from
opportunity data (``user_interactions`` table). Each row carries a configurable
``sample_weight`` the dataset builder uses later. NO model is trained here.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from config.enums import ML_ENTITY_TYPES, ML_INTERACTION_TYPES
from master_db.models import UserInteraction

# Default per-interaction sample weights (overridable per call). Positive vs negative
# is decided by the dataset builder (LABELS); this is only relative importance.
DEFAULT_SAMPLE_WEIGHTS: dict[str, float] = {
    "thumbs_up": 1.0, "thumbs_down": 1.0, "export": 1.2, "contact": 1.5, "ignore": 0.5,
}
# How each interaction maps to a training label (used by ml.dataset).
POSITIVE_INTERACTIONS = frozenset({"thumbs_up", "contact", "export"})
NEGATIVE_INTERACTIONS = frozenset({"thumbs_down", "ignore"})


def default_weight(interaction_type: str) -> float:
    return DEFAULT_SAMPLE_WEIGHTS.get(interaction_type, 1.0)


def record_interaction(session: Session, *, interaction_type: str, entity_type: str,
                       entity_id: str, user_id: int | None = None, user_email: str = "",
                       company_domain: str = "", sample_weight: float | None = None,
                       context: dict | None = None) -> UserInteraction:
    """Append one interaction. Validates the vocabularies; fills the default weight."""
    if interaction_type not in ML_INTERACTION_TYPES:
        raise ValueError(f"unknown interaction_type '{interaction_type}'")
    if entity_type not in ML_ENTITY_TYPES:
        raise ValueError(f"unknown entity_type '{entity_type}'")
    row = UserInteraction(
        user_id=user_id, user_email=user_email or "", interaction_type=interaction_type,
        entity_type=entity_type, entity_id=str(entity_id), company_domain=company_domain or "",
        sample_weight=default_weight(interaction_type) if sample_weight is None else float(sample_weight),
        context=context or {},
    )
    session.add(row)
    session.flush()
    return row


def interactions_for(session: Session, entity_type: str, entity_id: str) -> list[UserInteraction]:
    return list(session.scalars(
        select(UserInteraction)
        .where(UserInteraction.entity_type == entity_type, UserInteraction.entity_id == str(entity_id))
        .order_by(UserInteraction.created_at.desc())
    ))


def interactions_since(session: Session, since: datetime) -> list[UserInteraction]:
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    return list(session.scalars(
        select(UserInteraction).where(UserInteraction.created_at >= since)
        .order_by(UserInteraction.created_at.asc())
    ))


def engagement_counts(session: Session) -> dict[str, dict[str, int]]:
    """Per-company historical-engagement rollup (a feature): positive / negative /
    total interaction counts keyed by company_domain."""
    out: dict[str, dict[str, int]] = {}
    for r in session.scalars(select(UserInteraction).where(UserInteraction.company_domain != "")):
        b = out.setdefault(r.company_domain, {"positive": 0, "negative": 0, "total": 0})
        b["total"] += 1
        if r.interaction_type in POSITIVE_INTERACTIONS:
            b["positive"] += 1
        elif r.interaction_type in NEGATIVE_INTERACTIONS:
            b["negative"] += 1
    return out
