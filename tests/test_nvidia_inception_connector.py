"""NVIDIA Inception discovery connector.

Covers parsing, normalization, enumeration/pagination, incremental discovery,
crawling integration, configuration, logging, failure handling, robots compliance,
and the architectural boundary that keeps a connector free of business logic.

No network: the connector is driven through a stub CrawlService, which is exactly how
it is wired in production (it only ever talks to that abstraction). The HTML fixtures
are reduced from real nvidia.com pages, so the parser is tested against the shapes it
actually meets.
"""
import logging

import pytest

from backend.config import Settings
from backend.crawling.schemas import CrawlOptions, CrawlResult, CrawlStatus, PageContent
from backend.market_discovery.schemas import DiscoveryContext
from backend.market_discovery.sources.nvidia_inception import parser
from backend.market_discovery.sources.nvidia_inception.config import (
    DEFAULT_INDEX_PATHS,
    NvidiaInceptionConfig,
    robots_allows,
)
from backend.market_discovery.sources.nvidia_inception.connector import NvidiaInceptionSource

BASE = "https://www.nvidia.com"
CS = f"{BASE}/en-us/case-studies"


# ------------------------------------------------------------------ helpers
def _page(url, *, title="", description="", text="", links=(), headings=(), metadata=None):
    return PageContent(url=url, canonical_url=url, title=title, description=description,
                       text=text, links=tuple(links), headings=tuple(headings),
                       metadata=metadata or {}, provider="stub", status_code=200)


def _study(slug, *, title, keywords="", description="", links=()):
    """A case-study page shaped like the real thing."""
    return _page(f"{CS}/{slug}/", title=title,
                 metadata={"description": description, "keywords": keywords,
                           "og:title": title},
                 links=links)


class StubCrawl:
    """Stands in for CrawlService. Records every URL the connector requests."""

    def __init__(self, pages=None, *, sitemap=(), fail=(), raise_on=(), sitemap_raises=False):
        self.pages = pages or {}
        self.sitemap = list(sitemap)
        self.fail = set(fail)
        self.raise_on = set(raise_on)
        self.sitemap_raises = sitemap_raises
        self.requested: list[str] = []
        self.sitemap_requests: list[str] = []
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

    def sitemap_urls(self, url, options=None):
        self.sitemap_requests.append(url)
        self.options.append(options)
        if self.sitemap_raises:
            raise RuntimeError("sitemap unavailable")
        return list(self.sitemap)

    def select_provider(self, options=None):
        class _P:
            name = "stub"

            def capabilities(self_inner):
                from backend.crawling.schemas import ProviderCapabilities
                return ProviderCapabilities(name="stub", renders_javascript=False)

        return _P()


def _config(**kw):
    base = dict(base_url=BASE, index_paths=(), max_pages=2, max_companies=10,
                fetch_company_pages=False, incremental=False, use_sitemap=True)
    base.update(kw)
    return NvidiaInceptionConfig(**base)


def _source(crawl, **cfg):
    return NvidiaInceptionSource(config=_config(**cfg), crawl_service=crawl)


# ============================================================ robots compliance
@pytest.mark.parametrize("url,allowed", [
    (f"{CS}/baseten/", True),
    (f"{CS}/", True),
    (f"{BASE}/en-us/startups/showcase/", True),
    (f"{CS}/?filters=%7B%7D", True),
    (f"{CS}/?page=2", False),                     # robots.txt: Disallow /*[?&]page=*
    (f"{CS}/?PAGE=2", False),                     # case-insensitive
    (f"{BASE}/en-us/x/?utm_source=nl", False),
    (f"{BASE}/en-us/x/?utm_campaign=a", False),
    (f"{BASE}/admin/x", False),
    (f"{BASE}/gated-resources/report.pdf", False),
    (f"{BASE}/content/g/secret", False),
    ("not a url", True),                          # no path/query to disallow
])
def test_robots_rules_are_enforced(url, allowed):
    assert robots_allows(url) is allowed


def test_default_index_paths_are_robots_allowed():
    for path in DEFAULT_INDEX_PATHS:
        assert robots_allows(f"{BASE}{path}")


def test_pagination_never_uses_the_disallowed_page_parameter():
    """robots.txt forbids ?page=; the sitemap is what makes it unnecessary."""
    import ast
    import pathlib

    pkg = (pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_discovery"
           / "sources" / "nvidia_inception")
    for f in pkg.rglob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert "page=" not in node.value.lower() or "disallow" in node.value.lower(), \
                    f"{f.name} builds a ?page= URL"


# ================================================================== parsing
@pytest.mark.parametrize("url,expected", [
    (f"{CS}/baseten/", "baseten"),
    (f"{CS}/serve-robotics", "serve-robotics"),
    (f"{CS}/", ""),
    (f"{BASE}/en-us/startups/", ""),
    ("not a url", ""),
])
def test_case_study_slug_extraction(url, expected):
    """The path is locale-prefixed, so the slug pattern must not anchor at the start."""
    assert parser.case_study_slug(url) == expected


def test_sitemap_urls_are_filtered_to_case_studies():
    urls = [f"{CS}/a/", f"{CS}/", f"{BASE}/en-us/geforce/", f"{CS}/b/", f"{CS}/a/"]
    assert parser.filter_case_study_urls(urls, base_url=BASE) == [f"{CS}/a/", f"{CS}/b/"]


def test_a_short_title_is_the_company_name():
    raw = parser.parse_case_study(_study(
        "lightwheel", title="Lightwheel | NVIDIA Customer Stories",
        description="Lightwheel leveraged NVIDIA Omniverse.",
        keywords="Lightwheel, NVIDIA Omniverse, Isaac Sim, NVIDIA Customer Stories"))
    assert raw["company_name"] == "Lightwheel"
    assert "name_uncertain" not in raw
    assert raw["technologies"] == ["NVIDIA Omniverse", "Isaac Sim"]   # name + boilerplate gone


def test_a_headline_title_falls_back_to_the_slug():
    raw = parser.parse_case_study(_study(
        "serve-robotics", title="Serve Robotics Autonomous Sidewalk Delivery | NVIDIA",
        description="Serve Robotics is pioneering autonomous sidewalk delivery."))
    assert raw["company_name"] == "Serve Robotics"
    assert "name_uncertain" not in raw


def test_a_headline_slug_is_flagged_as_uncertain():
    """Some studies publish no company name anywhere — say so, don't pretend."""
    raw = parser.parse_case_study(_study(
        "virtual-human-meets-virtual-studio-ai-powers-text-to-video",
        title="Virtual Human Meets Virtual Studio | NVIDIA"))
    assert raw["name_uncertain"] is True


def test_html_entities_are_decoded():
    raw = parser.parse_case_study(_study(
        "gac", title="GAC Group | NVIDIA Customer Stories",
        description="GAC R&amp;D Center built a transient simulation."))
    assert "R&D Center" in raw["description"] and "&amp;" not in raw["description"]


def test_the_company_website_must_match_the_company():
    """The first external link is regularly an unrelated third party."""
    raw = parser.parse_case_study(_study(
        "lightwheel", title="Lightwheel | NVIDIA Customer Stories",
        links=["https://mimicgen.github.io/", "https://www.lightwheel.ai/"]))
    assert raw["website"] == "https://www.lightwheel.ai/"


def test_a_deep_company_link_is_reduced_to_its_homepage():
    raw = parser.parse_case_study(_study(
        "baseten", title="Baseten | NVIDIA Customer Stories",
        links=["https://www.baseten.co/products/multi-cloud/"]))
    assert raw["website"] == "https://www.baseten.co/"


def test_an_unrelated_external_link_is_never_taken_as_the_website():
    raw = parser.parse_case_study(_study(
        "artisight", title="Artisight | NVIDIA Customer Stories",
        links=["https://partner.example.com/x", "https://twitter.com/nvidia"]))
    assert "website" not in raw


@pytest.mark.parametrize("host", [
    "https://www.nvidia.com/x", "https://twitter.com/a", "https://www.linkedin.com/company/a",
    "https://github.com/a", "https://www.youtube.com/a",
])
def test_publisher_and_social_hosts_are_never_the_website(host):
    raw = parser.parse_case_study(_study("acme", title="Acme | NVIDIA Customer Stories",
                                         links=[host]))
    assert "website" not in raw


def test_industry_is_never_derived_from_keywords():
    """Keyword lists are dominated by NVIDIA product names, which are not industries."""
    raw = parser.parse_case_study(_study(
        "x", title="Acme | NVIDIA Customer Stories",
        keywords="NVIDIA Omniverse, Isaac Sim, healthcare"))
    assert "industry" not in raw


def test_a_generic_og_description_is_not_treated_as_a_company_description():
    raw = parser.parse_case_study(_page(
        f"{CS}/acme/", title="Acme | NVIDIA Customer Stories",
        metadata={"og:description": "Read this customer story and more."}))
    assert "description" not in raw


def test_missing_values_are_absent_never_invented():
    raw = parser.parse_case_study(_page(f"{CS}/mystery/", title="Mystery | NVIDIA"))
    for field in ("website", "description", "technologies", "industry", "country",
                  "headquarters"):
        assert field not in raw, f"{field} must not be fabricated"


def test_malformed_pages_do_not_raise():
    assert isinstance(parser.parse_case_study(_page(f"{CS}/x/")), dict)
    assert parser.parse_index_page(_page(f"{CS}/")) == []


def test_index_pages_yield_one_record_per_case_study():
    page = _page(f"{CS}/", links=[f"{CS}/a/", f"{CS}/b/", f"{CS}/a/", f"{BASE}/en-us/geforce/"])
    assert [r["slug"] for r in parser.parse_index_page(page)] == ["a", "b"]


# ================================================================ enumeration
def test_the_sitemap_is_the_primary_enumeration_surface():
    crawl = StubCrawl(sitemap=[f"{CS}/a/", f"{BASE}/en-us/geforce/", f"{CS}/b/"])
    candidates = _source(crawl).discover(DiscoveryContext(run_id="r1"))
    assert [c.source_id for c in candidates] == ["a", "b"]
    assert crawl.sitemap_requests == [f"{BASE}/en-us/en-us.sitemap.xml"]


def test_the_sitemap_request_is_not_capped_by_the_company_budget():
    """One request returns thousands of URLs; the budget bounds fetches, not entries."""
    crawl = StubCrawl(sitemap=[f"{CS}/{i}/" for i in range(50)])
    _source(crawl, max_companies=3).discover(DiscoveryContext())
    assert crawl.options[0].max_pages >= 20_000


def test_the_company_budget_bounds_the_result():
    crawl = StubCrawl(sitemap=[f"{CS}/{i}/" for i in range(50)])
    assert len(_source(crawl, max_companies=4).discover(DiscoveryContext())) == 4


def test_the_engines_per_source_limit_wins_when_smaller():
    crawl = StubCrawl(sitemap=[f"{CS}/{i}/" for i in range(50)])
    got = _source(crawl, max_companies=20).discover(DiscoveryContext(limit=3))
    assert len(got) == 3


def test_index_pages_supplement_the_sitemap():
    crawl = StubCrawl(
        pages={f"{BASE}/en-us/startups/showcase/": _page(
            f"{BASE}/en-us/startups/showcase/", links=[f"{CS}/from-index/"])},
        sitemap=[f"{CS}/from-sitemap/"])
    got = _source(crawl, index_paths=("/en-us/startups/showcase/",),
                  max_companies=10).discover(DiscoveryContext())
    assert sorted(c.source_id for c in got) == ["from-index", "from-sitemap"]


def test_the_sitemap_can_be_disabled():
    crawl = StubCrawl(
        pages={f"{BASE}/en-us/case-studies/": _page(f"{CS}/", links=[f"{CS}/a/"])},
        sitemap=[f"{CS}/never/"])
    got = _source(crawl, use_sitemap=False,
                  index_paths=("/en-us/case-studies/",)).discover(DiscoveryContext())
    assert crawl.sitemap_requests == []
    assert [c.source_id for c in got] == ["a"]


def test_duplicate_urls_across_surfaces_are_returned_once():
    crawl = StubCrawl(
        pages={f"{BASE}/en-us/case-studies/": _page(f"{CS}/", links=[f"{CS}/a/"])},
        sitemap=[f"{CS}/a/"])
    got = _source(crawl, index_paths=("/en-us/case-studies/",)).discover(DiscoveryContext())
    assert [c.source_id for c in got] == ["a"]


def test_disallowed_urls_from_a_sitemap_are_dropped():
    crawl = StubCrawl(sitemap=[f"{CS}/ok/", f"{CS}/bad/?page=2"])
    assert [c.source_id for c in _source(crawl).discover(DiscoveryContext())] == ["ok"]


# ================================================================= detail pages
def test_case_study_pages_are_fetched_when_enabled():
    crawl = StubCrawl(
        pages={f"{CS}/lightwheel/": _study(
            "lightwheel", title="Lightwheel | NVIDIA Customer Stories",
            description="Lightwheel leveraged NVIDIA Omniverse.",
            links=["https://www.lightwheel.ai/"])},
        sitemap=[f"{CS}/lightwheel/"])
    got = _source(crawl, fetch_company_pages=True).discover(DiscoveryContext())
    assert got[0].company_name == "Lightwheel"
    assert got[0].website == "https://www.lightwheel.ai/"
    assert f"{CS}/lightwheel/" in crawl.requested


def test_detail_pages_are_skipped_when_disabled():
    crawl = StubCrawl(sitemap=[f"{CS}/a/"])
    _source(crawl, fetch_company_pages=False).discover(DiscoveryContext())
    assert crawl.requested == []


# =============================================================== normalization
def test_normalization_maps_onto_the_discovery_schema():
    source = NvidiaInceptionSource(config=_config(), crawl_service=StubCrawl())
    candidate = source.normalize({
        "slug": "lightwheel", "company_name": "Lightwheel",
        "website": "https://www.lightwheel.ai/", "description": "Robotics simulation.",
        "technologies": ["NVIDIA Omniverse", "Isaac Sim"], "headline": "A headline",
        "source_url": f"{CS}/lightwheel/",
    }, DiscoveryContext())
    assert candidate.company_name == "Lightwheel"
    assert candidate.website == "https://www.lightwheel.ai/"
    assert candidate.technologies == ("NVIDIA Omniverse", "Isaac Sim")
    assert candidate.source_id == "lightwheel"
    assert candidate.metadata["programme"].startswith("NVIDIA Inception")
    assert candidate.metadata["headline"] == "A headline"


def test_normalization_never_invents_missing_values():
    source = NvidiaInceptionSource(config=_config(), crawl_service=StubCrawl())
    candidate = source.normalize({"slug": "mystery"}, DiscoveryContext())
    assert candidate.company_name == "mystery"
    for value in (candidate.website, candidate.description, candidate.country,
                  candidate.industry, candidate.headquarters):
        assert value == ""


def test_an_uncertain_name_is_flagged_on_the_candidate():
    source = NvidiaInceptionSource(config=_config(), crawl_service=StubCrawl())
    candidate = source.normalize(
        {"slug": "x", "company_name": "A Long Headline", "name_uncertain": True},
        DiscoveryContext())
    assert candidate.metadata["name_uncertain"] is True


def test_a_record_with_no_identity_is_dropped():
    source = NvidiaInceptionSource(config=_config(), crawl_service=StubCrawl())
    assert source.normalize({}, DiscoveryContext()) is None
    assert source.normalize("not a dict", DiscoveryContext()) is None


def test_provenance_is_stamped_by_the_base_class():
    crawl = StubCrawl(sitemap=[f"{CS}/a/"])
    candidate = _source(crawl).discover(DiscoveryContext())[0]
    assert candidate.source == "nvidia_inception"
    assert candidate.source_url == f"{CS}/a/"


# ======================================================= incremental discovery
def test_already_seen_studies_are_skipped():
    crawl = StubCrawl(sitemap=[f"{CS}/a/", f"{CS}/b/"])
    got = _source(crawl, incremental=True).discover(
        DiscoveryContext(known_source_ids={"nvidia_inception": frozenset({"a"})}))
    assert [c.source_id for c in got] == ["b"]


def test_incremental_can_be_disabled():
    crawl = StubCrawl(sitemap=[f"{CS}/a/", f"{CS}/b/"])
    got = _source(crawl, incremental=False).discover(
        DiscoveryContext(known_source_ids={"nvidia_inception": frozenset({"a"})}))
    assert len(got) == 2


def test_another_sources_ids_do_not_cause_skips():
    crawl = StubCrawl(sitemap=[f"{CS}/a/"])
    got = _source(crawl, incremental=True).discover(
        DiscoveryContext(known_source_ids={"wellfound": frozenset({"a"})}))
    assert len(got) == 1


def test_incremental_moves_on_to_the_next_batch():
    """Skipping what is known frees budget for companies not yet seen."""
    crawl = StubCrawl(sitemap=[f"{CS}/{i}/" for i in range(6)])
    got = _source(crawl, incremental=True, max_companies=2).discover(
        DiscoveryContext(known_source_ids={"nvidia_inception": frozenset({"0", "1"})}))
    assert [c.source_id for c in got] == ["2", "3"]


# ============================================================== error handling
def test_a_sitemap_failure_does_not_abort_the_source():
    crawl = StubCrawl(
        pages={f"{BASE}/en-us/case-studies/": _page(f"{CS}/", links=[f"{CS}/a/"])},
        sitemap_raises=True)
    got = _source(crawl, index_paths=("/en-us/case-studies/",)).discover(DiscoveryContext())
    assert [c.source_id for c in got] == ["a"]      # fell back to the index page


def test_a_missing_detail_page_keeps_the_enumeration_record():
    crawl = StubCrawl(sitemap=[f"{CS}/a/"], fail={f"{CS}/a/"})
    got = _source(crawl, fetch_company_pages=True).discover(DiscoveryContext())
    assert [c.source_id for c in got] == ["a"]


def test_a_raising_crawl_service_is_contained():
    crawl = StubCrawl(sitemap=[f"{CS}/a/"], raise_on={f"{CS}/a/"})
    got = _source(crawl, fetch_company_pages=True).discover(DiscoveryContext())
    assert [c.source_id for c in got] == ["a"]


def test_a_layout_change_degrades_to_a_thin_candidate():
    """The page loads but publishes nothing recognizable — keep what we enumerated."""
    crawl = StubCrawl(pages={f"{CS}/a/": _page("https://elsewhere.example/")},
                      sitemap=[f"{CS}/a/"])
    got = _source(crawl, fetch_company_pages=True).discover(DiscoveryContext())
    assert [c.source_id for c in got] == ["a"]


def test_an_empty_run_is_not_an_error():
    assert _source(StubCrawl(sitemap=[])).discover(DiscoveryContext()) == []


def test_a_source_failure_does_not_stop_the_pipeline():
    from backend.market_discovery.pipeline import DiscoveryPipeline, PipelineConfig
    from backend.market_discovery.registry import SourceRegistry

    class Exploding(NvidiaInceptionSource):
        def fetch(self, context):
            raise RuntimeError("nvidia.com unreachable")

    registry = SourceRegistry()
    registry.register(Exploding(config=_config(), crawl_service=StubCrawl()))
    result = DiscoveryPipeline(
        config=PipelineConfig(enabled_sources=("nvidia_inception",), retry_count=1,
                              retry_backoff_seconds=0.0),
        registry=registry).run(run_id="r")
    assert result.status == "failed" and result.failed_sources


# ========================================================= crawling integration
def test_the_connector_only_talks_to_the_crawl_service():
    import ast
    import pathlib

    pkg = (pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_discovery"
           / "sources" / "nvidia_inception")
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


def test_javascript_rendering_is_not_requested():
    """These pages are server-rendered; asking for JS would push a paid provider."""
    crawl = StubCrawl(sitemap=[f"{CS}/a/"])
    _source(crawl, fetch_company_pages=True).discover(DiscoveryContext())
    assert all(o.render_javascript is False for o in crawl.options if o is not None)


def test_crawl_options_come_from_configuration():
    crawl = StubCrawl(sitemap=[f"{CS}/a/"])
    _source(crawl, crawl_depth=3, fetch_company_pages=True).discover(DiscoveryContext())
    page_options = [o for o in crawl.options if o.max_pages < 20_000]
    assert page_options and page_options[0].max_depth == 3


# =============================================================== configuration
def test_config_is_environment_driven():
    settings = Settings(_env_file=None, nvidia_inception_max_pages=5,
                        nvidia_inception_max_companies=99,
                        nvidia_inception_fetch_company_pages=False,
                        nvidia_inception_incremental=False,
                        nvidia_inception_use_sitemap=False,
                        nvidia_inception_index_paths_raw="/a,/b")
    config = NvidiaInceptionConfig.from_settings(settings)
    assert config.max_pages == 5 and config.max_companies == 99
    assert not config.fetch_company_pages and not config.incremental
    assert not config.use_sitemap and config.index_paths == ("/a", "/b")


def test_empty_index_paths_fall_back_to_the_public_defaults():
    assert NvidiaInceptionConfig.from_settings(
        Settings(_env_file=None)).index_paths == DEFAULT_INDEX_PATHS


def test_base_url_and_sitemap_are_overridable():
    config = NvidiaInceptionConfig.from_settings(Settings(
        _env_file=None, nvidia_inception_base_url="https://staging.example/",
        nvidia_inception_sitemap_path="/x.xml"))
    assert config.sitemap_url == "https://staging.example/x.xml"
    assert config.index_url("/en-us/case-studies/") == "https://staging.example/en-us/case-studies/"


def test_capabilities_declare_incremental_and_no_credentials():
    caps = NvidiaInceptionSource().capabilities()
    assert caps.supports_incremental and caps.supports_pagination
    assert not caps.requires_credentials
    assert {"company_name", "website", "description"} <= caps.provides


# ===================================================================== logging
def test_start_and_completion_are_logged(caplog):
    crawl = StubCrawl(sitemap=[f"{CS}/a/", f"{CS}/b/"])
    with caplog.at_level(logging.INFO, logger="market_discovery.nvidia_inception"):
        _source(crawl).discover(DiscoveryContext(run_id="r9"))
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "started run=r9" in text
    assert "completed run=r9" in text
    assert "pages_crawled=" in text and "companies=2" in text and "in " in text


def test_skipped_and_failed_counts_are_logged(caplog):
    crawl = StubCrawl(sitemap=[f"{CS}/a/", f"{CS}/b/"], fail={f"{CS}/b/"})
    with caplog.at_level(logging.INFO, logger="market_discovery.nvidia_inception"):
        _source(crawl, incremental=True, fetch_company_pages=True).discover(
            DiscoveryContext(known_source_ids={"nvidia_inception": frozenset({"a"})}))
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "skipped_known=1" in text and "failed_pages=1" in text


def test_a_disallowed_url_is_logged_as_a_warning(caplog):
    """Refused before the request — and, with nothing else to try, reported as a
    failure rather than as an empty but successful run."""
    from backend.market_discovery.sources.nvidia_inception.connector import EnumerationFailed

    crawl = StubCrawl(sitemap=[])
    with caplog.at_level(logging.WARNING, logger="market_discovery.nvidia_inception"):
        with pytest.raises(EnumerationFailed, match="before any request"):
            _source(crawl, use_sitemap=False,
                    index_paths=("/en-us/x/?page=2",)).discover(DiscoveryContext())
    assert "robots.txt" in "\n".join(r.getMessage() for r in caplog.records)
    assert crawl.requested == []                  # nothing was ever fetched


# ====================================================== architectural boundary
def test_the_connector_has_no_database_access():
    import pathlib

    pkg = (pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_discovery"
           / "sources" / "nvidia_inception")
    offenders = {}
    for f in pkg.rglob("*.py"):
        code = f.read_text(encoding="utf-8")
        hits = [m for m in ("sqlalchemy", "session.", "master_db", "Session") if m in code]
        if hits:
            offenders[f.name] = hits
    assert offenders == {}, f"connector must not touch the database: {offenders}"


def test_the_connector_contains_no_business_logic():
    import ast
    import pathlib

    pkg = (pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_discovery"
           / "sources" / "nvidia_inception")
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


# =========================================================== scheduler wiring
def test_the_connector_registers_itself_on_autodiscovery():
    from backend.market_discovery.registry import SourceRegistry

    registry = SourceRegistry()
    registry.autodiscover()
    assert "nvidia_inception" in registry.names()


def test_registration_alone_does_not_enable_it():
    from backend.market_discovery.registry import SourceRegistry

    registry = SourceRegistry()
    registry.autodiscover()
    assert registry.enabled_sources(Settings(_env_file=None).discovery_sources) == []
    assert [s.name for s in registry.enabled_sources(["nvidia_inception"])] == ["nvidia_inception"]


def test_no_scheduler_change_was_required():
    import ast
    import inspect
    import textwrap

    from orchestrator import stages

    tree = ast.parse(textwrap.dedent(inspect.getsource(stages.market_discovery_ingest)))
    fn = tree.body[0]
    if isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant):
        fn.body = fn.body[1:]
    assert "nvidia" not in ast.unparse(fn).lower()


def test_the_full_pipeline_persists_discovered_companies():
    """Scheduler → engine → connector → crawl service → resolver → confidence → DB."""
    from backend.market_discovery import run_discovery
    from backend.market_discovery.registry import SourceRegistry
    from master_db.local import make_session_factory
    from master_db.models import Company, DiscoveryCandidateRecord

    crawl = StubCrawl(
        pages={f"{CS}/nanosilicon/": _study(
            "nanosilicon", title="NanoSilicon | NVIDIA Customer Stories",
            description="NanoSilicon designs low-power ASIC and RISC-V SoC silicon for edge AI.",
            keywords="ASIC, RISC-V, edge AI, NVIDIA Customer Stories",
            links=["https://www.nanosilicon.io/"])},
        sitemap=[f"{CS}/nanosilicon/"])
    registry = SourceRegistry()
    registry.register(NvidiaInceptionSource(
        config=_config(fetch_company_pages=True), crawl_service=crawl))
    settings = Settings(_env_file=None, discovery_sources_raw="nvidia_inception",
                        discovery_concurrency=1)

    with make_session_factory(":memory:")() as session:
        result = run_discovery(session, settings, registry=registry)
        assert result.status == "success" and result.fetched == 1
        row = session.query(DiscoveryCandidateRecord).one()
        assert row.company_name == "NanoSilicon"
        assert row.company_domain == "nanosilicon.io"
        assert row.source == "nvidia_inception" and row.source_id == "nanosilicon"
        assert row.confidence > 0
        # Discovery parks candidates; promoting one into `companies` is a separate step.
        assert session.query(Company).count() == 0


def test_a_slug_in_the_keywords_meta_is_not_a_technology():
    """Some studies put ONLY the URL slug in keywords; it is not a technology area."""
    raw = parser.parse_case_study(_study(
        "paving-the-future-of-factories-with-nvidia-omniverse-enterprise",
        title="BMW | NVIDIA Customer Stories",
        keywords="paving-the-future-of-factories-with-nvidia-omniverse-enterprise"))
    assert raw["company_name"] == "BMW"
    assert "technologies" not in raw


def test_hyphenated_url_fragments_are_filtered_from_keywords():
    raw = parser.parse_case_study(_study(
        "x", title="Acme | NVIDIA Customer Stories",
        keywords="some-long-url-fragment-here, edge AI"))
    assert raw["technologies"] == ["edge AI"]


# ============================================== production zero-result diagnosis
# Production ran with DISCOVERY_SOURCES=nvidia and reported "0 processed". These pin
# the cause (the connector registers as `nvidia_inception`, so `nvidia` selects
# nothing) and the observability that now makes it self-evident from Run History.
def test_the_connector_registers_under_its_canonical_name():
    """Registration is verified, never assumed from the module existing."""
    from backend.market_discovery.registry import SourceRegistry

    registry = SourceRegistry()
    registry.autodiscover()
    assert "nvidia_inception" in registry.names()
    assert registry.get("nvidia_inception") is not None
    ok, reason = registry.get("nvidia_inception").validate()
    assert ok, reason


def test_the_configured_name_nvidia_selects_nothing():
    """The production defect, pinned: `nvidia` is not the connector's name."""
    from backend.market_discovery.registry import SourceRegistry

    registry = SourceRegistry()
    registry.autodiscover()
    settings = Settings(_env_file=None, discovery_sources_raw="nvidia")
    assert settings.discovery_sources == ["nvidia"]        # parsing is not the problem
    assert registry.enabled_sources(settings.discovery_sources) == []
    assert registry.missing_sources(settings.discovery_sources) == ["nvidia"]


def test_the_canonical_name_selects_the_connector():
    from backend.market_discovery.registry import SourceRegistry

    registry = SourceRegistry()
    registry.autodiscover()
    for raw in ("nvidia_inception", " NVIDIA_INCEPTION ", "nvidia_inception,"):
        selected = registry.enabled_sources(Settings(
            _env_file=None, discovery_sources_raw=raw).discovery_sources)
        assert [s.name for s in selected] == ["nvidia_inception"], raw


def test_a_misconfigured_name_suggests_the_registered_one():
    from backend.market_discovery.registry import SourceRegistry

    registry = SourceRegistry()
    registry.autodiscover()
    assert registry.suggest("nvidia") == "nvidia_inception"
    assert registry.suggest("nvidia-inception") == "nvidia_inception"
    assert registry.suggest("totally-unrelated") == ""


def test_a_misconfigured_source_fails_the_run_instead_of_looking_empty():
    """The observability fix: 'nvidia' must not read as a clean no-op."""
    from backend.market_discovery import run_discovery
    from backend.market_discovery.registry import SourceRegistry
    from master_db.local import make_session_factory

    registry = SourceRegistry()
    registry.autodiscover()
    with make_session_factory(":memory:")() as session:
        result = run_discovery(session, Settings(_env_file=None, discovery_sources_raw="nvidia"),
                               registry=registry)
    assert result.status == "failed"
    assert result.configured == 1 and result.executed == 0
    outcome = result.sources[0]
    assert outcome.name == "nvidia" and "not registered" in outcome.error
    assert "nvidia_inception" in outcome.error           # names the fix
    assert "configured=1 executed=0" in result.summary()


def test_no_configured_sources_stays_a_clean_no_op():
    """Backward compatibility: the shipped default must not start reporting failure."""
    from backend.market_discovery import run_discovery
    from backend.market_discovery.registry import SourceRegistry
    from master_db.local import make_session_factory

    with make_session_factory(":memory:")() as session:
        result = run_discovery(session, Settings(_env_file=None, discovery_sources_raw=""),
                               registry=SourceRegistry())
    assert result.status == "success" and result.sources == []
    assert result.configured == 0 and result.executed == 0


def test_the_stage_reports_the_misconfiguration_to_run_history(monkeypatch):
    """What an operator actually sees: status + the reason, not a silent success."""
    from backend.market_discovery import service
    from backend.market_discovery.registry import SourceRegistry
    from master_db.local import make_session_factory
    from orchestrator.stages import STAGES

    registry = SourceRegistry()
    registry.autodiscover()
    monkeypatch.setattr(service, "default_registry", registry)
    monkeypatch.setattr("backend.config.get_settings",
                        lambda: Settings(_env_file=None, discovery_sources_raw="nvidia"))
    with make_session_factory(":memory:")() as session:
        metrics = STAGES["market_discovery"].ingest(session)
    assert metrics.status == "failed"
    assert any("not registered" in e and "nvidia_inception" in e for e in metrics.errors)
    assert "configured=1 executed=0" in metrics.notes


def test_zero_fetched_is_distinguishable_from_a_misconfigured_source():
    """A source that ran and found nothing is a different state from one that never ran."""
    from backend.market_discovery import run_discovery
    from backend.market_discovery.registry import SourceRegistry
    from master_db.local import make_session_factory

    registry = SourceRegistry()
    registry.register(NvidiaInceptionSource(config=_config(), crawl_service=StubCrawl(sitemap=[])))
    with make_session_factory(":memory:")() as session:
        result = run_discovery(session, Settings(_env_file=None,
                                                 discovery_sources_raw="nvidia_inception"),
                               registry=registry)
    assert result.status == "success"                    # it ran; there was nothing there
    assert result.configured == 1 and result.executed == 1
    assert result.fetched == 0 and result.sources[0].error == ""


def test_already_seen_candidates_are_distinguishable_from_a_fetch_failure():
    """Incremental skip and provider failure both yield 0 fetched — for opposite reasons."""
    from backend.market_discovery.schemas import DiscoveryContext

    page = _study("nanosilicon", title="NanoSilicon | NVIDIA Customer Stories",
                  description="ASIC and RISC-V SoC design.",
                  links=["https://www.nanosilicon.io/"])
    url = f"{CS}/nanosilicon/"

    seen = _source(StubCrawl(pages={url: page}, sitemap=[url]),
                   fetch_company_pages=True, incremental=True)
    known = DiscoveryContext(known_source_ids={"nvidia_inception": frozenset({"nanosilicon"})})
    assert seen.discover(known) == []                    # already stored, nothing fetched

    broken = _source(StubCrawl(pages={}, sitemap=[url], fail={url}),
                     fetch_company_pages=True, incremental=False)
    # A failed page keeps its enumeration-level record, so the run degrades rather
    # than silently reporting the same zero an up-to-date run would.
    assert len(broken.discover(DiscoveryContext())) == 1


def test_connector_tests_never_touch_a_real_database():
    """Every connector test drives a stub crawl service and an in-memory database.

    Checked over the module's CODE with this function removed — otherwise the
    assertion's own vocabulary is the match it is looking for.
    """
    import ast
    import pathlib

    tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    tree.body = [n for n in tree.body
                 if not (isinstance(n, ast.FunctionDef) and n.name.endswith("real_database"))]
    code = ast.unparse(tree).lower()
    for marker in ("postgres", "supabase", "master_local", "database_url"):
        assert marker not in code, f"connector tests must not reference {marker}"
    # Every session in this module is in-memory.
    sessions = [n for n in ast.walk(tree)
                if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "make_session_factory"]
    assert sessions, "expected the persistence tests to build a session"
    assert all(isinstance(c.args[0], ast.Constant) and c.args[0].value == ":memory:"
               for c in sessions)


# ======================================= unreachable-source diagnosis (prod #2)
# Production reported `configured=1 executed=1 sources=1 fetched=0` with no error
# after the source name was corrected — the same signature a totally unreachable
# network produces. These pin the difference so the next run answers it outright.
class _DeadNetwork:
    """Every request fails, as behind blocked egress or a DNS/TLS failure."""

    def __init__(self):
        self.requested = []

    def fetch_page(self, url, options=None):
        self.requested.append(url)
        raise OSError("[Errno 101] Network is unreachable")

    def sitemap_urls(self, url, options=None):
        self.requested.append(url)
        raise OSError("[Errno 101] Network is unreachable")

    def select_provider(self, options=None):
        class _P:
            name = "http"
        return _P()


def test_an_unreachable_source_fails_instead_of_reporting_nothing_found():
    from backend.market_discovery.sources.nvidia_inception.connector import EnumerationFailed

    with pytest.raises(EnumerationFailed, match="retrieval problem"):
        _source(_DeadNetwork(), fetch_company_pages=True).discover(DiscoveryContext())


def test_an_unreachable_source_is_recorded_as_a_failed_source():
    """What Run History must show: failed, with the reason — not a silent success."""
    from backend.config import Settings
    from backend.market_discovery import run_discovery
    from backend.market_discovery.registry import SourceRegistry
    from master_db.local import make_session_factory

    registry = SourceRegistry()
    registry.register(NvidiaInceptionSource(config=_config(fetch_company_pages=True),
                                            crawl_service=_DeadNetwork()))
    settings = Settings(_env_file=None, discovery_sources_raw="nvidia_inception",
                        discovery_retry_count=1, discovery_concurrency=1)
    with make_session_factory(":memory:")() as session:
        result = run_discovery(session, settings, registry=registry, persist=False)

    assert result.status == "failed"
    assert result.configured == 1 and result.fetched == 0
    assert "retrieval problem" in result.sources[0].error
    assert result.failed_sources


def test_a_reachable_source_with_nothing_new_still_succeeds():
    """The other side of the same coin: enumeration answered, there was nothing."""
    from backend.config import Settings
    from backend.market_discovery import run_discovery
    from backend.market_discovery.registry import SourceRegistry
    from master_db.local import make_session_factory

    registry = SourceRegistry()
    registry.register(NvidiaInceptionSource(config=_config(),
                                            crawl_service=StubCrawl(sitemap=[])))
    with make_session_factory(":memory:")() as session:
        result = run_discovery(session, Settings(_env_file=None,
                                                 discovery_sources_raw="nvidia_inception"),
                               registry=registry, persist=False)
    assert result.status == "success" and result.fetched == 0
    assert result.sources[0].error == ""


def test_everything_already_seen_still_succeeds():
    """Third zero-result state: reachable, had data, all of it already stored."""
    url = f"{CS}/nanosilicon/"
    crawl = StubCrawl(pages={url: _study("nanosilicon",
                                         title="NanoSilicon | NVIDIA Customer Stories")},
                      sitemap=[url])
    source = _source(crawl, fetch_company_pages=True, incremental=True)
    got = source.discover(DiscoveryContext(
        known_source_ids={"nvidia_inception": frozenset({"nanosilicon"})}))
    assert got == []
    assert crawl.sitemap_requests                 # it DID reach the source
    assert crawl.requested == []                  # and skipped the known detail page


def test_a_partial_enumeration_failure_still_returns_what_it_reached():
    """A dead sitemap plus a live index page is a degraded run, not a failed one."""
    crawl = StubCrawl(pages={f"{BASE}/en-us/case-studies/": _page(f"{CS}/",
                                                                 links=[f"{CS}/a/"])},
                      sitemap_raises=True)
    got = _source(crawl, index_paths=("/en-us/case-studies/",)).discover(DiscoveryContext())
    assert [c.source_id for c in got] == ["a"]
