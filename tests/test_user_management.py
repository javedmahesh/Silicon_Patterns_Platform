"""Enterprise user management: approval workflow, roles, lifecycle, guards, audit.

Identity is Microsoft Entra ID; these tests drive the admin user-management API and
the account lifecycle on top of it.
"""
import pytest
from fastapi.testclient import TestClient

from backend import repositories as repo
from backend import security
from backend.config import Settings
from backend.main import create_app
from master_db.models import Base

DOMAIN = "siliconpatterns.com"


def _fake_verify(id_token: str, settings: Settings) -> dict:
    return {"email": id_token, "name": "Test User", "oid": f"oid-{id_token}"}


@pytest.fixture(autouse=True)
def _stub_microsoft_verification(monkeypatch):
    monkeypatch.setattr(security, "verify_microsoft_id_token", _fake_verify)


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'um.db').as_posix()}", log_json=False,
        jwt_secret="testsecret-please-change-32bytes!!",
        admin_emails_raw="boss@siliconpatterns.com",
        # A non-empty api_key (unused elsewhere in this file) turns the dev bypass
        # off (see security._bypass_on), so /companies etc. genuinely enforce real
        # Bearer-token validation instead of silently granting a synthetic identity.
        api_key="test-key-unused",
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        yield c


def _login(c, email):
    return c.post("/auth/microsoft", json={"id_token": email})


def _admin(c):
    """Sign in the seeded admin (auto-approved via admin_emails_raw) and return its
    auth header + id."""
    body = _login(c, "boss@siliconpatterns.com").json()
    return {"Authorization": f"Bearer {body['token']}"}, body["user"]["id"]


def _register(c, email):
    """First Microsoft sign-in for a not-yet-seen email — creates a pending account."""
    _login(c, email)
    with c.app.state.db.sessionmaker() as s:
        return repo.get_user_by_email(s, email).id


# ------------------------------------------------------------------ approval workflow
def test_pending_then_approve_grants_access(client):
    c = client
    AT, _ = _admin(c)
    uid = _register(c, "alice@siliconpatterns.com")
    # appears as pending to the admin
    users = c.get("/admin/users", headers=AT).json()["items"]
    assert next(u for u in users if u["id"] == uid)["status"] == "pending"
    # approve → active; alice can now obtain a session
    assert c.post(f"/admin/users/{uid}/approve", headers=AT).json()["status"] == "active"
    assert _login(c, "alice@siliconpatterns.com").status_code == 200


def test_reject_blocks_access(client):
    c = client
    AT, _ = _admin(c)
    uid = _register(c, "bob@siliconpatterns.com")
    assert c.post(f"/admin/users/{uid}/reject", headers=AT).json()["status"] == "rejected"
    r = _login(c, "bob@siliconpatterns.com")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "account_rejected"


def test_disable_revokes_session_immediately(client):
    c = client
    AT, _ = _admin(c)
    uid = _register(c, "carol@siliconpatterns.com")
    c.post(f"/admin/users/{uid}/approve", headers=AT)
    tok = _login(c, "carol@siliconpatterns.com").json()["token"]
    H = {"Authorization": f"Bearer {tok}"}
    assert c.get("/companies", headers=H).status_code == 200
    c.patch(f"/admin/users/{uid}", headers=AT, json={"is_active": False})   # disable
    assert c.get("/companies", headers=H).status_code == 401                # token now rejected
    assert _login(c, "carol@siliconpatterns.com").status_code == 403        # re-login blocked
    # re-enable restores access
    c.patch(f"/admin/users/{uid}", headers=AT, json={"is_active": True})
    assert _login(c, "carol@siliconpatterns.com").status_code == 200


# ------------------------------------------------------------------ roles
def test_promote_and_demote(client):
    c = client
    AT, _ = _admin(c)
    uid = _register(c, "dave@siliconpatterns.com")
    c.post(f"/admin/users/{uid}/approve", headers=AT)
    assert c.patch(f"/admin/users/{uid}", headers=AT, json={"role": "manager"}).json()["role"] == "manager"
    assert c.patch(f"/admin/users/{uid}", headers=AT, json={"role": "member"}).json()["role"] == "member"


def test_member_cannot_use_admin_api(client):
    c = client
    AT, _ = _admin(c)
    uid = _register(c, "eve@siliconpatterns.com")
    c.post(f"/admin/users/{uid}/approve", headers=AT)
    tok = _login(c, "eve@siliconpatterns.com").json()["token"]
    H = {"Authorization": f"Bearer {tok}"}
    assert c.get("/admin/users", headers=H).status_code == 403           # role gate, backend-enforced
    assert c.post(f"/admin/users/{uid}/approve", headers=H).status_code == 403


# ------------------------------------------------------------------ soft delete + guards
def test_soft_delete_anonymizes_and_keeps_row(client):
    c = client
    AT, _ = _admin(c)
    uid = _register(c, "frank@siliconpatterns.com")
    c.post(f"/admin/users/{uid}/approve", headers=AT)
    out = c.delete(f"/admin/users/{uid}", headers=AT).json()
    assert out["status"] == "deleted" and out["deleted_at"]
    assert "frank@siliconpatterns.com" not in out["email"] and out["full_name"] == ""
    # row retained (still listed), and the email is freed/anonymized
    with c.app.state.db.sessionmaker() as s:
        assert repo.get_user(s, uid) is not None
        assert repo.get_user_by_email(s, "frank@siliconpatterns.com") is None


def test_cannot_remove_last_admin_or_act_on_self(client):
    c = client
    AT, boss_id = _admin(c)
    assert c.delete(f"/admin/users/{boss_id}", headers=AT).status_code == 400        # self delete
    assert c.patch(f"/admin/users/{boss_id}", headers=AT,
                   json={"role": "member"}).status_code == 400                        # last admin demote
    assert c.patch(f"/admin/users/{boss_id}", headers=AT,
                   json={"is_active": False}).status_code == 400                       # last admin disable


# ------------------------------------------------------------------ login count + audit
def test_login_count_increments(client):
    c = client
    AT, _ = _admin(c)
    uid = _register(c, "grace@siliconpatterns.com")
    c.post(f"/admin/users/{uid}/approve", headers=AT)
    _login(c, "grace@siliconpatterns.com")
    n1 = next(u for u in c.get("/admin/users", headers=AT).json()["items"] if u["id"] == uid)["login_count"]
    _login(c, "grace@siliconpatterns.com")
    n2 = next(u for u in c.get("/admin/users", headers=AT).json()["items"] if u["id"] == uid)["login_count"]
    assert n2 == n1 + 1 and n1 >= 1


def test_audit_trail_records_actions(client):
    c = client
    AT, _ = _admin(c)
    uid = _register(c, "heidi@siliconpatterns.com")
    c.post(f"/admin/users/{uid}/approve", headers=AT)
    c.patch(f"/admin/users/{uid}", headers=AT, json={"role": "manager"})
    c.delete(f"/admin/users/{uid}", headers=AT)
    actions = [e["action"] for e in c.get("/admin/users/audit", headers=AT).json()]
    for expected in ("registered", "approved", "role_changed", "deleted"):
        assert expected in actions, f"missing audit action {expected} in {actions}"
