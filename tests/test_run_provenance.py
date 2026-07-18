"""Per-run, per-engine record provenance (migration 0053) + the drill-down service.

Covers the guarantees the Run Details drill-down depends on: exact capture, created-
vs-updated semantics, strict run isolation (no cross-run leakage), the bulk-ingest
path, and honest degradation for historical runs with no provenance.
"""
import pytest

import orchestrator.stages as stages
from backend import run_records
from master_db.local import make_session_factory
from master_db.models import Company, DemandSignal, RunEngineRecord
from orchestrator.orchestrator import Orchestrator

_INDUSTRY_HEADER = (
    "canonical_company_id,company_name,company_domain,website,country,city,headquarters,"
    "founded_year,region_flag,prospect_type,company_tier,company_status,company_category,"
    "technology_focus,linkedin_url,confidence_score,validation_status,source,source_type,"
    "discovery_date,last_updated\n"
)
_GROQ = ("GROQ,Groq,groq.com,https://groq.com,United States,Mountain View,Mountain View,2016,"
         "APPROVED,PRODUCT_COMPANY,SCALEUP,ACTIVE,AI Accelerators,Inference,"
         "https://www.linkedin.com/company/groq,90,VALID,seed,Curated,2026-01-01,2026-01-02\n")
_TENSTORRENT = ("TENSTORRENT,Tenstorrent,tenstorrent.com,https://tenstorrent.com,Canada,Toronto,Toronto,2016,"
                "APPROVED,PRODUCT_COMPANY,SCALEUP,ACTIVE,RISC-V,AI,"
                "https://www.linkedin.com/company/tenstorrent,85,VALID,portfolio,VC,2026-01-03,2026-01-04\n")

_JOBS_HEADER = "company_name,company_domain,job_title,job_url,location,job_category,technologies\n"
_JOB_ROW = "Groq,groq.com,RTL Design Engineer,https://groq.com/jobs/1,Remote,RTL,SystemVerilog\n"


@pytest.fixture()
def session():
    Session = make_session_factory(":memory:")
    with Session() as s:
        yield s


def _run_industry(session, src, monkeypatch, pipeline_id):
    monkeypatch.setattr(stages, "find_source", lambda key: src if key == "industry" else None)
    return Orchestrator(session).run_stage("industry", pipeline_id=pipeline_id)


def test_capture_created_then_updated(session, tmp_path, monkeypatch):
    run1 = tmp_path / "r1.csv"; run1.write_text(_INDUSTRY_HEADER + _GROQ, encoding="utf-8")
    _run_industry(session, run1, monkeypatch, "run-A")
    out = run_records.engine_records(session, "run-A", "industry", limit=50, offset=0)
    assert out.available and out.total == 1
    assert out.breakdown == {"created": 1}
    assert out.items[0].entity_id == "groq.com" and out.items[0].operation == "created"
    assert out.items[0].title == "Groq"                      # joined from the canonical row

    # Second run over the SAME company -> recorded as an update, isolated to run-B.
    run2 = tmp_path / "r2.csv"; run2.write_text(_INDUSTRY_HEADER + _GROQ, encoding="utf-8")
    _run_industry(session, run2, monkeypatch, "run-B")
    b = run_records.engine_records(session, "run-B", "industry", limit=50, offset=0)
    assert b.total == 1 and b.breakdown == {"updated": 1}
    assert b.items[0].operation == "updated"


def test_run_isolation_no_cross_leak(session, tmp_path, monkeypatch):
    """Run A discovered Groq; Run B discovered Groq (update) + Tenstorrent (new).
    Each run's drill-down must show ONLY its own records."""
    run1 = tmp_path / "r1.csv"; run1.write_text(_INDUSTRY_HEADER + _GROQ, encoding="utf-8")
    _run_industry(session, run1, monkeypatch, "run-A")
    run2 = tmp_path / "r2.csv"; run2.write_text(_INDUSTRY_HEADER + _GROQ + _TENSTORRENT, encoding="utf-8")
    _run_industry(session, run2, monkeypatch, "run-B")

    a = run_records.engine_records(session, "run-A", "industry", limit=50, offset=0)
    b = run_records.engine_records(session, "run-B", "industry", limit=50, offset=0)
    a_ids = {i.entity_id for i in a.items}
    b_ids = {i.entity_id for i in b.items}
    assert a_ids == {"groq.com"}                              # run A never sees tenstorrent
    assert b_ids == {"groq.com", "tenstorrent.com"}
    assert a.total == 1 and b.total == 2


def test_bulk_jobs_path_records_provenance(session, tmp_path, monkeypatch):
    session.add(Company(company_domain="groq.com", canonical_company_id="GROQ", company_name="Groq",
                        name_key="groq", company_tier="SCALEUP", prospect_type="PRODUCT_COMPANY",
                        compliance_flag="APPROVED", validation_status="VALID"))
    session.commit()
    jobs = tmp_path / "jobs.csv"; jobs.write_text(_JOBS_HEADER + _JOB_ROW, encoding="utf-8")
    monkeypatch.setattr(stages, "find_source", lambda key: jobs if key == "career_jobs" else None)
    Orchestrator(session).run_stage("career", pipeline_id="run-C")

    out = run_records.engine_records(session, "run-C", "career", limit=50, offset=0)
    assert out.total == 1 and out.items[0].entity_table == "jobs"
    assert out.items[0].operation == "created"
    assert out.items[0].title == "RTL Design Engineer"


def test_scoring_prev_new_detail(session, tmp_path, monkeypatch):
    session.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                        name_key="acme", company_tier="STARTUP", prospect_type="PRODUCT_COMPANY",
                        compliance_flag="APPROVED", validation_status="VALID"))
    session.add(DemandSignal(company_domain="acme.com", demand_score=90.0,
                             lead_readiness_score=70.0, total_engineering_jobs=30))
    session.commit()
    Orchestrator(session).run_stage("scoring", pipeline_id="run-S1")
    Orchestrator(session).run_stage("scoring", pipeline_id="run-S2")

    s2 = run_records.engine_records(session, "run-S2", "scoring", limit=50, offset=0)
    assert s2.total == 1
    d = s2.items[0].detail
    assert d["prev_score"] is not None                       # captured from the run-S1 write
    assert d["changed"] is False                             # identical inputs -> no change


def test_ad_hoc_stage_without_pipeline_id_is_not_tracked(session):
    """A single-stage run with no pipeline_id (not shown in Run History) skips capture."""
    session.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                        name_key="acme", company_tier="STARTUP", prospect_type="PRODUCT_COMPANY",
                        compliance_flag="APPROVED", validation_status="VALID"))
    session.commit()
    Orchestrator(session).run_stage("scoring")               # pipeline_id="" -> no recorder
    assert session.query(RunEngineRecord).count() == 0


def test_historical_run_degrades_gracefully(session):
    """A run with no provenance rows reports available=False (never fabricated)."""
    out = run_records.engine_records(session, "run-OLD", "industry", limit=50, offset=0)
    assert out.available is False and out.total == 0 and out.items == []
