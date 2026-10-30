"""News Intelligence — adapters, dedup, multi-signal extraction, engine, API, review.

Covers the Phase requirements: multi-source ingestion, intelligent deduplication,
rich opportunity intelligence, multi-signal extraction, relationships + timeline,
opportunity detail, manual review (history without overwriting AI outputs), and the
data-refresh guarantee (only opportunities/news deleted).
"""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from integration.news import adapters, dedup
from integration.news.engine import (
    NewsIntelligenceEngine,
    enabled_news_sources,
    enrich_new_opportunities,
    refresh_opportunities,
    seed_news_sources,
)
from integration.news.extraction import extract_opportunities, extract_primary_company
from master_db.local import make_session_factory
from master_db.models import (
    Base,
    Company,
    LeadScore,
    NewsSource,
    Opportunity,
    OpportunityArticle,
)
import orchestrator.stages as stages


# ------------------------------------------------------------------ fixtures
@pytest.fixture()
def session():
    Session = make_session_factory(":memory:")
    with Session() as s:
        s.add_all([
            Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                    name_key="acme", company_tier="STARTUP", prospect_type="PRODUCT_COMPANY",
                    compliance_flag="APPROVED", validation_status="VALID"),
            Company(company_domain="globex.com", canonical_company_id="GLOBEX", company_name="Globex",
                    name_key="globex", company_tier="INCUMBENT", prospect_type="PRODUCT_COMPANY",
                    compliance_flag="APPROVED", validation_status="VALID"),
        ])
        s.commit()
        yield s


def _article(**kw):
    base = {
        "title": "Acme Semiconductor raises $50 million Series B",
        "body": "Acme Semiconductor Inc raised $50 million to accelerate its RISC-V roadmap.",
        "company_name": "Acme", "company_domain": "acme.com",
        "url": "https://eetimes.example/acme-series-b", "published_at": "2026-07-01",
        "publisher": "EE Times", "source_type": "rss",
    }
    base.update(kw)
    return base


RSS_XML = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>EE Times</title>
<item><title>Acme raises $50M Series B</title><link>https://ee.example/acme?utm_source=rss</link>
<description>Acme raised $50 million to accelerate its RISC-V roadmap.</description>
<pubDate>Wed, 01 Jul 2026 10:00:00 +0000</pubDate></item>
<item><title>Globex unveils new 3nm GPU</title><link>https://ee.example/globex-gpu</link>
<description>Globex launches a new GPU.</description>
<pubDate>Wed, 01 Jul 2026 12:00:00 +0000</pubDate></item>
</channel></rss>"""

ATOM_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Google Alert - semiconductor</title>
<entry><title>Acme acquires RivalChip</title>
<link href="https://www.google.com/url?rct=j&amp;url=https://news.example/acme-acquires&amp;usg=x"/>
<summary>Acme to acquire RivalChip.</summary><published>2026-07-02T09:00:00Z</published></entry>
</feed>"""


# ------------------------------------------------------------------ adapters
def test_rss_adapter_parses_items():
    src = NewsSource(id=1, name="EE Times", adapter_type="rss", publisher="EE Times")
    arts = adapters.fetch_articles(src, raw=RSS_XML)
    assert len(arts) == 2
    assert arts[0]["title"] == "Acme raises $50M Series B"
    assert arts[0]["url"].startswith("https://ee.example/acme")
    assert arts[0]["adapter_type"] == "rss" and arts[0]["publisher"] == "EE Times"
    assert arts[0]["published_at"]  # pubDate carried through


def test_google_alerts_adapter_unwraps_redirect():
    src = NewsSource(id=2, name="Alert", adapter_type="google_alerts", publisher="Google Alerts")
    arts = adapters.fetch_articles(src, raw=ATOM_XML)
    assert len(arts) == 1
    assert arts[0]["url"] == "https://news.example/acme-acquires"   # google redirect unwrapped
    assert arts[0]["source_type"] == "google_alerts"


def test_file_adapter_maps_feed_rows():
    src = NewsSource(id=3, name="Blog feed", adapter_type="file")
    rows = [{"article_title": "Acme launches chip", "article_url": "https://x/y",
             "summary": "New chip.", "company_name": "Acme", "company_domain": "acme.com",
             "opportunity_type": "PRODUCT_LAUNCH", "source": "Blog"}]
    arts = adapters.fetch_articles(src, rows=rows)
    assert arts[0]["title"] == "Acme launches chip"
    assert arts[0]["_feed_row"]["opportunity_type"] == "PRODUCT_LAUNCH"


def test_unknown_adapter_falls_back_to_rss():
    assert isinstance(adapters.get_adapter("nope"), adapters.RssAdapter)


def test_malformed_feed_reports_error_but_returns_empty():
    """A broken feed must be observable (error captured) yet never raise — one bad
    source can't break collection."""
    src = NewsSource(id=9, name="Broken", adapter_type="rss", publisher="Broken")
    errs: list[str] = []
    arts = adapters.fetch_articles(src, raw="<rss><channel><item>unterminated", errors=errs)
    assert arts == []                      # resilient: no crash, no articles
    assert errs and "parse error" in errs[0]   # but the failure is recorded


def test_engine_surfaces_dead_feed_in_source_errors(session, monkeypatch):
    """A live source whose fetch fails is recorded in metrics.source_errors (named),
    while a healthy source in the same run still produces its opportunity."""
    dead = NewsSource(id=20, name="Dead Feed", adapter_type="rss", url="https://dead.example/feed",
                      publisher="Dead", enabled=True)
    good = NewsSource(id=21, name="Good Feed", adapter_type="rss", url="https://good.example/feed",
                      publisher="EE Times", enabled=True)
    session.add_all([dead, good])   # FK: news_articles.source_id references these
    session.commit()

    def fake_fetch(source, *, raw=None, rows=None, incremental=True, errors=None):
        if source.id == 20:
            if errors is not None:
                errors.append("URLError: connection refused")
            return []
        return [_article()]

    monkeypatch.setattr(adapters, "fetch_articles", fake_fetch)
    m = NewsIntelligenceEngine(session).run(sources=[dead, good])
    assert any("Dead Feed" in e for e in m.source_errors)   # named + observable
    assert m.opportunities_created >= 1                      # healthy source unaffected


# ------------------------------------------------------------------ dedup
def test_canonical_url_strips_tracking_and_scheme():
    a = dedup.canonical_url("http://www.Example.com/path/?utm_source=x&id=5#frag")
    b = dedup.canonical_url("https://example.com/path?id=5")
    assert a == b


def test_normalized_title_drops_publisher_suffix():
    assert dedup.normalize_title("Acme raises $50M - EE Times") == "acme raises 50m"


def test_title_similarity_and_same_event():
    assert dedup.title_similarity("Acme raises $50M Series B", "Acme Raises $50 Million Series B") > 0.7
    assert dedup.is_same_event(
        company_domain="acme.com", opportunity_type="FUNDING",
        title="Acme raises $50M Series B", published_at="2026-07-01",
        other_title="Acme raises $50 million Series B", other_published_at="2026-07-02",
        same_company=True)
    # different company never merges
    assert not dedup.is_same_event(
        company_domain="acme.com", opportunity_type="FUNDING", title="x", published_at="2026-07-01",
        other_title="x", other_published_at="2026-07-01", same_company=False)


def test_fingerprint_separates_different_events_same_company():
    fp1 = dedup.entity_fingerprint("acme.com", "FUNDING", ["RISC-V"], "2026-07-01")
    fp2 = dedup.entity_fingerprint("acme.com", "ACQUISITION", ["RivalChip"], "2026-07-01")
    assert fp1 != fp2


# ------------------------------------------------------------------ extraction
def test_multi_signal_extraction_from_one_article():
    sigs = extract_opportunities(_article(
        title="Acme acquires RivalChip, expands India R&D and is hiring RTL engineers",
        body="Acme Inc will acquire RivalChip for $1.2 billion, open a new R&D center in India, "
             "and is hiring 200 verification engineers. CEO Jane Doe cited the RISC-V roadmap."))
    types = {s.opportunity_type for s in sigs}
    # "open a new R&D center" is now classified as the more precise RND_CENTER project
    # event, which SUPERSEDES the generic EXPANSION for the same event (no redundant pair).
    assert {"ACQUISITION", "RND_CENTER", "HIRING"} <= types
    assert "EXPANSION" not in types
    acq = next(s for s in sigs if s.opportunity_type == "ACQUISITION")
    assert "RISC-V" in acq.technologies and "India" in acq.countries
    assert "Jane Doe" in acq.people
    assert acq.confidence > 0 and set(acq.confidence_breakdown) >= {
        "title_signal", "entity_richness", "specificity", "source_credibility"}
    assert acq.executive_summary and acq.why_this_matters and acq.business_impact and acq.ai_reasoning
    assert acq.source_credibility > 0


def test_extraction_honors_feed_type():
    sigs = extract_opportunities({"title": "Acme quarterly update", "body": "routine update",
                                  "company_name": "Acme", "_feed_row": {"opportunity_type": "PRODUCT_LAUNCH"}})
    assert any(s.opportunity_type == "PRODUCT_LAUNCH" for s in sigs)


# ------------------------------------------------------------------ engine
def test_engine_creates_rich_opportunity(session):
    m = NewsIntelligenceEngine(session).run(articles=[_article()])
    assert m.opportunities_created == 1 and m.rejected == 0
    opp = session.query(Opportunity).filter_by(opportunity_type="FUNDING").one()
    assert opp.ai_summary and opp.why_this_matters and opp.lifecycle_status == "NEW"
    assert opp.related_group_id and opp.entity_fingerprint
    assert session.query(OpportunityArticle).filter_by(opportunity_id=opp.opportunity_id).count() == 1


def test_engine_merges_same_event_across_sources(session):
    eng = NewsIntelligenceEngine(session)
    eng.run(articles=[_article()])
    # a second outlet reports the SAME funding round -> no new opp, extra source attached
    m2 = eng.ingest_articles([_article(
        url="https://anandtech.example/acme-50m", publisher="AnandTech",
        title="Acme raises $50 million Series B round")])
    assert m2.opportunities_created == 0 and m2.duplicates_merged == 1 and m2.sources_attached == 1
    opp = session.query(Opportunity).filter_by(opportunity_type="FUNDING").one()
    assert session.query(OpportunityArticle).filter_by(opportunity_id=opp.opportunity_id).count() == 2


def test_engine_keeps_different_events_separate(session):
    eng = NewsIntelligenceEngine(session)
    eng.run(articles=[_article()])  # FUNDING
    eng.ingest_articles([_article(title="Acme acquires RivalChip", url="https://x/acq",
                                  body="Acme to acquire RivalChip for $1B.")])
    types = {o.opportunity_type for o in session.query(Opportunity).all()}
    assert "FUNDING" in types and "ACQUISITION" in types


def test_engine_rejects_unresolved_company(session):
    m = NewsIntelligenceEngine(session, create_stub=False).run(
        articles=[_article(company_name="Nonexistent Co", company_domain="", url="https://x/z")])
    assert m.rejected == 1 and m.opportunities_created == 0


def test_refresh_deletes_only_opportunities(session):
    session.add(LeadScore(company_domain="acme.com", lead_score=80.0, grade="A", model_version="t"))
    session.commit()
    NewsIntelligenceEngine(session).run(articles=[_article()])
    assert session.query(Opportunity).count() >= 1
    refresh_opportunities(session, articles=[_article(
        title="Acme acquires RivalChip", url="https://x/acq2", body="Acme to acquire RivalChip.")])
    # companies + lead scores preserved; opportunities regenerated
    assert session.query(Company).count() == 2
    assert session.query(LeadScore).count() == 1
    assert session.query(Opportunity).filter_by(opportunity_type="ACQUISITION").count() == 1


def test_refresh_guard_refuses_empty_wipe(session):
    NewsIntelligenceEngine(session).run(articles=[_article()])
    with pytest.raises(ValueError):
        refresh_opportunities(session)  # nothing to regenerate from -> must not wipe


def test_enrich_backfills_plain_opportunity_in_place(session):
    session.add(Opportunity(
        opportunity_id="OPP-PLAIN", company_domain="acme.com", company_name="Acme",
        opportunity_type="FUNDING", article_title="Acme raises $50M Series B for RISC-V",
        summary="Acme raised capital.", effective_opportunity_score=80, published_date="2026-07-01"))
    session.commit()
    before = session.query(Opportunity).count()
    n = enrich_new_opportunities(session)
    assert n == 1 and session.query(Opportunity).count() == before  # count-preserving
    opp = session.get(Opportunity, "OPP-PLAIN")
    assert opp.ai_summary and opp.why_this_matters and opp.lifecycle_status == "NEW"
    assert opp.opportunity_type == "FUNDING"  # type untouched


# ------------------------------------------------------------------ API
@pytest.fixture()
def client(tmp_path):
    settings = Settings(database_url=f"sqlite:///{(tmp_path / 'news.db').as_posix()}",
                        log_json=False, microsoft_tenant_id="", microsoft_client_id="")
    app = create_app(settings)
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                          name_key="acme", validation_status="VALID"))
            s.flush()
            NewsIntelligenceEngine(s).run(articles=[_article(
                title="Acme acquires RivalChip, expands India R&D and hires RTL engineers",
                body="Acme Inc will acquire RivalChip for $1.2 billion, open an India R&D center, "
                     "and is hiring verification engineers. RISC-V roadmap.")])
            s.commit()
        yield c


def _first_id(client, opp_type="ACQUISITION"):
    items = client.get("/opportunities").json()["items"]
    return next(i["opportunity_id"] for i in items if i["opportunity_type"] == opp_type)


def test_api_list_exposes_rich_fields(client):
    items = client.get("/opportunities").json()["items"]
    assert len(items) >= 3  # multi-signal
    acq = next(i for i in items if i["opportunity_type"] == "ACQUISITION")
    assert acq["lifecycle_status"] == "NEW" and acq["technologies"]


def test_api_detail_has_full_intelligence(client):
    oid = _first_id(client)
    d = client.get(f"/opportunities/{oid}").json()
    assert d["why_this_matters"] and d["business_impact"] and d["ai_reasoning"]
    assert d["confidence_breakdown"] and d["people"] is not None
    assert len(d["sources"]) == 1
    assert len(d["related"]) >= 2       # sibling multi-signal opportunities
    assert len(d["timeline"]) >= 3      # company event timeline
    assert any(t["is_current"] for t in d["timeline"])


def test_api_review_not_relevant_records_history_and_preserves_ai(client):
    oid = _first_id(client)
    before = client.get(f"/opportunities/{oid}").json()
    r = client.post(f"/opportunities/{oid}/review", json={"action": "not_relevant", "detail": "dup"})
    assert r.status_code == 200
    d = r.json()
    assert d["lifecycle_status"] == "ARCHIVED" and d["is_relevant"] is False
    assert len(d["reviews"]) == 1 and d["reviews"][0]["action"] == "not_relevant"
    # AI outputs untouched
    assert d["ai_summary"] == before["ai_summary"] and d["why_this_matters"] == before["why_this_matters"]


def test_api_hide_archived_filter(client):
    oid = _first_id(client)
    total_before = client.get("/opportunities").json()["total"]
    client.post(f"/opportunities/{oid}/review", json={"action": "not_relevant"})
    shown = client.get("/opportunities", params={"hide_archived": "true"}).json()["total"]
    assert shown == total_before - 1


def test_api_change_type_and_restore(client):
    oid = _first_id(client)
    client.post(f"/opportunities/{oid}/review", json={"action": "change_type", "new_type": "PARTNERSHIP"})
    assert client.get(f"/opportunities/{oid}").json()["opportunity_type"] == "PARTNERSHIP"
    client.post(f"/opportunities/{oid}/review", json={"action": "not_relevant"})
    d = client.post(f"/opportunities/{oid}/review", json={"action": "restore"}).json()
    assert d["is_relevant"] is True and d["lifecycle_status"] == "ACTIVE"


def test_api_merge_reparents_sources(client):
    items = client.get("/opportunities").json()["items"]
    acq = next(i["opportunity_id"] for i in items if i["opportunity_type"] == "ACQUISITION")
    # the seed's "India R&D center" is now the precise RND_CENTER project event
    other = next(i["opportunity_id"] for i in items if i["opportunity_type"] == "RND_CENTER")
    d = client.post(f"/opportunities/{acq}/review",
                    json={"action": "merge", "target_opportunity_id": other}).json()
    assert d["merged_into"] == other and d["lifecycle_status"] == "ARCHIVED"


def test_api_change_type_requires_new_type(client):
    oid = _first_id(client)
    assert client.post(f"/opportunities/{oid}/review", json={"action": "change_type"}).status_code == 422


def test_api_lifecycle_endpoint(client):
    oid = _first_id(client)
    d = client.post(f"/opportunities/{oid}/lifecycle", params={"lifecycle_status": "MONITORING"}).json()
    assert d["lifecycle_status"] == "MONITORING"
    assert client.post(f"/opportunities/{oid}/lifecycle",
                       params={"lifecycle_status": "BOGUS"}).status_code == 422


def test_api_detail_404(client):
    assert client.get("/opportunities/NOPE").status_code == 404


def test_api_news_sources_endpoint(client):
    assert client.get("/opportunities/news-sources").json() == []


def test_list_opportunities_sort_newest_oldest(session):
    from backend import repositories as repo
    session.add_all([
        Opportunity(opportunity_id="OPP-OLD", company_domain="acme.com", opportunity_type="FUNDING",
                    published_date="2026-01-05", effective_opportunity_score=90),
        Opportunity(opportunity_id="OPP-MID", company_domain="acme.com", opportunity_type="FUNDING",
                    published_date="2026-06-15", effective_opportunity_score=50),
        Opportunity(opportunity_id="OPP-NEW", company_domain="acme.com", opportunity_type="FUNDING",
                    published_date="2026-07-20", effective_opportunity_score=10),
    ])
    session.commit()
    newest, _ = repo.list_opportunities(session, sort="newest")
    assert [o.opportunity_id for o in newest] == ["OPP-NEW", "OPP-MID", "OPP-OLD"]
    oldest, _ = repo.list_opportunities(session, sort="oldest")
    assert [o.opportunity_id for o in oldest] == ["OPP-OLD", "OPP-MID", "OPP-NEW"]
    # default is still relevance (score), unchanged for existing callers
    score, _ = repo.list_opportunities(session)
    assert [o.opportunity_id for o in score] == ["OPP-OLD", "OPP-MID", "OPP-NEW"]  # 90,50,10


def test_engine_normalizes_published_date_to_iso(session):
    NewsIntelligenceEngine(session).run(articles=[_article(
        url="https://ee/x", published_at="Wed, 01 Jul 2026 10:00:00 +0000")])
    opp = session.query(Opportunity).filter_by(opportunity_type="FUNDING").first()
    assert opp.published_date == "2026-07-01"  # RFC-822 -> ISO, so newest/oldest sort works


# ---------------------------------------------- live source configuration
def test_primary_company_from_headline():
    assert extract_primary_company("NVIDIA Launches New Blackwell GPU", []) == "NVIDIA"
    assert extract_primary_company("Acme Semiconductor Raises $50M Series B", []) == "Acme Semiconductor"
    assert extract_primary_company("Some headline", ["Globex Corp"]) == "Globex Corp"  # org wins


def test_seed_news_sources_idempotent(session):
    r1 = seed_news_sources(session)
    session.commit()
    assert r1["created"] > 0 and r1["created"] == r1["total"]
    total = session.query(NewsSource).count()
    # a live analyst edit must survive re-seeding
    ee = session.query(NewsSource).filter_by(name="EE Times").one()
    ee.enabled = False
    session.commit()
    r2 = seed_news_sources(session)
    session.commit()
    assert r2["created"] == 0 and session.query(NewsSource).count() == total  # no dupes
    assert session.query(NewsSource).filter_by(name="EE Times").one().enabled is False  # edit kept


def test_enabled_news_sources_filters_disabled_and_blank(session):
    session.add_all([
        NewsSource(name="Live", adapter_type="rss", url="https://x/feed", enabled=True),
        NewsSource(name="Off", adapter_type="rss", url="https://y/feed", enabled=False),
        NewsSource(name="NoUrl", adapter_type="google_alerts", url="", enabled=True),
    ])
    session.commit()
    names = {s.name for s in enabled_news_sources(session)}
    assert names == {"Live"}


def test_news_stage_noop_without_sources(session):
    m = stages.news_ingest(session)
    assert m.rows_upserted == 0 and "no enabled news sources" in m.notes
    assert session.query(Opportunity).count() == 0


def test_news_stage_collects_from_source_offline(session, monkeypatch):
    monkeypatch.setattr(adapters.RssAdapter, "_download", lambda self, url, **kw: RSS_XML)
    session.add(NewsSource(name="EE", adapter_type="rss", url="https://ee/feed",
                           publisher="EE Times", credibility=75, enabled=True))
    session.commit()
    m = stages.news_ingest(session)
    assert m.rows_upserted >= 1 and m.status == "success"
    # RSS items resolve to the seeded acme.com / globex.com via headline company extraction
    domains = {o.company_domain for o in session.query(Opportunity).all()}
    assert "acme.com" in domains
    assert session.query(NewsSource).filter_by(name="EE").one().last_collected_at is not None


def test_news_incremental_second_run_no_duplicates(session, monkeypatch):
    monkeypatch.setattr(adapters.RssAdapter, "_download", lambda self, url, **kw: RSS_XML)
    session.add(NewsSource(name="EE", adapter_type="rss", url="https://ee/feed", enabled=True))
    session.commit()
    stages.news_ingest(session)
    first = session.query(Opportunity).count()
    m2 = stages.news_ingest(session)          # published dates now <= last_collected_at
    assert m2.rows_in == 0                     # incremental: nothing new collected
    assert session.query(Opportunity).count() == first  # no duplicates


def test_incremental_passes_if_modified_since(session, monkeypatch):
    from datetime import datetime, timezone
    captured = {}
    monkeypatch.setattr(adapters.RssAdapter, "_download",
                        lambda self, url, **kw: captured.update(kw) or "")
    src = NewsSource(name="EE", adapter_type="rss", url="https://ee/feed", enabled=True,
                     last_collected_at=datetime(2026, 7, 1, tzinfo=timezone.utc))
    adapters.fetch_articles(src, incremental=True)
    assert captured.get("if_modified_since") == src.last_collected_at


def test_http_date_format():
    from datetime import datetime, timezone
    hdr = adapters._http_date(datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc))
    assert "01 Jul 2026" in hdr and hdr.endswith("GMT")


def test_download_returns_empty_on_304(monkeypatch):
    from urllib.error import HTTPError
    def _raise_304(*a, **k):
        raise HTTPError("https://x/feed", 304, "Not Modified", {}, None)
    monkeypatch.setattr(adapters, "urlopen", _raise_304)
    assert adapters.RssAdapter()._download("https://x/feed") == ""


def test_pipeline_includes_news_stage():
    # Scheduler + Standard Run run the full PIPELINE_ORDER, so 'news' is automatically included.
    assert "news" in stages.PIPELINE_ORDER
    assert stages.PIPELINE_ORDER.index("news") == stages.PIPELINE_ORDER.index("blog") + 1
    assert stages.STAGES["news"].engine is None  # internal engine, no external subprocess


def test_orchestrator_runs_news_stage(session, monkeypatch):
    from orchestrator.orchestrator import Orchestrator
    monkeypatch.setattr(adapters.RssAdapter, "_download", lambda self, url, **kw: RSS_XML)
    session.add(NewsSource(name="EE", adapter_type="rss", url="https://ee/feed", enabled=True))
    session.commit()
    results = Orchestrator(session).run_pipeline(components=["news"])
    assert [r.component for r in results] == ["news"]
    assert results[0].status == "success" and results[0].created >= 1


def test_api_create_toggle_seed_news_sources(client):
    created = client.post("/opportunities/news-sources", json={
        "name": "My RSS", "adapter_type": "rss", "url": "https://ex/feed", "credibility": 60}).json()
    assert created["name"] == "My RSS" and created["enabled"] is True
    # duplicate name -> 409
    assert client.post("/opportunities/news-sources", json={"name": "My RSS"}).status_code == 409
    # bad adapter -> 422
    assert client.post("/opportunities/news-sources",
                       json={"name": "Bad", "adapter_type": "carrier_pigeon"}).status_code == 422
    # toggle off
    patched = client.patch(f"/opportunities/news-sources/{created['id']}", json={"enabled": False}).json()
    assert patched["enabled"] is False
    # seed the curated feeds
    seeded = client.post("/opportunities/news-sources/seed").json()
    assert seeded["created"] >= 1
    names = [s["name"] for s in client.get("/opportunities/news-sources").json()]
    assert "EE Times" in names and "My RSS" in names
