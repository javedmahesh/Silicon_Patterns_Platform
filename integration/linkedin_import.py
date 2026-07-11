"""Live LinkedIn import: read the existing Supabase ``candidates`` table and
populate ``decision_makers`` in the master DB.

Usage (PowerShell), from the Silicon_Patterns_Platform folder:

    $env:SP_SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
    $env:SP_SUPABASE_KEY = "YOUR-ANON-KEY"
    python -m integration.linkedin_import

Credentials come from the environment (never the repo). Writes into
``master_local.db`` by default; pass a different path as the first argument.
Prints the P2 metrics. Read-only against Supabase; the LinkedIn app is untouched.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from sqlalchemy import func, select

from config.supabase import load_supabase_credentials
from integration.ingestors.supabase_source import SupabaseError, import_decision_makers
from master_db.local import make_session_factory
from master_db.models import Company, DecisionMaker, ResolutionReviewQueue

DEFAULT_DB = Path(__file__).resolve().parent.parent / "master_local.db"


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    argv = sys.argv[1:] if argv is None else argv
    db_path = Path(argv[0]) if argv else DEFAULT_DB

    url, key = load_supabase_credentials()
    if not url or not key:
        print("ERROR: Supabase credentials not found.\n"
              "Set them first, e.g.:\n"
              '  $env:SP_SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"\n'
              '  $env:SP_SUPABASE_KEY = "YOUR-ANON-KEY"')
        return 2

    if not db_path.exists():
        print(f"ERROR: master DB not found at {db_path}. Run the backfill first.")
        return 2

    Session = make_session_factory(db_path)
    with Session() as s:
        before = s.scalar(select(func.count()).select_from(DecisionMaker))
        rq_before = s.scalar(select(func.count()).select_from(ResolutionReviewQueue))
        try:
            res = import_decision_makers(s, url, key)
        except SupabaseError as exc:
            print(f"ERROR: {exc}")
            return 1

        total = s.scalar(select(func.count()).select_from(DecisionMaker))
        matched = s.scalar(select(func.count()).select_from(DecisionMaker)
                           .where(DecisionMaker.company_domain.isnot(None)))
        unresolved = s.scalar(select(func.count()).select_from(DecisionMaker)
                              .where(DecisionMaker.company_domain.is_(None)))
        distinct_co = s.scalar(select(func.count(func.distinct(DecisionMaker.company_domain)))
                               .where(DecisionMaker.company_domain.isnot(None)))
        rq_after = s.scalar(select(func.count()).select_from(ResolutionReviewQueue))

        print("\n========== P2 LinkedIn Import Results ==========")
        print(f"  candidates read from Supabase   : {res.rows_in}")
        print(f"  1. decision makers imported     : {res.rows_upserted}  (table now holds {total})")
        print(f"  2. matched to company_domain    : {matched}  ({distinct_co} distinct companies)")
        print(f"  3. unresolved company matches   : {unresolved}")
        print(f"  4. duplicate contacts detected  : {res.rows_duplicate}")
        print(f"  5. review_queue additions       : {rq_after - rq_before}  (queue now {rq_after})")
        print(f"     failed rows                  : {res.rows_rejected}  (status: {res.status})")
        print("================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
