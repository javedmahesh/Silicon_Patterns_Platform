"""Master database package.

The authoritative schema lives in ``master_db/migrations/*.sql`` (PostgreSQL /
Supabase dialect). :mod:`master_db.models` provides SQLAlchemy ORM mirrors of
**all** master tables so the resolver and the ingestors can run and be
unit-tested against a local SQLite file with no Supabase credentials.
"""
