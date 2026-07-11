"""Populate the master DB with a full end-to-end dataset from the bundled
fixtures — every engine + the curated feeds + scoring + the platform derivations
— WITHOUT running the external engines.

    # from Silicon_Patterns_Platform/
    python scripts/seed_master_db.py                  # -> master_local.db
    python scripts/seed_master_db.py --db scratch.db  # -> a throwaway DB (safe to test)

Gives a real Discovery dataset (companies + opportunities incl. annual lists &
company news + demand signals + decision makers + lead scores + leadership signals
+ engagement recommendations). Idempotent: every ingestor upserts and the
derivations rebuild cleanly, so it is safe to re-run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engagement.recommend import rebuild as rebuild_engagement  # noqa: E402
from integration.ingestors.annual_lists import AnnualListIngestor  # noqa: E402
from integration.ingestors.backfill import run_backfill  # noqa: E402
from integration.ingestors.company_news import CompanyNewsIngestor  # noqa: E402
from lead_scoring.service import score_all  # noqa: E402
from leadership_signals.derive import rebuild as rebuild_leadership  # noqa: E402
from master_db.local import make_session_factory  # noqa: E402

FIX = ROOT / "tests" / "fixtures"

# The four engine outputs (run_backfill ingests them in dependency order).
SOURCES = {
    "industry": FIX / "industry_companies.csv",
    "blog": FIX / "blog_opportunities.jsonl",
    "career_jobs": FIX / "career_jobs.csv",
    "career_demand": FIX / "career_demand_signals.csv",
    "career_intel": FIX / "company_intelligence.csv",
    "linkedin": FIX / "linkedin_candidates.json",
}

# Curated platform feeds (Change_04 annual lists / Change_03 company news) — not
# engine outputs, so they're ingested directly.
CURATED: list[tuple[str, type, Path]] = [
    ("annual_list", AnnualListIngestor, FIX / "annual_lists.jsonl"),
    ("company_news", CompanyNewsIngestor, FIX / "company_news.jsonl"),
]


def seed(db_path: str | Path, *, verbose: bool = True) -> dict:
    """Seed *db_path* from the bundled fixtures; return a summary dict. Idempotent."""
    def log(msg: str) -> None:
        if verbose:
            print(msg)

    summary: dict = {}
    with make_session_factory(db_path)() as s:
        # 1) the four engines
        for key, res in run_backfill(s, sources=SOURCES).items():
            summary[key] = res.rows_upserted
            log(f"  {key:14s} in={res.rows_in} upserted={res.rows_upserted} rejected={res.rows_rejected}")
        # 2) curated feeds (annual lists + company news)
        for key, cls, path in CURATED:
            if path.exists():
                res = cls(s, mode="pipeline").ingest(path)
                summary[key] = res.rows_upserted
                log(f"  {key:14s} in={res.rows_in} upserted={res.rows_upserted} rejected={res.rows_rejected}")
        s.commit()

        # 3) scoring + the platform derivations (leadership signals, engagement)
        summary["scoring"] = score_all(s).grade_counts
        summary["leadership"] = rebuild_leadership(s)
        summary["engagement"] = rebuild_engagement(s)
        log(f"  scoring        {summary['scoring']}")
        log(f"  leadership     {summary['leadership']}")
        log(f"  engagement     {summary['engagement']}")
    log(f"master DB seeded -> {db_path}")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed the master DB from bundled fixtures.")
    ap.add_argument("--db", default=str(ROOT / "master_local.db"),
                    help="SQLite DB path (default: master_local.db). Use a throwaway path to test.")
    seed(ap.parse_args().db)


if __name__ == "__main__":
    main()
