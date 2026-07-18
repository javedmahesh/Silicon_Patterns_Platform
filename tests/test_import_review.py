"""Phase 5 — import review & approval (states, field-level, conflicts, bulk, audit)."""
import openpyxl
import pytest
from fastapi.testclient import TestClient

from backend import import_repo, review_repo
from backend import sync_service as svc
from backend.config import Settings
from backend.main import create_app
from integration.normalizer import name_key
from master_db.local import make_session_factory
from master_db.models import (Base, Company, DecisionMaker, ImportReviewEvent, ImportReviewItem)
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
                         city="", match_score=99.0, status="approved", profile_data={"ai": "keep"})


@pytest.fixture()
def session():
    clear_caches()
    Session = make_session_factory(":memory:")
    with Session() as s:
        s.add(_company("amd.com", "Advanced Micro Devices", industry_category=""))
        s.add(_existing_dm())
        s.commit()
        yield s


def _co_records():
    return [HistoricalCompany(raw_name="Groq", website="https://groq.com",
                              fields={"company_name": "Groq", "industry_category": "AI"}, source_ref="c1"),
            HistoricalCompany(raw_name="AMD", website="https://amd.com",
                              fields={"industry_category": "Semiconductors"}, source_ref="c2")]


def _dm_records(lisa_title="CEO"):
    return [
        HistoricalDecisionMaker(full_name="Lisa Su", company_name="AMD", company_website="amd.com",
                                linkedin_url="https://linkedin.com/in/lisa-su",
                                fields={"full_name": "Lisa Su", "city": "Austin", "current_title": lisa_title},
                                source_ref="d1"),
        HistoricalDecisionMaker(full_name="Jane New", company_name="Groq", company_website="groq.com",
                                linkedin_url="https://linkedin.com/in/jane-new",
                                fields={"first_name": "Jane", "last_name": "New", "full_name": "Jane New"},
                                source_ref="d2"),
        HistoricalDecisionMaker(full_name="Ghost", company_name="Groq", company_website="groq.com",
                                linkedin_url="", fields={"full_name": "Ghost"}, source_ref="d3"),
    ]


def _previewed_job(session, lisa_title="CEO"):
    cp = reconcile_companies(session, _co_records()).to_dict()
    dp = reconcile_decision_makers(session, _dm_records(lisa_title)).to_dict()
    job = import_repo.record_import_job(
        session, source="historical_excel", filename="f.xlsx", initiated_by="a@b.c",
        status="previewed", preview={"companies": cp, "decision_makers": dp})
    review_repo.seed_review_items(session, job)
    return job


# --------------------------------------------------------------- seeding
def test_seed_gives_every_record_a_state(session):
    job = _previewed_job(session)
    items = session.query(ImportReviewItem).filter_by(job_id=job.id).all()
    by_cat = {i.category: i.state for i in items}
    assert by_cat["new_company"] == "pending" and by_cat["updated_company"] == "pending"
    assert by_cat["new_decision_maker"] == "pending" and by_cat["updated_decision_maker"] == "pending"
    assert by_cat["invalid"] == "skipped"           # invalid auto-skipped, still explicit


def test_states_persist(session):
    job = _previewed_job(session)
    review_repo.decide(session, job, kind="company", source_ref="c1", decision="approve", reviewer="r@x")
    again = review_repo._get_item(session, job, "company", "c1")
    assert again.state == "approved" and again.reviewer == "r@x" and again.decided_at is not None


# ------------------------------------------------- only approved imports
def test_nothing_imports_until_approved(session):
    job = _previewed_job(session)
    before = session.query(Company).count()
    report = svc.commit_import(session, job.import_id, commit=True)   # no approvals yet
    assert report.companies_created == 0 and report.decision_makers_created == 0
    assert session.query(Company).count() == before


def test_approved_import_and_rejected_never_imports(session):
    job = _previewed_job(session)
    review_repo.bulk(session, job, action="approve_all", reviewer="r@x")       # approve all pending
    review_repo.decide(session, job, kind="company", source_ref="c1", decision="reject", reviewer="r@x")  # reject Groq
    report = svc.commit_import(session, job.import_id, commit=True)
    assert report.decision_makers_created == 1                       # Jane imported
    assert session.get(Company, "groq.com") is None                 # rejected company never created
    assert session.query(DecisionMaker).filter_by(full_name="Jane New").count() == 1


# ----------------------------------------------------- field-level review
def test_field_keep_platform_excludes_the_change(session):
    job = _previewed_job(session)
    # AMD update would fill industry_category; reviewer keeps the (empty) platform value
    review_repo.resolve_field(session, job, kind="company", source_ref="c2",
                              field="industry_category", choice="keep_platform", reviewer="r@x")
    review_repo.decide(session, job, kind="company", source_ref="c2", decision="approve", reviewer="r@x")
    svc.commit_import(session, job.import_id, commit=True)
    assert session.get(Company, "amd.com").industry_category == ""   # not filled


def test_conflict_accept_historical_applies(session):
    job = _previewed_job(session, lisa_title="CFO")   # historical title conflicts with platform CEO
    item = review_repo._get_item(session, job, "decision_maker", "d1")
    assert item.category == "conflict" and item.state == "pending"
    review_repo.resolve_field(session, job, kind="decision_maker", source_ref="d1",
                              field="current_title", choice="accept_historical", reviewer="r@x")
    assert review_repo._get_item(session, job, "decision_maker", "d1").state == "resolved"
    svc.commit_import(session, job.import_id, commit=True)
    assert session.query(DecisionMaker).filter_by(full_name="Lisa Su").one().current_title == "CFO"


def test_conflict_keep_platform_preserves(session):
    job = _previewed_job(session, lisa_title="CFO")
    review_repo.resolve_field(session, job, kind="decision_maker", source_ref="d1",
                              field="current_title", choice="keep_platform", reviewer="r@x")
    assert review_repo._get_item(session, job, "decision_maker", "d1").state == "skipped"
    svc.commit_import(session, job.import_id, commit=True)
    assert session.query(DecisionMaker).filter_by(full_name="Lisa Su").one().current_title == "CEO"


# --------------------------------------------------------------- bulk + stats
def test_bulk_by_category(session):
    job = _previewed_job(session)
    n = review_repo.bulk(session, job, action="approve_category", category="new_company", reviewer="r@x")
    assert n == 1
    assert review_repo._get_item(session, job, "company", "c1").state == "approved"
    assert review_repo._get_item(session, job, "company", "c2").state == "pending"   # untouched


def test_statistics(session):
    job = _previewed_job(session)
    st = review_repo.statistics(session, job)
    assert st["total"] == 5 and st["pending"] == 4 and st["by_state"]["skipped"] == 1


# --------------------------------------------------------------- audit
def test_audit_trail_records_decisions(session):
    job = _previewed_job(session, lisa_title="CFO")
    review_repo.resolve_field(session, job, kind="decision_maker", source_ref="d1",
                              field="current_title", choice="accept_historical", reviewer="r@x", reason="verified")
    review_repo.decide(session, job, kind="company", source_ref="c1", decision="approve", reviewer="r@x")
    events = session.query(ImportReviewEvent).filter_by(job_id=job.id).all()
    actions = {e.action for e in events}
    assert "resolve_field" in actions and "approve" in actions
    fld = next(e for e in events if e.action == "resolve_field")
    assert fld.previous_value == "CEO" and fld.approved_value == "CFO" and fld.reviewer == "r@x"


# --------------------------------------------------------------- endpoints
def _write_xlsx(path):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Sales_Research_Master_v7"
    ws.append(["Company Name", "Company Website", "Contact First Name", "Contact Last Name",
               "Designation", "LinkedIn URL"])
    ws.append(["AMD", "https://amd.com", "Lisa", "Su", "CFO", "https://linkedin.com/in/lisa-su"])
    ws.append(["Groq", "https://groq.com", "Jane", "New", "VP", "https://linkedin.com/in/jane-new"])
    wb.save(path)


def test_review_endpoints(tmp_path):
    clear_caches()
    xl = tmp_path / "hist.xlsx"; _write_xlsx(xl)
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'rev.db').as_posix()}",
                              historical_import_path=str(xl), log_json=False))
    mgr = {"X-Dev-Role": "manager"}
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(_company("amd.com", "Advanced Micro Devices")); s.add(_existing_dm()); s.commit()
        iid = c.post("/sync/imports/preview", headers=mgr).json()["import_id"]
        # review list has field diffs; a conflict is present (Lisa CFO vs CEO)
        review = c.get(f"/sync/imports/{iid}/review", headers=mgr).json()
        assert review["items"] and any(i["category"] == "conflict" for i in review["items"])
        # resolve the conflict field, approve the new records, check stats + audit
        c.post(f"/sync/imports/{iid}/review/resolve", headers=mgr,
               json={"kind": "decision_maker", "source_ref": "row 2", "field": "current_title",
                     "choice": "accept_historical"})
        c.post(f"/sync/imports/{iid}/review/bulk", headers=mgr, json={"action": "approve_all"})
        stats = c.get(f"/sync/imports/{iid}/review/stats", headers=mgr).json()
        assert stats["importable"] >= 1
        audit = c.get(f"/sync/imports/{iid}/review/audit", headers=mgr).json()["events"]
        assert any(e["action"] == "resolve_field" for e in audit)
        # commit applies only approved/resolved
        done = c.post(f"/sync/imports/{iid}/commit", headers={"X-Dev-Role": "admin"}).json()
        assert done["status"] == "completed"
