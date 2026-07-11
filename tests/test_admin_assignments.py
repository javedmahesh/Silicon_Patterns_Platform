"""Phase 2 RBAC + lead assignment + CRM, exercised via the dev role switcher (X-Dev-Role)."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company, LeadScore


def _seed(s):
    s.add_all([
        Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                name_key="acme", prospect_type="PRODUCT_COMPANY", validation_status="VALID"),
        Company(company_domain="globex.com", canonical_company_id="GLOBEX", company_name="Globex",
                name_key="globex", prospect_type="PRODUCT_COMPANY", validation_status="VALID"),
    ])
    s.flush()
    s.add_all([
        LeadScore(company_domain="acme.com", lead_score=80, grade="A", priority_rank=1, model_version="t"),
        LeadScore(company_domain="globex.com", lead_score=40, grade="B", priority_rank=2, model_version="t"),
    ])
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'crm.db').as_posix()}",
                              log_json=False, dev_auth_bypass=True))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def H(role):
    return {"X-Dev-Role": role}


def _uid(c, role):
    return c.get("/auth/me", headers=H(role)).json()["id"]


def test_member_restrictions_but_full_read(client):
    assert client.get("/admin/users", headers=H("member")).status_code == 403
    assert client.get("/assignments", headers=H("member")).status_code == 403
    assert client.get("/assignments/workload", headers=H("member")).status_code == 403
    # …yet members can read all intelligence (shared repository principle)
    assert client.get("/companies", headers=H("member")).status_code == 200
    assert client.get("/decision-makers", headers=H("member")).status_code == 200


def test_admin_user_management_soft_delete(client):
    for r in ("admin", "manager", "member"):
        client.get("/auth/me", headers=H(r))  # materialise the identities
    users = client.get("/admin/users", headers=H("admin")).json()["items"]
    assert len(users) >= 3
    member_id = _uid(client, "member")
    r = client.patch(f"/admin/users/{member_id}", json={"is_active": False}, headers=H("admin"))
    assert r.status_code == 200 and r.json()["is_active"] is False
    # Delete is a SOFT delete: status=deleted, PII scrubbed, but the row is retained
    # (never a hard delete) so audit/FK history stays intact.
    out = client.delete(f"/admin/users/{member_id}", headers=H("admin"))
    assert out.status_code == 200 and out.json()["status"] == "deleted"
    assert len(client.get("/admin/users", headers=H("admin")).json()["items"]) == len(users)


def test_manager_assignment_audit_and_workload(client):
    member_id = _uid(client, "member")
    created = client.post("/assignments",
                          json={"company_domain": "acme.com", "user_id": member_id, "status": "assigned",
                                "note": "Warm intro via VP Eng — prioritise this week."},
                          headers=H("manager"))
    assert created.status_code == 200
    aid = created.json()["id"]
    assert created.json()["company_name"] == "Acme" and created.json()["grade"] == "A"
    # the assigner's note + who-assigned-it attribution come back on the assignment
    assert created.json()["note"].startswith("Warm intro")
    assert created.json()["assigned_by_email"] == "betatestingmanager@siliconpatterns.com"

    # member sees it under /mine — with the note and who left it — and can update their own status
    mine = client.get("/assignments/mine", headers=H("member")).json()
    row = next(a for a in mine if a["id"] == aid)
    assert row["note"].startswith("Warm intro")
    assert row["assigned_by_email"] == "betatestingmanager@siliconpatterns.com"
    patched = client.patch(f"/assignments/{aid}", json={"status": "contacted"}, headers=H("member"))
    assert patched.json()["status"] == "contacted"
    # member cannot create assignments
    assert client.post("/assignments", json={"company_domain": "globex.com", "user_id": member_id},
                       headers=H("member")).status_code == 403

    # workload reflects the member's one lead
    wl = client.get("/assignments/workload", headers=H("manager")).json()
    assert any(u["user_id"] == member_id and u["total"] == 1 for u in wl["users"])

    # audit: activity timeline shows the assignment + the status change
    acts = client.get("/companies/acme.com/activity", headers=H("manager")).json()
    assert "assignment" in {a["kind"] for a in acts}
    assert "status changed" in {a["title"] for a in acts}

    assert client.delete(f"/assignments/{aid}", headers=H("manager")).status_code == 204


def test_company_notes_and_activity(client):
    r = client.post("/companies/acme.com/notes", json={"body": "Met at DAC; warm intro via VP Eng."},
                    headers=H("member"))
    assert r.status_code == 200 and r.json()["author_email"] == "betatestingmember@siliconpatterns.com"
    notes = client.get("/companies/acme.com/notes", headers=H("member")).json()
    assert len(notes) == 1
    assert any(a["kind"] == "note" for a in client.get("/companies/acme.com/activity", headers=H("member")).json())
