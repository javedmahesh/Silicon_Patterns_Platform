"""Company-news ingestor (Change_03) — people moves / leadership changes →
opportunities, news-type normalization, the company_news_only filter, and the
synergy that feeds director+ moves into the person-level leadership_signals.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.config import Settings
from backend.main import create_app
from integration.ingestors.company_news import CompanyNewsIngestor, normalize_news_type
from leadership_signals.derive import from_blog_events
from master_db.local import make_session_factory
from master_db.models import Base, Company, Opportunity

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture()
def session():
    with make_session_factory(":memory:")() as s:
        s.add_all([
            Company(company_domain="groq.com", canonical_company_id="GROQ", company_name="Groq",
                    name_key="groq", prospect_type="PRODUCT_COMPANY", validation_status="VALID"),
            Company(company_domain="tenstorrent.com", canonical_company_id="TENSTORRENT",
                    company_name="Tenstorrent", name_key="tenstorrent",
                    prospect_type="PRODUCT_COMPANY", validation_status="VALID"),
        ])
        s.commit()
        yield s


def test_news_type_normalization():
    assert normalize_news_type("switch") == "LEADERSHIP_CHANGE"
    assert normalize_news_type("PROMOTION") == "ROLE_CHANGE"
    assert normalize_news_type("hire") == "EXECUTIVE_HIRE"
    assert normalize_news_type("anything else") == "COMPANY_NEWS"


def test_ingest_creates_company_news_opportunities(session):
    res = CompanyNewsIngestor(session).ingest(FIX / "company_news.jsonl")
    assert (res.rows_in, res.rows_upserted, res.rows_rejected) == (4, 4, 0)

    by_type = {o.opportunity_type: o for o in session.scalars(select(Opportunity))}
    assert set(by_type) == {"EXECUTIVE_HIRE", "LEADERSHIP_CHANGE", "ROLE_CHANGE", "COMPANY_NEWS"}
    assert by_type["EXECUTIVE_HIRE"].company_news_signal == "Jane Doe joined as VP of Engineering (ex-Intel)"
    assert "->" in by_type["LEADERSHIP_CHANGE"].company_news_signal      # "John Roe: Director -> SVP Silicon"
    assert by_type["COMPANY_NEWS"].company_news_signal == "Opens new Austin design center"


def test_ingest_idempotent(session):
    CompanyNewsIngestor(session).ingest(FIX / "company_news.jsonl")
    CompanyNewsIngestor(session).ingest(FIX / "company_news.jsonl")
    assert session.scalar(select(func.count()).select_from(Opportunity)) == 4


def test_company_news_feeds_leadership_signals(session):
    """The headline synergy: director+ people moves ingested as company-news
    opportunities are picked up by the person-level leadership_signals feeder."""
    CompanyNewsIngestor(session).ingest(FIX / "company_news.jsonl")
    sigs = {s["person_name"]: s for s in from_blog_events(session)}

    assert set(sigs) == {"Jane Doe", "John Roe"}   # director+ only
    assert sigs["Jane Doe"]["movement_type"] == "new_executive_hire"
    assert sigs["Jane Doe"]["to_title"] == "VP of Engineering" and sigs["Jane Doe"]["seniority_band"] == "vp"
    assert sigs["John Roe"]["from_title"] == "Director" and sigs["John Roe"]["to_title"] == "SVP Silicon"
    assert sigs["John Roe"]["seniority_band"] == "svp" and sigs["John Roe"]["source"] == "blog_event"
    # Amy Lin → "Principal Eng" is below the director+ gate; the Austin-center item has no person
    assert "Amy Lin" not in sigs


# ----------------------------------------------------------------- API
@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'cn.db').as_posix()}",
                              log_json=False, dev_auth_bypass=True))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(Company(company_domain="groq.com", canonical_company_id="GROQ", company_name="Groq",
                          name_key="groq", prospect_type="PRODUCT_COMPANY", validation_status="VALID"))
            s.commit()
            CompanyNewsIngestor(s).ingest_rows([
                {"company_name": "Groq", "company_domain": "groq.com", "news_type": "EXECUTIVE_HIRE",
                 "person_name": "Jane Doe", "person_title": "VP of Engineering", "article_url": "u1"}])
        yield c


def test_api_company_news_only_filter(client):
    items = client.get("/opportunities").json()["items"]
    cn = [o for o in items if o["opportunity_type"] == "EXECUTIVE_HIRE"]
    assert cn and cn[0]["company_news_signal"].startswith("Jane Doe joined")

    only = client.get("/opportunities?company_news_only=true").json()["items"]
    assert only and all(
        o["opportunity_type"] in ("EXECUTIVE_HIRE", "LEADERSHIP_CHANGE", "ROLE_CHANGE", "COMPANY_NEWS")
        for o in only
    )
