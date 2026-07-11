"""FastAPI backend for the Silicon Patterns master platform (P4).

Layering (each layer depends only on the one below it):

    routers/      HTTP endpoints — params, status codes, response models
    services.py   business logic — assemble profiles, analytics, ORM->schema
    repositories.py   data access — SQLAlchemy queries over master_db.models
    database.py   engine + connection pool + session factory
    config.py     environment-based settings

Read-only over the master DB; it never writes engine data and never touches the
four scrapers.
"""
