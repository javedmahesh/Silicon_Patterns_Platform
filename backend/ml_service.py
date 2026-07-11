"""ML service layer — wraps the ``ml`` package for the API + CLI.

Read/refresh feature vectors, capture feedback, build the training dataset, and expose
the registries. Never trains a model, never touches the Lead Scorer or the Scheduler.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import Settings
from master_db.models import (
    MlFeatureRow,
    MlModel,
    MlRecommendation,
    MlTrainingRun,
    RoleEmbedding,
    User,
    UserInteraction,
)
from ml import dataset as ds
from ml import features as feat
from ml import feedback, registry
from ml import model as mdl
from ml import promote as promote_mod


def record_interaction(session: Session, settings: Settings, *, user: User, body) -> UserInteraction:
    try:
        row = feedback.record_interaction(
            session, interaction_type=body.interaction_type, entity_type=body.entity_type,
            entity_id=body.entity_id, user_id=user.id, user_email=user.email,
            company_domain=body.company_domain, sample_weight=body.sample_weight,
            context=body.context or {},
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    session.commit()
    return row


def list_interactions(session: Session, *, entity_type: str | None, entity_id: str | None,
                      limit: int = 100) -> list[UserInteraction]:
    q = select(UserInteraction)
    if entity_type:
        q = q.where(UserInteraction.entity_type == entity_type)
    if entity_id:
        q = q.where(UserInteraction.entity_id == entity_id)
    return list(session.scalars(q.order_by(UserInteraction.created_at.desc()).limit(limit)))


def feature_vector(session: Session, settings: Settings, domain: str) -> dict:
    version = settings.ml_feature_version or feat.FEATURE_VERSION
    row = session.scalar(
        select(MlFeatureRow).where(
            MlFeatureRow.entity_type == "company", MlFeatureRow.entity_id == domain,
            MlFeatureRow.feature_version == version,
        )
    )
    if row is not None:
        return {"entity_type": "company", "entity_id": domain,
                "feature_version": version, "features": row.features}
    # not cached yet -> compute just this one (persists it too)
    res = feat.build_features_batch(session, settings, domains=[domain], incremental=True)
    session.commit()
    if domain not in res.features:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "company not found")
    return {"entity_type": "company", "entity_id": domain,
            "feature_version": version, "features": res.features[domain]}


def refresh_features(session: Session, settings: Settings, *, incremental: bool = True) -> dict:
    res = feat.build_features_batch(session, settings, incremental=incremental)
    session.commit()
    return {"feature_version": res.feature_version, "computed": res.computed,
            "reused": res.reused, "total": res.total}


def build_dataset(session: Session, settings: Settings, *, window_days: int | None) -> dict:
    result = ds.build_training_dataset(session, settings, window_days=window_days)
    session.commit()
    return {"version": result.version, "feature_version": result.feature_version,
            "window_days": result.window_days, "row_count": result.row_count,
            "positive": result.positive, "negative": result.negative, "columns": result.columns}


def list_models(session: Session) -> list[MlModel]:
    return registry.list_models(session)


def get_model(session: Session, settings: Settings, version: str) -> MlModel:
    m = registry.get_model(session, version, settings.ml_model_name)
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "model version not found")
    return m


def train(session: Session, settings: Settings, *, window_days: int | None,
          hyperparams: dict | None, actor_email: str) -> dict:
    res = mdl.train_candidate(session, settings, window_days=window_days,
                              hyperparams=hyperparams, actor_email=actor_email)
    session.commit()
    return {"version": res.version, "backend": res.backend, "feature_version": res.feature_version,
            "dataset_version": res.dataset_version, "n_rows": res.n_rows, "positive": res.positive,
            "negative": res.negative, "metrics": res.metrics, "status": "draft"}


def promote(session: Session, settings: Settings, *, version: str, actor_email: str) -> dict:
    r = promote_mod.promote(session, settings, model_version=version, actor_email=actor_email)
    return {"promoted": r.promoted, "version": r.version, "reason": r.reason,
            "previous_version": r.previous_version, "metrics": r.metrics, "checks": r.checks}


def rollback(session: Session, settings: Settings, *, version: str, actor_email: str) -> dict:
    r = promote_mod.rollback(session, settings, to_version=version, actor_email=actor_email)
    if not r.promoted and r.reason in ("target version not found",):
        raise HTTPException(status.HTTP_404_NOT_FOUND, r.reason)
    return {"promoted": r.promoted, "version": r.version, "reason": r.reason,
            "previous_version": r.previous_version, "metrics": {}, "checks": {}}


def run_inference(session: Session, settings: Settings, *, version: str | None) -> dict:
    model = None
    if version:
        model = get_model(session, settings, version)
    try:
        res = mdl.run_inference(session, settings, model=model)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    session.commit()
    return {"model_version": res.model_version, "scored": res.scored, "batches": res.batches}


def list_recommendations(session: Session, *, company_domain: str | None,
                         model_version: str | None, limit: int = 100) -> list[MlRecommendation]:
    return registry.list_recommendations(session, company_domain=company_domain,
                                         model_version=model_version, limit=limit)


def ml_status(session: Session, settings: Settings) -> dict:
    def count(model) -> int:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)

    prod = registry.active_model(session, settings.ml_model_name)
    return {
        "ml_enabled": settings.ml_enabled,
        "feature_version": settings.ml_feature_version or feat.FEATURE_VERSION,
        "embedding_backend": settings.ml_embedding_backend,
        "embedding_model": settings.ml_embedding_model,
        "embedding_dim": settings.ml_embedding_dim,
        "decay_half_lives": settings.decay_half_lives(),
        "feature_row_count": count(MlFeatureRow),
        "embedding_count": count(RoleEmbedding),
        "interaction_count": count(UserInteraction),
        "model_count": count(MlModel),
        "training_run_count": count(MlTrainingRun),
        "production_model": prod.version if prod else None,
        "recommendation_count": count(MlRecommendation),
    }
