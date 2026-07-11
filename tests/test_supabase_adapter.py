"""Tests for the P2 Supabase LinkedIn adapter — fully offline (httpx MockTransport).

Covers: REST pagination, name-based company resolution via aliases, unresolved
employers -> NULL domain + review queue, person never dropped, no company stub
minted from a person, and duplicate-contact detection on re-import.
"""
import httpx
import pytest
from sqlalchemy import func, select
from urllib.parse import parse_qs, urlparse

from integration.ingestors.linkedin import LinkedInIngestor
from integration.ingestors.supabase_source import fetch_candidates, import_decision_makers
from integration.normalizer import canonical_company_id, name_key
from master_db.local import make_session_factory
from master_db.models import Company, CompanyAlias, DecisionMaker, ResolutionReviewQueue

SAMPLE = [
    {
        "linkedin_url": "https://www.linkedin.com/in/ada",
        "first_name": "Ada", "last_name": "Lovelace",
        "headline": "VP Engineering at Tenstorrent", "current_title": "VP Engineering",
        "location": "Toronto", "match_score": 88, "status": "sourced", "agent_score": 91,
        "profile_data": {"positions": [{"title": "VP Engineering", "companyName": "Tenstorrent"}]},
    },
    {
        "linkedin_url": "https://www.linkedin.com/in/bob?trk=abc",
        "first_name": "Bob", "last_name": "Metcalfe",
        "headline": "Director of Silicon at Nowhere Inc", "current_title": "Director of Silicon",
        "location": "Austin", "match_score": 60, "status": "sourced",
        "profile_data": {},
    },
]


@pytest.fixture()
def session():
    Session = make_session_factory(":memory:")
    with Session() as s:
        yield s


def _seed_company(s, domain, name):
    s.add(Company(company_domain=domain, canonical_company_id=canonical_company_id(domain, name),
                  company_name=name, name_key=name_key(name), validation_status="VALID"))
    s.add(CompanyAlias(alias=name, name_key=name_key(name), company_domain=domain, source="test"))
    s.flush()


def _mock_client(pages_by_offset):
    def handler(request: httpx.Request) -> httpx.Response:
        q = parse_qs(urlparse(str(request.url)).query)
        offset = int(q.get("offset", ["0"])[0])
        return httpx.Response(200, json=pages_by_offset.get(offset, []))
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_candidates_paginates():
    pages = {0: [{"linkedin_url": f"u{i}"} for i in range(1000)], 1000: [{"linkedin_url": "last"}]}
    with _mock_client(pages) as client:
        rows = fetch_candidates("https://proj.supabase.co", "anon-key", page_size=1000, client=client)
    assert len(rows) == 1001


def test_import_resolves_and_reviews(session):
    _seed_company(session, "tenstorrent.com", "Tenstorrent")
    with _mock_client({0: SAMPLE}) as client:
        res = import_decision_makers(session, "https://proj.supabase.co", "anon-key", client=client)

    assert (res.rows_in, res.rows_upserted, res.rows_rejected) == (2, 2, 0)
    ada = session.scalar(select(DecisionMaker).where(DecisionMaker.first_name == "Ada"))
    assert ada.company_domain == "tenstorrent.com"          # resolved via alias
    assert ada.seniority == "senior" and ada.agent_score == 91
    bob = session.scalar(select(DecisionMaker).where(DecisionMaker.first_name == "Bob"))
    assert bob.company_domain is None                        # unresolved -> NULL, not dropped
    assert res.rows_review_queued == 1
    q = session.scalar(select(ResolutionReviewQueue).where(ResolutionReviewQueue.source_engine == "linkedin"))
    assert "Nowhere" in q.raw_name
    # A person never mints a company.
    assert session.scalar(select(func.count()).select_from(Company)) == 1


def test_duplicate_contacts_detected_on_reimport(session):
    _seed_company(session, "tenstorrent.com", "Tenstorrent")
    LinkedInIngestor(session, create_stub=False).ingest_rows(SAMPLE, "supabase:test")
    res2 = LinkedInIngestor(session, create_stub=False).ingest_rows(SAMPLE, "supabase:test")
    assert res2.rows_duplicate == 2                          # both already present
    assert session.scalar(select(func.count()).select_from(DecisionMaker)) == 2  # no new rows


def test_linkedin_url_is_normalized_as_key(session):
    # The '?trk=abc' query string is stripped, so re-imports dedupe correctly.
    LinkedInIngestor(session, create_stub=False).ingest_rows(SAMPLE, "s")
    dm = session.scalar(select(DecisionMaker).where(DecisionMaker.first_name == "Bob"))
    assert dm.linkedin_url == "https://www.linkedin.com/in/bob"
