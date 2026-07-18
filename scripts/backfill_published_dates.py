"""One-off backfill: normalize existing ``opportunities.published_date`` to ISO
``YYYY-MM-DD`` so the Opportunities newest/oldest sort and date-range filters are
chronological. Idempotent — safe to re-run.

New rows are already normalized on write by the ORM listener in master_db.models;
this only fixes rows written before that listener existed (e.g. legacy
"Month D, YYYY" annual-list / company-news / blog events).

Runs against whatever DATABASE_URL the backend/orchestrator use (Supabase in the
real deployment; the local SQLite when DATABASE_URL points at master_local.db):

    python -m scripts.backfill_published_dates
"""
from __future__ import annotations

from sqlalchemy import select

from backend.config import get_settings
from backend.database import Database
from master_db.models import Opportunity, normalize_published_date


def main() -> None:
    changed = 0
    with Database(get_settings()).sessionmaker() as session:
        for opp in session.scalars(select(Opportunity)):
            iso = normalize_published_date(opp.published_date)
            if iso != (opp.published_date or ""):
                opp.published_date = iso
                changed += 1
        session.commit()
    print(f"normalized {changed} opportunity published_date value(s) to ISO")


if __name__ == "__main__":
    main()
