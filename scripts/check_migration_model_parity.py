"""Static parity check between master_db/migrations/*.sql and master_db/models.py.

Catches the class of bug that already happened once (see backend/database.py's
`ensure_local_schema` comment about `users.last_seen_at` drift): a column added to an
ORM model but never added to the SQL migrations (or vice versa), which SQLite's
`Base.metadata.create_all()` + `ensure_local_schema` self-heal masks in tests and dev,
but Postgres/Supabase — which is owned solely by the migrations — never gets.

No database connection required: this parses the .sql files textually and compares
against SQLAlchemy's own model metadata. Not a full SQL parser — just enough to track
CREATE TABLE column blocks (paren-depth aware, so CHECK (... IN (...)) constraints don't
confuse the top-level comma split) and ALTER TABLE ... ADD COLUMN IF NOT EXISTS lines,
which is the only DDL vocabulary this codebase's migrations actually use (see
master_db/migrations/README.md).

Usage:
    python scripts/check_migration_model_parity.py

Exit code 0 = no drift found, 1 = drift found (CI-friendly). Run this in CI on every PR
that touches master_db/models.py or master_db/migrations/*.sql.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MIGRATIONS_DIR = ROOT / "master_db" / "migrations"

_SKIP_PREFIXES = (
    "CONSTRAINT", "CHECK", "UNIQUE", "PRIMARY", "FOREIGN", "INDEX",
)


def _split_top_level(text: str) -> list[str]:
    """Split on commas at paren-depth 0 (so nested CHECK (... , ...) isn't split)."""
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if "".join(buf).strip():
        parts.append("".join(buf))
    return parts


def _extract_create_table_blocks(sql_text: str) -> dict[str, str]:
    """{table_name: raw column-definition block} for every CREATE TABLE (with or
    without IF NOT EXISTS — this codebase uses IF NOT EXISTS everywhere except a
    DROP-then-CREATE fix-up migration, where a bare CREATE TABLE is intentional)."""
    blocks: dict[str, str] = {}
    for m in re.finditer(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)\s*\(", sql_text, re.IGNORECASE):
        name = m.group(1).lower()
        start = m.end()
        depth = 1
        i = start
        while depth > 0 and i < len(sql_text):
            if sql_text[i] == "(":
                depth += 1
            elif sql_text[i] == ")":
                depth -= 1
            i += 1
        blocks[name] = sql_text[start:i - 1]
    return blocks


def _columns_in_block(block_text: str) -> set[str]:
    cols = set()
    for part in _split_top_level(block_text):
        stripped = part.strip()
        if not stripped:
            continue
        first_word = stripped.split(None, 1)[0].upper().strip(",")
        if first_word in _SKIP_PREFIXES:
            continue
        col_name = stripped.split(None, 1)[0].strip(",")
        cols.add(col_name.lower())
    return cols


def _extract_added_columns(sql_text: str) -> dict[str, set[str]]:
    """{table_name: {col, ...}} for every ALTER TABLE ... ADD COLUMN IF NOT EXISTS."""
    added: dict[str, set[str]] = {}
    for m in re.finditer(
        r"ALTER TABLE\s+(\w+)\s+ADD COLUMN IF NOT EXISTS\s+(\w+)", sql_text, re.IGNORECASE
    ):
        table, col = m.group(1).lower(), m.group(2).lower()
        added.setdefault(table, set()).add(col)
    return added


def _strip_sql_comments(sql_text: str) -> str:
    """Drop `-- ...` line comments (but not `--` inside a quoted string literal, which
    this codebase's migrations never use in a way that would trigger a false strip)."""
    return re.sub(r"--[^\n]*", "", sql_text)


def sql_schema_from_migrations() -> dict[str, set[str]]:
    """Merge every migration file's CREATE TABLE + ADD COLUMN statements into one
    {table_name: {columns}} view — the cumulative schema the migrations produce."""
    schema: dict[str, set[str]] = {}
    for sql_file in sorted(MIGRATIONS_DIR.glob("0*.sql")):
        text = _strip_sql_comments(sql_file.read_text(encoding="utf-8"))
        for table, block in _extract_create_table_blocks(text).items():
            schema.setdefault(table, set()).update(_columns_in_block(block))
        for table, cols in _extract_added_columns(text).items():
            schema.setdefault(table, set()).update(cols)
    return schema


def orm_schema_from_models() -> dict[str, set[str]]:
    from master_db.models import Base
    return {
        table_name: {c.name for c in table.columns}
        for table_name, table in Base.metadata.tables.items()
    }


def main() -> int:
    sql_schema = sql_schema_from_migrations()
    orm_schema = orm_schema_from_models()

    problems: list[str] = []

    orm_only_tables = sorted(set(orm_schema) - set(sql_schema))
    if orm_only_tables:
        problems.append(f"Tables in models.py with no CREATE TABLE in any migration: {orm_only_tables}")

    for table in sorted(set(orm_schema) & set(sql_schema)):
        orm_cols, sql_cols = orm_schema[table], sql_schema[table]
        missing_in_sql = sorted(orm_cols - sql_cols)
        if missing_in_sql:
            problems.append(f"{table}: ORM columns missing from migrations: {missing_in_sql}")
        extra_in_sql = sorted(sql_cols - orm_cols)
        if extra_in_sql:
            problems.append(f"{table}: migration columns not in the ORM model (possibly stale): {extra_in_sql}")

    sql_only_tables = sorted(set(sql_schema) - set(orm_schema))
    if sql_only_tables:
        problems.append(f"Tables created by a migration with no ORM model: {sql_only_tables}")

    print(f"Checked {len(orm_schema)} ORM tables against {len(sql_schema)} tables found in migrations.\n")
    if not problems:
        print("OK: no model <-> migration drift detected.")
        return 0

    print(f"FOUND {len(problems)} PARITY ISSUE(S):\n")
    for p in problems:
        print(f"  - {p}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
