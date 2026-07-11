"""Phase 3: senior filter + professional contacts (work email/phone only)."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company, DecisionMaker

H = {"X-Dev-Role": "member"}    # member: read-only access to professional contacts
HW = {"X-Dev-Role": "manager"}  # manager/admin: may edit professional contacts


def _seed(s):
    s.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                  name_key="acme", prospect_type="PRODUCT_COMPANY", validation_status="VALID"))
    s.flush()
    s.add_all([
        DecisionMaker(linkedin_url="https://l/cto", company_domain="acme.com", first_name="Carol",
                      current_title="Chief Technology Officer", seniority="c_level", match_score=90),
        DecisionMaker(linkedin_url="https://l/eng", company_domain="acme.com", first_name="Dave",
                      current_title="Software Engineer", seniority="senior", match_score=50),
    ])
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'dm.db').as_posix()}",
                              log_json=False, dev_auth_bypass=True))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _cto_id(c):
    items = c.get("/decision-makers", headers=H).json()["items"]
    return next(d["id"] for d in items if "Chief" in d["current_title"])


def test_senior_filter(client):
    assert client.get("/decision-makers", headers=H).json()["total"] == 2
    senior = client.get("/decision-makers", params={"senior": True}, headers=H).json()
    assert senior["total"] == 1 and "Chief" in senior["items"][0]["current_title"]


def test_company_senior_count(client):
    acme = next(x for x in client.get("/decision-makers/companies", headers=H).json()["companies"]
                if x["company_domain"] == "acme.com")
    assert acme["total"] == 2 and acme["senior"] == 1


def test_contact_upsert_and_get(client):
    dm_id = _cto_id(client)
    assert client.get(f"/decision-makers/{dm_id}/contact", headers=H).json() is None
    r = client.put(f"/decision-makers/{dm_id}/contact", headers=HW,
                   json={"work_email": "carol@acme.com", "work_phone": "+1-555-0100", "notes": "Met at DAC"})
    assert r.status_code == 200
    body = r.json()
    assert body["work_email"] == "carol@acme.com" and body["work_phone"] == "+1-555-0100"
    assert body["added_by_email"] == "betatestingmanager@siliconpatterns.com"
    assert client.get(f"/decision-makers/{dm_id}/contact", headers=H).json()["work_email"] == "carol@acme.com"
    # idempotent upsert (one row, updated)
    assert client.put(f"/decision-makers/{dm_id}/contact", headers=HW,
                      json={"work_email": "c@acme.com"}).json()["work_email"] == "c@acme.com"


def test_contact_404_for_missing_dm(client):
    assert client.put("/decision-makers/99999/contact", headers=HW,
                      json={"work_email": "x@y.com"}).status_code == 404


def test_member_read_only_admin_manager_edit(client):
    """Viewing professional contacts is open to any authenticated user; editing is
    an admin/manager action (members get 403)."""
    dm_id = _cto_id(client)
    assert client.get(f"/decision-makers/{dm_id}/contact", headers=H).status_code == 200
    # member cannot write
    assert client.put(f"/decision-makers/{dm_id}/contact", headers=H,
                      json={"work_email": "no@acme.com"}).status_code == 403
    # manager + admin can write
    assert client.put(f"/decision-makers/{dm_id}/contact", headers=HW,
                      json={"work_email": "mgr@acme.com"}).status_code == 200
    assert client.put(f"/decision-makers/{dm_id}/contact", headers={"X-Dev-Role": "admin"},
                      json={"work_email": "adm@acme.com"}).status_code == 200
    # the admin write is readable by a member
    assert client.get(f"/decision-makers/{dm_id}/contact",
                      headers=H).json()["work_email"] == "adm@acme.com"


def test_senior_filter_ignores_substring_collisions(tmp_path):
    """A naive '%cto%'/'%cro%'/'%coo%' substring match flags ordinary engineers
    at chip companies ('semiconduCTOrs', 'miCROchip', 'COOrdinator'). The senior
    filter must match whole tokens only."""
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'sr.db').as_posix()}",
                              log_json=False, dev_auth_bypass=True))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            s.add(Company(company_domain="chip.com", canonical_company_id="CHIP", company_name="Chip Co",
                          name_key="chip", prospect_type="PRODUCT_COMPANY", validation_status="VALID"))
            s.flush()
            s.add_all([
                DecisionMaker(linkedin_url="https://l/1", company_domain="chip.com", first_name="Ivy",
                              current_title="SOC Verification Engineer at NXP Semiconductors",
                              seniority="senior", match_score=40),
                DecisionMaker(linkedin_url="https://l/2", company_domain="chip.com", first_name="Raj",
                              current_title="Partnerships Coordinator, Microchip Technology",
                              seniority="", match_score=30),
                DecisionMaker(linkedin_url="https://l/3", company_domain="chip.com", first_name="Sam",
                              current_title="VP Engineering", seniority="", match_score=80),
                DecisionMaker(linkedin_url="https://l/4", company_domain="chip.com", first_name="Lee",
                              current_title="CEO & Co-Founder", seniority="c_level", match_score=95),
            ])
            s.commit()
        senior = c.get("/decision-makers", params={"senior": True}, headers=H).json()
        titles = sorted(d["current_title"] for d in senior["items"])
        assert titles == ["CEO & Co-Founder", "VP Engineering"], titles
        comp = next(x for x in c.get("/decision-makers/companies", headers=H).json()["companies"]
                    if x["company_domain"] == "chip.com")
        assert comp["total"] == 4 and comp["senior"] == 2
