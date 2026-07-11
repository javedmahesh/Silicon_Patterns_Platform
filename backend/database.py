"""Database engine + connection pool + session factory.

Handles both the local SQLite master (for review/tests) and a pooled
Postgres/Supabase engine (production) from one ``DATABASE_URL``.
"""
from __future__ import annotations

import logging

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import Settings

logger = logging.getLogger("backend.database")


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


class Database:
    """Owns the SQLAlchemy engine + session factory for the app's lifetime."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = self._make_engine(settings)
        self.sessionmaker = sessionmaker(
            bind=self.engine, class_=Session, expire_on_commit=False, future=True
        )
        logger.info("database engine ready (%s)", self._safe_url(settings.database_url))

    @staticmethod
    def _safe_url(url: str) -> str:
        # never log credentials
        if "@" in url:
            return url.split("@", 1)[0].rsplit(":", 1)[0] + ":***@" + url.split("@", 1)[1]
        return url

    def _make_engine(self, s: Settings) -> Engine:
        if _is_sqlite(s.database_url):
            engine = create_engine(
                s.database_url, echo=s.db_echo, future=True,
                connect_args={"check_same_thread": False},
            )

            @event.listens_for(engine, "connect")
            def _enable_fk(dbapi_conn, _record):  # noqa: ANN001
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()

            # Local-dev self-heal: ensure the SQLite schema matches the models
            # (create_all alone never adds a newly-modelled column to an existing
            # table — this is what caused the users.last_seen_at drift). Postgres
            # is owned by the SQL migrations, so this is SQLite-only.
            from master_db.local import ensure_local_schema

            ensure_local_schema(engine)
            return engine

        # Postgres / Supabase / other server DBs: a real pooled engine.
        return create_engine(
            s.database_url, echo=s.db_echo, future=True, pool_pre_ping=True,
            pool_size=s.db_pool_size, max_overflow=s.db_max_overflow,
            pool_timeout=s.db_pool_timeout, pool_recycle=s.db_pool_recycle,
        )

    def dispose(self) -> None:
        self.engine.dispose()
        logger.info("database engine disposed")
