"""Default source-file locations for each engine output.

The engines write their deliverables into their own folders when run. These are
the default paths the ingestors look for, tried in priority order (richest source
first, Excel/CSV fallback). Override per call by passing an explicit path.

NOTE: as of P1 the engines have not been run, so most of these files do not exist
yet. :func:`find_source` returns ``None`` for a missing engine, and the backfill
simply skips it — no error. Once you run an engine, drop its output in place (or
point the ingestor at it) and re-run the backfill.
"""
from __future__ import annotations

import os
from pathlib import Path

# Where the four engine folders live. Override with SP_ENGINES_DIR in any non-dev
# environment (e.g. the cloud refresh runner checks the engines out under a different
# path). Defaults to the original dev location so local runs are unchanged.
ASSIGNMENTS = Path(
    os.environ.get("SP_ENGINES_DIR", r"C:\College\Internships\Silicon Patterns\assignments")
)

INDUSTRY_DIR = ASSIGNMENTS / "Industry_Discovery_Scraper_FINAL"
BLOG_DIR = ASSIGNMENTS / "Blog_Scraper_FINAL"
CAREER_DIR = ASSIGNMENTS / "Career_Scraper_FINAL" / "career scrapper"
# Decision makers come from the Apify Decision Maker Intelligence engine (an API
# call, not a source file) — see config/apify.py. No file-source entry is needed.

# Curated platform feeds (not an engine output) — e.g. annual lists / rankings.
# Dropped at the platform root or its data/ dir by an analyst.
PLATFORM_ROOT = Path(__file__).resolve().parent.parent
PLATFORM_DATA = PLATFORM_ROOT / "data"

# engine key -> candidate paths, richest source first.
DEFAULT_SOURCES: dict[str, list[Path]] = {
    "industry": [
        INDUSTRY_DIR / "master_company_universe.xlsx",
        INDUSTRY_DIR / "master_company_universe.csv",
    ],
    "blog": [
        BLOG_DIR / "blog_opportunities.jsonl",
        BLOG_DIR / "blog_opportunities.csv",
        BLOG_DIR / "blog_opportunities.xlsx",
    ],
    "career_jobs": [
        CAREER_DIR / "career_jobs.xlsx",
        CAREER_DIR / "career_jobs.csv",
    ],
    "career_demand": [
        CAREER_DIR / "career_demand_signals.xlsx",
        CAREER_DIR / "career_demand_signals.csv",
    ],
    "career_intel": [
        CAREER_DIR / "company_intelligence.xlsx",
        CAREER_DIR / "company_intelligence.csv",
    ],
    # Curated annual-lists / rankings feed (Change_04). Drop at the platform root or
    # data/; the BLOG_DIR fallback matches the colleague's documented location.
    "annual_list": [
        PLATFORM_DATA / "annual_lists.jsonl",
        PLATFORM_DATA / "annual_lists.csv",
        PLATFORM_DATA / "annual_lists.xlsx",
        PLATFORM_ROOT / "annual_lists.jsonl",
        PLATFORM_ROOT / "annual_lists.csv",
        BLOG_DIR / "annual_lists.jsonl",
        BLOG_DIR / "annual_lists.csv",
        BLOG_DIR / "annual_lists.xlsx",
    ],
    # Company-news / people-moves feed (Change_03) — a Blog-Crawler enrichment feed.
    "company_news": [
        PLATFORM_DATA / "company_news.jsonl",
        PLATFORM_DATA / "company_news.csv",
        PLATFORM_DATA / "company_news.xlsx",
        PLATFORM_ROOT / "company_news.jsonl",
        PLATFORM_ROOT / "company_news.csv",
        BLOG_DIR / "company_news.jsonl",
        BLOG_DIR / "company_news.csv",
        BLOG_DIR / "company_news.xlsx",
    ],
}


def find_source(engine: str) -> Path | None:
    """First existing source file for *engine*, or ``None`` if none exist yet."""
    for candidate in DEFAULT_SOURCES.get(engine, []):
        if candidate.exists():
            return candidate
    return None
