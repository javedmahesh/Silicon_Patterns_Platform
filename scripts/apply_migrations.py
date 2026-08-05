"""Apply the SQL migrations to the target Postgres database, in order, once each.

The platform applies pending migrations automatically at API startup (see
``backend/main.py`` and ``SP_AUTO_MIGRATE``), so a normal deploy needs no manual step.
This script is the same runner exposed as a CLI, for the cases where you want it
out-of-band: inspecting what would change, adopting the tracker on an existing
database, or migrating from CI.

    python scripts/apply_migrations.py                # apply everything pending
    python scripts/apply_migrations.py --dry-run      # list what WOULD apply
    python scripts/apply_migrations.py --baseline     # record all as applied, run nothing

Uses DATABASE_URL from the environment / .env. Refuses to run against SQLite (local
dev builds its schema from the ORM via ensure_local_schema).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from master_db.migrate import (  # noqa: E402
    MIGRATIONS_DIR,
    apply_pending,
    is_postgres,
    migration_files,
    pending_migrations,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="show pending migrations, apply nothing")
    ap.add_argument("--baseline", action="store_true",
                    help="mark ALL migration files as applied WITHOUT running them — for "
                         "adopting this tracker on a DB whose schema is already up to date")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("ERROR: DATABASE_URL is not set (postgresql+psycopg://... required).")
        return 2
    if not is_postgres(url):
        print("ERROR: DATABASE_URL does not point at Postgres. Local dev builds the schema "
              "from the ORM (master_db.local.ensure_local_schema); migrations run only "
              "against Postgres.")
        return 2
    if not migration_files():
        print(f"No migration files found in {MIGRATIONS_DIR}")
        return 1

    if args.baseline:
        import psycopg

        from master_db.migrate import _BOOKKEEPING, _pg_url

        names = pending_migrations(url)
        with psycopg.connect(_pg_url(url), autocommit=True) as conn:
            conn.execute(_BOOKKEEPING)
            for name in names:
                conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s) "
                             "ON CONFLICT (filename) DO NOTHING", (name,))
        print(f"baseline: marked {len(names)} migration(s) as applied (nothing executed).")
        return 0

    result = apply_pending(url, dry_run=args.dry_run)
    if result.status == "skipped":
        print(f"skipped: {result.detail}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
