"""Integration layer for the Silicon Patterns platform.

The new join / resolution / orchestration code that unifies the four engines.
P0 ships the foundation only: :mod:`integration.normalizer` (canonical keys) and
:mod:`integration.resolver` (company resolution + stub/review-queue). Ingestors,
orchestrator and CLI arrive in later phases. No engine is modified by this package.
"""
