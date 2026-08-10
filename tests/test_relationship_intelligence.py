"""Phase 3 — relationship intelligence: relationship strength, next best contact/
action, follow-up engine, contact risk, smart alerts, opportunity intelligence and
the relationship graph. Deterministic, no LLM."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import (
    Base,
    Company,
    DecisionMaker,
    DemandSignal,
    LeadScore,
    LeadershipSignal,
    Opportunity,
    OutreachActivity,
    OutreachLead,
    OutreachMessage,
)

MEMBER = {"X-Dev-Role": "member"}
MANAGER = {"X-Dev-Role": "manager"}
NOW = datetime.now(timezone.utc)


def _dm(s, lurl, title, **kw):
    dm = DecisionMaker(linkedin_url=lurl, company_domain="acme.com", current_title=title, **kw)
    s.add(dm)
    return dm


def _seed(s):
    s.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                  name_key="acme", prospect_type="PRODUCT_COMPANY", validation_status="VALID",
                  company_tier="INCUMBENT", discovery_date="2025-02-01"))
    s.flush()
    cto = _dm(s, "https://l/cto", "Chief Technology Officer", first_name="Carol", last_name="Vance",
              seniority="senior", work_email="carol@acme.com", email_status="verified",
              work_phone="+1-555-0100")
    vpe = _dm(s, "https://l/vpe", "VP Engineering", first_name="Vic", last_name="Park", seniority="senior",
              work_email="vic@acme.com", email_status="verified")
    _dm(s, "https://l/dv", "Director of Verification", first_name="Dee", last_name="Ray", seniority="senior",
        work_email="dee@acme.com", email_status="verified")
    _dm(s, "https://l/ic", "Verification Engineer", first_name="Ike", last_name="Coe")
    dep = _dm(s, "https://l/ops", "VP Operations", first_name="Otto", last_name="Vee", seniority="senior",
              work_email="otto@acme.com", email_status="verified")
    s.add(LeadScore(company_domain="acme.com", lead_score=86.0, grade="A", priority_rank=1))
    s.add(DemandSignal(company_domain="acme.com", total_engineering_jobs=14,
                       normalized_demand_score=70.0, hiring_trend="up", primary_focus="ASIC",
                       newest_job_date="2026-05-01"))
    s.add(Opportunity(opportunity_id="op-hire", company_domain="acme.com", opportunity_type="hiring_surge",
                      article_title="Acme expands ASIC team", effective_opportunity_score=80,
                      published_date="2026-04-10"))
    s.add(Opportunity(opportunity_id="op-ldr", company_domain="acme.com", opportunity_type="leadership_change",
                      article_title="Acme names new CTO", effective_opportunity_score=75,
                      published_date="2026-03-01"))
    s.flush()
    s.add(LeadershipSignal(signal_id="sig-promo", company_domain="acme.com", decision_maker_id=cto.id,
                           person_name="Carol Vance", movement_type="promotion", seniority_band="c_level",
                           source="linkedin_history", confidence="high", to_title="Chief Technology Officer",
                           effective_date="2026-03"))
    s.add(LeadershipSignal(signal_id="sig-join", company_domain="acme.com", person_name="New VP",
                           movement_type="new_executive_hire", seniority_band="vp",
                           source="linkedin_history", confidence="medium", to_title="VP Silicon"))
    s.add(LeadershipSignal(signal_id="sig-dep", company_domain="acme.com", decision_maker_id=dep.id,
                           person_name="Otto Vee", movement_type="executive_departure", seniority_band="vp",
                           source="linkedin_history", confidence="low", effective_date="2026-02"))
    # outreach: CTO engaged (sent + reply now); VP Eng sent 10d ago, no reply (overdue Follow Up)
    lead = OutreachLead(company_domain="acme.com", stage="meeting_scheduled", last_activity_at=NOW)
    s.add(lead)
    s.flush()
    s.add(OutreachMessage(outreach_lead_id=lead.id, decision_maker_id=cto.id, direction="outbound",
                          status="sent", to_email="carol@acme.com", subject="Intro", body="Hi", sent_at=NOW))
    s.add(OutreachMessage(outreach_lead_id=lead.id, decision_maker_id=cto.id, direction="inbound",
                          status="replied", from_email="carol@acme.com", subject="Re", body="Yes", sent_at=NOW))
    s.add(OutreachMessage(outreach_lead_id=lead.id, decision_maker_id=vpe.id, direction="outbound",
                          status="sent", to_email="vic@acme.com", subject="Hello", body="Hi",
                          sent_at=NOW - timedelta(days=10)))
    s.add(OutreachActivity(outreach_lead_id=lead.id, type="sent", detail="Sent"))
    s.add(OutreachActivity(outreach_lead_id=lead.id, type="reply_received", detail="Reply"))
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'reli.db').as_posix()}",
                              log_json=False, dev_auth_bypass=True))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _rel(client):
    r = client.get("/decision-makers/company/acme.com/relationships", headers=MEMBER)
    assert r.status_code == 200
    return r.json()


def _by_title(nbc, title):
    return next(c for c in nbc if c["contact"]["title"] == title)


def test_relationship_strength_and_next_action(client):
    nbc = _rel(client)["next_best_contacts"]
    cto = _by_title(nbc, "Chief Technology Officer")
    assert cto["relationship_status"] in ("Engaged", "Active", "Strategic")
    assert cto["relationship_score"] > 0
    # VP Eng: sent, no reply, overdue → Follow Up
    vpe = _by_title(nbc, "VP Engineering")
    assert vpe["next_action"]["action"] == "Follow Up"
    assert vpe["follow_up"]["overdue"] is True
    # Director Verification: reachable, no outreach → Send Introduction (Cold)
    dv = _by_title(nbc, "Director of Verification")
    assert dv["relationship_status"] == "Cold"
    assert dv["next_action"]["action"] == "Send Introduction"


def test_departed_contact_recommends_alternate(client):
    nbc = _rel(client)["next_best_contacts"]
    dep = _by_title(nbc, "VP Operations")
    assert dep["next_action"]["action"] == "Contact Alternate Decision Maker"
    assert dep["risk_severity"] == "high" and "Left company" in dep["risk_flags"]


def test_next_best_contact_priority(client):
    nbc = _rel(client)["next_best_contacts"]
    assert all(c["priority"] in ("Contact Now", "Contact This Week", "Monitor", "Low Priority") for c in nbc)
    # sorted by score desc
    scores = [c["score"] for c in nbc]
    assert scores == sorted(scores, reverse=True)


def test_follow_up_engine(client):
    fu = _rel(client)["follow_ups"]
    assert any(c["contact"]["title"] == "VP Engineering" for c in fu)
    vpe = _by_title(fu, "VP Engineering")
    assert vpe["follow_up"]["overdue"] and vpe["follow_up"]["days_since_last_contact"] >= 7


def test_contact_risk_severity(client):
    nbc = _rel(client)["next_best_contacts"]
    ic = _by_title(nbc, "Verification Engineer")
    assert ic["risk_severity"] in ("high", "medium")     # missing email → high
    assert "Missing email" in ic["risk_flags"]


def test_opportunity_intelligence(client):
    oi = {o["opportunity_id"]: o for o in _rel(client)["opportunity_intelligence"]}
    assert oi["op-ldr"]["best_department"] == "Executive"
    assert oi["op-hire"]["best"] is not None
    assert oi["op-hire"]["suggested_action"] is not None
    assert isinstance(oi["op-hire"]["backups"], list)


def test_company_alerts(client):
    types = {a["type"] for a in _rel(client)["alerts"]}
    assert "executive_departed" in types
    assert "new_opportunity" in types
    assert "hiring_spike" in types
    assert {"promotion", "executive_joined"} & types


def test_relationship_graph(client):
    g = _rel(client)["graph"]
    kinds = {n["kind"] for n in g["nodes"]}
    assert {"company", "department", "contact"} <= kinds
    assert any(n["kind"] == "contact" and n["dm_id"] for n in g["nodes"])
    assert len(g["edges"]) > 0
    # every edge references existing nodes
    ids = {n["id"] for n in g["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in g["edges"])


def test_dm_detail_has_relationship(client):
    items = client.get("/decision-makers", headers=MEMBER).json()["items"]
    cto_id = next(d["id"] for d in items if d["current_title"] == "Chief Technology Officer")
    d = client.get(f"/decision-makers/{cto_id}", headers=MEMBER).json()
    assert d["relationship_status"] in ("Engaged", "Active", "Strategic")
    assert d["next_action"] is not None and d["follow_up"] is not None


def test_outreach_contacts_have_relationship(client):
    leads = client.get("/outreach/leads", headers=MANAGER).json()["items"]
    lead_id = next(l["id"] for l in leads if l["company_domain"] == "acme.com")
    contacts = client.get(f"/outreach/leads/{lead_id}", headers=MANAGER).json()["contacts"]
    cto = next(c for c in contacts if c["title"] == "Chief Technology Officer")
    assert cto["relationship_status"] in ("Engaged", "Active", "Strategic")
    assert cto["next_action"]


def test_global_alerts(client):
    alerts = client.get("/alerts", headers=MEMBER).json()
    types = {a["type"] for a in alerts}
    assert types & {"executive_departed", "new_opportunity", "promotion", "executive_joined"}


# ------------------------------------------------- alert -> opportunity handover
# A Smart Alert is an entry point into Opportunities, so it has to carry an
# identifier the Opportunities page can act on. A headline is a label, not a key.
def test_an_opportunity_alert_carries_its_opportunity_id(client):
    alerts = client.get("/alerts", headers=MEMBER).json()
    opp_alerts = [a for a in alerts if a["type"] == "new_opportunity"]
    assert opp_alerts, "expected at least one opportunity-derived alert"
    assert all(a["opportunity_id"] for a in opp_alerts)


def test_company_scoped_opportunity_alerts_carry_their_id(client):
    alerts = _rel(client)["alerts"]
    opp_alerts = [a for a in alerts if a["type"] == "new_opportunity"]
    assert opp_alerts and all(a["opportunity_id"] for a in opp_alerts)


def test_an_opportunity_alert_id_resolves_to_a_real_opportunity(client):
    """The handover is only useful if the id opens something."""
    alerts = client.get("/alerts", headers=MEMBER).json()
    oid = next(a["opportunity_id"] for a in alerts if a["type"] == "new_opportunity")
    assert client.get(f"/opportunities/{oid}", headers=MEMBER).status_code == 200


def test_non_opportunity_alerts_leave_the_id_empty(client):
    """Leadership moves and contact changes have no single opportunity behind them —
    the field stays null rather than pointing somewhere arbitrary."""
    alerts = client.get("/alerts", headers=MEMBER).json()
    others = [a for a in alerts if a["type"] != "new_opportunity"]
    assert others and all(a["opportunity_id"] is None for a in others)


def test_every_alert_can_be_routed(client):
    """Alerts without an opportunity still carry the company, which is what the
    Opportunities page filters on."""
    alerts = client.get("/alerts", headers=MEMBER).json()
    assert alerts
    assert all(a["opportunity_id"] or a["company_domain"] for a in alerts)


def test_opportunities_can_be_filtered_by_the_company_an_alert_names(client):
    """The destination filter an alert relies on."""
    alerts = client.get("/alerts", headers=MEMBER).json()
    domain = next(a["company_domain"] for a in alerts if a["company_domain"])
    page = client.get("/opportunities", headers=MEMBER,
                      params={"company_domain": domain, "signal_category": "ALL"}).json()
    assert all(o["company_domain"] == domain for o in page["items"])


def test_relationships_404(client):
    assert client.get("/decision-makers/company/nope.com/relationships", headers=MEMBER).status_code == 404


# =============================================== Smart Alert freshness semantics
# Production showed 2024-2025 leadership events at the top of "Smart alerts". The
# leadership stage re-derives every signal on each run, so `computed_at` was today
# for ALL of them - selecting or ordering on it dated old events to now. These pin
# the event date as the only thing that decides freshness.
from sqlalchemy import select as _select   # noqa: E402
from sqlalchemy.orm import Session as _Session   # noqa: E402

from backend import relationship_intelligence as _reli   # noqa: E402
from master_db.local import make_session_factory   # noqa: E402


def _alerts_session():
    """A bare session - smart_alerts() needs no app, and the app fixture is slow."""
    return make_session_factory(":memory:")()


def _co(s: _Session, domain: str, name: str) -> None:
    s.add(Company(company_domain=domain, canonical_company_id=domain.upper(),
                  company_name=name, name_key=name.lower(), prospect_type="PRODUCT_COMPANY",
                  validation_status="VALID", company_tier="INCUMBENT",
                  discovery_date="2025-01-01"))


def _sig(s: _Session, sid: str, domain: str, *, effective: str, age_days: int,
         computed: datetime, movement: str = "new_executive_hire", title: str = "CTO") -> None:
    s.add(LeadershipSignal(signal_id=sid, company_domain=domain, company_name=domain,
                           person_name="P" + sid, movement_type=movement,
                           seniority_band="c_level", to_title=title, effective_date=effective,
                           event_age_days=age_days, confidence="high", computed_at=computed))


def test_an_old_event_recomputed_today_is_not_a_current_alert():
    """Case A: event 2024-06, row recomputed now. It must still read as 2024."""
    with _alerts_session() as s:
        _co(s, "old.com", "Oldco")
        _sig(s, "old-1", "old.com", effective="2024-06", age_days=800, computed=NOW)
        s.commit()
        alert = next(a for a in _reli.smart_alerts(s) if a.company_domain == "old.com")
    assert alert.at.startswith("2024-06")
    assert str(NOW.year) not in alert.at          # never stamped with the recompute date


def test_a_new_event_outranks_an_old_one_recomputed_at_the_same_moment():
    """Case B: identical computed_at, different event dates - the event decides."""
    with _alerts_session() as s:
        _co(s, "old.com", "Oldco")
        _co(s, "new.com", "Newco")
        _sig(s, "old-1", "old.com", effective="2024-06", age_days=800, computed=NOW)
        _sig(s, "new-1", "new.com", effective="2026-08", age_days=1, computed=NOW)
        s.commit()
        order = [a.company_domain for a in _reli.smart_alerts(s)]
    assert order.index("new.com") < order.index("old.com")


def test_recomputation_alone_does_not_reorder_the_feed():
    """The whole defect in one assertion: touching computed_at changes nothing."""
    with _alerts_session() as s:
        _co(s, "old.com", "Oldco")
        _co(s, "new.com", "Newco")
        _sig(s, "old-1", "old.com", effective="2024-06", age_days=800,
             computed=NOW - timedelta(days=400))
        _sig(s, "new-1", "new.com", effective="2026-08", age_days=1,
             computed=NOW - timedelta(days=400))
        s.commit()
        before = [(a.company_domain, a.at) for a in _reli.smart_alerts(s)]

        # The leadership stage re-derives everything; only computed_at moves.
        for sig in s.scalars(_select(LeadershipSignal)):
            sig.computed_at = NOW
        s.commit()
        after = [(a.company_domain, a.at) for a in _reli.smart_alerts(s)]
    assert before == after


def test_an_undated_event_is_still_shown_just_not_first():
    """Case C: no effective_date. It must not vanish, and must not claim to be new."""
    with _alerts_session() as s:
        _co(s, "old.com", "Oldco")
        _co(s, "nodate.com", "Nodate")
        _sig(s, "new-1", "old.com", effective="2026-08", age_days=1, computed=NOW)
        _sig(s, "und-1", "nodate.com", effective="", age_days=-1, computed=NOW)
        s.commit()
        alerts = _reli.smart_alerts(s)
    domains = [a.company_domain for a in alerts]
    assert "nodate.com" in domains                      # present
    assert domains.index("old.com") < domains.index("nodate.com")
    assert next(a for a in alerts if a.company_domain == "nodate.com").at == ""


def test_opportunity_freshness_uses_the_published_date():
    with _alerts_session() as s:
        _co(s, "a.com", "Aco")
        s.add(Opportunity(opportunity_id="op-old", company_domain="a.com", company_name="Aco",
                          opportunity_type="FUNDING", article_title="Old news",
                          published_date="2024-01-05", ingested_at=NOW))
        s.add(Opportunity(opportunity_id="op-new", company_domain="a.com", company_name="Aco",
                          opportunity_type="FUNDING", article_title="Fresh news",
                          published_date="2026-08-09", ingested_at=NOW - timedelta(days=400)))
        s.commit()
        order = [a.opportunity_id for a in _reli.smart_alerts(s) if a.opportunity_id]
    assert order.index("op-new") < order.index("op-old")


def test_severity_breaks_ties_between_events_of_the_same_date():
    with _alerts_session() as s:
        _co(s, "a.com", "Aco")
        _sig(s, "hire", "a.com", effective="2026-08", age_days=1, computed=NOW,
             movement="new_executive_hire")
        s.add(Opportunity(opportunity_id="op-1", company_domain="a.com", company_name="Aco",
                          opportunity_type="FUNDING", article_title="Same-day news",
                          published_date="2026-08-01", ingested_at=NOW))
        s.commit()
        alerts = _reli.smart_alerts(s)
    assert alerts[0].severity == "high"          # the executive hire, not the news item


def test_a_recomputed_duplicate_does_not_take_two_slots():
    """A re-derived signal that lands under a new id must not double up."""
    with _alerts_session() as s:
        _co(s, "a.com", "Aco")
        _sig(s, "sig-v1", "a.com", effective="2026-07", age_days=30, computed=NOW)
        _sig(s, "sig-v2", "a.com", effective="2026-08", age_days=1, computed=NOW)
        s.commit()
        alerts = _reli.smart_alerts(s)
    assert len(alerts) == 1 and alerts[0].at.startswith("2026-08")   # newest kept


def test_the_alert_limit_is_respected():
    with _alerts_session() as s:
        _co(s, "a.com", "Aco")
        for i in range(30):
            s.add(Opportunity(opportunity_id="op-%d" % i, company_domain="a.com",
                              company_name="Aco", opportunity_type="FUNDING",
                              article_title="Story %d" % i,
                              published_date="2026-07-%02d" % (i % 28 + 1),
                              ingested_at=NOW))
        s.commit()
        assert len(_reli.smart_alerts(s, limit=5)) == 5


@pytest.mark.parametrize("value,expected", [
    ("2024-06", (2024, 6, 1)),
    ("2026-08-09", (2026, 8, 9)),
    ("2026/08/09", (2026, 8, 9)),
    ("", (0, 0, 0)),
    ("not a date", (0, 0, 0)),
    (None, (0, 0, 0)),
    (datetime(2025, 3, 4, tzinfo=timezone.utc), (2025, 3, 4)),
])
def test_event_key_parses_every_shape_a_date_arrives_in(value, expected):
    assert _reli._event_key(value) == expected


def test_company_alerts_never_date_an_event_by_its_recomputation(client):
    """The company-scoped path had the same computed_at fallback."""
    alerts = _rel(client)["alerts"]
    moves = [a for a in alerts if a["type"] in
             ("executive_joined", "executive_departed", "promotion", "leadership_change")]
    assert moves
    for a in moves:
        assert a["at"] == "" or len(a["at"]) <= 10   # a YYYY-MM event date, not a timestamp
