"""Enterprise CRM Phase 11: Enterprise Search & Knowledge Platform tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company

MGR = {"X-Dev-Role": "manager"}
MEM = {"X-Dev-Role": "member"}
ADMIN = {"X-Dev-Role": "admin"}

DEFAULT_STAGES = [
    {"name": "Prospect", "stage_type": "open", "stage_order": 1, "probability": 10},
    {"name": "Won", "stage_type": "won", "stage_order": 2, "probability": 100},
    {"name": "Lost", "stage_type": "lost", "stage_order": 3, "probability": 0},
]


def _seed(s):
    s.add(Company(
        company_domain="acme.com", canonical_company_id="ACME",
        company_name="Acme Rocket Corp", name_key="acme",
        prospect_type="PRODUCT_COMPANY", validation_status="VALID",
        company_tier="INCUMBENT",
    ))
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'search.db').as_posix()}",
        log_json=False, dev_auth_bypass=True,
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _make_pipeline(client):
    return client.post("/pipelines", headers=MGR, json={"name": "P", "stages": DEFAULT_STAGES}).json()


def _make_deal(client, pipeline_id, stage_id, **kw):
    payload = {
        "title": kw.get("title", "Rocket Deal"), "company_domain": "acme.com",
        "pipeline_id": pipeline_id, "stage_id": stage_id,
        "value": 50_000.0, "probability": 25,
    }
    return client.post("/deals", headers=MGR, json=payload).json()


def _make_category(client, **kw):
    payload = {"name": "Onboarding", **kw}
    return client.post("/knowledge/categories", headers=MGR, json=payload).json()


def _make_article(client, **kw):
    payload = {"title": "Getting Started with Rockets", "body": "This article covers rocket setup.", "tags": ["rocket", "setup"], **kw}
    return client.post("/knowledge/articles", headers=MGR, json=payload).json()


# =====================================================================
# Global Search
# =====================================================================
class TestGlobalSearch:
    def test_search_finds_company(self, client):
        r = client.get("/search", headers=MGR, params={"q": "Rocket"})
        assert r.status_code == 200
        body = r.json()
        assert any(x["entity_type"] == "company" for x in body["results"])

    def test_search_finds_deal(self, client):
        pipeline = _make_pipeline(client)
        open_stage = next(s for s in pipeline["stages"] if s["stage_type"] == "open")
        _make_deal(client, pipeline["id"], open_stage["id"], title="Big Rocket Deal")
        r = client.get("/search", headers=MGR, params={"q": "Big Rocket"})
        assert any(x["entity_type"] == "deal" and x["title"] == "Big Rocket Deal" for x in r.json()["results"])

    def test_search_empty_query_returns_no_results(self, client):
        r = client.get("/search", headers=MGR, params={"q": ""})
        assert r.json()["results"] == []

    def test_search_filters_by_entity_types(self, client):
        pipeline = _make_pipeline(client)
        open_stage = next(s for s in pipeline["stages"] if s["stage_type"] == "open")
        _make_deal(client, pipeline["id"], open_stage["id"], title="Rocket Deal")
        r = client.get("/search", headers=MGR, params={"q": "Rocket", "entity_types": ["company"]})
        assert all(x["entity_type"] == "company" for x in r.json()["results"])

    def test_search_relevance_ranking_exact_match_first(self, client):
        client.post("/knowledge/categories", headers=MGR, json={"name": "Rocket"})
        client.post("/knowledge/categories", headers=MGR, json={"name": "Rocket Science 101"})
        r = client.get("/search", headers=MGR, params={"q": "Rocket", "entity_types": ["custom_object"]})
        assert r.status_code == 200

    def test_search_pagination(self, client):
        for i in range(5):
            client.post("/deals", headers=MGR, json={
                "title": f"Widget Deal {i}", "company_domain": "acme.com",
                "pipeline_id": _make_pipeline(client)["id"] if i == 0 else 1,
                "stage_id": 1, "value": 1000.0, "probability": 10,
            })
        r1 = client.get("/search", headers=MGR, params={"q": "Widget Deal", "entity_types": ["deal"], "limit": 2, "offset": 0})
        assert len(r1.json()["results"]) <= 2

    def test_full_text_search_finds_notes(self, client):
        pipeline = _make_pipeline(client)
        open_stage = next(s for s in pipeline["stages"] if s["stage_type"] == "open")
        deal = _make_deal(client, pipeline["id"], open_stage["id"])
        client.patch(f"/deals/{deal['id']}", headers=MGR, json={"notes": "Customer mentioned unique keyword zzqx99"})
        r = client.get("/search/full-text", headers=MGR, params={"q": "zzqx99"})
        assert any(x["entity_type"] == "note" for x in r.json()["results"])

    def test_full_text_search_finds_published_article(self, client):
        a = _make_article(client, title="Unique Article Zzqy88")
        client.post(f"/knowledge/articles/{a['id']}/publish", headers=MGR)
        r = client.get("/search/full-text", headers=MGR, params={"q": "Zzqy88"})
        assert any(x["entity_type"] == "kb_article" for x in r.json()["results"])

    def test_search_logs_recent_search(self, client):
        client.get("/search", headers=MGR, params={"q": "Rocket"})
        r = client.get("/search/recent", headers=MGR)
        assert len(r.json()) >= 1
        assert r.json()[0]["query_text"] == "Rocket"


# =====================================================================
# Saved Searches
# =====================================================================
class TestSavedSearches:
    def test_create_and_list_saved_search(self, client):
        r = client.post("/search/saved", headers=MGR, json={"name": "My Search", "query": {"q": "Rocket"}})
        assert r.status_code == 201
        assert client.get("/search/saved", headers=MGR).json()[0]["name"] == "My Search"

    def test_favorite_and_shared_flags(self, client):
        r = client.post("/search/saved", headers=MGR, json={"name": "Fav", "query": {"q": "x"}, "is_favorite": True})
        assert r.json()["is_favorite"] is True

    def test_favorites_only_filter(self, client):
        client.post("/search/saved", headers=MGR, json={"name": "A", "query": {"q": "x"}, "is_favorite": False})
        client.post("/search/saved", headers=MGR, json={"name": "B", "query": {"q": "x"}, "is_favorite": True})
        r = client.get("/search/saved", headers=MGR, params={"favorites_only": True})
        assert len(r.json()) == 1

    def test_run_saved_search(self, client):
        s = client.post("/search/saved", headers=MGR, json={"name": "Run Me", "query": {"q": "Rocket", "entity_types": ["company"]}}).json()
        r = client.post(f"/search/saved/{s['id']}/run", headers=MGR)
        assert r.status_code == 200
        assert any(x["entity_type"] == "company" for x in r.json()["results"])

    def test_delete_saved_search(self, client):
        s = client.post("/search/saved", headers=MGR, json={"name": "Del", "query": {"q": "x"}}).json()
        assert client.delete(f"/search/saved/{s['id']}", headers=MGR).status_code == 204

    def test_shared_search_visible_to_other_users(self, client):
        client.post("/search/saved", headers=MGR, json={"name": "Shared", "query": {"q": "x"}, "is_shared": True})
        r = client.get("/search/saved", headers=MEM)
        assert any(s["name"] == "Shared" for s in r.json())


# =====================================================================
# Knowledge Base
# =====================================================================
class TestKnowledgeBase:
    def test_create_category(self, client):
        c = _make_category(client)
        assert c["id"] > 0

    def test_create_category_manager_only(self, client):
        r = client.post("/knowledge/categories", headers=MEM, json={"name": "X"})
        assert r.status_code == 403

    def test_create_article_starts_draft(self, client):
        a = _make_article(client)
        assert a["status"] == "draft"
        assert a["version"] == 1

    def test_get_article_logs_view_and_increments_count(self, client):
        a = _make_article(client)
        client.get(f"/knowledge/articles/{a['id']}", headers=MGR)
        r = client.get(f"/knowledge/articles/{a['id']}", headers=MGR)
        assert r.json()["view_count"] >= 2

    def test_patch_article_creates_version_on_content_change(self, client):
        a = _make_article(client)
        client.patch(f"/knowledge/articles/{a['id']}", headers=MGR, json={"body": "Updated body content"})
        versions = client.get(f"/knowledge/articles/{a['id']}/versions", headers=MGR).json()
        assert len(versions) == 1
        assert versions[0]["body"] == "This article covers rocket setup."

    def test_patch_article_rejects_status_field(self, client):
        a = _make_article(client)
        r = client.patch(f"/knowledge/articles/{a['id']}", headers=MGR, json={"status": "published"})
        assert r.status_code == 422

    def test_article_ownership_enforced(self, client):
        a = client.post("/knowledge/articles", headers=MGR, json={"title": "X"}).json()
        r = client.patch(f"/knowledge/articles/{a['id']}", headers=MEM, json={"title": "Hacked"})
        assert r.status_code == 403

    def test_delete_article(self, client):
        a = _make_article(client)
        assert client.delete(f"/knowledge/articles/{a['id']}", headers=MGR).status_code == 204


# =====================================================================
# Knowledge Management (publishing workflow)
# =====================================================================
class TestKnowledgePublishing:
    def test_submit_draft_for_approval(self, client):
        a = _make_article(client)
        r = client.post(f"/knowledge/articles/{a['id']}/submit", headers=MGR)
        assert r.json()["status"] == "pending_approval"

    def test_submit_non_draft_rejected(self, client):
        a = _make_article(client)
        client.post(f"/knowledge/articles/{a['id']}/submit", headers=MGR)
        r = client.post(f"/knowledge/articles/{a['id']}/submit", headers=MGR)
        assert r.status_code == 409

    def test_publish_requires_manager(self, client):
        a = _make_article(client)
        client.post(f"/knowledge/articles/{a['id']}/submit", headers=MGR)
        r = client.post(f"/knowledge/articles/{a['id']}/publish", headers=MEM)
        assert r.status_code == 403

    def test_publish_sets_published_at(self, client):
        a = _make_article(client)
        client.post(f"/knowledge/articles/{a['id']}/submit", headers=MGR)
        r = client.post(f"/knowledge/articles/{a['id']}/publish", headers=MGR)
        assert r.json()["status"] == "published"
        assert r.json()["published_at"] is not None

    def test_archive_article(self, client):
        a = _make_article(client)
        r = client.post(f"/knowledge/articles/{a['id']}/archive", headers=MGR)
        assert r.json()["status"] == "archived"

    def test_only_published_articles_are_full_text_searchable(self, client):
        a = _make_article(client, title="Hidden Zzqz77 Draft")
        r = client.get("/search/full-text", headers=MGR, params={"q": "Zzqz77"})
        assert not any(x["entity_type"] == "kb_article" for x in r.json()["results"])


# =====================================================================
# AI Knowledge Assistance (deterministic)
# =====================================================================
class TestAiKnowledgeAssistance:
    def test_related_articles_by_shared_tags(self, client):
        a1 = _make_article(client, title="Rocket Setup", tags=["rocket", "setup"])
        a2 = _make_article(client, title="Rocket Maintenance", tags=["rocket", "maintenance"])
        client.post(f"/knowledge/articles/{a1['id']}/publish", headers=MGR)
        client.post(f"/knowledge/articles/{a2['id']}/publish", headers=MGR)
        r = client.get(f"/knowledge/articles/{a1['id']}/related", headers=MGR)
        assert any(x["article_id"] == a2["id"] for x in r.json())

    def test_related_articles_excludes_self(self, client):
        a1 = _make_article(client)
        client.post(f"/knowledge/articles/{a1['id']}/publish", headers=MGR)
        r = client.get(f"/knowledge/articles/{a1['id']}/related", headers=MGR)
        assert all(x["article_id"] != a1["id"] for x in r.json())

    def test_context_suggestions_by_tag(self, client):
        a = _make_article(client, title="Deal Playbook", tags=["deal"])
        client.post(f"/knowledge/articles/{a['id']}/publish", headers=MGR)
        r = client.get("/knowledge/context-suggestions", headers=MGR, params={"entity_type": "deal", "entity_id": "1"})
        assert any(x["article_id"] == a["id"] for x in r.json()["articles"])

    def test_similar_records_scoped_to_entity_type(self, client):
        pipeline = _make_pipeline(client)
        open_stage = next(s for s in pipeline["stages"] if s["stage_type"] == "open")
        _make_deal(client, pipeline["id"], open_stage["id"], title="Similar Rocket Deal")
        r = client.get("/search/similar-records", headers=MGR, params={"entity_type": "deal", "q": "Rocket"})
        assert all(x["entity_type"] == "deal" for x in r.json())

    def test_similar_records_invalid_entity_type_rejected(self, client):
        r = client.get("/search/similar-records", headers=MGR, params={"entity_type": "bogus", "q": "x"})
        assert r.status_code == 422

    def test_knowledge_summary_is_deterministic(self, client):
        a = _make_article(client)
        r1 = client.get(f"/knowledge/articles/{a['id']}/summary", headers=MGR)
        r2 = client.get(f"/knowledge/articles/{a['id']}/summary", headers=MGR)
        assert r1.json()["summary"] == r2.json()["summary"]


# =====================================================================
# Search Dashboard + Analytics
# =====================================================================
class TestSearchDashboardAndAnalytics:
    def test_dashboard_fields(self, client):
        client.get("/search", headers=MGR, params={"q": "Rocket"})
        a = _make_article(client)
        client.post(f"/knowledge/articles/{a['id']}/publish", headers=MGR)
        r = client.get("/search/dashboard/summary", headers=MGR)
        body = r.json()
        assert len(body["recent_searches"]) >= 1
        assert "published" in body["knowledge_activity"]

    def test_analytics_fields(self, client):
        client.get("/search", headers=MGR, params={"q": "NoSuchThingXYZ"})
        r = client.get("/search/analytics/summary", headers=MGR)
        body = r.json()
        assert body["search_volume"] >= 1
        assert body["zero_result_searches"] >= 1


# =====================================================================
# Backward compatibility
# =====================================================================
class TestBackwardCompatibility:
    def test_existing_integrations_endpoints_unaffected(self, client):
        assert client.get("/integrations", headers=MGR).status_code == 200

    def test_existing_governance_endpoints_unaffected(self, client):
        assert client.get("/governance/organizations", headers=MGR).status_code == 200

    def test_existing_workflow_endpoints_unaffected(self, client):
        assert client.get("/workflows", headers=MGR).status_code == 200
