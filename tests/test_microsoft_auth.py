"""Microsoft Entra ID authentication: token verification failure handling, first
sign-in provisioning (pending / auto-active admin / auto-active super_admin
bootstrap), lifecycle gating on repeat sign-in, oid-vs-email lookup precedence and
backfill, and duplicate/concurrent first-sign-in safety. Approval/rejection/
disable/RBAC/audit are covered by tests/test_user_management.py and
tests/test_access_governance.py; this file only covers what's specific to the
Microsoft sign-in mechanism itself.
"""
import jwt
import pytest
from fastapi.testclient import TestClient

from backend import repositories as repo
from backend import security
from backend import services
from backend.config import Settings
from backend.main import create_app
from master_db.models import Base

DOMAIN = "siliconpatterns.com"


def _fake_verify(id_token: str, settings: Settings) -> dict:
    """A deterministic stand-in for security.verify_microsoft_id_token: treats the
    "id_token" as the email address itself and derives a stable oid from it, so
    repeated sign-ins for the same email present the same Microsoft identity."""
    if id_token == "BAD_TOKEN":
        raise jwt.InvalidTokenError("signature verification failed")
    if id_token == "NO_EMAIL_TOKEN":
        return {"oid": "oid-no-email", "name": "No Email Claim"}
    return {"email": id_token, "name": "Test User", "oid": f"oid-{id_token}"}


@pytest.fixture(autouse=True)
def _stub_microsoft_verification(monkeypatch):
    monkeypatch.setattr(security, "verify_microsoft_id_token", _fake_verify)


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'msauth.db').as_posix()}", log_json=False,
        jwt_secret="testsecret-please-change-32bytes!!",
        admin_emails_raw="boss@siliconpatterns.com",
        bootstrap_admin_email="rootadmin@siliconpatterns.com",
        api_key="unused-disables-bypass",
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        yield c


def _signin(c, email):
    return c.post("/auth/microsoft", json={"id_token": email})


# ------------------------------------------------------------------ token verification
def test_invalid_microsoft_token_is_rejected(client):
    r = _signin(client, "BAD_TOKEN")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "invalid_microsoft_token"


def test_token_without_email_claim_is_rejected(client):
    r = _signin(client, "NO_EMAIL_TOKEN")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "invalid_microsoft_token"


def test_external_domain_sign_in_rejected_server_side(client):
    c = client
    r = _signin(c, "someone@gmail.com")
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "forbidden_domain"
    with c.app.state.db.sessionmaker() as s:
        assert repo.get_user_by_email(s, "someone@gmail.com") is None


# ------------------------------------------------------------------ first sign-in provisioning
def test_first_sign_in_for_unknown_email_creates_pending(client):
    c = client
    r = _signin(c, "newperson@siliconpatterns.com")
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "account_pending"
    with c.app.state.db.sessionmaker() as s:
        user = repo.get_user_by_email(s, "newperson@siliconpatterns.com")
        assert user is not None and user.status == "pending" and user.role == "member"
        assert user.microsoft_oid == "oid-newperson@siliconpatterns.com"
        actions = {e.action for e in repo.list_user_audit(s)}
        assert "registered" in actions


def test_admin_email_first_sign_in_is_active_immediately(client):
    c = client
    r = _signin(c, "boss@siliconpatterns.com")
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "admin"
    assert r.json()["user"]["status"] == "active"


def test_bootstrap_email_first_sign_in_is_active_super_admin(client):
    c = client
    r = _signin(c, "rootadmin@siliconpatterns.com")
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "super_admin"
    assert r.json()["user"]["status"] == "active"
    with c.app.state.db.sessionmaker() as s:
        actions = {e.action for e in repo.list_user_audit(s)}
        assert "super_admin_bootstrap" in actions


def test_bootstrap_does_not_reverse_a_later_demotion(client):
    """Once the bootstrap email's row exists, a later sign-in must never re-elevate
    it — a deliberate demotion by another admin has to stick."""
    c = client
    _signin(c, "rootadmin@siliconpatterns.com")
    with c.app.state.db.sessionmaker() as s:
        user = repo.get_user_by_email(s, "rootadmin@siliconpatterns.com")
        repo.set_user_state(s, user, role="admin")
        s.commit()
    r = _signin(c, "rootadmin@siliconpatterns.com")
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "admin"  # NOT silently re-promoted to super_admin


def test_repeated_first_sign_in_before_approval_is_a_safe_no_op(client):
    """Signing in again while still pending must not create a duplicate row."""
    c = client
    _signin(c, "dup@siliconpatterns.com")
    _signin(c, "dup@siliconpatterns.com")
    with c.app.state.db.sessionmaker() as s:
        _, total = repo.list_users(s, q="dup@siliconpatterns.com", limit=10)
        assert total == 1


def test_concurrent_first_sign_in_race_does_not_crash_or_duplicate(client, monkeypatch):
    """A concurrent first-sign-in for the same email wins the UNIQUE(email) race --
    login_with_microsoft must recover by treating it as the safe no-op above."""
    c = client
    real_create_user = repo.create_user

    def _racing_create_user(session, **kwargs):
        real_create_user(session, **kwargs)
        session.commit()
        from sqlalchemy.exc import IntegrityError
        raise IntegrityError("insert", {}, Exception("UNIQUE constraint failed: users.email"))

    monkeypatch.setattr(repo, "create_user", _racing_create_user)
    r = _signin(c, "racer@siliconpatterns.com")
    assert r.status_code == 403  # still lands on the normal pending gate, not a 500
    with c.app.state.db.sessionmaker() as s:
        assert repo.list_users(s, q="racer", limit=10)[1] == 1


# ------------------------------------------------------------------ lifecycle gating on repeat sign-in
def test_pending_user_denied_on_repeat_sign_in(client):
    c = client
    _signin(c, "pending@siliconpatterns.com")
    r = _signin(c, "pending@siliconpatterns.com")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "account_pending"


def test_rejected_user_denied_and_audited(client):
    c = client
    _signin(c, "rejected@siliconpatterns.com")
    with c.app.state.db.sessionmaker() as s:
        repo.set_user_state(s, repo.get_user_by_email(s, "rejected@siliconpatterns.com"), status="rejected")
        s.commit()
    r = _signin(c, "rejected@siliconpatterns.com")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "account_rejected"
    with c.app.state.db.sessionmaker() as s:
        events = repo.list_user_audit(s)
        assert any(e.action == "denied" and "rejected" in e.detail for e in events)


def test_disabled_user_denied_and_audited(client):
    c = client
    _signin(c, "disabled@siliconpatterns.com")
    with c.app.state.db.sessionmaker() as s:
        u = repo.get_user_by_email(s, "disabled@siliconpatterns.com")
        repo.set_user_state(s, u, status="active")
        s.commit()
        repo.set_user_state(s, u, status="disabled")
        s.commit()
    r = _signin(c, "disabled@siliconpatterns.com")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "account_disabled"
    with c.app.state.db.sessionmaker() as s:
        events = repo.list_user_audit(s)
        assert any(e.action == "denied" and "disabled" in e.detail for e in events)


def test_deleted_user_denied(client):
    c = client
    _signin(c, "gone@siliconpatterns.com")
    with c.app.state.db.sessionmaker() as s:
        repo.set_user_state(s, repo.get_user_by_email(s, "gone@siliconpatterns.com"), status="deleted")
        s.commit()
    r = _signin(c, "gone@siliconpatterns.com")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "account_deleted"


def test_approved_user_second_sign_in_succeeds_and_increments_login_count(client):
    c = client
    _signin(c, "approved@siliconpatterns.com")
    with c.app.state.db.sessionmaker() as s:
        repo.set_user_state(s, repo.get_user_by_email(s, "approved@siliconpatterns.com"), status="active")
        s.commit()
    r1 = _signin(c, "approved@siliconpatterns.com")
    assert r1.status_code == 200
    n1 = r1.json()["user"]["login_count"]
    r2 = _signin(c, "approved@siliconpatterns.com")
    assert r2.json()["user"]["login_count"] == n1 + 1


# ------------------------------------------------------------------ oid lookup/backfill
def test_existing_password_era_account_is_recognized_by_email_and_backfilled(client):
    """An account created before this column existed (e.g. by the dev bypass or an
    older auth mechanism) must be recognized by email on its first Microsoft
    sign-in, not duplicated — and its microsoft_oid backfilled from that point on."""
    c = client
    with c.app.state.db.sessionmaker() as s:
        legacy = repo.create_user(s, email="legacy@siliconpatterns.com", role="manager", status="active")
        s.commit()
        legacy_id = legacy.id
    r = _signin(c, "legacy@siliconpatterns.com")
    assert r.status_code == 200
    assert r.json()["user"]["id"] == legacy_id
    assert r.json()["user"]["role"] == "manager"  # untouched
    with c.app.state.db.sessionmaker() as s:
        assert repo.get_user(s, legacy_id).microsoft_oid == "oid-legacy@siliconpatterns.com"
        _, total = repo.list_users(s, q="legacy@siliconpatterns.com", limit=10)
        assert total == 1  # no duplicate row


# ------------------------------------------------------------------ session
def test_session_persists_across_requests(client):
    c = client
    _signin(c, "persist@siliconpatterns.com")
    with c.app.state.db.sessionmaker() as s:
        repo.set_user_state(s, repo.get_user_by_email(s, "persist@siliconpatterns.com"), status="active")
        s.commit()
    token = _signin(c, "persist@siliconpatterns.com").json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert c.get("/auth/me", headers=headers).status_code == 200
    assert c.get("/auth/me", headers=headers).status_code == 200  # same token, second call


def test_user_never_returns_password_fields(client):
    c = client
    _signin(c, "boss@siliconpatterns.com")
    body = _signin(c, "boss@siliconpatterns.com").json()
    assert "password" not in body["user"] and "password_hash" not in body["user"]
    assert "must_change_password" not in body["user"]
