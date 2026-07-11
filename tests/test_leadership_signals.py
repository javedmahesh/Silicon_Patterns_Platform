"""Leadership-signals (P-task 8): the director+ gate, the LinkedIn-history
classifier, the blog-event feeder, and the API surface."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from integration.normalizer import name_key
from leadership_signals import derive
from leadership_signals.seniority import classify_seniority, rank
from master_db.models import Base, Company, DecisionMaker, Opportunity

NOW = (2026, 6)
NOW_DT = datetime(2026, 6, 1, tzinfo=timezone.utc)


# ----------------------------------------------------------------- the gate
def test_gate_includes_director_plus():
    cases = {
        "Director of Engineering": "director",
        "Senior Director, Silicon": "senior_director",
        "VP Engineering": "vp",
        "SVP Worldwide Sales": "svp",
        "EVP, Operations": "evp",
        "Chief Technology Officer": "c_level",
        "CEO": "c_level",
        "Co-Founder": "founder",
        "Managing Director": "managing_director",
        "President": "president",
        "Head of Product": "head_of",
    }
    for title, band in cases.items():
        got = classify_seniority(title)
        assert got is not None and got[0] == band, (title, got)


def test_gate_excludes_managers_and_ics():
    for title in ["Engineering Manager", "Senior Manager", "Staff Engineer", "Principal Engineer",
                  "Software Engineer", "Associate Director", "IC Design Verification Engineer",
                  "Field Application Engineer", "Head of People", "", None]:
        assert classify_seniority(title) is None, title


def test_rank_orders_seniority():
    assert rank("vp") > rank("director")
    assert rank("c_level") > rank("vp") > rank("senior_director")


# -------------------------------------------------- LinkedIn-history classifier
def _pos(title, company, start, end=None, present=True):
    return {"title": title, "company": company, "start": start, "end": end, "present": present}


def _types(positions):
    person = {"linkedin_url": "https://lnkd.in/x", "person_name": "Jordan Lee", "dm_id": None}
    resolve = lambda name: "acme.com" if name else None  # noqa: E731
    sigs = derive.signals_from_person(person, positions, resolve, NOW, 24)
    return {s["movement_type"] for s in sigs}


def test_promotion_is_not_a_departure():
    # Internal promotion: the prior role ended, but the person did NOT leave.
    types = _types([
        _pos("VP Engineering", "Acme", (2025, 6)),
        _pos("Director of Engineering", "Acme", (2022, 1), end=(2025, 6), present=False),
    ])
    assert "promotion" in types and "executive_departure" not in types


def test_role_change_lateral():
    assert "role_change" in _types([
        _pos("VP Product", "Acme", (2025, 3)),
        _pos("VP Engineering", "Acme", (2023, 1), end=(2025, 3), present=False),
    ])


def test_new_hire_departure_founder_board():
    assert _types([_pos("Chief Technology Officer", "Acme", (2025, 9))]) == {"new_executive_hire"}
    assert _types([_pos("SVP Sales", "OldCo", (2020, 1), end=(2025, 9), present=False)]) == {"executive_departure"}
    assert _types([_pos("Co-Founder", "Acme", (2025, 3))]) == {"founder_change"}
    assert _types([_pos("Board Member", "Acme", (2025, 5))]) == {"board_appointment"}


def test_ic_history_and_stale_moves_yield_nothing():
    assert _types([
        _pos("Senior Design Verification Engineer", "Acme", (2025, 1)),
        _pos("Design Verification Engineer", "Acme", (2021, 1), end=(2025, 1), present=False),
    ]) == set()
    assert _types([_pos("VP Engineering", "Acme", (2019, 1))]) == set()  # outside the 24-month window


# --------------------------------------------------------- blog-event feeder
def test_blog_event_feeder_extracts_director_plus(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'b.db').as_posix()}", log_json=False))
    with TestClient(app):
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(Company(company_domain="nova.com", canonical_company_id="NOVA", company_name="NovaCore",
                          name_key=name_key("NovaCore"), validation_status="VALID"))
            s.flush()
            s.add(Opportunity(
                opportunity_id="OPP-LDR-1", company_domain="nova.com", company_name="NovaCore",
                opportunity_type="Leadership Change", published_date="2026-05-10",
                article_title="NovaCore appoints Jane Doe as Chief Technology Officer",
                summary="NovaCore Semiconductor appoints Jane Doe as new Chief Technology Officer."))
            s.commit()
            sigs = derive.from_blog_events(s, now=NOW_DT)
    assert any(x["movement_type"] == "new_executive_hire" and x["seniority_band"] == "c_level"
               and "Jane Doe" in x["person_name"] and x["source"] == "blog_event" for x in sigs)


# --------------------------------------------------------------------- API
@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'ldr.db').as_posix()}", log_json=False))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme Silicon",
                          name_key=name_key("Acme Silicon"), company_tier="STARTUP",
                          prospect_type="PRODUCT_COMPANY", compliance_flag="APPROVED", validation_status="VALID"))
            s.flush()
            s.add(DecisionMaker(
                linkedin_url="https://lnkd.in/cto", company_domain="acme.com", first_name="Dana",
                last_name="Cho", current_title="Chief Technology Officer", resolved_company_name="Acme Silicon",
                profile_data={"positions": [
                    {"position": "Chief Technology Officer", "companyName": "Acme Silicon",
                     "startDate": {"year": 2025, "month": "Sep"}, "endDate": {"text": "Present"}},
                    {"position": "VP Engineering", "companyName": "PriorCo",
                     "startDate": {"year": 2019, "month": "Jan"}, "endDate": {"year": 2025, "month": "Aug"}},
                ]}))
            s.commit()
            derive.rebuild(s, now=NOW_DT)
        yield c


def test_company_bundle_includes_leadership_signals(client):
    body = client.get("/companies/acme.com").json()
    assert body["counts"]["leadership_signals"] >= 1
    hires = [x for x in body["leadership_signals"] if x["movement_type"] == "new_executive_hire"]
    assert hires and hires[0]["seniority_band"] == "c_level" and hires[0]["company_domain"] == "acme.com"


def test_leadership_signals_list_and_filters(client):
    assert client.get("/leadership-signals").json()["total"] >= 2  # the hire + the prior-company departure
    assert client.get("/leadership-signals", params={"company_domain": "acme.com"}).json()["total"] >= 1
    assert client.get("/leadership-signals", params={"movement_type": "executive_departure"}).json()["total"] >= 1
    assert client.get("/leadership-signals", params={"seniority_band": "c_level"}).json()["total"] >= 1
    assert client.get("/leadership-signals", params={"movement_type": "promotion"}).json()["total"] == 0
