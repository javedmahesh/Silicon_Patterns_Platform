"""Tests for the P5 orchestrator: run tracking, idempotency, skip, health, resume."""
import pytest
from sqlalchemy import select

import orchestrator.stages as stages
from master_db.local import make_session_factory
from master_db.models import Company, DemandSignal, PipelineRun
from orchestrator.health import health_report
from orchestrator.orchestrator import Orchestrator


@pytest.fixture()
def session():
    Session = make_session_factory(":memory:")
    with Session() as s:
        s.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                      name_key="acme", company_tier="STARTUP", prospect_type="PRODUCT_COMPANY",
                      compliance_flag="APPROVED", validation_status="VALID"))
        s.add(DemandSignal(company_domain="acme.com", demand_score=90.0,
                           lead_readiness_score=70.0, total_engineering_jobs=30))
        s.commit()
        yield s


def test_scoring_stage_tracks_run(session):
    res = Orchestrator(session).run_stage("scoring")
    assert res.status == "success" and res.processed == 1 and res.created == 1
    run = session.scalars(select(PipelineRun).order_by(PipelineRun.run_id.desc())).first()
    assert run.component == "scoring" and run.status == "success"
    assert run.records_created == 1 and run.finished_at is not None and run.duration_ms >= 0


def test_scoring_is_idempotent(session):
    Orchestrator(session).run_stage("scoring")
    res2 = Orchestrator(session).run_stage("scoring")
    assert res2.created == 0 and res2.updated == 1          # re-scored in place, no new rows


_INDUSTRY_HEADER = (
    "canonical_company_id,company_name,company_domain,website,country,city,headquarters,"
    "founded_year,region_flag,prospect_type,company_tier,company_status,company_category,"
    "technology_focus,linkedin_url,confidence_score,validation_status,source,source_type,"
    "discovery_date,last_updated\n"
)
_GROQ_ROW = (
    "GROQ,Groq,groq.com,https://groq.com,United States,Mountain View,Mountain View,2016,"
    "APPROVED,PRODUCT_COMPANY,SCALEUP,ACTIVE,AI Accelerators,Inference,"
    "https://www.linkedin.com/company/groq,90,VALID,seed_list,Curated,2026-01-01,2026-01-02 09:00\n"
)
_TENSTORRENT_ROW = (
    "TENSTORRENT,Tenstorrent,tenstorrent.com,https://tenstorrent.com,Canada,Toronto,Toronto,2016,"
    "APPROVED,PRODUCT_COMPANY,SCALEUP,ACTIVE,RISC-V,AI;RISC-V,"
    "https://www.linkedin.com/company/tenstorrent,85,VALID,portfolio,VC,2026-01-03,2026-01-04 10:00\n"
)


def test_industry_stage_distinguishes_created_from_updated(session, tmp_path, monkeypatch):
    """Regression: re-running the industry stage over a source file that mixes an
    already-known domain with a genuinely new one must report created=1/updated=1,
    never created=0/updated=2 — i.e. resolution must not silently convert a new
    discovery into an update of something else."""
    import orchestrator.stages as stages

    run1 = tmp_path / "run1.csv"
    run1.write_text(_INDUSTRY_HEADER + _GROQ_ROW, encoding="utf-8")
    monkeypatch.setattr(stages, "find_source", lambda key: run1 if key == "industry" else None)
    res1 = Orchestrator(session).run_stage("industry")
    assert (res1.processed, res1.created, res1.updated) == (1, 1, 0)

    # Second file: groq.com already exists; tenstorrent.com is brand new.
    run2 = tmp_path / "run2.csv"
    run2.write_text(_INDUSTRY_HEADER + _GROQ_ROW + _TENSTORRENT_ROW, encoding="utf-8")
    monkeypatch.setattr(stages, "find_source", lambda key: run2 if key == "industry" else None)
    res2 = Orchestrator(session).run_stage("industry")
    assert (res2.processed, res2.created, res2.updated) == (2, 1, 1)


def test_agg_propagates_and_dedupes_stale_notes():
    """Regression: career_ingest() aggregates 3 sub-ingestors (jobs/demand/intel)
    via _agg(); it must not silently drop each sub-result's `notes` (as it did
    before), since that's the only place the stale-source signal from base.py's
    _stale_source_note() can surface for the career stage."""
    from integration.ingestors.base import IngestionResult
    from orchestrator.stages import _agg

    stale = "source unchanged since last ingest (x) - upstream engine likely not re-run"
    results = [
        IngestionResult(engine="career_jobs", rows_in=1, rows_upserted=1, notes=stale),
        IngestionResult(engine="career_demand", rows_in=1, rows_upserted=1, notes=""),
        IngestionResult(engine="career_intel", rows_in=1, rows_upserted=1, notes=stale),
    ]
    m = _agg(results)
    assert (m.rows_in, m.rows_upserted) == (3, 3)
    assert m.notes.count("source unchanged") == 1            # present, and de-duplicated


def test_stale_source_flagged_when_file_unchanged_since_last_ingest(session, tmp_path, monkeypatch):
    """Re-ingesting the exact same (untouched) file the upstream engine already
    produced must surface a clear note so a refresh-only pattern (engine never
    re-run) is diagnosable instead of looking identical to a healthy refresh."""
    import orchestrator.stages as stages

    src = tmp_path / "industry.csv"
    src.write_text(_INDUSTRY_HEADER + _GROQ_ROW, encoding="utf-8")
    monkeypatch.setattr(stages, "find_source", lambda key: src if key == "industry" else None)

    res1 = Orchestrator(session).run_stage("industry")
    assert "unchanged" not in res1.notes                     # first-ever ingest: nothing to compare to

    res2 = Orchestrator(session).run_stage("industry")        # same file, untouched on disk
    assert res2.created == 0 and res2.updated == 1
    assert "source unchanged since last ingest" in res2.notes
    assert "not re-run" in res2.notes


def test_single_component_runs_engine_before_ingest(session, monkeypatch):
    """run_engine=True makes a stage invoke its upstream engine (subprocess) BEFORE
    ingesting; run_engine=False goes straight to ingest. This is the switch the CLI
    now defaults ON for single-component runs (`run industry` crawls the latest
    universe, then ingests) — see orchestrator.cli._effective_run_engine."""
    import orchestrator.orchestrator as orch_mod
    import orchestrator.stages as stages

    # Keep the ingest half a fast no-op so the test targets the engine invocation.
    monkeypatch.setattr(stages, "find_source", lambda key: None)

    class _Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    engine_calls: list[tuple] = []

    def fake_run(cmd, **kwargs):
        engine_calls.append((list(cmd), str(kwargs.get("cwd"))))
        return _Proc()

    monkeypatch.setattr(orch_mod.subprocess, "run", fake_run)

    Orchestrator(session, run_engine=True).run_stage("industry")
    assert len(engine_calls) == 1, "run_engine=True must invoke the upstream engine first"
    cmd, cwd = engine_calls[0]
    assert "main.py" in cmd and "discover" in cmd          # the Industry Discovery engine
    assert "Industry_Discovery_Scraper_FINAL" in cwd        # ...at the updated engine's folder

    engine_calls.clear()
    Orchestrator(session, run_engine=False).run_stage("industry")
    assert engine_calls == [], "run_engine=False stays ingest-only (no engine subprocess)"


def test_engine_launch_oserror_is_a_clean_stage_failure(session, monkeypatch):
    """A subprocess launch OSError (e.g. WinError 267 'directory name is invalid'
    when the engine's working dir is unusable) must surface as a clean `failed`
    stage with a useful note — not an unhandled exception that bubbles up."""
    import orchestrator.orchestrator as orch_mod

    def boom(cmd, **kwargs):
        raise NotADirectoryError(267, "The directory name is invalid")

    monkeypatch.setattr(orch_mod.subprocess, "run", boom)

    res = Orchestrator(session, run_engine=True).run_stage("industry")
    assert res.status == "failed"
    assert "engine launch failed" in res.notes
    assert "Industry_Discovery_Scraper_FINAL" in res.notes  # names the offending cwd


def test_effective_run_engine_default_on_for_single_component():
    """The CLI default: an unspecified flag runs the engine for a single component
    but not for `run all`; an explicit flag always wins."""
    from orchestrator.cli import _effective_run_engine

    assert _effective_run_engine("industry", None) is True
    assert _effective_run_engine("blog", None) is True
    assert _effective_run_engine("all", None) is False       # `run all` stays ingest-only
    assert _effective_run_engine("industry", False) is False  # explicit opt-out wins
    assert _effective_run_engine("all", True) is True         # explicit opt-in wins


def test_decision_maker_intelligence_skips_without_credentials(session, monkeypatch):
    # Mock missing Apify credentials
    monkeypatch.setenv("APIFY_API_TOKEN", "")
    res = Orchestrator(session).run_stage("decision_maker_intelligence")
    assert res.status == "skipped" and "credentials" in res.notes.lower()
    run = session.scalars(select(PipelineRun).where(PipelineRun.component == "decision_maker_intelligence")).first()
    assert run.status == "skipped"


def test_health_report_reads_schedule(session):
    Orchestrator(session).run_stage("scoring")
    report = health_report(session)
    scoring = next(h for h in report if h["component"] == "scoring")
    assert scoring["last_status"] == "success"
    assert scoring["failed_runs"] == 0
    assert scoring["cadence"] == "daily"                    # from config/schedules.json
    assert scoring["next_scheduled_run"] not in ("on demand", "after first success")


def test_pipeline_grouping_and_resume(session, monkeypatch):
    # Mock missing Apify credentials
    monkeypatch.setenv("APIFY_API_TOKEN", "")
    # decision_maker_intelligence can still be run explicitly (it stays in STAGES);
    # it is simply no longer part of the AUTOMATIC pipeline (PIPELINE_ORDER).
    Orchestrator(session).run_pipeline(components=["scoring", "decision_maker_intelligence"])
    pids = {r.pipeline_id for r in session.scalars(select(PipelineRun)) if r.pipeline_id}
    assert pids and all(p.startswith("run-") for p in pids)
    # the manual DM stage was recorded (skipped without credentials)
    dm = session.scalars(
        select(PipelineRun).where(PipelineRun.component == "decision_maker_intelligence")
    ).first()
    assert dm is not None and dm.status == "skipped"

    # Resume only ever re-runs unfinished AUTOMATIC stages. decision_maker_intelligence
    # is manual-only (not in PIPELINE_ORDER), so resume never re-runs it — even though
    # it was skipped above. scoring succeeded, so there is nothing to resume.
    resumed = Orchestrator(session).run_pipeline(resume=True)
    assert [r.component for r in resumed] == []


def test_derive_status_no_false_green():
    """Regression: a failed/partial ingest must NOT be reported as success.

    Previously the orchestrator inferred status from rows_rejected alone, so an
    Apify fetch where every batch 400'd (0 rows, only errors) showed as 'success'.
    """
    from orchestrator.stages import IngestMetrics

    d = Orchestrator._derive_status
    # explicit failure from the ingestor wins (all batches failed, nothing fetched)
    assert d(IngestMetrics(rows_in=0, rows_upserted=0, status="failed",
                           errors=["batch 1 400", "batch 2 400"])) == "failed"
    # some batches failed but others ingested -> partial
    assert d(IngestMetrics(rows_upserted=5, status="partial", errors=["batch 2 400"])) == "partial"
    # no explicit hint: errors or rejected rows still degrade to partial
    assert d(IngestMetrics(rows_rejected=3)) == "partial"
    assert d(IngestMetrics(errors=["x"])) == "partial"
    # clean run is success
    assert d(IngestMetrics(rows_upserted=10)) == "success"


def test_company_limit_threads_to_decision_maker_intelligence_only(session, monkeypatch):
    """Orchestrator(company_limit=N) passes limit=N only to the
    decision_maker_intelligence stage; every other stage is invoked exactly as
    before (no extra kwarg), so benchmark mode can never change their behavior."""
    from orchestrator.stages import IngestMetrics, Stage

    calls = {}

    def fake_dm_ingest(s, *, limit=None):
        calls["dm_limit"] = limit
        return IngestMetrics(rows_in=0, rows_upserted=0)

    def fake_scoring_ingest(s):  # no limit kwarg accepted at all -- would TypeError if passed one
        calls["scoring_ran"] = True
        return IngestMetrics(rows_in=1, rows_upserted=1)

    monkeypatch.setitem(stages.STAGES, "decision_maker_intelligence",
                        Stage("decision_maker_intelligence", 4, [], fake_dm_ingest, None, "test"))
    monkeypatch.setitem(stages.STAGES, "scoring",
                        Stage("scoring", 5, [], fake_scoring_ingest, None, "test"))

    orch = Orchestrator(session, company_limit=7)
    orch.run_stage("decision_maker_intelligence")
    orch.run_stage("scoring")

    assert calls["dm_limit"] == 7
    assert calls["scoring_ran"] is True


def test_company_limit_none_is_byte_for_byte_production_call(session, monkeypatch):
    """company_limit=None (the default -- an ordinary `run all`/`run <component>`
    with no --limit) never passes a limit kwarg to decision_maker_intelligence
    either: the exact same call shape as before benchmark mode existed."""
    from orchestrator.stages import IngestMetrics, Stage

    calls = {}

    def fake_dm_ingest(s):  # no limit kwarg accepted -- proves nothing extra is passed
        calls["called"] = True
        return IngestMetrics(rows_in=0, rows_upserted=0)

    monkeypatch.setitem(stages.STAGES, "decision_maker_intelligence",
                        Stage("decision_maker_intelligence", 4, [], fake_dm_ingest, None, "test"))

    Orchestrator(session).run_stage("decision_maker_intelligence")  # company_limit defaults to None
    assert calls["called"] is True


def test_failed_ingest_recorded_as_failed(session, monkeypatch):
    """A stage whose ingest reports failure is tracked as 'failed' in pipeline_runs."""
    from orchestrator.stages import IngestMetrics, Stage

    def failing_ingest(_s):
        return IngestMetrics(rows_in=3, rows_upserted=0, status="failed", errors=["apify 400"])

    monkeypatch.setitem(stages.STAGES, "scoring",
                        Stage("scoring", 5, [], failing_ingest, None, "test-failed"))
    res = Orchestrator(session).run_stage("scoring")
    assert res.status == "failed"
    run = session.scalars(
        select(PipelineRun).where(PipelineRun.component == "scoring")
        .order_by(PipelineRun.run_id.desc())
    ).first()
    assert run.status == "failed" and run.error_count >= 1
