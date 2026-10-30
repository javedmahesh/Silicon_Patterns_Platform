"""Model / feature / training-run registries — ML infrastructure (no classifier yet).

Thin helpers over the ``ml_models`` / ``ml_feature_versions`` / ``ml_training_runs``
tables so versioning + metadata have one owner. A trainer added later records its model
+ metrics here; today only the feature/dataset builders write.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from master_db.models import MlFeatureVersion, MlModel, MlModelEvent, MlRecommendation, MlTrainingRun


def register_feature_version(session: Session, version: str, spec: dict, *,
                             notes: str = "") -> MlFeatureVersion:
    row = session.scalar(select(MlFeatureVersion).where(MlFeatureVersion.version == version))
    feature_count = len(spec.get("features", [])) if isinstance(spec, dict) else 0
    if row is None:
        row = MlFeatureVersion(version=version, spec=spec, feature_count=feature_count, notes=notes)
        session.add(row)
    else:
        row.spec, row.feature_count, row.notes = spec, feature_count, notes
    session.flush()
    return row


def register_model(session: Session, *, name: str, version: str, status: str = "draft",
                   model_type: str = "", feature_version: str = "", artifact_path: str = "",
                   artifact: str = "", feature_importance: dict | None = None,
                   metrics: dict | None = None, metadata: dict | None = None) -> MlModel:
    row = session.scalar(
        select(MlModel).where(MlModel.name == name, MlModel.version == version)
    )
    if row is None:
        row = MlModel(name=name, version=version, status=status, model_type=model_type,
                      feature_version=feature_version, artifact_path=artifact_path, artifact=artifact,
                      feature_importance=feature_importance or {}, metrics=metrics or {},
                      model_metadata=metadata or {})
        session.add(row)
    else:
        row.status, row.model_type, row.feature_version = status, model_type, feature_version
        row.artifact_path, row.metrics, row.model_metadata = artifact_path, metrics or {}, metadata or {}
        row.artifact, row.feature_importance = artifact, feature_importance or {}
    session.flush()
    return row


def get_model(session: Session, version: str, name: str = "lead_recommender") -> MlModel | None:
    return session.scalar(select(MlModel).where(MlModel.name == name, MlModel.version == version))


def list_models(session: Session) -> list[MlModel]:
    return list(session.scalars(select(MlModel).order_by(MlModel.created_at.desc())))


def active_model(session: Session, name: str = "lead_recommender") -> MlModel | None:
    return session.scalar(
        select(MlModel).where(MlModel.name == name, MlModel.status == "active")
        .order_by(MlModel.created_at.desc())
    )


def record_event(session: Session, *, model: MlModel | None, action: str, detail: str = "",
                 metrics: dict | None = None, actor_email: str = "") -> MlModelEvent:
    ev = MlModelEvent(model_id=(model.id if model else None),
                      model_version=(model.version if model else ""), action=action,
                      detail=detail, metrics=metrics or {}, actor_email=actor_email or "")
    session.add(ev)
    session.flush()
    return ev


def list_events(session: Session, limit: int = 100) -> list[MlModelEvent]:
    return list(session.scalars(
        select(MlModelEvent).order_by(MlModelEvent.created_at.desc()).limit(limit)))


def list_recommendations(session: Session, *, company_domain: str | None = None,
                         model_version: str | None = None, limit: int = 100) -> list[MlRecommendation]:
    q = select(MlRecommendation)
    if company_domain:
        q = q.where(MlRecommendation.company_domain == company_domain)
    if model_version:
        q = q.where(MlRecommendation.model_version == model_version)
    return list(session.scalars(q.order_by(MlRecommendation.probability.desc()).limit(limit)))


def record_training_run(session: Session, *, dataset_version: str, feature_version: str,
                        window_days: int, row_count: int, positive_count: int,
                        negative_count: int, status: str = "dataset_built",
                        params: dict | None = None, metrics: dict | None = None,
                        notes: str = "", model_id: int | None = None) -> MlTrainingRun:
    run = MlTrainingRun(
        model_id=model_id, dataset_version=dataset_version, feature_version=feature_version,
        window_days=window_days, row_count=row_count, positive_count=positive_count,
        negative_count=negative_count, status=status, params=params or {}, metrics=metrics or {},
        notes=notes, finished_at=datetime.now(timezone.utc),
    )
    session.add(run)
    session.flush()
    return run

