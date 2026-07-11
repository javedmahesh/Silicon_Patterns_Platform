"""Apply the SQL migrations to the production Postgres database, in order, once each.

Idempotent + safe to re-run: a ``schema_migrations`` bookkeeping table records which
files have been applied, and each migration is wrapped in its own transaction. Every
migration file is already written defensively (``CREATE TABLE IF NOT EXISTS`` /
``ADD COLUMN IF NOT EXISTS``), so a partial history self-heals.

    # PowerShell / bash — DATABASE_URL points at the target Postgres
    python scripts/apply_migrations.py
    python scripts/apply_migrations.py --dry-run     # list what WOULD apply, change nothing

Uses DATABASE_URL from the environment / .env (postgresql[+psycopg]://...). Refuses to
run against SQLite (the local dev DB is built from the ORM via ensure_local_schema).
This is the production migration step — run it once per deploy, before/at startup.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

MIGRATIONS_DIR = ROOT / "master_db" / "migrations"

_RAW = os.environ.get("DATABASE_URL", "").strip()
if not _RAW:
    print("ERROR: DATABASE_URL is not set (postgresql+psycopg://... required).")
    raise SystemExit(2)
if _RAW.startswith("sqlite"):
    print("ERROR: DATABASE_URL points at SQLite. Local dev builds the schema from the ORM "
          "(master_db.local.ensure_local_schema); migrations run only against Postgres.")
    raise SystemExit(2)
PG_URL = _RAW.replace("postgresql+psycopg://", "postgresql://", 1)

import psycopg  # noqa: E402

_BOOKKEEPING = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    text PRIMARY KEY,
    applied_at  timestamptz NOT NULL DEFAULT now()
);
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="show pending migrations, apply nothing")
    ap.add_argument("--baseline", action="store_true",
                    help="mark ALL migration files as applied WITHOUT running them — for "
                         "adopting this tracker on a DB whose schema is already up to date")
    args = ap.parse_args()

    files = sorted(MIGRATIONS_DIR.glob("0*.sql"))
    if not files:
        print(f"No migration files found in {MIGRATIONS_DIR}")
        return 1

    with psycopg.connect(PG_URL, autocommit=True) as conn:
        conn.execute(_BOOKKEEPING)
        applied = {r[0] for r in conn.execute("SELECT filename FROM schema_migrations").fetchall()}
        pending = [f for f in files if f.name not in applied]

        if args.baseline:
            for f in pending:
                conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s) "
                             "ON CONFLICT (filename) DO NOTHING", (f.name,))
            print(f"baseline: marked {len(pending)} migration(s) as applied (nothing executed).")
            return 0

        print(f"migrations: {len(files)} total, {len(applied)} applied, {len(pending)} pending")
        if not pending:
            print("Database is up to date.")
            return 0
        if args.dry_run:
            print("PENDING (dry-run — nothing applied):")
            for f in pending:
                print(f"  - {f.name}")
            return 0

        for f in pending:
            sql = f.read_text(encoding="utf-8")
            print(f"applying {f.name} ...", end=" ", flush=True)
            # Each file carries its own BEGIN/COMMIT and is idempotent (IF NOT EXISTS),
            # so run it on the autocommit connection, then record it. A crash between the
            # two just re-applies (harmlessly) next run.
            conn.execute(sql)
            conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s) "
                         "ON CONFLICT (filename) DO NOTHING", (f.name,))
            print("ok")
    print(f"Applied {len(pending)} migration(s). Database is up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
