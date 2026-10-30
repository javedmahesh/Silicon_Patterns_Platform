"""Recommendation model — training, evaluation, explainability, offline inference.

Trains a binary classifier from the EXISTING dataset builder (no feature-generation
change) using the stored sample weights. LightGBM is used when installed (preferred);
otherwise scikit-learn's GradientBoostingClassifier (a real GBDT, always available
here) — same sklearn API (``fit(sample_weight=)`` + ``feature_importances_`` +
``predict_proba``), so ``pip install lightgbm`` is a drop-in upgrade.

Everything runs OFFLINE (CLI/API), never inside a scheduled run. Inference stores a
probability in ``ml_recommendations`` ALONGSIDE — never inside — the lead score.
"""
from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import joblib
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ml import dataset as ds
from ml import features as feat
from ml import registry
from master_db.models import MlModel, MlRecommendation

logger = logging.getLogger("ml.model")

FEATURE_COLS = feat.feature_spec()   # tabular model inputs (scalar features, in order)

_DEFAULT_HP_SKLEARN = {"n_estimators": 200, "learning_rate": 0.05, "max_depth": 3, "random_state": 42}
_DEFAULT_HP_LGBM = {"n_estimators": 200, "learning_rate": 0.05, "num_leaves": 15,
                    "random_state": 42, "verbosity": -1}


def _backend() -> str:
    import importlib.util
    return "lightgbm" if importlib.util.find_spec("lightgbm") else "sklearn"


class _ConstantModel:
    """Prior-probability predictor for degenerate datasets (single class / too few rows).
    Keeps 'every training run produces a candidate' true without crashing."""

    def __init__(self, prior: float, n_features: int) -> None:
        self.prior = float(min(max(prior, 1e-6), 1 - 1e-6))
        self.feature_importances_ = np.zeros(n_features)

    def predict_proba(self, X):
        p = np.full((len(X), 2), 0.0)
        p[:, 1] = self.prior
        p[:, 0] = 1 - self.prior
        return p


def _matrix(rows: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = np.array([[float(r.get(c, 0) or 0) for c in FEATURE_COLS] for r in rows], dtype=float)
    y = np.array([int(r["label"]) for r in rows], dtype=int)
    w = np.array([float(r.get("sample_weight", 1.0) or 1.0) for r in rows], dtype=float)
    return X, y, w


def _split(n: int, val_fraction: float) -> tuple[list[int], list[int]]:
    """Deterministic index split (no shuffling => reproducible)."""
    if n < 4:
        idx = list(range(n))
        return idx, idx  # too small to hold out — evaluate on train (reported as such)
    n_val = max(1, int(round(n * val_fraction)))
    return list(range(n - n_val)), list(range(n - n_val, n))


def evaluate(y_true: np.ndarray, y_prob: np.ndarray, weights: np.ndarray | None = None) -> dict:
    """ROC-AUC, PR-AUC, precision, recall, F1, log-loss (sample-weighted where supported)."""
    from sklearn.metrics import (
        average_precision_score, f1_score, log_loss, precision_score, recall_score, roc_auc_score,
    )
    y_true = np.asarray(y_true); y_prob = np.asarray(y_prob)
    y_pred = (y_prob >= 0.5).astype(int)
    single_class = len(np.unique(y_true)) < 2
    m: dict = {"n": int(len(y_true)), "positive_rate": float(np.mean(y_true)) if len(y_true) else 0.0}
    try:
        m["roc_auc"] = None if single_class else float(roc_auc_score(y_true, y_prob, sample_weight=weights))
        m["pr_auc"] = None if single_class else float(average_precision_score(y_true, y_prob, sample_weight=weights))
        m["precision"] = float(precision_score(y_true, y_pred, sample_weight=weights, zero_division=0))
        m["recall"] = float(recall_score(y_true, y_pred, sample_weight=weights, zero_division=0))
        m["f1"] = float(f1_score(y_true, y_pred, sample_weight=weights, zero_division=0))
        m["log_loss"] = float(log_loss(y_true, np.clip(y_prob, 1e-6, 1 - 1e-6),
                                       labels=[0, 1], sample_weight=weights))
    except Exception as exc:  # pragma: no cover - defensive on tiny/degenerate data
        logger.warning("evaluate: %s", exc)
        m["error"] = str(exc)
    return m


@dataclass
class CandidateResult:
    version: str
    feature_version: str
    backend: str
    metrics: dict
    feature_importance: dict
    n_rows: int
    positive: int
    negative: int
    dataset_version: str = ""
    notes: str = ""


def _serialize(model, backend: str) -> str:
    buf = io.BytesIO()
    joblib.dump({"model": model, "features": FEATURE_COLS, "backend": backend}, buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def train_candidate(session: Session, settings, *, window_days: int | None = None,
                    hyperparams: dict | None = None, actor_email: str = "") -> CandidateResult:
    """Train ONE candidate from the dataset builder + stored sample weights. Registers a
    draft ``ml_models`` row with metrics + hyperparameters + feature importance + artifact.
    Never auto-promotes."""
    data = ds.build_training_dataset(session, settings, window_days=window_days)
    rows = data.rows
    backend = _backend()
    hp = dict((_DEFAULT_HP_LGBM if backend == "lightgbm" else _DEFAULT_HP_SKLEARN))
    hp.update(hyperparams or {})

    if not rows:
        # No labelled feedback yet — still register a (constant) candidate so the
        # registry + promotion workflow are exercised; metrics reflect "no data".
        model = _ConstantModel(0.5, len(FEATURE_COLS))
        metrics = {"n": 0, "note": "no training rows (no feedback in window)"}
        importance = {c: 0.0 for c in FEATURE_COLS}
    else:
        X, y, w = _matrix(rows)
        tr, va = _split(len(rows), settings.ml_val_fraction)
        model, used = _fit(X[tr], y[tr], w[tr], backend, hp)
        backend = used
        proba = model.predict_proba(X[va])[:, 1]
        metrics = evaluate(y[va], proba, w[va])
        metrics["train_rows"], metrics["val_rows"] = len(tr), len(va)
        importance = _importance(model)

    _now = datetime.now(timezone.utc)
    # microsecond suffix keeps two candidates trained in the same second distinct
    # (a same-second collision would UPDATE the first candidate instead of adding one).
    version = f"m-{_now.strftime('%Y%m%d%H%M%S')}-{_now.microsecond:06d}-{data.feature_version}"
    pos = sum(1 for r in rows if r["label"] == 1)
    mdl = registry.register_model(
        session, name=settings.ml_model_name, version=version, status="draft",
        model_type=backend, feature_version=data.feature_version,
        metrics=metrics,
        metadata={"hyperparameters": hp, "window_days": data.window_days,
                  "dataset_version": data.version, "n_rows": len(rows),
                  "positive": pos, "negative": len(rows) - pos, "backend": backend},
        feature_importance=importance, artifact=_serialize(model, backend),
    )
    registry.record_event(session, model=mdl, action="trained", actor_email=actor_email,
                          metrics=metrics, detail=f"backend={backend} rows={len(rows)}")
    session.flush()
    return CandidateResult(version=version, feature_version=data.feature_version, backend=backend,
                           metrics=metrics, feature_importance=importance, n_rows=len(rows),
                           positive=pos, negative=len(rows) - pos, dataset_version=data.version)


def _fit(X, y, w, backend: str, hp: dict):
    if len(np.unique(y)) < 2:
        return _ConstantModel(float(np.mean(y)) if len(y) else 0.5, X.shape[1]), "constant"
    if backend == "lightgbm":
        try:
            import lightgbm as lgb

            model = lgb.LGBMClassifier(**hp)
            model.fit(X, y, sample_weight=w)
            return model, "lightgbm"
        except Exception as exc:  # pragma: no cover - only if lgbm install is broken
            logger.warning("lightgbm failed (%s); using sklearn", exc)
    from sklearn.ensemble import GradientBoostingClassifier

    sk_hp = {k: v for k, v in hp.items() if k in {"n_estimators", "learning_rate", "max_depth", "random_state"}}
    model = GradientBoostingClassifier(**sk_hp)
    model.fit(X, y, sample_weight=w)
    return model, "sklearn"


def _importance(model) -> dict:
    fi = getattr(model, "feature_importances_", None)
    if fi is None:
        return {c: 0.0 for c in FEATURE_COLS}
    total = float(np.sum(fi)) or 1.0
    return {c: round(float(v) / total, 6) for c, v in zip(FEATURE_COLS, fi)}


# ---------------------------------------------------------------- inference
class Predictor:
    """Loads a serialized ``MlModel`` and scores feature dicts in batches."""

    def __init__(self, model, features: list[str], version: str) -> None:
        self._model = model
        self._features = features
        self.version = version

    @classmethod
    def load(cls, mlmodel: MlModel) -> "Predictor":
        raw = base64.b64decode(mlmodel.artifact.encode("ascii"))
        payload = joblib.load(io.BytesIO(raw))
        return cls(payload["model"], payload["features"], mlmodel.version)

    def predict_dicts(self, feature_dicts: list[dict]) -> list[float]:
        if not feature_dicts:
            return []
        X = np.array([[float(d.get(c, 0) or 0) for c in self._features] for d in feature_dicts], dtype=float)
        return [float(p) for p in self._model.predict_proba(X)[:, 1]]


@dataclass
class InferenceResult:
    model_version: str
    scored: int = 0
    batches: int = 0


def run_inference(session: Session, settings, *, model: MlModel | None = None,
                  batch_size: int = 500) -> InferenceResult:
    """Batched offline inference over every company, reusing the cached feature store
    (no feature recompute for unchanged inputs). Upserts ``ml_recommendations`` — the
    lead score is never touched."""
    if model is None:
        model = registry.active_model(session, settings.ml_model_name)
    if model is None:
        raise ValueError("no production model to run inference with (train + promote one first)")
    predictor = Predictor.load(model)

    fs = feat.build_features_batch(session, settings, incremental=True)  # cached / incremental
    session.flush()
    domains = list(fs.features)
    existing = {(r.entity_id): r for r in session.scalars(
        select(MlRecommendation).where(MlRecommendation.model_version == model.version,
                                        MlRecommendation.entity_type == "company"))}
    res = InferenceResult(model_version=model.version)
    for i in range(0, len(domains), batch_size):
        chunk = domains[i:i + batch_size]
        probs = predictor.predict_dicts([fs.features[d] for d in chunk])
        for domain, p in zip(chunk, probs):
            row = existing.get(domain)
            if row is None:
                session.add(MlRecommendation(model_id=model.id, model_version=model.version,
                                             entity_type="company", entity_id=domain,
                                             company_domain=domain, probability=round(p, 6)))
            else:
                row.probability, row.model_id = round(p, 6), model.id
            res.scored += 1
        res.batches += 1
        session.flush()
    logger.info("inference %s: scored=%d batches=%d", model.version, res.scored, res.batches)
    return res
