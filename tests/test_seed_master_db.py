"""Master-DB seed script (Change_06) — populates a full end-to-end dev dataset
from the bundled fixtures (engines + curated feeds + scoring + derivations),
without the external engines, against a throwaway DB.
"""
from sqlalchemy import func, select

from master_db.local import make_session_factory
from master_db.models import (
    Company,
    EngagementRecommendation,
    LeadScore,
    LeadershipSignal,
    Opportunity,
)
from scripts.seed_master_db import seed


def test_seed_populates_full_dataset(tmp_path):
    db = tmp_path / "seed.db"
    summary = seed(db, verbose=False)

    # the summary reports each ingest + the derivations
    assert summary["industry"] >= 2
    assert summary["annual_list"] >= 1 and summary["company_news"] >= 1
    assert summary["engagement"]["total"] >= 1

    with make_session_factory(db)() as s:
        def n(model):
            return s.scalar(select(func.count()).select_from(model))

        assert n(Company) >= 2
        assert n(LeadScore) >= 2                 # scored
        assert n(EngagementRecommendation) >= 1  # engagement derivation ran
        # curated feeds landed as opportunities
        assert s.scalar(select(func.count()).select_from(Opportunity)
                        .where(Opportunity.opportunity_type == "ANNUAL_LIST")) >= 1
        # the company-news -> leadership synergy produced blog_event signals
        assert n(LeadershipSignal) >= 1
        assert s.scalar(select(func.count()).select_from(LeadershipSignal)
                        .where(LeadershipSignal.source == "blog_event")) >= 1


def test_seed_is_idempotent(tmp_path):
    db = tmp_path / "seed.db"
    seed(db, verbose=False)
    seed(db, verbose=False)   # re-run: upserts + rebuilds, no duplication
    with make_session_factory(db)() as s:
        companies = s.scalar(select(func.count()).select_from(Company))
        scores = s.scalar(select(func.count()).select_from(LeadScore))
        assert companies == scores   # 1:1 lead_scores per company, no dupes
