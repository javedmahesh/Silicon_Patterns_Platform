"""Phase 4 — transactional historical import engine (apply the Phase 2/3 previews)."""
import openpyxl
import pytest
from fastapi.testclient import TestClient

from backend import import_engine, import_repo
from backend.config import Settings
from backend.import_engine import run_import
from backend.main import create_app
from integration.normalizer import name_key
from master_db.local import make_session_factory
from master_db.models import Base, Company, DecisionMaker, ImportJob
from sync import (HistoricalCompany, HistoricalDecisionMaker, reconcile_companies,
                  reconcile_decision_makers)
from sync.normalization import clear_caches


def _company(domain, nm, **over):
    b = dict(company_domain=domain, canonical_company_id=name_key(nm).upper().replace(" ", ""),
             company_name=nm, name_key=name_key(nm), validation_status="VALID")
    b.update(over)
    return Company(**b)


def _existing_dm():
    return DecisionMaker(linkedin_url="https://www.linkedin.com/in/lisa-su", company_domain="amd.com",
                         first_name="Lisa", last_name="Su", full_name="Lisa Su", current_title="CEO",
                         city="", match_score=99.0, agent_score=88.0, status="approved",
                         profile_data={"ai": "keep me"})


@pytest.fixture()
def session():
    clear_caches()
    Session = make_session_factory(":memory:")
    with Session() as s:
        s.add(_company("amd.com", "Advanced Micro Devices", industry_category=""))
        s.add(_existing_dm())
        s.commit()
        yield s


# historical batch: groq (new company + new DM), amd (fill industry), lisa (fill city), ghost (invalid)
def _co_records():
    return [HistoricalCompany(raw_name="Groq", website="https://groq.com",
                              fields={"company_name": "Groq", "industry_category": "AI"}, source_ref="c1"),
            HistoricalCompany(raw_name="AMD", website="https://amd.com",
                              fields={"industry_category": "Semiconductors"}, source_ref="c2")]


def _dm_records():
    return [
        HistoricalDecisionMaker(full_name="Lisa Su", company_name="AMD", company_website="amd.com",
                                linkedin_url="https://linkedin.com/in/lisa-su",
                                fields={"first_name": "Lisa", "last_name": "Su", "full_name": "Lisa Su",
                                        "city": "Austin", "current_title": "CEO"}, source_ref="d1"),
        HistoricalDecisionMaker(full_name="Jane New", company_name="Groq", company_website="groq.com",
                                linkedin_url="https://linkedin.com/in/jane-new",
                                fields={"first_name": "Jane", "last_name": "New", "full_name": "Jane New"},
                                source_ref="d2"),
        HistoricalDecisionMaker(full_name="Ghost", company_name="Groq", company_website="groq.com",
                                linkedin_url="", fields={"full_name": "Ghost"}, source_ref="d3"),
    ]


def _previews(s):
    return (reconcile_companies(s, _co_records()).to_dict(),
            reconcile_decision_makers(s, _dm_records()).to_dict())


def _job(s, cp, dp):
    job = ImportJob(import_id="job-x", status="previewed",
                    preview={"companies": cp, "decision_makers": dp}, total_records=0)
    s.add(job); s.commit()
    return job


# ------------------------------------------------------------- dry run
def test_dry_run_zero_writes(session):
    cp, dp = _previews(session)
    before_c, before_d = session.query(Company).count(), session.query(DecisionMaker).count()
    report = run_import(session, company_preview=cp, dm_preview=dp, commit=False)
    assert report.companies_created == 1 and report.decision_makers_created == 1
    assert report.invalid_skipped == 1
    assert session.query(Company).count() == before_c        # nothing written
    assert session.query(DecisionMaker).count() == before_d
    assert not session.new and not session.dirty


# ------------------------------------------------------------- commit
def test_commit_creates_updates_and_skips(session):
    cp, dp = _previews(session)
    job = _job(session, cp, dp)
    report = run_import(session, company_preview=cp, dm_preview=dp, commit=True, job=job)
    assert report.status == "completed"
    assert report.companies_created == 1 and report.companies_updated == 1
    assert report.decision_makers_created == 1 and report.decision_makers_updated == 1
    assert report.invalid_skipped == 1
    # rows really landed
    assert session.get(Company, "groq.com") is not None
    assert session.query(DecisionMaker).filter_by(full_name="Jane New").count() == 1
    # amd got its fill; jane's company FK is valid
    assert session.get(Company, "amd.com").industry_category == "Semiconductors"
    assert session.query(DecisionMaker).filter_by(full_name="Jane New").one().company_domain == "groq.com"
    # job lifecycle
    assert job.status == "completed" and job.progress_pct == 100 and job.current_stage == "done"
    assert job.records_processed == 4


def test_commit_preserves_existing_intelligence(session):
    cp, dp = _previews(session)
    run_import(session, company_preview=cp, dm_preview=dp, commit=True)
    lisa = session.query(DecisionMaker).filter_by(full_name="Lisa Su").one()
    assert lisa.match_score == 99.0 and lisa.agent_score == 88.0        # earned scores untouched
    assert lisa.status == "approved" and lisa.profile_data == {"ai": "keep me"}
    assert lisa.city == "Austin"                                        # only the empty owned field filled


def test_conflict_is_skipped_not_overwritten(session):
    # historical claims a different title for an existing DM -> conflict, never overwritten
    dm = [HistoricalDecisionMaker(full_name="Lisa Su", company_name="AMD", company_website="amd.com",
                                  linkedin_url="https://linkedin.com/in/lisa-su",
                                  fields={"full_name": "Lisa Su", "current_title": "CFO"}, source_ref="d1")]
    dp = reconcile_decision_makers(session, dm).to_dict()
    report = run_import(session, company_preview={"results": []}, dm_preview=dp, commit=True)
    assert report.conflicts_skipped == 1 and report.decision_makers_updated == 0
    assert session.query(DecisionMaker).filter_by(full_name="Lisa Su").one().current_title == "CEO"


# ------------------------------------------------------- rollback / failure
def test_force_rollback_leaves_no_writes(session):
    cp, dp = _previews(session)
    job = _job(session, cp, dp)
    before_c, before_d = session.query(Company).count(), session.query(DecisionMaker).count()
    report = run_import(session, company_preview=cp, dm_preview=dp, commit=True, job=job, force_rollback=True)
    assert report.status == "rolled_back"
    assert session.query(Company).count() == before_c and session.query(DecisionMaker).count() == before_d
    assert job.status == "rolled_back"


def test_failure_rolls_back_everything(session, monkeypatch):
    cp, dp = _previews(session)
    job = _job(session, cp, dp)
    before_c = session.query(Company).count()

    def boom(*a, **k):
        raise RuntimeError("relationship refresh failed")
    monkeypatch.setattr(import_engine, "_refresh_relationships", boom)

    report = run_import(session, company_preview=cp, dm_preview=dp, commit=True, job=job)
    assert report.status == "failed" and report.errors
    assert session.query(Company).count() == before_c            # groq creation rolled back
    assert session.get(Company, "groq.com") is None
    assert job.status == "failed" and "relationship refresh failed" in job.error_message


def test_idempotent_no_duplicates_on_replay(session):
    cp, dp = _previews(session)
    run_import(session, company_preview=cp, dm_preview=dp, commit=True)
    c1, d1 = session.query(Company).count(), session.query(DecisionMaker).count()
    # replay the SAME (now-stale) preview: guards must prevent duplicate rows
    report2 = run_import(session, company_preview=cp, dm_preview=dp, commit=True)
    assert report2.status == "completed"
    assert session.query(Company).count() == c1                  # no duplicate company
    assert session.query(DecisionMaker).count() == d1            # no duplicate DM
    assert report2.duplicates_skipped >= 1


# ------------------------------------------------------------- endpoint
def _write_xlsx(path):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Sales_Research_Master_v7"
    ws.append(["Company Name", "Company Website", "Contact First Name", "Contact Last Name",
               "Designation", "LinkedIn URL", "Email ID"])
    ws.append(["AMD", "https://amd.com", "Lisa", "Su", "CEO", "https://linkedin.com/in/lisa-su", ""])
    ws.append(["Groq", "https://groq.com", "Jane", "New", "VP", "https://linkedin.com/in/jane-new", ""])
    wb.save(path)


def test_import_endpoints_preview_then_commit(tmp_path):
    clear_caches()
    xl = tmp_path / "hist.xlsx"; _write_xlsx(xl)
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'imp.db').as_posix()}",
                              historical_import_path=str(xl), log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(_company("amd.com", "Advanced Micro Devices")); s.add(_existing_dm()); s.commit()
        # preview (manager)
        prev = c.post("/sync/imports/preview", headers={"X-Dev-Role": "manager"})
        assert prev.status_code == 200
        import_id = prev.json()["import_id"]
        # commit requires admin
        assert c.post(f"/sync/imports/{import_id}/commit", headers={"X-Dev-Role": "manager"}).status_code == 403
        # dry-run rehearsal writes nothing
        dry = c.post(f"/sync/imports/{import_id}/commit?dry_run=true", headers={"X-Dev-Role": "admin"})
        assert dry.status_code == 200 and dry.json()["status"] == "previewed"
        # Phase 5: nothing imports until approved
        c.post(f"/sync/imports/{import_id}/review/bulk", headers={"X-Dev-Role": "manager"},
               json={"action": "approve_all"})
        # real commit
        done = c.post(f"/sync/imports/{import_id}/commit", headers={"X-Dev-Role": "admin"})
        assert done.status_code == 200
        body = done.json()
        assert body["status"] == "completed" and body["decision_makers_created"] == 1
        # committing again is refused (not 'previewed' anymore)
        assert c.post(f"/sync/imports/{import_id}/commit", headers={"X-Dev-Role": "admin"}).status_code == 409
        with app.state.db.sessionmaker() as s:
            assert s.get(Company, "groq.com") is not None
        # Phase 7: the commit automatically fired the intelligence refresh (12 tracked stages)
        refresh = c.get(f"/sync/imports/{import_id}/refresh", headers={"X-Dev-Role": "manager"}).json()
        assert refresh["ran"] and len(refresh["stages"]) == 12
        assert c.post(f"/sync/imports/{import_id}/refresh/retry", headers={"X-Dev-Role": "manager"}).status_code == 403
