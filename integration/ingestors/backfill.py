"""Run every ingestor in dependency order against the master DB.

Order matters: **Industry Discovery first** so authoritative company rows exist
before the other engines attach (or stub) to them. Each ingestor is idempotent,
so the whole backfill is safe to re-run — it updates in place.

This is the P1 building block the P5 orchestrator/CLI will wrap. It does not
connect to Supabase: hand it any SQLAlchemy Session (local SQLite for review,
Postgres later).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Mapping

from sqlalchemy.orm import Session

from config.sources import find_source
from integration.ingestors.base import IngestionResult
from integration.ingestors.blog import BlogIngestor
from integration.ingestors.career import (
    CompanyRollupsIngestor,
    DemandSignalsIngestor,
    JobsIngestor,
)
from integration.ingestors.industry import IndustryIngestor
from integration.ingestors.linkedin import LinkedInIngestor

logger = logging.getLogger(__name__)

# Ordered: companies must land before the rows that reference them.
INGESTOR_ORDER: list[tuple[str, type]] = [
    ("industry", IndustryIngestor),
    ("blog", BlogIngestor),
    ("career_jobs", JobsIngestor),
    ("career_demand", DemandSignalsIngestor),
    ("career_intel", CompanyRollupsIngestor),
    ("linkedin", LinkedInIngestor),
]


def run_backfill(
    session: Session,
    *,
    sources: Mapping[str, str | Path] | None = None,
    create_stub: bool = True,
    mode: str = "pipeline",
) -> dict[str, IngestionResult]:
    """Run all ingestors. *sources* maps engine key -> path; any engine absent
    from the mapping falls back to :func:`config.sources.find_source`, and an
    engine with no available source is skipped (logged, not failed).

    Returns engine key -> :class:`IngestionResult`.
    """
    results: dict[str, IngestionResult] = {}
    for key, ingestor_cls in INGESTOR_ORDER:
        path = None
        if sources and key in sources:
            path = sources[key]
        else:
            path = find_source(key)
        if not path:
            logger.info("[backfill] no source for %s — skipped", key)
            continue
        ingestor = ingestor_cls(session, create_stub=create_stub, mode=mode)
        results[key] = ingestor.ingest(path)
    return results
