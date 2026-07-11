"""Review-driven score adjustment (reconciled Change_05).

The human review may OPTIONALLY influence a SEPARATE adjusted score/grade — the
model score is never touched. These tests exercise the feature ON (it's OFF by
default): boost/penalty/floor, model preservation, anti-stacking, the mandatory
reason + RBAC gates, expiry, the audit snapshot, the combined sort, and analytics.
"""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from lead_scoring.config import ScoringConfig
from lead_scoring.human_review import adjusted_score
from master_db.models import Base, Company, LeadScore


def enabled_cfg() -> ScoringConfig:
    cfg = ScoringConfig.load()
    cfg.review_feedback = {
        "enabled": True,
        "status_effects": {
            "strategic_account": {"boost": 1.15, "floor_grade": "A"},
            "approved": {"boost": 1.05},
            "disqualified": {"penalty": 0.6},
            "watchlist": {},
            "needs_review": {},
        },
    }
    return cfg


def _seed(s):
    s.add_all([
        Company(company_domain="tenstorrent.com", canonical_company_id="TT", company_name="Tenstorrent",
                name_key="tenstorrent", prospect_type="PRODUCT_COMPANY", validation_status="VALID"),
        Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                name_key="acme", prospect_type="PRODUCT_COMPANY", validation_status="VALID"),
        Company(company_domain="globex.com", canonical_company_id="GLOBEX", company_name="Globex",
                name_key="globex", prospect_type="PRODUCT_COMPANY", validation_status="VALID"),
    ])
    s.flush()
    s.add_all([
        LeadScore(company_domain="tenstorrent.com", lead_score=99.0, grade="A+", priority_rank=1, model_version="t"),
        LeadScore(company_domain="acme.com", lead_score=80.0, grade="A", priority_rank=2, model_version="t"),
        LeadScore(company_domain="globex.com", lead_score=49.5, grade="B", priority_rank=3, model_version="t"),
    ])
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'adj.db').as_posix()}",
                              log_json=False, dev_auth_bypass=True))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


@pytest.fixture()
def enabled(monkeypatch):
    """Turn the (default-off) review→score feature ON for the API path."""
    monkeypatch.setattr("backend.services.review_scoring_config", enabled_cfg)


def H(role):
    return {"X-Dev-Role": role}


# ------------------------------------------------------------- pure adjustment
def test_adjusted_off_equals_model():
    cfg = ScoringConfig.load()  # OFF by default
    assert cfg.review_feedback_enabled is False
    assert adjusted_score(49.5, "B", "strategic_account", cfg)[:2] == (49.5, "B")


def test_adjusted_on_boost_floor_penalty_neutral():
    cfg = enabled_cfg()
    s, g, _ = adjusted_score(49.5, "B", "strategic_account", cfg)   # boost → B becomes A
    assert g == "A" and s > 49.5
    # a low score the boost alone can't lift gets floored up to the floor grade
    s2, g2, r2 = adjusted_score(20.0, "C", "strategic_account", cfg)   # 20*1.15=23 < 50 → floored
    assert g2 == "A" and s2 == 50.0 and r2["floor_grade"] == "A"
    assert adjusted_score(80.0, "A", "disqualified", cfg)[1] == "B"       # penalty A → B
    assert adjusted_score(49.5, "B", "watchlist", cfg)[:2] == (49.5, "B")  # neutral, unchanged
    assert adjusted_score(49.5, "B", "needs_review", cfg)[:2] == (49.5, "B")


def test_adjusted_expired_lapses():
    cfg = enabled_cfg()
    s, g, r = adjusted_score(49.5, "B", "strategic_account", cfg, expired=True)
    assert (s, g) == (49.5, "B") and r.get("expired") is True


def test_adjusted_is_idempotent_from_model():
    cfg = enabled_cfg()
    a = adjusted_score(49.5, "B", "strategic_account", cfg)[0]
    b = adjusted_score(49.5, "B", "strategic_account", cfg)[0]
    assert a == b   # always from the pristine model score — never compounds


# --------------------------------------------------------- model preserved (API)
def test_review_adjusts_separate_score_but_preserves_model(client, enabled):
    r = client.put("/reviews/globex.com",
                   json={"review_status": "strategic_account", "human_notes": "Strategic — active programs."},
                   headers=H("manager"))
    assert r.status_code == 200

    ls = client.get("/companies/globex.com").json()["lead_score"]
    assert ls["lead_score"] == 49.5 and ls["grade"] == "B"     # MODEL untouched
    assert ls["adjusted_grade"] == "A" and ls["adjusted_score"] > 49.5  # adjusted is separate
    assert ls["rationale"]["adjustment"]["reason"].startswith("Strategic")
    assert ls["rationale"]["adjustment"]["reviewed_by"].endswith("@siliconpatterns.com")


def test_adjustment_does_not_stack_on_resubmit(client, enabled):
    body = {"review_status": "strategic_account", "human_notes": "known account"}
    client.put("/reviews/globex.com", json=body, headers=H("manager"))
    first = client.get("/companies/globex.com").json()["lead_score"]["adjusted_score"]
    client.put("/reviews/globex.com", json=body, headers=H("manager"))
    second = client.get("/companies/globex.com").json()["lead_score"]["adjusted_score"]
    assert first == second   # re-applying the same verdict never compounds


# ------------------------------------------------------------- reason + RBAC
def test_mandatory_reason_and_rbac(client, enabled):
    # score-affecting status needs a reason
    assert client.put("/reviews/globex.com", json={"review_status": "strategic_account"},
                      headers=H("manager")).status_code == 422
    # ...and manager/admin only
    assert client.put("/reviews/globex.com",
                      json={"review_status": "strategic_account", "human_notes": "x"},
                      headers=H("member")).status_code == 403
    assert client.put("/reviews/globex.com",
                      json={"review_status": "strategic_account", "human_notes": "x"},
                      headers=H("manager")).status_code == 200
    # neutral status is open to members and needs no reason
    assert client.put("/reviews/acme.com", json={"review_status": "watchlist"},
                      headers=H("member")).status_code == 200


def test_feature_off_keeps_task_viii_open_access(client):
    # no `enabled` fixture → feature OFF → members may set any status, no reason required
    assert client.put("/reviews/globex.com", json={"review_status": "strategic_account"},
                      headers=H("member")).status_code == 200
    ls = client.get("/companies/globex.com").json()["lead_score"]
    assert ls["adjusted_grade"] == ls["grade"]   # adjusted == model when off


# ------------------------------------------------------------- expiry
def test_expired_review_does_not_affect_score(client, enabled):
    r = client.put("/reviews/globex.com",
                   json={"review_status": "strategic_account", "human_notes": "lapsed",
                         "expires_at": "2000-01-01T00:00:00Z"},
                   headers=H("manager"))
    assert r.status_code == 200 and r.json()["expires_at"] is not None
    ls = client.get("/companies/globex.com").json()["lead_score"]
    assert ls["adjusted_grade"] == "B" and ls["adjusted_score"] == 49.5   # effect lapsed → model
    assert ls["rationale"]["adjustment"]["expired"] is True


# ------------------------------------------------------------- audit snapshot
def test_audit_event_snapshots_model_and_adjusted(client, enabled):
    client.put("/reviews/globex.com",
               json={"review_status": "strategic_account", "human_notes": "snapshot"}, headers=H("manager"))
    hist = client.get("/reviews/globex.com/history").json()
    assert hist[0]["model_grade"] == "B" and hist[0]["model_score"] == 49.5
    assert hist[0]["adjusted_grade"] == "A" and hist[0]["adjusted_score"] > 49.5


# ------------------------------------------------------- combined sort + analytics
def test_combined_sort_and_adjustment_analytics(client, enabled):
    client.put("/reviews/globex.com", json={"review_status": "strategic_account", "human_notes": "up"},
               headers=H("manager"))     # B 49.5 → A ~56.9
    client.put("/reviews/acme.com", json={"review_status": "disqualified", "human_notes": "down"},
               headers=H("manager"))     # A 80 → B 48

    combined = [x["company_domain"] for x in client.get("/leads?sort=combined").json()["items"]]
    # by adjusted score: tenstorrent (100) > globex (~56.9) > acme (48)
    assert combined == ["tenstorrent.com", "globex.com", "acme.com"]

    stats = client.get("/reviews/reports").json()["adjustments"]
    assert stats["enabled"] is True
    assert stats["boosted"] >= 1 and stats["penalised"] >= 1
    assert stats["active_adjustments"] >= 2
    assert stats["total_delta"] != 0.0
    movers = {m["company_domain"] for m in stats["movers"]}
    assert {"globex.com", "acme.com"} <= movers
