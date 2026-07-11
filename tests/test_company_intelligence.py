"""Phase 2.5 — company intelligence bundle: buying-committee + department coverage,
contact completeness, engagement score, contact risk, relationship heatmap,
opportunity alignment, and the unified timeline. Deterministic, no LLM."""
from datetime import datetime, timezone

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


def _dm(s, lurl, title, **kw):
    dm = DecisionMaker(linkedin_url=lurl, company_domain="acme.com", current_title=title, **kw)
    s.add(dm)
    return dm


def _seed(s):
    s.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                  name_key="acme", prospect_type="PRODUCT_COMPANY", validation_status="VALID",
                  company_tier="INCUMBENT", discovery_date="2025-01-15"))
    s.flush()
    cto = _dm(s, "https://l/cto", "Chief Technology Officer", first_name="Carol", last_name="Vance",
              seniority="senior", work_email="carol@acme.com", email_status="verified",
              work_phone="+1-555-0100")
    _dm(s, "https://l/ceo", "Chief Executive Officer", first_name="Cara", last_name="Ng", seniority="senior",
        work_email="cara@acme.com", email_status="verified")
    _dm(s, "https://l/vpe", "VP Engineering", first_name="Vic", last_name="Park", seniority="senior",
        work_email="vic@acme.com", email_status="verified")
    _dm(s, "https://l/dv", "Director of Verification", first_name="Dee", last_name="Ray", seniority="senior",
        work_email="dee@acme.com", email_status="verified")
    _dm(s, "https://l/dft", "Director of DFT", first_name="Dan", last_name="Fox", seniority="senior")
    # an IC with no contact details (drives completeness + risk)
    _dm(s, "https://l/ic", "Verification Engineer", first_name="Ike", last_name="Coe")
    _dm(s, "https://l/rec", "Technical Recruiter", first_name="Rae", last_name="Lin",
        work_email="rae@acme.com", email_status="verified")
    _dm(s, "https://l/proc", "Procurement Manager", first_name="Pat", last_name="Ito")
    s.add(LeadScore(company_domain="acme.com", lead_score=86.0, grade="A", priority_rank=1))
    s.add(DemandSignal(company_domain="acme.com", total_engineering_jobs=15,
                       normalized_demand_score=72.0, primary_focus="ASIC", newest_job_date="2026-05-01"))
    s.add(Opportunity(opportunity_id="op-hire", company_domain="acme.com",
                      opportunity_type="hiring_surge", article_title="Acme expands ASIC team",
                      effective_opportunity_score=80, published_date="2026-04-10"))
    s.add(Opportunity(opportunity_id="op-ldr", company_domain="acme.com",
                      opportunity_type="leadership_change", article_title="Acme names new CTO",
                      effective_opportunity_score=75, published_date="2026-03-01"))
    s.flush()
    s.add(LeadershipSignal(signal_id="sig-promo", company_domain="acme.com", decision_maker_id=cto.id,
                           person_name="Carol Vance", movement_type="promotion", seniority_band="c_level",
                           source="linkedin_history", confidence="high", to_title="Chief Technology Officer",
                           effective_date="2026-03"))
    s.add(LeadershipSignal(signal_id="sig-dep", company_domain="acme.com", person_name="Old VP",
                           movement_type="executive_departure", seniority_band="vp",
                           source="linkedin_history", confidence="low", effective_date="2026-02"))
    # outreach engagement: a meeting-stage lead with a sent message + a reply + a note
    lead = OutreachLead(company_domain="acme.com", stage="meeting_scheduled",
                        last_activity_at=datetime.now(timezone.utc))
    s.add(lead)
    s.flush()
    s.add(OutreachMessage(outreach_lead_id=lead.id, direction="outbound", status="sent",
                          to_email="carol@acme.com", subject="Intro", body="Hi"))
    s.add(OutreachMessage(outreach_lead_id=lead.id, direction="inbound", status="replied",
                          from_email="carol@acme.com", subject="Re: Intro", body="Let's talk"))
    s.add(OutreachActivity(outreach_lead_id=lead.id, type="sent", detail="Sent intro"))
    s.add(OutreachActivity(outreach_lead_id=lead.id, type="reply_received", detail="Reply"))
    s.add(OutreachActivity(outreach_lead_id=lead.id, type="note_added", detail="Warm lead"))
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'cintel.db').as_posix()}",
                              log_json=False, dev_auth_bypass=True))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _intel(client):
    r = client.get("/decision-makers/company/acme.com/intelligence", headers=MEMBER)
    assert r.status_code == 200
    return r.json()


def test_buying_committee_coverage(client):
    bc = _intel(client)["buying_committee"]
    present = {r["role"]: r for r in bc["roles"] if r["present"]}
    assert "CEO" in present and "CTO" in present
    assert "Director Verification" in present and "Director DFT" in present
    assert "Procurement" in present and "Recruiting" in present
    assert present["CTO"]["contact"]["influence_score"] is not None
    assert 0 < bc["coverage_pct"] <= 100 and bc["total"] == 12


def test_department_coverage(client):
    dc = _intel(client)["department_coverage"]
    rows = {r["department"]: r for r in dc["rows"]}
    assert rows["Executive"]["present"] and rows["Verification"]["present"] and rows["DFT"]["present"]
    assert "Sales" in dc["missing"]            # no sales contact seeded
    assert dc["coverage_pct"] > 0 and dc["total"] == len(dc["rows"])


def test_contact_completeness(client):
    cc = _intel(client)["contact_completeness"]
    assert cc["total_contacts"] == 8
    assert cc["missing_email"] >= 1            # IC + procurement have none
    assert 0 <= cc["verified_email_pct"] <= 100
    assert cc["avg_influence"] > 0 and cc["avg_confidence"] > 0


def test_engagement_score(client):
    eng = _intel(client)["engagement"]
    assert eng["score"] >= 35                   # replies + meeting + sent + recent
    assert eng["label"] in ("Healthy", "Warm")
    assert eng["relationship"] in ("Active", "Strategic", "Engaged")
    assert eng["factors"]


def test_contact_risk(client):
    risk = _intel(client)["contact_risk"]
    assert risk["missing_email"] >= 1 and risk["missing_phone"] >= 1
    assert risk["leadership_departures"] == 1    # the executive_departure signal
    assert any("Missing email" in it["risks"] for it in risk["items"])


def test_relationship_heatmap(client):
    heat = {r["department"]: r for r in _intel(client)["relationship_heatmap"]}
    assert set(heat) == {"Executive", "Engineering", "Verification", "RTL", "DFT", "Sales", "Recruiting"}
    assert heat["Sales"]["status"] == "Missing"
    assert heat["Verification"]["status"] in ("Strong", "Moderate", "Weak")
    assert heat["RTL"]["status"] == "Missing"    # no RTL contact


def test_opportunity_alignment(client):
    align = {a["opportunity_id"]: a for a in _intel(client)["opportunity_alignment"]}
    assert len(align) == 2
    assert align["op-ldr"]["best_department"] == "Executive"
    assert align["op-hire"]["contact"] is not None
    assert align["op-hire"]["reason"]


def test_timeline(client):
    tl = _intel(client)["timeline"]
    kinds = {e["kind"] for e in tl}
    assert "discovery" in kinds
    assert any(k.startswith("outreach_") for k in kinds)
    assert "leadership" in kinds and "decision_makers" in kinds
    # newest-first ordering (dated events are non-increasing)
    dated = [e["at"] for e in tl if e["at"]]
    assert dated == sorted(dated, reverse=True)


def test_intelligence_404(client):
    assert client.get("/decision-makers/company/nope.com/intelligence", headers=MEMBER).status_code == 404
