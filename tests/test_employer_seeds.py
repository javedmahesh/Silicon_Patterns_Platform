"""Tests for P2 Option B: employer seeding + decision-maker re-resolution."""
import pytest
from sqlalchemy import func, select

from integration.employer_seeds import seed_employers
from integration.ingestors.linkedin import LinkedInIngestor
from integration.reresolve import reresolve_decision_makers
from master_db.local import make_session_factory
from master_db.models import Company, DecisionMaker, ResolutionReviewQueue

CANDIDATES = [
    {"linkedin_url": "https://lnkd.in/a", "first_name": "A", "current_title": "Eng",
     "profile_data": {"positions": [{"companyName": "Cadence Design Systems"}]}},
    {"linkedin_url": "https://lnkd.in/b", "first_name": "B", "current_title": "Eng",
     "profile_data": {"positions": [{"companyName": "Cadenece"}]}},          # typo variant
    {"linkedin_url": "https://lnkd.in/c", "first_name": "C", "current_title": "Eng",
     "profile_data": {"positions": [{"companyName": "Intel Corporation"}]}},
    {"linkedin_url": "https://lnkd.in/d", "first_name": "D", "current_title": "Eng",
     "profile_data": {"positions": [{"companyName": "Obscure Unknown LLC"}]}},  # stays unresolved
]


@pytest.fixture()
def session():
    Session = make_session_factory(":memory:")
    with Session() as s:
        yield s


def test_seed_then_reresolve(session):
    LinkedInIngestor(session, create_stub=False).ingest_rows(CANDIDATES, "supabase:test")
    matched0 = session.scalar(select(func.count()).select_from(DecisionMaker)
                              .where(DecisionMaker.company_domain.isnot(None)))
    assert matched0 == 0
    assert session.scalar(select(func.count()).select_from(ResolutionReviewQueue)
                          .where(ResolutionReviewQueue.status == "pending")) == 4

    created, mappings = seed_employers(session)
    assert created >= 35 and len(mappings) > created      # aliases include extra spellings
    assert session.get(Company, "mirafra.com") is None    # SERVICE_PROVIDER seeds are excluded

    stats = reresolve_decision_makers(session)
    assert stats.matched_before == 0
    assert stats.newly_matched == 3                        # 2 Cadence variants + Intel
    assert stats.still_unresolved == 1                     # Obscure Unknown LLC
    assert stats.review_closed == 3

    doms = {d.first_name: d.company_domain for d in session.scalars(select(DecisionMaker)).all()}
    assert doms["A"] == "cadence.com" and doms["B"] == "cadence.com"   # both variants -> one domain
    assert doms["C"] == "intel.com"
    assert doms["D"] is None
    assert session.scalar(select(func.count()).select_from(ResolutionReviewQueue)
                          .where(ResolutionReviewQueue.status == "pending")) == 1


def test_reresolve_adds_no_new_review_rows(session):
    LinkedInIngestor(session, create_stub=False).ingest_rows(CANDIDATES, "s")
    seed_employers(session)
    reresolve_decision_makers(session)
    rq1 = session.scalar(select(func.count()).select_from(ResolutionReviewQueue))
    reresolve_decision_makers(session)                     # idempotent second pass
    rq2 = session.scalar(select(func.count()).select_from(ResolutionReviewQueue))
    assert rq1 == rq2
