"""Annual-lists ingestor (Change_04) — appearances on rankings → ANNUAL_LIST
opportunities, the shared `company_news_signal` rank, idempotency, and the API.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.config import Settings
from backend.main import create_app
from integration.ingestors.annual_lists import AnnualListIngestor
from master_db.local import make_session_factory
from master_db.models import Base, Company, Opportunity

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture()
def session():
    with make_session_factory(":memory:")() as s:
        # the two companies the sample feed references, catalogued (not stubs)
        s.add_all([
            Company(company_domain="groq.com", canonical_company_id="GROQ", company_name="Groq",
                    name_key="groq", prospect_type="PRODUCT_COMPANY", validation_status="VALID"),
            Company(company_domain="tenstorrent.com", canonical_company_id="TENSTORRENT",
                    company_name="Tenstorrent", name_key="tenstorrent",
                    prospect_type="PRODUCT_COMPANY", validation_status="VALID"),
        ])
        s.commit()
        yield s


def test_ingest_creates_annual_list_opportunities(session):
    res = AnnualListIngestor(session).ingest(FIX / "annual_lists.jsonl")
    assert (res.rows_in, res.rows_upserted, res.rows_rejected) == (3, 3, 0)

    opps = list(session.scalars(select(Opportunity).where(Opportunity.opportunity_type == "ANNUAL_LIST")))
    assert len(opps) == 3
    forbes = next(o for o in opps if o.opportunity_category == "Forbes AI 50")
    assert forbes.company_domain == "groq.com"
    assert forbes.company_news_signal == "Rank: 7"          # rank captured in the shared column
    assert "Forbes AI 50" in forbes.summary                  # auto-summary built
    assert forbes.effective_opportunity_score == 60          # nudges the opportunity sub-score
    # a list appearance without a rank leaves the signal blank
    no_rank = next(o for o in opps if o.opportunity_category == "CNBC Disruptor 50" and o.company_domain == "groq.com")
    assert no_rank.company_news_signal == ""


def test_ingest_is_idempotent(session):
    AnnualListIngestor(session).ingest(FIX / "annual_lists.jsonl")
    AnnualListIngestor(session).ingest(FIX / "annual_lists.jsonl")
    assert session.scalar(select(func.count()).select_from(Opportunity)) == 3


def test_unresolved_company_becomes_stub(session):
    # a company not catalogued → resolver creates a low-confidence stub (pipeline never blocks)
    res = AnnualListIngestor(session).ingest_rows([
        {"company_name": "Brandnew Silicon", "company_domain": "brandnew-silicon.example",
         "list_name": "EE Times Silicon 100", "list_year": "2024", "list_rank": "88"}])
    assert res.rows_upserted == 1
    stub = session.get(Company, "brandnew-silicon.example")
    assert stub is not None and stub.is_stub is True


# ----------------------------------------------------------------- API
@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'al.db').as_posix()}",
                              log_json=False, dev_auth_bypass=True))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(Company(company_domain="groq.com", canonical_company_id="GROQ", company_name="Groq",
                          name_key="groq", prospect_type="PRODUCT_COMPANY", validation_status="VALID"))
            s.commit()
            AnnualListIngestor(s).ingest_rows([
                {"company_name": "Groq", "company_domain": "groq.com", "list_name": "Forbes AI 50",
                 "list_year": "2024", "list_rank": "7", "list_publisher": "Forbes",
                 "article_url": "https://forbes.com/ai50"}])
        yield c


def test_api_exposes_annual_lists(client):
    # appears in /opportunities with the new signal field
    items = client.get("/opportunities").json()["items"]
    al = [o for o in items if o["opportunity_type"] == "ANNUAL_LIST"]
    assert al and al[0]["company_news_signal"] == "Rank: 7"
    assert al[0]["opportunity_category"] == "Forbes AI 50"

    # the annual_lists_only quick-filter returns only ANNUAL_LIST rows
    only = client.get("/opportunities?annual_lists_only=true").json()["items"]
    assert only and all(o["opportunity_type"] == "ANNUAL_LIST" for o in only)

    # and on the company profile (Recognition card reads these)
    prof = client.get("/companies/groq.com").json()
    assert any(o["opportunity_type"] == "ANNUAL_LIST" for o in prof["opportunities"])
