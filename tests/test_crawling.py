"""Web crawling infrastructure (backend/crawling).

Covers the provider contract and registry, extraction, caching, rate limiting,
retries, the service, configuration, failure handling and logging — plus the
architectural boundary that keeps this layer free of business logic.

No network. Providers are exercised against an httpx MockTransport, which is the
real client code path with a fake wire, so the request/response mapping is genuinely
tested rather than stubbed away.
"""
import logging
import threading
import time

import httpx
import pytest

from backend.config import Settings
from backend.crawling import base, cache as cache_mod
from backend.crawling.base import CrawlProvider
from backend.crawling.cache import InMemoryCrawlCache, NullCrawlCache, cache_key
from backend.crawling.extractor import absolute_links, extract, to_markdown
from backend.crawling.providers.firecrawl import FirecrawlProvider
from backend.crawling.providers.http import HttpCrawlProvider
from backend.crawling.rate_limit import RateLimitConfig, RateLimiter, TokenBucket, host_of
from backend.crawling.retry import RetryOutcome, RetryPolicy, is_retryable, with_retries
from backend.crawling.schemas import (
    CrawlOptions,
    CrawlResult,
    CrawlStatus,
    CrawlTimeout,
    PageContent,
    PermanentCrawlError,
    ProviderCapabilities,
    ProviderNotConfigured,
    ProviderStatus,
    RateLimited,
    TransientCrawlError,
)
from backend.crawling.service import CrawlConfig, CrawlService

HTML = """<!doctype html>
<html lang="en"><head>
<title>Acme Semiconductor</title>
<meta name="description" content="We design ASIC and SoC silicon.">
<meta property="og:title" content="Acme OG">
<link rel="canonical" href="https://acme.com/">
<script type="application/ld+json">{"@type":"Organization","name":"Acme"}</script>
<style>body{color:red}</style>
</head><body>
<h1>Acme Semiconductor</h1>
<h2>Careers</h2>
<p>We build chips in Bengaluru.</p>
<a href="/careers">Jobs</a>
<a href="/careers#apply">Jobs anchor</a>
<a href="https://partner.example.com/x">Partner</a>
<a href="mailto:hi@acme.com">Mail</a>
<script>var tracking = 1;</script>
</body></html>"""


# ------------------------------------------------------------------ fixtures
@pytest.fixture(autouse=True)
def _clean_registry():
    base.clear_providers()
    yield
    base.clear_providers()


def _settings(**kw):
    base_kw = dict(_env_file=None, crawl_retry_backoff_seconds=0.0,
                   crawl_retry_max_backoff_seconds=0.0)
    base_kw.update(kw)
    return Settings(**base_kw)


class FakeProvider(CrawlProvider):
    """A provider written exactly as a real one is."""

    name = "fake"

    def __init__(self, *, name="fake", pages=None, fail_times=0, error=None,
                 renders_js=True, supports_crawl=False, supports_sitemap=False,
                 valid=True, sitemap=None):
        self.name = name
        self._pages = pages if pages is not None else [PageContent(url="https://a.com", title="A")]
        self.fail_times = fail_times
        self.error = error or TransientCrawlError("provider hiccup")
        self._renders_js = renders_js
        self._supports_crawl = supports_crawl
        self._supports_sitemap = supports_sitemap
        self._valid = valid
        self._sitemap = sitemap or []
        self.calls = 0
        self.closed = False

    def capabilities(self):
        return ProviderCapabilities(
            name=self.name, renders_javascript=self._renders_js,
            supports_crawl=self._supports_crawl, supports_sitemap=self._supports_sitemap,
            requires_credentials=False)

    def validate(self):
        return (True, "") if self._valid else (False, "not configured")

    def fetch_page(self, url, options):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self.error
        page = self._pages[0]
        return PageContent(url=url, title=page.title, markdown=page.markdown,
                           links=page.links, provider=self.name)

    def crawl_site(self, url, options):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self.error
        return list(self._pages)

    def fetch_sitemap(self, url, options):
        if not self._supports_sitemap:
            raise NotImplementedError
        return list(self._sitemap)

    def close(self):
        self.closed = True


def _service(providers, **cfg):
    config = CrawlConfig(retry=RetryPolicy(attempts=1, base_delay_seconds=0.0, jitter=False),
                         **cfg)
    return CrawlService(config=config, providers={p.name: p for p in providers})


# ================================================================== extraction
def test_extracts_every_documented_field():
    page = extract(HTML, url="https://acme.com/about", include_html=True)
    assert page.title == "Acme Semiconductor"
    assert page.description == "We design ASIC and SoC silicon."
    assert page.canonical_url == "https://acme.com/"
    assert page.language == "en"
    assert page.headings == ("Acme Semiconductor", "Careers")
    assert page.metadata["og:title"] == "Acme OG"
    assert page.metadata["json_ld"] == [{"@type": "Organization", "name": "Acme"}]
    assert page.html and page.markdown and page.text


def test_script_and_style_content_is_never_page_text():
    page = extract(HTML, url="https://acme.com/")
    assert "var tracking" not in page.text and "color:red" not in page.text


def test_links_are_absolute_deduplicated_and_fragment_free():
    page = extract(HTML, url="https://acme.com/about")
    assert "https://acme.com/careers" in page.links
    assert page.links.count("https://acme.com/careers") == 1      # #apply collapsed
    assert "https://partner.example.com/x" in page.links
    assert not any(l.startswith("mailto:") for l in page.links)


@pytest.mark.parametrize("href", ["#top", "javascript:void(0)", "mailto:a@b.c", "tel:+1", "data:x"])
def test_non_navigable_hrefs_are_dropped(href):
    assert absolute_links([href], "https://acme.com/") == ()


def test_html_is_omitted_unless_requested():
    assert extract(HTML, url="https://acme.com/").html == ""
    assert extract(HTML, url="https://acme.com/", include_html=True).html


def test_malformed_html_does_not_raise():
    page = extract("<html><body><p>unclosed <div><h1>Title", url="https://x.com/")
    assert isinstance(page, PageContent) and "unclosed" in page.text


def test_empty_input_yields_an_empty_page():
    assert extract("", url="https://x.com/").empty


def test_markdown_carries_headings_and_body():
    md = to_markdown(HTML)
    assert md.startswith("# Acme Semiconductor")
    assert "## Acme Semiconductor" in md and "### Careers" in md
    assert "We build chips in Bengaluru." in md


def test_extraction_is_generic_not_domain_specific():
    """Infrastructure: no semiconductor vocabulary anywhere in the extractor."""
    import pathlib

    src = _code_only(pathlib.Path(__file__).resolve().parent.parent / "backend" / "crawling"
                     / "extractor.py").lower()
    for word in ("semiconductor", "asic", "chip", "company", "discovery"):
        assert word not in src, f"extractor must stay generic; found {word!r}"


def test_best_text_prefers_markdown_then_text():
    assert PageContent(markdown="M", text="T", html="H").best_text() == "M"
    assert PageContent(text="T", html="H").best_text() == "T"
    assert PageContent(html="H").best_text() == "H"


# ======================================================================= cache
def test_identical_requests_share_a_key():
    o = CrawlOptions(max_depth=2)
    assert cache_key("https://a.com", "page", "fake", o) == \
           cache_key("HTTPS://A.com", "page", "fake", o)


def test_key_changes_with_provider_and_content_affecting_options():
    o = CrawlOptions()
    baseline = cache_key("https://a.com", "page", "fake", o)
    assert cache_key("https://a.com", "page", "other", o) != baseline
    assert cache_key("https://a.com", "crawl", "fake", o) != baseline
    assert cache_key("https://a.com", "page", "fake", CrawlOptions(max_depth=3)) != baseline
    assert cache_key("https://a.com", "page", "fake", CrawlOptions(include_html=True)) != baseline


def test_key_ignores_options_that_do_not_change_content():
    """bypass/timeout change HOW we fetch, not WHAT comes back."""
    baseline = cache_key("https://a.com", "page", "fake", CrawlOptions())
    assert cache_key("https://a.com", "page", "fake", CrawlOptions(bypass_cache=True)) == baseline
    assert cache_key("https://a.com", "page", "fake",
                     CrawlOptions(timeout_seconds=99)) == baseline


def test_cache_round_trip_and_hit_flag():
    c = InMemoryCrawlCache()
    result = CrawlResult(url="https://a.com", pages=[PageContent(url="https://a.com")])
    assert c.get("k") is None
    c.set("k", result, ttl_seconds=60)
    hit = c.get("k")
    assert hit is not None and hit.from_cache and not result.from_cache   # original untouched


def test_cache_respects_ttl(monkeypatch):
    c = InMemoryCrawlCache()
    now = [1000.0]
    monkeypatch.setattr(cache_mod.time, "monotonic", lambda: now[0])
    c.set("k", CrawlResult(url="u"), ttl_seconds=10)
    now[0] += 5
    assert c.get("k") is not None
    now[0] += 6
    assert c.get("k") is None


def test_ttl_of_zero_disables_storage():
    c = InMemoryCrawlCache()
    c.set("k", CrawlResult(url="u"), ttl_seconds=0)
    assert c.get("k") is None


def test_cache_invalidate_and_clear():
    c = InMemoryCrawlCache()
    c.set("a", CrawlResult(url="a"), ttl_seconds=60)
    c.set("b", CrawlResult(url="b"), ttl_seconds=60)
    assert c.invalidate("a") and not c.invalidate("a")
    assert c.clear() == 1 and len(c) == 0


def test_cache_evicts_oldest_when_full():
    c = InMemoryCrawlCache(max_entries=2)
    for k in ("a", "b", "c"):
        c.set(k, CrawlResult(url=k), ttl_seconds=60)
        time.sleep(0.001)
    assert len(c) == 2 and c.get("a") is None


def test_cache_reports_hit_rate():
    c = InMemoryCrawlCache()
    c.set("k", CrawlResult(url="u"), ttl_seconds=60)
    c.get("k")
    c.get("missing")
    stats = c.stats()
    assert stats["hits"] == 1 and stats["misses"] == 1 and stats["hit_rate"] == 0.5


def test_null_cache_never_stores():
    c = NullCrawlCache()
    c.set("k", CrawlResult(url="u"), ttl_seconds=60)
    assert c.get("k") is None and c.clear() == 0


def test_cache_is_provider_agnostic():
    """It stores results, and knows nothing about who produced them."""
    import pathlib

    src = (pathlib.Path(__file__).resolve().parent.parent / "backend" / "crawling"
           / "cache.py").read_text(encoding="utf-8").lower()
    assert "firecrawl" not in src and "httpx" not in src


# ================================================================ rate limiting
def test_token_bucket_allows_burst_then_throttles():
    bucket = TokenBucket(60, burst=3)
    assert [bucket.try_acquire() for _ in range(3)] == [True, True, True]
    assert bucket.try_acquire() is False
    assert bucket.time_until_token() > 0


def test_token_bucket_refills_over_time(monkeypatch):
    bucket = TokenBucket(60, burst=1)
    assert bucket.try_acquire()
    assert not bucket.try_acquire()
    monkeypatch.setattr(time, "monotonic", lambda: bucket._updated + 2.0)
    assert bucket.try_acquire()          # ~1 token/second at 60/min


def test_a_rate_of_zero_means_unlimited():
    bucket = TokenBucket(0)
    assert bucket.unlimited and all(bucket.try_acquire() for _ in range(100))


def test_concurrency_is_capped():
    limiter = RateLimiter(RateLimitConfig(max_concurrency=2, requests_per_minute=0,
                                          per_host_requests_per_minute=0,
                                          max_per_host_concurrency=2))
    peak = 0
    current = 0
    lock = threading.Lock()

    def worker():
        nonlocal peak, current
        with limiter.slot("https://a.com/x"):
            with lock:
                current += 1
                peak = max(peak, current)
            time.sleep(0.05)
            with lock:
                current -= 1

    threads = [threading.Thread(target=worker) for _ in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert peak <= 2


def test_per_host_limits_are_independent():
    limiter = RateLimiter(RateLimitConfig(requests_per_minute=0, per_host_requests_per_minute=0,
                                          max_concurrency=4, max_per_host_concurrency=1))
    with limiter.slot("https://a.com/1"):
        with limiter.slot("https://b.com/1"):      # different host, not blocked
            pass
    assert limiter.stats()["tracked_hosts"] == 2


def test_a_slot_is_released_on_exception():
    limiter = RateLimiter(RateLimitConfig(max_concurrency=1, requests_per_minute=0,
                                          per_host_requests_per_minute=0))
    with pytest.raises(ValueError):
        with limiter.slot("https://a.com/x"):
            raise ValueError("boom")
    with limiter.slot("https://a.com/x"):          # would deadlock if leaked
        pass


@pytest.mark.parametrize("url,expected", [
    ("https://Acme.COM/x", "acme.com"), ("http://a.b.c/", "a.b.c"), ("not a url", ""),
])
def test_host_extraction(url, expected):
    assert host_of(url) == expected


# ====================================================================== retries
@pytest.mark.parametrize("exc,expected", [
    (TransientCrawlError("x"), True),
    (CrawlTimeout("x"), True),
    (RateLimited("x"), True),
    (PermanentCrawlError("x"), False),
    (ProviderNotConfigured("x"), False),
    (TimeoutError("x"), True),
    (ConnectionError("x"), True),
    (ValueError("x"), False),
])
def test_only_recoverable_errors_are_retried(exc, expected):
    assert is_retryable(exc) is expected


def test_a_permanent_error_is_not_retried():
    calls = []

    def fn():
        calls.append(1)
        raise PermanentCrawlError("404")

    with pytest.raises(PermanentCrawlError):
        with_retries(fn, RetryPolicy(attempts=5), sleep=lambda s: None)
    assert len(calls) == 1


def test_a_transient_error_is_retried_then_succeeds():
    calls = []

    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise TransientCrawlError("502")
        return "ok"

    outcome = RetryOutcome()
    assert with_retries(fn, RetryPolicy(attempts=3), sleep=lambda s: None,
                        outcome=outcome) == "ok"
    assert len(calls) == 3 and outcome.attempts == 3


def test_retries_are_exhausted_then_the_error_surfaces():
    with pytest.raises(TransientCrawlError):
        with_retries(lambda: (_ for _ in ()).throw(TransientCrawlError("502")),
                     RetryPolicy(attempts=2), sleep=lambda s: None)


def test_backoff_grows_exponentially_and_is_capped():
    policy = RetryPolicy(base_delay_seconds=1.0, multiplier=2.0, max_delay_seconds=8.0,
                         jitter=False)
    assert [policy.delay_for(i) for i in range(1, 6)] == [1.0, 2.0, 4.0, 8.0, 8.0]


def test_jitter_spreads_the_delay():
    policy = RetryPolicy(base_delay_seconds=4.0, multiplier=1.0, jitter=True)
    delays = {policy.delay_for(1) for _ in range(30)}
    assert len(delays) > 1 and all(0 <= d <= 4.0 for d in delays)


def test_a_provider_retry_after_wins_over_the_computed_delay():
    policy = RetryPolicy(base_delay_seconds=1.0, jitter=False)
    assert policy.delay_for(1, retry_after=12.0) == 12.0


def test_slept_time_is_recorded():
    slept = []
    outcome = RetryOutcome()
    with pytest.raises(TransientCrawlError):
        with_retries(lambda: (_ for _ in ()).throw(TransientCrawlError("x")),
                     RetryPolicy(attempts=3, base_delay_seconds=1.0, jitter=False),
                     sleep=slept.append, outcome=outcome)
    assert len(slept) == 2 and outcome.total_delay_seconds == sum(slept)


# ===================================================================== registry
def test_register_lookup_and_unregister():
    base.register(FakeProvider(name="p1"))
    assert base.list_providers() == ["p1"]
    assert base.get_provider("P1") is not None      # case-insensitive
    base.unregister("p1")
    assert base.list_providers() == []


def test_duplicate_registration_is_refused_unless_replacing():
    base.register(FakeProvider(name="p"))
    with pytest.raises(ValueError, match="already registered"):
        base.register(FakeProvider(name="p"))
    base.register(FakeProvider(name="p"), replace=True)


def test_a_provider_without_a_name_is_refused():
    with pytest.raises(ValueError, match="non-empty"):
        base.register(FakeProvider(name=""))


def test_registry_health_contains_a_raising_provider():
    class Sick(FakeProvider):
        def health(self):
            raise RuntimeError("probe failed")

    base.register(Sick(name="sick"))
    assert base.provider_health()["sick"].status is ProviderStatus.UNAVAILABLE


def test_default_providers_register_from_settings():
    from backend.crawling import register_default_providers

    assert register_default_providers(_settings()) == ["firecrawl", "http"]
    assert set(base.list_providers()) == {"firecrawl", "http"}


# ============================================================ provider: HTTP
def _http_provider(handler, **kw):
    return HttpCrawlProvider(client=httpx.Client(transport=httpx.MockTransport(handler),
                                                 follow_redirects=True), **kw)


def test_http_provider_fetches_and_extracts():
    provider = _http_provider(lambda r: httpx.Response(
        200, text=HTML, headers={"Content-Type": "text/html"}))
    page = provider.fetch_page("https://acme.com/about", CrawlOptions())
    assert page.title == "Acme Semiconductor" and page.provider == "http"
    assert "https://acme.com/careers" in page.links


def test_http_provider_needs_no_credentials():
    ok, _ = HttpCrawlProvider().validate()
    assert ok and not HttpCrawlProvider().capabilities().requires_credentials


@pytest.mark.parametrize("status,expected", [
    (404, PermanentCrawlError), (401, PermanentCrawlError), (403, PermanentCrawlError),
    (500, TransientCrawlError), (503, TransientCrawlError), (429, RateLimited),
])
def test_http_status_maps_to_the_right_error(status, expected):
    provider = _http_provider(lambda r: httpx.Response(status, text=""))
    with pytest.raises(expected):
        provider.fetch_page("https://acme.com/", CrawlOptions())


def test_http_timeout_becomes_a_crawl_timeout():
    def handler(request):
        raise httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(CrawlTimeout):
        _http_provider(handler).fetch_page("https://acme.com/", CrawlOptions())


def test_non_html_content_is_rejected_rather_than_parsed_as_garbage():
    provider = _http_provider(lambda r: httpx.Response(
        200, content=b"%PDF-1.4", headers={"Content-Type": "application/pdf"}))
    with pytest.raises(PermanentCrawlError, match="content type"):
        provider.fetch_page("https://acme.com/doc.pdf", CrawlOptions())


def test_unsupported_scheme_is_permanent():
    with pytest.raises(PermanentCrawlError, match="scheme"):
        HttpCrawlProvider().fetch_page("ftp://acme.com/x", CrawlOptions())


def test_http_sitemap_parsing_follows_a_sitemap_index():
    def handler(request):
        if request.url.path == "/sitemap.xml":
            return httpx.Response(200, text=(
                "<sitemapindex><sitemap><loc>https://acme.com/s1.xml</loc></sitemap>"
                "<url><loc>https://acme.com/a</loc></url></sitemapindex>"),
                headers={"Content-Type": "application/xml"})
        return httpx.Response(200, text="<urlset><url><loc>https://acme.com/b</loc></url></urlset>",
                              headers={"Content-Type": "application/xml"})

    urls = _http_provider(handler).fetch_sitemap("https://acme.com", CrawlOptions())
    assert "https://acme.com/a" in urls and "https://acme.com/b" in urls


def test_oversized_bodies_are_truncated():
    provider = _http_provider(lambda r: httpx.Response(
        200, text="<html><body>" + ("x" * 5000), headers={"Content-Type": "text/html"}),
        max_bytes=100)
    page = provider.fetch_page("https://acme.com/", CrawlOptions())
    assert len(page.text) < 5000


# ======================================================= provider: Firecrawl
def _firecrawl(handler, **kw):
    return FirecrawlProvider(api_key="fc-test", client=httpx.Client(
        transport=httpx.MockTransport(handler)), **kw)


def test_firecrawl_requires_an_api_key():
    ok, reason = FirecrawlProvider(api_key="").validate()
    assert not ok and "FIRECRAWL_API_KEY" in reason
    with pytest.raises(ProviderNotConfigured):
        FirecrawlProvider(api_key="").fetch_page("https://a.com", CrawlOptions())


def test_firecrawl_declares_javascript_rendering():
    caps = FirecrawlProvider(api_key="k").capabilities()
    assert caps.renders_javascript and caps.supports_crawl and caps.supports_sitemap


def test_firecrawl_sends_a_bearer_token_and_maps_the_response():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("Authorization")
        seen["path"] = request.url.path
        return httpx.Response(200, json={"data": {
            "markdown": "# Acme\n\nWe design chips.",
            "metadata": {"title": "Acme Semiconductor", "description": "ASIC house",
                         "sourceURL": "https://acme.com/", "statusCode": 200},
        }})

    page = _firecrawl(handler).fetch_page("https://acme.com/", CrawlOptions())
    assert seen["auth"] == "Bearer fc-test" and seen["path"] == "/v1/scrape"
    assert page.title == "Acme Semiconductor" and page.provider == "firecrawl"
    assert page.markdown.startswith("# Acme")


def test_firecrawl_prefers_its_own_markdown_over_local_conversion():
    def handler(request):
        return httpx.Response(200, json={"data": {
            "html": HTML, "markdown": "PROVIDER MARKDOWN",
            "metadata": {"sourceURL": "https://acme.com/"}}})

    page = _firecrawl(handler).fetch_page("https://acme.com/", CrawlOptions())
    assert page.markdown == "PROVIDER MARKDOWN"
    assert page.headings == ("Acme Semiconductor", "Careers")   # still extracted from HTML


def test_firecrawl_falls_back_to_extracting_html_when_no_markdown():
    def handler(request):
        return httpx.Response(200, json={"data": {"html": HTML,
                                                  "metadata": {"sourceURL": "https://acme.com/"}}})

    page = _firecrawl(handler).fetch_page("https://acme.com/", CrawlOptions())
    assert page.title == "Acme Semiconductor" and page.markdown


@pytest.mark.parametrize("status,expected", [
    (401, PermanentCrawlError), (400, PermanentCrawlError), (404, PermanentCrawlError),
    (429, RateLimited), (500, TransientCrawlError), (503, TransientCrawlError),
])
def test_firecrawl_status_maps_to_the_right_error(status, expected):
    with pytest.raises(expected):
        _firecrawl(lambda r: httpx.Response(status, text="err")).fetch_page(
            "https://a.com", CrawlOptions())


def test_firecrawl_never_echoes_the_api_key_in_an_error():
    def handler(request):
        return httpx.Response(401, text="invalid key fc-test")

    with pytest.raises(PermanentCrawlError) as excinfo:
        _firecrawl(handler).fetch_page("https://a.com", CrawlOptions())
    assert "fc-test" not in str(excinfo.value)


def test_firecrawl_honours_retry_after():
    def handler(request):
        return httpx.Response(429, headers={"Retry-After": "7"}, text="slow down")

    with pytest.raises(RateLimited) as excinfo:
        _firecrawl(handler).fetch_page("https://a.com", CrawlOptions())
    assert excinfo.value.retry_after == 7.0


def test_firecrawl_polls_an_async_crawl_to_completion(monkeypatch):
    monkeypatch.setattr("backend.crawling.providers.firecrawl.time.sleep", lambda s: None)
    state = {"polls": 0}

    def handler(request):
        if request.url.path == "/v1/crawl":
            return httpx.Response(200, json={"id": "job-1"})
        state["polls"] += 1
        if state["polls"] < 2:
            return httpx.Response(200, json={"status": "scraping"})
        return httpx.Response(200, json={"status": "completed", "data": [
            {"markdown": "# A", "metadata": {"sourceURL": "https://acme.com/a"}},
            {"markdown": "# B", "metadata": {"sourceURL": "https://acme.com/b"}}]})

    pages = _firecrawl(handler).crawl_site("https://acme.com", CrawlOptions(max_pages=5))
    assert [p.url for p in pages] == ["https://acme.com/a", "https://acme.com/b"]


def test_a_failed_firecrawl_job_is_transient():
    def handler(request):
        if request.url.path == "/v1/crawl":
            return httpx.Response(200, json={"id": "job-1"})
        return httpx.Response(200, json={"status": "failed", "error": "upstream"})

    with pytest.raises(TransientCrawlError):
        _firecrawl(handler).crawl_site("https://acme.com", CrawlOptions())


def test_firecrawl_map_returns_absolute_urls():
    def handler(request):
        return httpx.Response(200, json={"links": ["/a", "https://acme.com/b"]})

    urls = _firecrawl(handler).fetch_sitemap("https://acme.com", CrawlOptions())
    assert urls == ["https://acme.com/a", "https://acme.com/b"]


# ====================================================================== service
def test_fetch_page_returns_a_normalized_result():
    provider = FakeProvider(pages=[PageContent(url="https://a.com", title="A")])
    result = _service([provider]).fetch_page("https://a.com")
    assert result.ok and result.page_count == 1 and result.provider == "fake"
    assert result.page.title == "A" and result.duration_ms >= 0


def test_a_second_identical_request_is_served_from_cache():
    provider = FakeProvider()
    service = _service([provider], cache_ttl_seconds=60)
    first = service.fetch_page("https://a.com")
    second = service.fetch_page("https://a.com")
    assert not first.from_cache and second.from_cache
    assert provider.calls == 1


def test_bypass_cache_forces_a_refetch():
    provider = FakeProvider()
    service = _service([provider], cache_ttl_seconds=60)
    service.fetch_page("https://a.com")
    service.fetch_page("https://a.com", CrawlOptions(bypass_cache=True))
    assert provider.calls == 2


def test_invalidate_drops_one_cached_entry():
    provider = FakeProvider()
    service = _service([provider], cache_ttl_seconds=60)
    service.fetch_page("https://a.com")
    assert service.invalidate("https://a.com")
    service.fetch_page("https://a.com")
    assert provider.calls == 2


def test_a_failure_is_returned_not_raised():
    provider = FakeProvider(fail_times=99, error=PermanentCrawlError("404"))
    result = _service([provider]).fetch_page("https://a.com")
    assert result.failed and result.status is CrawlStatus.FAILED and "404" in result.error


def test_timeouts_and_rate_limits_get_their_own_status():
    assert _service([FakeProvider(name="t", fail_times=99, error=CrawlTimeout("slow"))]) \
        .fetch_page("https://a.com").status is CrawlStatus.TIMEOUT
    assert _service([FakeProvider(name="r", fail_times=99, error=RateLimited("429"))]) \
        .fetch_page("https://a.com").status is CrawlStatus.RATE_LIMITED


def test_failures_are_not_cached():
    provider = FakeProvider(fail_times=1, error=TransientCrawlError("502"))
    service = CrawlService(
        config=CrawlConfig(cache_ttl_seconds=60,
                           retry=RetryPolicy(attempts=1, base_delay_seconds=0.0)),
        providers={"fake": provider})
    assert service.fetch_page("https://a.com").failed
    assert service.fetch_page("https://a.com").ok      # retried live, not served a cached failure


def test_the_service_retries_through_the_policy():
    provider = FakeProvider(fail_times=1, error=TransientCrawlError("502"))
    service = CrawlService(
        config=CrawlConfig(cache_ttl_seconds=0,
                           retry=RetryPolicy(attempts=3, base_delay_seconds=0.0, jitter=False)),
        providers={"fake": provider})
    result = service.fetch_page("https://a.com")
    assert result.ok and result.attempts == 2 and provider.calls == 2


def test_no_usable_provider_is_reported_cleanly():
    result = _service([FakeProvider(valid=False)]).fetch_page("https://a.com")
    assert result.failed and "no usable crawl provider" in result.error


def test_the_configured_provider_is_preferred():
    js = FakeProvider(name="js", renders_js=True)
    plain = FakeProvider(name="plain", renders_js=False)
    service = _service([js, plain], provider="plain")
    assert service.select_provider().name == "plain"


def test_selection_falls_back_when_the_configured_provider_is_unusable():
    """A missing API key must degrade to another provider, not fail the crawl."""
    broken = FakeProvider(name="broken", valid=False)
    plain = FakeProvider(name="plain", renders_js=False)
    service = _service([broken, plain], provider="broken")
    assert service.select_provider().name == "plain"


def test_javascript_rendering_drives_capability_based_selection():
    """Both directions, with the JS provider sorting FIRST by name — so a pass proves
    capability decided, not alphabetical order."""
    js = FakeProvider(name="ajs", renders_js=True)
    plain = FakeProvider(name="zplain", renders_js=False)
    service = _service([js, plain])
    assert service.select_provider(CrawlOptions(render_javascript=True)).name == "ajs"
    assert service.select_provider(CrawlOptions(render_javascript=False)).name == "zplain"


def test_server_side_crawl_is_used_when_the_provider_supports_it():
    provider = FakeProvider(supports_crawl=True, pages=[
        PageContent(url="https://a.com/1"), PageContent(url="https://a.com/2")])
    result = _service([provider]).crawl_site("https://a.com")
    assert result.page_count == 2 and provider.calls == 1      # one job, not N fetches


def test_local_crawl_walks_links_breadth_first_within_the_host():
    class Linked(FakeProvider):
        def fetch_page(self, url, options):
            self.calls += 1
            links = ("https://a.com/x", "https://other.com/y") if url == "https://a.com" else ()
            return PageContent(url=url, title=url, links=links, provider=self.name)

    provider = Linked(supports_crawl=False)
    result = _service([provider]).crawl_site("https://a.com", CrawlOptions(max_depth=2,
                                                                          max_pages=10))
    urls = [p.url for p in result.pages]
    assert urls == ["https://a.com", "https://a.com/x"]        # off-host link not followed


def test_local_crawl_respects_the_page_budget():
    class Linked(FakeProvider):
        def fetch_page(self, url, options):
            self.calls += 1
            return PageContent(url=url, links=tuple(f"https://a.com/{i}" for i in range(20)),
                               provider=self.name)

    result = _service([Linked()]).crawl_site("https://a.com",
                                             CrawlOptions(max_depth=3, max_pages=4))
    assert result.page_count == 4


def test_local_crawl_honours_path_filters():
    class Linked(FakeProvider):
        def fetch_page(self, url, options):
            self.calls += 1
            links = ("https://a.com/careers/1", "https://a.com/blog/1")
            return PageContent(url=url, links=links if url == "https://a.com" else (),
                               provider=self.name)

    result = _service([Linked()]).crawl_site(
        "https://a.com", CrawlOptions(max_depth=2, max_pages=10, only_paths=("/careers",)))
    assert [p.url for p in result.pages] == ["https://a.com", "https://a.com/careers/1"]


def test_one_broken_child_page_does_not_abort_the_crawl():
    class Flaky(FakeProvider):
        def fetch_page(self, url, options):
            self.calls += 1
            if url.endswith("/bad"):
                raise PermanentCrawlError("404")
            links = ("https://a.com/bad", "https://a.com/good") if url == "https://a.com" else ()
            return PageContent(url=url, links=links, provider=self.name)

    result = _service([Flaky()]).crawl_site("https://a.com", CrawlOptions(max_depth=2,
                                                                          max_pages=5))
    assert [p.url for p in result.pages] == ["https://a.com", "https://a.com/good"]


def test_a_failing_root_page_fails_the_crawl():
    result = _service([FakeProvider(fail_times=99, error=PermanentCrawlError("404"))]) \
        .crawl_site("https://a.com")
    assert result.failed


def test_sitemap_falls_back_to_a_provider_that_supports_it():
    no_sitemap = FakeProvider(name="nomap", supports_sitemap=False)
    mapper = FakeProvider(name="http", supports_sitemap=True,
                          sitemap=["https://a.com/1", "https://a.com/2"])
    service = _service([no_sitemap, mapper], provider="nomap", fallback_provider="http")
    assert service.sitemap_urls("https://a.com") == ["https://a.com/1", "https://a.com/2"]


def test_health_reports_providers_cache_and_limits():
    service = _service([FakeProvider()])
    service.fetch_page("https://a.com")
    health = service.health()
    assert health["selected_provider"] == "fake"
    assert health["providers"]["fake"]["status"] == "ok"
    assert health["requests"] == 1 and "hit_rate" in health["cache"]


def test_close_releases_every_provider():
    provider = FakeProvider()
    _service([provider]).close()
    assert provider.closed


# ================================================================ configuration
def test_config_is_built_from_settings():
    config = CrawlConfig.from_settings(_settings(
        crawl_provider="firecrawl", crawl_cache_ttl_seconds=120, crawl_max_depth=3,
        crawl_max_pages=50, crawl_concurrency=8, crawl_retry_count=5,
        crawl_rate_limit_per_minute=90))
    assert config.provider == "firecrawl" and config.cache_ttl_seconds == 120
    assert config.default_options.max_depth == 3 and config.default_options.max_pages == 50
    assert config.rate_limit.max_concurrency == 8 and config.retry.attempts == 5
    assert config.rate_limit.requests_per_minute == 90


def test_a_zero_ttl_selects_the_null_cache():
    service = CrawlService.from_settings(_settings(crawl_cache_ttl_seconds=0))
    assert isinstance(service.cache, NullCrawlCache)


def test_settings_bind_from_both_prefixed_and_bare_env(monkeypatch):
    for name in ("SP_FIRECRAWL_API_KEY", "FIRECRAWL_API_KEY", "SP_CRAWL_PROVIDER",
                 "CRAWL_PROVIDER", "SP_CRAWL_MAX_DEPTH", "CRAWL_MAX_DEPTH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-live")
    monkeypatch.setenv("CRAWL_PROVIDER", "firecrawl")
    monkeypatch.setenv("CRAWL_MAX_DEPTH", "4")
    s = Settings(_env_file=None)
    assert s.firecrawl_api_key == "fc-live" and s.crawl_provider == "firecrawl"
    assert s.crawl_max_depth == 4


def test_nothing_is_hardcoded_when_settings_are_supplied():
    provider = FirecrawlProvider.from_settings(
        _settings(firecrawl_api_key="k", firecrawl_base_url="https://self-hosted.internal",
                  crawl_timeout_seconds=99))
    assert provider.api_key == "k" and provider.base_url == "https://self-hosted.internal"
    assert provider.timeout_seconds == 99


# ===================================================================== logging
def test_the_lifecycle_is_logged(caplog):
    with caplog.at_level(logging.INFO, logger="crawling.service"):
        service = _service([FakeProvider()], cache_ttl_seconds=60)
        service.fetch_page("https://a.com")
        service.fetch_page("https://a.com")
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "cache MISS" in text and "cache HIT" in text
    assert "started page https://a.com" in text and "completed page https://a.com" in text
    assert "provider=fake" in text


def test_failures_are_logged_with_attempts_and_duration(caplog):
    with caplog.at_level(logging.WARNING, logger="crawling.service"):
        _service([FakeProvider(fail_times=99, error=PermanentCrawlError("404"))]) \
            .fetch_page("https://a.com")
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "failed page https://a.com" in text and "attempts=1" in text


def test_retries_are_logged(caplog):
    with caplog.at_level(logging.INFO, logger="crawling.retry"):
        with pytest.raises(TransientCrawlError):
            with_retries(lambda: (_ for _ in ()).throw(TransientCrawlError("502")),
                         RetryPolicy(attempts=2, base_delay_seconds=0.0, jitter=False),
                         label="page https://a.com", sleep=lambda s: None)
    assert "retrying in" in "\n".join(r.getMessage() for r in caplog.records)



# ====================================================== architectural boundary
# These enforce the layering structurally. They inspect CODE ONLY: the docstrings
# and comments in this package legitimately name the very things the boundary
# forbids, because their job is to explain the boundary.
def _code_only(path) -> str:
    """Source with every docstring and comment stripped."""
    import ast
    import io
    import tokenize

    src = path.read_text(encoding="utf-8")
    without_comments = tokenize.untokenize(
        tok for tok in tokenize.generate_tokens(io.StringIO(src).readline)
        if tok.type != tokenize.COMMENT
    )
    tree = ast.parse(without_comments)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)                     and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def test_crawling_never_touches_the_database():
    """Infrastructure: no session, no ORM, anywhere in the layer."""
    import pathlib

    pkg = pathlib.Path(__file__).resolve().parent.parent / "backend" / "crawling"
    offenders = {}
    for f in pkg.rglob("*.py"):
        hits = [m for m in ("sqlalchemy", "session.add", "session.commit", "master_db")
                if m in _code_only(f)]
        if hits:
            offenders[f.name] = hits
    assert offenders == {}, f"crawling must not touch the database: {offenders}"


def test_crawling_contains_no_discovery_or_business_logic():
    import pathlib

    pkg = pathlib.Path(__file__).resolve().parent.parent / "backend" / "crawling"
    banned = ("market_discovery", "discoverycandidate", "confidencengine", "company_domain",
              "candidate_key", "resolve_to_company", "lead_score")
    offenders = {}
    for f in pkg.rglob("*.py"):
        code = _code_only(f).lower()
        hits = [b for b in banned if b in code]
        if hits:
            offenders[f.name] = hits
    assert offenders == {}, f"crawling must stay free of business logic: {offenders}"


def test_only_the_provider_module_knows_the_vendor():
    """Swapping Firecrawl must not touch anything above providers/."""
    import pathlib

    pkg = pathlib.Path(__file__).resolve().parent.parent / "backend" / "crawling"
    offenders = []
    for f in pkg.rglob("*.py"):
        if f.parent.name == "providers":
            continue
        if "firecrawl" in _code_only(f).lower():
            offenders.append(f.name)
    assert offenders == [], f"vendor name leaked outside providers/: {offenders}"


def test_two_independent_providers_satisfy_one_contract():
    """The proof the abstraction is real rather than Firecrawl-shaped."""
    for provider in (FirecrawlProvider(api_key="k"), HttpCrawlProvider()):
        assert isinstance(provider, CrawlProvider)
        caps = provider.capabilities()
        assert caps.name == provider.name
        assert isinstance(provider.validate(), tuple)
        assert provider.health().name == provider.name
    assert FirecrawlProvider(api_key="k").capabilities().renders_javascript
    assert not HttpCrawlProvider().capabilities().renders_javascript


# ============================================= market discovery integration
def test_a_discovery_source_can_crawl_without_gaining_database_access():
    from backend.market_discovery import CrawlingDiscoverySource
    from backend.market_discovery.schemas import DiscoveryCandidate, SourceCapabilities

    class Connector(CrawlingDiscoverySource):
        name = "example"

        def capabilities(self):
            return SourceCapabilities(name=self.name, provides=frozenset({"website"}))

        def fetch(self, context):
            result = self.crawl.fetch_page("https://a.com")
            return [{"title": result.page.title}] if result.ok else []

        def normalize(self, raw, context):
            return DiscoveryCandidate(company_name=raw["title"], website="https://a.com")

    from backend.market_discovery.schemas import DiscoveryContext

    connector = Connector(crawl_service=_service([FakeProvider(
        pages=[PageContent(url="https://a.com", title="Acme Semiconductor")])]))
    candidates = connector.discover(DiscoveryContext(run_id="r"))
    assert [c.company_name for c in candidates] == ["Acme Semiconductor"]
    assert candidates[0].source == "example"
    assert not hasattr(connector, "session")


def test_a_crawling_source_reports_provider_trouble_as_source_health():
    from backend.market_discovery import CrawlingDiscoverySource
    from backend.market_discovery.schemas import SourceCapabilities, SourceStatus as SS

    class Connector(CrawlingDiscoverySource):
        name = "example"

        def capabilities(self):
            return SourceCapabilities(name=self.name)

        def fetch(self, context):
            return []

        def normalize(self, raw, context):
            return None

    connector = Connector(crawl_service=_service([FakeProvider(valid=False)]))
    ok, reason = connector.validate()
    assert not ok and "no usable crawl provider" in reason
    assert connector.health().status is SS.UNAVAILABLE


def test_no_production_discovery_source_is_registered():
    """Phase 3 ships infrastructure only — no connector goes live."""
    import pathlib

    sources = (pathlib.Path(__file__).resolve().parent.parent / "backend"
               / "market_discovery" / "sources")
    assert [f.name for f in sources.glob("*.py") if f.name != "__init__.py"] == []


# ================================== sitemap diagnostics (prod vs local divergence)
# Production receives ONE self-referencing entry for the NVIDIA locale sitemap while
# a developer machine receives ~4,270. These pin the bounded instrumentation that
# tells those two apart: response shape and provenance, never the body.
SITEMAP_XML = ('<urlset><url><loc>https://acme.com/a/</loc></url>'
               '<url><loc>https://acme.com/b/</loc></url></urlset>')


def _sitemap_handler(body=SITEMAP_XML, **headers):
    hdrs = {"Content-Type": "application/xml"}
    hdrs.update(headers)
    return lambda r: httpx.Response(200, text=body, headers=hdrs)


def test_sitemap_diagnostics_log_response_shape(caplog):
    # No fake Content-Encoding: httpx would try to decompress a plain body and fail.
    handler = _sitemap_handler(**{"Cache-Control": "no-store"})
    with caplog.at_level(logging.INFO, logger="crawling.providers.http"):
        _http_provider(handler).fetch_sitemap("https://acme.com/s.xml", CrawlOptions())
    line = next(m for m in (r.getMessage() for r in caplog.records) if "sitemap https://" in m)
    for field in ("final=", "status=200", "ctype=", "cenc=", "clen=", "bytes=",
                  "sha256=", "locs=2", "self_referencing=False", "first="):
        assert field in line, f"{field} missing from: {line}"


def test_sitemap_diagnostics_never_log_the_body(caplog):
    secret = "https://acme.com/very-distinctive-path/"
    body = f"<urlset><url><loc>{secret}</loc></url>{'<!-- padding -->' * 200}</urlset>"
    with caplog.at_level(logging.INFO, logger="crawling.providers.http"):
        _http_provider(_sitemap_handler(body)).fetch_sitemap("https://acme.com/s.xml",
                                                             CrawlOptions())
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "padding" not in text                      # the body itself never appears
    assert secret in text                             # a sampled loc is metadata, and useful


def test_sitemap_diagnostics_sample_is_bounded(caplog):
    from backend.crawling.providers.http import _SITEMAP_LOC_SAMPLE

    locs = "".join(f"<url><loc>https://acme.com/{i}/</loc></url>" for i in range(40))
    with caplog.at_level(logging.INFO, logger="crawling.providers.http"):
        _http_provider(_sitemap_handler(f"<urlset>{locs}</urlset>")).fetch_sitemap(
            "https://acme.com/s.xml", CrawlOptions(max_pages=100))
    line = next(m for m in (r.getMessage() for r in caplog.records) if "sitemap https://" in m)
    assert "locs=40" in line
    sample = line.split("first=", 1)[1]
    assert sample.count("https://acme.com/") == _SITEMAP_LOC_SAMPLE     # 40 seen, 3 shown


def test_a_self_referencing_sitemap_is_flagged(caplog):
    """The exact production shape: one entry, equal to the URL we asked for."""
    url = "https://acme.com/s.xml"
    body = f"<urlset><url><loc>{url}</loc></url></urlset>"
    with caplog.at_level(logging.INFO, logger="crawling.providers.http"):
        _http_provider(_sitemap_handler(body)).fetch_sitemap(url, CrawlOptions())
    line = next(m for m in (r.getMessage() for r in caplog.records) if "sitemap https://" in m)
    assert "self_referencing=True" in line and "locs=1" in line


def test_sitemap_diagnostics_never_break_the_crawl(monkeypatch):
    from backend.crawling.providers import http as http_mod

    monkeypatch.setattr(http_mod, "hashlib", None)     # force the diagnostic to raise
    urls = _http_provider(_sitemap_handler()).fetch_sitemap("https://acme.com/s.xml",
                                                            CrawlOptions())
    assert urls == ["https://acme.com/a/", "https://acme.com/b/"]


def test_the_client_configuration_is_logged_once(caplog):
    provider = HttpCrawlProvider()                     # builds its own client lazily
    from backend.crawling.providers import http as http_mod

    monkeypatch_flag = http_mod._client_config_logged
    http_mod._client_config_logged = False
    try:
        with caplog.at_level(logging.INFO, logger="crawling.providers.http"):
            provider.client
            provider.client                            # second access: no second line
        lines = [m for m in (r.getMessage() for r in caplog.records) if "http client:" in m]
        assert len(lines) == 1
        for field in ("httpx=", "follow_redirects=True", "timeout=", "ua=", "proxy_env="):
            assert field in lines[0]
    finally:
        http_mod._client_config_logged = monkeypatch_flag
        provider.close()


def test_proxy_diagnostics_report_names_never_values(monkeypatch):
    from backend.crawling.providers.http import _proxy_env

    monkeypatch.setenv("HTTPS_PROXY", "http://user:secret@proxy.internal:8080")
    names = _proxy_env()
    assert "HTTPS_PROXY" in names
    assert not any("secret" in n for n in names)


def test_the_enumerating_provider_is_logged(caplog):
    """Selection is capability-based, so which provider answered is the first thing
    to know when two environments disagree about the same sitemap."""
    provider = _http_provider(_sitemap_handler())
    service = CrawlService(config=CrawlConfig(provider="http"), cache=NullCrawlCache(),
                           providers={"http": provider})
    with caplog.at_level(logging.INFO, logger="crawling.service"):
        service.sitemap_urls("https://acme.com/s.xml", CrawlOptions())
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "enumerated by provider=http" in text and "2 url(s)" in text


def test_sitemap_enumeration_results_are_unchanged_by_diagnostics():
    """Instrumentation only: the returned URLs must be exactly what they were."""
    urls = _http_provider(_sitemap_handler()).fetch_sitemap("https://acme.com/s.xml",
                                                            CrawlOptions())
    assert urls == ["https://acme.com/a/", "https://acme.com/b/"]


# ============================== provider selection: honouring render_javascript=False
# Production had FIRECRAWL_API_KEY set and no CRAWL_PROVIDER. Selection preferred a JS
# renderer only when JS was ASKED FOR; the other half fell through to the first usable
# provider in name order, so "firecrawl" beat "http" for every plain request — including
# sitemap enumeration, which /map answers with the URL it was handed.
def test_plain_http_is_selected_when_javascript_is_not_requested():
    """The production bug, pinned: firecrawl sorts before http and must NOT win here."""
    firecrawl = FakeProvider(name="firecrawl", renders_js=True)
    http = FakeProvider(name="http", renders_js=False)
    service = _service([firecrawl, http])
    assert service.select_provider(CrawlOptions(render_javascript=False)).name == "http"


def test_a_javascript_provider_is_selected_when_rendering_is_requested():
    firecrawl = FakeProvider(name="firecrawl", renders_js=True)
    http = FakeProvider(name="http", renders_js=False)
    service = _service([firecrawl, http])
    assert service.select_provider(CrawlOptions(render_javascript=True)).name == "firecrawl"


def test_an_explicit_provider_still_overrides_capability_matching():
    """CRAWL_PROVIDER remains the operator's escape hatch, in both directions."""
    firecrawl = FakeProvider(name="firecrawl", renders_js=True)
    http = FakeProvider(name="http", renders_js=False)
    service = _service([firecrawl, http], provider="firecrawl")
    assert service.select_provider(CrawlOptions(render_javascript=False)).name == "firecrawl"


def test_a_plain_request_still_runs_when_only_a_renderer_is_available():
    """Backward compatible: preference, not a requirement — the caller gets content."""
    firecrawl = FakeProvider(name="firecrawl", renders_js=True)
    service = _service([firecrawl])
    assert service.select_provider(CrawlOptions(render_javascript=False)).name == "firecrawl"


def test_a_js_request_still_runs_when_only_a_plain_provider_is_available():
    http = FakeProvider(name="http", renders_js=False)
    service = _service([http])
    assert service.select_provider(CrawlOptions(render_javascript=True)).name == "http"


def test_an_unusable_preferred_provider_is_skipped_for_the_matching_one():
    """A missing API key must not drag a plain request onto a broken renderer."""
    firecrawl = FakeProvider(name="firecrawl", renders_js=True, valid=False)
    http = FakeProvider(name="http", renders_js=False)
    service = _service([firecrawl, http])
    assert service.select_provider(CrawlOptions(render_javascript=True)).name == "http"
    assert service.select_provider(CrawlOptions(render_javascript=False)).name == "http"


def test_a_provider_whose_capabilities_raise_is_not_selected():
    class Broken(FakeProvider):
        def capabilities(self):
            raise RuntimeError("capabilities exploded")

    broken = Broken(name="abroken", renders_js=False)
    http = FakeProvider(name="http", renders_js=False)
    assert _service([broken, http]).select_provider(
        CrawlOptions(render_javascript=False)).name == "http"


def test_the_real_providers_select_correctly_with_a_firecrawl_key():
    """End to end over the REAL registry — the shape production runs in."""
    from backend.crawling import register_default_providers
    from backend.crawling.service import CrawlConfig as _CC

    settings = Settings(_env_file=None, firecrawl_api_key="fc-test-key")
    register_default_providers(settings)
    service = CrawlService(config=_CC.from_settings(settings), cache=NullCrawlCache())
    assert service.select_provider(CrawlOptions(render_javascript=False)).name == "http"
    assert service.select_provider(CrawlOptions(render_javascript=True)).name == "firecrawl"


def test_selection_contains_no_source_specific_logic():
    """The fix is capability-based; no connector may be named in the crawler."""
    import ast
    import inspect
    import textwrap

    from backend.crawling import service as service_mod

    tree = ast.parse(textwrap.dedent(inspect.getsource(service_mod.CrawlService.select_provider)))
    fn = tree.body[0]
    if isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant):
        fn.body = fn.body[1:]                      # drop the docstring; inspect code only
    code = ast.unparse(fn).lower()
    for name in ("nvidia", "inception", "wellfound", "case-studies", "sitemap.xml"):
        assert name not in code, f"selection must not reference {name}"


def test_http_sitemap_enumeration_is_unchanged_by_the_selection_fix():
    urls = _http_provider(_sitemap_handler()).fetch_sitemap("https://acme.com/s.xml",
                                                            CrawlOptions())
    assert urls == ["https://acme.com/a/", "https://acme.com/b/"]
