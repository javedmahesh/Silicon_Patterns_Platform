"""NVIDIA Inception discovery connector.

Registered on import (``SourceRegistry.autodiscover()`` imports this package), but
registration alone runs nothing: a source must also be named in
``DISCOVERY_SOURCES``. Crawling a third party stays an explicit configuration
decision, never a side effect of shipping the code.

    DISCOVERY_SOURCES=nvidia_inception
"""
from __future__ import annotations

from backend.market_discovery.registry import register
from backend.market_discovery.sources.nvidia_inception.config import (
    NvidiaInceptionConfig,
    robots_allows,
)
from backend.market_discovery.sources.nvidia_inception.connector import NvidiaInceptionSource

__all__ = ["NvidiaInceptionConfig", "NvidiaInceptionSource", "robots_allows"]

register(NvidiaInceptionSource(), replace=True)
