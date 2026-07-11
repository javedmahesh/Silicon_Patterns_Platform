"""Training Dataset Builder — assemble ML-ready rows from recent platform activity.

Joins the user-feedback labels (last 30–90 days) with the feature-store vector for each
labelled company. Deliberately SEPARATE from model training: it emits rows + a recorded
``ml_training_runs`` entry, and trains nothing. A trainer added later consumes this.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ml import features as feat
from ml import feedback, registry

_WINDOW_MIN, _WINDOW_MAX = 30, 90


@dataclass
class DatasetResult:
    version: str
    feature_version: str
    window_days: int
    columns: list[str]
    rows: list[dict] = field(default_factory=list)
    positive: int = 0
    negative: int = 0

    @property
    def row_count(self) -> int:
        return len(self.rows)


def _label(interaction_type: str) -> int | None:
    if interaction_type in feedback.POSITIVE_INTERACTIONS:
        return 1
    if interaction_type in feedback.NEGATIVE_INTERACTIONS:
        return 0
    return None


def _company_of(interaction) -> str:
    """The company an interaction is about (explicit column, or the entity itself)."""
    if interaction.company_domain:
        return interaction.company_domain
    if interaction.entity_type == "company":
        return interaction.entity_id
    return ""


def build_training_dataset(session: Session, settings, *, window_days: int | None = None,
                           feature_version: str | None = None, persist: bool = True) -> DatasetResult:
    """Build the labelled training dataset for the trailing *window_days* (clamped 30–90).

    Deterministic: the same feedback + platform state yields the same rows. Records an
    ``ml_training_runs`` row (status='dataset_built'). No model is trained."""
    window = window_days if window_days is not None else settings.ml_training_window_days
    window = max(_WINDOW_MIN, min(_WINDOW_MAX, int(window)))
    fversion = feature_version or settings.ml_feature_version or feat.FEATURE_VERSION
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=window)

    interactions = feedback.interactions_since(session, since)
    labelled = [(i, _label(i.interaction_type), _company_of(i)) for i in interactions]
    labelled = [(i, y, dom) for (i, y, dom) in labelled if y is not None and dom]

    domains = sorted({dom for (_, _, dom) in labelled})
    # Reuse the feature store (cache), computed for exactly the labelled companies.
    fs = feat.build_features_batch(session, settings, domains=domains, incremental=True,
                                   persist=persist) if domains else None
    scalar_cols = feat.feature_spec()
    columns = [*scalar_cols, "label", "sample_weight", "interaction_type", "entity_type",
               "entity_id", "company_domain"]

    rows: list[dict] = []
    pos = neg = 0
    for interaction, y, dom in labelled:
        feats = (fs.features.get(dom) if fs else None) or {}
        row = {col: feats.get(col, 0) for col in scalar_cols}
        row.update({
            "label": y,
            "sample_weight": float(interaction.sample_weight),
            "interaction_type": interaction.interaction_type,
            "entity_type": interaction.entity_type,
            "entity_id": interaction.entity_id,
            "company_domain": dom,
        })
        rows.append(row)
        pos, neg = (pos + 1, neg) if y == 1 else (pos, neg + 1)

    version = f"ds-{now.strftime('%Y%m%d%H%M%S')}-w{window}-{fversion}"
    result = DatasetResult(version=version, feature_version=fversion, window_days=window,
                           columns=columns, rows=rows, positive=pos, negative=neg)
    if persist:
        registry.register_feature_version(
            session, fversion, {"features": scalar_cols,
                                "embeddings": ["dm_role_embedding_mean"], "lists": ["tech_tags"]},
            notes="feature-store scalar spec")
        registry.record_training_run(
            session, dataset_version=version, feature_version=fversion, window_days=window,
            row_count=len(rows), positive_count=pos, negative_count=neg,
            params={"window_days": window}, notes="dataset built (no training)")
        session.flush()
    return result
