"""Enterprise CRM Phase 2: Pipeline & Deal Management tests."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company, DecisionMaker, LeadScore

MGR = {"X-Dev-Role": "manager"}
MEM = {"X-Dev-Role": "member"}

# ---- Default pipeline stage definitions for tests ----
DEFAULT_STAGES = [
    {"name": "Prospect",    "stage_type": "open", "stage_order": 1, "probability": 10},
    {"name": "Qualified",   "stage_type": "open", "stage_order": 2, "probability": 25},
    {"name": "Proposal",    "stage_type": "open", "stage_order": 3, "probability": 60},
    {"name": "Won",         "stage_type": "won",  "stage_order": 4, "probability": 100},
    {"name": "Lost",        "stage_type": "lost", "stage_order": 5, "probability": 0},
]


def _seed(s):
    s.add(Company(
        company_domain="acme.com", canonical_company_id="ACME",
        company_name="Acme Corp", name_key="acme",
        prospect_type="PRODUCT_COMPANY", validation_status="VALID",
        company_tier="INCUMBENT",
    ))
    s.add(Company(
        company_domain="beta.com", canonical_company_id="BETA",
        company_name="Beta Inc", name_key="beta",
        prospect_type="PRODUCT_COMPANY", validation_status="VALID",
        company_tier="SCALEUP",
    ))
    s.flush()
    s.add_all([
        LeadScore(company_domain="acme.com", lead_score=88.0, grade="A", priority_rank=1),
        DecisionMaker(
            linkedin_url="https://l/cto_acme", company_domain="acme.com",
            first_name="Alice", last_name="Smith", current_title="CTO",
            seniority="senior", work_email="alice@acme.com", match_score=90,
        ),
    ])
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'deals.db').as_posix()}",
        log_json=False, dev_auth_bypass=True,
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _make_pipeline(client, name="Test Pipeline", stages=None):
    return client.post("/pipelines", headers=MGR, json={
        "name": name,
        "stages": stages if stages is not None else DEFAULT_STAGES,
    }).json()


def _make_deal(client, pipeline_id, stage_id, **kw):
    payload = {
        "title": kw.get("title", "Test Deal"),
        "company_domain": kw.get("company_domain", "acme.com"),
        "pipeline_id": pipeline_id,
        "stage_id": stage_id,
        "value": kw.get("value", 50000.0),
        "currency": kw.get("currency", "USD"),
        "probability": kw.get("probability", 25),
        "forecast_category": kw.get("forecast_category", "pipeline"),
    }
    return client.post("/deals", headers=MGR, json=payload).json()


# =====================================================================
# Pipeline CRUD
# =====================================================================
class TestPipelineCRUD:
    def test_create_pipeline_no_stages(self, client):
        r = client.post("/pipelines", headers=MGR, json={"name": "Empty Pipeline"})
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Empty Pipeline"
        assert body["stage_count"] == 0
        assert body["is_active"] is True
        assert body["id"] > 0

    def test_create_pipeline_with_stages(self, client):
        body = _make_pipeline(client)
        assert body["stage_count"] == len(DEFAULT_STAGES)
        assert body["stages"][0]["name"] == "Prospect"
        assert body["stages"][3]["stage_type"] == "won"

    def test_list_pipelines_empty(self, client):
        r = client.get("/pipelines", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_list_pipelines_populated(self, client):
        _make_pipeline(client, "P1")
        _make_pipeline(client, "P2")
        r = client.get("/pipelines", headers=MGR)
        assert r.json()["total"] == 2

    def test_get_pipeline(self, client):
        p = _make_pipeline(client)
        r = client.get(f"/pipelines/{p['id']}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["name"] == "Test Pipeline"

    def test_get_pipeline_not_found(self, client):
        r = client.get("/pipelines/9999", headers=MGR)
        assert r.status_code == 404

    def test_patch_pipeline(self, client):
        p = _make_pipeline(client)
        r = client.patch(f"/pipelines/{p['id']}", headers=MGR, json={"name": "Renamed"})
        assert r.status_code == 200
        assert r.json()["name"] == "Renamed"

    def test_delete_pipeline(self, client):
        p = _make_pipeline(client)
        r = client.delete(f"/pipelines/{p['id']}", headers=MGR)
        assert r.status_code == 204
        assert client.get(f"/pipelines/{p['id']}", headers=MGR).status_code == 404

    def test_member_can_create_pipeline(self, client):
        r = client.post("/pipelines", headers=MEM, json={"name": "Member Pipeline"})
        assert r.status_code == 201

    def test_member_cannot_delete_pipeline(self, client):
        p = _make_pipeline(client)
        r = client.delete(f"/pipelines/{p['id']}", headers=MEM)
        assert r.status_code == 403


# =====================================================================
# Stage Management
# =====================================================================
class TestStageManagement:
    def test_add_stage(self, client):
        p = _make_pipeline(client, stages=[])
        r = client.post(f"/pipelines/{p['id']}/stages", headers=MGR, json={
            "name": "Discovery", "stage_type": "open", "stage_order": 1, "probability": 40,
        })
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Discovery"
        assert body["probability"] == 40

    def test_patch_stage(self, client):
        p = _make_pipeline(client)
        stage_id = p["stages"][0]["id"]
        r = client.patch(f"/pipelines/{p['id']}/stages/{stage_id}", headers=MGR, json={
            "name": "Updated Prospect", "probability": 15,
        })
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Prospect"
        assert r.json()["probability"] == 15

    def test_delete_stage(self, client):
        p = _make_pipeline(client)
        stage_id = p["stages"][0]["id"]
        r = client.delete(f"/pipelines/{p['id']}/stages/{stage_id}", headers=MGR)
        assert r.status_code == 204

    def test_stage_wrong_pipeline_404(self, client):
        p1 = _make_pipeline(client, "P1")
        p2 = _make_pipeline(client, "P2")
        stage_id = p2["stages"][0]["id"]
        r = client.patch(f"/pipelines/{p1['id']}/stages/{stage_id}", headers=MGR, json={"name": "X"})
        assert r.status_code == 404

    def test_stages_ordered(self, client):
        p = _make_pipeline(client)
        orders = [s["stage_order"] for s in p["stages"]]
        assert orders == sorted(orders)


# =====================================================================
# Deal CRUD
# =====================================================================
class TestDealCRUD:
    def test_create_deal(self, client):
        p = _make_pipeline(client)
        stage_id = p["stages"][0]["id"]
        r = client.post("/deals", headers=MGR, json={
            "title": "ACME Enterprise Deal",
            "company_domain": "acme.com",
            "pipeline_id": p["id"],
            "stage_id": stage_id,
            "value": 75000.0,
            "currency": "USD",
            "probability": 25,
            "forecast_category": "pipeline",
        })
        assert r.status_code == 201
        body = r.json()
        assert body["title"] == "ACME Enterprise Deal"
        assert body["value"] == 75000.0
        assert body["stage_name"] == "Prospect"
        assert body["probability"] == 25
        assert body["id"] > 0

    def test_owner_email_populated_on_every_deal_response(self, client):
        """owner_id defaults to the creator; owner_email must be resolved and
        stay populated across create/get/patch/move — not just list/kanban."""
        p = _make_pipeline(client)
        created = _make_deal(client, p["id"], p["stages"][0]["id"])
        assert created["owner_email"] == "betatestingmanager@siliconpatterns.com"

        fetched = client.get(f"/deals/{created['id']}", headers=MGR).json()
        assert fetched["owner_email"] == "betatestingmanager@siliconpatterns.com"

        patched = client.patch(f"/deals/{created['id']}", headers=MGR, json={"notes": "x"}).json()
        assert patched["owner_email"] == "betatestingmanager@siliconpatterns.com"

        moved = client.post(
            f"/deals/{created['id']}/move", headers=MGR, json={"stage_id": p["stages"][1]["id"]},
        ).json()
        assert moved["owner_email"] == "betatestingmanager@siliconpatterns.com"

    def test_create_deal_wrong_stage_pipeline(self, client):
        p1 = _make_pipeline(client, "P1")
        p2 = _make_pipeline(client, "P2")
        r = client.post("/deals", headers=MGR, json={
            "title": "Bad Deal",
            "company_domain": "acme.com",
            "pipeline_id": p1["id"],
            "stage_id": p2["stages"][0]["id"],  # wrong pipeline's stage
        })
        assert r.status_code == 400

    def test_list_deals_empty(self, client):
        r = client.get("/deals", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_list_deals_filtered_by_pipeline(self, client):
        p1 = _make_pipeline(client, "P1")
        p2 = _make_pipeline(client, "P2")
        _make_deal(client, p1["id"], p1["stages"][0]["id"], title="D1")
        _make_deal(client, p2["id"], p2["stages"][0]["id"], title="D2")
        r = client.get(f"/deals?pipeline_id={p1['id']}", headers=MGR)
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["title"] == "D1"

    def test_list_deals_search(self, client):
        p = _make_pipeline(client)
        _make_deal(client, p["id"], p["stages"][0]["id"], title="Alpha Deal")
        _make_deal(client, p["id"], p["stages"][0]["id"], title="Beta Deal")
        r = client.get("/deals?search=Alpha", headers=MGR)
        assert r.json()["total"] == 1

    def test_get_deal(self, client):
        p = _make_pipeline(client)
        d = _make_deal(client, p["id"], p["stages"][0]["id"])
        r = client.get(f"/deals/{d['id']}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["id"] == d["id"]

    def test_get_deal_not_found(self, client):
        assert client.get("/deals/9999", headers=MGR).status_code == 404

    def test_patch_deal(self, client):
        p = _make_pipeline(client)
        d = _make_deal(client, p["id"], p["stages"][0]["id"])
        r = client.patch(f"/deals/{d['id']}", headers=MGR, json={
            "title": "Updated Title", "value": 99000.0, "notes": "Important account",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["title"] == "Updated Title"
        assert body["value"] == 99000.0
        assert body["notes"] == "Important account"

    def test_delete_deal(self, client):
        p = _make_pipeline(client)
        d = _make_deal(client, p["id"], p["stages"][0]["id"])
        r = client.delete(f"/deals/{d['id']}", headers=MGR)
        assert r.status_code == 204
        assert client.get(f"/deals/{d['id']}", headers=MGR).status_code == 404

    def test_member_cannot_delete_deal(self, client):
        p = _make_pipeline(client)
        d = _make_deal(client, p["id"], p["stages"][0]["id"])
        assert client.delete(f"/deals/{d['id']}", headers=MEM).status_code == 403

    def test_deal_probability_inherits_from_stage(self, client):
        p = _make_pipeline(client)
        stage = p["stages"][1]  # Qualified, probability=25
        d = client.post("/deals", headers=MGR, json={
            "title": "Inherited Prob Deal",
            "company_domain": "acme.com",
            "pipeline_id": p["id"],
            "stage_id": stage["id"],
            # No probability specified → inherits from stage
        }).json()
        assert d["probability"] == stage["probability"]


# =====================================================================
# Kanban Board
# =====================================================================
class TestKanban:
    def test_kanban_returns_all_stages(self, client):
        p = _make_pipeline(client)
        r = client.get(f"/pipelines/{p['id']}/kanban", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert len(body["columns"]) == len(DEFAULT_STAGES)
        assert body["pipeline_id"] == p["id"]

    def test_kanban_deals_in_columns(self, client):
        p = _make_pipeline(client)
        s0 = p["stages"][0]
        s1 = p["stages"][1]
        _make_deal(client, p["id"], s0["id"], title="D1")
        _make_deal(client, p["id"], s0["id"], title="D2")
        _make_deal(client, p["id"], s1["id"], title="D3")
        r = client.get(f"/pipelines/{p['id']}/kanban", headers=MGR)
        cols = {c["stage_id"]: c for c in r.json()["columns"]}
        assert cols[s0["id"]]["deal_count"] == 2
        assert cols[s1["id"]]["deal_count"] == 1

    def test_kanban_total_value(self, client):
        p = _make_pipeline(client)
        s0 = p["stages"][0]["id"]
        _make_deal(client, p["id"], s0, value=10000.0)
        _make_deal(client, p["id"], s0, value=20000.0)
        r = client.get(f"/pipelines/{p['id']}/kanban", headers=MGR)
        assert r.json()["total_value"] == pytest.approx(30000.0)

    def test_kanban_lazy_single_stage(self, client):
        p = _make_pipeline(client)
        s0 = p["stages"][0]
        _make_deal(client, p["id"], s0["id"])
        r = client.get(f"/pipelines/{p['id']}/kanban?stage_id={s0['id']}", headers=MGR)
        assert len(r.json()["columns"]) == 1
        assert r.json()["columns"][0]["stage_id"] == s0["id"]

    def test_kanban_search_filter(self, client):
        p = _make_pipeline(client)
        s0 = p["stages"][0]["id"]
        _make_deal(client, p["id"], s0, title="Alpha")
        _make_deal(client, p["id"], s0, title="Beta")
        r = client.get(f"/pipelines/{p['id']}/kanban?search=Alpha", headers=MGR)
        total = sum(c["deal_count"] for c in r.json()["columns"])
        assert total == 1

    def test_kanban_pipeline_not_found(self, client):
        r = client.get("/pipelines/9999/kanban", headers=MGR)
        assert r.status_code == 404


# =====================================================================
# Stage Move (Kanban Drag & Drop)
# =====================================================================
class TestDealMove:
    def test_move_deal_to_new_stage(self, client):
        p = _make_pipeline(client)
        s0 = p["stages"][0]
        s1 = p["stages"][1]
        d = _make_deal(client, p["id"], s0["id"])
        r = client.post(f"/deals/{d['id']}/move", headers=MGR, json={"stage_id": s1["id"]})
        assert r.status_code == 200
        body = r.json()
        assert body["stage_id"] == s1["id"]
        assert body["stage_name"] == s1["name"]
        assert body["probability"] == s1["probability"]

    def test_move_records_history(self, client):
        p = _make_pipeline(client)
        s0 = p["stages"][0]
        s1 = p["stages"][1]
        d = _make_deal(client, p["id"], s0["id"])
        client.post(f"/deals/{d['id']}/move", headers=MGR, json={"stage_id": s1["id"]})
        hist = client.get(f"/deals/{d['id']}/history", headers=MGR).json()
        # Initial entry + move entry
        assert len(hist) == 2
        assert hist[0]["to_stage_id"] == s0["id"]  # ordered by entered_at asc
        assert hist[1]["to_stage_id"] == s1["id"]
        # Previous stage was closed with time_in_stage_seconds set
        assert hist[0]["exited_at"] is not None
        assert hist[0]["time_in_stage_seconds"] is not None

    def test_move_same_stage_is_noop(self, client):
        p = _make_pipeline(client)
        s0 = p["stages"][0]
        d = _make_deal(client, p["id"], s0["id"])
        r = client.post(f"/deals/{d['id']}/move", headers=MGR, json={"stage_id": s0["id"]})
        assert r.status_code == 200
        hist = client.get(f"/deals/{d['id']}/history", headers=MGR).json()
        assert len(hist) == 1  # only the initial entry, no new history created

    def test_move_to_wrong_pipeline_stage(self, client):
        p1 = _make_pipeline(client, "P1")
        p2 = _make_pipeline(client, "P2")
        d = _make_deal(client, p1["id"], p1["stages"][0]["id"])
        r = client.post(f"/deals/{d['id']}/move", headers=MGR, json={"stage_id": p2["stages"][0]["id"]})
        assert r.status_code == 400

    def test_multiple_moves_build_history(self, client):
        p = _make_pipeline(client)
        stages = p["stages"]
        d = _make_deal(client, p["id"], stages[0]["id"])
        client.post(f"/deals/{d['id']}/move", headers=MEM, json={"stage_id": stages[1]["id"]})
        client.post(f"/deals/{d['id']}/move", headers=MEM, json={"stage_id": stages[2]["id"]})
        hist = client.get(f"/deals/{d['id']}/history", headers=MGR).json()
        assert len(hist) == 3


# =====================================================================
# Stage History & Velocity
# =====================================================================
class TestStageHistory:
    def test_initial_history_created_on_deal_create(self, client):
        p = _make_pipeline(client)
        d = _make_deal(client, p["id"], p["stages"][0]["id"])
        hist = client.get(f"/deals/{d['id']}/history", headers=MGR).json()
        assert len(hist) == 1
        assert hist[0]["from_stage_id"] is None
        assert hist[0]["to_stage_id"] == p["stages"][0]["id"]
        assert hist[0]["exited_at"] is None

    def test_time_in_stage_computed_on_exit(self, client):
        p = _make_pipeline(client)
        d = _make_deal(client, p["id"], p["stages"][0]["id"])
        client.post(f"/deals/{d['id']}/move", headers=MGR, json={"stage_id": p["stages"][1]["id"]})
        hist = client.get(f"/deals/{d['id']}/history", headers=MGR).json()
        assert hist[0]["time_in_stage_seconds"] is not None
        assert hist[0]["time_in_stage_seconds"] >= 0


# =====================================================================
# Forecast
# =====================================================================
class TestForecast:
    def _setup(self, client):
        p = _make_pipeline(client)
        stages = {s["stage_type"]: s for s in p["stages"]}
        # open deals
        _make_deal(client, p["id"], stages["open"]["id"], value=100_000.0, probability=50)
        _make_deal(client, p["id"], stages["open"]["id"], value=200_000.0, probability=75)
        # won deal
        _make_deal(client, p["id"], stages["won"]["id"], value=150_000.0, probability=100)
        # lost deal
        _make_deal(client, p["id"], stages["lost"]["id"], value=80_000.0, probability=0)
        return p

    def test_forecast_pipeline_value(self, client):
        p = self._setup(client)
        r = client.get(f"/pipelines/{p['id']}/forecast", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        # 100k + 200k open
        assert body["pipeline_value"] == pytest.approx(300_000.0)

    def test_forecast_weighted_pipeline(self, client):
        p = self._setup(client)
        body = client.get(f"/pipelines/{p['id']}/forecast", headers=MGR).json()
        # 100k*0.5 + 200k*0.75 = 50k + 150k = 200k
        assert body["weighted_pipeline"] == pytest.approx(200_000.0)

    def test_forecast_win_probability(self, client):
        p = self._setup(client)
        body = client.get(f"/pipelines/{p['id']}/forecast", headers=MGR).json()
        # 1 won / 2 closed = 50%
        assert body["win_probability"] == pytest.approx(50.0)

    def test_forecast_deal_counts(self, client):
        p = self._setup(client)
        body = client.get(f"/pipelines/{p['id']}/forecast", headers=MGR).json()
        assert body["open_deals"] == 2
        assert body["won_deals"] == 1
        assert body["lost_deals"] == 1

    def test_forecast_empty_pipeline(self, client):
        p = _make_pipeline(client)
        body = client.get(f"/pipelines/{p['id']}/forecast", headers=MGR).json()
        assert body["pipeline_value"] == 0.0
        assert body["weighted_pipeline"] == 0.0
        assert body["win_probability"] == 0.0

    def test_forecast_by_quarter(self, client):
        p = _make_pipeline(client)
        stage_id = p["stages"][0]["id"]
        # Deal closing in Q1 2026
        client.post("/deals", headers=MGR, json={
            "title": "Q1 Deal",
            "company_domain": "acme.com",
            "pipeline_id": p["id"],
            "stage_id": stage_id,
            "value": 50_000.0,
            "probability": 80,
            "forecast_category": "commit",
            "expected_close_date": "2026-03-15T00:00:00Z",
        })
        body = client.get(f"/pipelines/{p['id']}/forecast", headers=MGR).json()
        quarters = {q["quarter"]: q["weighted_value"] for q in body["forecast_by_quarter"]}
        assert "Q1 2026" in quarters
        assert quarters["Q1 2026"] == pytest.approx(40_000.0)

    def test_forecast_not_found(self, client):
        r = client.get("/pipelines/9999/forecast", headers=MGR)
        assert r.status_code == 404


# =====================================================================
# Analytics
# =====================================================================
class TestPipelineAnalytics:
    def test_analytics_win_loss_rates(self, client):
        p = _make_pipeline(client)
        stages = {s["name"]: s for s in p["stages"]}
        _make_deal(client, p["id"], stages["Won"]["id"], value=100_000.0)
        _make_deal(client, p["id"], stages["Won"]["id"], value=50_000.0)
        _make_deal(client, p["id"], stages["Lost"]["id"], value=30_000.0)
        body = client.get(f"/pipelines/{p['id']}/analytics", headers=MGR).json()
        assert body["win_rate"] == pytest.approx(2 / 3, rel=0.01)
        assert body["loss_rate"] == pytest.approx(1 / 3, rel=0.01)

    def test_analytics_total_counts(self, client):
        p = _make_pipeline(client)
        s0 = p["stages"][0]["id"]
        _make_deal(client, p["id"], s0)
        _make_deal(client, p["id"], s0)
        body = client.get(f"/pipelines/{p['id']}/analytics", headers=MGR).json()
        assert body["total_deals"] == 2
        assert body["open_deals"] == 2

    def test_analytics_stage_velocity_structure(self, client):
        p = _make_pipeline(client)
        body = client.get(f"/pipelines/{p['id']}/analytics", headers=MGR).json()
        assert len(body["stage_velocity"]) == len(DEFAULT_STAGES)
        for sv in body["stage_velocity"]:
            assert "stage_id" in sv
            assert "avg_time_days" in sv
            assert "conversion_rate" in sv

    def test_analytics_stalled_deals(self, client):
        p = _make_pipeline(client)
        s0 = p["stages"][0]["id"]
        _make_deal(client, p["id"], s0)
        body = client.get(f"/pipelines/{p['id']}/analytics", headers=MGR).json()
        # Freshly created deals are not stalled
        assert body["stalled_deal_count"] == 0

    def test_analytics_not_found(self, client):
        assert client.get("/pipelines/9999/analytics", headers=MGR).status_code == 404


# =====================================================================
# Deal Timeline
# =====================================================================
class TestDealTimeline:
    def test_timeline_empty(self, client):
        p = _make_pipeline(client)
        d = _make_deal(client, p["id"], p["stages"][0]["id"])
        r = client.get(f"/deals/{d['id']}/timeline", headers=MGR)
        assert r.status_code == 200
        events = r.json()
        # Stage change event created on deal creation
        stage_events = [e for e in events if e["event_type"] == "stage_change"]
        assert len(stage_events) == 1

    def test_timeline_after_move(self, client):
        p = _make_pipeline(client)
        stages = p["stages"]
        d = _make_deal(client, p["id"], stages[0]["id"])
        client.post(f"/deals/{d['id']}/move", headers=MGR, json={"stage_id": stages[1]["id"]})
        events = client.get(f"/deals/{d['id']}/timeline", headers=MGR).json()
        stage_events = [e for e in events if e["event_type"] == "stage_change"]
        assert len(stage_events) == 2

    def test_timeline_deal_not_found(self, client):
        assert client.get("/deals/9999/timeline", headers=MGR).status_code == 404

    def test_timeline_ordered_desc(self, client):
        p = _make_pipeline(client)
        stages = p["stages"]
        d = _make_deal(client, p["id"], stages[0]["id"])
        client.post(f"/deals/{d['id']}/move", headers=MGR, json={"stage_id": stages[1]["id"]})
        events = client.get(f"/deals/{d['id']}/timeline", headers=MGR).json()
        timestamps = [e["timestamp"] for e in events]
        assert timestamps == sorted(timestamps, reverse=True)


# =====================================================================
# Dashboard
# =====================================================================
class TestDealDashboard:
    def test_dashboard_empty(self, client):
        r = client.get("/pipelines/dashboard", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert body["total_open_deals"] == 0
        assert body["closing_soon"] == []

    def test_dashboard_with_deals(self, client):
        p = _make_pipeline(client)
        s0 = p["stages"][0]["id"]
        _make_deal(client, p["id"], s0, value=50_000.0)
        _make_deal(client, p["id"], s0, value=100_000.0)
        r = client.get("/pipelines/dashboard", headers=MGR)
        assert r.json()["total_open_deals"] == 2
        assert r.json()["pipeline_value"] == pytest.approx(150_000.0)

    def test_dashboard_recently_won(self, client):
        p = _make_pipeline(client)
        won_stage = next(s for s in p["stages"] if s["stage_type"] == "won")
        _make_deal(client, p["id"], won_stage["id"], value=200_000.0)
        body = client.get("/pipelines/dashboard", headers=MGR).json()
        assert len(body["recently_won"]) == 1

    def test_dashboard_pipeline_filter(self, client):
        p1 = _make_pipeline(client, "P1")
        p2 = _make_pipeline(client, "P2")
        _make_deal(client, p1["id"], p1["stages"][0]["id"], value=100_000.0)
        _make_deal(client, p2["id"], p2["stages"][0]["id"], value=200_000.0)
        body = client.get(f"/pipelines/dashboard?pipeline_id={p1['id']}", headers=MGR).json()
        assert body["pipeline_id"] == p1["id"]
        assert body["pipeline_value"] == pytest.approx(100_000.0)


# =====================================================================
# Deal Intelligence (Opportunity Intelligence Integration)
# =====================================================================
class TestDealIntelligence:
    def test_intelligence_returns_correct_deal(self, client):
        p = _make_pipeline(client)
        d = _make_deal(client, p["id"], p["stages"][0]["id"])
        r = client.get(f"/deals/{d['id']}/intelligence", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert body["deal_id"] == d["id"]
        assert body["company_domain"] == "acme.com"

    def test_intelligence_has_expected_fields(self, client):
        p = _make_pipeline(client)
        d = _make_deal(client, p["id"], p["stages"][0]["id"])
        body = client.get(f"/deals/{d['id']}/intelligence", headers=MGR).json()
        # All intelligence fields must be present (may be null if no data)
        assert "best_contact" in body
        assert "backup_contacts" in body
        assert "buying_committee" in body
        assert "relationship_strength" in body
        assert "success_probability" in body
        assert "next_action" in body
        assert "recommended_sequence" in body
        assert "outreach_priority" in body

    def test_intelligence_deal_not_found(self, client):
        assert client.get("/deals/9999/intelligence", headers=MGR).status_code == 404

    def test_intelligence_relationship_strength_is_numeric(self, client):
        p = _make_pipeline(client)
        d = _make_deal(client, p["id"], p["stages"][0]["id"])
        body = client.get(f"/deals/{d['id']}/intelligence", headers=MGR).json()
        assert isinstance(body["relationship_strength"], int)


# =====================================================================
# Backward Compatibility
# =====================================================================
class TestBackwardCompatibility:
    def test_companies_endpoint_still_works(self, client):
        r = client.get("/companies", headers=MGR)
        assert r.status_code == 200

    def test_leads_endpoint_still_works(self, client):
        r = client.get("/leads", headers=MGR)
        assert r.status_code == 200

    def test_campaigns_endpoint_still_works(self, client):
        r = client.get("/campaigns", headers=MGR)
        assert r.status_code == 200

    def test_pipelines_does_not_conflict_with_orchestrator_pipeline(self, client):
        # GET /pipeline (orchestrator) vs GET /pipelines (CRM) must coexist
        r = client.get("/pipeline/health", headers=MGR)
        assert r.status_code == 200
        r2 = client.get("/pipelines", headers=MGR)
        assert r2.status_code == 200

    def test_sequences_endpoint_still_works(self, client):
        r = client.get("/sequences", headers=MGR)
        assert r.status_code == 200
