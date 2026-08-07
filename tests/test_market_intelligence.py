"""Market Intelligence Layer (backend/market_intelligence).

Covers the rules engine and its matching guarantees, company classification,
technology detection, the three signal passes, opportunity priority, explainability,
configuration and rule packs, events, persistence, scheduler integration, logging,
determinism, performance boundaries, and the architectural boundaries that keep
business logic in this layer and nowhere else.

No network, no external service, no AI. Every test builds candidates in-process,
which is exactly how the layer runs in production — it never fetches anything.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from backend.config import Settings
from backend.market_discovery.schemas import DiscoveryCandidate
from backend.market_intelligence import events, models, scoring, service
from backend.market_intelligence.classifiers import classify, core_classifications
from backend.market_intelligence.config import IntelligenceConfig, apply_overlay, build_pack
from backend.market_intelligence.explainability import build_explanation, evidence_terms
from backend.market_intelligence.pipeline import (
    IntelligencePipeline,
    clear_enrichers,
    evaluate_candidate,
    register_enricher,
    unregister_enricher,
)
from backend.market_intelligence.rules import (
    DEFAULT_THRESHOLDS,
    DEFAULT_WEIGHTS,
    Rule,
    RulePack,
    build_context,
    evaluate_rule,
    match_terms,
    rules_from_json,
)
from backend.market_intelligence.schemas import (
    Evidence,
    MarketIntelligence,
    Priority,
    RuleKind,
    SignalCategory,
)
from backend.market_intelligence.signals import (
    detect_engineering,
    detect_funding,
    detect_signals,
    detect_strategic,
)
from backend.market_intelligence.technology import categories, detect_technologies, overlap_score
from backend.market_intelligence.vocabulary import CORE_CLASSIFICATIONS, default_pack
from master_db.local import make_session_factory
from master_db.models import DiscoveryCandidateRecord, MarketIntelligenceRecord

NOW = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)


# ------------------------------------------------------------------ fixtures
@pytest.fixture()
def session():
    with make_session_factory(":memory:")() as s:
        yield s


@pytest.fixture()
def pack():
    return default_pack()


@pytest.fixture(autouse=True)
def _isolated_extensions():
    """Events and enrichers are process-wide; no test may leak into the next."""
    events.clear_subscribers()
    clear_enrichers()
    yield
    events.clear_subscribers()
    clear_enrichers()


def candidate(**kwargs) -> DiscoveryCandidate:
    """A normalized-looking candidate. Only the engine sets candidate_key, so tests
    set it explicitly rather than pretending a source could."""
    key = kwargs.pop("candidate_key", "key-" + kwargs.get("company_name", "x").lower()[:8])
    domain = kwargs.pop("company_domain", "")
    metadata = kwargs.pop("metadata", None)
    fields = {"company_name": "Acme Silicon", "source": "fake",
              "first_seen": NOW, "last_seen": NOW}
    fields.update(kwargs)
    out = DiscoveryCandidate(**fields)
    out.candidate_key = key
    out.company_domain = domain
    if metadata is not None:
        out.metadata = metadata
    out.metadata.setdefault("sources", (out.source,) if out.source else ())
    return out


def ctx(cand, pack, *, year: int = 2026):
    return build_context(cand, pack=pack, now_year=year)


# ================================================================ rules engine
def test_a_single_word_term_matches_only_a_whole_token(pack):
    """"chip" must never match "chipotle" — the guarantee the whole layer rests on."""
    found = match_terms(ctx(candidate(description="We sell chipotle bowls"), pack), ("chip",))
    assert found == ()
    found = match_terms(ctx(candidate(description="We build a chip"), pack), ("chip",))
    assert [e.term for e in found] == ["chip"]


def test_a_hyphenated_word_still_matches_a_single_word_term(pack):
    """Tokenization splits on hyphens, so "ai-accelerator" contains "accelerator"."""
    found = match_terms(ctx(candidate(description="An ai-accelerator company"), pack),
                        ("accelerator",))
    assert [e.term for e in found] == ["accelerator"]


def test_a_punctuated_term_is_boundary_anchored(pack):
    """"2.5d" must not match inside "12.5db"."""
    assert match_terms(ctx(candidate(description="rated at 12.5db"), pack), ("2.5d",)) == ()
    assert match_terms(ctx(candidate(description="uses 2.5d packaging"), pack), ("2.5d",))


def test_a_multi_word_phrase_matches_as_a_phrase(pack):
    found = match_terms(ctx(candidate(description="expert in physical design flows"), pack),
                        ("physical design",))
    assert [e.field for e in found] == ["description"]


def test_matching_is_case_insensitive_through_normalization(pack):
    found = match_terms(ctx(candidate(description="Leading ASIC and RTL work"), pack),
                        ("asic", "rtl"))
    assert sorted(e.term for e in found) == ["asic", "rtl"]


def test_evidence_records_which_field_it_came_from(pack):
    cand = candidate(company_name="Acme ASIC", description="An asic design house")
    found = match_terms(ctx(cand, pack), ("asic",))
    assert {e.field for e in found} == {"company_name", "description"}


def test_a_rule_can_restrict_which_fields_it_reads(pack):
    cand = candidate(description="hiring engineers", country="hiring")
    rule = Rule(key="r", label="R", kind=RuleKind.SIGNAL, terms=("hiring",),
                fields=("description",))
    match = evaluate_rule(rule, ctx(cand, pack), pack=pack)
    assert [e.field for e in match.evidence] == ["description"]


def test_min_matches_requires_corroboration(pack):
    cand = candidate(description="an asic company")
    rule = Rule(key="r", label="R", kind=RuleKind.SIGNAL, terms=("asic",), min_matches=2)
    assert evaluate_rule(rule, ctx(cand, pack), pack=pack) is None


def test_confidence_rises_with_independent_evidence(pack):
    one = candidate(description="an asic company")
    two = candidate(company_name="Acme ASIC", description="an asic company")
    rule = Rule(key="r", label="R", kind=RuleKind.SIGNAL, terms=("asic",),
                base_confidence=0.6)
    weak = evaluate_rule(rule, ctx(one, pack), pack=pack)
    strong = evaluate_rule(rule, ctx(two, pack), pack=pack)
    assert strong.confidence > weak.confidence


def test_confidence_never_exceeds_the_rule_ceiling(pack):
    cand = candidate(company_name="asic asic", description="asic asic asic",
                     industry="asic", markets=("asic",), technologies=("asic",))
    rule = Rule(key="r", label="R", kind=RuleKind.SIGNAL, terms=("asic",),
                base_confidence=0.9, max_confidence=0.95)
    assert evaluate_rule(rule, ctx(cand, pack), pack=pack).confidence <= 0.95


def test_a_disabled_rule_never_fires(pack):
    rule = Rule(key="r", label="R", kind=RuleKind.SIGNAL, terms=("asic",), enabled=False)
    assert evaluate_rule(rule, ctx(candidate(description="asic"), pack), pack=pack) is None


def test_a_rule_with_unmet_prerequisites_does_not_fire(pack):
    rule = Rule(key="r", label="R", kind=RuleKind.SIGNAL, requires=("fact:early_stage",))
    assert evaluate_rule(rule, ctx(candidate(), pack), pack=pack) is None


def test_requires_any_is_satisfied_by_one_member_of_each_group(pack):
    cand = candidate(funding_stage="seed")
    rule = Rule(key="r", label="R", kind=RuleKind.SIGNAL,
                requires_any=(("fact:early_stage", "fact:recently_founded"),))
    assert evaluate_rule(rule, ctx(cand, pack), pack=pack) is not None


def test_excludes_blocks_a_rule(pack):
    context = ctx(candidate(website="https://acme.com"), pack)
    rule = Rule(key="r", label="R", kind=RuleKind.SIGNAL, requires=("fact:has_website",),
                excludes=("fact:has_website",))
    assert evaluate_rule(rule, context, pack=pack) is None


def test_a_source_scoped_rule_only_fires_for_that_source(pack):
    rule = Rule(key="r", label="R", kind=RuleKind.SIGNAL, sources=("nvidia_inception",))
    assert evaluate_rule(rule, ctx(candidate(source="wellfound"), pack), pack=pack) is None
    assert evaluate_rule(rule, ctx(candidate(source="nvidia_inception"), pack),
                         pack=pack) is not None


def test_a_derived_rule_inherits_the_evidence_of_its_prerequisites(pack):
    """A conclusion drawn from other rules must still point at published text."""
    cand = candidate(description="a fabless asic company")
    context = ctx(cand, pack)
    classify(context, pack=pack)
    rule = Rule(key="derived", label="Derived", kind=RuleKind.SIGNAL, requires=("fabless",))
    match = evaluate_rule(rule, context, pack=pack)
    assert match.evidence and all(e.term for e in match.evidence)


def test_a_rule_that_matches_nothing_is_rejected_at_definition_time():
    with pytest.raises(ValueError):
        Rule(key="empty", label="Empty", kind=RuleKind.SIGNAL)


def test_facts_are_derived_from_the_candidate_alone(pack):
    cand = candidate(website="https://acme.com", founded_year="2024",
                     funding_stage="seed", description="x" * 50)
    facts = ctx(cand, pack).facts
    assert {"has_website", "has_description", "early_stage", "recently_founded",
            "first_sighting"} <= facts


def test_an_old_company_is_not_recently_founded(pack):
    facts = ctx(candidate(founded_year="1998"), pack).facts
    assert "has_founded_year" in facts and "recently_founded" not in facts


def test_a_re_seen_candidate_is_not_a_first_sighting(pack):
    cand = candidate(first_seen=NOW, last_seen=NOW + timedelta(days=3))
    assert "first_sighting" not in ctx(cand, pack).facts


# ============================================================== classification
def test_a_fabless_company_is_classified(pack):
    found = classify(ctx(candidate(description="A fabless semiconductor startup"), pack),
                     pack=pack)
    assert "fabless" in [c.key for c in found]


def test_a_company_can_hold_several_classifications(pack):
    cand = candidate(description="A fabless AI accelerator company building robots")
    keys = [c.key for c in classify(ctx(cand, pack), pack=pack)]
    assert {"fabless", "ai_hardware", "robotics"} <= set(keys)


def test_the_most_specific_classification_comes_first(pack):
    """Fabless outranks the generic Semiconductor for text supporting both."""
    cand = candidate(description="A fabless semiconductor company")
    found = classify(ctx(cand, pack), pack=pack)
    assert found[0].key == "fabless"


def test_an_unrecognizable_company_gets_no_classification(pack):
    """No catch-all "Other": an absence of evidence is reported as an absence."""
    cand = candidate(company_name="Blue Bottle", description="A coffee roaster.")
    assert classify(ctx(cand, pack), pack=pack) == ()


def test_core_and_adjacent_markets_are_distinguished(pack):
    core = classify(ctx(candidate(description="fabless asic design"), pack), pack=pack)
    adjacent = classify(ctx(candidate(description="industrial automation systems"), pack),
                        pack=pack)
    assert core_classifications(core) and not core_classifications(adjacent)


def test_every_classification_carries_its_evidence(pack):
    found = classify(ctx(candidate(description="an eda tools vendor"), pack), pack=pack)
    assert all(c.evidence for c in found)


def test_classification_reads_the_technologies_field_too(pack):
    cand = candidate(company_name="Acme", technologies=("ai accelerator",))
    assert "ai_hardware" in [c.key for c in classify(ctx(cand, pack), pack=pack)]


# ================================================================== technology
def test_technologies_are_detected_from_the_description(pack):
    cand = candidate(description="We do RTL design, DFT and physical design for SoCs")
    keys = [t.key for t in detect_technologies(ctx(cand, pack), pack=pack)]
    assert {"rtl", "dft", "physical_design", "soc"} <= set(keys)


def test_technology_detection_covers_the_configured_vocabulary(pack):
    cand = candidate(description="chiplet risc-v serdes pcie hbm 3d ic iso 26262 cuda")
    keys = {t.key for t in detect_technologies(ctx(cand, pack), pack=pack)}
    assert {"chiplet", "risc_v", "serdes", "pcie", "hbm", "three_d_ic", "iso_26262",
            "cuda"} <= keys


def test_technologies_are_grouped_into_categories(pack):
    cand = candidate(description="asic design with advanced packaging and pcie")
    found = detect_technologies(ctx(cand, pack), pack=pack)
    assert {"design", "packaging", "interface"} <= set(categories(found))


def test_overlap_saturates_at_the_configured_target(pack):
    cand = candidate(description="asic rtl fpga soc pcie ddr hbm")
    found = detect_technologies(ctx(cand, pack), pack=pack)
    assert overlap_score(found, target=3.0) == 1.0
    assert 0 < overlap_score(found[:1], target=3.0) < 1.0


def test_no_technologies_means_no_overlap(pack):
    assert overlap_score((), target=3.0) == 0.0


# =========================================================== engineering signals
def test_engineering_hiring_is_detected(pack):
    cand = candidate(description="We are hiring engineers across the design team")
    assert "engineering_hiring" in [s.key for s in
                                    detect_engineering(ctx(cand, pack), pack=pack)]


def test_engineering_expansion_is_detected(pack):
    cand = candidate(description="Opening a new design centre and scaling the team")
    keys = [s.key for s in detect_engineering(ctx(cand, pack), pack=pack)]
    assert "engineering_expansion" in keys and "engineering_centre" in keys


def test_design_and_verification_services_are_detected(pack):
    cand = candidate(description="ASIC design services and verification services")
    keys = [s.key for s in detect_engineering(ctx(cand, pack), pack=pack)]
    assert {"design_services", "verification_services"} <= set(keys)


def test_chip_development_and_manufacturing_are_detected(pack):
    cand = candidate(description="First silicon taped out; volume production started")
    keys = [s.key for s in detect_engineering(ctx(cand, pack), pack=pack)]
    assert {"chip_development", "manufacturing_activity"} <= set(keys)


def test_eda_usage_is_detected_from_tool_names(pack):
    cand = candidate(description="Our flow uses Cadence and Synopsys tools")
    assert "eda_usage" in [s.key for s in detect_engineering(ctx(cand, pack), pack=pack)]


def test_every_engineering_signal_is_categorized_and_explained(pack):
    cand = candidate(description="We are hiring engineers for silicon bring-up")
    for signal in detect_engineering(ctx(cand, pack), pack=pack):
        assert signal.category is SignalCategory.ENGINEERING
        assert signal.explanation and signal.type


# =============================================================== funding signals
@pytest.mark.parametrize("text,expected", [
    ("closed a seed round", "seed_funding"),
    ("raised a series a", "series_a"),
    ("raised a series b", "series_b"),
    ("announced its series c", "series_c_plus"),
    ("completed its initial public offering", "ipo"),
    ("a strategic investment from a corporate venture arm", "strategic_investment"),
    ("awarded a research grant", "grant_funding"),
    ("supported by the india semiconductor mission", "government_funding"),
    ("part of the techstars accelerator program", "accelerator"),
    ("incubated at the university", "incubator"),
])
def test_funding_signals_are_detected(pack, text, expected):
    cand = candidate(description=f"The company {text}.")
    assert expected in [s.key for s in detect_funding(ctx(cand, pack), pack=pack)]


def test_funding_stage_alone_is_enough(pack):
    cand = candidate(funding_stage="series b")
    assert "series_b" in [s.key for s in detect_funding(ctx(cand, pack), pack=pack)]


def test_an_ai_accelerator_is_not_read_as_an_accelerator_programme(pack):
    """The word "accelerator" is hardware here; treating it as funding would put a
    false Accelerator Member on real chip companies."""
    cand = candidate(description="We build an AI accelerator", technologies=("ai accelerator",))
    assert "accelerator" not in [s.key for s in detect_funding(ctx(cand, pack), pack=pack)]


# ============================================================= strategic signals
def test_a_new_market_entrant_needs_a_first_sighting_and_a_market(pack):
    cand = candidate(description="A fabless semiconductor company", first_seen=NOW,
                     last_seen=NOW)
    context = ctx(cand, pack)
    classify(context, pack=pack)
    detect_technologies(context, pack=pack)
    detect_engineering(context, pack=pack)
    detect_funding(context, pack=pack)
    assert "new_market_entrant" in [s.key for s in detect_strategic(context, pack=pack)]


def test_a_known_company_is_not_a_new_market_entrant(pack):
    cand = candidate(description="A fabless semiconductor company", first_seen=NOW,
                     last_seen=NOW + timedelta(days=10))
    context = ctx(cand, pack)
    classify(context, pack=pack)
    assert "new_market_entrant" not in [s.key for s in detect_strategic(context, pack=pack)]


def test_a_semiconductor_startup_needs_both_market_and_stage(pack):
    early = candidate(description="A fabless chip company", funding_stage="seed")
    mature = candidate(description="A fabless chip company", founded_year="1985")
    assert "semiconductor_startup" in _signal_keys(early, pack)
    assert "semiconductor_startup" not in _signal_keys(mature, pack)


def test_derived_company_type_signals_follow_their_classification(pack):
    assert "ai_hardware_company" in _signal_keys(
        candidate(description="We build an ai accelerator chip"), pack)
    assert "eda_company" in _signal_keys(
        candidate(description="An electronic design automation vendor"), pack)
    assert "ip_company" in _signal_keys(
        candidate(description="We license silicon ip cores"), pack)


def test_edge_ai_is_detected_from_its_own_vocabulary(pack):
    assert "edge_ai" in _signal_keys(candidate(description="tinyml inference at the edge"),
                                     pack)


def test_a_strategic_partnership_is_detected(pack):
    assert "strategic_partnership" in _signal_keys(
        candidate(description="Announced a strategic partnership with a foundry"), pack)


def test_technology_launch_requires_a_relevant_company(pack):
    relevant = candidate(description="The fabless firm unveils a new architecture")
    unrelated = candidate(company_name="Cafe Co", description="The cafe unveils a new menu")
    assert "technology_launch" in _signal_keys(relevant, pack)
    assert "technology_launch" not in _signal_keys(unrelated, pack)


def test_ecosystem_membership_is_interpreted_here_not_by_the_connector(pack):
    assert "nvidia_ecosystem" in _signal_keys(candidate(source="nvidia_inception"), pack)
    assert "nvidia_ecosystem" not in _signal_keys(candidate(source="wellfound"), pack)


def test_a_signal_below_the_reporting_floor_is_not_reported(pack):
    strict = pack.with_overrides(thresholds={"signal_min_confidence": 0.99})
    cand = candidate(description="We are hiring engineers")
    assert detect_signals(ctx(cand, strict), pack=strict) == ()


def test_a_weak_signal_still_counts_as_a_prerequisite(pack):
    """Raising the reporting floor must not silently break a derived rule."""
    strict = pack.with_overrides(thresholds={"signal_min_confidence": 0.66})
    cand = candidate(description="A fabless chip company. Volume production started.",
                     funding_stage="seed")
    context = ctx(cand, strict)
    classify(context, pack=strict)
    detect_technologies(context, pack=strict)
    detect_signals(context, pack=strict)
    assert "manufacturing_capability" in context.matched


def _signal_keys(cand, pack) -> list[str]:
    context = ctx(cand, pack)
    classify(context, pack=pack)
    detect_technologies(context, pack=pack)
    return [s.key for s in detect_signals(context, pack=pack)]


# ============================================================ priority + scoring
def test_a_strong_semiconductor_company_is_high_priority():
    record = evaluate_candidate(candidate(
        company_name="Lightwheel", website="https://lightwheel.ai",
        description=("Lightwheel builds AI accelerator silicon: a fabless SoC with PCIe "
                     "and ASIC design. Series A funded and hiring engineers."),
        technologies=("ai accelerator", "soc", "pcie"), funding_stage="series a",
        founded_year="2024", headquarters="San Jose", confidence=0.5,
        company_domain="lightwheel.ai"))
    assert record.priority in (Priority.CRITICAL, Priority.HIGH)


def test_an_unrelated_company_is_low_priority():
    record = evaluate_candidate(candidate(
        company_name="Blue Bottle", description="A specialty coffee roaster.",
        website="https://bluebottle.com", confidence=0.3))
    assert record.priority is Priority.LOW


def test_the_score_is_the_weighted_mean_of_its_factors(pack):
    """The published arithmetic must reproduce the score by hand."""
    record = evaluate_candidate(candidate(
        description="A fabless asic company", funding_stage="seed", confidence=0.5))
    earned = sum(f.contribution for f in record.factors)
    weight = sum(f.weight for f in record.factors)
    assert record.priority_score == pytest.approx(round(earned / weight, 4), abs=1e-4)


def test_every_factor_reports_value_weight_and_contribution():
    record = evaluate_candidate(candidate(description="A fabless asic company"))
    assert record.factors
    for factor in record.factors:
        assert factor.contribution == pytest.approx(factor.value * factor.weight, abs=1e-4)
        assert 0.0 <= factor.value <= 1.0


def test_a_zero_weight_factor_is_not_evaluated_and_not_in_the_denominator(pack):
    without = pack.with_overrides(weights={"funding_activity": 0.0})
    config = IntelligenceConfig(pack=without)
    record = IntelligencePipeline(config).evaluate(candidate(description="fabless asic"))
    assert "funding_activity" not in [f.name for f in record.factors]


def test_priority_bands_come_from_configuration(pack):
    everything_critical = pack.with_overrides(thresholds={"priority_critical": 0.0})
    record = IntelligencePipeline(IntelligenceConfig(pack=everything_critical)).evaluate(
        candidate(company_name="Cafe", description="A coffee shop."))
    assert record.priority is Priority.CRITICAL


def test_the_band_reports_the_threshold_it_cleared(pack):
    assessment = scoring.assess(candidate(), classifications=(), technologies=(),
                                signals=(), pack=pack)
    assert assessment.priority is Priority.LOW and assessment.threshold == 0.0


def test_core_semiconductor_outranks_an_adjacent_market():
    core = evaluate_candidate(candidate(description="A fabless asic design house"))
    adjacent = evaluate_candidate(candidate(description="An industrial automation vendor"))
    assert core.priority_score > adjacent.priority_score


def test_confidence_is_separate_from_priority():
    """A company can be confidently unimportant, or promisingly under-documented."""
    thin = evaluate_candidate(candidate(company_name="Acme", description="asic"))
    rich = evaluate_candidate(candidate(
        company_name="Acme", website="https://acme.com", company_domain="acme.com",
        description="A fabless asic and soc design house using rtl and dft flows.",
        founded_year="2023", headquarters="Bengaluru", funding_stage="seed",
        confidence=0.6))
    assert rich.confidence > thin.confidence


def test_confidence_never_leaves_the_unit_interval():
    record = evaluate_candidate(candidate(confidence=5.0, description="asic soc rtl dft"))
    assert 0.0 <= record.confidence <= 1.0


# ============================================================== explainability
def test_every_record_explains_itself():
    record = evaluate_candidate(candidate(description="A fabless asic company"))
    assert record.reasons and record.explanation
    assert record.priority.value.upper() in record.explanation


def test_the_explanation_names_the_evidence():
    record = evaluate_candidate(candidate(description="We design ASICs and SoCs"))
    assert "asic" in record.explanation.lower()


def test_an_unclassified_company_says_so_rather_than_staying_silent():
    record = evaluate_candidate(candidate(company_name="Cafe", description="Coffee."))
    assert any("no classification" in r.lower() for r in record.reasons)


def test_the_explanation_names_what_was_not_found():
    record = evaluate_candidate(candidate(company_name="Cafe", description="Coffee."))
    assert any("no evidence found" in r.lower() for r in record.reasons)


def test_the_score_composition_is_published_in_the_explanation():
    record = evaluate_candidate(candidate(description="A fabless asic company"))
    assert "score composition" in record.explanation.lower()


def test_evidence_terms_are_de_duplicated_and_truncated():
    evidence = tuple(Evidence("description", t) for t in ("a", "a", "b", "c", "d", "e"))
    assert evidence_terms(evidence, limit=3) == "a, b, c (+2 more)"


def test_explanations_never_invent_a_value():
    """Nothing may claim a website, a location or a stage the candidate lacks."""
    record = evaluate_candidate(candidate(company_name="Acme", description="asic design"))
    text = " ".join(record.reasons).lower()
    assert "verified company website" not in text


# ============================================================== rules + packs
def test_the_shipped_pack_is_internally_consistent(pack):
    keys = [r.key for r in pack.rules]
    assert len(keys) == len(set(keys)), "rule keys must be globally unique"
    known = set(keys)
    for rule in pack.rules:
        for dep in (*rule.requires, *(k for g in rule.requires_any for k in g)):
            if dep.startswith(("fact:", "source:")):
                continue
            assert dep in known, f"{rule.key} depends on unknown rule {dep}"


def test_rules_are_evaluated_in_the_configured_priority_order(pack):
    ordered = pack.of_kind(RuleKind.CLASSIFICATION)
    assert [r.priority for r in ordered] == sorted(r.priority for r in ordered)


def test_a_rule_can_be_disabled_by_configuration(pack):
    without = pack.with_overrides(disabled=["fabless"])
    keys = [c.key for c in classify(ctx(candidate(description="a fabless company"),
                                        without), pack=without)]
    assert "fabless" not in keys


def test_vocabulary_can_be_extended_by_configuration(pack):
    extended = pack.with_overrides(extra_terms={"asic": ["bespoke silicon"]})
    cand = candidate(description="We build bespoke silicon")
    assert "asic" in [t.key for t in detect_technologies(ctx(cand, extended),
                                                         pack=extended)]


def test_overrides_never_mutate_the_original_pack(pack):
    before = [r.enabled for r in pack.rules]
    pack.with_overrides(disabled=["fabless"], thresholds={"priority_high": 0.9})
    assert [r.enabled for r in pack.rules] == before
    assert pack.threshold("priority_high") == DEFAULT_THRESHOLDS["priority_high"]


def test_an_overlay_can_add_a_rule_and_bumps_the_pack_version(pack):
    overlay = {"rules": [{"key": "photonics", "label": "Photonics", "kind": "classification",
                          "terms": ["photonics", "silicon photonics"], "core": True}]}
    extended = apply_overlay(pack, overlay)
    assert extended.rule("photonics") is not None
    assert extended.version != pack.version
    cand = candidate(description="A silicon photonics company")
    assert "photonics" in [c.key for c in classify(ctx(cand, extended), pack=extended)]


def test_an_overlay_can_replace_a_built_in_rule(pack):
    overlay = {"rules": [{"key": "fabless", "label": "Fab-less", "kind": "classification",
                          "terms": ["no fab"]}]}
    extended = apply_overlay(pack, overlay)
    assert extended.rule("fabless").label == "Fab-less"
    assert len(extended.rules) == len(pack.rules)


def test_a_malformed_overlay_rule_is_skipped_not_fatal():
    assert rules_from_json([{"label": "no key"}, {"key": "ok", "kind": "signal",
                                                 "terms": ["x"]}]) [0].key == "ok"


def test_an_empty_overlay_leaves_the_pack_untouched(pack):
    assert apply_overlay(pack, {}) is pack


# ============================================================== configuration
def _settings(**kwargs) -> Settings:
    return Settings(_env_file=None, **kwargs)


def test_configuration_defaults_are_safe():
    config = IntelligenceConfig.from_settings(_settings())
    assert config.enabled and config.pack.name == "semiconductor"
    assert config.pack.threshold("priority_high") == DEFAULT_THRESHOLDS["priority_high"]


def test_priority_thresholds_are_environment_driven():
    config = IntelligenceConfig.from_settings(_settings(intelligence_priority_high=0.9))
    assert config.pack.threshold("priority_high") == 0.9


def test_weights_can_be_overridden_as_json():
    config = IntelligenceConfig.from_settings(
        _settings(intelligence_weights_raw='{"funding_activity": 4}'))
    assert config.pack.weight("funding_activity") == 4.0
    assert config.pack.weight("technology_overlap") == DEFAULT_WEIGHTS["technology_overlap"]


def test_extra_vocabulary_can_be_supplied_as_json():
    config = IntelligenceConfig.from_settings(
        _settings(intelligence_extra_terms_raw='{"asic": ["bespoke silicon"]}'))
    assert "bespoke silicon" in config.pack.rule("asic").terms


def test_rules_can_be_disabled_by_environment():
    config = IntelligenceConfig.from_settings(
        _settings(intelligence_disabled_rules_raw="fabless, quantum"))
    assert config.pack.rule("fabless").enabled is False
    assert config.pack.rule("quantum").enabled is False


def test_malformed_configuration_json_is_ignored_not_fatal():
    config = IntelligenceConfig.from_settings(
        _settings(intelligence_weights_raw="{not json"))
    assert config.pack.weight("funding_activity") == DEFAULT_WEIGHTS["funding_activity"]


def test_an_unknown_rule_pack_falls_back_to_the_built_in_one():
    assert build_pack(_settings(intelligence_rule_pack="nope")).name == "semiconductor"


def test_a_missing_overlay_file_falls_back_to_the_built_in_pack():
    pack = build_pack(_settings(intelligence_rules_path="does/not/exist.json"))
    assert pack.rule("fabless") is not None


def test_an_overlay_file_is_loaded(tmp_path):
    path = tmp_path / "pack.json"
    path.write_text(json.dumps({"version": "9.9", "disable": ["quantum"]}), encoding="utf-8")
    pack = build_pack(_settings(intelligence_rules_path=str(path)))
    assert pack.version == "9.9" and pack.rule("quantum").enabled is False


def test_the_layer_can_be_switched_off(session):
    result = service.run_market_intelligence(session, _settings(intelligence_enabled=False))
    assert result.evaluated == 0 and result.status == "success"


def test_no_business_rule_is_hardcoded_outside_the_vocabulary():
    """Vocabulary lives in rule packs; the engine modules must carry no term lists."""
    import pathlib

    pkg = pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_intelligence"
    for name in ("classifiers.py", "technology.py", "signals.py", "scoring.py"):
        source = (pkg / name).read_text(encoding="utf-8")
        for term in ("fabless", "risc-v", "series a"):
            code = "\n".join(line for line in source.splitlines()
                             if not line.strip().startswith("#"))
            assert f'"{term}"' not in code, f"{name} hardcodes the term {term!r}"


# ==================================================================== pipeline
def test_the_pipeline_runs_every_stage():
    record = evaluate_candidate(candidate(
        description="A fabless AI accelerator startup building an ASIC. Seed funded.",
        funding_stage="seed", website="https://acme.com", company_domain="acme.com"))
    assert record.classifications and record.technologies and record.signals
    assert record.priority and record.reasons and record.explanation


def test_a_candidate_without_identity_is_rejected():
    orphan = candidate(candidate_key="")
    result = IntelligencePipeline().run([orphan])
    assert result.rejected == 1 and result.evaluated == 0


def test_a_thin_candidate_is_still_interpreted():
    """A name-only company must not vanish: an honest LOW is information."""
    result = IntelligencePipeline().run([candidate(company_name="Acme")])
    assert result.evaluated == 1 and result.records[0].priority is Priority.LOW


def test_one_failing_candidate_does_not_cost_the_others(monkeypatch):
    pipeline = IntelligencePipeline()
    original = pipeline.evaluate

    def explode(cand, **kwargs):
        if cand.company_name == "Bad":
            raise RuntimeError("boom")
        return original(cand, **kwargs)

    monkeypatch.setattr(pipeline, "evaluate", explode)
    result = pipeline.run([candidate(company_name="Bad", candidate_key="a"),
                           candidate(company_name="Good", candidate_key="b")])
    assert result.evaluated == 1 and result.failed == 1
    assert result.status == "partial"


def test_the_pipeline_never_mutates_its_input():
    cand = candidate(description="A fabless asic company")
    before = (cand.company_name, cand.technologies, dict(cand.metadata))
    evaluate_candidate(cand)
    assert (cand.company_name, cand.technologies, dict(cand.metadata)) == before


def test_the_result_summarizes_by_priority():
    result = IntelligencePipeline().run([candidate(company_name="Cafe",
                                                   description="Coffee.")])
    assert result.by_priority["low"] == 1 and "low=1" in result.summary()


def test_actionable_records_are_the_critical_and_high_ones():
    result = IntelligencePipeline().run([
        candidate(company_name="Cafe", candidate_key="a", description="Coffee."),
        candidate(company_name="Chipco", candidate_key="b", website="https://chipco.com",
                  company_domain="chipco.com", funding_stage="seed", founded_year="2024",
                  headquarters="Austin", confidence=0.6,
                  description=("A fabless AI accelerator startup: ASIC, SoC, RTL and "
                               "PCIe design. Hiring engineers, series a funded.")),
    ])
    assert [r.company_name for r in result.actionable] == ["Chipco"]


# ================================================================= determinism
def test_the_same_candidate_always_produces_the_same_record():
    cand = candidate(description="A fabless AI accelerator startup with ASIC and PCIe",
                     funding_stage="seed", website="https://acme.com")
    first = evaluate_candidate(cand).as_dict()
    second = evaluate_candidate(cand).as_dict()
    for out in (first, second):
        out.pop("evaluated_at")
    assert first == second


def test_evidence_order_is_stable_not_set_order():
    cand = candidate(company_name="ASIC Corp", description="asic and soc design",
                     technologies=("asic",))
    runs = [[e.as_dict() for c in evaluate_candidate(cand).classifications
             for e in c.evidence] for _ in range(5)]
    assert all(r == runs[0] for r in runs)


def test_batch_order_matches_input_order_regardless_of_concurrency():
    batch = [candidate(company_name=f"Co{i}", candidate_key=f"k{i}") for i in range(12)]
    serial = IntelligencePipeline(IntelligenceConfig(concurrency=1)).run(batch)
    parallel = IntelligencePipeline(IntelligenceConfig(concurrency=4)).run(batch)
    assert ([r.company_name for r in serial.records]
            == [r.company_name for r in parallel.records])


def test_concurrency_does_not_change_any_score():
    batch = [candidate(company_name=f"Co{i}", candidate_key=f"k{i}",
                       description="A fabless asic company") for i in range(8)]
    serial = IntelligencePipeline(IntelligenceConfig(concurrency=1)).run(batch)
    parallel = IntelligencePipeline(IntelligenceConfig(concurrency=4)).run(batch)
    assert ([r.priority_score for r in serial.records]
            == [r.priority_score for r in parallel.records])


# ======================================================== performance boundaries
def test_a_large_batch_stays_within_a_sane_time_budget():
    """Guards against an accidental O(n²) or a per-candidate re-compile."""
    import time

    batch = [candidate(company_name=f"Co{i}", candidate_key=f"k{i}",
                       description="A fabless AI accelerator company doing ASIC, RTL, "
                                   "DFT and physical design work. Series A funded.")
             for i in range(300)]
    started = time.monotonic()
    result = IntelligencePipeline().run(batch)
    elapsed = time.monotonic() - started
    assert result.evaluated == 300
    assert elapsed < 10.0, f"300 candidates took {elapsed:.1f}s"


def test_text_is_decomposed_once_per_candidate(pack):
    """Every rule reads the same prepared context — twenty rules, one tokenization."""
    context = ctx(candidate(description="asic soc rtl"), pack)
    assert set(context.tokens) == {name for name, _ in context.fields}


def test_the_batch_size_bounds_one_pass(session):
    _store_candidates(session, 5)
    config = IntelligenceConfig(batch_size=2)
    result = service.run_market_intelligence(session, _settings(), config=config)
    assert result.evaluated == 2


# ================================================================== persistence
def _store_candidates(session, count: int, *, status: str = "new") -> None:
    for i in range(count):
        session.add(DiscoveryCandidateRecord(
            candidate_key=f"key{i}", company_name=f"Company {i}",
            company_domain=f"co{i}.com", website=f"https://co{i}.com",
            description="A fabless asic design company.", source="fake",
            status=status, confidence=0.5, first_seen=NOW, last_seen=NOW,
            technologies=json.dumps(["asic"]), markets="[]", sources=json.dumps(["fake"]),
        ))
    session.commit()


def test_a_run_persists_one_row_per_candidate(session):
    _store_candidates(session, 3)
    service.run_market_intelligence(session, _settings())
    assert session.query(MarketIntelligenceRecord).count() == 3


def test_persisted_rows_carry_the_queryable_columns(session):
    _store_candidates(session, 1)
    service.run_market_intelligence(session, _settings())
    row = session.query(MarketIntelligenceRecord).one()
    assert row.priority in {"critical", "high", "medium", "low"}
    assert row.primary_classification and row.rule_pack == "semiconductor"
    assert json.loads(row.classifications) and json.loads(row.factors)


def test_re_running_replaces_rather_than_duplicates(session):
    _store_candidates(session, 2)
    service.run_market_intelligence(session, _settings(),
                                    config=IntelligenceConfig(reprocess_all=True))
    service.run_market_intelligence(session, _settings(),
                                    config=IntelligenceConfig(reprocess_all=True))
    assert session.query(MarketIntelligenceRecord).count() == 2


def test_an_unchanged_candidate_is_skipped_on_the_next_run(session):
    _store_candidates(session, 3)
    service.run_market_intelligence(session, _settings())
    second = service.run_market_intelligence(session, _settings())
    assert second.evaluated == 0 and second.skipped == 3


def test_a_re_seen_candidate_is_interpreted_again(session):
    _store_candidates(session, 1)
    service.run_market_intelligence(session, _settings())
    # Seen again AFTER it was interpreted — the comparison is against the stored
    # evaluation time, which is wall-clock, not the fixture's timestamp.
    evaluated = session.query(MarketIntelligenceRecord).one().evaluated_at
    row = session.query(DiscoveryCandidateRecord).one()
    row.last_seen = evaluated.replace(tzinfo=None) + timedelta(days=1)
    session.commit()
    assert service.run_market_intelligence(session, _settings()).evaluated == 1


def test_reprocess_all_ignores_the_incremental_shortcut(session):
    _store_candidates(session, 2)
    service.run_market_intelligence(session, _settings())
    again = service.run_market_intelligence(session, _settings(),
                                            config=IntelligenceConfig(reprocess_all=True))
    assert again.evaluated == 2 and again.skipped == 0


def test_rejected_and_duplicate_candidates_are_not_interpreted(session):
    _store_candidates(session, 2, status="duplicate")
    assert service.run_market_intelligence(session, _settings()).evaluated == 0


def test_the_layer_never_writes_to_companies_or_candidates(session):
    from master_db.models import Company

    _store_candidates(session, 2)
    service.run_market_intelligence(session, _settings())
    assert session.query(Company).count() == 0
    statuses = {r.status for r in session.query(DiscoveryCandidateRecord)}
    assert statuses == {"new"}      # discovery's own field, untouched


def test_a_write_failure_does_not_lose_the_findings(session, monkeypatch):
    _store_candidates(session, 1)
    monkeypatch.setattr(models, "upsert_record",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")))
    result = service.run_market_intelligence(session, _settings())
    assert result.evaluated == 1      # computed, even though nothing was written


def test_priority_counts_are_reported(session):
    _store_candidates(session, 2)
    service.run_market_intelligence(session, _settings())
    assert sum(models.priority_counts(session).values()) == 2


def test_health_reports_the_active_configuration(session):
    health = service.intelligence_health(session, _settings())
    assert health["enabled"] and health["rule_pack"] == "semiconductor"
    assert health["rules"]["classifications"] > 0 and health["rules"]["signals"] > 0
    assert set(health["records"]) == {"critical", "high", "medium", "low"}


def test_the_candidate_query_is_deterministically_ordered(session):
    _store_candidates(session, 4)
    first = [r.candidate_key for r in models.candidates_for_intelligence(session, limit=2)]
    second = [r.candidate_key for r in models.candidates_for_intelligence(session, limit=2)]
    assert first == second


# ====================================================================== events
def test_every_stage_emits_a_structured_event():
    seen = []
    events.subscribe(seen.append)
    evaluate_candidate(candidate(description="A fabless asic company. Seed funded.",
                                 funding_stage="seed"))
    types = {e.type.value for e in seen}
    assert {"company_classified", "technology_identified", "signal_generated",
            "priority_assigned"} <= types


def test_pipeline_events_bracket_a_run():
    seen = []
    events.subscribe(seen.append)
    IntelligencePipeline().run([candidate()], run_id="r1")
    assert seen[0].type.value == "pipeline_started"
    assert seen[-1].type.value == "pipeline_completed"


def test_a_rejected_candidate_emits_an_event():
    seen = []
    events.subscribe(seen.append)
    IntelligencePipeline().run([candidate(candidate_key="")])
    assert any(e.type.value == "candidate_rejected" for e in seen)


def test_a_failing_subscriber_cannot_break_a_run():
    def bad(_event):
        raise RuntimeError("sink is down")

    events.subscribe(bad)
    assert evaluate_candidate(candidate()).priority is Priority.LOW


def test_a_signal_event_carries_its_evidence():
    seen = []
    events.subscribe(seen.append)
    evaluate_candidate(candidate(description="We are hiring engineers"))
    signal_events = [e for e in seen if e.type.value == "signal_generated"]
    assert signal_events and signal_events[0].data["evidence"]


# ================================================================== enrichment
def test_an_enricher_can_add_to_enrichment_only():
    register_enricher(lambda record, cand: {"embedding_id": "abc"})
    record = evaluate_candidate(candidate(description="A fabless asic company"))
    assert record.enrichment == {"embedding_id": "abc"}
    assert record.classifications      # deterministic output still present


def test_an_enricher_cannot_change_a_deterministic_conclusion():
    """The forward-compatibility guarantee: AI may add, never overrule."""
    def rogue(record, _cand):
        record.priority = Priority.CRITICAL
        record.priority_score = 1.0
        record.classifications = ()
        return {"note": "tried"}

    register_enricher(rogue)
    record = evaluate_candidate(candidate(company_name="Cafe", description="Coffee."))
    assert record.priority is Priority.LOW and record.priority_score < 1.0
    assert record.enrichment == {"note": "tried"}


def test_a_failing_enricher_is_ignored():
    def broken(_record, _cand):
        raise RuntimeError("model unavailable")

    register_enricher(broken)
    assert evaluate_candidate(candidate(description="fabless asic")).classifications


def test_enrichers_can_be_removed():
    fn = register_enricher(lambda record, cand: {"x": 1})
    unregister_enricher(fn)
    assert evaluate_candidate(candidate()).enrichment == {}


# ========================================================= scheduler integration
def test_the_stage_is_registered_in_the_automatic_pipeline():
    from orchestrator.stages import PIPELINE_ORDER, STAGES

    assert "market_intelligence" in PIPELINE_ORDER
    assert STAGES["market_intelligence"].engine is None      # in-process, no engine
    order = PIPELINE_ORDER.index("market_intelligence")
    assert PIPELINE_ORDER.index("market_discovery") < order < PIPELINE_ORDER.index("scoring")


def test_the_stage_runs_with_no_candidates(session):
    from orchestrator.stages import STAGES

    metrics = STAGES["market_intelligence"].ingest(session)
    assert metrics.status == "success" and metrics.rows_upserted == 0


def test_the_stage_reports_metrics_the_orchestrator_understands(session):
    from orchestrator.stages import STAGES

    _store_candidates(session, 2)
    metrics = STAGES["market_intelligence"].ingest(session)
    assert metrics.rows_in == 2 and metrics.rows_upserted == 2
    assert metrics.status == "success" and "evaluated=2" in metrics.notes


def test_the_scheduler_knows_nothing_about_rules_or_vocabulary():
    import ast
    import inspect
    import textwrap

    from orchestrator import stages

    tree = ast.parse(textwrap.dedent(inspect.getsource(stages.market_intelligence_ingest)))
    fn = tree.body[0]
    if isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant):
        fn.body = fn.body[1:]                      # drop the docstring; keep only code
    body = ast.unparse(fn).lower()
    for name in ("fabless", "asic", "semiconductor", "priority_high", "rule"):
        assert name not in body, f"scheduler must not reference {name}"


def test_the_dashboard_health_strip_includes_the_layer():
    from backend.repositories import PIPELINE_COMPONENTS

    assert "market_intelligence" in PIPELINE_COMPONENTS


# ===================================================================== logging
def test_a_run_logs_what_it_processed(caplog):
    with caplog.at_level("INFO", logger="market_intelligence.pipeline"):
        evaluate_candidate(candidate(description="A fabless asic company"))
    text = caplog.text
    assert "classifications" in text and "technologies" in text and "signals" in text


def test_a_run_logs_its_duration_and_counts(caplog):
    with caplog.at_level("INFO", logger="market_intelligence.pipeline"):
        IntelligencePipeline().run([candidate()], run_id="r9")
    assert "finished in" in caplog.text and "evaluated=" in caplog.text


def test_events_are_logged_structurally(caplog):
    with caplog.at_level("INFO", logger="market_intelligence.events"):
        evaluate_candidate(candidate(description="fabless asic"))
    assert "priority_assigned" in caplog.text


def test_a_rejected_candidate_is_logged_as_a_warning(caplog):
    with caplog.at_level("WARNING", logger="market_intelligence.events"):
        IntelligencePipeline().run([candidate(candidate_key="")])
    assert "candidate_rejected" in caplog.text


# ========================================================= architectural boundary
# Enforced structurally rather than by convention, so a future contributor cannot
# quietly erode the layering.
def test_only_the_persistence_layer_can_write_to_the_database():
    import pathlib

    pkg = pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_intelligence"
    markers = ("session.add", "session.commit", "session.execute", "session.query",
               "session.delete", "session.merge", "session.flush")
    writers = {f.name for f in pkg.rglob("*.py")
               if any(m in f.read_text(encoding="utf-8") for m in markers)}
    assert writers == {"models.py", "service.py"}, f"unexpected DB writers: {writers}"


def test_no_intelligence_module_performs_network_or_ai_calls():
    """Deterministic means offline: no HTTP client, no model, no external service."""
    import ast
    import pathlib

    pkg = pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_intelligence"
    banned = ("requests", "httpx", "urllib.request", "openai", "anthropic",
              "sklearn", "torch", "transformers", "sentence_transformers")
    offenders = {}
    for f in pkg.rglob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            hits = [b for b in banned if any(n.startswith(b) for n in names)]
            if hits:
                offenders.setdefault(f.name, []).extend(hits)
    assert offenders == {}, f"intelligence must stay offline: {offenders}"


def test_the_layer_depends_on_discovery_schemas_only():
    """It consumes candidates; it must not reach into the discovery engine's guts."""
    import ast
    import pathlib

    pkg = pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_intelligence"
    allowed = {"backend.market_discovery.schemas", "backend.market_discovery.models"}
    offenders = {}
    for f in pkg.rglob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                    "backend.market_discovery"):
                if node.module not in allowed:
                    offenders.setdefault(f.name, []).append(node.module)
    assert offenders == {}, f"reaches into the discovery engine: {offenders}"


def test_the_discovery_engine_does_not_depend_on_intelligence():
    """The lower layer must stay unaware of the higher one."""
    import pathlib

    pkg = pathlib.Path(__file__).resolve().parent.parent / "backend" / "market_discovery"
    offenders = [f.name for f in pkg.rglob("*.py")
                 if "market_intelligence" in f.read_text(encoding="utf-8")]
    assert offenders == []


def test_the_pipeline_needs_no_database_session():
    """Proof the pipeline is pure: it interprets candidates with no session at all."""
    record = IntelligencePipeline().evaluate(candidate(description="fabless asic"))
    assert isinstance(record, MarketIntelligence) and record.classifications
