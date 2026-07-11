"""News Intelligence — multi-source ingestion + rich opportunity extraction.

Upgrades the News Collection Engine into a production-grade intelligence layer,
feeding the *existing* downstream pipeline unchanged:

    News Sources -> News Collection Engine -> AI Opportunity Extraction
        -> Company Resolution -> Opportunities -> Lead Scoring -> Dashboard

Public surface:
  * :mod:`.adapters`   — pluggable source adapters (RSS, Google Alerts, file, ...).
  * :mod:`.dedup`      — canonical-url / normalized-title / semantic / entity dedup.
  * :mod:`.extraction` — deterministic, evidence-grounded multi-signal extraction.
  * :mod:`.engine`     — orchestrates collect -> extract -> resolve -> opportunities.
"""
from __future__ import annotations

from integration.news.engine import (
    NewsIntelligenceEngine,
    NewsRunMetrics,
    enabled_news_sources,
    enrich_opportunity,
    refresh_opportunities,
    seed_news_sources,
)

__all__ = [
    "NewsIntelligenceEngine",
    "NewsRunMetrics",
    "enabled_news_sources",
    "enrich_opportunity",
    "refresh_opportunities",
    "seed_news_sources",
]
