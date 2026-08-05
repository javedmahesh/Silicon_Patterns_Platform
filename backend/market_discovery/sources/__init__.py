"""Discovery source connectors.

Empty by design in this phase: the framework must run correctly with zero sources,
and it does — a discovery run with nothing registered is a successful no-op.

A connector (Firecrawl, Wellfound, Dealroom, Crunchbase, a conference site, a VC
portfolio, a government registry, a company website) is added as one module here:

    # backend/market_discovery/sources/firecrawl.py
    from backend.market_discovery.base_source import DiscoverySource
    from backend.market_discovery.registry import register

    class FirecrawlSource(DiscoverySource):
        name = "firecrawl"
        def capabilities(self): ...
        def fetch(self, context): ...
        def normalize(self, raw, context): ...

    register(FirecrawlSource())

``SourceRegistry.autodiscover()`` imports every module in this package, so the
``register`` call is all the wiring there is. The engine, pipeline, resolver,
confidence model and scheduler stay untouched — that is the architectural
guarantee this package exists to protect.

A connector returns candidates and nothing more. It must never open a database
session, judge duplicates, assign confidence, or apply business rules.
"""
