"""Migration runner — the single implementation used by startup and the CLI script.

    from master_db.migrate import apply_pending
    apply_pending(database_url)

Applies every ``master_db/migrations/0*.sql`` file that a ``schema_migrations``
bookkeeping table does not already record, in filename order, exactly once each.

Design notes that matter in production:

* **Advisory-locked.** A Postgres session-level advisory lock serializes concurrent
  boots, so N replicas starting together cannot race: one applies, the others wait
  and then find nothing pending. This is what made boot-time migration unsafe before.
* **Ordered and gap-free.** Files sort lexicographically, which for zero-padded
  ``NNNN_`` names is numeric order. A file is never skipped: anything not in
  ``schema_migrations`` is pending, regardless of how far ahead the schema looks.
* **Self-healing.** Every migration file is written defensively (``IF NOT EXISTS``,
  ``DROP CONSTRAINT IF EXISTS`` before ``ADD CONSTRAINT``), so re-applying one whose
  effects are already present is a no-op. That is what lets this adopt a database
  whose schema was advanced out-of-band — it re-runs those files harmlessly and
  records them, rather than refusing to start.
* **Fails loudly.** A SQL error propagates; nothing is swallowed. Callers decide
  whether that aborts the process.

SQLite is not supported and is not an error: local dev builds its schema from the ORM
(``master_db.local.ensure_local_schema``). :func:`apply_pending` reports ``skipped``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("master_db.migrate")

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

# Distinct from the Standard Run's key (backend/standard_run.py) — a migration must
# never contend with a pipeline run, only with another migration.
_ADVISORY_LOCK_KEY = 748291014
_LOCK_TIMEOUT_MS = 120_000

_BOOKKEEPING = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    text PRIMARY KEY,
    applied_at  timestamptz NOT NULL DEFAULT now()
);
"""


@dataclass(slots=True)
class MigrationResult:
    status: str                                    # applied | up_to_date | skipped
    total: int = 0
    already_applied: int = 0
    applied: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    detail: str = ""

    @property
    def changed(self) -> bool:
        return bool(self.applied)


def migration_files(directory: Path | None = None) -> list[Path]:
    """Every migration file, in apply order."""
    return sorted((directory or MIGRATIONS_DIR).glob("0*.sql"))


def _pg_url(database_url: str) -> str:
    """psycopg connects with a bare libpq URL; SQLAlchemy's ``+psycopg`` suffix is a
    driver selector it does not understand."""
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def is_postgres(database_url: str) -> bool:
    return (database_url or "").strip().lower().startswith("postgres")


def pending_migrations(database_url: str, *, directory: Path | None = None) -> list[str]:
    """Filenames that would be applied. Read-only — used by --dry-run and by tests."""
    import psycopg

    files = migration_files(directory)
    with psycopg.connect(_pg_url(database_url), autocommit=True) as conn:
        conn.execute(_BOOKKEEPING)
        applied = {r[0] for r in conn.execute("SELECT filename FROM schema_migrations").fetchall()}
    return [f.name for f in files if f.name not in applied]


def apply_pending(
    database_url: str,
    *,
    directory: Path | None = None,
    dry_run: bool = False,
    log: logging.Logger | None = None,
) -> MigrationResult:
    """Apply every pending migration, in order, exactly once.

    Raises on any SQL failure — the caller decides whether that is fatal. On success
    the database is guaranteed to be at the latest migration on disk.
    """
    out = log or logger
    if not is_postgres(database_url):
        return MigrationResult("skipped", detail="not a Postgres database (schema comes from the ORM)")

    import psycopg

    files = migration_files(directory)
    if not files:
        return MigrationResult("skipped", detail=f"no migration files in {directory or MIGRATIONS_DIR}")

    out.info("Checking database migrations...")
    with psycopg.connect(_pg_url(database_url), autocommit=True) as conn:
        conn.execute(_BOOKKEEPING)
        # Serialize concurrent boots. pg_advisory_lock blocks rather than failing, so a
        # second replica waits for the first to finish and then finds nothing pending.
        conn.execute(f"SET lock_timeout = {_LOCK_TIMEOUT_MS}")
        conn.execute("SELECT pg_advisory_lock(%s)", (_ADVISORY_LOCK_KEY,))
        try:
            applied_before = {
                r[0] for r in conn.execute("SELECT filename FROM schema_migrations").fetchall()
            }
            pending = [f for f in files if f.name not in applied_before]
            result = MigrationResult(
                "up_to_date", total=len(files), already_applied=len(applied_before),
                pending=[f.name for f in pending],
            )
            out.info("Pending migrations: %d (of %d total, %d already applied)",
                     len(pending), len(files), len(applied_before))
            if not pending:
                out.info("Database is up to date.")
                return result
            if dry_run:
                for f in pending:
                    out.info("  would apply %s", f.name)
                result.detail = "dry run — nothing applied"
                return result

            for f in pending:
                out.info("Applying migration %s", f.name)
                # Each file carries its own BEGIN/COMMIT and is idempotent, so it runs on
                # the autocommit connection and is then recorded. A crash between the two
                # only means the file re-applies (harmlessly) on the next boot.
                conn.execute(f.read_text(encoding="utf-8"))
                conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s) "
                    "ON CONFLICT (filename) DO NOTHING", (f.name,),
                )
                result.applied.append(f.name)
            result.status = "applied"
            out.info("Migration complete. Applied %d migration(s); database is at %s.",
                     len(result.applied), files[-1].name)
            return result
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (_ADVISORY_LOCK_KEY,))
