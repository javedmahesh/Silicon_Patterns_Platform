"""Phase 3 — New Semiconductor Project Intelligence.

Precise, content-driven detection of concrete company-level semiconductor projects
via the EXISTING News Collection Engine + Opportunities architecture. Covers every
required project event type, India geography, startup/India priority, generic-
commentary rejection, multi-signal preservation, dedup (A/B/C/D), canonical company
resolution, provenance survival, role-family relevance, and the Opportunities API
(filter/sort/geography/priority) — no Apify, no external services.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from integration.news.engine import NewsIntelligenceEngine
from integration.news.extraction import extract_opportunities
from integration.news.project_intel import (
    PROJECT_ROLE_FAMILIES,
    extract_project_events,
    project_priority,
)
from integration.normalizer import name_key
from master_db.local import make_session_factory
from master_db.models import Base, Company, Opportunity


def _article(title, body="", company="Acme Semiconductor", domain="acme.com", url=None, published="2026-07-01"):
    return {"title": title, "body": body or title, "company_name": company, "company_domain": domain,
            "url": url or f"https://example.com/{abs(hash(title)) % 10**8}", "published_at": published,
            "publisher": "EE Times", "source_type": "rss"}


@pytest.fixture()
def session():
    Session = make_session_factory(":memory:")
    with Session() as s:
        s.add_all([
            Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme Semiconductor",
                    name_key=name_key("Acme Semiconductor"), company_tier="STARTUP",
                    prospect_type="PRODUCT_COMPANY", compliance_flag="APPROVED", validation_status="VALID"),
            Company(company_domain="globex.com", canonical_company_id="GLOBEX", company_name="Globex",
                    name_key=name_key("Globex"), company_tier="INCUMBENT",
                    prospect_type="PRODUCT_COMPANY", compliance_flag="APPROVED", validation_status="VALID"),
        ])
        s.commit()
        yield s


# ---------------------------------------------------- event-type detection (all 11)
@pytest.mark.parametrize("title,expected", [
    ("Acme Semiconductor is developing a new AI accelerator chip.", "NEW_CHIP_PROGRAM"),
    ("Acme Semiconductor is designing a custom ASIC for datacenters.", "NEW_ASIC_SOC"),
    ("Acme Semiconductor taped out its new 3nm processor.", "TAPEOUT"),
    ("Acme Semiconductor secured a design win at a major OEM for its chip.", "DESIGN_WIN"),
    ("Acme Semiconductor opened a semiconductor design center in Bengaluru.", "DESIGN_CENTER"),
    ("Acme Semiconductor opened a new R&D center in Hyderabad.", "RND_CENTER"),
    ("Acme Semiconductor will build a new wafer fab in Gujarat.", "FAB_NEW"),
    ("Acme Semiconductor is expanding its semiconductor fab in Oregon.", "FAB_EXPANSION"),
    ("Acme Semiconductor opened an OSAT assembly and test facility.", "OSAT_ATMP"),
    ("Acme Semiconductor is expanding chip manufacturing capacity in Noida.", "CAPACITY_EXPANSION"),
    ("Acme Semiconductor expands its semiconductor manufacturing facility in Pune.", "FACILITY_EXPANSION"),
])
def test_each_project_type_detected(title, expected):
    evs = {e.event_type for e in extract_project_events(title, "")}
    assert expected in evs, (title, evs)


# ------------------------------------------------------------ precision (rejection)
@pytest.mark.parametrize("title", [
    "The semiconductor market is expanding.",
    "AI chips are expected to grow rapidly.",
    "India could become a semiconductor design center.",
    "Company X believes semiconductor demand will increase.",
    "Analysts forecast strong foundry capacity growth.",
    "The chip industry may see new fabs in the future.",
])
def test_generic_commentary_rejected(title):
    assert extract_project_events(title, "") == []


def test_weak_keyword_coincidence_rejected():
    # mentions "fab" and "expand" but as market commentary, no company project
    assert extract_project_events("Global fab capacity is expanding across the industry.", "") == []


# --------------------------------------------------------------------- geography
def test_india_geography_extracted():
    evs = extract_project_events("Acme opened a design center in Bengaluru.", "")
    from integration.news.project_intel import project_geography
    assert project_geography("Acme opened a design center in Bengaluru.") == "Bengaluru, India"
    assert evs and evs[0].event_type == "DESIGN_CENTER"


def test_geography_not_inferred_from_absence():
    from integration.news.project_intel import project_geography
    assert project_geography("Acme opened a design center in Munich, Germany.") == ""


# ---------------------------------------------------------------------- priority
def test_startup_project_high_priority():
    assert project_priority("STARTUP", "FACILITY_EXPANSION", "") == "high"   # startup lifts even soft types


def test_india_project_high_priority():
    assert project_priority("INCUMBENT", "CAPACITY_EXPANSION", "Noida, India") == "high"


def test_high_intent_type_high_priority_regardless_of_size():
    assert project_priority("INCUMBENT", "TAPEOUT", "") == "high"
    assert project_priority("INCUMBENT", "DESIGN_CENTER", "") == "high"


def test_soft_expansion_large_company_non_india_is_medium():
    assert project_priority("INCUMBENT", "CAPACITY_EXPANSION", "") == "medium"
    assert project_priority("INCUMBENT", "FACILITY_EXPANSION", "") == "medium"


# ----------------------------------------------------------------- multi-signal
def test_multi_signal_preserves_distinct_events():
    sigs = extract_opportunities(_article(
        "Startup X raises $50M to tape out its AI accelerator and open a Bengaluru design center.",
        "Startup X raised $50 million to tape out its AI accelerator and open a new design center in Bengaluru."))
    types = {s.opportunity_type for s in sigs}
    assert "FUNDING" in types and "TAPEOUT" in types and "DESIGN_CENTER" in types


def test_precise_project_supersedes_generic():
    sigs = extract_opportunities(_article(
        "Acme opens a new semiconductor fab in Arizona.",
        "Acme Semiconductor will build a new wafer fab in Arizona."))
    types = {s.opportunity_type for s in sigs}
    assert "FAB_NEW" in types and "EXPANSION" not in types   # no redundant generic pair


# ------------------------------------------------------------ engine end-to-end
def test_engine_creates_project_opportunity_with_provenance(session):
    m = NewsIntelligenceEngine(session).run(articles=[_article(
        "Acme Semiconductor opened a chip design center in Bengaluru.",
        "Acme Semiconductor opened a new semiconductor design center in Bengaluru to build AI accelerators.")])
    assert m.opportunities_created >= 1
    opp = session.query(Opportunity).filter_by(opportunity_type="DESIGN_CENTER").one()
    assert opp.opportunity_category == "PROJECT_INTEL"
    assert opp.signal_category == "PROJECT"
    assert opp.geography == "Bengaluru, India"
    assert opp.priority_tier == "high"                       # startup company
    assert opp.company_domain == "acme.com"                  # canonical resolution
    assert opp.article_url and opp.source and opp.published_date   # provenance survives
    from master_db.models import OpportunityArticle
    assert session.query(OpportunityArticle).filter_by(opportunity_id=opp.opportunity_id).count() == 1


def test_large_company_project_priority_end_to_end(session):
    NewsIntelligenceEngine(session).run(articles=[_article(
        "Globex expands its semiconductor manufacturing facility in Germany.",
        "Globex is expanding its semiconductor manufacturing facility in Dresden, Germany.",
        company="Globex", domain="globex.com")])
    opp = session.query(Opportunity).filter_by(opportunity_type="FACILITY_EXPANSION").one()
    assert opp.priority_tier == "medium"                     # incumbent, non-India, soft type — kept, deprioritized


# --------------------------------------------------------------------- dedup
def test_same_article_twice_no_duplicate(session):
    eng = NewsIntelligenceEngine(session)
    art = _article("Acme taped out its new RISC-V SoC.", "Acme Semiconductor taped out its new RISC-V SoC.")
    eng.run(articles=[art])
    m2 = eng.ingest_articles([art])                          # exact same article again
    assert m2.opportunities_created == 0


def test_two_publications_same_event_dedup(session):
    eng = NewsIntelligenceEngine(session)
    eng.run(articles=[_article("Acme taped out its 3nm AI accelerator.",
                               "Acme Semiconductor taped out its 3nm AI accelerator.",
                               url="https://a.example/1")])
    m2 = eng.ingest_articles([_article("Acme Semiconductor tapes out 3nm AI accelerator",
                                       "Acme Semiconductor has taped out its 3nm AI accelerator.",
                                       url="https://b.example/2")])
    assert m2.opportunities_created == 0 and m2.duplicates_merged >= 1   # collapsed real-world event


def test_same_company_different_projects_distinct(session):
    eng = NewsIntelligenceEngine(session)
    eng.run(articles=[_article("Acme opened a design center in Bengaluru.",
                               "Acme Semiconductor opened a design center in Bengaluru.", url="https://a/1")])
    eng.ingest_articles([_article("Acme taped out its new SoC.",
                                  "Acme Semiconductor taped out its new SoC.", url="https://a/2")])
    types = {o.opportunity_type for o in session.query(Opportunity).all()}
    assert "DESIGN_CENTER" in types and "TAPEOUT" in types   # two genuinely different projects kept


def test_ambiguous_company_not_duplicated(session):
    # article with no resolvable company + create_stub off -> rejected, no bogus company
    m = NewsIntelligenceEngine(session, create_stub=False).run(articles=[_article(
        "A new design center opened in Bengaluru.", "A new semiconductor design center opened in Bengaluru.",
        company="", domain="")])
    assert m.opportunities_created == 0
    assert session.query(Company).count() == 2               # no new company minted


# --------------------------------------------------------- role families (no Apify)
def test_role_families_surfaced_for_project_types():
    assert "CTO" in PROJECT_ROLE_FAMILIES["TAPEOUT"]
    assert "Manufacturing Leadership" in PROJECT_ROLE_FAMILIES["FAB_NEW"]
    assert "Procurement/Sourcing" in PROJECT_ROLE_FAMILIES["DESIGN_CENTER"]


# ------------------------------------------------------------------------ API
@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'proj.db').as_posix()}", log_json=False,
                              dev_auth_bypass=True, microsoft_tenant_id="", microsoft_client_id=""))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme Semiconductor",
                          name_key=name_key("Acme Semiconductor"), company_tier="STARTUP",
                          prospect_type="PRODUCT_COMPANY", compliance_flag="APPROVED", validation_status="VALID"))
            s.flush()
            NewsIntelligenceEngine(s).run(articles=[
                _article("Acme opened a chip design center in Bengaluru.",
                         "Acme Semiconductor opened a design center in Bengaluru.", url="https://a/1", published="2026-07-05"),
                _article("Acme taped out its new AI accelerator.",
                         "Acme Semiconductor taped out its new AI accelerator.", url="https://a/2", published="2026-07-10"),
            ])
            s.commit()
        yield c


def test_api_filter_by_project_type(client):
    body = client.get("/opportunities", params={"opportunity_type": "TAPEOUT"}).json()
    assert body["total"] == 1 and body["items"][0]["opportunity_type"] == "TAPEOUT"


def test_api_filter_by_project_signal_category(client):
    body = client.get("/opportunities", params={"signal_category": "PROJECT"}).json()
    assert body["total"] == 2
    assert all(i["opportunity_type"] in ("DESIGN_CENTER", "TAPEOUT") for i in body["items"])


def test_api_project_surfaces_geography_priority(client):
    dc = next(i for i in client.get("/opportunities").json()["items"] if i["opportunity_type"] == "DESIGN_CENTER")
    assert dc["geography"] == "Bengaluru, India" and dc["priority_tier"] == "high"


def test_api_newest_first_sort(client):
    items = client.get("/opportunities", params={"sort": "newest", "signal_category": "PROJECT"}).json()["items"]
    assert [i["published_date"] for i in items] == sorted((i["published_date"] for i in items), reverse=True)


def test_api_detail_exposes_role_families_and_evidence(client):
    tid = next(i["opportunity_id"] for i in client.get("/opportunities").json()["items"]
               if i["opportunity_type"] == "TAPEOUT")
    d = client.get(f"/opportunities/{tid}").json()
    assert "CTO" in d["role_families"]                       # surfaced without running Apify
    assert "Project evidence" in d["ai_reasoning"]           # provenance / why-it-exists
