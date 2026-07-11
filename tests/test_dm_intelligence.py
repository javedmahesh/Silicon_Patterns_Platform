"""Phase 2 — decision-intelligence engine: influence + confidence scoring,
department classification, org hierarchy, contact recommendations + map, and the
leadership / outreach integration. Deterministic, no LLM."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.dm_intelligence import (
    CompanyContext,
    classify_department,
    compute,
    confidence,
    department_group,
    exec_rank,
    influence,
    rank_contacts,
)
from backend.main import create_app
from master_db.models import (
    Base,
    Company,
    DecisionMaker,
    DemandSignal,
    LeadScore,
    LeadershipSignal,
)

MEMBER = {"X-Dev-Role": "member"}
MANAGER = {"X-Dev-Role": "manager"}


def _dm(**kw) -> DecisionMaker:
    base = dict(linkedin_url="https://l/x", company_domain="acme.com",
                ingested_at=datetime.now(timezone.utc), profile_data={})
    base.update(kw)
    return DecisionMaker(**base)


# --------------------------------------------------------------- department classification
@pytest.mark.parametrize("title,expected", [
    ("Chief Executive Officer", "Executive"),
    ("CFO", "Executive"),
    ("Chief Technology Officer", "Engineering"),
    ("Chief AI Officer", "AI"),
    ("VP, Design Verification", "Verification"),
    ("Senior DFT Engineer", "DFT"),
    ("RTL Design Engineer", "RTL"),
    ("Physical Design Lead", "Physical Design"),
    ("Embedded Software Engineer", "Embedded"),
    ("Machine Learning Engineer", "AI"),
    ("Technical Recruiter", "HR"),
    ("VP of Sales", "Sales"),
    ("Director of Business Development", "Business Development"),
    ("Procurement Manager", "Procurement"),
    ("General Counsel", "Legal"),
    ("Marketing Manager", "Marketing"),
])
def test_department_classification(title, expected):
    assert classify_department(title) == expected


def test_classification_is_deterministic():
    assert classify_department("VP Verification") == classify_department("VP Verification")


def test_department_group_mapping():
    assert department_group("Verification") == "Engineering Leaders"
    assert department_group("Executive") == "Executive"
    assert department_group("HR") == "Recruiting"
    assert department_group("Finance") == "Other"


# ------------------------------------------------------------------------ hierarchy
@pytest.mark.parametrize("title,rank", [
    ("Founder & CEO", 0),
    ("Chief Technology Officer", 1),
    ("SVP Engineering", 2),
    ("VP of ASIC", 3),
    ("Director of DFT", 4),
    ("Engineering Manager", 5),
    ("Verification Engineer", 6),
    ("", 7),
])
def test_exec_rank(title, rank):
    assert exec_rank(title) == rank


# ------------------------------------------------------------------------ influence
def _ctx(**kw) -> CompanyContext:
    base = dict(domain="acme.com", lead_score=80.0, opportunity_score=70,
                hiring_score=60.0, engineering_jobs=5, leadership_total=2,
                leadership_dm_ids=frozenset(), tier="INCUMBENT", offering="engineering")
    base.update(kw)
    return CompanyContext(**base)


def test_influence_in_range_and_deterministic():
    dm = _dm(current_title="VP Verification", seniority="senior")
    a = influence(dm, _ctx())
    b = influence(dm, _ctx())
    assert 0 <= a.normalized <= 100
    assert a.raw == b.raw and a.normalized == b.normalized
    assert a.factors  # non-empty reasoning


def test_influence_orders_executive_above_ic():
    ctx = _ctx()
    cto = influence(_dm(current_title="Chief Technology Officer", seniority="senior"), ctx).normalized
    ic = influence(_dm(current_title="Verification Engineer", seniority=""), ctx).normalized
    assert cto > ic


def test_influence_rewards_company_signals():
    dm = _dm(current_title="Director of ASIC", seniority="senior")
    hot = influence(dm, _ctx(lead_score=95, opportunity_score=90, hiring_score=90)).normalized
    cold = influence(dm, _ctx(lead_score=5, opportunity_score=0, hiring_score=0,
                              engineering_jobs=0, leadership_total=0, tier="STARTUP")).normalized
    assert hot > cold


def test_influence_person_leadership_bonus():
    dm = _dm(current_title="VP Engineering")
    dm.id = 7
    with_sig = influence(dm, _ctx(leadership_dm_ids=frozenset({7}))).normalized
    without = influence(dm, _ctx(leadership_dm_ids=frozenset())).normalized
    assert with_sig >= without


# ------------------------------------------------------------------------ confidence
def test_confidence_high_when_complete():
    dm = _dm(first_name="Ada", last_name="Lin", full_name="Ada Lin",
             current_title="VP Engineering", seniority="senior", city="Austin",
             work_email="ada@acme.com", email_status="verified", work_phone="+1-555-0100",
             linkedin_url="https://l/ada", profile_data={"raw": {"x": 1}, "industry": "Semi"})
    r = confidence(dm)
    assert r.score >= 70 and r.level == "High"


def test_scoring_handles_list_profile_fields():
    """Real Apify rows store list values (e.g. skills); scoring must not crash on them."""
    dm = _dm(current_title="VP Verification",
             profile_data={"skills": ["UVM", "SystemVerilog"], "industry": ["Semiconductors"],
                           "raw": {"x": 1}})
    assert 0 <= confidence(dm).score <= 100
    assert 0 <= influence(dm, _ctx()).normalized <= 100
    assert compute(dm, _ctx()).department == "Verification"


def test_confidence_low_when_sparse():
    dm = _dm(current_title="", seniority="", company_domain=None, linkedin_url="",
             work_email=None, work_phone=None, ingested_at=datetime(2000, 1, 1, tzinfo=timezone.utc))
    r = confidence(dm)
    assert r.level == "Low" and r.score < 40


# ------------------------------------------------------------------------ recommendations
def test_rank_contacts_assigns_primary_secondary_alternate():
    dms = [
        _dm(current_title="Verification Engineer"),
        _dm(current_title="Chief Technology Officer", seniority="senior", work_email="cto@acme.com",
            email_status="verified", linkedin_url="https://l/cto"),
        _dm(current_title="Director of Verification", seniority="senior"),
    ]
    for i, d in enumerate(dms, start=1):
        d.id = i
    ranked = rank_contacts(dms, _ctx())
    assert [r.rank for r in ranked[:3]] == ["primary", "secondary", "alternate"]
    assert ranked[0].dm.current_title == "Chief Technology Officer"
    assert ranked[0].reasons  # deterministic reasoning present


# ------------------------------------------------------------------------ API integration
def _seed(s):
    s.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                  name_key="acme", prospect_type="PRODUCT_COMPANY", validation_status="VALID",
                  company_tier="INCUMBENT"))
    s.flush()
    cto = DecisionMaker(linkedin_url="https://l/cto", company_domain="acme.com", first_name="Carol",
                        last_name="Vance", current_title="Chief Technology Officer", seniority="senior",
                        work_email="carol@acme.com", email_status="verified", work_phone="+1-555-0100")
    dft = DecisionMaker(linkedin_url="https://l/dft", company_domain="acme.com", first_name="Dan",
                        last_name="Reed", current_title="Director of DFT", seniority="senior")
    ic = DecisionMaker(linkedin_url="https://l/ic", company_domain="acme.com", first_name="Ike",
                       last_name="Coe", current_title="Verification Engineer")
    s.add_all([cto, dft, ic])
    s.add(LeadScore(company_domain="acme.com", lead_score=88.0, grade="A", priority_rank=1))
    s.add(DemandSignal(company_domain="acme.com", total_engineering_jobs=12, normalized_demand_score=70.0))
    s.flush()
    s.add(LeadershipSignal(signal_id="sig-1", company_domain="acme.com", decision_maker_id=cto.id,
                           person_name="Carol Vance", movement_type="promotion", seniority_band="c_level",
                           source="linkedin_history", confidence="high", summary="Promoted to CTO",
                           to_title="Chief Technology Officer"))
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'intel.db').as_posix()}",
                              log_json=False, dev_auth_bypass=True))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def test_list_exposes_intelligence(client):
    items = client.get("/decision-makers", headers=MEMBER).json()["items"]
    cto = next(d for d in items if d["current_title"] == "Chief Technology Officer")
    assert cto["department_class"] == "Engineering"
    assert cto["department_group"] == "Engineering Leaders"
    assert cto["exec_level"] == "C-Suite"
    assert 0 <= cto["influence_score"] <= 100
    assert cto["confidence_level"] in ("High", "Medium", "Low")


def test_detail_has_full_intelligence_and_leadership(client):
    items = client.get("/decision-makers", headers=MEMBER).json()["items"]
    cto_id = next(d["id"] for d in items if d["current_title"] == "Chief Technology Officer")
    d = client.get(f"/decision-makers/{cto_id}", headers=MEMBER).json()
    assert d["influence_raw"] is not None and d["influence_factors"]
    assert d["confidence_factors"]
    assert d["hierarchy_rank"] == 1
    # leadership integration: the promotion signal is surfaced on the profile
    assert any(s["movement_type"] == "promotion" for s in d["leadership_signals"])


def test_company_contacts_map_and_hierarchy(client):
    body = client.get("/decision-makers/company/acme.com", headers=MEMBER).json()
    assert body["total"] == 3
    ranks = [r["rank"] for r in body["recommended"]]
    assert ranks == ["primary", "secondary", "alternate"]
    assert body["recommended"][0]["contact"]["current_title"] == "Chief Technology Officer"
    assert body["recommended"][0]["reasons"]
    # contact map groups + hierarchy present
    assert any(g["group"] == "Engineering Leaders" for g in body["groups"])
    assert [h["rank"] for h in body["hierarchy"]] == sorted(h["rank"] for h in body["hierarchy"])


def test_company_contacts_404(client):
    assert client.get("/decision-makers/company/nope.com", headers=MEMBER).status_code == 404


def test_outreach_contacts_ranked_and_primary_preselected(client):
    client.post("/outreach/leads/sync", headers=MANAGER)
    leads = client.get("/outreach/leads", headers=MANAGER).json()["items"]
    lead_id = next(l["id"] for l in leads if l["company_domain"] == "acme.com")
    detail = client.get(f"/outreach/leads/{lead_id}", headers=MANAGER).json()
    contacts = detail["contacts"]
    assert contacts[0]["is_primary"] is True                      # primary preselected
    assert contacts[0]["recommendation_rank"] == "primary"
    assert contacts[0]["influence_score"] is not None
    assert contacts[0]["department"] and contacts[0]["recommendation_reason"]
