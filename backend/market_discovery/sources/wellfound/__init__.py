"""Wellfound discovery connector.

Registered on import (``SourceRegistry.autodiscover()`` imports this package), but
registration alone runs nothing: a source must also be named in
``DISCOVERY_SOURCES``. That two-step is deliberate — this connector crawls a third
party, so going live is an explicit configuration decision, never a side effect of
shipping the code.

    DISCOVERY_SOURCES=wellfound
"""
from __future__ import annotations

from backend.market_discovery.registry import register
from backend.market_discovery.sources.wellfound.config import WellfoundConfig
from backend.market_discovery.sources.wellfound.connector import (
    BlockedByProvider,
    WellfoundSource,
)

__all__ = ["BlockedByProvider", "WellfoundConfig", "WellfoundSource"]

register(WellfoundSource(), replace=True)
