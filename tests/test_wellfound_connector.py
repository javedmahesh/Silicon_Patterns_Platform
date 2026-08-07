"""Wellfound discovery connector.

Covers the connector, pagination, normalization, configuration, incremental
discovery, error handling, crawling integration, logging, and the architectural
boundary that keeps a connector free of business logic.

No network: the connector is driven through a stub CrawlService, which is exactly
how it is wired in production (it only ever talks to that abstraction), so these
tests exercise the real integration path rather than a mock of it.
"""
import logging

import pytest

from backend.config import Settings
from backend.crawling.schemas import CrawlOptions, CrawlResult, CrawlStatus, PageContent
from backend.market_discovery.schemas import DiscoveryContext, SourceStatus
from backend.market_discovery.sources.wellfound import parser
from backend.market_discovery.sources.wellfound.config import WellfoundConfig
from backend.market_discovery.sources.wellfound.connector import (
    BlockedByProvider,
    WellfoundSource,
)

CHALLENGE_HTML = (
    "<html><head><title>wellfound.com</title></head><body>"
    "<p>Please enable JS and disable any ad blocker</p>"
    "<script src='https://ct.captcha-delivery.com/c.js'></script></body></html>"
)


# ------------------------------------------------------------------ helpers
def _page(url, *, title="", description="", text="", links=(), headings=(),
          metadata=None, html=""):
    return PageContent(url=url, canonical_url=url, title=title, description=description,
                       text=text, html=html, links=tuple(links), headings=tuple(headings),
                       metadata=metadata or {}, provider="stub", status_code=200)


class StubCrawl:
    """Stands in for CrawlService. Records every URL the connector requests."""

    def __init__(self, pages=None, *, fail=(), raise_on=()):
        self.pages = pages or {}
        self.fail = set(fail)
        self.raise_on = set(raise_on)
        self.requested: list[str] = []
        self.options: list[CrawlOptions] = []

    def fetch_page(self, url, options=None):
        self.requested.append(url)
        self.options.append(options)
        if url in self.raise_on:
            raise RuntimeError("crawl exploded")
        if url in self.fail:
            return CrawlResult(url=url, status=CrawlStatus.FAILED, error="HTTP 404",
                               provider="stub")
        page = self.pages.get(url)
        if page is None:
            return CrawlResult(url=url, status=CrawlStatus.FAILED, error="not found",
                               provider="stub")
        return CrawlResult(url=url, status=CrawlStatus.OK, pages=[page], provider="stub")

    def select_provider(self, options=None):
        class _P:
            name = "stub"

            def capabilities(self_inner):
                from backend.crawling.schemas import ProviderCapabilities
                return ProviderCapabilities(name="stub", renders_javascript=True)

        return _P()


def _config(**kw):
    base = dict(base_url="https://wellfound.com", listing_paths=("/startups",),
                max_pages=2, max_companies=10, fetch_company_pages=False,
                incremental=False)
    base.update(kw)
    return WellfoundConfig(**base)


def _source(crawl, **cfg):
    return WellfoundSource(config=_config(**cfg), crawl_service=crawl)


def _listing(page_number=1, slugs=("acme-semi", "globex")):
    url = ("https://wellfound.com/startups" if page_number == 1
           else f"https://wellfound.com/startups?page={page_number}")
    return url, _page(url, title="Startups",
                      links=[f"https://wellfound.com/company/{s}" for s in slugs],
                      headings=[s.replace("-", " ") for s in slugs])


# ================================================================= parsing
def test_company_slug_extraction():
    assert parser.company_slug("https://wellfound.com/company/acme-semi") == "acme-semi"
    assert parser.company_slug("https://wellfound.com/company/acme-semi/") == "acme-semi"
    assert parser.company_slug("https://wellfound.com/company/acme/jobs") == ""
    assert parser.company_slug("https://wellfound.com/startups") == ""
    assert parser.company_slug("not a url") == ""


def test_listing_yields_one_record_per_unique_company():
    _url, page = _listing(slugs=("acme-semi", "globex", "acme-semi"))
    records = parser.parse_listing_page(page)
    assert [r["slug"] for r in records] == ["acme-semi", "globex"]
    assert all(r["source_url"].startswith("https://wellfound.com/company/") for r in records)


def test_company_page_prefers_structured_data():
    page = _page(
        "https://wellfound.com/company/acme-semi",
        title="Acme Semiconductor — Jobs | Wellfound",
        metadata={"json_ld": [{"@type": "Organization", "name": "Acme Semiconductor",
                               "url": "https://acme-semi.com",
                               "description": "We design ASIC and SoC silicon.",
                               "address": {"addressLocality": "Bengaluru",
                                           "addressCountry": "India"}}]},
        text="Founded in 2019. 51-200 employees. Series A.",
    )
    raw = parser.parse_company_page(page)
    assert raw["company_name"] == "Acme Semiconductor"
    assert raw["website"] == "https://acme-semi.com"
    assert raw["description"] == "We design ASIC and SoC silicon."
    assert raw["headquarters"] == "Bengaluru, India" and raw["country"] == "India"
    assert raw["founded_year"] == "2019"
    assert raw["employee_count"] == "51-200" and raw["funding_stage"] == "series a"


def test_wellfound_urls_are_never_reported_as_the_company_website():
    page = _page("https://wellfound.com/company/acme",
                 title="Acme | Wellfound",
                 metadata={"og:url": "https://wellfound.com/company/acme"})
    assert "website" not in parser.parse_company_page(page)


def test_social_links_are_not_mistaken_for_a_homepage():
    page = _page("https://wellfound.com/company/acme", title="Acme",
                 links=["https://twitter.com/acme", "https://github.com/acme",
                        "https://www.linkedin.com/company/acme", "https://acme.com"])
    raw = parser.parse_company_page(page)
    assert raw["website"] == "https://acme.com"
    assert raw["linkedin_url"] == "https://www.linkedin.com/company/acme"


def test_missing_values_are_absent_never_invented():
    raw = parser.parse_company_page(_page("https://wellfound.com/company/mystery",
                                          title="Mystery | Wellfound"))
    for field in ("website", "description", "country", "founded_year", "employee_count",
                  "funding_stage", "headquarters"):
        assert field not in raw, f"{field} must not be fabricated"


def test_malformed_page_does_not_raise():
    assert isinstance(parser.parse_company_page(_page("https://wellfound.com/company/x")), dict)
    assert parser.parse_listing_page(_page("https://wellfound.com/startups")) == []


@pytest.mark.parametrize("marker", [
    "captcha-delivery", "Please enable JS", "datadome", "Just a moment",
])
def test_bot_challenge_pages_are_recognised(marker):
    assert parser.looks_blocked(_page("https://wellfound.com/startups", text=marker))


def test_a_real_page_is_not_mistaken_for_a_challenge():
    assert not parser.looks_blocked(_page("https://wellfound.com/company/acme",
                                          title="Acme", text="We design chips."))
    assert not parser.looks_blocked(None)


# ================================================================ connector
def test_discovers_companies_from_a_listing():
    url, page = _listing()
    crawl = StubCrawl({url: page})
    candidates = _source(crawl).discover(DiscoveryContext(run_id="r1"))
    assert [c.company_name for c in candidates] == ["acme semi", "globex"]
    assert all(c.source == "wellfound" for c in candidates)
    assert candidates[0].source_id == "acme-semi"


def test_company_pages_are_fetched_when_enabled():
    url, listing = _listing(slugs=("acme-semi",))
    detail = _page("https://wellfound.com/company/acme-semi",
                   title="Acme Semiconductor | Wellfound",
                   metadata={"json_ld": [{"@type": "Organization",
                                          "name": "Acme Semiconductor",
                                          "url": "https://acme-semi.com"}]})
    crawl = StubCrawl({url: listing, "https://wellfound.com/company/acme-semi": detail})
    candidates = _source(crawl, fetch_company_pages=True).discover(DiscoveryContext())
    assert candidates[0].company_name == "Acme Semiconductor"
    assert candidates[0].website == "https://acme-semi.com"
    assert "https://wellfound.com/company/acme-semi" in crawl.requested


def test_company_pages_are_skipped_when_disabled():
    url, listing = _listing(slugs=("acme-semi",))
    crawl = StubCrawl({url: listing})
    _source(crawl, fetch_company_pages=False, max_pages=1).discover(DiscoveryContext())
    assert crawl.requested == [url]      # listing only, no per-company request


def test_capabilities_declare_pagination_and_incremental():
    caps = WellfoundSource().capabilities()
    assert caps.supports_pagination and caps.supports_incremental
    assert not caps.requires_credentials      # public information only
    assert "website" in caps.provides


# =============================================================== pagination
def test_walks_multiple_listing_pages():
    u1, p1 = _listing(1, ("a", "b"))
    u2, p2 = _listing(2, ("c", "d"))
    crawl = StubCrawl({u1: p1, u2: p2})
    candidates = _source(crawl, max_pages=2).discover(DiscoveryContext())
    assert {c.source_id for c in candidates} == {"a", "b", "c", "d"}
    assert crawl.requested == [u1, u2]


def test_pagination_stops_at_the_configured_page_limit():
    pages = {}
    for n in range(1, 6):
        u, p = _listing(n, (f"c{n}",))
        pages[u] = p
    crawl = StubCrawl(pages)
    _source(crawl, max_pages=2).discover(DiscoveryContext())
    assert len(crawl.requested) == 2


def test_an_empty_page_ends_pagination_gracefully():
    u1, p1 = _listing(1, ("a",))
    u2 = "https://wellfound.com/startups?page=2"
    crawl = StubCrawl({u1: p1, u2: _page(u2, title="Startups")})      # no company links
    _source(crawl, max_pages=5).discover(DiscoveryContext())
    assert crawl.requested == [u1, u2]      # stopped after the empty page


def test_a_missing_page_ends_pagination_gracefully():
    u1, p1 = _listing(1, ("a",))
    crawl = StubCrawl({u1: p1})             # page 2 is simply absent
    candidates = _source(crawl, max_pages=4).discover(DiscoveryContext())
    assert [c.source_id for c in candidates] == ["a"]


def test_the_company_budget_is_enforced():
    u1, p1 = _listing(1, tuple(f"c{i}" for i in range(20)))
    crawl = StubCrawl({u1: p1})
    candidates = _source(crawl, max_companies=5).discover(DiscoveryContext())
    assert len(candidates) == 5


def test_the_engines_per_source_limit_wins_when_smaller():
    u1, p1 = _listing(1, tuple(f"c{i}" for i in range(20)))
    crawl = StubCrawl({u1: p1})
    candidates = _source(crawl, max_companies=15).discover(DiscoveryContext(limit=3))
    assert len(candidates) == 3


def test_duplicate_slugs_across_pages_are_returned_once():
    u1, p1 = _listing(1, ("acme", "globex"))
    u2, p2 = _listing(2, ("acme", "initech"))
    crawl = StubCrawl({u1: p1, u2: p2})
    candidates = _source(crawl, max_pages=2).discover(DiscoveryContext())
    assert sorted(c.source_id for c in candidates) == ["acme", "globex", "initech"]


def test_multiple_listing_paths_are_walked():
    u1, p1 = _listing(1, ("a",))
    u2 = "https://wellfound.com/discover/startups"
    crawl = StubCrawl({u1: p1, u2: _page(u2, links=["https://wellfound.com/company/b"])})
    candidates = _source(crawl, listing_paths=("/startups", "/discover/startups"),
                         max_pages=1).discover(DiscoveryContext())
    assert sorted(c.source_id for c in candidates) == ["a", "b"]


# ============================================================ normalization
def test_normalization_maps_onto_the_discovery_schema():
    source = WellfoundSource(config=_config(), crawl_service=StubCrawl())
    candidate = source.normalize({
        "slug": "acme-semi", "company_name": "Acme Semiconductor",
        "website": "https://acme-semi.com", "linkedin_url": "https://linkedin.com/company/acme",
        "description": "ASIC design house", "country": "India", "headquarters": "Bengaluru",
        "founded_year": "2019", "employee_count": "51-200", "funding_stage": "series a",
        "industry": "Semiconductors", "source_url": "https://wellfound.com/company/acme-semi",
        "headings": ["Silicon", "Careers"],
    }, DiscoveryContext())
    assert candidate.company_name == "Acme Semiconductor"
    assert candidate.website == "https://acme-semi.com"
    assert candidate.country == "India" and candidate.employee_count == "51-200"
    assert candidate.technologies == ("Silicon", "Careers")
    assert candidate.source_id == "acme-semi"
    assert candidate.raw_payload["slug"] == "acme-semi"


def test_normalization_never_invents_missing_values():
    source = WellfoundSource(config=_config(), crawl_service=StubCrawl())
    candidate = source.normalize({"slug": "mystery"}, DiscoveryContext())
    assert candidate.company_name == "mystery"      # the only public label available
    for value in (candidate.website, candidate.description, candidate.country,
                  candidate.founded_year, candidate.employee_count, candidate.funding_stage):
        assert value == ""


def test_a_record_with_no_identity_is_dropped():
    source = WellfoundSource(config=_config(), crawl_service=StubCrawl())
    assert source.normalize({}, DiscoveryContext()) is None
    assert source.normalize("not a dict", DiscoveryContext()) is None


def test_provenance_is_stamped_by_the_base_class():
    url, page = _listing(slugs=("acme",))
    candidates = _source(StubCrawl({url: page})).discover(DiscoveryContext())
    assert candidates[0].source == "wellfound"
    assert candidates[0].source_url.endswith("/company/acme")


# ======================================================= incremental discovery
def test_already_known_companies_are_skipped():
    from backend.market_discovery.normalize import normalize_candidate
    from backend.market_discovery.schemas import DiscoveryCandidate

    known = normalize_candidate(DiscoveryCandidate(company_name="acme", source="wellfound"))
    url, page = _listing(slugs=("acme", "globex"))
    crawl = StubCrawl({url: page})
    candidates = _source(crawl, incremental=True).discover(
        DiscoveryContext(known_candidate_keys=frozenset({known.candidate_key})))
    assert [c.source_id for c in candidates] == ["globex"]


def test_incremental_can_be_disabled():
    from backend.market_discovery.normalize import normalize_candidate
    from backend.market_discovery.schemas import DiscoveryCandidate

    known = normalize_candidate(DiscoveryCandidate(company_name="acme", source="wellfound"))
    url, page = _listing(slugs=("acme", "globex"))
    candidates = _source(StubCrawl({url: page}), incremental=False).discover(
        DiscoveryContext(known_candidate_keys=frozenset({known.candidate_key})))
    assert len(candidates) == 2


def test_a_full_run_has_no_known_keys():
    url, page = _listing(slugs=("acme",))
    candidates = _source(StubCrawl({url: page}), incremental=True).discover(DiscoveryContext())
    assert len(candidates) == 1


def test_the_engine_supplies_known_keys_from_the_database():
    """Incremental discovery without a source ever touching a session."""
    from master_db.local import make_session_factory
    from master_db.models import DiscoveryCandidateRecord
    from backend.market_discovery.pipeline import DiscoveryPipeline

    with make_session_factory(":memory:")() as session:
        session.add(DiscoveryCandidateRecord(candidate_key="abc123", company_name="Known"))
        session.commit()
        pipeline = DiscoveryPipeline(session=session)
        assert pipeline._known_keys() == frozenset({"abc123"})


def test_known_key_lookup_failure_degrades_to_a_full_run():
    from backend.market_discovery.pipeline import DiscoveryPipeline

    class Broken:
        def scalars(self, *a, **k):
            raise RuntimeError("db down")

    assert DiscoveryPipeline(session=Broken())._known_keys() == frozenset()


# =============================================================== configuration
def test_config_is_environment_driven():
    settings = Settings(_env_file=None, wellfound_max_pages=7, wellfound_max_companies=99,
                        wellfound_fetch_company_pages=False, wellfound_incremental=False,
                        wellfound_listing_paths_raw="/a,/b", wellfound_listing_query="stage=seed")
    config = WellfoundConfig.from_settings(settings)
    assert config.max_pages == 7 and config.max_companies == 99
    assert not config.fetch_company_pages and not config.incremental
    assert config.listing_paths == ("/a", "/b")
    assert config.listing_url("/a", 1) == "https://wellfound.com/a?stage=seed"
    assert config.listing_url("/a", 2) == "https://wellfound.com/a?stage=seed&page=2"


def test_empty_listing_paths_fall_back_to_the_public_defaults():
    from backend.market_discovery.sources.wellfound.config import DEFAULT_LISTING_PATHS

    config = WellfoundConfig.from_settings(Settings(_env_file=None))
    assert config.listing_paths == DEFAULT_LISTING_PATHS


def test_default_paths_are_outside_the_robots_disallow_set():
    """robots.txt disallows /_jobs/, /auth/, /u/, /projects/, /re/ and query variants."""
    from backend.market_discovery.sources.wellfound.config import DEFAULT_LISTING_PATHS

    disallowed = ("/_jobs/", "/auth/", "/u/", "/projects/", "/re/", "/embed/", "/documents/")
    for path in DEFAULT_LISTING_PATHS:
        assert not any(path.startswith(d) for d in disallowed)


def test_base_url_is_overridable():
    config = WellfoundConfig.from_settings(
        Settings(_env_file=None, wellfound_base_url="https://staging.example/"))
    assert config.company_url("acme") == "https://staging.example/company/acme"


# ============================================================== error handling
def test_a_crawl_failure_does_not_abort_the_source():
    u1, p1 = _listing(1, ("a",))
    detail_url = "https://wellfound.com/company/a"
    crawl = StubCrawl({u1: p1}, fail={detail_url})
    candidates = _source(crawl, fetch_company_pages=True).discover(DiscoveryContext())
    assert [c.source_id for c in candidates] == ["a"]      # listing data survives


def test_a_raising_crawl_service_is_contained():
    u1, p1 = _listing(1, ("a",))
    crawl = StubCrawl({u1: p1}, raise_on={"https://wellfound.com/company/a"})
    candidates = _source(crawl, fetch_company_pages=True).discover(DiscoveryContext())
    assert [c.source_id for c in candidates] == ["a"]


def test_a_blocked_listing_raises_so_the_pipeline_records_it():
    url = "https://wellfound.com/startups"
    crawl = StubCrawl({url: _page(url, title="wellfound.com",
                                  text="Please enable JS and disable any ad blocker")})
    with pytest.raises(BlockedByProvider, match="bot-protection challenge"):
        _source(crawl).discover(DiscoveryContext())


def test_a_blocked_company_page_leaves_the_listing_candidate_intact():
    u1, p1 = _listing(1, ("a",))
    detail_url = "https://wellfound.com/company/a"
    crawl = StubCrawl({u1: p1, detail_url: _page(detail_url, text="captcha-delivery")})
    candidates = _source(crawl, fetch_company_pages=True).discover(DiscoveryContext())
    assert [c.source_id for c in candidates] == ["a"]


def test_a_source_failure_does_not_stop_the_pipeline():
    from backend.market_discovery.pipeline import DiscoveryPipeline, PipelineConfig
    from backend.market_discovery.registry import SourceRegistry

    url = "https://wellfound.com/startups"
    blocked = _source(StubCrawl({url: _page(url, text="captcha-delivery")}))
    registry = SourceRegistry()
    registry.register(blocked)
    result = DiscoveryPipeline(
        config=PipelineConfig(enabled_sources=("wellfound",), retry_count=1,
                              retry_backoff_seconds=0.0),
        registry=registry).run(run_id="r")
    assert result.status == "failed" and result.failed_sources
    assert "bot-protection" in result.failed_sources[0].error


# ========================================================= crawling integration
def test_the_connector_only_talks_to_the_crawl_service():
    """It must never reach a provider — that is the infrastructure's job."""
    import ast
    import pathlib

    pkg = (pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_discovery"
           / "sources" / "wellfound")
    offenders = {}
    for f in pkg.rglob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = getattr(node, "body", None)
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    node.body = body[1:] or [ast.Pass()]
        code = ast.unparse(tree).lower()
        hits = [m for m in ("firecrawl", "httpx", "requests.get", "urlopen") if m in code]
        if hits:
            offenders[f.name] = hits
    assert offenders == {}, f"connector must use CrawlService only: {offenders}"


def test_the_connector_requests_javascript_rendering():
    url, page = _listing(slugs=("a",))
    crawl = StubCrawl({url: page})
    _source(crawl).discover(DiscoveryContext())
    assert crawl.options[0].render_javascript is True


def test_crawl_options_come_from_configuration():
    url, page = _listing(slugs=("a",))
    crawl = StubCrawl({url: page})
    _source(crawl, crawl_depth=3).discover(DiscoveryContext())
    assert crawl.options[0].max_depth == 3


def test_health_warns_when_the_provider_cannot_render_javascript():
    class PlainCrawl(StubCrawl):
        def select_provider(self, options=None):
            class _P:
                name = "http"

                def capabilities(self_inner):
                    from backend.crawling.schemas import ProviderCapabilities
                    return ProviderCapabilities(name="http", renders_javascript=False)

            return _P()

    health = _source(PlainCrawl()).health()
    assert health.status is SourceStatus.DEGRADED and "bot challenge" in health.detail


def test_health_is_unavailable_without_a_crawl_provider():
    class NoProvider(StubCrawl):
        def select_provider(self, options=None):
            raise RuntimeError("no usable crawl provider is registered")

    health = _source(NoProvider()).health()
    assert health.status is SourceStatus.UNAVAILABLE


# ===================================================================== logging
def test_start_and_completion_are_logged(caplog):
    url, page = _listing(slugs=("a", "b"))
    with caplog.at_level(logging.INFO, logger="market_discovery.wellfound"):
        _source(StubCrawl({url: page})).discover(DiscoveryContext(run_id="r7"))
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "started run=r7" in text
    assert "completed run=r7" in text and "pages_crawled=" in text and "companies=2" in text


def test_blocked_pages_are_logged_as_warnings(caplog):
    url = "https://wellfound.com/startups"
    with caplog.at_level(logging.WARNING, logger="market_discovery.wellfound"):
        with pytest.raises(BlockedByProvider):
            _source(StubCrawl({url: _page(url, text="captcha-delivery")})).discover(
                DiscoveryContext())
    assert "bot challenge" in "\n".join(r.getMessage() for r in caplog.records)


def test_skipped_known_companies_are_counted_in_the_log(caplog):
    from backend.market_discovery.normalize import normalize_candidate
    from backend.market_discovery.schemas import DiscoveryCandidate

    known = normalize_candidate(DiscoveryCandidate(company_name="acme", source="wellfound"))
    url, page = _listing(slugs=("acme", "globex"))
    with caplog.at_level(logging.INFO, logger="market_discovery.wellfound"):
        _source(StubCrawl({url: page}), incremental=True).discover(
            DiscoveryContext(known_candidate_keys=frozenset({known.candidate_key})))
    assert "skipped_known=1" in "\n".join(r.getMessage() for r in caplog.records)


# ====================================================== architectural boundary
def test_the_connector_has_no_database_access():
    import ast
    import pathlib

    pkg = (pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_discovery"
           / "sources" / "wellfound")
    offenders = {}
    for f in pkg.rglob("*.py"):
        code = f.read_text(encoding="utf-8")
        hits = [m for m in ("sqlalchemy", "session.", "master_db", "Session") if m in code]
        if hits:
            offenders[f.name] = hits
    assert offenders == {}, f"connector must not touch the database: {offenders}"


def test_the_connector_contains_no_business_logic():
    """No confidence, no dedup, no resolution, no events — all engine concerns."""
    import ast
    import pathlib

    pkg = (pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_discovery"
           / "sources" / "wellfound")
    banned = ("confidenceengine", "confidence_score", "resolve_to_company", "discoveryresolver",
              "events.emit", "company_domain", "lead_score", "priority_tier")
    offenders = {}
    for f in pkg.rglob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = getattr(node, "body", None)
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    node.body = body[1:] or [ast.Pass()]
        code = ast.unparse(tree).lower()
        hits = [b for b in banned if b in code]
        if hits:
            offenders[f.name] = hits
    assert offenders == {}, f"connector must contain no business logic: {offenders}"


def test_no_bot_detection_evasion():
    """The platform reports a block; it never works around one."""
    import pathlib

    pkg = (pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_discovery"
           / "sources" / "wellfound")
    banned = ("mozilla/", "chrome/", "safari/", "webkit", "solve_captcha", "anticaptcha",
              "2captcha", "undetected", "stealth", "cf_clearance", "datadome_cookie")
    offenders = {}
    for f in pkg.rglob("*.py"):
        code = f.read_text(encoding="utf-8").lower()
        hits = [b for b in banned if b in code]
        if hits:
            offenders[f.name] = hits
    assert offenders == {}, f"no evasion is permitted: {offenders}"


# =========================================================== scheduler wiring
def test_the_connector_registers_itself_on_autodiscovery():
    from backend.market_discovery.registry import SourceRegistry

    registry = SourceRegistry()
    registry.autodiscover()
    assert "wellfound" in registry.names()


def test_registration_alone_does_not_enable_it():
    """Crawling a third party must be an explicit configuration decision."""
    from backend.market_discovery.registry import SourceRegistry

    registry = SourceRegistry()
    registry.autodiscover()
    assert registry.enabled_sources(Settings(_env_file=None).discovery_sources) == []
    assert [s.name for s in registry.enabled_sources(["wellfound"])] == ["wellfound"]


def test_no_scheduler_change_was_required():
    """The stage calls the registry; it never names a connector."""
    import ast
    import inspect
    import textwrap

    from orchestrator import stages

    tree = ast.parse(textwrap.dedent(inspect.getsource(stages.market_discovery_ingest)))
    fn = tree.body[0]
    if isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant):
        fn.body = fn.body[1:]
    assert "wellfound" not in ast.unparse(fn).lower()
