"""Dialect-aware bulk upsert (INSERT ... ON CONFLICT DO UPDATE).

One round-trip per chunk instead of one-SELECT-plus-one-write per row. Works on
PostgreSQL (production) and SQLite (local/tests). Rows are chunked so a single
statement never exceeds the driver's bound-parameter limit (SQLite 32766,
Postgres 65535).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

# Conservative cap that holds for SQLite >= 3.32 (32766) and Postgres (65535).
_MAX_BIND_PARAMS = 20000


def bulk_upsert(
    session: Session,
    model: type,
    rows: list[dict[str, Any]],
    conflict_cols: list[str],
    update_cols: list[str] | None = None,
) -> int:
    """Upsert *rows* into *model*, keyed on *conflict_cols*, chunked to stay under
    the bound-parameter limit. Columns updated on conflict default to every
    inserted column except the conflict key(s). Returns rows submitted."""
    if not rows:
        return 0
    # SQLAlchemy expands the INSERT to every table column (filling defaults), so
    # size chunks by the table's column count, not the dict's keys.
    n_cols = max(1, len(model.__table__.columns))
    chunk_size = max(1, _MAX_BIND_PARAMS // n_cols)
    total = 0
    for start in range(0, len(rows), chunk_size):
        total += _upsert_chunk(session, model, rows[start:start + chunk_size], conflict_cols, update_cols)
    return total


def _upsert_chunk(session, model, rows, conflict_cols, update_cols) -> int:
    dialect = session.get_bind().dialect.name
    table = model.__table__
    inserted_cols = list(rows[0].keys())
    to_update = update_cols or [c for c in inserted_cols if c not in conflict_cols]

    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as _insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as _insert
    else:
        # Generic fallback: row-by-row merge (correctness over speed).
        for row in rows:
            pk = {c: row[c] for c in conflict_cols}
            if session.execute(table.select().filter_by(**pk)).first():
                session.execute(table.update().filter_by(**pk).values(**row))
            else:
                session.execute(table.insert().values(**row))
        return len(rows)

    stmt = _insert(table).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=conflict_cols,
        set_={c: getattr(stmt.excluded, c) for c in to_update},
    )
    session.execute(stmt)
    return len(rows)
