"""Refresh Existing Data — regenerate Opportunities through the upgraded News
Collection Engine (Phase: News Intelligence Enhancement, requirement 8).

Deletes ONLY opportunity/news-signal rows (opportunities, opportunity_articles,
opportunity_reviews, news_articles) and regenerates them from the existing
opportunities' own article data (title/summary/company/url/type) run back through
the upgraded multi-signal extraction + intelligent dedup engine. Companies, users,
lead scores, career data, decision makers, and all configuration are left untouched.

    python scripts/refresh_news_opportunities.py            # live refresh (DATABASE_URL)
    python scripts/refresh_news_opportunities.py --dry-run  # regenerate into a rollback tx, report only

Safety: reads every source article into memory FIRST, refuses to wipe if that yields
nothing, and (dry-run) can preview the regenerated counts without committing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.config import get_settings          # noqa: E402
from backend.database import Database             # noqa: E402
from integration.news.engine import refresh_opportunities  # noqa: E402
from master_db.models import Company, LeadScore, Opportunity  # noqa: E402


def _articles_from_existing(session) -> list[dict]:
    """Turn each existing opportunity into a source article dict (preserving its
    classification + entities via ``_feed_row``) so the engine can regenerate."""
    articles: list[dict] = []
    for o in session.query(Opportunity).all():
        articles.append({
            "title": o.article_title or o.summary or o.company_news_signal or "",
            "body": o.summary or "",
            "company_name": o.company_name or "",
            "company_domain": o.company_domain or "",
            "url": o.article_url or f"opp://{o.opportunity_id}",
            "published_at": o.published_date or "",
            "publisher": o.source or "",
            "source_name": o.source or "",
            "source_type": o.source_type or "file",
            "_feed_row": {
                "opportunity_type": o.opportunity_type,
                "technology_mentioned": o.technology_mentioned,
                "product_mentioned": o.product_mentioned,
                "partner_company": o.partner_company,
                "country": o.country,
                "source_tier": o.source_tier,
            },
        })
    return articles


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="regenerate but roll back (report only)")
    args = ap.parse_args()

    settings = get_settings()
    db = Database(settings)
    print(f"Target database: {Database._safe_url(settings.database_url)}")

    with db.sessionmaker() as s:
        companies_before = s.query(Company).count()
        leadscores_before = s.query(LeadScore).count()
        opp_before = s.query(Opportunity).count()
        articles = _articles_from_existing(s)
        print(f"Before: opportunities={opp_before} companies={companies_before} lead_scores={leadscores_before}")
        if not articles:
            print("No source articles to regenerate from — aborting (nothing changed).")
            return 1

        metrics = refresh_opportunities(s, articles=articles, wipe=True)
        opp_after = s.query(Opportunity).count()
        companies_after = s.query(Company).count()
        leadscores_after = s.query(LeadScore).count()

        print(f"Regenerated: created={metrics.opportunities_created} "
              f"merged={metrics.duplicates_merged} rejected={metrics.rejected}")
        print(f"After: opportunities={opp_after} companies={companies_after} lead_scores={leadscores_after}")

        # Invariant: never touch companies / lead scores.
        assert companies_after == companies_before, "companies changed — aborting"
        assert leadscores_after == leadscores_before, "lead scores changed — aborting"

        if args.dry_run:
            s.rollback()
            print("DRY RUN — rolled back, no changes committed.")
        else:
            s.commit()
            print("COMMITTED — Opportunities page now shows only newly generated opportunities.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
