"""Machine Learning Foundation — infrastructure for a future recommendation model.

Prepares (but does NOT train) a production ML system, reusing the platform's existing
intelligence and never touching the Lead Scorer or the Scheduler:

  * :mod:`.features`   — one deterministic, cached, incremental feature builder reused
                         for both training and inference (the Feature Store).
  * :mod:`.decay`      — configurable exponential time-decay as a generated feature.
  * :mod:`.embeddings` — cached role/title embeddings (lightweight model + fallback).
  * :mod:`.feedback`   — user-interaction dataset (thumbs/export/contact/ignore).
  * :mod:`.dataset`    — training-dataset builder over the trailing 30–90 days.
  * :mod:`.registry`   — model / feature / training-run versioning + metadata.
"""
from __future__ import annotations

from ml.dataset import build_training_dataset
from ml.features import FEATURE_VERSION, build_company_features, build_features_batch, feature_spec
from ml.model import evaluate, run_inference, train_candidate

# NOTE: ``promote``/``rollback`` live in the ``ml.promote`` submodule and are NOT
# re-exported here — a top-level ``promote`` name would shadow the submodule.
__all__ = [
    "FEATURE_VERSION",
    "build_company_features",
    "build_features_batch",
    "build_training_dataset",
    "feature_spec",
    "train_candidate",
    "evaluate",
    "run_inference",
]
