"""Machine Learning Foundation API — feedback capture + feature-store + registries.

Feedback capture is open to any signed-in user (thumbs up/down etc. from the UI); the
feature/dataset/registry operations are manager-gated. No endpoint trains a model.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend import ml_service
from backend.dependencies import get_session
from backend.schemas import (
    DatasetBuildResult,
    FeatureRefreshResult,
    FeatureVectorOut,
    InferenceResultOut,
    InteractionIn,
    InteractionOut,
    MlModelDetailOut,
    MlModelOut,
    MlStatusOut,
    PromotionResultOut,
    RecommendationOut,
    TrainResultOut,
)
from backend.security import get_current_user, require_manager
from master_db.models import User

from pydantic import BaseModel


class TrainRequest(BaseModel):
    window_days: int | None = None
    hyperparameters: dict = {}

router = APIRouter(prefix="/ml", tags=["machine-learning"])


def _settings(request: Request):
    return request.app.state.settings


@router.post("/interactions", response_model=InteractionOut, status_code=201,
             summary="Record a user feedback interaction (thumbs up/down/export/contact/ignore)")
def record_interaction(
    body: InteractionIn,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return InteractionOut.model_validate(
        ml_service.record_interaction(session, _settings(request), user=user, body=body))


@router.get("/interactions", response_model=list[InteractionOut], summary="List feedback interactions")
def list_interactions(
    session: Session = Depends(get_session),
    _: User = Depends(require_manager),
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    limit: int = Query(100, le=500),
):
    return [InteractionOut.model_validate(r)
            for r in ml_service.list_interactions(session, entity_type=entity_type,
                                                  entity_id=entity_id, limit=limit)]


@router.get("/status", response_model=MlStatusOut, summary="ML foundation status + counts")
def ml_status(request: Request, session: Session = Depends(get_session),
              _: User = Depends(require_manager)):
    return MlStatusOut(**ml_service.ml_status(session, _settings(request)))


@router.get("/features/{company_domain}", response_model=FeatureVectorOut,
            summary="Feature vector for a company (cached or computed on demand)")
def feature_vector(company_domain: str, request: Request,
                   session: Session = Depends(get_session), _: User = Depends(require_manager)):
    return FeatureVectorOut(**ml_service.feature_vector(session, _settings(request), company_domain))


@router.post("/features/refresh", response_model=FeatureRefreshResult,
             summary="Incrementally (re)build the feature store")
def refresh_features(request: Request, session: Session = Depends(get_session),
                     _: User = Depends(require_manager),
                     incremental: bool = Query(True, description="Skip companies with unchanged inputs")):
    return FeatureRefreshResult(**ml_service.refresh_features(
        session, _settings(request), incremental=incremental))


@router.post("/dataset/build", response_model=DatasetBuildResult,
             summary="Build the training dataset from the trailing 30–90 days (no training)")
def build_dataset(request: Request, session: Session = Depends(get_session),
                  _: User = Depends(require_manager),
                  window_days: int | None = Query(None, ge=1, le=365)):
    return DatasetBuildResult(**ml_service.build_dataset(
        session, _settings(request), window_days=window_days))


@router.get("/models", response_model=list[MlModelOut], summary="Model registry")
def list_models(session: Session = Depends(get_session), _: User = Depends(require_manager)):
    return [MlModelOut.model_validate(m) for m in ml_service.list_models(session)]


@router.get("/models/{version}", response_model=MlModelDetailOut,
            summary="Model detail (metrics + feature importance + hyperparameters)")
def get_model(version: str, request: Request, session: Session = Depends(get_session),
              _: User = Depends(require_manager)):
    return MlModelDetailOut.model_validate(ml_service.get_model(session, _settings(request), version))


@router.post("/train", response_model=TrainResultOut,
             summary="Train a candidate model from the dataset builder (no auto-promotion)")
def train(body: TrainRequest, request: Request, session: Session = Depends(get_session),
          user: User = Depends(require_manager)):
    return TrainResultOut(**ml_service.train(
        session, _settings(request), window_days=body.window_days,
        hyperparams=body.hyperparameters, actor_email=user.email))


@router.post("/models/{version}/promote", response_model=PromotionResultOut,
             summary="Promote a candidate to production (gated: thresholds + outperform)")
def promote(version: str, request: Request, session: Session = Depends(get_session),
            user: User = Depends(require_manager)):
    return PromotionResultOut(**ml_service.promote(
        session, _settings(request), version=version, actor_email=user.email))


@router.post("/models/{version}/rollback", response_model=PromotionResultOut,
             summary="Roll back production to a previous model version")
def rollback(version: str, request: Request, session: Session = Depends(get_session),
             user: User = Depends(require_manager)):
    return PromotionResultOut(**ml_service.rollback(
        session, _settings(request), version=version, actor_email=user.email))


@router.post("/inference/run", response_model=InferenceResultOut,
             summary="Run offline inference (probabilities stored alongside the lead score)")
def run_inference(request: Request, session: Session = Depends(get_session),
                  _: User = Depends(require_manager),
                  version: str | None = Query(None, description="Model version (default: production)")):
    return InferenceResultOut(**ml_service.run_inference(session, _settings(request), version=version))


@router.get("/recommendations", response_model=list[RecommendationOut],
            summary="Offline inference recommendations (separate from the lead score)")
def list_recommendations(session: Session = Depends(get_session), _: User = Depends(require_manager),
                         company_domain: str | None = Query(None),
                         model_version: str | None = Query(None),
                         limit: int = Query(100, le=500)):
    return [RecommendationOut.model_validate(r) for r in ml_service.list_recommendations(
        session, company_domain=company_domain, model_version=model_version, limit=limit)]
