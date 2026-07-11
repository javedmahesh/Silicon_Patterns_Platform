"""Local SQLite bootstrap for offline P0 review/testing — NO Supabase needed.

Builds the resolution-layer tables from the ORM models in a SQLite database
(file or in-memory) so you can exercise the normalizer and resolver before any
production database exists. Production uses the SQL migrations against Postgres;
this helper is strictly for local development and the P0 test-suite.
"""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine, event, inspect as sa_inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.enums import (
    DM_NOTE_TYPES,
    OUTREACH_ACTIVITY_TYPES,
    OUTREACH_MESSAGE_STATUSES,
    USER_AUDIT_ACTIONS,
    USER_ROLES,
)
from master_db.models import Base

logger = logging.getLogger("master_db.local")


def _enable_sqlite_fk(engine: Engine) -> None:
    """SQLite ignores foreign keys unless asked; turn them on so the local DB
    enforces the same FK/cascade behaviour the Postgres schema will."""

    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


def _reconcile_sqlite_columns(engine: Engine) -> None:
    """Dev-only self-heal: ``ADD COLUMN`` for model columns missing from an
    already-existing SQLite table.

    ``create_all`` issues ``CREATE TABLE IF NOT EXISTS`` — it creates missing
    *tables* but never adds a newly-modelled *column* to a table that already
    exists, so a long-lived local DB silently drifts whenever a model gains a
    column (e.g. ``users.last_seen_at``). Postgres is owned by the SQL migrations
    and is left untouched.
    """
    if engine.dialect.name != "sqlite":
        return
    insp = sa_inspect(engine)
    existing = set(insp.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing:
            continue
        have = {c["name"] for c in insp.get_columns(table.name)}
        missing = [c for c in table.columns if c.name not in have]
        if not missing:
            continue
        with engine.begin() as conn:
            for col in missing:
                if not col.nullable and col.default is None and col.server_default is None:
                    logger.warning(
                        "local schema: %s.%s is NOT NULL with no default — add it via a migration",
                        table.name, col.name,
                    )
                    continue
                ddl_type = col.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {ddl_type}'))
                logger.info("local schema: added %s.%s (%s)", table.name, col.name, ddl_type)


def _reconcile_dm_note_constraint(engine: Engine) -> None:
    """Dev-only self-heal: rebuild ``decision_maker_notes`` when its ``note_type``
    CHECK is stale.

    ``_reconcile_sqlite_columns`` can add a missing *column* but cannot alter a
    CHECK constraint, and ``create_all`` won't touch a table that already exists.
    So a long-lived local DB created when only ('team','personal') were allowed
    would reject the new 'admin'/'manager' notes. Here we detect that case and
    rebuild the one table in place (rows preserved). Postgres is owned by the SQL
    migrations (0022) and is left untouched.
    """
    if engine.dialect.name != "sqlite":
        return
    insp = sa_inspect(engine)
    if "decision_maker_notes" not in insp.get_table_names():
        return
    with engine.begin() as conn:
        sql = conn.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='decision_maker_notes'"
        ).scalar() or ""
        # Only act on a stale CHECK: present, but not allowing every current value.
        if "CHECK" not in sql.upper() or "note_type" not in sql:
            return
        if all(f"'{t}'" in sql for t in DM_NOTE_TYPES):
            return  # already permits all current note types — nothing to do
        cols = "id, decision_maker_id, note_type, created_by, author_email, content, created_at, updated_at"
        rows = conn.exec_driver_sql(f"SELECT {cols} FROM decision_maker_notes").all()
        conn.exec_driver_sql("DROP TABLE decision_maker_notes")
        Base.metadata.tables["decision_maker_notes"].create(bind=conn)  # new CHECK + indexes
        if rows:
            conn.execute(
                text(
                    "INSERT INTO decision_maker_notes "
                    "(id, decision_maker_id, note_type, created_by, author_email, content, created_at, updated_at) "
                    "VALUES (:id, :dm, :nt, :cb, :ae, :c, :ca, :ua)"
                ),
                [dict(id=r[0], dm=r[1], nt=r[2], cb=r[3], ae=r[4], c=r[5], ca=r[6], ua=r[7]) for r in rows],
            )
        logger.info("local schema: rebuilt decision_maker_notes for new note_type values (%d rows kept)", len(rows))


def _reconcile_outreach_msg_constraint(engine: Engine) -> None:
    """Dev-only self-heal: rebuild ``outreach_messages`` when its ``status`` CHECK is stale."""
    if engine.dialect.name != "sqlite":
        return
    insp = sa_inspect(engine)
    if "outreach_messages" not in insp.get_table_names():
        return
    with engine.begin() as conn:
        sql = conn.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='outreach_messages'"
        ).scalar() or ""
        if "CHECK" not in sql.upper():
            return
        if all(f"'{s}'" in sql for s in OUTREACH_MESSAGE_STATUSES):
            return
        old_col_names = [c.strip() for c in (
            "id, outreach_lead_id, decision_maker_id, template_id, created_by, approved_by, "
            "direction, status, to_email, from_email, subject, body, thread_id, "
            "failed_reason, approved_at, sent_at, created_at, updated_at"
        ).split(",")]
        table = Base.metadata.tables["outreach_messages"]
        rows = conn.exec_driver_sql(f"SELECT {', '.join(old_col_names)} FROM outreach_messages").all()
        conn.exec_driver_sql("DROP TABLE outreach_messages")
        table.create(bind=conn)
        if rows:
            # Core insert() (not raw text) so columns added since old_col_names was last
            # updated (retry_count, provider, is_read, ...) pick up their model ``default=``
            # instead of NULL, which would violate their NOT NULL constraint.
            conn.execute(table.insert(), [dict(zip(old_col_names, row)) for row in rows])
        logger.info("local schema: rebuilt outreach_messages for new status values (%d rows kept)", len(rows))


def _reconcile_outreach_activity_constraint(engine: Engine) -> None:
    """Dev-only self-heal: rebuild ``outreach_activities`` when its ``type`` CHECK is stale."""
    if engine.dialect.name != "sqlite":
        return
    insp = sa_inspect(engine)
    if "outreach_activities" not in insp.get_table_names():
        return
    with engine.begin() as conn:
        sql = conn.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='outreach_activities'"
        ).scalar() or ""
        if "CHECK" not in sql.upper():
            return
        if all(f"'{t}'" in sql for t in OUTREACH_ACTIVITY_TYPES):
            return
        rows = conn.exec_driver_sql(
            "SELECT id, outreach_lead_id, actor_id, actor_email, type, detail, created_at "
            "FROM outreach_activities"
        ).all()
        conn.exec_driver_sql("DROP TABLE outreach_activities")
        Base.metadata.tables["outreach_activities"].create(bind=conn)
        if rows:
            conn.execute(
                text(
                    "INSERT INTO outreach_activities "
                    "(id, outreach_lead_id, actor_id, actor_email, type, detail, created_at) "
                    "VALUES (:id, :lid, :aid, :ae, :t, :d, :ca)"
                ),
                [dict(id=r[0], lid=r[1], aid=r[2], ae=r[3], t=r[4], d=r[5], ca=r[6]) for r in rows],
            )
        logger.info(
            "local schema: rebuilt outreach_activities for new type values (%d rows kept)", len(rows)
        )


def _reconcile_users_role_constraint(engine: Engine) -> None:
    """Dev-only self-heal: rebuild ``users`` when its ``role`` CHECK is stale (e.g. a
    long-lived local DB created before "super_admin" existed). Many tables hold an FK
    to ``users.id``; foreign_keys is toggled off for the rebuild so those rows (kept,
    same ids) don't trip a spurious violation while the parent table briefly doesn't
    exist, then restored."""
    if engine.dialect.name != "sqlite":
        return
    insp = sa_inspect(engine)
    if "users" not in insp.get_table_names():
        return
    with engine.begin() as conn:
        sql = conn.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
        ).scalar() or ""
        if "CHECK" not in sql.upper() or all(f"'{r}'" in sql for r in USER_ROLES):
            return
        cols = ("id, email, google_sub, microsoft_oid, full_name, picture, role, status, is_active, "
                "login_count, created_at, last_login_at, last_seen_at, deleted_at, "
                "password_hash, must_change_password")
        rows = conn.exec_driver_sql(f"SELECT {cols} FROM users").all()
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        conn.exec_driver_sql("DROP TABLE users")
        Base.metadata.tables["users"].create(bind=conn)
        if rows:
            conn.execute(
                text(
                    "INSERT INTO users "
                    f"({cols}) VALUES "
                    "(:id,:em,:gs,:mso,:fn,:pic,:role,:st,:ia,:lc,:ca,:lla,:lsa,:da,:ph,:mcp)"
                ),
                [dict(id=r[0], em=r[1], gs=r[2], mso=r[3], fn=r[4], pic=r[5], role=r[6], st=r[7],
                      ia=r[8], lc=r[9], ca=r[10], lla=r[11], lsa=r[12], da=r[13],
                      ph=r[14], mcp=r[15]) for r in rows],
            )
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        logger.info("local schema: rebuilt users for new role values (%d rows kept)", len(rows))


def _reconcile_user_audit_constraint(engine: Engine) -> None:
    """Dev-only self-heal: rebuild ``user_audit_events`` when its ``action`` CHECK is
    stale (e.g. missing the newer "super_admin_bootstrap"/"denied" actions)."""
    if engine.dialect.name != "sqlite":
        return
    insp = sa_inspect(engine)
    if "user_audit_events" not in insp.get_table_names():
        return
    with engine.begin() as conn:
        sql = conn.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='user_audit_events'"
        ).scalar() or ""
        if "CHECK" not in sql.upper() or all(f"'{a}'" in sql for a in USER_AUDIT_ACTIONS):
            return
        cols = "id, target_user_id, target_email, actor_user_id, actor_email, action, detail, created_at"
        rows = conn.exec_driver_sql(f"SELECT {cols} FROM user_audit_events").all()
        conn.exec_driver_sql("DROP TABLE user_audit_events")
        Base.metadata.tables["user_audit_events"].create(bind=conn)
        if rows:
            conn.execute(
                text(
                    "INSERT INTO user_audit_events "
                    f"({cols}) VALUES "
                    "(:id,:tid,:te,:aid,:ae,:act,:d,:ca)"
                ),
                [dict(id=r[0], tid=r[1], te=r[2], aid=r[3], ae=r[4], act=r[5], d=r[6], ca=r[7]) for r in rows],
            )
        logger.info("local schema: rebuilt user_audit_events for new action values (%d rows kept)", len(rows))


def ensure_local_schema(engine: Engine) -> None:
    """Create any missing tables, then add any missing columns + heal stale
    constraints (SQLite dev only)."""
    Base.metadata.create_all(engine)
    _reconcile_sqlite_columns(engine)
    _reconcile_dm_note_constraint(engine)
    _reconcile_outreach_msg_constraint(engine)
    _reconcile_outreach_activity_constraint(engine)
    _reconcile_users_role_constraint(engine)
    _reconcile_user_audit_constraint(engine)


def make_engine(db_path: str | Path = ":memory:") -> Engine:
    url = "sqlite://" if db_path == ":memory:" else f"sqlite:///{db_path}"
    engine = create_engine(url, future=True)
    _enable_sqlite_fk(engine)
    ensure_local_schema(engine)
    return engine


def make_session_factory(db_path: str | Path = ":memory:") -> sessionmaker[Session]:
    return sessionmaker(bind=make_engine(db_path), future=True)
