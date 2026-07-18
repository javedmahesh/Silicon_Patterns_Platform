"""Phase 3 — decision-maker synchronization engine (read-only) + import-job infra."""
import openpyxl
import pytest
from fastapi.testclient import TestClient

from backend import import_repo
from backend.config import Settings
from backend.main import create_app
from integration.normalizer import name_key
from master_db.local import make_session_factory
from master_db.models import Base, Company, DecisionMaker, ImportJob
from sync import HistoricalDecisionMaker, canonical_linkedin_url, reconcile_decision_makers
from sync.normalization import DM_PRESERVED_FIELDS, clear_caches


def _company(domain, nm):
    return Company(company_domain=domain, canonical_company_id=name_key(nm).upper().replace(" ", ""),
                   company_name=nm, name_key=name_key(nm), validation_status="VALID")


def _dm(**over):
    base = dict(linkedin_url="https://www.linkedin.com/in/lisa-su", company_domain="amd.com",
                first_name="Lisa", last_name="Su", full_name="Lisa Su", current_title="CEO",
                seniority="CxO", work_email="lisa.su@amd.com", match_score=99.0, agent_score=88.0,
                status="approved", profile_data={"ai": "keep me"})
    base.update(over)
    return DecisionMaker(**base)


@pytest.fixture()
def session():
    clear_caches()
    Session = make_session_factory(":memory:")
    with Session() as s:
        s.add(_company("amd.com", "Advanced Micro Devices"))
        s.add(_company("groq.com", "Groq"))
        s.add(_dm())
        s.commit()
        yield s


def _rec(full_name, *, company="", website="", linkedin="", email="", **fields):
    return HistoricalDecisionMaker(full_name=full_name, company_name=company, company_website=website,
                                   linkedin_url=linkedin, work_email=email, fields=dict(fields),
                                   source_ref=f"row:{full_name}:{linkedin or email}")


# ----------------------------------------------- LinkedIn canonicalization
@pytest.mark.parametrize("url", [
    "https://www.linkedin.com/in/lisa-su",
    "http://linkedin.com/in/lisa-su/",
    "https://m.linkedin.com/in/lisa-su",
    "https://www.linkedin.com/in/lisa-su/?locale=en_US&trk=x",
    "https://de.linkedin.com/in/lisa-su/en",
    "linkedin.com/in/Lisa-Su/",
])
def test_linkedin_canonicalization_equivalence(url):
    assert canonical_linkedin_url(url) == "linkedin.com/in/lisa-su"


def test_linkedin_non_profile_is_empty():
    assert canonical_linkedin_url("https://example.com/in/x") == ""
    assert canonical_linkedin_url("") == ""


# ----------------------------------------------------------- matching
def test_match_by_linkedin_differing_format(session):
    p = reconcile_decision_makers(session, [_rec("Lisa Su", linkedin="http://linkedin.com/in/lisa-su/?trk=1",
                                                 company="AMD", website="amd.com")])
    r = p.results[0]
    assert r.match_type == "LINKEDIN_URL" and r.matched_dm_id is not None
    assert r.classification in ("unchanged", "update")


def test_match_by_email_when_no_linkedin(session):
    p = reconcile_decision_makers(session, [_rec("Lisa Su", email="LISA.SU@amd.com", company="AMD", website="amd.com")])
    assert p.results[0].match_type == "WORK_EMAIL" and p.results[0].matched_dm_id is not None


def test_match_by_company_and_name(session):
    p = reconcile_decision_makers(session, [_rec("Lisa  Su", company="AMD", website="https://amd.com")])
    assert p.results[0].match_type == "COMPANY_NAME" and p.results[0].resolved_company_domain == "amd.com"


def test_new_decision_maker(session):
    p = reconcile_decision_makers(session, [_rec("Jane New", linkedin="https://linkedin.com/in/jane-new",
                                                 company="Groq", website="https://groq.com")])
    r = p.results[0]
    assert r.classification == "new" and r.resolved_company_domain == "groq.com"


def test_invalid_without_linkedin_or_match(session):
    # no linkedin, no email, and no existing (company,name) match -> cannot create
    p = reconcile_decision_makers(session, [_rec("Ghost Person", company="Groq", website="https://groq.com")])
    assert p.results[0].classification == "invalid" and p.results[0].match_type == "INVALID"


# ------------------------------------------------------- update rules
def test_fill_missing_only(session):
    # existing Lisa Su has no city; historical adds one -> fill. Title equal -> no change.
    p = reconcile_decision_makers(session, [_rec("Lisa Su", linkedin="https://linkedin.com/in/lisa-su",
                                                 company="AMD", website="amd.com", city="Santa Clara",
                                                 current_title="CEO")])
    r = p.results[0]
    assert r.classification == "update"
    assert [(c.field, c.action) for c in r.changes] == [("city", "fill")]


def test_conflict_never_overwrites(session):
    # different title on an existing DM -> conflict, platform value preserved in report
    p = reconcile_decision_makers(session, [_rec("Lisa Su", linkedin="https://linkedin.com/in/lisa-su",
                                                 company="AMD", website="amd.com", current_title="CFO")])
    r = p.results[0]
    assert r.classification == "conflict"
    assert r.conflicts[0].field == "current_title" and r.conflicts[0].current == "CEO"


def test_never_touches_preserved_fields(session):
    p = reconcile_decision_makers(session, [_rec("Lisa Su", linkedin="https://linkedin.com/in/lisa-su",
                                                 company="AMD", website="amd.com", city="Austin",
                                                 work_phone="512-1", seniority="VP")])
    for r in p.results:
        for ch in r.changes + r.conflicts:
            assert ch.field not in DM_PRESERVED_FIELDS


# --------------------------------------------------- duplicates / conflicts
def test_duplicate_same_person_within_batch(session):
    recs = [_rec("Jane New", linkedin="https://linkedin.com/in/jane-new"),
            _rec("Jane  New ", linkedin="http://www.linkedin.com/in/jane-new/")]
    p = reconcile_decision_makers(session, recs)
    assert sorted(r.classification for r in p.results) == ["duplicate", "new"]
    assert p.stats.duplicates == 1


def test_conflicting_identity_same_url_different_person(session):
    recs = [_rec("Alice Alpha", linkedin="https://linkedin.com/in/shared-x"),
            _rec("Bob Beta", linkedin="https://linkedin.com/in/shared-x")]
    p = reconcile_decision_makers(session, recs)
    classes = sorted(r.classification for r in p.results)
    assert "conflict" in classes and p.stats.conflicts == 1   # not silently merged


def test_conflict_url_matches_different_platform_person(session):
    # historical LinkedIn matches Lisa Su's URL but names a different person
    p = reconcile_decision_makers(session, [_rec("Someone Else", linkedin="https://linkedin.com/in/lisa-su",
                                                 company="AMD", website="amd.com")])
    r = p.results[0]
    assert r.classification == "conflict" and "different platform person" in r.notes


# ----------------------------------------------------- invariants
def test_reconcile_is_read_only(session):
    before = session.query(DecisionMaker).count()
    reconcile_decision_makers(session, [_rec("Jane New", linkedin="https://linkedin.com/in/jane-new"),
                                        _rec("Lisa Su", linkedin="https://linkedin.com/in/lisa-su",
                                             company="AMD", website="amd.com")])
    assert session.query(DecisionMaker).count() == before
    assert session.query(ImportJob).count() == 0
    assert not session.new and not session.dirty


def test_deterministic(session):
    recs = [_rec("Jane New", linkedin="https://linkedin.com/in/jane-new", company="Groq", website="groq.com"),
            _rec("Lisa Su", linkedin="https://linkedin.com/in/lisa-su", company="AMD", website="amd.com"),
            _rec("Ghost", company="Groq", website="groq.com")]
    a = reconcile_decision_makers(session, list(recs)).to_dict()
    b = reconcile_decision_makers(session, list(reversed(recs))).to_dict()
    a["generated_at"] = b["generated_at"] = ""
    assert a == b


# ----------------------------------------------------- import job infra
def test_import_job_repo(session):
    job = import_repo.record_import_job(session, source="historical_excel", filename="f.xlsx",
                                        initiated_by="a@b.c", decision_makers_processed=10, created=7,
                                        conflicts=1, stats={"x": 1})
    assert job.import_id and job.status == "previewed"
    assert import_repo.get_import_job(session, job.import_id).created_count == 7
    assert len(import_repo.list_import_jobs(session)) == 1


# ----------------------------------------------------- excel + endpoint
def _write_xlsx(path):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Sales_Research_Master_v7"
    ws.append(["Region", "Company Name", "Company Website", "Contact First Name", "Contact Last Name",
               "Designation", "Seniority Level", "LinkedIn URL", "Email ID"])
    ws.append(["US", "AMD", "https://amd.com", "Lisa", "Su", "CEO", "CxO",
               "https://www.linkedin.com/in/lisa-su/", "lisa.su@amd.com"])   # matches existing
    ws.append(["US", "Groq", "https://groq.com", "Jane", "New", "VP Eng", "VP",
               "https://linkedin.com/in/jane-new", ""])                       # new
    ws.append(["US", "Groq", "https://groq.com", "No", "Linkedin", "Eng", "IC", "", ""])  # invalid
    wb.save(path)


def test_dm_preview_endpoint_and_import_job(tmp_path):
    clear_caches()
    xl = tmp_path / "hist.xlsx"; _write_xlsx(xl)
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'dm.db').as_posix()}",
                              historical_import_path=str(xl), log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(_company("amd.com", "Advanced Micro Devices")); s.add(_company("groq.com", "Groq"))
            s.add(_dm()); s.commit()
        assert c.post("/sync/decision-makers/preview", headers={"X-Dev-Role": "member"}).status_code == 403
        resp = c.post("/sync/decision-makers/preview", headers={"X-Dev-Role": "manager"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["stats"]["total_input"] == 3
        assert body["stats"]["new"] == 1 and body["stats"]["invalid"] == 1
        assert body["import_id"]
        # the import job was recorded and is listable
        listed = c.get("/sync/imports", headers={"X-Dev-Role": "manager"}).json()["items"]
        assert listed and listed[0]["import_id"] == body["import_id"]
        assert listed[0]["decision_makers_processed"] == 3
