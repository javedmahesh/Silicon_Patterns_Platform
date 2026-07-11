"""Seed the curated production news feeds into ``news_sources`` (idempotent).

Configuration/DB-driven: after seeding, sources are managed in the DB (enable/disable,
edit, or add more via ``POST /opportunities/news-sources`` or directly). The Scheduler
and Standard Run automatically collect from every enabled source with a URL.

    python scripts/seed_news_sources.py            # seed against DATABASE_URL
    python scripts/seed_news_sources.py --list     # just list configured sources

Google Alerts feeds are seeded DISABLED with a blank URL — create the alert at
https://www.google.com/alerts (Deliver to: RSS feed), paste the feed URL onto the
row, and enable it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.config import get_settings          # noqa: E402
from backend.database import Database             # noqa: E402
from integration.news.engine import seed_news_sources  # noqa: E402
from master_db.models import NewsSource           # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="list configured sources and exit")
    args = ap.parse_args()

    db = Database(get_settings())
    with db.sessionmaker() as s:
        if not args.list:
            result = seed_news_sources(s)
            s.commit()
            print(f"Seeded news sources: created={result['created']} updated={result['updated']} "
                  f"total_curated={result['total']}")
        print("\nConfigured news sources:")
        for src in s.query(NewsSource).order_by(NewsSource.name).all():
            flag = "on " if src.enabled else "off"
            url = src.url or "(no URL — needs setup)"
            print(f"  [{flag}] {src.name:<32} {src.adapter_type:<14} cred={src.credibility:<3} {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
