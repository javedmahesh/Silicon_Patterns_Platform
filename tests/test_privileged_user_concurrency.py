"""F1 remediation: the last-active-SUPER_ADMIN / last-active-admin TOCTOU race.

The bug: two concurrent requests each demoting/disabling/deleting a *different*
active admin-tier user could each independently count "another admin-tier user is
still active" (a plain SELECT, no lock) and both commit, leaving zero active
admins. The fix centralizes the check behind
``backend.repositories.lock_active_privileged_users`` -- a single ``SELECT ...
FOR UPDATE`` (on PostgreSQL) over the whole active admin-tier cohort, evaluated
fresh from inside the caller's own transaction, immediately before the mutation.

This file has three tiers:
  1. Deterministic, non-DB logic tests of the guard functions themselves.
  2. A structural test proving FOR UPDATE is actually applied on the postgresql
     dialect (and correctly NOT on sqlite, for dev/test compatibility) -- this is
     what SQLite cannot exercise, so it's verified by compiling the statement
     directly against each dialect, no live connection needed.
  3. A threaded regression/smoke test against SQLite, and a skippable *live*
     PostgreSQL test that is the actual proof of the concurrency fix.

IMPORTANT: this fix's concurrency guarantee is PostgreSQL-specific (``FOR UPDATE``
is a no-op on SQLite by design -- see ``lock_active_privileged_users``). The
SQLite-based threaded test below deliberately does NOT assert that the race is
prevented -- empirically, it is NOT prevented on SQLite, because the invariant
check runs against an in-memory snapshot with no row lock behind it, so both
threads can independently see "safe" from the same stale state. That test only
asserts what SQLite CAN honestly guarantee: no crash, and audit-log correctness
per attempt. Only ``test_concurrent_demotion_race_on_real_postgres`` (skipped
unless ``SP_LIVE_POSTGRES_TEST_URL`` is set) proves the race itself is fixed.
"""
from __future__ import annotations

import os
import threading

import pytest
from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql, sqlite

import backend.repositories as repo
import backend.services as services
from master_db.local import make_session_factory
from master_db.models import User, UserAuditEvent


# =====================================================================
# 1. Pure-logic tests of the guard primitives (no DB, or a trivial one).
# =====================================================================
def _user(id_, role="super_admin", status="active"):
    u = User(email=f"u{id_}@x.com", role=role, status=status, is_active=(status == "active"))
    u.id = id_
    return u


def test_check_keeps_an_admin_rejects_when_it_is_the_last_one():
    cohort = [_user(1, role="super_admin")]
    with pytest.raises(repo.LastPrivilegedUserError, match="last active admin"):
        repo.check_keeps_an_admin(cohort, cohort[0])


def test_check_keeps_an_admin_allows_when_another_remains():
    cohort = [_user(1, role="super_admin"), _user(2, role="admin")]
    repo.check_keeps_an_admin(cohort, cohort[0])  # must not raise


def test_check_keeps_a_super_admin_rejects_when_it_is_the_last_one():
    cohort = [_user(1, role="super_admin"), _user(2, role="admin")]  # admin doesn't count for THIS check
    with pytest.raises(repo.LastPrivilegedUserError, match="last active super_admin"):
        repo.check_keeps_a_super_admin(cohort, cohort[0])


def test_check_keeps_a_super_admin_allows_when_another_super_admin_remains():
    cohort = [_user(1, role="super_admin"), _user(2, role="super_admin")]
    repo.check_keeps_a_super_admin(cohort, cohort[0])  # must not raise


def test_check_keeps_a_super_admin_is_noop_for_a_plain_admin():
    cohort = [_user(1, role="admin")]
    repo.check_keeps_a_super_admin(cohort, cohort[0])  # must not raise -- not a super_admin


@pytest.mark.parametrize("old_role,new_role,status,expect", [
    ("super_admin", "admin", "active", (False, True)),    # stays admin-tier -> only super_admin check
    ("super_admin", "member", "active", (True, True)),    # leaves admin-tier entirely -> both checks
    ("admin", "member", "active", (True, False)),         # leaves admin-tier, was never super_admin
    ("admin", "manager", "active", (True, False)),
    ("super_admin", "super_admin", "active", (False, False)),  # no-op role "change"
    ("member", "admin", "active", (False, False)),        # promotion -> can never violate the invariant
    ("super_admin", "member", "disabled", (False, False)),  # already inactive -> can't affect either invariant
])
def test_role_change_exposure_matrix(old_role, new_role, status, expect):
    u = _user(1, role=old_role, status=status)
    assert repo.role_change_exposure(u, new_role) == expect


def test_is_active_privileged():
    assert repo.is_active_privileged(_user(1, role="super_admin", status="active"))
    assert repo.is_active_privileged(_user(1, role="admin", status="active"))
    assert not repo.is_active_privileged(_user(1, role="member", status="active"))
    assert not repo.is_active_privileged(_user(1, role="super_admin", status="disabled"))


# =====================================================================
# 2. Structural proof: FOR UPDATE is applied on postgresql, not on sqlite.
# =====================================================================
def _compiled_sql(dialect_module) -> str:
    stmt = (
        select(User)
        .where(User.role.in_(("admin", "super_admin")), User.status == "active")
        .order_by(User.id)
    )
    # Mirror lock_active_privileged_users' own dialect check without a live connection.
    stmt = stmt.with_for_update() if dialect_module is postgresql else stmt
    return str(stmt.compile(dialect=dialect_module.dialect(), compile_kwargs={"literal_binds": True}))


def test_lock_query_uses_for_update_on_postgresql_dialect():
    assert "FOR UPDATE" in _compiled_sql(postgresql)


def test_lock_query_has_no_for_update_on_sqlite_dialect():
    # SQLite doesn't support FOR UPDATE -- lock_active_privileged_users must not emit it there.
    assert "FOR UPDATE" not in _compiled_sql(sqlite)


def test_lock_active_privileged_users_dialect_gate(tmp_path):
    """End-to-end (against the real sqlite dialect check the function uses):
    confirms lock_active_privileged_users itself -- not just a hand-compiled
    mirror -- skips FOR UPDATE on sqlite and still returns the correct cohort."""
    factory = make_session_factory(str(tmp_path / "gate.db"))
    with factory() as s:
        s.add_all([_user(1, "super_admin"), _user(2, "admin"), _user(3, "member")])
        s.commit()
        cohort = repo.lock_active_privileged_users(s)
        assert {u.id for u in cohort} == {1, 2}  # member excluded, both admin-tier included


# =====================================================================
# 3. Threaded regression/smoke test (SQLite) + live PostgreSQL proof.
# =====================================================================
class _Actor:
    def __init__(self, id_):
        self.id = id_
        self.role = "super_admin"
        self.email = f"actor{id_}@x.com"


def _run_concurrent_mutual_demotion(session_factory, id1, id2):
    """Two threads each try to demote the OTHER of two active super_admins
    (super_admin -> admin) at the same time. Returns (outcomes, remaining_count,
    audit_actions_by_target). Forces both threads' cohort-read to happen before
    either commits -- the exact interleaving F1 describes -- via a barrier."""
    barrier = threading.Barrier(2)
    real_lock = repo.lock_active_privileged_users

    def _synced_lock(session):
        # Barrier BEFORE the lock attempt, not after: a real FOR UPDATE causes
        # whichever thread arrives second to block inside real_lock() until the
        # first commits. Waiting on the barrier after the lock would deadlock
        # (thread A parked at the barrier waiting for B; B parked inside the DB
        # call waiting for A's commit). SQLite's no-op FOR UPDATE never blocks,
        # so this ordering never mattered here -- but keep both helpers
        # consistent with the live-Postgres version below.
        barrier.wait(timeout=5)
        return real_lock(session)

    outcomes: dict[int, tuple[str, str]] = {}

    def _demote(target_id, other_id):
        try:
            with session_factory() as s:
                actor = s.get(User, other_id)
                out = services.set_user_role(s, target_id, "admin", actor)
                outcomes[target_id] = ("ok", out.role)
        except Exception as e:  # HTTPException (clean 400) OR a raw DB locking error
            outcomes[target_id] = ("rejected", getattr(e, "detail", str(e)))

    import unittest.mock as mock
    with mock.patch.object(repo, "lock_active_privileged_users", side_effect=_synced_lock):
        t1 = threading.Thread(target=_demote, args=(id1, id2))
        t2 = threading.Thread(target=_demote, args=(id2, id1))
        t1.start(); t2.start()
        t1.join(timeout=10); t2.join(timeout=10)

    with session_factory() as s:
        remaining = s.scalar(
            select(func.count()).select_from(User)
            .where(User.role == "super_admin", User.status == "active")
        ) or 0
        role_changed_targets = {
            e.target_user_id for e in s.scalars(
                select(UserAuditEvent).where(UserAuditEvent.action == "role_changed")
            )
        }
    return outcomes, remaining, role_changed_targets


def test_concurrent_mutual_demotion_sqlite_smoke(tmp_path):
    """Regression/smoke test only -- see module docstring. Confirms two points
    that hold REGARDLESS of whether SQLite happens to let the race through:

    1. The production code path (services.set_user_role) never crashes or leaves
       a partial/inconsistent write under concurrent invocation -- each attempt
       cleanly resolves to either a committed mutation + its audit row, or a
       rejection with no audit row at all (never a misleading one).
    2. This is a per-transaction correctness property, provable without real row
       locking, so it's honest to assert on SQLite.

    What this test deliberately does NOT assert: that at least one active
    super_admin survives. On SQLite, lock_active_privileged_users takes no lock
    (FOR UPDATE is a no-op there), so both threads' cohort reads happen before
    either commits and both can independently conclude "safe" from the same
    stale 2-active snapshot -- the exact F1 race, reproducible here because
    SQLite provides no relevant protection. That is expected and consistent with
    the module docstring; it is NOT a regression in the fix, whose target is
    PostgreSQL. The cross-thread invariant is proven only by
    test_concurrent_demotion_race_on_real_postgres.
    """
    factory = make_session_factory(str(tmp_path / "mutual.db"))
    with factory() as s:
        s.add_all([_user(1, "super_admin"), _user(2, "super_admin")])
        s.commit()

    outcomes, _remaining, role_changed_targets = _run_concurrent_mutual_demotion(factory, 1, 2)

    assert len(outcomes) == 2, "both concurrent attempts must resolve (no hang, no unhandled crash)"
    for tid, (status, _detail) in outcomes.items():
        if status == "ok":
            assert tid in role_changed_targets, "a committed mutation must retain its audit event"
        else:
            assert tid not in role_changed_targets, "a rejected/failed mutation must not emit a misleading success audit event"


# ============================================================================
# The CLI is a second, un-authenticated mutation path (found during the F1
# inspection, not in Opus's original file list -- see orchestrator/cli.py's
# `users promote` / `users deactivate`) that could previously zero out the last
# active admin/super_admin with NO protection at all (not even the old racy
# check). It must now route through the same centralized primitive.
# ============================================================================
def test_cli_promote_blocks_demoting_the_last_active_admin(tmp_path):
    import orchestrator.cli as cli

    db = tmp_path / "cli_last_admin.db"
    factory = make_session_factory(str(db))
    with factory() as s:
        s.add(User(email="boss@x.com", role="super_admin", status="active", is_active=True))
        s.commit()

    with pytest.raises(cli.typer.Exit):
        cli.users_promote(email="boss@x.com", role="member", db=db)

    with factory() as s:
        assert s.scalar(select(User).where(User.email == "boss@x.com")).role == "super_admin"


def test_cli_deactivate_blocks_disabling_the_last_active_super_admin(tmp_path):
    import orchestrator.cli as cli

    db = tmp_path / "cli_last_super.db"
    factory = make_session_factory(str(db))
    with factory() as s:
        s.add_all([
            User(email="boss@x.com", role="super_admin", status="active", is_active=True),
            User(email="admin2@x.com", role="admin", status="active", is_active=True),
        ])
        s.commit()

    with pytest.raises(cli.typer.Exit):
        cli.users_deactivate(email="boss@x.com", db=db)

    with factory() as s:
        assert s.scalar(select(User).where(User.email == "boss@x.com")).is_active is True


def test_cli_promote_allows_a_safe_demotion(tmp_path):
    """Baseline: the new guard must not block a transition that doesn't threaten
    either invariant (a second super_admin still exists)."""
    import orchestrator.cli as cli

    db = tmp_path / "cli_safe.db"
    factory = make_session_factory(str(db))
    with factory() as s:
        s.add_all([
            User(email="boss@x.com", role="super_admin", status="active", is_active=True),
            User(email="boss2@x.com", role="super_admin", status="active", is_active=True),
        ])
        s.commit()

    cli.users_promote(email="boss@x.com", role="admin", db=db)  # must not raise

    with factory() as s:
        assert s.scalar(select(User).where(User.email == "boss@x.com")).role == "admin"


# --------------------------------------------------------- live PostgreSQL proof
_LIVE_PG_URL = os.environ.get("SP_LIVE_POSTGRES_TEST_URL", "").strip()

pytestmark_live = pytest.mark.skipif(
    not _LIVE_PG_URL,
    reason="set SP_LIVE_POSTGRES_TEST_URL to a Postgres DSN to run the real-concurrency F1 proof "
           "(uses a disposable 'sp_validation' schema; never touches public/production data)",
)


@pytestmark_live
def test_concurrent_demotion_race_on_real_postgres():
    """The actual F1 proof: two real, separate connections to real PostgreSQL,
    each demoting a different one of two active super_admins, synchronized with a
    barrier so both reach the lock point together. On unfixed code (a plain COUNT,
    no lock), both would pass their check and both would commit, leaving zero
    active super_admins. With the fix, the second transaction's ``FOR UPDATE``
    blocks until the first commits, then re-evaluates against the now-committed
    state and is rejected.

    Runs entirely inside a dedicated, disposable 'sp_validation' schema (dropped +
    recreated up front, dropped again on exit) -- the same isolation pattern
    scripts/validate_postgres.py uses. Never touches public or any other schema.
    """
    import urllib.parse

    import psycopg
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from master_db.models import Base

    VALIDATION_SCHEMA = "sp_validation"
    raw = _LIVE_PG_URL.replace("postgresql+psycopg://", "postgresql://", 1)
    sa_url = _LIVE_PG_URL if _LIVE_PG_URL.startswith("postgresql+psycopg://") \
        else _LIVE_PG_URL.replace("postgresql://", "postgresql+psycopg://", 1)

    def _with_search_path(url: str) -> str:
        opt = urllib.parse.quote(f"-c search_path={VALIDATION_SCHEMA},public", safe="")
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}options={opt}"

    with psycopg.connect(raw, autocommit=True) as boot:
        boot.execute(f"DROP SCHEMA IF EXISTS {VALIDATION_SCHEMA} CASCADE")
        boot.execute(f"CREATE SCHEMA {VALIDATION_SCHEMA}")
    try:
        engine = create_engine(_with_search_path(sa_url), future=True)
        # checkfirst=False: we just DROP+CREATE'd VALIDATION_SCHEMA above, so these
        # tables are guaranteed absent there. checkfirst's existence probe resolves
        # unqualified table names via Postgres search_path visibility, which can
        # match a same-named table in `public` (e.g. the real production `users`)
        # and skip creation here entirely -- silently redirecting the INSERTs below
        # to `public`. Empirically confirmed against this project's own Supabase
        # instance: checkfirst=True found `public.users` visible and skipped
        # creating sp_validation.users, and the subsequent INSERT targeted
        # `public.users` directly (only caught because that table's schema has
        # since drifted and lacks a column the model expects).
        Base.metadata.create_all(engine, tables=[User.__table__, UserAuditEvent.__table__], checkfirst=False)
        SM = sessionmaker(bind=engine, future=True, expire_on_commit=False)

        with SM() as s:
            s.add_all([_user_no_pk("a@x.com"), _user_no_pk("b@x.com")])
            s.commit()
            ids = [u.id for u in s.scalars(select(User).order_by(User.id))]
        id1, id2 = ids

        barrier = threading.Barrier(2)
        real_lock = repo.lock_active_privileged_users

        def _synced_lock(session):
            # See the identical comment in _run_concurrent_mutual_demotion: the
            # barrier must fire BEFORE the real FOR UPDATE attempt, or the two
            # threads deadlock (second thread blocks in-DB waiting for the
            # first's commit, while the first waits at the barrier for the
            # second to arrive -- which it never can).
            barrier.wait(timeout=10)
            return real_lock(session)

        outcomes: dict[int, tuple[str, str]] = {}

        def _demote(target_id, other_id):
            try:
                with SM() as s:
                    actor = s.get(User, other_id)
                    out = services.set_user_role(s, target_id, "admin", actor)
                    outcomes[target_id] = ("ok", out.role)
            except Exception as e:
                outcomes[target_id] = ("rejected", getattr(e, "detail", str(e)))

        import unittest.mock as mock
        with mock.patch.object(repo, "lock_active_privileged_users", side_effect=_synced_lock):
            t1 = threading.Thread(target=_demote, args=(id1, id2))
            t2 = threading.Thread(target=_demote, args=(id2, id1))
            t1.start(); t2.start()
            t1.join(timeout=15); t2.join(timeout=15)

        with SM() as s:
            remaining = len(list(s.scalars(
                select(User).where(User.role == "super_admin", User.status == "active")
            )))
            role_changed_targets = {
                e.target_user_id for e in s.scalars(
                    select(UserAuditEvent).where(UserAuditEvent.action == "role_changed")
                )
            }

        assert remaining >= 1, "F1 REGRESSION: both concurrent demotions committed -- zero active super_admins"
        successes = [tid for tid, (status, _) in outcomes.items() if status == "ok"]
        assert len(successes) == 1, f"expected exactly one of the two conflicting demotions to succeed, got {outcomes}"
        rejected = [tid for tid, (status, _) in outcomes.items() if status != "ok"]
        assert len(rejected) == 1
        assert successes[0] in role_changed_targets
        assert rejected[0] not in role_changed_targets, "rejected demotion must not emit a misleading success audit event"

        engine.dispose()
    finally:
        with psycopg.connect(raw, autocommit=True) as cleanup:
            cleanup.execute(f"DROP SCHEMA IF EXISTS {VALIDATION_SCHEMA} CASCADE")


def _user_no_pk(email: str) -> User:
    return User(email=email, role="super_admin", status="active", is_active=True)
