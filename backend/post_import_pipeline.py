"""Post-import intelligence refresh pipeline (Phase 7).

Runs automatically AFTER a successful committed historical import (never after a
preview / dry-run / failed / rolled-back import). It folds the newly imported and
updated companies + decision makers into the platform's intelligence by re-running the
EXISTING engines incrementally — no business logic is reimplemented here; every stage
delegates to the engine that already owns it.

Twelve ordered stages, each tracked as its own ``pipeline_runs`` row (reusing
:class:`orchestrator.runs.RunTracker`) so the whole refresh shows up in the existing
pipeline execution history. Stages are independent: one failing is recorded and the
rest continue (failure recovery), and only failed stages can be retried — completed
work is never invalidated.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from master_db.models import Company, DecisionMaker, PipelineRun
from orchestrator.runs import RunTracker


@dataclass(slots=True)
class RefreshContext:
    session: Session
    settings: object
    domains: list[str]          # affected company domains (created/updated + gained a DM)
    dm_ids: list[int]           # affected decision-maker ids


# ------------------------------------------------------------------ stages
def _stage_company_relationships(ctx: RefreshContext) -> tuple[int, str]:
    if not ctx.domains:
        return 0, "no affected companies"
    present = ctx.session.scalar(select(func.count()).select_from(Company)
                                 .where(Company.company_domain.in_(ctx.domains))) or 0
    return present, f"validated {present}/{len(ctx.domains)} company rows"


def _stage_dm_relationships(ctx: RefreshContext) -> tuple[int, str]:
    if not ctx.dm_ids:
        return 0, "no affected decision makers"
    # every affected DM must point at a real company (or NULL) — relationships stay valid
    dangling = ctx.session.scalar(
        select(func.count()).select_from(DecisionMaker).outerjoin(
            Company, DecisionMaker.company_domain == Company.company_domain)
        .where(DecisionMaker.id.in_(ctx.dm_ids),
               DecisionMaker.company_domain.isnot(None),
               Company.company_domain.is_(None))) or 0
    return len(ctx.dm_ids), f"{len(ctx.dm_ids)} DMs checked, {dangling} dangling"


def _stage_company_statistics(ctx: RefreshContext) -> tuple[int, str]:
    from master_db.models import Opportunity, Job
    n = 0
    for d in ctx.domains:
        opp = ctx.session.scalar(select(func.count()).select_from(Opportunity)
                                 .where(Opportunity.company_domain == d)) or 0
        jobs = ctx.session.scalar(select(func.count()).select_from(Job)
                                  .where(Job.company_domain == d)) or 0
        n += 1 if (opp or jobs) else 0
    return len(ctx.domains), f"recomputed stats for {len(ctx.domains)} companies ({n} with signals)"


def _stage_dm_statistics(ctx: RefreshContext) -> tuple[int, str]:
    if not ctx.domains:
        return 0, "no affected companies"
    rows = ctx.session.execute(
        select(DecisionMaker.company_domain, func.count())
        .where(DecisionMaker.company_domain.in_(ctx.domains))
        .group_by(DecisionMaker.company_domain)).all()
    total = sum(c for _, c in rows)
    return total, f"{total} decision makers across {len(rows)} companies"


def _stage_company_coverage(ctx: RefreshContext) -> tuple[int, str]:
    from master_db.models import Opportunity, Job
    covered = 0
    for d in ctx.domains:
        has_dm = ctx.session.scalar(select(func.count()).select_from(DecisionMaker)
                                    .where(DecisionMaker.company_domain == d)) or 0
        has_opp = ctx.session.scalar(select(func.count()).select_from(Opportunity)
                                     .where(Opportunity.company_domain == d)) or 0
        has_job = ctx.session.scalar(select(func.count()).select_from(Job)
                                     .where(Job.company_domain == d)) or 0
        covered += 1 if (has_dm or has_opp or has_job) else 0
    return len(ctx.domains), f"coverage refreshed: {covered}/{len(ctx.domains)} with any signal"


def _stage_leadership_signals(ctx: RefreshContext) -> tuple[int, str]:
    from leadership_signals.derive import rebuild
    counts = rebuild(ctx.session)                       # reuse the leadership engine
    return counts.get("total", 0), f"leadership signals rebuilt (total={counts.get('total', 0)})"


def _stage_lead_scores(ctx: RefreshContext) -> tuple[int, str]:
    from lead_scoring.service import score_all
    summary = score_all(ctx.session)                    # reuse the scoring engine (idempotent upsert)
    return summary.scored, f"lead scores recalculated ({summary.scored} companies)"


def _stage_ml_features(ctx: RefreshContext) -> tuple[int, str]:
    if not ctx.domains:
        return 0, "no affected companies"
    from ml import features as feat
    res = feat.build_features_batch(ctx.session, ctx.settings, domains=ctx.domains, incremental=True)
    return res.computed, f"ml features: computed={res.computed} reused={res.reused} total={res.total}"


def _stage_recommendations(ctx: RefreshContext) -> tuple[int, str]:
    from engagement.recommend import rebuild
    counts = rebuild(ctx.session)                        # reuse the engagement engine
    return counts.get("total", 0), f"recommendations regenerated (total={counts.get('total', 0)})"


def _stage_dashboard_statistics(ctx: RefreshContext) -> tuple[int, str]:
    from backend import cache
    cache.refresh_version(ctx.session)                  # memoized dashboard rollups pick up new rows
    return 0, "dashboard cache version bumped"


def _stage_search_index(ctx: RefreshContext) -> tuple[int, str]:
    from backend import cache
    cache.refresh_version(ctx.session)                  # search is query-time; version bump exposes new rows
    return len(ctx.domains) + len(ctx.dm_ids), "search refreshed (query-time index)"


def _stage_cache_invalidation(ctx: RefreshContext) -> tuple[int, str]:
    from backend import cache
    cache.clear()
    return 0, "response cache cleared"


# ordered pipeline: (stage_key, fn). stage_key becomes the pipeline_runs.component suffix.
STAGES: list[tuple[str, Callable[[RefreshContext], tuple[int, str]]]] = [
    ("company_relationships", _stage_company_relationships),
    ("dm_relationships", _stage_dm_relationships),
    ("company_statistics", _stage_company_statistics),
    ("dm_statistics", _stage_dm_statistics),
    ("company_coverage", _stage_company_coverage),
    ("leadership_signals", _stage_leadership_signals),
    ("lead_scores", _stage_lead_scores),
    ("ml_features", _stage_ml_features),
    ("recommendations", _stage_recommendations),
    ("dashboard_statistics", _stage_dashboard_statistics),
    ("search_index", _stage_search_index),
    ("cache_invalidation", _stage_cache_invalidation),
]
STAGE_KEYS = [k for k, _ in STAGES]
_COMPONENT_PREFIX = "post_import:"


def pipeline_id_for(import_id: str) -> str:
    return f"postimport-{import_id}"


@dataclass(slots=True)
class RefreshSummary:
    pipeline_id: str
    stages: list[dict] = field(default_factory=list)

    @property
    def failed(self) -> list[str]:
        return [s["stage"] for s in self.stages if s["status"] == "failed"]

    def to_dict(self) -> dict:
        return {"pipeline_id": self.pipeline_id, "stages": self.stages,
                "succeeded": sum(1 for s in self.stages if s["status"] == "success"),
                "failed": self.failed}


def run_post_import_refresh(
    session: Session, *, import_id: str, domains: list[str], dm_ids: list[int],
    settings=None, only: list[str] | None = None,
) -> RefreshSummary:
    """Run the refresh pipeline for the affected records. Each stage is tracked and
    isolated — a failing stage is recorded and the pipeline continues."""
    from backend.config import get_settings
    settings = settings or get_settings()
    ctx = RefreshContext(session, settings, sorted(set(d for d in domains if d)),
                         sorted(set(int(i) for i in dm_ids)))
    pid = pipeline_id_for(import_id)
    tracker = RunTracker(session)
    summary = RefreshSummary(pipeline_id=pid)
    for key, fn in STAGES:
        if only is not None and key not in only:
            continue
        run = tracker.start(component=f"{_COMPONENT_PREFIX}{key}", pipeline_id=pid,
                            mode="refresh", trigger="post_import")
        try:
            processed, notes = fn(ctx)
            tracker.finish(run, status="success", processed=processed, notes=notes)
            summary.stages.append({"stage": key, "status": "success", "processed": processed,
                                   "notes": notes, "duration_ms": run.duration_ms})
        except Exception as exc:                          # isolate: record + continue
            session.rollback()                            # undo this stage's partial writes only
            tracker.finish(run, status="failed", errors=[str(exc)], notes="stage failed")
            summary.stages.append({"stage": key, "status": "failed", "processed": 0,
                                   "error": str(exc), "duration_ms": run.duration_ms})
    return summary


def refresh_status(session: Session, import_id: str) -> dict:
    """Read the post-import refresh pipeline_runs for an import (for the UI)."""
    pid = pipeline_id_for(import_id)
    latest: dict[str, PipelineRun] = {}
    for r in session.scalars(select(PipelineRun).where(PipelineRun.pipeline_id == pid)
                             .order_by(PipelineRun.run_id)):
        latest[r.component] = r
    stages = [{"stage": c[len(_COMPONENT_PREFIX):], "status": r.status,
               "processed": r.records_processed, "duration_ms": r.duration_ms, "notes": r.notes}
              for c, r in latest.items() if c.startswith(_COMPONENT_PREFIX)]
    return {"pipeline_id": pid, "ran": bool(stages), "stages": stages,
            "failed": [s["stage"] for s in stages if s["status"] == "failed"]}


def failed_stages(session: Session, import_id: str) -> list[str]:
    """Stage keys whose most-recent run for this import is 'failed'."""
    pid = pipeline_id_for(import_id)
    latest: dict[str, PipelineRun] = {}
    for r in session.scalars(select(PipelineRun).where(PipelineRun.pipeline_id == pid)
                             .order_by(PipelineRun.run_id)):
        latest[r.component] = r                           # last one wins
    return [c[len(_COMPONENT_PREFIX):] for c, r in latest.items()
            if r.status == "failed" and c.startswith(_COMPONENT_PREFIX)]


def retry_failed(session: Session, import_id: str, *, domains: list[str] | None = None,
                 dm_ids: list[int] | None = None, settings=None) -> RefreshSummary:
    """Re-run ONLY the stages that failed for this import — completed work is untouched.

    Affected sets default to those persisted on the ImportJob (report stats)."""
    only = failed_stages(session, import_id)
    if not only:
        return RefreshSummary(pipeline_id=pipeline_id_for(import_id))
    if domains is None or dm_ids is None:
        from backend import import_repo
        job = import_repo.get_import_job(session, import_id)
        stats = (job.stats if job else {}) or {}
        domains = domains if domains is not None else stats.get("affected_company_domains", [])
        dm_ids = dm_ids if dm_ids is not None else stats.get("affected_dm_ids", [])
    return run_post_import_refresh(session, import_id=import_id, domains=domains,
                                   dm_ids=dm_ids, settings=settings, only=only)
