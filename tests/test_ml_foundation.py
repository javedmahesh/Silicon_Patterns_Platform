"""Machine Learning Foundation — decay, embeddings, feature store, feedback, dataset,
registries, API, and non-regression (lead scoring + scheduler untouched).

No model is trained; this exercises the infrastructure only.
"""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.local import make_session_factory
from master_db.models import (
    Base, Company, DecisionMaker, DemandSignal, LeadScore, MlTrainingRun,
    Opportunity, RoleEmbedding,
)
from ml import decay, dataset, features as feat, feedback, registry
from ml import embeddings as emb

SETTINGS = Settings(database_url="sqlite:///:memory:", ml_embedding_dim=384)


@pytest.fixture()
def session():
    Session = make_session_factory(":memory:")
    with Session() as s:
        s.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                      name_key="acme", company_tier="STARTUP", prospect_type="PRODUCT_COMPANY",
                      compliance_flag="APPROVED", industry_category="Fabless",
                      technology_focus="RTL, ASIC", validation_status="VALID"))
        s.flush()
        s.add_all([
            Opportunity(opportunity_id="O1", company_domain="acme.com", opportunity_type="FUNDING",
                        effective_opportunity_score=80, published_date="2026-07-01", technologies=["RISC-V"]),
            Opportunity(opportunity_id="O2", company_domain="acme.com", opportunity_type="HIRING",
                        effective_opportunity_score=60, published_date="2026-05-01"),
            DecisionMaker(linkedin_url="https://l/1", company_domain="acme.com",
                          current_title="VP Engineering", seniority="senior", match_score=88.0),
            DecisionMaker(linkedin_url="https://l/2", company_domain="acme.com",
                          current_title="Director of ASIC", seniority="senior", match_score=70.0),
            LeadScore(company_domain="acme.com", lead_score=75.0, grade="A", opportunity_subscore=80,
                      coverage=3, model_version="t"),
            DemandSignal(company_domain="acme.com", demand_score=90.0, total_engineering_jobs=40,
                         lead_readiness_score=70.0),
        ])
        s.commit()
        yield s


# ------------------------------------------------------------------ decay
def test_decay_categories_and_exponential():
    assert decay.decay_category("FUNDING") == "funding"
    assert decay.decay_category("LAYOFF") == "layoffs"
    assert decay.decay_category("PRODUCT_LAUNCH") == "projects"
    assert decay.decay_category("mystery") == "default"
    assert decay.exp_decay(0, 30) == 1.0
    assert abs(decay.exp_decay(30, 30) - 0.5) < 1e-9
    # funding (hl 120) outlasts a layoff (hl 30) at the same age
    assert decay.decayed_strength(80, 60, "funding") > decay.decayed_strength(80, 60, "layoffs")


def test_decay_features_per_category():
    f = decay.decay_features([("FUNDING", 80, 10), ("LAYOFF", 70, 200), ("HIRING", 50, 0)])
    assert f.per_category["funding"] > 0 and f.per_category["hiring"] == 50.0
    assert f.per_category["layoffs"] < 5  # heavily decayed
    assert f.active_count >= 1 and f.overall_max > 0


# ------------------------------------------------------------------ embeddings
def test_embeddings_deterministic_and_unit_norm():
    a = emb._hash_embed(emb.normalize_title("VP  Engineering"), 384)
    b = emb._hash_embed(emb.normalize_title("vp engineering"), 384)
    assert a == b and len(a) == 384
    import math
    assert abs(math.sqrt(sum(x * x for x in a)) - 1.0) < 1e-6


def test_embeddings_cache_reused(session):
    titles = ["VP Engineering", "Director of ASIC", "VP Engineering"]
    v1 = emb.embed_titles(session, titles, SETTINGS)
    session.commit()
    n_after_first = session.query(RoleEmbedding).count()
    assert n_after_first == 2  # deduped: 2 distinct titles cached
    v2 = emb.embed_titles(session, titles, SETTINGS)  # second call reuses cache
    session.commit()
    assert session.query(RoleEmbedding).count() == n_after_first  # NO new rows
    assert v1 == v2


# ------------------------------------------------------------------ feature store
def test_feature_store_has_all_groups(session):
    res = feat.build_features_batch(session, SETTINGS)
    session.commit()
    fv = res.features["acme.com"]
    # company / opportunity / news / career / dm / lead / engagement / decay / tags / embedding
    for key in ("company_tier_rank", "num_opportunities", "newest_signal_age_days",
                "total_engineering_jobs", "dm_count", "senior_dm_count", "lead_score",
                "engagement_total", "decay_funding", "tech_tag_count", "dm_role_embedding_mean"):
        assert key in fv, key
    assert fv["lead_score"] == 75.0 and fv["dm_count"] == 2 and fv["senior_dm_count"] == 2
    assert fv["decay_funding"] > 0 and fv["tech_tags"] == ["ASIC", "RISC-V", "RTL"]
    assert len(fv["dm_role_embedding_mean"]) == 384


def test_feature_generation_deterministic(session):
    a = feat.build_company_features("acme.com", feat.load_bundle(session, SETTINGS))
    b = feat.build_company_features("acme.com", feat.load_bundle(session, SETTINGS))
    assert a == b


def test_feature_store_incremental_reuse(session):
    r1 = feat.build_features_batch(session, SETTINGS)
    session.commit()
    assert r1.computed == 1 and r1.reused == 0
    r2 = feat.build_features_batch(session, SETTINGS)  # unchanged inputs, same day
    session.commit()
    assert r2.computed == 0 and r2.reused == 1  # reused the cache, no recompute


def test_feature_store_recomputes_on_data_change(session):
    feat.build_features_batch(session, SETTINGS)
    session.commit()
    session.add(Opportunity(opportunity_id="O3", company_domain="acme.com",
                            opportunity_type="ACQUISITION", effective_opportunity_score=90,
                            published_date="2026-07-05"))
    session.commit()
    r = feat.build_features_batch(session, SETTINGS)  # inputs changed -> recompute
    session.commit()
    assert r.computed == 1 and r.reused == 0


# ------------------------------------------------------------------ feedback
def test_record_interaction_and_weights(session):
    i = feedback.record_interaction(session, interaction_type="contact", entity_type="company",
                                    entity_id="acme.com", company_domain="acme.com")
    assert i.sample_weight == feedback.DEFAULT_SAMPLE_WEIGHTS["contact"] == 1.5
    feedback.record_interaction(session, interaction_type="ignore", entity_type="opportunity",
                                entity_id="O1", company_domain="acme.com")
    session.commit()
    counts = feedback.engagement_counts(session)
    assert counts["acme.com"] == {"positive": 1, "negative": 1, "total": 2}
    with pytest.raises(ValueError):
        feedback.record_interaction(session, interaction_type="nope", entity_type="company", entity_id="x")


# ------------------------------------------------------------------ dataset
def test_dataset_builder_labels_and_clamp(session):
    feedback.record_interaction(session, interaction_type="thumbs_up", entity_type="company",
                                entity_id="acme.com", company_domain="acme.com")
    feedback.record_interaction(session, interaction_type="thumbs_down", entity_type="opportunity",
                                entity_id="O2", company_domain="acme.com")
    session.commit()
    res = dataset.build_training_dataset(session, SETTINGS, window_days=10)  # clamps up to 30
    session.commit()
    assert res.window_days == 30
    assert res.row_count == 2 and res.positive == 1 and res.negative == 1
    # each row carries the feature vector + label + weight
    assert "lead_score" in res.rows[0] and "label" in res.rows[0] and "sample_weight" in res.rows[0]
    # a training-run + feature-version were recorded (no model trained)
    assert session.query(MlTrainingRun).count() == 1
    run = session.query(MlTrainingRun).one()
    assert run.status == "dataset_built" and run.row_count == 2


def test_dataset_deterministic(session):
    feedback.record_interaction(session, interaction_type="export", entity_type="company",
                                entity_id="acme.com", company_domain="acme.com")
    session.commit()
    a = dataset.build_training_dataset(session, SETTINGS, window_days=60, persist=False)
    b = dataset.build_training_dataset(session, SETTINGS, window_days=60, persist=False)
    assert a.rows == b.rows


# ------------------------------------------------------------------ registry
def test_registry_model_and_feature_version(session):
    registry.register_feature_version(session, "fs-1", {"features": feat.feature_spec()})
    m = registry.register_model(session, name="lead_recommender", version="v0", status="draft",
                                model_type="none", feature_version="fs-1")
    session.commit()
    assert m.id and registry.list_models(session)[0].version == "v0"
    m2 = registry.register_model(session, name="lead_recommender", version="v1", status="active")
    session.commit()
    assert registry.active_model(session).version == "v1"


# ------------------------------------------------------------------ non-regression
def test_lead_scoring_unchanged_by_ml(session):
    from lead_scoring.service import score_all
    before = score_all(session)
    feat.build_features_batch(session, SETTINGS)  # building ML features must not touch scores
    session.commit()
    after = score_all(session)
    assert before.scored == after.scored
    ls = session.query(LeadScore).filter_by(company_domain="acme.com").one()
    assert ls.lead_score > 0  # scoring still works, unchanged pathway


def test_scheduler_and_pipeline_untouched():
    import orchestrator.stages as stages
    # ML is deliberately NOT a pipeline stage — the Standard Run / scheduler are unchanged.
    assert "ml" not in stages.PIPELINE_ORDER
    assert "features" not in stages.PIPELINE_ORDER
    from backend import standard_run
    assert standard_run.STANDARD_RUN_COMPONENTS is None  # unchanged default


# ------------------------------------------------------------------ API
@pytest.fixture()
def client(tmp_path):
    settings = Settings(database_url=f"sqlite:///{(tmp_path / 'ml.db').as_posix()}",
                        log_json=False, microsoft_tenant_id="", microsoft_client_id="")
    app = create_app(settings)
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                          name_key="acme", company_tier="STARTUP", compliance_flag="APPROVED",
                          validation_status="VALID"))
            s.flush()
            s.add_all([
                Opportunity(opportunity_id="O1", company_domain="acme.com", opportunity_type="FUNDING",
                            effective_opportunity_score=80, published_date="2026-07-01"),
                LeadScore(company_domain="acme.com", lead_score=75.0, grade="A", model_version="t"),
            ])
            s.commit()
        yield c


def test_api_record_interaction_and_status(client):
    r = client.post("/ml/interactions", json={"interaction_type": "thumbs_up",
                    "entity_type": "opportunity", "entity_id": "O1", "company_domain": "acme.com"})
    assert r.status_code == 201 and r.json()["sample_weight"] == 1.0
    st = client.get("/ml/status").json()
    assert st["ml_enabled"] is True and st["feature_version"] == "fs-1"
    assert st["interaction_count"] == 1 and st["embedding_backend"] == "hash"


def test_api_bad_interaction_rejected(client):
    assert client.post("/ml/interactions", json={"interaction_type": "boo",
                       "entity_type": "opportunity", "entity_id": "O1"}).status_code == 422


def test_api_feature_refresh_and_vector(client):
    ref = client.post("/ml/features/refresh").json()
    assert ref["computed"] >= 1 and ref["feature_version"] == "fs-1"
    fv = client.get("/ml/features/acme.com").json()
    assert fv["entity_id"] == "acme.com" and "lead_score" in fv["features"]
    # second refresh reuses the cache
    ref2 = client.post("/ml/features/refresh").json()
    assert ref2["reused"] >= 1


def test_api_dataset_build_and_models(client):
    client.post("/ml/interactions", json={"interaction_type": "contact",
                "entity_type": "company", "entity_id": "acme.com", "company_domain": "acme.com"})
    ds = client.post("/ml/dataset/build", params={"window_days": 45}).json()
    assert ds["window_days"] == 45 and ds["row_count"] == 1 and ds["positive"] == 1
    assert "lead_score" in ds["columns"]
    assert client.get("/ml/models").json() == []  # registry empty (no model registered/trained)
