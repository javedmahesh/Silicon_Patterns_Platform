"""Pipeline stage registry.

Each stage ingests one component's data into the master DB, and optionally
declares how to run the upstream engine (used with ``--run-engine``). The
ingest functions are idempotent (they delegate to the P1 ingestors / P3 scorer).
"""
from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from config.sources import BLOG_DIR, CAREER_DIR, INDUSTRY_DIR, find_source
from integration.ingestors.annual_lists import AnnualListIngestor
from integration.ingestors.base import IngestionResult
from integration.ingestors.blog import BlogIngestor
from integration.ingestors.company_news import CompanyNewsIngestor
from integration.ingestors.career import (
    CompanyRollupsIngestor,
    DemandSignalsIngestor,
    JobsIngestor,
)
from integration.ingestors.industry import IndustryIngestor
from master_db.models import (
    Company,
    CompanyRollup,
    DecisionMaker,
    DiscoveryCandidateRecord,
    DemandSignal,
    EngagementRecommendation,
    Job,
    LeadScore,
    LeadershipSignal,
    MarketIntelligenceRecord,
    Opportunity,
)

PY = sys.executable


class SkipStage(Exception):
    """Raised by an ingest fn when the stage cannot run (e.g. no credentials)."""


@dataclass(slots=True)
class IngestMetrics:
    rows_in: int = 0
    rows_upserted: int = 0
    rows_rejected: int = 0
    rows_review: int = 0
    errors: list[str] = field(default_factory=list)
    notes: str = ""
    # Explicit status hint from the ingestor ("success"|"partial"|"failed"). When
    # set, the orchestrator honors it instead of inferring status from row counts —
    # this is how a fully-failed Apify fetch (0 rows, only errors) reports as failed
    # rather than a hollow "success".
    status: str = ""


@dataclass(slots=True)
class EngineSpec:
    cmd: list[str]
    cwd: Path
    timeout: int = 1800
    description: str = ""


@dataclass(slots=True)
class Stage:
    name: str
    order: int
    tables: list           # ORM models, for before/after row counts
    ingest: Callable[[Session], IngestMetrics]
    engine: EngineSpec | None = None
    description: str = ""


def _from_result(r: IngestionResult) -> IngestMetrics:
    return IngestMetrics(
        rows_in=r.rows_in, rows_upserted=r.rows_upserted, rows_rejected=r.rows_rejected,
        rows_review=r.rows_review_queued, errors=list(r.errors), notes=r.notes,
        status=r.status,
    )


def _agg(results: list[IngestionResult]) -> IngestMetrics:
    m = IngestMetrics()
    notes: list[str] = []
    for r in results:
        m.rows_in += r.rows_in
        m.rows_upserted += r.rows_upserted
        m.rows_rejected += r.rows_rejected
        m.rows_review += r.rows_review_queued
        m.errors += list(r.errors)
        if r.notes and r.notes not in notes:
            notes.append(r.notes)
    m.notes = " | ".join(notes)
    return m


# ------------------------------------------------------------- ingest fns
def industry_ingest(session: Session) -> IngestMetrics:
    src = find_source("industry")
    if not src:
        return IngestMetrics(notes="no industry output found (run the engine first)")
    return _from_result(IndustryIngestor(session, mode="pipeline").ingest(src))


def _enrich_opportunities(session: Session, metrics: IngestMetrics) -> IngestMetrics:
    """Backfill rich News-Intelligence AI fields on opportunities this stage wrote.

    Count-preserving (updates rows in place; never creates/deletes an opportunity),
    so downstream lead scoring and every existing test see the same row set — only
    the new intelligence columns get populated. Best-effort: a failure here never
    fails the stage."""
    try:
        from integration.news.engine import enrich_new_opportunities

        n = enrich_new_opportunities(session)
        if n:
            note = f"enriched {n} opportunities with News Intelligence"
            metrics.notes = f"{metrics.notes} | {note}" if metrics.notes else note
    except Exception as exc:  # pragma: no cover - enrichment is additive, never fatal
        metrics.notes = (metrics.notes + " | " if metrics.notes else "") + f"enrichment skipped: {exc}"
    return metrics


def blog_ingest(session: Session) -> IngestMetrics:
    src = find_source("blog")
    if not src:
        return IngestMetrics(notes="no blog output found")
    return _enrich_opportunities(session, _from_result(BlogIngestor(session, mode="pipeline").ingest(src)))


def news_ingest(session: Session) -> IngestMetrics:
    """Collect from the configured, enabled ``news_sources`` (RSS / Google Alerts)
    through the News Collection Engine → multi-signal AI extraction → resolver →
    opportunities. Incremental (If-Modified-Since + published-date + content-hash
    dedup) so a scheduled re-run only processes genuinely new articles and never
    duplicates. A clean no-op when no sources are configured/enabled — so a fresh
    install (or the hermetic test suite) runs the stage without any network call."""
    from integration.news.engine import NewsIntelligenceEngine, enabled_news_sources

    sources = enabled_news_sources(session)
    if not sources:
        return IngestMetrics(notes="no enabled news sources configured (seed via scripts/seed_news_sources.py)")
    m = NewsIntelligenceEngine(session, mode="pipeline").run(sources=sources)
    status = "partial" if m.errors else "success"
    notes = (f"sources={len(sources)} collected={m.articles_collected} "
             f"created={m.opportunities_created} merged={m.duplicates_merged}")
    # Surface dead/broken feeds so they're diagnosable — but a failed feed is NOT a
    # stage failure (the other sources still ran), it only annotates the run.
    if m.source_errors:
        notes += f" | feeds_failed={len(m.source_errors)}: " + "; ".join(m.source_errors[:5])
    return IngestMetrics(
        rows_in=m.articles_collected, rows_upserted=m.opportunities_created + m.opportunities_updated,
        rows_rejected=m.rejected, rows_review=m.review_queued, errors=list(m.errors),
        status=status, notes=notes,
    )


def annual_list_ingest(session: Session) -> IngestMetrics:
    """Ingest annual-list / ranking appearances as ANNUAL_LIST opportunities — a
    curated platform feed (no live crawler). A no-op when no feed is present, so it
    is safe in every `run all`."""
    src = find_source("annual_list")
    if not src:
        return IngestMetrics(notes="no annual-list feed found (drop annual_lists.{jsonl,csv,xlsx})")
    return _from_result(AnnualListIngestor(session, mode="pipeline").ingest(src))


def company_news_ingest(session: Session) -> IngestMetrics:
    """Ingest company-news / people-move items (executive hires, leadership & role
    changes) as opportunities. Director+ rows are also picked up by the
    leadership_signals blog-event feeder. A no-op when no feed is present."""
    src = find_source("company_news")
    if not src:
        return IngestMetrics(notes="no company-news feed found (drop company_news.{jsonl,csv,xlsx})")
    return _enrich_opportunities(
        session, _from_result(CompanyNewsIngestor(session, mode="pipeline").ingest(src)))


def career_ingest(session: Session) -> IngestMetrics:
    results = []
    for key, cls in (("career_jobs", JobsIngestor), ("career_demand", DemandSignalsIngestor),
                     ("career_intel", CompanyRollupsIngestor)):
        src = find_source(key)
        if src:
            results.append(cls(session, mode="pipeline").ingest(src))
    if not results:
        return IngestMetrics(notes="no career output found")
    return _agg(results)


def decision_maker_intelligence_ingest(session: Session, *, limit: int | None = None) -> IngestMetrics:
    """Ingest decision makers via the Apify Decision Maker Intelligence engine.

    The platform's sole decision-maker discovery engine (C-suite, directors, VPs).
    Requires the APIFY_API_TOKEN environment variable.

    `limit` is benchmark mode (see orchestrator/cli.py's `--limit`): when set,
    restricts the run to the first `limit` companies instead of the full universe.
    `None` (the default) is the unchanged production path — every other caller of
    this function, and every other stage, is unaffected.
    """
    from config.apify import load_apify_credentials
    from integration.ingestors.apify_source import import_decision_makers

    api_token, _ = load_apify_credentials()
    if not api_token:
        raise SkipStage("no Apify credentials (set APIFY_API_TOKEN)")

    return _from_result(import_decision_makers(session, limit=limit))


def market_discovery_ingest(session: Session) -> IngestMetrics:
    """Run the Market Discovery Engine over its registered, enabled sources.

    The scheduler knows nothing about individual sources: it calls the engine, the
    engine asks the registry which sources are enabled, and the registry is the only
    thing that knows Firecrawl/Wellfound/Dealroom/etc. exist. Adding a connector
    therefore never touches this function.

    With zero registered sources — the state this framework ships in — the run is a
    successful no-op, which is why the stage is safe to include in the automatic
    pipeline before any connector exists.
    """
    from backend.config import get_settings
    from backend.market_discovery import registry, run_discovery

    registry.autodiscover()      # import any connector modules so they self-register
    result = run_discovery(session, get_settings())
    return IngestMetrics(
        rows_in=result.fetched,
        rows_upserted=result.new + result.updated,
        rows_rejected=result.rejected,
        rows_review=result.below_threshold,
        errors=[f"{s.name}: {s.error}" for s in result.failed_sources],
        status=result.status,
        notes=result.summary(),
    )


def market_intelligence_ingest(session: Session) -> IngestMetrics:
    """Interpret discovery candidates into market intelligence.

    Runs immediately after the Market Discovery Engine, so a company found this run
    is classified, signalled and prioritized in the same pass. Deterministic rules
    only — in-process, no network, no credentials — so the stage is always safe to
    include: with no candidates it is a successful no-op.

    The scheduler knows nothing about rules or vocabularies; changing what the
    platform looks for is a rule-pack change and never touches this function.
    """
    from backend.config import get_settings
    from backend.market_intelligence import run_market_intelligence

    result = run_market_intelligence(session, get_settings())
    return IngestMetrics(
        rows_in=result.evaluated + result.skipped,
        rows_upserted=result.evaluated,
        rows_rejected=result.rejected,
        rows_review=len(result.actionable),
        errors=list(result.errors),
        status=result.status,
        notes=result.summary(),
    )


def scoring_ingest(session: Session) -> IngestMetrics:
    from lead_scoring.service import score_all

    summary = score_all(session)
    return IngestMetrics(
        rows_in=summary.scored, rows_upserted=summary.scored,
        notes=f"grades={summary.grade_counts}",
    )


def leadership_ingest(session: Session) -> IngestMetrics:
    """Recompute person-level director+ leadership-movement signals — a platform
    derivation over decision-maker snapshots + blog events (no engine, no re-crawl),
    so it runs every refresh even when the engines aren't vendored. (Legacy career
    history from earlier profile data still contributes while it exists.)"""
    from leadership_signals.derive import rebuild

    counts = rebuild(session)
    return IngestMetrics(
        rows_in=counts["total"], rows_upserted=counts["total"],
        notes=(f"snapshot_comparison={counts['snapshot_comparison']} "
               f"blog_event={counts['blog_event']} legacy_history={counts['linkedin_history']}"),
    )


def engagement_ingest(session: Session) -> IngestMetrics:
    """Recompute each company's sales-pitch / engagement recommendation — a platform
    derivation over every other signal, so it runs last in the pipeline."""
    from engagement.recommend import rebuild

    counts = rebuild(session)
    return IngestMetrics(rows_in=counts["total"], rows_upserted=counts["total"],
                         notes=f"recommendations={counts['total']}")


# ------------------------------------------------------------- registry
STAGES: dict[str, Stage] = {
    "industry": Stage(
        "industry", 1, [Company], industry_ingest,
        EngineSpec([PY, "main.py", "discover", "--export"], INDUSTRY_DIR, 3600, "Industry Discovery crawl"),
        "Find companies -> companies",
    ),
    "blog": Stage(
        "blog", 2, [Opportunity], blog_ingest,
        # The Blog Crawler is now the modular News Collection Engine (RSS-first).
        # `--news` runs source-registry ingestion (news_sources -> raw_articles),
        # feeds every new article through the unchanged AI opportunity pipeline, and
        # writes the same blog_opportunities.{jsonl,csv} contract that blog_ingest
        # reads into `opportunities` (the Signals section).
        EngineSpec([PY, "-m", "silicon_patterns_blogcrawler", "--news"], BLOG_DIR, 3600,
                   "News Collection Engine (RSS)"),
        "Collect news (RSS) -> opportunities",
    ),
    "news": Stage(
        "news", 2, [Opportunity], news_ingest, None,
        "Collect live news (RSS / Google Alerts from news_sources) -> opportunities",
    ),
    "annual_list": Stage(
        "annual_list", 3, [Opportunity], annual_list_ingest, None,
        "Ingest annual-list / ranking appearances -> opportunities (ANNUAL_LIST)",
    ),
    "company_news": Stage(
        "company_news", 3, [Opportunity], company_news_ingest, None,
        "Ingest company-news / people moves -> opportunities (EXECUTIVE_HIRE / LEADERSHIP_CHANGE / …)",
    ),
    "career": Stage(
        "career", 3, [Job, DemandSignal, CompanyRollup], career_ingest,
        # --full: the engine defaults to `resume=True`, which permanently skips any
        # company already stamped success/no_ats/no_careers/parser_error in its own
        # crawl_scraper.sqlite3 -- without --full a scheduled re-run crawls ZERO
        # companies after the first pass (confirmed against a real run), so no new
        # postings at already-known companies are ever discovered again.
        EngineSpec([PY, "-m", "career_scraper", "run", "career_companies_large.csv", "--output", ".", "--full"],
                   CAREER_DIR, 3600, "Career Scraper"),
        "Find demand -> jobs/demand_signals/company_rollups",
    ),
    # MANUAL-ONLY stage: intentionally NOT in PIPELINE_ORDER (below). The Apify actor
    # has a per-lead cost, so decision-maker intelligence is never run by the scheduler,
    # a Standard Run, or `run all`. It is triggered explicitly — per company, with a
    # requested count — from the Decision Makers page (backend/dm_intelligence_jobs.py)
    # or via `sp-platform run decision_maker_intelligence`. Kept in the STAGES registry
    # (and runnable via run_stage) so that manual path, and existing data, keep working.
    "decision_maker_intelligence": Stage(
        "decision_maker_intelligence", 4, [DecisionMaker], decision_maker_intelligence_ingest, None,
        "Scrape decision makers (C-suite, directors, VPs) -> decision_makers (Apify) — MANUAL only",
    ),
    # Market Discovery Engine: finds NEW market entrants. Runs before scoring so a
    # company promoted this run is scored in the same pass. No engine spec — the
    # engine is in-process and its sources are plugged in via the registry, not here.
    "market_discovery": Stage(
        "market_discovery", 4, [DiscoveryCandidateRecord], market_discovery_ingest, None,
        "Discover new market entrants -> discovery_candidates",
    ),
    # Market Intelligence Layer: interprets what discovery found. Immediately after
    # discovery so a company found this run is prioritized in the same pass, and
    # before scoring so lead scoring sees current intelligence. Deterministic rules,
    # in-process — no engine spec, no credentials, no network.
    "market_intelligence": Stage(
        "market_intelligence", 4, [MarketIntelligenceRecord], market_intelligence_ingest, None,
        "Interpret discovered companies -> market_intelligence",
    ),
    "scoring": Stage(
        "scoring", 5, [LeadScore], scoring_ingest, None,
        "Score leads -> lead_scores",
    ),
    "leadership": Stage(
        "leadership", 6, [LeadershipSignal], leadership_ingest, None,
        "Derive director+ leadership movement -> leadership_signals",
    ),
    "engagement": Stage(
        "engagement", 7, [EngagementRecommendation], engagement_ingest, None,
        "Recommend a sales pitch per company -> engagement_recommendations",
    ),
}

# The AUTOMATIC pipeline — what the scheduler, a Standard Run, and `run all` execute.
# ``decision_maker_intelligence`` is deliberately absent: it is manual-only (paid Apify
# actor) and is triggered per-company from the Decision Makers page instead. It remains
# in STAGES above so it can still be run on demand via ``run_stage`` / the manual job.
PIPELINE_ORDER: list[str] = ["industry", "blog", "news", "annual_list", "company_news", "career", "market_discovery", "market_intelligence", "scoring", "leadership", "engagement"]
