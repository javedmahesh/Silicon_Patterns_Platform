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


def test_relationships_404(client):
    assert client.get("/decision-makers/company/nope.com/relationships", headers=MEMBER).status_code == 404
