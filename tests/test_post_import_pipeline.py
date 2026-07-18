"""Phase 7 — post-import intelligence refresh pipeline (trigger, stages, tracking, recovery)."""
import pytest

from backend.import_engine import run_import
from backend.post_import_pipeline import (STAGE_KEYS, failed_stages, retry_failed,
                                          run_post_import_refresh)
from integration.normalizer import name_key
from master_db.local import make_session_factory
from master_db.models import (Company, DecisionMaker, LeadScore, MlFeatureRow, PipelineRun)
from sync import HistoricalCompany, reconcile_companies
from sync.normalization import clear_caches


def _company(domain, nm):
    return Company(company_domain=domain, canonical_company_id=name_key(nm).upper().replace(" ", ""),
                   company_name=nm, name_key=name_key(nm), validation_status="VALID")


@pytest.fixture()
def session():
    clear_caches()
    Session = make_session_factory(":memory:")
    with Session() as s:
        s.add(_company("amd.com", "Advanced Micro Devices"))
        s.add(_company("other.com", "Other Co"))
        s.add(DecisionMaker(linkedin_url="https://linkedin.com/in/lisa-su", company_domain="amd.com",
                            full_name="Lisa Su", first_name="Lisa", last_name="Su"))
        s.commit()
        yield s


def _dm_id(s):
    return s.query(DecisionMaker).one().id


# ------------------------------------------------------- full pipeline
def test_pipeline_runs_all_twelve_stages(session):
    summary = run_post_import_refresh(session, import_id="imp1",
                                      domains=["amd.com", "other.com"], dm_ids=[_dm_id(session)])
    assert summary.failed == [], summary.failed
    assert [s["stage"] for s in summary.stages] == STAGE_KEYS       # order preserved
    # imported companies received lead scores + ML features (intelligence integration)
    assert session.query(LeadScore).filter_by(company_domain="amd.com").count() == 1
    assert session.query(MlFeatureRow).filter_by(entity_id="amd.com").count() == 1
    # every stage recorded in pipeline_runs under one post-import pipeline
    runs = session.query(PipelineRun).filter_by(trigger="post_import").all()
    assert len(runs) == 12 and all(r.status == "success" for r in runs)
    assert {r.component for r in runs} == {f"post_import:{k}" for k in STAGE_KEYS}
    assert all(r.pipeline_id == "postimport-imp1" for r in runs)


def test_ml_features_are_incremental(session):
    # only the affected domain gets features; an untouched company does not
    run_post_import_refresh(session, import_id="imp2", domains=["amd.com"], dm_ids=[])
    assert session.query(MlFeatureRow).filter_by(entity_id="amd.com").count() == 1
    assert session.query(MlFeatureRow).filter_by(entity_id="other.com").count() == 0


# ------------------------------------------------------- failure recovery
def test_failure_isolates_and_retries(session, monkeypatch):
    import lead_scoring.service as ls

    def boom(*a, **k):
        raise RuntimeError("scoring boom")
    monkeypatch.setattr(ls, "score_all", boom)

    summary = run_post_import_refresh(session, import_id="imp3", domains=["amd.com"], dm_ids=[])
    assert "lead_scores" in summary.failed
    # independent stages still ran to completion
    assert any(s["stage"] == "ml_features" and s["status"] == "success" for s in summary.stages)
    assert failed_stages(session, "imp3") == ["lead_scores"]

    monkeypatch.undo()                                   # fix the underlying engine
    retry = retry_failed(session, "imp3", domains=["amd.com"], dm_ids=[])
    assert retry.failed == [] and [s["stage"] for s in retry.stages] == ["lead_scores"]
    assert failed_stages(session, "imp3") == []          # completed work not invalidated


# ------------------------------------------------------- trigger gating
def _groq_preview(session):
    return reconcile_companies(session, [HistoricalCompany(
        raw_name="Groq", website="https://groq.com",
        fields={"company_name": "Groq"}, source_ref="c1")]).to_dict()


def test_commit_with_refresh_triggers_pipeline(session):
    run_import(session, company_preview=_groq_preview(session), dm_preview={"results": []},
               commit=True, refresh=True)
    assert session.query(PipelineRun).filter_by(trigger="post_import").count() == 12
    assert session.get(Company, "groq.com") is not None
    assert session.query(LeadScore).filter_by(company_domain="groq.com").count() == 1


def test_refresh_false_does_not_trigger(session):
    run_import(session, company_preview=_groq_preview(session), dm_preview={"results": []},
               commit=True, refresh=False)
    assert session.query(PipelineRun).filter_by(trigger="post_import").count() == 0


def test_dry_run_never_triggers(session):
    run_import(session, company_preview=_groq_preview(session), dm_preview={"results": []},
               commit=False, refresh=True)
    assert session.query(PipelineRun).filter_by(trigger="post_import").count() == 0
    assert session.get(Company, "groq.com") is None      # dry run wrote nothing
