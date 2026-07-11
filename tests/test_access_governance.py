"""Enterprise User Approval & Access Governance: the initial administrator
bootstrap (the bootstrap email's first Microsoft sign-in), its
overwrite-safe/concurrency-safe guarantees, the super_admin RBAC tier
(self-promotion / privilege-escalation / last-active-super_admin protection),
denial auditing, user search/filter/pagination, and production-readiness checks.

Approve/reject/disable/promote/demote/soft-delete/last-*admin*-protection at the
"admin" tier are already covered by tests/test_user_management.py — this file only
covers what's new for "super_admin" on top of that.
"""
import threading

import pytest
from fastapi.testclient import TestClient

from backend import repositories as repo
from backend import security
from backend import services
from backend.config import Settings
from backend.main import create_app
from master_db.models import Base

DOMAIN = "siliconpatterns.com"
BOSS = "boss@siliconpatterns.com"


def _fake_verify(id_token: str, settings: Settings) -> dict:
    return {"email": id_token, "name": "Test User", "oid": f"oid-{id_token}"}


@pytest.fixture(autouse=True)
def _stub_microsoft_verification(monkeypatch):
    monkeypatch.setattr(security, "verify_microsoft_id_token", _fake_verify)


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'gov.db').as_posix()}", log_json=False,
        jwt_secret="testsecret-please-change-32bytes!!",
        admin_emails_raw=BOSS,
        bootstrap_admin_email=BOSS,
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        yield c


def _login_headers(c, email):
    body = c.post("/auth/microsoft", json={"id_token": email}).json()
    return {"Authorization": f"Bearer {body['token']}"}


def _boss(c):
    """Sign in as the bootstrapped super_admin (immediately active — no
    password/change-password step) and return its auth header + id."""
    login = c.post("/auth/microsoft", json={"id_token": BOSS}).json()
    return {"Authorization": f"Bearer {login['token']}"}, login["user"]["id"]


def _register_active(c, email, role="member"):
    """First Microsoft sign-in + admin-approve a plain account, returning its id."""
    c.post("/auth/microsoft", json={"id_token": email})
    with c.app.state.db.sessionmaker() as s:
        u = repo.get_user_by_email(s, email)
        u.status, u.is_active, u.role = "active", True, role
        s.commit()
        return u.id


# ------------------------------------------------------------------ bootstrap
def test_bootstrap_creates_active_super_admin_on_first_sign_in(client):
    c = client
    r = c.post("/auth/microsoft", json={"id_token": BOSS})
    assert r.status_code == 200
    with c.app.state.db.sessionmaker() as s:
        user = repo.get_user_by_email(s, BOSS)
        assert user is not None and user.role == "super_admin" and user.status == "active"
        actions = {e.action for e in repo.list_user_audit(s)}
        assert "super_admin_bootstrap" in actions


def test_bootstrap_does_not_reverse_a_later_demotion(client):
    c = client
    AT, boss_id = _boss(c)
    other_id = _register_active(c, "second@siliconpatterns.com", role="admin")
    OT = _login_headers(c, "second@siliconpatterns.com")
    # promote the second admin to super_admin so boss is no longer the *only* one,
    # then demote boss — a deliberate, later governance action.
    c.patch(f"/admin/users/{other_id}", headers=AT, json={"role": "super_admin"})
    r = c.patch(f"/admin/users/{boss_id}", headers=OT, json={"role": "admin"})
    assert r.status_code == 200 and r.json()["role"] == "admin"
    # boss signs in again — must NOT be silently re-promoted back to super_admin.
    r2 = c.post("/auth/microsoft", json={"id_token": BOSS})
    assert r2.json()["user"]["role"] == "admin"
    with c.app.state.db.sessionmaker() as s:
        assert repo.get_user_by_email(s, BOSS).role == "admin"


def test_no_bootstrap_email_configured_means_no_automatic_super_admin(tmp_path):
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'nogov.db').as_posix()}", log_json=False,
        jwt_secret="testsecret-please-change-32bytes!!",
        bootstrap_admin_email="",
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with c.app.state.db.sessionmaker() as s:
            import backend.security as sec
            from unittest.mock import patch
            with patch.object(sec, "verify_microsoft_id_token", _fake_verify):
                c.post("/auth/microsoft", json={"id_token": "admin@siliconpatterns.com"})
        with c.app.state.db.sessionmaker() as s:
            user = repo.get_user_by_email(s, "admin@siliconpatterns.com")
            assert user is not None and user.role == "member" and user.status == "pending"


def test_bootstrap_does_not_overwrite_an_existing_administrator(client):
    """If the configured bootstrap email already has an account (e.g. created by
    the dev bypass, or under a prior auth mechanism), signing in via Microsoft must
    not touch its existing role — just recognize and log it in."""
    c = client
    with c.app.state.db.sessionmaker() as s:
        existing = repo.create_user(s, email=BOSS, role="member", status="active")
        s.commit()
        existing_id = existing.id
    r = c.post("/auth/microsoft", json={"id_token": BOSS})
    assert r.status_code == 200
    assert r.json()["user"]["id"] == existing_id
    assert r.json()["user"]["role"] == "member"  # untouched — NOT promoted to super_admin
    with c.app.state.db.sessionmaker() as s:
        assert repo.get_user(s, existing_id).role == "member"


def test_bootstrap_concurrency_safe(tmp_path):
    """Two concurrent requests racing to sign in as the bootstrap email for the very
    first time: the UNIQUE(email) constraint — caught and recovered from in
    login_with_microsoft, same pattern the old register_user used — is what
    actually makes this safe. Exactly one user row and one 'super_admin_bootstrap'
    audit row must exist afterward, and neither thread may crash or hang."""
    from master_db.local import make_session_factory

    db = tmp_path / "boot_race.db"
    factory = make_session_factory(str(db))
    settings = Settings(
        database_url=f"sqlite:///{db.as_posix()}", jwt_secret="x" * 40,
        bootstrap_admin_email=BOSS,
    )
    barrier = threading.Barrier(2)
    real_get_by_oid = repo.get_user_by_microsoft_oid

    def _synced_get(session, oid):
        result = real_get_by_oid(session, oid)
        barrier.wait(timeout=5)
        return result

    errors: list[Exception] = []

    def _worker():
        try:
            with factory() as s:
                services.login_with_microsoft(s, BOSS, settings)
        except Exception as e:  # pragma: no cover - failure path, asserted on below
            errors.append(e)

    import unittest.mock as mock
    with mock.patch.object(security, "verify_microsoft_id_token", _fake_verify), \
         mock.patch.object(repo, "get_user_by_microsoft_oid", side_effect=_synced_get):
        t1 = threading.Thread(target=_worker)
        t2 = threading.Thread(target=_worker)
        t1.start(); t2.start()
        t1.join(timeout=10); t2.join(timeout=10)

    assert not errors, f"login_with_microsoft raised under concurrency: {errors}"
    with factory() as s:
        assert repo.list_users(s, q="boss", limit=10)[1] == 1
        bootstrap_events = [e for e in repo.list_user_audit(s) if e.action == "super_admin_bootstrap"]
        assert len(bootstrap_events) == 1


# ------------------------------------------------------------------ RBAC tier
def test_self_role_change_always_blocked(client):
    c = client
    AT, boss_id = _boss(c)
    _register_active(c, "second@siliconpatterns.com", role="admin")  # a 2nd admin exists
    # Even though boss is NOT the last admin here, self-role-change is still denied.
    r = c.patch(f"/admin/users/{boss_id}", headers=AT, json={"role": "admin"})
    assert r.status_code == 400


def test_ordinary_admin_cannot_grant_super_admin(client):
    c = client
    _boss(c)  # ensures the bootstrap has run; not otherwise needed here
    admin2_id = _register_active(c, "admin2@siliconpatterns.com", role="admin")
    A2 = _login_headers(c, "admin2@siliconpatterns.com")
    member_id = _register_active(c, "member1@siliconpatterns.com", role="member")
    r = c.patch(f"/admin/users/{member_id}", headers=A2, json={"role": "super_admin"})
    assert r.status_code == 403
    with c.app.state.db.sessionmaker() as s:
        assert repo.get_user(s, member_id).role == "member"


def test_ordinary_admin_cannot_modify_a_super_admin(client):
    c = client
    _, boss_id = _boss(c)
    _register_active(c, "admin2@siliconpatterns.com", role="admin")
    A2 = _login_headers(c, "admin2@siliconpatterns.com")
    assert c.patch(f"/admin/users/{boss_id}", headers=A2, json={"role": "admin"}).status_code == 403
    assert c.patch(f"/admin/users/{boss_id}", headers=A2, json={"is_active": False}).status_code == 403
    assert c.delete(f"/admin/users/{boss_id}", headers=A2).status_code == 403


def test_super_admin_can_manage_another_super_admin(client):
    c = client
    AT, boss_id = _boss(c)
    admin2_id = _register_active(c, "admin2@siliconpatterns.com", role="admin")
    A2T = _login_headers(c, "admin2@siliconpatterns.com")
    # boss (super_admin) may grant super_admin to someone else.
    r = c.patch(f"/admin/users/{admin2_id}", headers=AT, json={"role": "super_admin"})
    assert r.status_code == 200 and r.json()["role"] == "super_admin"
    # now two super_admins exist — the new one may demote boss.
    r2 = c.patch(f"/admin/users/{boss_id}", headers=A2T, json={"role": "admin"})
    assert r2.status_code == 200 and r2.json()["role"] == "admin"


def test_cannot_remove_last_active_super_admin(client):
    c = client
    AT, boss_id = _boss(c)
    # boss is the ONLY super_admin — even self-checks aside, no OTHER super_admin exists
    # to perform the action, so exercise it via a second super_admin who then can't drop boss.
    admin2_id = _register_active(c, "admin2@siliconpatterns.com", role="admin")
    c.patch(f"/admin/users/{admin2_id}", headers=AT, json={"role": "super_admin"})
    A2T = _login_headers(c, "admin2@siliconpatterns.com")
    # demote the second super_admin back down — now boss is again the last one.
    c.patch(f"/admin/users/{admin2_id}", headers=AT, json={"role": "admin"})
    assert c.patch(f"/admin/users/{boss_id}", headers=AT, json={"role": "admin"}).status_code == 400
    assert c.patch(f"/admin/users/{boss_id}", headers=AT, json={"is_active": False}).status_code == 400
    assert c.delete(f"/admin/users/{boss_id}", headers=AT).status_code == 400


def test_denied_privilege_escalation_is_audited(client):
    c = client
    _boss(c)
    _register_active(c, "admin2@siliconpatterns.com", role="admin")
    A2 = _login_headers(c, "admin2@siliconpatterns.com")
    member_id = _register_active(c, "member1@siliconpatterns.com", role="member")
    c.patch(f"/admin/users/{member_id}", headers=A2, json={"role": "super_admin"})
    with c.app.state.db.sessionmaker() as s:
        events = repo.list_user_audit(s, target_user_id=member_id)
        assert any(e.action == "denied" for e in events)


# ------------------------------------------------------------------ list/search/filter
def test_list_users_search_and_status_filter(client):
    c = client
    AT, _ = _boss(c)
    _register_active(c, "searchme@siliconpatterns.com", role="member")
    c.post("/auth/microsoft", json={"id_token": "stillpending@siliconpatterns.com"})

    by_status = c.get("/admin/users", headers=AT, params={"status": "pending"}).json()
    assert by_status["total"] >= 1
    assert all(u["status"] == "pending" for u in by_status["items"])

    by_q = c.get("/admin/users", headers=AT, params={"q": "searchme"}).json()
    assert by_q["total"] == 1 and by_q["items"][0]["email"] == "searchme@siliconpatterns.com"


# ------------------------------------------------------------------ production readiness
def test_readiness_fails_without_active_super_admin(tmp_path):
    from backend import platform_service
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'noready.db').as_posix()}",
        environment="production", jwt_secret="a" * 40,
        dev_auth_bypass=False, cors_origins=["https://app.siliconpatterns.com"],
        rate_limit_per_minute=60,
        microsoft_tenant_id="test-tenant", microsoft_client_id="test-client",
    ))
    with TestClient(app):
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            result = platform_service.production_readiness(app.state.settings, s)
    assert result["ready"] is False
    assert result["checks"]["active_super_admin_exists"] is False
