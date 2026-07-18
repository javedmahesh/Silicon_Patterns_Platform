"""Historical data synchronization engine (Phase 2 — companies only).

A reusable, **read-only** engine that reconciles uploaded historical company data
against the master platform and produces a deterministic :class:`SyncPreview` of
what would be created / updated / left unchanged — without writing to the database
and without touching decision makers (that is Phase 3).

It reuses the platform's canonical layer end to end:
  * :mod:`integration.normalizer`  — domain / name_key / canonical id (here wrapped
    in an LRU cache so a company seen on 40 contact rows is normalized once).
  * :class:`master_db.models.CompanyAlias` + :mod:`sync.aliases` — the shared alias
    system (AMD ↔ Advanced Micro Devices …) also used by the four engines.

Public entry points::

    from sync import reconcile_companies, load_historical_companies, SyncPreview
"""
from sync.models import (
    CompanySyncResult,
    DmSyncPreview,
    DmSyncResult,
    DmSyncStats,
    FieldChange,
    HistoricalCompany,
    HistoricalDecisionMaker,
    SyncPreview,
    SyncStats,
)
from sync.company_sync import PlatformCompanyIndex, reconcile_companies
from sync.dm_sync import PlatformDecisionMakerIndex, reconcile_decision_makers
from sync.linkedin import canonical_linkedin_url
from sync.excel_source import load_historical_companies, load_historical_decision_makers

__all__ = [
    "reconcile_companies",
    "reconcile_decision_makers",
    "load_historical_companies",
    "load_historical_decision_makers",
    "canonical_linkedin_url",
    "PlatformCompanyIndex",
    "PlatformDecisionMakerIndex",
    "SyncPreview",
    "SyncStats",
    "CompanySyncResult",
    "DmSyncPreview",
    "DmSyncStats",
    "DmSyncResult",
    "FieldChange",
    "HistoricalCompany",
    "HistoricalDecisionMaker",
]
