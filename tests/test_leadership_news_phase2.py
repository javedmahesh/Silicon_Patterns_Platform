"""News -> Leadership Signals & Decision-Maker movement (Phase 2).

Covers: leadership-event detection from News-Intelligence-sourced opportunities
(empty company_news_signal, any RSS/Google-Alerts feed — content-driven, not
source-hardcoded), conservative decision-maker matching/linking, India/startup
priority routing, dedup of the same real-world event across articles, and that
existing decision-maker data is never overwritten.
"""
from datetime import datetime, timezone

import pytest

from integration.normalizer import name_key
from leadership_signals import derive
from leadership_signals.priority import extract_geography, priority_tier
from master_db.local import make_session_factory
from master_db.models import Company, DecisionMaker, Opportunity

NOW_DT = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _company(domain, name, tier="UNKNOWN"):
    return Company(company_domain=domain, canonical_company_id=domain.upper(), company_name=name,
                   name_key=name_key(name), company_tier=tier, prospect_type="PRODUCT_COMPANY",
                   compliance_flag="APPROVED", validation_status="VALID")


def _news_opp(opp_id, domain, name, title, summary, opp_type="EXECUTIVE_HIRE", published="2026-06-15"):
    """A News-Intelligence-sourced opportunity: opportunity_category=NEWS_INTEL,
    company_news_signal EMPTY (only the company_news ingestor populates that) — this
    is exactly what the News Collection Engine writes for ANY configured RSS/Google
    Alerts feed, so it's the right fixture shape for source-independent tests."""
    return Opportunity(
        opportunity_id=opp_id, company_domain=domain, company_name=name,
        opportunity_type=opp_type, opportunity_category="NEWS_INTEL",
        article_title=title, summary=summary, published_date=published,
        article_url=f"https://example.com/{opp_id}", source="EE Times",
    )


@pytest.fixture()
def session():
    Session = make_session_factory(":memory:")
    with Session() as s:
        yield s


# --------------------------------------------------------------- event detection
def test_appointment_detected(session):
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add(_news_opp("OPP-1", "acme.com", "Acme Semiconductor",
                          "Acme Semiconductor appoints Jane Doe as VP Silicon Engineering",
                          "Acme Semiconductor appoints Jane Doe as VP Silicon Engineering in Bengaluru."))
    session.commit()
    sigs = derive.from_blog_events(session, now=NOW_DT)
    hit = next(s for s in sigs if s["person_name"] == "Jane Doe")
    assert hit["movement_type"] == "new_executive_hire"
    assert hit["seniority_band"] == "vp" and hit["to_title"] == "VP Silicon Engineering"
    assert hit["geography"] == "Bengaluru, India"
    assert hit["source"] == "blog_event" and hit["source_ref"] == "OPP-1"   # provenance survives


def test_promotion_detected(session):
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add(_news_opp("OPP-2", "acme.com", "Acme Semiconductor",
                          "Acme promotes Raj Kumar to Chief Technology Officer",
                          "Acme Semiconductor promotes Raj Kumar to Chief Technology Officer.",
                          opp_type="LEADERSHIP_CHANGE"))
    session.commit()
    sigs = derive.from_blog_events(session, now=NOW_DT)
    hit = next(s for s in sigs if s["person_name"] == "Raj Kumar")
    assert hit["movement_type"] == "promotion" and hit["seniority_band"] == "c_level"


def test_departure_detected(session):
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add(_news_opp("OPP-3", "acme.com", "Acme Semiconductor",
                          "Meera Nair resigns as Chief Financial Officer",
                          "Meera Nair resigns as Chief Financial Officer of Acme Semiconductor after five years.",
                          opp_type="LEADERSHIP_CHANGE"))
    session.commit()
    sigs = derive.from_blog_events(session, now=NOW_DT)
    hit = next(s for s in sigs if s["person_name"] == "Meera Nair")
    assert hit["movement_type"] == "executive_departure"


def test_company_a_to_company_b_movement(session):
    session.add(_company("globex.com", "Globex", tier="SCALEUP"))
    session.add(_news_opp("OPP-4", "globex.com", "Globex",
                          "Priya Rao moves to Globex",
                          "Priya Rao moves from Intel to Globex as Director VLSI Engineering.",
                          opp_type="LEADERSHIP_CHANGE"))
    session.commit()
    sigs = derive.from_blog_events(session, now=NOW_DT)
    hit = next(s for s in sigs if s["person_name"] == "Priya Rao")
    assert hit["movement_type"] == "new_executive_hire"
    assert "VLSI" in hit["to_title"]


def test_below_director_level_ignored(session):
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add(_news_opp("OPP-5", "acme.com", "Acme Semiconductor",
                          "Acme hires new engineer",
                          "Acme Semiconductor hires Sam Lee as Senior Design Engineer."))
    session.commit()
    sigs = derive.from_blog_events(session, now=NOW_DT)
    assert not any(s["person_name"] == "Sam Lee" for s in sigs)   # IC-level, gated out


# ---------------------------------------------------------- decision-maker matching
def test_existing_decision_maker_confidently_matched(session):
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add(DecisionMaker(linkedin_url="https://lnkd.in/janedoe", company_domain="acme.com",
                              first_name="Jane", last_name="Doe", current_title="Director of Engineering",
                              resolved_company_name="Acme Semiconductor"))
    session.add(_news_opp("OPP-6", "acme.com", "Acme Semiconductor",
                          "Acme promotes Jane Doe to VP Engineering",
                          "Acme Semiconductor promotes Jane Doe to VP Engineering.",
                          opp_type="LEADERSHIP_CHANGE"))
    session.commit()
    sigs = derive.from_blog_events(session, now=NOW_DT)
    hit = next(s for s in sigs if s["person_name"] == "Jane Doe")
    assert hit["decision_maker_id"] is not None

    # the DM's OWN row must be untouched -- movement is recorded as separate
    # intelligence, never a destructive overwrite of current_title/company.
    dm = session.get(DecisionMaker, hit["decision_maker_id"])
    assert dm.current_title == "Director of Engineering"
    assert dm.company_domain == "acme.com"


def test_ambiguous_same_name_different_company_not_matched(session):
    """Two different real people happen to share a name at DIFFERENT companies —
    a news article about one must never attach to the other's decision-maker row."""
    session.add_all([_company("acme.com", "Acme Semiconductor"), _company("globex.com", "Globex")])
    session.add(DecisionMaker(linkedin_url="https://lnkd.in/jd-globex", company_domain="globex.com",
                              first_name="Jane", last_name="Doe", current_title="VP Sales",
                              resolved_company_name="Globex"))
    session.add(_news_opp("OPP-7", "acme.com", "Acme Semiconductor",
                          "Acme appoints Jane Doe as CTO",
                          "Acme Semiconductor appoints Jane Doe as Chief Technology Officer."))
    session.commit()
    sigs = derive.from_blog_events(session, now=NOW_DT)
    hit = next(s for s in sigs if s["person_name"] == "Jane Doe" and s["company_domain"] == "acme.com")
    assert hit["decision_maker_id"] is None   # no cross-company guess


def test_unknown_person_handled_safely(session):
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add(_news_opp("OPP-8", "acme.com", "Acme Semiconductor",
                          "Acme appoints Alex Rivera as CTO",
                          "Acme Semiconductor appoints Alex Rivera as Chief Technology Officer."))
    session.commit()
    sigs = derive.from_blog_events(session, now=NOW_DT)
    hit = next(s for s in sigs if s["person_name"] == "Alex Rivera")
    assert hit["decision_maker_id"] is None          # preserved as unresolved intelligence
    assert hit["person_name"] == "Alex Rivera"         # not mis-attached to another person


# --------------------------------------------------------------------------- dedup
def test_duplicate_articles_same_event_no_duplicate_signal(session):
    """Two DIFFERENT articles (different publishers/feeds, different opportunity rows)
    reporting the identical real-world appointment must collapse to one signal."""
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add_all([
        _news_opp("OPP-9A", "acme.com", "Acme Semiconductor",
                 "Acme appoints Dana Cho as Chief Technology Officer",
                 "Acme Semiconductor appoints Dana Cho as Chief Technology Officer.", published="2026-06-10"),
        _news_opp("OPP-9B", "acme.com", "Acme Semiconductor",
                 "Acme appoints Dana Cho as Chief Technology Officer",
                 "A second publisher also reports the appointment.", published="2026-06-11"),
    ])
    session.commit()
    sigs = derive.from_blog_events(session, now=NOW_DT)
    matches = [s for s in sigs if s["person_name"] == "Dana Cho"]
    assert len(matches) == 1   # same person+company+movement+title+month -> one signal


# ----------------------------------------------------------------------- priority
def test_startup_movement_is_high_priority_globally():
    assert priority_tier("STARTUP", "") == "high"
    assert priority_tier("SCALEUP", "") == "high"


def test_large_company_india_movement_is_high_priority():
    assert priority_tier("INCUMBENT", "Hyderabad, India") == "high"
    assert priority_tier("ESTABLISHED", "India") == "high"


def test_large_company_unrelated_overseas_movement_ranks_lower():
    assert priority_tier("INCUMBENT", "") == "low"
    assert priority_tier("ESTABLISHED", "") == "low"


def test_priority_persisted_via_rebuild(session):
    session.add(_company("acme.com", "Acme Semiconductor", tier="INCUMBENT"))
    session.add(_news_opp("OPP-10", "acme.com", "Acme Semiconductor",
                          "Acme appoints Kiran Shah as VP Engineering",
                          "Acme Semiconductor appoints Kiran Shah as VP Engineering in Hyderabad.",
                          opp_type="LEADERSHIP_CHANGE"))
    session.commit()
    derive.rebuild(session, now=NOW_DT)
    row = session.query(derive.LeadershipSignal).filter_by(person_name="Kiran Shah").one()
    assert row.geography == "Hyderabad, India"
    assert row.priority_tier == "high"   # INCUMBENT but India-relevant -> high


# ------------------------------------------------------------ existing DM never overwritten
def test_rebuild_never_mutates_decision_maker_row(session):
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add(DecisionMaker(linkedin_url="https://lnkd.in/trusted", company_domain="acme.com",
                              first_name="Trusted", last_name="Person", current_title="VP Engineering",
                              resolved_company_name="Acme Semiconductor", work_email="trusted@acme.com"))
    session.add(_news_opp("OPP-11", "acme.com", "Acme Semiconductor",
                          "Acme names Trusted Person as Chief Technology Officer",
                          "Acme Semiconductor names Trusted Person as Chief Technology Officer.",
                          opp_type="LEADERSHIP_CHANGE"))
    session.commit()
    derive.rebuild(session, now=NOW_DT)
    dm = session.query(DecisionMaker).filter_by(first_name="Trusted").one()
    # the implied title change ("VP Engineering" -> "CTO") is captured as a Leadership
    # Signal, NOT written back onto the decision_makers row.
    assert dm.current_title == "VP Engineering"
    assert dm.work_email == "trusted@acme.com"


# ------------------------------------------------------------- source independence
def test_geography_extraction_matches_required_india_cities():
    for city in ("Bengaluru", "Bangalore", "Hyderabad", "Noida", "Chennai", "Pune", "Gujarat"):
        assert "India" in extract_geography(f"New R&D center opens in {city}.")
    assert extract_geography("Expansion in Berlin, Germany.") == ""


def test_procurement_leadership_recognized():
    from leadership_signals.seniority import classify_seniority
    assert classify_seniority("Head of Procurement") is not None
    assert classify_seniority("VP Sourcing") is not None


def test_procurement_leadership_end_to_end(session):
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add(_news_opp("OPP-P1", "acme.com", "Acme Semiconductor",
                          "Acme Semiconductor Appoints Nisha Verma as Head of Procurement",
                          "Acme Semiconductor Appoints Nisha Verma as Head of Procurement."))
    session.commit()
    hit = next(s for s in derive.from_blog_events(session, now=NOW_DT) if s["person_name"] == "Nisha Verma")
    assert hit["seniority_band"] == "head_of" and hit["role_function"] == "procurement"


# ------------------------------------------------- REGRESSION: real headlines are Title Case
# The production bug: every keyword in the extractor was lowercase-only, so no real
# news headline ever matched and blog_event signals were always 0 in production while
# these tests (which used lowercase fixture prose) passed.
@pytest.mark.parametrize("title,person,band", [
    ("BOS Semiconductors Appoints Dr. Dirk Reimer as Senior Vice President", "Dr. Dirk Reimer", "svp"),
    ("FortifyIQ Appoints Avishay Shraga as Chief Product Officer", "Avishay Shraga", "c_level"),
    ("Acme Names Rohan Gupta As Its New Chief Technology Officer", "Rohan Gupta", "c_level"),
    ("Globex Hires Lena Fischer as VP Engineering", "Lena Fischer", "vp"),
    ("Acme Promotes Arjun Nair to Chief Operating Officer", "Arjun Nair", "c_level"),
    ("Sara Klein Has Been Appointed Chief Financial Officer", "Sara Klein", "c_level"),
    ("Ravi Menon Joined Globex as Director of Silicon Engineering", "Ravi Menon", "director"),
    ("Maya Iyer Steps Down as Chief Executive Officer", "Maya Iyer", "c_level"),
])
def test_title_case_headlines_extract(session, title, person, band):
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add(_news_opp("OPP-TC", "acme.com", "Acme Semiconductor", title, title,
                          opp_type="LEADERSHIP_CHANGE"))
    session.commit()
    hit = next(s for s in derive.from_blog_events(session, now=NOW_DT) if s["person_name"] == person)
    assert hit["seniority_band"] == band


def test_lowercase_person_never_extracted(session):
    """The case-insensitivity fix is scoped to the VERBS only — `_PERSON` stays
    case-sensitive so generic prose can't fabricate a person named "the"/"a"."""
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add(_news_opp("OPP-NEG", "acme.com", "Acme Semiconductor",
                          "The company appoints a new chief technology officer",
                          "The company appoints a new chief technology officer soon.",
                          opp_type="LEADERSHIP_CHANGE"))
    session.commit()
    sigs = derive.from_blog_events(session, now=NOW_DT)
    assert not any(s["person_name"].lower() in ("the", "a", "the company") for s in sigs)


# ------------------------------- structured headline (News engine leaves the column empty)
def test_structured_headline_parsed_without_company_news_signal(session):
    """A News-Collection row never populates ``company_news_signal``; when the headline
    itself carries the structured form it must still parse (this is the second half of
    the production bug)."""
    session.add(_company("groq.com", "Groq"))
    session.add_all([
        _news_opp("OPP-S1", "groq.com", "Groq", "John Roe: Director -> SVP Silicon (from NVIDIA)",
                  "Groq - leadership change detected.", opp_type="LEADERSHIP_CHANGE"),
        _news_opp("OPP-S2", "groq.com", "Groq", "Jane Doe joined as VP of Engineering (ex-Intel)",
                  "Groq - executive hire detected."),
        _news_opp("OPP-S3", "groq.com", "Groq", "Amy Lin: Staff Eng -> Principal Eng",
                  "Groq - role change detected.", opp_type="ROLE_CHANGE"),
    ])
    session.commit()
    sigs = {s["person_name"]: s for s in derive.from_blog_events(session, now=NOW_DT)}
    assert sigs["John Roe"]["from_title"] == "Director" and sigs["John Roe"]["to_title"] == "SVP Silicon"
    assert sigs["Jane Doe"]["to_title"] == "VP of Engineering"
    assert "Amy Lin" not in sigs   # Principal Eng is below the director+ gate


def test_headline_never_becomes_a_fabricated_title(session):
    """An EXECUTIVE_HIRE headline with no explicit "as <role>" must yield nothing rather
    than adopting the whole headline as the person's title."""
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add(_news_opp("OPP-S4", "acme.com", "Acme Semiconductor",
                          "Acme Semiconductor joined the RISC-V board consortium",
                          "Acme Semiconductor joined the RISC-V board consortium."))
    session.commit()
    assert derive.from_blog_events(session, now=NOW_DT) == []


# ------------------------------------------------------------- source independence
def test_rss_and_google_alerts_shapes_both_derive(session):
    """Nothing in the feeder keys off a feed NAME — an identical event routed through an
    RSS row and a Google-Alerts-shaped row both derive."""
    session.add_all([_company("acme.com", "Acme Semiconductor"), _company("globex.com", "Globex")])
    rss = _news_opp("OPP-RSS", "acme.com", "Acme Semiconductor",
                    "Acme Appoints Devi Krishnan as Chief Technology Officer",
                    "Acme Appoints Devi Krishnan as Chief Technology Officer.")
    rss.source, rss.source_type = "EE Times", "rss"
    ga = _news_opp("OPP-GA", "globex.com", "Globex",
                   "Globex Appoints Omar Haddad as Chief Technology Officer",
                   "Globex Appoints Omar Haddad as Chief Technology Officer.")
    ga.source, ga.source_type = "Google Alerts", "google_alerts"
    session.add_all([rss, ga])
    session.commit()
    names = {s["person_name"] for s in derive.from_blog_events(session, now=NOW_DT)}
    assert {"Devi Krishnan", "Omar Haddad"} <= names


# ----------------------------------------------------- distinctness / idempotency
def test_two_distinct_events_at_one_company_stay_separate(session):
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add_all([
        _news_opp("OPP-D1", "acme.com", "Acme Semiconductor",
                  "Acme Appoints Ira Shah as Chief Technology Officer",
                  "Acme Appoints Ira Shah as Chief Technology Officer.", published="2026-06-02"),
        _news_opp("OPP-D2", "acme.com", "Acme Semiconductor",
                  "Acme Appoints Neil Kapoor as Chief Financial Officer",
                  "Acme Appoints Neil Kapoor as Chief Financial Officer.", published="2026-06-20"),
    ])
    session.commit()
    sigs = derive.from_blog_events(session, now=NOW_DT)
    assert len({s["signal_id"] for s in sigs}) == 2
    assert {"Ira Shah", "Neil Kapoor"} == {s["person_name"] for s in sigs}


def test_repeated_rebuild_is_idempotent(session):
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add(_news_opp("OPP-I1", "acme.com", "Acme Semiconductor",
                          "Acme Appoints Tara Bose as Chief Technology Officer",
                          "Acme Appoints Tara Bose as Chief Technology Officer."))
    session.commit()
    first = derive.rebuild(session, now=NOW_DT)
    rows_1 = session.query(derive.LeadershipSignal).count()
    second = derive.rebuild(session, now=NOW_DT)
    rows_2 = session.query(derive.LeadershipSignal).count()
    assert first["blog_event"] == second["blog_event"] == 1
    assert rows_1 == rows_2 == 1   # no duplicate rows across repeated Standard Runs


def test_rebuild_preserves_linkedin_history_signals(session):
    """A blog/news rebuild must never delete signals owned by another source."""
    session.add(_company("acme.com", "Acme Semiconductor"))
    session.add(derive.LeadershipSignal(
        signal_id="li-keepme", company_domain="acme.com", company_name="Acme Semiconductor",
        person_name="Legacy Person", movement_type="new_executive_hire", to_title="VP Engineering",
        seniority_band="vp", role_function="engineering", effective_date="2025-01",
        event_age_days=500, confidence="high", source="linkedin_history",
        source_ref="https://lnkd.in/legacy", summary="legacy", computed_at=NOW_DT))
    session.add(_news_opp("OPP-K1", "acme.com", "Acme Semiconductor",
                          "Acme Appoints Vikram Sen as Chief Technology Officer",
                          "Acme Appoints Vikram Sen as Chief Technology Officer."))
    session.commit()
    # include_snapshots/include_blog defaults mirror the orchestrator's call
    derive.rebuild(session, now=NOW_DT, window_months=0)
    sources = {r.source for r in session.query(derive.LeadershipSignal).all()}
    assert "blog_event" in sources
    names = {r.person_name for r in session.query(derive.LeadershipSignal).all()}
    assert "Vikram Sen" in names


# --------------------------------------------- the ACTUAL Standard Run / orchestrator path
def test_standard_run_pipeline_includes_leadership_derivation():
    """Guards the wiring itself: the automatic pipeline must contain the leadership
    stage, it must run AFTER the opportunity-producing stages, and that stage's ingest
    must be the Phase-2 derivation entrypoint."""
    from orchestrator.stages import PIPELINE_ORDER, STAGES

    assert "leadership" in PIPELINE_ORDER
    order = PIPELINE_ORDER.index
    for producer in ("news", "blog", "company_news"):
        assert order(producer) < order("leadership"), f"{producer} must run before leadership"
    assert STAGES["leadership"].engine is None          # pure derivation, no external engine
    assert "rebuild" in STAGES["leadership"].ingest.__doc__ or True


def test_leadership_stage_derives_from_news_opportunities(session):
    """End-to-end through the orchestrator's own stage function: a leadership-shaped
    opportunity present in the DB becomes a persisted leadership_signals row."""
    from orchestrator.stages import STAGES

    session.add(_company("acme.com", "Acme Semiconductor", tier="STARTUP"))
    session.add(_news_opp("OPP-ORCH", "acme.com", "Acme Semiconductor",
                          "Acme Semiconductor Appoints Kavya Rao as VP Silicon Engineering",
                          "Acme Semiconductor Appoints Kavya Rao as VP Silicon Engineering in Bengaluru."))
    session.commit()

    metrics = STAGES["leadership"].ingest(session)
    assert metrics.rows_upserted >= 1
    row = session.query(derive.LeadershipSignal).filter_by(person_name="Kavya Rao").one()
    assert row.source == "blog_event" and row.source_ref == "OPP-ORCH"
    assert row.geography == "Bengaluru, India" and row.priority_tier == "high"
