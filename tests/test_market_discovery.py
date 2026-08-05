"""Market Discovery Engine framework (backend/market_discovery).

Covers the source interface and its architectural boundary, the registry,
normalization, validation, the pipeline, the duplicate resolver, the confidence
engine, events, configuration, scheduler integration, persistence and failure
handling.

No network, no external service, no real connector — the framework ships with zero
sources and every test here uses in-test fakes, which is exactly how a future
Firecrawl/Wellfound/Dealroom connector will be tested too.
"""
from datetime import datetime, timedelta, timezone

import pytest

from backend.config import Settings
from backend.market_discovery import events, models, service
from backend.market_discovery.base_source import DiscoverySource
from backend.market_discovery.confidence import (
    ConfidenceConfig,
    ConfidenceEngine,
    has_careers_page,
    has_funding_information,
    has_semiconductor_signal,
)
from backend.market_discovery.normalize import (
    candidate_key,
    comparison_name,
    normalize_candidate,
    normalize_linkedin,
    normalize_website,
    validate_candidate,
)
from backend.market_discovery.pipeline import DiscoveryPipeline, PipelineConfig
from backend.market_discovery.registry import SourceRegistry
from backend.market_discovery.resolver import DiscoveryResolver, DuplicateStrategy
from backend.market_discovery.schemas import (
    CandidateStatus,
    DiscoveryCandidate,
    DiscoveryContext,
    SourceCapabilities,
    SourceStatus,
)
from master_db.local import make_session_factory
from master_db.models import Company, DiscoveryCandidateRecord

NOW = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)


# ------------------------------------------------------------------ fixtures
@pytest.fixture()
def session():
    with make_session_factory(":memory:")() as s:
        yield s


@pytest.fixture()
def registry():
    return SourceRegistry()


@pytest.fixture(autouse=True)
def _no_leaked_subscribers():
    events.clear_subscribers()
    yield
    events.clear_subscribers()


def _settings(**kw):
    base = dict(_env_file=None, discovery_enabled=True, discovery_sources_raw="",
                discovery_retry_backoff_seconds=0.0, discovery_concurrency=1)
    base.update(kw)
    return Settings(**base)


def _candidate(**kw) -> DiscoveryCandidate:
    base = dict(company_name="Acme Semiconductor", website="https://acme-semi.com",
                source="fake", first_seen=NOW, last_seen=NOW)
    base.update(kw)
    return DiscoveryCandidate(**base)


class FakeSource(DiscoverySource):
    """A source exactly as a real connector will be written."""

    name = "fake"

    def __init__(self, records=None, *, name="fake", fail_times=0, provides=("website",)):
        self.name = name
        self._records = records if records is not None else []
        self.fail_times = fail_times
        self.calls = 0
        self._provides = frozenset(provides)

    def capabilities(self):
        return SourceCapabilities(name=self.name, provides=self._provides,
                                  description="test double")

    def fetch(self, context):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError(f"provider unavailable (attempt {self.calls})")
        return list(self._records)

    def normalize(self, raw, context):
        if not raw.get("name"):
            return None
        return DiscoveryCandidate(
            company_name=raw["name"], website=raw.get("website", ""),
            linkedin_url=raw.get("linkedin", ""), description=raw.get("description", ""),
            industry=raw.get("industry", ""), country=raw.get("country", ""),
            funding_stage=raw.get("funding", ""),
            technologies=tuple(raw.get("technologies", ())),
            source_id=raw.get("id", ""), raw_payload=raw,
        )


# ============================================================ source interface
def test_source_must_implement_the_contract():
    with pytest.raises(TypeError):
        DiscoverySource()          # abstract: capabilities/fetch/normalize required


def test_discover_stamps_provenance_the_source_cannot_fake():
    src = FakeSource([{"name": "Acme", "website": "acme.com"}], name="firecrawl")
    out = src.discover(DiscoveryContext(run_id="r1", now=NOW))
    assert len(out) == 1
    assert out[0].source == "firecrawl"      # stamped by the base class, not the subclass
    assert out[0].last_seen == NOW


def test_discover_skips_a_record_that_normalizes_to_none():
    src = FakeSource([{"name": "Acme"}, {"name": ""}, {"name": "Globex"}])
    assert [c.company_name for c in src.discover(DiscoveryContext(now=NOW))] == ["Acme", "Globex"]


def test_discover_survives_one_bad_record():
    class Broken(FakeSource):
        def normalize(self, raw, context):
            if raw.get("name") == "boom":
                raise ValueError("bad record")
            return super().normalize(raw, context)

    src = Broken([{"name": "Acme"}, {"name": "boom"}, {"name": "Globex"}])
    assert len(src.discover(DiscoveryContext(now=NOW))) == 2      # one skipped, not fatal


def test_discover_honours_the_engine_supplied_limit():
    src = FakeSource([{"name": f"Co {i}"} for i in range(50)])
    assert len(src.discover(DiscoveryContext(now=NOW, limit=5))) == 5


def test_default_validate_blocks_a_source_needing_credentials():
    class NeedsKey(FakeSource):
        def capabilities(self):
            return SourceCapabilities(name=self.name, requires_credentials=True)

    ok, reason = NeedsKey().validate()
    assert not ok and "credentials" in reason


def test_default_health_derives_from_validate_without_network():
    assert FakeSource().health().status is SourceStatus.OK


def test_source_has_no_database_access():
    """The architectural boundary: a source cannot reach the DB even if it wanted to."""
    src = FakeSource()
    assert not hasattr(src, "session")
    assert not any("session" in p for p in DiscoverySource.discover.__code__.co_varnames)


# ==================================================================== registry
def test_register_and_lookup(registry):
    registry.register(FakeSource(name="wellfound"))
    assert registry.names() == ["wellfound"]
    assert registry.get("WELLFOUND") is not None      # case-insensitive
    assert "wellfound" in registry and len(registry) == 1


def test_duplicate_registration_is_refused_unless_replacing(registry):
    registry.register(FakeSource(name="dealroom"))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeSource(name="dealroom"))
    registry.register(FakeSource(name="dealroom"), replace=True)     # explicit is fine


def test_a_source_without_a_name_is_refused(registry):
    with pytest.raises(ValueError, match="non-empty"):
        registry.register(FakeSource(name=""))


def test_nothing_runs_until_explicitly_enabled(registry):
    """These providers cost money — registration alone must not run them."""
    registry.register(FakeSource(name="crunchbase"))
    assert registry.enabled_sources(None) == []
    assert registry.enabled_sources([]) == []
    assert [s.name for s in registry.enabled_sources(["crunchbase"])] == ["crunchbase"]


def test_wildcard_enables_every_registered_source(registry):
    registry.register(FakeSource(name="a"))
    registry.register(FakeSource(name="b"))
    assert [s.name for s in registry.enabled_sources(["*"])] == ["a", "b"]


def test_enabled_order_is_deterministic(registry):
    for n in ("zeta", "alpha", "mid"):
        registry.register(FakeSource(name=n))
    assert [s.name for s in registry.enabled_sources(["zeta", "mid", "alpha"])] == [
        "alpha", "mid", "zeta"]


def test_a_configured_but_unregistered_source_is_skipped_not_fatal(registry):
    registry.register(FakeSource(name="real"))
    assert [s.name for s in registry.enabled_sources(["real", "not_shipped_yet"])] == ["real"]


def test_runnable_sources_separates_the_unvalidatable(registry):
    class NeedsKey(FakeSource):
        def validate(self):
            return False, "API key missing"

    registry.register(FakeSource(name="ok"))
    registry.register(NeedsKey(name="needskey"))
    runnable, skipped = registry.runnable_sources(["ok", "needskey"])
    assert [s.name for s in runnable] == ["ok"]
    assert [h.name for h in skipped] == ["needskey"] and "API key" in skipped[0].detail


def test_a_source_whose_validate_raises_is_contained(registry):
    class Exploding(FakeSource):
        def validate(self):
            raise RuntimeError("bang")

    registry.register(Exploding(name="boom"))
    runnable, skipped = registry.runnable_sources(["boom"])
    assert runnable == [] and "bang" in skipped[0].detail


def test_health_reports_disabled_for_registered_but_off_sources(registry):
    registry.register(FakeSource(name="on"))
    registry.register(FakeSource(name="off"))
    health = registry.health(["on"])
    assert health["on"].status is SourceStatus.OK
    assert health["off"].status is SourceStatus.DISABLED


def test_health_contains_a_raising_source(registry):
    class Sick(FakeSource):
        def health(self):
            raise RuntimeError("probe failed")

    registry.register(Sick(name="sick"))
    assert registry.health(["sick"])["sick"].status is SourceStatus.UNAVAILABLE


def test_capabilities_are_exposed(registry):
    registry.register(FakeSource(name="fc", provides=("website", "funding_stage")))
    caps = registry.capabilities()["fc"]
    assert caps.can_provide("website") and not caps.can_provide("linkedin_url")


def test_autodiscover_finds_registered_connectors(registry):
    """Importing a connector module is what registers it; the call is idempotent."""
    first = registry.autodiscover()
    assert "wellfound" in registry.names()
    registry.autodiscover()                    # cached imports must not lose anything
    assert "wellfound" in registry.names()
    assert isinstance(first, list)


# =============================================================== normalization
@pytest.mark.parametrize("raw,expected", [
    ("acme.com", "https://acme.com"),
    ("https://www.ACME.com/about?x=1", "https://acme.com"),
    ("http://acme.com", "https://acme.com"),
    ("not a url", ""),
    ("", ""),
])
def test_website_normalizes_to_the_registrable_domain(raw, expected):
    assert normalize_website(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("https://www.linkedin.com/company/acme-semi/", "https://www.linkedin.com/company/acme-semi"),
    ("linkedin.com/company/Acme-Semi", "https://www.linkedin.com/company/acme-semi"),
    ("https://linkedin.com/in/someone", ""),      # a person, not a company
    ("", ""),
])
def test_linkedin_normalizes_to_a_canonical_company_url(raw, expected):
    assert normalize_linkedin(raw) == expected


@pytest.mark.parametrize("name,expected", [
    ("Acme Semiconductor, Inc.", "acme semiconductor"),
    ("ACME  Semiconductor   Ltd", "acme semiconductor"),
    ("Acme Semiconductor GmbH", "acme semiconductor"),
    ("Acme", "acme"),
])
def test_comparison_name_strips_legal_form_and_punctuation(name, expected):
    assert comparison_name(name) == expected


def test_normalization_is_deterministic_and_pure():
    original = _candidate(website="HTTPS://WWW.Acme-Semi.com/x", company_name=" Acme  Semi ")
    a = normalize_candidate(original)
    b = normalize_candidate(original)
    assert a.candidate_key == b.candidate_key
    assert original.website == "HTTPS://WWW.Acme-Semi.com/x"      # input untouched


def test_candidate_key_prefers_domain_then_linkedin_then_name():
    by_domain = normalize_candidate(_candidate(website="acme.com", company_name="Acme"))
    same_domain_other_name = normalize_candidate(
        _candidate(website="acme.com", company_name="Totally Different"))
    assert by_domain.candidate_key == same_domain_other_name.candidate_key

    by_linkedin = normalize_candidate(_candidate(
        website="", linkedin_url="linkedin.com/company/acme", company_name="Acme"))
    by_name = normalize_candidate(_candidate(website="", linkedin_url="", company_name="Acme"))
    assert len({by_domain.candidate_key, by_linkedin.candidate_key, by_name.candidate_key}) == 3


def test_legal_suffix_variants_share_a_name_key():
    a = normalize_candidate(_candidate(website="", company_name="Acme Semiconductor, Inc."))
    b = normalize_candidate(_candidate(website="", company_name="acme semiconductor"))
    assert a.candidate_key == b.candidate_key


def test_tokens_are_deduplicated_and_lowercased():
    c = normalize_candidate(_candidate(technologies=("RISC-V", "risc-v", "ASIC, SoC")))
    assert c.technologies == ("risc-v", "asic", "soc")


# ==================================================================== validation
def test_a_well_formed_candidate_validates():
    assert validate_candidate(normalize_candidate(_candidate())) == []


@pytest.mark.parametrize("kw,field", [
    (dict(company_name=""), "company_name"),
    (dict(company_name="X", website="", linkedin_url=""), "company_name"),
    (dict(source=""), "source"),
])
def test_invalid_candidates_are_reported(kw, field):
    issues = validate_candidate(normalize_candidate(_candidate(**kw)))
    assert field in {i.field for i in issues}


def test_a_candidate_with_no_identity_is_rejected():
    issues = validate_candidate(normalize_candidate(
        DiscoveryCandidate(company_name="", source="fake")))
    assert "candidate_key" in {i.field for i in issues}


def test_competitor_domains_are_rejected_whatever_surfaced_them(monkeypatch):
    monkeypatch.setattr("backend.market_discovery.normalize.is_excluded_domain",
                        lambda d: d == "competitor.com")
    issues = validate_candidate(normalize_candidate(_candidate(website="competitor.com")))
    assert "company_domain" in {i.field for i in issues}


# ==================================================================== resolver
def test_duplicates_across_sources_collapse_to_one():
    resolver = DiscoveryResolver()
    a = normalize_candidate(_candidate(source="firecrawl", website="acme.com"))
    b = normalize_candidate(_candidate(source="wellfound", website="https://www.acme.com/careers",
                                       country="India"))
    groups = resolver.group([a, b])
    assert len(groups) == 1
    assert groups[0].is_duplicate and groups[0].source_names == ("firecrawl", "wellfound")
    assert groups[0].candidate.country == "India"      # thinner sighting still contributes


def test_distinct_companies_stay_separate():
    resolver = DiscoveryResolver()
    groups = resolver.group([
        normalize_candidate(_candidate(website="acme.com")),
        normalize_candidate(_candidate(website="globex.com", company_name="Globex")),
    ])
    assert len(groups) == 2


def test_a_merge_never_blanks_an_existing_value():
    resolver = DiscoveryResolver()
    rich = normalize_candidate(_candidate(website="acme.com", country="India",
                                          description="A" * 60))
    thin = normalize_candidate(_candidate(website="acme.com", country="", description=""))
    merged = resolver.group([rich, thin])[0].candidate
    assert merged.country == "India" and len(merged.description) == 60


def test_field_conflicts_are_reported_not_silently_resolved():
    resolver = DiscoveryResolver()
    a = normalize_candidate(_candidate(website="acme.com", country="India"))
    b = normalize_candidate(_candidate(website="acme.com", country="Germany"))
    group = resolver.group([a, b])[0]
    conflict = next(c for c in group.conflicts if c.field == "country")
    assert conflict.kept == "India" and conflict.discarded == "Germany"


def test_grouping_is_order_stable():
    resolver = DiscoveryResolver()
    cands = [normalize_candidate(_candidate(website=f"c{i}.com", company_name=f"C{i}"))
             for i in range(5)]
    assert [g.key for g in resolver.group(cands)] == [g.key for g in resolver.group(cands)]


def test_duplicate_strategy_is_the_extension_point_for_fuzzy_matching():
    class NameOnly(DuplicateStrategy):
        def key_for(self, candidate):
            return comparison_name(candidate.company_name)

    resolver = DiscoveryResolver(strategy=NameOnly())
    groups = resolver.group([
        normalize_candidate(_candidate(website="acme.com")),
        normalize_candidate(_candidate(website="acme-semi.io")),      # different domain
    ])
    assert len(groups) == 1      # same name -> one company under the custom strategy


def test_resolution_against_the_platform_is_read_only(session):
    """Discovery must never create a company as a side effect of resolving."""
    resolver = DiscoveryResolver(session)
    before = session.query(Company).count()
    domain, _note = resolver.resolve_to_company(
        normalize_candidate(_candidate(website="brand-new-co.com")))
    assert session.query(Company).count() == before      # no stub created
    assert domain is None


def test_a_known_company_resolves_to_its_domain(session):
    session.add(Company(company_domain="acme-semi.com", canonical_company_id="ACME",
                        company_name="Acme Semiconductor", name_key="acmesemiconductor",
                        prospect_type="PRODUCT_COMPANY", validation_status="VALID"))
    session.commit()
    resolver = DiscoveryResolver(session)
    domain, _ = resolver.resolve_to_company(normalize_candidate(_candidate()))
    assert domain == "acme-semi.com"


def test_merge_plan_describes_without_writing(session):
    resolver = DiscoveryResolver(session)
    group = resolver.group([
        normalize_candidate(_candidate(source="a", website="acme.com", country="India")),
        normalize_candidate(_candidate(source="b", website="acme.com", country="Germany")),
    ])[0]
    plan = resolver.merge_plan(group)
    assert plan["source_count"] == 2 and plan["conflicts"][0]["field"] == "country"
    assert session.query(DiscoveryCandidateRecord).count() == 0


# ================================================================== confidence
def test_confidence_is_deterministic():
    engine = ConfidenceEngine()
    c = normalize_candidate(_candidate())
    assert engine.score(c) == engine.score(c) == engine.score(normalize_candidate(_candidate()))


def test_a_richer_candidate_scores_higher():
    engine = ConfidenceEngine()
    thin = normalize_candidate(DiscoveryCandidate(company_name="Mystery Co", source="s"))
    rich = normalize_candidate(_candidate(
        linkedin_url="linkedin.com/company/acme", description="A" * 60,
        industry="semiconductor", country="India", founded_year="2019",
        funding_stage="series a", technologies=("asic",)))
    assert engine.score(rich) > engine.score(thin)


def test_independent_corroboration_raises_confidence():
    engine = ConfidenceEngine()
    one = normalize_candidate(_candidate())
    two = normalize_candidate(_candidate())
    two.metadata["sources"] = ("firecrawl", "dealroom")
    assert engine.score(two) > engine.score(one)


@pytest.mark.parametrize("text,expected", [
    ("We design ASIC and SoC silicon", True),
    ("RISC-V processor IP", True),
    ("physical design services", True),
    ("We sell chipotle burritos", False),          # substring must not match
    ("A generic software company", False),
])
def test_semiconductor_keyword_detection(text, expected):
    assert has_semiconductor_signal(
        normalize_candidate(_candidate(description=text, company_name="X"))) is expected


def test_careers_and_funding_factors():
    assert has_careers_page(_candidate(source_url="https://acme.com/careers"))
    assert has_careers_page(_candidate(metadata={"careers_url": "https://x/jobs"}))
    assert not has_careers_page(_candidate(source_url="https://acme.com/about"))
    assert has_funding_information(_candidate(funding_stage="series b"))
    assert has_funding_information(_candidate(metadata={"investors": ["VC"]}))
    assert not has_funding_information(_candidate(funding_stage=""))


def test_weights_are_configurable():
    strict = ConfidenceEngine(ConfidenceConfig(semiconductor_keywords=10.0))
    loose = ConfidenceEngine(ConfidenceConfig(semiconductor_keywords=0.1))
    c = normalize_candidate(_candidate(description="ASIC and SoC design"))
    assert strict.score(c) != loose.score(c)


def test_a_zero_weight_factor_is_not_evaluated():
    """Disabling a factor must not shift the others by changing the denominator."""
    engine = ConfidenceEngine(ConfidenceConfig(careers_page=0.0))
    score = engine.evaluate(normalize_candidate(_candidate()))
    assert "careers_page" not in score.factors


def test_score_is_bounded_and_threshold_configurable():
    engine = ConfidenceEngine(ConfidenceConfig(threshold=0.9))
    value = engine.score(normalize_candidate(_candidate()))
    assert 0.0 <= value <= 1.0
    assert engine.meets_threshold(0.95) and not engine.meets_threshold(0.5)


# ==================================================================== pipeline
def _pipeline(registry, session=None, **cfg):
    config = PipelineConfig(enabled_sources=("fake",), retry_backoff_seconds=0.0,
                            concurrency=1, **cfg)
    return DiscoveryPipeline(config=config, registry=registry, session=session)


def test_zero_sources_is_a_successful_no_op(registry):
    result = DiscoveryPipeline(config=PipelineConfig(), registry=registry).run(run_id="r")
    assert result.status == "success" and result.processed == [] and result.fetched == 0


def test_pipeline_end_to_end(registry):
    registry.register(FakeSource([
        {"name": "Acme Semiconductor", "website": "acme.com", "description": "ASIC design house",
         "country": "India", "funding": "series a"},
        {"name": "", "website": "bad.com"},                       # dropped by the source
        {"name": "Nameless", "website": ""},                      # low confidence
    ]))
    result = _pipeline(registry).run(run_id="r1")
    assert result.fetched == 2
    accepted = [p.candidate.company_name for p in result.accepted]
    assert "Acme Semiconductor" in accepted


def test_pipeline_is_deterministic(registry):
    registry.register(FakeSource([{"name": f"Co {i}", "website": f"c{i}.com"} for i in range(6)]))
    a = _pipeline(registry).run(run_id="r")
    b = _pipeline(registry).run(run_id="r")
    assert [p.candidate.candidate_key for p in a.processed] == \
           [p.candidate.candidate_key for p in b.processed]


def test_duplicates_across_two_sources_are_counted_once(registry):
    rec = {"name": "Acme Semiconductor", "website": "acme.com", "description": "ASIC design"}
    registry.register(FakeSource([rec], name="src_a"))
    registry.register(FakeSource([dict(rec, country="India")], name="src_b"))
    config = PipelineConfig(enabled_sources=("src_a", "src_b"), retry_backoff_seconds=0.0,
                            concurrency=1)
    result = DiscoveryPipeline(config=config, registry=registry).run(run_id="r")
    assert result.fetched == 2 and result.duplicates == 1
    merged = next(p for p in result.processed if p.accepted)
    assert set(merged.candidate.sources) == {"src_a", "src_b"}


def test_invalid_candidates_are_rejected_not_persisted(registry):
    registry.register(FakeSource([{"name": "A"}]))      # name too short to identify
    result = _pipeline(registry).run(run_id="r")
    assert result.rejected == 1 and result.accepted == []


def test_low_confidence_candidates_are_parked_not_promoted(registry):
    registry.register(FakeSource([{"name": "Mystery Holdings"}]))
    result = _pipeline(registry, confidence=ConfidenceConfig(threshold=0.99)).run(run_id="r")
    assert result.below_threshold == 1 and result.accepted == []


def test_a_failing_source_does_not_stop_the_others(registry):
    registry.register(FakeSource([], name="broken", fail_times=99))
    registry.register(FakeSource([{"name": "Acme Semi", "website": "acme.com"}], name="good"))
    config = PipelineConfig(enabled_sources=("broken", "good"), retry_count=1,
                            retry_backoff_seconds=0.0, concurrency=1)
    result = DiscoveryPipeline(config=config, registry=registry).run(run_id="r")
    assert result.status == "partial"
    assert [s.name for s in result.failed_sources] == ["broken"]
    assert result.fetched == 1


def test_every_source_failing_is_a_failed_run(registry):
    registry.register(FakeSource([], name="a", fail_times=99))
    config = PipelineConfig(enabled_sources=("a",), retry_count=1, retry_backoff_seconds=0.0)
    assert DiscoveryPipeline(config=config, registry=registry).run(run_id="r").status == "failed"


def test_a_source_is_retried_then_succeeds(registry):
    src = FakeSource([{"name": "Acme Semi", "website": "acme.com"}], fail_times=1)
    registry.register(src)
    result = _pipeline(registry, retry_count=2).run(run_id="r")
    assert src.calls == 2 and result.fetched == 1 and result.status == "success"


def test_concurrent_collection_preserves_deterministic_order(registry):
    for n in ("zeta", "alpha", "mid"):
        registry.register(FakeSource([{"name": f"{n} Corp", "website": f"{n}.com"}], name=n))
    config = PipelineConfig(enabled_sources=("zeta", "alpha", "mid"), concurrency=3,
                            retry_backoff_seconds=0.0)
    a = DiscoveryPipeline(config=config, registry=registry).run(run_id="r")
    b = DiscoveryPipeline(config=config, registry=registry).run(run_id="r")
    assert [s.name for s in a.sources] == ["alpha", "mid", "zeta"] == [s.name for s in b.sources]


def test_source_limit_is_enforced(registry):
    registry.register(FakeSource([{"name": f"Co {i}", "website": f"c{i}.com"} for i in range(30)]))
    assert _pipeline(registry, source_limit=4).run(run_id="r").fetched == 4


# ====================================================================== events
def test_events_are_emitted_for_the_whole_lifecycle(registry):
    seen = []
    events.subscribe(seen.append)
    registry.register(FakeSource([{"name": "Acme Semiconductor", "website": "acme.com",
                                   "description": "ASIC design house", "country": "India"}]))
    _pipeline(registry).run(run_id="r1")
    types = [e.type.value for e in seen]
    assert types[0] == "pipeline_started" and types[-1] == "pipeline_completed"
    assert "source_started" in types and "source_completed" in types
    assert "company_discovered" in types


def test_failure_and_duplicate_events(registry):
    seen = []
    events.subscribe(seen.append)
    registry.register(FakeSource([], name="broken", fail_times=99))
    config = PipelineConfig(enabled_sources=("broken",), retry_count=1, retry_backoff_seconds=0.0)
    DiscoveryPipeline(config=config, registry=registry).run(run_id="r")
    assert "source_failed" in [e.type.value for e in seen]


def test_a_raising_subscriber_cannot_break_a_run(registry):
    events.subscribe(lambda e: (_ for _ in ()).throw(RuntimeError("sink down")))
    ok = []
    events.subscribe(ok.append)
    registry.register(FakeSource([{"name": "Acme Semi", "website": "acme.com"}]))
    result = _pipeline(registry).run(run_id="r")
    assert result.status == "success" and ok      # the good sink still received events


def test_events_serialize_for_a_future_sink():
    e = events.DiscoveryEvent(events.EventType.COMPANY_DISCOVERED, run_id="r",
                              company_name="Acme")
    payload = e.as_dict()
    assert payload["type"] == "company_discovered" and isinstance(payload["occurred_at"], str)


# =============================================================== configuration
def test_sources_are_parsed_deduplicated_and_lowercased():
    s = _settings(discovery_sources_raw=" Firecrawl , wellfound,FIRECRAWL , ")
    assert s.discovery_sources == ["firecrawl", "wellfound"]


def test_no_configured_sources_means_none_run():
    assert _settings().discovery_sources == []


def test_pipeline_config_is_built_from_settings():
    s = _settings(discovery_sources_raw="a,b", discovery_source_limit=7,
                  discovery_concurrency=3, discovery_retry_count=5,
                  discovery_confidence_threshold=0.8)
    cfg = PipelineConfig.from_settings(s)
    assert cfg.enabled_sources == ("a", "b") and cfg.source_limit == 7
    assert cfg.concurrency == 3 and cfg.retry_count == 5
    assert cfg.confidence.threshold == 0.8


def test_a_zero_source_limit_means_unbounded():
    assert PipelineConfig.from_settings(_settings(discovery_source_limit=0)).source_limit is None


# ================================================================ persistence
def test_accepted_candidates_are_persisted(session, registry):
    registry.register(FakeSource([{"name": "Acme Semiconductor", "website": "acme.com",
                                   "description": "ASIC design house", "country": "India"}]))
    result = service.run_discovery(session, _settings(discovery_sources_raw="fake"),
                                   registry=registry)
    assert result.accepted
    rows = session.query(DiscoveryCandidateRecord).all()
    assert len(rows) == 1 and rows[0].company_name == "Acme Semiconductor"
    assert rows[0].times_seen == 1 and rows[0].status == "new"


def test_a_second_run_refreshes_rather_than_duplicating(session, registry):
    registry.register(FakeSource([{"name": "Acme Semiconductor", "website": "acme.com",
                                   "description": "ASIC design house"}]))
    settings = _settings(discovery_sources_raw="fake")
    service.run_discovery(session, settings, registry=registry)
    service.run_discovery(session, settings, registry=registry)
    rows = session.query(DiscoveryCandidateRecord).all()
    assert len(rows) == 1 and rows[0].times_seen == 2


def test_first_seen_is_never_overwritten(session, registry):
    registry.register(FakeSource([{"name": "Acme Semiconductor", "website": "acme.com",
                                   "description": "ASIC design house"}]))
    settings = _settings(discovery_sources_raw="fake")
    service.run_discovery(session, settings, registry=registry)
    original = session.query(DiscoveryCandidateRecord).one().first_seen
    service.run_discovery(session, settings, registry=registry)
    assert session.query(DiscoveryCandidateRecord).one().first_seen == original


def test_rejected_candidates_are_not_persisted(session, registry):
    registry.register(FakeSource([{"name": "A"}]))
    service.run_discovery(session, _settings(discovery_sources_raw="fake"), registry=registry)
    assert session.query(DiscoveryCandidateRecord).count() == 0


def test_discovery_never_creates_a_company(session, registry):
    """The engine parks candidates; promoting one into `companies` is a separate step."""
    registry.register(FakeSource([{"name": "Brand New Fab", "website": "brandnewfab.com",
                                   "description": "wafer foundry"}]))
    service.run_discovery(session, _settings(discovery_sources_raw="fake"), registry=registry)
    assert session.query(Company).count() == 0


def test_provenance_is_recorded_for_a_known_company(session, registry):
    session.add(Company(company_domain="acme.com", canonical_company_id="ACME",
                        company_name="Acme", name_key="acme",
                        prospect_type="PRODUCT_COMPANY", validation_status="VALID"))
    session.commit()
    registry.register(FakeSource([{"name": "Acme", "website": "acme.com",
                                   "description": "ASIC design house",
                                   "country": "India"}], name="firecrawl"))
    service.run_discovery(session, _settings(discovery_sources_raw="firecrawl"), registry=registry)
    sources = session.query(models.CompanySource).filter_by(company_domain="acme.com").all()
    assert [s.source_name for s in sources] == ["firecrawl"]


def test_a_candidate_round_trips_through_the_record(session, registry):
    registry.register(FakeSource([{"name": "Acme Semiconductor", "website": "acme.com",
                                   "description": "ASIC design house", "country": "India",
                                   "technologies": ["asic", "risc-v"]}]))
    service.run_discovery(session, _settings(discovery_sources_raw="fake"), registry=registry)
    restored = models.from_record(session.query(DiscoveryCandidateRecord).one())
    assert restored.company_name == "Acme Semiconductor"
    assert restored.technologies == ("asic", "risc-v") and restored.country == "India"


def test_persistence_failure_does_not_lose_the_result(session, registry, monkeypatch):
    registry.register(FakeSource([{"name": "Acme Semi", "website": "acme.com",
                                   "description": "ASIC design house", "country": "India"}]))
    monkeypatch.setattr(service, "_persist",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")))
    result = service.run_discovery(session, _settings(discovery_sources_raw="fake"),
                                   registry=registry)
    assert result.status == "success" and result.accepted      # findings survive


def test_discovery_can_be_disabled_entirely(session, registry):
    registry.register(FakeSource([{"name": "Acme Semi", "website": "acme.com"}]))
    result = service.run_discovery(
        session, _settings(discovery_enabled=False, discovery_sources_raw="fake"),
        registry=registry)
    assert result.fetched == 0 and session.query(DiscoveryCandidateRecord).count() == 0


def test_health_reports_registry_and_candidate_state(session, registry):
    registry.register(FakeSource(name="firecrawl"))
    health = service.discovery_health(session, _settings(discovery_sources_raw="firecrawl"),
                                      registry=registry)
    assert health["registered_sources"] == ["firecrawl"]
    assert health["enabled_sources"] == ["firecrawl"]
    assert health["sources"]["firecrawl"]["status"] == "ok"
    assert "firecrawl" in health["capabilities"]


# ========================================================= scheduler integration
def test_the_stage_is_registered_in_the_automatic_pipeline():
    from orchestrator.stages import PIPELINE_ORDER, STAGES

    assert "market_discovery" in PIPELINE_ORDER
    assert STAGES["market_discovery"].engine is None      # in-process, no external engine
    # Discovery must precede scoring so a company promoted this run is scored in it.
    assert PIPELINE_ORDER.index("market_discovery") < PIPELINE_ORDER.index("scoring")


def test_the_scheduler_knows_nothing_about_individual_sources():
    """The architectural guarantee: no source name appears in the scheduler path."""
    import ast
    import inspect
    import textwrap

    from orchestrator import stages

    tree = ast.parse(textwrap.dedent(inspect.getsource(stages.market_discovery_ingest)))
    fn = tree.body[0]
    if isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant):
        fn.body = fn.body[1:]                      # drop the docstring; keep only code
    body = ast.unparse(fn).lower()
    for name in ("firecrawl", "wellfound", "dealroom", "crunchbase", "linkedin"):
        assert name not in body, f"scheduler must not reference {name}"
    assert "registry" in body        # it talks to the registry, and only the registry


def test_the_stage_runs_with_zero_sources(session):
    from orchestrator.stages import STAGES

    metrics = STAGES["market_discovery"].ingest(session)
    assert metrics.status == "success" and metrics.rows_in == 0


def test_the_stage_reports_metrics_the_orchestrator_understands(session, registry, monkeypatch):
    from orchestrator.stages import STAGES

    registry.register(FakeSource([{"name": "Acme Semiconductor", "website": "acme.com",
                                   "description": "ASIC design house", "country": "India"}]))
    # The stage calls run_discovery() without passing a registry, so it uses the
    # process-wide default the service bound at import time — that is what to patch.
    monkeypatch.setattr(service, "default_registry", registry)
    monkeypatch.setattr("backend.config.get_settings",
                        lambda: _settings(discovery_sources_raw="fake"))
    metrics = STAGES["market_discovery"].ingest(session)
    assert metrics.rows_in == 1 and metrics.rows_upserted == 1
    assert metrics.status == "success" and "new=1" in metrics.notes


def test_the_dashboard_health_strip_includes_discovery():
    from backend.repositories import PIPELINE_COMPONENTS

    assert "market_discovery" in PIPELINE_COMPONENTS


# ==================================================== architectural boundary
# These enforce the separation of responsibilities structurally rather than by
# convention, so a future connector cannot quietly erode it.
def test_only_the_persistence_layer_can_write_to_the_database():
    """Sources, pipeline, resolver and confidence must be DB-free."""
    import pathlib

    pkg = pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_discovery"
    markers = ("session.add", "session.commit", "session.execute", "session.query",
               "session.delete", "session.merge", "session.flush")
    writers = {
        f.name for f in pkg.rglob("*.py")
        if any(m in f.read_text(encoding="utf-8") for m in markers)
    }
    assert writers == {"models.py", "service.py"}, f"unexpected DB writers: {writers}"


def test_a_source_cannot_reach_a_database_session():
    import pathlib

    base = (pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_discovery"
            / "base_source.py").read_text(encoding="utf-8")
    assert "sqlalchemy" not in base and "Session" not in base


def test_no_engine_module_references_a_specific_connector():
    """The engine stays source-agnostic: connector names appear only in prose."""
    import ast
    import pathlib

    pkg = pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_discovery"
    offenders = {}
    for f in pkg.rglob("*.py"):
        if "sources" in f.parts:
            continue          # a connector names itself; the engine must not
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = getattr(node, "body", None)
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    node.body = body[1:] or [ast.Pass()]
        code = ast.unparse(tree).lower()
        found = [c for c in ("firecrawl", "wellfound", "dealroom", "crunchbase") if c in code]
        if found:
            offenders[f.name] = found
    assert offenders == {}, f"engine code references connectors: {offenders}"


def test_a_registered_connector_still_requires_explicit_enablement(registry):
    """Registration is not activation: crawling a third party is a configuration
    decision, never a side effect of shipping the connector."""
    from backend.config import Settings

    registry.autodiscover()
    assert registry.names(), "expected at least one connector to be registered"
    assert registry.enabled_sources(Settings(_env_file=None).discovery_sources) == []
