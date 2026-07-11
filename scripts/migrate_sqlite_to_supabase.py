"""One-time data migration: local SQLite master (`master_local.db`) -> the platform's
Supabase PostgreSQL database (the single source of truth after the DB unification).

Copies every application table VERBATIM — original primary keys, foreign keys,
timestamps, and audit history preserved exactly, no duplicates — then fixes each
serial sequence so the app's next insert doesn't collide. The one row that must
survive is the live Microsoft super_admin (bootstrap email) that was created directly
on Supabase during setup and never existed in SQLite; it is captured up front and
re-provisioned after the copy (with a fresh id past the migrated users, since SQLite
already owns the low ids).

Reads columns through the ORM models (not a raw reflection) so JSON/typed columns
round-trip correctly across dialects. FK triggers are disabled for the copy
(`session_replication_role = replica`, which the Supabase `postgres` role permits) so
insertion order — including the four self-referential tables (kb_categories,
crm_comments, org_units, outreach_messages) — never trips a constraint.

The whole Postgres side runs in ONE transaction: if anything fails it rolls back and
Supabase is left exactly as it was. Safe to re-run (it truncates + reloads).

    python scripts/migrate_sqlite_to_supabase.py [--yes]

Idempotent target reset: TRUNCATE ... RESTART IDENTITY CASCADE on the 109 model
tables only — Supabase's own auth/storage schemas are never touched.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.orm import Session

from backend.config import get_settings
from master_db.models import Base, User

SQLITE_PATH = ROOT / "master_local.db"
BOOTSTRAP_EMAIL = (get_settings().bootstrap_admin_email or "").strip().lower()


def _serial_sequence(conn, table: str, col: str) -> str | None:
    return conn.execute(text("SELECT pg_get_serial_sequence(:t, :c)"), {"t": table, "c": col}).scalar()


def _default_value(col):
    """Resolve a column's Python-side default scalar, so a NULL carried over from
    SQLite (which self-healed newer NOT-NULL columns as nullable) becomes the value
    the ORM would have written — e.g. users.must_change_password NULL -> False."""
    d = col.default
    if d is None:
        return None
    if getattr(d, "is_scalar", False):
        return d.arg
    if getattr(d, "is_callable", False):
        try:
            return d.arg({})
        except Exception:
            return None
    return None


def main(assume_yes: bool = False) -> int:
    if not SQLITE_PATH.exists():
        print(f"ERROR: {SQLITE_PATH} not found — nothing to migrate.")
        return 2

    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        print("ERROR: DATABASE_URL resolves to SQLite — set the Supabase URL in .env first.")
        return 2

    sqlite_engine = create_engine(f"sqlite:///{SQLITE_PATH.as_posix()}", future=True)
    pg_engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)

    masked = settings.database_url.split("@", 1)
    print(f"SOURCE : sqlite:///{SQLITE_PATH.as_posix()}")
    print(f"TARGET : {masked[0].rsplit(':', 1)[0]}:***@{masked[1] if len(masked) > 1 else ''}")
    if not assume_yes:
        print("\nThis TRUNCATES the target's 109 application tables and reloads them from SQLite.")
        print("Re-run with --yes to proceed.")
        return 0

    sqlite_cols = {t: {c["name"] for c in inspect(sqlite_engine).get_columns(t)}
                   for t in inspect(sqlite_engine).get_table_names()}
    tables = list(Base.metadata.sorted_tables)  # parent-first (only matters cosmetically under replica)

    # --- capture the live Supabase-only super_admin before we wipe the table -------
    prud: dict | None = None
    with pg_engine.connect() as c:
        row = c.execute(select(User).where(func.lower(User.email) == BOOTSTRAP_EMAIL)).mappings().first()
        prud = dict(row) if row else None

    # Minimal reset scope: only the tables that actually hold rows in the target need
    # clearing before the load — every other model table is already empty, so we never
    # touch it. On a fresh Supabase this is just the bootstrap user + backend-seeded
    # system labels + that user's session-audit rows (all preserved/regenerated), not a
    # bulk wipe of the schema.
    with pg_engine.connect() as c:
        nonempty = [t.name for t in tables
                    if (c.execute(text(f'SELECT COUNT(*) FROM "{t.name}"')).scalar() or 0) > 0]
    print(f"\nTarget tables to clear before load (non-empty only): {nonempty or 'none'}")

    copied: dict[str, int] = {}
    with pg_engine.begin() as pg:
        pg.execute(text("SET TIME ZONE 'UTC'"))
        pg.execute(text("SET session_replication_role = replica"))  # FK triggers off for clear + copy

        for name in nonempty:
            pg.execute(text(f'DELETE FROM "{name}"'))

        # Most PKs are `GENERATED ALWAYS AS IDENTITY`, which rejects the explicit id
        # values we must preserve. Flip them to `GENERATED BY DEFAULT` for the copy and
        # restore `ALWAYS` at the end — net-zero schema change, atomic with the copy.
        model_names = {t.name for t in tables}
        always_idents = [
            (r[0], r[1]) for r in pg.execute(text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND is_identity='YES' AND identity_generation='ALWAYS'"
            )).fetchall() if r[0] in model_names
        ]
        for tn, cn in always_idents:
            pg.execute(text(f'ALTER TABLE "{tn}" ALTER COLUMN "{cn}" SET GENERATED BY DEFAULT'))

        with sqlite_engine.connect() as sc:
            for t in tables:
                have = sqlite_cols.get(t.name)
                if not have:
                    copied[t.name] = 0
                    continue
                cols = [t.c[name] for name in (col.name for col in t.columns) if name in have]
                rows = [dict(r) for r in sc.execute(select(*cols)).mappings()]
                # Fill NULLs on NOT-NULL columns with the ORM default (keeps every row's
                # key set identical, which SQLAlchemy executemany requires).
                nn_defaults = {c.name: _default_value(c) for c in t.columns if not c.nullable}
                for r in rows:
                    for k, dv in nn_defaults.items():
                        if k in r and r[k] is None:
                            r[k] = dv
                if rows:
                    pg.execute(t.insert(), rows)
                copied[t.name] = len(rows)

        # --- realign every serial sequence past the migrated max id ----------------
        for t in tables:
            pk = list(t.primary_key.columns)
            if len(pk) != 1:
                continue
            col = pk[0].name
            seq = _serial_sequence(pg, t.name, col)
            if not seq:
                continue
            mx = pg.execute(text(f'SELECT COALESCE(MAX("{col}"), 0) FROM "{t.name}"')).scalar() or 0
            pg.execute(text("SELECT setval(:s, :v, true)"), {"s": seq, "v": max(int(mx), 1)})

        # --- guarantee the platform super_admin (bootstrap email) -------------------
        # The account may arrive from SQLite as an older 'admin' copy, or have existed
        # only on Supabase before this unification. Either way it must end as an active
        # super_admin (the explicitly-configured SP_BOOTSTRAP_ADMIN_EMAIL), with no
        # duplicate row and its Microsoft oid preserved.
        readded = False
        existing_id = pg.execute(
            select(User.id).where(func.lower(User.email) == BOOTSTRAP_EMAIL)
        ).scalar()
        if existing_id is not None:
            pg.execute(text(
                "UPDATE users SET role='super_admin', status='active', is_active=true "
                "WHERE lower(email) = :e"
            ), {"e": BOOTSTRAP_EMAIL})
            audit_id = existing_id
        elif prud is not None:
            payload = {k: v for k, v in prud.items() if k != "id"}
            payload.update(role="super_admin", status="active", is_active=True)
            pg.execute(User.__table__.insert(), [payload])
            audit_id = pg.execute(select(User.id).where(func.lower(User.email) == BOOTSTRAP_EMAIL)).scalar()
            readded = True
        else:
            audit_id = None
        if audit_id is not None:
            pg.execute(text(
                "INSERT INTO user_audit_events (target_user_id, target_email, actor_user_id, "
                "actor_email, action, detail, created_at) VALUES "
                "(:tid, :em, :tid, :em, 'role_changed', :d, now())"
            ), {"tid": audit_id, "em": BOOTSTRAP_EMAIL,
                "d": "super_admin confirmed after SQLite->Supabase data unification"})

        # Restore the original identity generation (schema nets out unchanged).
        for tn, cn in always_idents:
            pg.execute(text(f'ALTER TABLE "{tn}" ALTER COLUMN "{cn}" SET GENERATED ALWAYS'))

        pg.execute(text("SET session_replication_role = origin"))

    # --- verification: SQLite vs Supabase row counts ------------------------------
    print("\n=== ROW-COUNT VERIFICATION (SQLite -> Supabase) ===")
    mismatches = []
    with sqlite_engine.connect() as sc, pg_engine.connect() as pc:
        for t in tables:
            if copied.get(t.name, 0) == 0 and t.name not in sqlite_cols:
                continue
            s_n = sc.execute(text(f'SELECT COUNT(*) FROM "{t.name}"')).scalar() if t.name in sqlite_cols else 0
            p_n = pc.execute(text(f'SELECT COUNT(*) FROM "{t.name}"')).scalar()
            expected = s_n
            note = ""
            if t.name == "users" and readded:
                expected += 1
                note = "  (+1 bootstrap super_admin)"
            if t.name == "user_audit_events" and audit_id is not None:
                expected += 1
                note = "  (+1 provenance audit row)"
            ok = p_n == expected
            if not ok:
                mismatches.append((t.name, s_n, p_n))
            if s_n or p_n:
                print(f"  {t.name:32} sqlite={s_n:<7} supabase={p_n:<7} {'OK' if ok else 'MISMATCH'}{note}")

    if mismatches:
        print("\nFAILED — mismatched tables:", mismatches)
        return 1
    print("\nMIGRATION COMPLETE — all tables match (users = SQLite + 1 bootstrap super_admin).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(assume_yes="--yes" in sys.argv))
