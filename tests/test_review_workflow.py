"""P5.5: review-queue workflow endpoints (approve / merge / reject / alias + audit)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.config import Settings
from backend.main import create_app
from master_db.models import (
    Base, Company, CompanyAlias, Job, ResolutionReviewQueue,
)


def _company(domain, name, **kw):
    return Company(company_domain=domain, canonical_company_id=name.upper().replace(" ", ""),
                   company_name=name, name_key=name.lower(), **kw)


def _seed(s):
    s.add_all([
        _company("tenstorrent.com", "Tenstorrent", validation_status="VALID"),     # real (merge target)
        _company("tenstorent.com", "Tenstorent", is_stub=True, validation_status="STUB"),  # typo stub
        _company("newco.com", "NewCo", is_stub=True, validation_status="STUB"),     # approve
        _company("rejectme.com", "Reject Me", is_stub=True, validation_status="STUB"),  # reject
        _company("acme.com", "Acme", validation_status="VALID"),                    # alias target
    ])
    s.flush()
    s.add(Job(job_id="JOB-T1", company_domain="tenstorent.com", job_title="ASIC Engineer",
              job_url="https://tenstorent.com/j/1"))
    s.add_all([
        ResolutionReviewQueue(raw_name="Tenstorent", suggested_domain="tenstorent.com",
                              source_engine="career_jobs", match_type="NEW_STUB", status="pending"),  # id 1 merge
        ResolutionReviewQueue(raw_name="NewCo", suggested_domain="newco.com",
                              source_engine="blog", match_type="NEW_STUB", status="pending"),          # id 2 approve
        ResolutionReviewQueue(raw_name="Reject Me", suggested_domain="rejectme.com",
                              source_engine="career_jobs", match_type="NEW_STUB", status="pending"),   # id 3 reject
        ResolutionReviewQueue(raw_name="Mystery Co", suggested_domain="",
                              source_engine="linkedin", match_type="UNRESOLVED", status="pending"),    # id 4 alias
    ])
    s.commit()


@pytest.fixture()
def client(tmp_path):
    settings = Settings(database_url=f"sqlite:///{(tmp_path / 'rev.db').as_posix()}", log_json=False)
    app = create_app(settings)
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        c.app_db = app.state.db  # type: ignore[attr-defined]
        yield c


def _session(client):
    return client.app_db.sessionmaker()


def test_list_pending(client):
    body = client.get("/review-queue", params={"status": "pending"}).json()
    assert body["total"] == 4


def test_merge_moves_children_and_drops_stub(client):
    r = client.post("/review-queue/1/merge", json={"target_domain": "tenstorrent.com"})
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "merged" and out["moved"]["jobs"] == 1
    with _session(client) as s:
        assert s.get(Company, "tenstorent.com") is None                  # stub gone
        job = s.get(Job, "JOB-T1")
        assert job is not None and job.company_domain == "tenstorrent.com"  # re-pointed
    # audit trail recorded
    actions = client.get("/review-queue/1/actions").json()
    assert actions and actions[0]["action"] == "merge"
    # acting again is rejected
    assert client.post("/review-queue/1/merge", json={"target_domain": "tenstorrent.com"}).status_code == 409


def test_approve_confirms_company(client):
    r = client.post("/review-queue/2/approve")
    assert r.status_code == 200 and r.json()["status"] == "approved"
    with _session(client) as s:
        c = s.get(Company, "newco.com")
        assert c.is_stub is False and c.validation_status == "VALID"


def test_reject_marks_company(client):
    r = client.post("/review-queue/3/reject", json={"reason": "not a prospect"})
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    with _session(client) as s:
        assert s.get(Company, "rejectme.com").validation_status == "REJECTED"


def test_create_alias(client):
    r = client.post("/review-queue/4/alias", json={"name": "Mystery Co", "company_domain": "acme.com"})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    with _session(client) as s:
        n = s.scalar(select(func.count()).select_from(CompanyAlias)
                     .where(CompanyAlias.company_domain == "acme.com",
                            CompanyAlias.name_key == "mystery"))
        assert n == 1


def test_merge_guards_nonstub(client):
    # item 4 has no suggested_domain -> 400
    assert client.post("/review-queue/4/merge", json={"target_domain": "acme.com"}).status_code == 400
