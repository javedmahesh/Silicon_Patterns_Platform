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
