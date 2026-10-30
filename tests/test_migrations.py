"""Startup migration automation (master_db/migrate.py + backend/main.py lifespan).

The database-backed cases are DESTRUCTIVE (DDL + TRUNCATE) and run only against a
URL that clears the production guard below — never the application's own database.
They skip otherwise, which is the default. The ordering, idempotency, SQLite and
startup-abort guarantees need no database and always run.
"""
import logging
import os
import uuid

import pytest

from backend.config import Settings
from master_db import migrate
from master_db.migrate import (
    apply_pending,
    is_postgres,
    migration_files,
)

# ---------------------------------------------------------------------------
# PRODUCTION SAFETY GUARD
#
# These tests write DDL and TRUNCATE bookkeeping tables. Pointing them at a live
# database destroys data — that is not hypothetical, it happened: schema isolation
# via a `search_path` connection option did NOT hold through a hosted connection
# pooler, and the suite ran against the production `public` schema.
#
# So isolation is no longer trusted as the safety mechanism. The URL itself is
# vetted before a single statement runs, and the checks are deliberately paranoid:
#
#   1. SP_TEST_POSTGRES_URL must be set — never falls back to DATABASE_URL.
#   2. It must not equal DATABASE_URL (the app's own database).
#   3. Its host must not look managed/hosted (supabase, neon, rds, railway, …).
#   4. Its database name must look like a test database.
#
# Rule 3 or 4 can be waived ONLY with SP_ALLOW_DESTRUCTIVE_DB_TESTS=i-understand,
# which is required to be typed in full so it cannot be set by reflex.
# ---------------------------------------------------------------------------
PG_URL = os.environ.get("SP_TEST_POSTGRES_URL", "").strip()
_OVERRIDE = os.environ.get("SP_ALLOW_DESTRUCTIVE_DB_TESTS", "").strip().lower() == "i-understand"

_HOSTED_MARKERS = ("supabase.co", "supabase.com", "pooler.supabase", "neon.tech", "render.com",
                   "railway.app", "rds.amazonaws.com", "azure.com", "cloudsql", "heroku",
                   "planetscale", "cockroachlabs", "digitalocean", "aivencloud")
_TEST_DB_MARKERS = ("test", "_ci", "ci_", "scratch", "sandbox", "tmp")


def _guard_reason(url: str) -> str:
    """Empty string when the URL is safe to run destructive tests against."""
    if not url:
        return "SP_TEST_POSTGRES_URL is not set"
    if _OVERRIDE:
        return ""
    app_url = os.environ.get("DATABASE_URL", "").strip()
    if app_url and url.split("?")[0] == app_url.split("?")[0]:
        return ("SP_TEST_POSTGRES_URL is the SAME database as DATABASE_URL — refusing to run "
                "destructive migration tests against the application's own database")
    lowered = url.lower()
    for marker in _HOSTED_MARKERS:
        if marker in lowered:
            return (f"SP_TEST_POSTGRES_URL points at a hosted database ({marker}) — refusing. "
                    f"Use a local/disposable Postgres, or set "
                    f"SP_ALLOW_DESTRUCTIVE_DB_TESTS=i-understand if it really is disposable")
    dbname = lowered.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
    if not any(m in dbname for m in _TEST_DB_MARKERS):
        return (f"database name {dbname!r} does not look like a test database (expected one of "
                f"{_TEST_DB_MARKERS} in the name) — refusing. Set "
                f"SP_ALLOW_DESTRUCTIVE_DB_TESTS=i-understand to override")
    return ""


_GUARD = _guard_reason(PG_URL)
needs_pg = pytest.mark.skipif(bool(_GUARD), reason=_GUARD or "ok")


@pytest.mark.parametrize("url,needle", [
    ("", "not set"),
    ("postgresql://u:p@aws-1-ap-south-1.pooler.supabase.com:5432/postgres", "hosted database"),
    ("postgresql://u:p@x.neon.tech:5432/maindb", "hosted database"),
    ("postgresql://u:p@localhost:5432/postgres", "does not look like a test database"),
    ("postgresql://u:p@localhost:5432/silicon_patterns", "does not look like a test database"),
])
def test_production_guard_rejects_unsafe_urls(url, needle):
    assert needle in _guard_reason(url)


def test_production_guard_rejects_the_application_database(monkeypatch):
    """The check that would have prevented the incident: never the app's own DB."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/sp_test")
    assert "SAME database" in _guard_reason("postgresql://u:p@localhost:5432/sp_test")


@pytest.mark.parametrize("url", [
    "postgresql://u:p@localhost:5432/sp_test",
    "postgresql://postgres@127.0.0.1:5432/silicon_patterns_test",
    "postgresql://u:p@localhost:5432/ci_scratch",
])
def test_production_guard_allows_local_test_databases(url):
    assert _guard_reason(url) == ""


# --------------------------------------------------------------- file ordering
def test_migrations_are_ordered_and_gap_free():
    names = [f.name for f in migration_files()]
    assert names, "no migration files found"
    numbers = [int(n[:4]) for n in names]
    assert numbers == sorted(numbers), "filename sort must be numeric order"
    assert numbers == list(range(1, len(numbers) + 1)), f"gap in migration numbering: {numbers}"


def test_latest_migration_is_the_newest_on_disk():
    """Pins the head so a migration added without renumbering is caught."""
    assert migration_files()[-1].name == "0058_market_intelligence.sql"


def test_every_migration_is_reapplyable():
    """The runner may re-apply a file whose effects are already present (that is how it
    adopts a database advanced out-of-band), so every DDL statement must be guarded."""
    offenders = []
    for f in migration_files():
        sql = f.read_text(encoding="utf-8")
        lowered = sql.lower()
        for i, line in enumerate(sql.splitlines(), 1):
            stripped = line.strip().lower()
            if stripped.startswith("create table") and "if not exists" not in stripped:
                offenders.append(f"{f.name}:{i} CREATE TABLE without IF NOT EXISTS")
            if stripped.startswith("create index") and "if not exists" not in stripped:
                offenders.append(f"{f.name}:{i} CREATE INDEX without IF NOT EXISTS")
            if stripped.startswith("create unique index") and "if not exists" not in stripped:
                offenders.append(f"{f.name}:{i} CREATE UNIQUE INDEX without IF NOT EXISTS")
            if "add column" in stripped and "if not exists" not in stripped:
                offenders.append(f"{f.name}:{i} ADD COLUMN without IF NOT EXISTS")
            if "add constraint" in stripped:
                # must be preceded somewhere by a matching DROP CONSTRAINT IF EXISTS
                name = stripped.split("add constraint", 1)[1].strip().split()[0]
                if f"drop constraint if exists {name}" not in lowered:
                    offenders.append(f"{f.name}:{i} ADD CONSTRAINT {name} without a prior DROP IF EXISTS")
    assert not offenders, "non-idempotent migration statements:\n  " + "\n  ".join(offenders)


# ------------------------------------------------------------------- SQLite
def test_sqlite_is_skipped_not_an_error():
    result = apply_pending("sqlite:///:memory:")
    assert result.status == "skipped" and not result.changed
    assert "ORM" in result.detail


def test_is_postgres_detects_both_url_forms():
    assert is_postgres("postgresql://u:p@h/db")
    assert is_postgres("postgresql+psycopg://u:p@h/db")
    assert not is_postgres("sqlite:///x.db")
    assert not is_postgres("")


# ------------------------------------------------------- real Postgres runner
@pytest.fixture()
def pg_schema():
    """A throwaway schema on the test Postgres, dropped afterwards.

    search_path is set on the CONNECTION, not via a URL option — a URL-level
    ``options=-csearch_path=...`` silently did not survive a hosted pooler, which is
    how this suite once wrote to production. The guard above is the real protection;
    this is defence in depth."""
    import psycopg

    name = f"sp_test_{uuid.uuid4().hex[:12]}"
    url = migrate._pg_url(PG_URL)
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{name}"')
    scoped = f"{url}{'&' if '?' in url else '?'}options=-csearch_path%3D{name}"
    try:
        yield scoped, name
    finally:
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{name}" CASCADE')


def _table_exists(url: str, schema: str, table: str) -> bool:
    import psycopg

    with psycopg.connect(migrate._pg_url(url), autocommit=True) as conn:
        return bool(conn.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s", (schema, table)).fetchone()[0])


@needs_pg
def test_fresh_database_applies_every_migration(pg_schema):
    url, schema = pg_schema
    result = apply_pending(url)
    assert result.status == "applied"
    assert len(result.applied) == len(migration_files())
    assert result.applied[-1] == "0056_notification_deliveries.sql"
    assert _table_exists(PG_URL, schema, "companies")
    assert _table_exists(PG_URL, schema, "notification_deliveries")


@needs_pg
def test_second_run_is_a_no_op(pg_schema):
    url, _schema = pg_schema
    apply_pending(url)
    again = apply_pending(url)
    assert again.status == "up_to_date"
    assert again.applied == [] and again.pending == []
    assert not again.changed


@needs_pg
def test_partially_migrated_database_applies_only_the_remainder(pg_schema):
    """The production case: a schema advanced out-of-band, tracker behind."""
    import psycopg

    url, _schema = pg_schema
    all_files = [f.name for f in migration_files()]
    # Apply everything, then forget the last two — as if they were run manually.
    apply_pending(url)
    with psycopg.connect(migrate._pg_url(url), autocommit=True) as conn:
        conn.execute("DELETE FROM schema_migrations WHERE filename = ANY(%s)", (all_files[-2:],))

    result = apply_pending(url)
    assert result.status == "applied"
    assert result.applied == all_files[-2:]        # only the forgotten ones re-ran
    assert apply_pending(url).status == "up_to_date"


@needs_pg
def test_reapplying_over_an_existing_schema_is_harmless(pg_schema):
    """Re-running a file whose effects are already present must not error or destroy
    data — this is exactly what production's first automatic run will do."""
    import psycopg

    url, _schema = pg_schema
    apply_pending(url)
    with psycopg.connect(migrate._pg_url(url), autocommit=True) as conn:
        conn.execute("INSERT INTO companies (company_domain, canonical_company_id, company_name, "
                     "name_key, prospect_type, validation_status) "
                     "VALUES ('keep.com', 'KEEP', 'Keep', 'keep', 'PRODUCT_COMPANY', 'VALID')")
        conn.execute("TRUNCATE schema_migrations")         # force a full re-apply

    result = apply_pending(url)
    assert result.status == "applied" and len(result.applied) == len(migration_files())
    with psycopg.connect(migrate._pg_url(url), autocommit=True) as conn:
        assert conn.execute("SELECT count(*) FROM companies").fetchone()[0] == 1


@needs_pg
def test_pending_list_is_read_only(pg_schema):
    url, schema = pg_schema
    names = migrate.pending_migrations(url)
    assert names == [f.name for f in migration_files()]
    assert not _table_exists(PG_URL, schema, "companies")     # nothing was applied


@needs_pg
def test_dry_run_changes_nothing(pg_schema):
    url, schema = pg_schema
    result = apply_pending(url, dry_run=True)
    assert result.status == "up_to_date" and result.applied == []
    assert result.pending == [f.name for f in migration_files()]
    assert not _table_exists(PG_URL, schema, "companies")


@needs_pg
def test_a_failing_migration_raises_and_records_nothing(pg_schema, tmp_path):
    """A broken migration must surface, not be swallowed — and must not be recorded."""
    import psycopg

    url, _schema = pg_schema
    (tmp_path / "0001_ok.sql").write_text("CREATE TABLE IF NOT EXISTS ok_t (id int);", encoding="utf-8")
    (tmp_path / "0002_broken.sql").write_text("CREATE TABLE broken (", encoding="utf-8")

    with pytest.raises(Exception):
        apply_pending(url, directory=tmp_path)

    with psycopg.connect(migrate._pg_url(url), autocommit=True) as conn:
        recorded = {r[0] for r in conn.execute("SELECT filename FROM schema_migrations").fetchall()}
    assert recorded == {"0001_ok.sql"}       # the good one stuck, the broken one did not


@needs_pg
def test_logs_report_check_pending_apply_and_complete(pg_schema, caplog):
    url, _schema = pg_schema
    with caplog.at_level(logging.INFO, logger="master_db.migrate"):
        apply_pending(url)
    text = "\n".join(r.message % r.args if r.args else r.message for r in caplog.records)
    assert "Checking database migrations..." in text
    assert "Pending migrations:" in text
    assert "Applying migration 0056_notification_deliveries.sql" in text
    assert "Migration complete." in text


# ------------------------------------------------------------ startup wiring
def test_auto_migrate_defaults_on_and_is_configurable(monkeypatch):
    for name in ("SP_AUTO_MIGRATE", "AUTO_MIGRATE"):
        monkeypatch.delenv(name, raising=False)
    assert Settings(_env_file=None).auto_migrate is True
    monkeypatch.setenv("SP_AUTO_MIGRATE", "false")
    assert Settings(_env_file=None).auto_migrate is False


def test_startup_aborts_when_a_migration_fails(monkeypatch):
    """Production must not come up on an outdated schema."""
    from fastapi.testclient import TestClient

    from backend.main import create_app

    def _boom(*a, **k):
        raise RuntimeError("relation does not exist")

    monkeypatch.setattr("master_db.migrate.apply_pending", _boom)
    app = create_app(Settings(database_url="postgresql+psycopg://u:p@localhost/x",
                              auto_migrate=True, log_json=False, dev_auth_bypass=True,
                              scheduler_enabled=False))
    with pytest.raises(RuntimeError, match="Startup aborted: database migration failed"):
        with TestClient(app):
            pass


def test_startup_runs_migrations_before_serving(tmp_path, monkeypatch):
    """The runner is invoked during lifespan, before any request is handled."""
    from fastapi.testclient import TestClient

    from backend.main import create_app
    from master_db.models import Base

    calls = []
    monkeypatch.setattr("master_db.migrate.apply_pending",
                        lambda url, **kw: calls.append(url) or migrate.MigrationResult("up_to_date"))
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'm.db').as_posix()}",
                              auto_migrate=True, log_json=False, dev_auth_bypass=True,
                              scheduler_enabled=False))
    with TestClient(app) as client:
        Base.metadata.create_all(app.state.db.engine)
        assert calls, "apply_pending was not called during startup"
        assert client.get("/health/live").status_code == 200


def test_auto_migrate_false_skips_the_runner(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from backend.main import create_app
    from master_db.models import Base

    calls = []
    monkeypatch.setattr("master_db.migrate.apply_pending", lambda url, **kw: calls.append(url))
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'm2.db').as_posix()}",
                              auto_migrate=False, log_json=False, dev_auth_bypass=True,
                              scheduler_enabled=False))
    with TestClient(app) as client:
        Base.metadata.create_all(app.state.db.engine)
        assert calls == []
        assert client.get("/health/live").status_code == 200


def test_sqlite_startup_is_unaffected(tmp_path):
    """The default local/dev path: real runner, real SQLite URL, no error."""
    from fastapi.testclient import TestClient

    from backend.main import create_app
    from master_db.models import Base

    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'm3.db').as_posix()}",
                              auto_migrate=True, log_json=False, dev_auth_bypass=True,
                              scheduler_enabled=False))
    with TestClient(app) as client:
        Base.metadata.create_all(app.state.db.engine)
        assert client.get("/health/live").status_code == 200
