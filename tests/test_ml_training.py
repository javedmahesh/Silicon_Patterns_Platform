"""Recommendation model — training, weighted fit, evaluation, candidate registry,
promotion + rollback, offline inference, explainability, and non-regression.

Uses the existing ML foundation (feature store / dataset builder / registry). No
feature-generation, lead-scoring, or scheduler object is modified.
"""
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.local import make_session_factory
from master_db.models import (
    Base, Company, LeadScore, MlRecommendation, Opportunity,
)
from ml import feedback, model as mdl, promote as promote_mod, registry

# Low thresholds so a well-separated toy set is promotable; overridden per test.
SETTINGS = Settings(database_url="sqlite:///:memory:", ml_val_fraction=0.3,
                    ml_promote_min_roc_auc=0.5, ml_promote_min_pr_auc=0.5)


def _seed(session, n=16, *, single_class=False):
    """Separable toy set: even companies are strong leads (+), odd are weak (-)."""
    for i in range(n):
        dom = f"c{i}.com"
        pos = (i % 2 == 0)
        session.add(Company(company_domain=dom, canonical_company_id=f"C{i}", company_name=f"Co{i}",
                            name_key=f"co{i}", company_tier="STARTUP", compliance_flag="APPROVED",
                            validation_status="VALID"))
        session.flush()
        session.add(Opportunity(opportunity_id=f"O{i}", company_domain=dom, opportunity_type="FUNDING",
                                effective_opportunity_score=90 if pos else 15, published_date="2026-07-01"))
        session.add(LeadScore(company_domain=dom, lead_score=85.0 if pos else 12.0,
                              grade="A" if pos else "C", model_version="rules-v1"))
        # labels/weights come ONLY from the feedback system (no hardcoded labels)
        if single_class or pos:
            itype = "thumbs_up"          # strong positive
        else:
            itype = "thumbs_down" if i % 4 == 1 else "ignore"  # strong / weak negative
        feedback.record_interaction(session, interaction_type=itype, entity_type="company",
                                    entity_id=dom, company_domain=dom)
    session.commit()


@pytest.fixture()
def session():
    Session = make_session_factory(":memory:")
    with Session() as s:
        yield s


# ------------------------------------------------------------------ training
def test_train_produces_candidate(session):
    _seed(session)
    r = mdl.train_candidate(session, SETTINGS)
    session.commit()
    m = registry.get_model(session, r.version, SETTINGS.ml_model_name)
    assert m is not None and m.status == "draft"          # candidate, NOT auto-promoted
    assert m.model_type in ("lightgbm", "sklearn")
    assert m.feature_version == r.feature_version
    # candidate registry stores: version, feature version, window, metrics, timestamp, hyperparams
    assert m.model_metadata["window_days"] and m.model_metadata["hyperparameters"]
    assert m.model_metadata["dataset_version"] and m.created_at is not None
    assert registry.active_model(session, SETTINGS.ml_model_name) is None  # nothing promoted


def test_weighted_training_uses_feedback_tiers(session):
    _seed(session)
    # Strong Positive / Strong Negative / Weak Negative all come from the feedback weights
    assert feedback.DEFAULT_SAMPLE_WEIGHTS["thumbs_up"] == 1.0     # strong positive
    assert feedback.DEFAULT_SAMPLE_WEIGHTS["thumbs_down"] == 1.0   # strong negative
    assert feedback.DEFAULT_SAMPLE_WEIGHTS["ignore"] == 0.5        # weak negative
    from ml import dataset as ds
    data = ds.build_training_dataset(session, SETTINGS, window_days=45, persist=False)
    weights = {r["interaction_type"]: r["sample_weight"] for r in data.rows}
    assert weights["ignore"] == 0.5 and weights["thumbs_up"] == 1.0  # weights flow into rows


def test_evaluate_respects_sample_weights():
    y = np.array([1, 1, 0, 0])
    p = np.array([0.9, 0.4, 0.1, 0.6])
    unw = mdl.evaluate(y, p)
    w = mdl.evaluate(y, p, np.array([5.0, 1.0, 1.0, 1.0]))  # up-weight a correct positive
    assert unw["log_loss"] != w["log_loss"]  # weighting changes the metric


def test_evaluation_metrics_present(session):
    _seed(session)
    r = mdl.train_candidate(session, SETTINGS)
    session.commit()
    for k in ("roc_auc", "pr_auc", "precision", "recall", "f1", "log_loss"):
        assert k in r.metrics, k
    assert r.metrics["roc_auc"] is not None and r.metrics["pr_auc"] is not None


# ------------------------------------------------------------------ explainability
def test_feature_importance_stored(session):
    _seed(session)
    r = mdl.train_candidate(session, SETTINGS)
    session.commit()
    m = registry.get_model(session, r.version, SETTINGS.ml_model_name)
    assert m.feature_importance and set(m.feature_importance) <= set(mdl.FEATURE_COLS)
    assert abs(sum(m.feature_importance.values()) - 1.0) < 1e-3  # normalized importances


# ------------------------------------------------------------------ promotion
def test_promotion_gated_and_manual(session):
    _seed(session)
    r = mdl.train_candidate(session, SETTINGS)
    session.commit()
    res = promote_mod.promote(session, SETTINGS, model_version=r.version)
    assert res.promoted is True and res.reason == "promoted"
    assert registry.active_model(session, SETTINGS.ml_model_name).version == r.version


def test_promotion_rejects_when_not_outperforming(session):
    _seed(session)
    a = mdl.train_candidate(session, SETTINGS); session.commit()
    promote_mod.promote(session, SETTINGS, model_version=a.version)
    b = mdl.train_candidate(session, SETTINGS); session.commit()  # identical metrics
    res = promote_mod.promote(session, SETTINGS, model_version=b.version)
    assert res.promoted is False and "outperform" in res.reason
    assert registry.active_model(session, SETTINGS.ml_model_name).version == a.version  # incumbent kept


def test_promotion_rejects_failed_evaluation(session):
    _seed(session, single_class=True)  # only positives -> ROC/PR undefined -> eval fails
    r = mdl.train_candidate(session, SETTINGS); session.commit()
    res = promote_mod.promote(session, SETTINGS, model_version=r.version)
    assert res.promoted is False and res.checks["evaluation_succeeded"] is False


def test_promotion_rejects_below_threshold(session):
    _seed(session)
    strict = Settings(database_url="sqlite:///:memory:", ml_val_fraction=0.3,
                      ml_promote_min_roc_auc=1.01, ml_promote_min_pr_auc=1.01)  # impossible gate
    r = mdl.train_candidate(session, strict); session.commit()
    res = promote_mod.promote(session, strict, model_version=r.version)
    assert res.promoted is False and res.checks["thresholds_met"] is False


def test_rollback_restores_previous_version(session):
    _seed(session)
    a = mdl.train_candidate(session, SETTINGS); session.commit()
    promote_mod.promote(session, SETTINGS, model_version=a.version)
    b = mdl.train_candidate(session, SETTINGS); session.commit()
    # force b active via rollback API (a valid target), then roll back to a
    promote_mod.rollback(session, SETTINGS, to_version=b.version)
    assert registry.active_model(session, SETTINGS.ml_model_name).version == b.version
    rb = promote_mod.rollback(session, SETTINGS, to_version=a.version)
    assert rb.promoted and registry.active_model(session, SETTINGS.ml_model_name).version == a.version


# ------------------------------------------------------------------ inference
def test_offline_inference_stores_probabilities_not_lead_score(session):
    _seed(session)
    r = mdl.train_candidate(session, SETTINGS); session.commit()
    promote_mod.promote(session, SETTINGS, model_version=r.version)
    before = {ls.company_domain: ls.lead_score for ls in session.query(LeadScore)}
    res = mdl.run_inference(session, SETTINGS); session.commit()
    assert res.scored == 16 and session.query(MlRecommendation).count() == 16
    recs = {rc.company_domain: rc.probability for rc in session.query(MlRecommendation)}
    assert all(0.0 <= p <= 1.0 for p in recs.values())
    # lead scores are the production ranking and remain UNTOUCHED
    after = {ls.company_domain: ls.lead_score for ls in session.query(LeadScore)}
    assert before == after
    # a strong lead scores higher than a weak one under the model
    assert recs["c0.com"] > recs["c1.com"]


def test_inference_batched_and_reuses_feature_cache(session):
    _seed(session)
    from ml import features as feat
    r = mdl.train_candidate(session, SETTINGS); session.commit()
    promote_mod.promote(session, SETTINGS, model_version=r.version)
    mdl.run_inference(session, SETTINGS); session.commit()
    # a subsequent feature build reuses the cache (no recompute) -> incremental/perf
    fs = feat.build_features_batch(session, SETTINGS)
    assert fs.reused == fs.total and fs.computed == 0


# ------------------------------------------------------------------ non-regression
def test_feature_generation_unchanged(session):
    _seed(session)
    from ml import features as feat
    a = feat.build_company_features("c0.com", feat.load_bundle(session, SETTINGS))
    mdl.train_candidate(session, SETTINGS); session.commit()
    b = feat.build_company_features("c0.com", feat.load_bundle(session, SETTINGS))
    assert a == b  # training never mutates feature generation


def test_lead_scoring_still_production_ranking(session):
    _seed(session)
    from lead_scoring.service import score_all
    before = score_all(session)
    r = mdl.train_candidate(session, SETTINGS); session.commit()
    promote_mod.promote(session, SETTINGS, model_version=r.version)
    mdl.run_inference(session, SETTINGS); session.commit()
    after = score_all(session)
    assert before.scored == after.scored  # scoring pathway unchanged by ML


def test_scheduler_untouched():
    import orchestrator.stages as stages
    from backend import standard_run
    assert "ml" not in stages.PIPELINE_ORDER and "train" not in stages.PIPELINE_ORDER
    assert standard_run.STANDARD_RUN_COMPONENTS is None


# ------------------------------------------------------------------ API
@pytest.fixture()
def client(tmp_path):
    settings = Settings(database_url=f"sqlite:///{(tmp_path / 'mltrain.db').as_posix()}",
                        log_json=False, microsoft_tenant_id="", microsoft_client_id="",
                        ml_val_fraction=0.3, ml_promote_min_roc_auc=0.5, ml_promote_min_pr_auc=0.5)
    app = create_app(settings)
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def test_api_train_promote_infer_rollback(client):
    trained = client.post("/ml/train", json={"window_days": 45}).json()
    assert trained["status"] == "draft" and "roc_auc" in trained["metrics"]
    v1 = trained["version"]
    # detail exposes metrics + feature importance (explainability)
    detail = client.get(f"/ml/models/{v1}").json()
    assert detail["feature_importance"] and detail["metrics"]["pr_auc"] is not None
    # promote
    pr = client.post(f"/ml/models/{v1}/promote").json()
    assert pr["promoted"] is True
    assert client.get("/ml/status").json()["production_model"] == v1
    # inference
    inf = client.post("/ml/inference/run").json()
    assert inf["scored"] == 16
    recs = client.get("/ml/recommendations", params={"company_domain": "c0.com"}).json()
    assert recs and 0.0 <= recs[0]["probability"] <= 1.0
    # a second model + rollback to v1
    v2 = client.post("/ml/train", json={"window_days": 45}).json()["version"]
    client.post(f"/ml/models/{v2}/rollback")  # make v2 active
    back = client.post(f"/ml/models/{v1}/rollback").json()
    assert back["promoted"] is True
    assert client.get("/ml/status").json()["production_model"] == v1


def test_api_inference_requires_model(client):
    # no model promoted yet -> inference is a clean 422, not a crash
    assert client.post("/ml/inference/run").status_code == 422
