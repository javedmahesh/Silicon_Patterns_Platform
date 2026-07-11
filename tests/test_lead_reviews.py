"""Human lead review + feedback system (P-task viii).

Verifies the core promise — the human assessment is stored SEPARATELY and never
overwrites the model score — plus the audit trail, the lead-table human status +
combined ranking, and the model-vs-human reports.
"""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from lead_scoring.human_review import disagreement
from master_db.models import Base, Company, LeadScore


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
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'reviews.db').as_posix()}",
                              log_json=False, dev_auth_bypass=True))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def H(role):
    return {"X-Dev-Role": role}


# --------------------------------------------------------------- pure logic
def test_disagreement_classification():
    assert disagreement("A+", "disqualified") == "false_positive"
    assert disagreement("A", "disqualified") == "false_positive"
    assert disagreement("C", "strategic_account") == "false_negative"
    assert disagreement("B", "approved") == "false_negative"
    assert disagreement("A+", "strategic_account") is None   # model + human agree
    assert disagreement("B", "needs_review") is None


# --------------------------------------------------------------- preserve model score
def test_review_is_separate_and_never_overwrites_model_score(client):
    before = client.get("/companies/globex.com").json()
    assert before["lead_score"]["grade"] == "B" and before["lead_score"]["lead_score"] == 49.5
    assert before["lead_review"] is None

    r = client.put("/reviews/globex.com",
                   json={"review_status": "strategic_account",
                         "human_notes": "Existing customer relationship with multiple active projects."},
                   headers=H("member"))
    assert r.status_code == 200
    assert r.json()["review_status"] == "strategic_account"
    assert r.json()["reviewed_by_email"] == "betatestingmember@siliconpatterns.com"

    after = client.get("/companies/globex.com").json()
    # model score/grade are UNTOUCHED; the human verdict lives alongside it
    assert after["lead_score"]["grade"] == "B" and after["lead_score"]["lead_score"] == 49.5
    assert after["lead_review"]["review_status"] == "strategic_account"
    assert "multiple active projects" in after["lead_review"]["human_notes"]
    assert after["counts"]["review_events"] == 1


# --------------------------------------------------------------- audit trail
def test_review_history_audit_trail(client):
    for status in ("needs_review", "watchlist", "approved"):
        assert client.put("/reviews/acme.com", json={"review_status": status},
                          headers=H("manager")).status_code == 200

    hist = client.get("/reviews/acme.com/history").json()
    assert len(hist) == 3
    # newest first; the chain records previous -> new status, user, and a model snapshot
    assert hist[0]["to_status"] == "approved" and hist[0]["from_status"] == "watchlist"
    assert hist[0]["actor_email"] == "betatestingmanager@siliconpatterns.com"
    assert hist[0]["model_grade"] == "A" and hist[0]["model_score"] == 80.0
    assert hist[-1]["from_status"] == "" and hist[-1]["to_status"] == "needs_review"
    # surfaces in the unified company activity timeline too
    assert "review" in {a["kind"] for a in client.get("/companies/acme.com/activity").json()}


# --------------------------------------------------------------- lead table + ranking
def test_lead_table_human_status_and_sorts(client):
    # (review_feedback is OFF by default, so members may set any status and the
    #  model score is untouched — adjusted == model everywhere.)
    client.put("/reviews/tenstorrent.com", json={"review_status": "strategic_account"}, headers=H("member"))
    client.put("/reviews/acme.com", json={"review_status": "disqualified"}, headers=H("member"))

    # model order: by priority_rank (untouched by human review)
    model = [x["company_domain"] for x in client.get("/leads?sort=model").json()["items"]]
    assert model == ["tenstorrent.com", "acme.com", "globex.com"]

    # human order: group by status tier — strategic floats up, disqualified sinks below unreviewed
    human = client.get("/leads?sort=human").json()["items"]
    assert [x["company_domain"] for x in human] == ["tenstorrent.com", "globex.com", "acme.com"]

    # combined order: by adjusted score — with the feature OFF, adjusted == model
    combined = [x["company_domain"] for x in client.get("/leads?sort=combined").json()["items"]]
    assert combined == ["tenstorrent.com", "acme.com", "globex.com"]

    by_dom = {x["company_domain"]: x for x in human}
    assert by_dom["tenstorrent.com"]["human_status"] == "strategic_account"
    assert by_dom["acme.com"]["human_status"] == "disqualified"
    assert by_dom["globex.com"]["human_status"] is None      # unreviewed shows no human status
    # both verdicts present; with feature off the adjusted grade equals the model grade
    assert by_dom["tenstorrent.com"]["grade"] == "A+"
    assert by_dom["tenstorrent.com"]["adjusted_grade"] == "A+"


# --------------------------------------------------------------- reports (§7)
def test_review_reports_disagreements_and_false_pos_neg(client):
    client.put("/reviews/tenstorrent.com", json={"review_status": "disqualified"}, headers=H("manager"))  # A+ but disq
    client.put("/reviews/globex.com", json={"review_status": "strategic_account"}, headers=H("manager"))  # B but strategic

    rep = client.get("/reviews/reports").json()
    fp = {r["company_domain"] for r in rep["false_positives"]}
    fn = {r["company_domain"] for r in rep["false_negatives"]}
    assert "tenstorrent.com" in fp
    assert "globex.com" in fn
    assert {"tenstorrent.com", "globex.com"} <= {r["company_domain"] for r in rep["disagreements"]}
    assert "globex.com" in {r["company_domain"] for r in rep["strategic_accounts"]}
    assert rep["status_distribution"].get("strategic_account") == 1
    assert rep["status_distribution"].get("disqualified") == 1


def test_frequently_overridden(client):
    for status in ("needs_review", "watchlist", "approved", "strategic_account"):
        client.put("/reviews/acme.com", json={"review_status": status}, headers=H("manager"))
    client.put("/reviews/globex.com", json={"review_status": "approved"}, headers=H("manager"))  # only once

    rep = client.get("/reviews/reports").json()
    overridden = {r["company_domain"]: r["override_count"] for r in rep["frequently_overridden"]}
    assert overridden.get("acme.com") == 4
    assert "globex.com" not in overridden   # a single action is not "frequently overridden"


# --------------------------------------------------------------- access + validation
def test_any_user_can_review_but_status_is_validated(client):
    # open to any authenticated user (analyst feedback, like notes)
    assert client.put("/reviews/acme.com", json={"review_status": "watchlist"},
                      headers=H("member")).status_code == 200
    # invalid status rejected
    assert client.put("/reviews/acme.com", json={"review_status": "super_hot"},
                      headers=H("member")).status_code == 422
    # unknown company -> 404
    assert client.put("/reviews/nope.com", json={"review_status": "approved"},
                      headers=H("member")).status_code == 404
