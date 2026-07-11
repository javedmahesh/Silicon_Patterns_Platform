"""Decision-maker enhancements: engine-sourced contact auto-populate, the lazy
enrichment detail endpoint, and four-tier collaboration notes
(admin / manager / team / personal) with per-role permissions + ordering."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company, DecisionMaker

MEMBER = {"X-Dev-Role": "member"}
MANAGER = {"X-Dev-Role": "manager"}
ADMIN = {"X-Dev-Role": "admin"}


def _seed(s):
    s.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                  name_key="acme", prospect_type="PRODUCT_COMPANY", validation_status="VALID"))
    s.flush()
    s.add(DecisionMaker(
        linkedin_url="https://l/cto", company_domain="acme.com", first_name="Carol",
        last_name="Vance", current_title="Chief Technology Officer", seniority="c_level",
        # engine-sourced (Apify) structured fields
        work_email="carol@acme.com", work_phone="+1-555-0100", email_status="verified",
        city="Austin", state_region="Texas", country="United States",
        organization_linkedin="https://linkedin.com/company/acme", match_score=90,
    ))
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'notes.db').as_posix()}",
                              log_json=False, dev_auth_bypass=True))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _dm_id(c):
    return c.get("/decision-makers", headers=MEMBER).json()["items"][0]["id"]


# ------------------------------------------------------------------ contact auto-populate
def test_contact_auto_populates_from_engine_fields(client):
    """With no analyst-entered contact row, GET returns the Apify-sourced work email/
    phone (flagged from_source) so the UI shows them without manual entry."""
    dm_id = _dm_id(client)
    body = client.get(f"/decision-makers/{dm_id}/contact", headers=MEMBER).json()
    assert body is not None
    assert body["work_email"] == "carol@acme.com"
    assert body["work_phone"] == "+1-555-0100"
    assert body["from_source"] is True


def test_decision_maker_list_exposes_structured_fields(client):
    dm = client.get("/decision-makers", headers=MEMBER).json()["items"][0]
    assert dm["work_email"] == "carol@acme.com"
    assert dm["work_phone"] == "+1-555-0100"
    assert dm["city"] == "Austin" and dm["country"] == "United States"
    assert dm["organization_linkedin"] == "https://linkedin.com/company/acme"


def test_contact_override_preserves_apify_source(client):
    """A manual override keeps the Apify original (source_*), flags the field
    overridden, and a confirm-with-same-value is NOT flagged."""
    dm_id = _dm_id(client)
    # 1. auto-filled, no override
    c0 = client.get(f"/decision-makers/{dm_id}/contact", headers=MEMBER).json()
    assert c0["from_source"] is True and c0["email_overridden"] is False
    assert c0["source_work_email"] == "carol@acme.com"
    # 2. manager overrides the email; phone unchanged
    client.put(f"/decision-makers/{dm_id}/contact", headers=MANAGER,
               json={"work_email": "carol.vance@acme.com", "work_phone": "+1-555-0100"})
    c1 = client.get(f"/decision-makers/{dm_id}/contact", headers=MEMBER).json()
    assert c1["work_email"] == "carol.vance@acme.com"      # manual value wins
    assert c1["email_overridden"] is True                   # flagged overridden
    assert c1["source_work_email"] == "carol@acme.com"      # Apify original preserved
    assert c1["phone_overridden"] is False                  # phone matches source
    assert c1["from_source"] is False
    # 3. confirm: save the SAME value as Apify -> not an override
    client.put(f"/decision-makers/{dm_id}/contact", headers=MANAGER,
               json={"work_email": "carol@acme.com", "work_phone": "+1-555-0100"})
    c2 = client.get(f"/decision-makers/{dm_id}/contact", headers=MEMBER).json()
    assert c2["email_overridden"] is False and c2["from_source"] is True


def test_blank_saved_field_falls_back_to_apify(client):
    """Saving only a phone leaves the email blank in the row, but the effective
    contact still surfaces the Apify email (no manual entry required)."""
    dm_id = _dm_id(client)
    client.put(f"/decision-makers/{dm_id}/contact", headers=MANAGER,
               json={"work_email": "", "work_phone": "+1-555-9999"})
    c = client.get(f"/decision-makers/{dm_id}/contact", headers=MEMBER).json()
    assert c["work_email"] == "carol@acme.com"   # fell back to Apify source
    assert c["work_phone"] == "+1-555-9999"
    assert c["phone_overridden"] is True


def test_saved_contact_overrides_source(client):
    dm_id = _dm_id(client)
    client.put(f"/decision-makers/{dm_id}/contact", headers=MANAGER,
               json={"work_email": "c.vance@acme.com", "work_phone": "+1-555-0199"})
    body = client.get(f"/decision-makers/{dm_id}/contact", headers=MEMBER).json()
    assert body["work_email"] == "c.vance@acme.com"
    assert body["from_source"] is False  # now an analyst-owned row


# ------------------------------------------------------------------ admin / manager tiers
def test_admin_note_requires_admin(client):
    dm_id = _dm_id(client)
    for headers in (MEMBER, MANAGER):
        assert client.post(f"/decision-makers/{dm_id}/notes", headers=headers,
                           json={"note_type": "admin", "content": "x"}).status_code == 403
    r = client.post(f"/decision-makers/{dm_id}/notes", headers=ADMIN,
                    json={"note_type": "admin", "content": "Board-level account"})
    assert r.status_code == 201 and r.json()["note_type"] == "admin"
    assert r.json()["author_role"] == "admin" and r.json()["can_edit"] is True


def test_manager_note_requires_manager(client):
    dm_id = _dm_id(client)
    assert client.post(f"/decision-makers/{dm_id}/notes", headers=MEMBER,
                       json={"note_type": "manager", "content": "x"}).status_code == 403
    for headers, role in ((MANAGER, "manager"), (ADMIN, "admin")):
        r = client.post(f"/decision-makers/{dm_id}/notes", headers=headers,
                        json={"note_type": "manager", "content": "Owned by sales eng"})
        assert r.status_code == 201 and r.json()["author_role"] == role


# ------------------------------------------------------------------ team notes
def test_team_note_allows_any_user(client):
    dm_id = _dm_id(client)
    # any authenticated user (incl. a member) may add a shared team note
    r = client.post(f"/decision-makers/{dm_id}/notes", headers=MEMBER,
                    json={"note_type": "team", "content": "Met at DAC"})
    assert r.status_code == 201 and r.json()["note_type"] == "team"
    assert r.json()["can_edit"] is True and r.json()["author_role"] == "member"


def test_team_note_visible_to_all(client):
    dm_id = _dm_id(client)
    client.post(f"/decision-makers/{dm_id}/notes", headers=MANAGER,
                json={"note_type": "team", "content": "Do not contact before Q4"})
    # every role sees the team note
    for headers, can_edit in ((MEMBER, False), (MANAGER, True), (ADMIN, True)):
        notes = client.get(f"/decision-makers/{dm_id}/notes", headers=headers).json()
        team = [n for n in notes if n["note_type"] == "team"]
        assert len(team) == 1 and team[0]["content"] == "Do not contact before Q4"
        assert team[0]["can_edit"] is can_edit


# ------------------------------------------------------------------ personal notes
def test_personal_note_is_private_to_author(client):
    dm_id = _dm_id(client)
    r = client.post(f"/decision-makers/{dm_id}/notes", headers=MEMBER,
                    json={"note_type": "personal", "content": "Follow up after DAC"})
    assert r.status_code == 201 and r.json()["can_edit"] is True
    # author (member) sees it
    member_notes = client.get(f"/decision-makers/{dm_id}/notes", headers=MEMBER).json()
    assert any(n["content"] == "Follow up after DAC" for n in member_notes)
    # other users (manager, admin) do NOT see another user's personal note
    for headers in (MANAGER, ADMIN):
        notes = client.get(f"/decision-makers/{dm_id}/notes", headers=headers).json()
        assert all(n["note_type"] != "personal" for n in notes)


def test_notes_sorted_by_tier(client):
    dm_id = _dm_id(client)
    client.post(f"/decision-makers/{dm_id}/notes", headers=MEMBER, json={"note_type": "personal", "content": "mine"})
    client.post(f"/decision-makers/{dm_id}/notes", headers=MEMBER, json={"note_type": "team", "content": "team"})
    client.post(f"/decision-makers/{dm_id}/notes", headers=MANAGER, json={"note_type": "manager", "content": "mgr"})
    client.post(f"/decision-makers/{dm_id}/notes", headers=ADMIN, json={"note_type": "admin", "content": "adm"})
    # the member sees the three shared tiers (admin→manager→team) then their own personal
    notes = client.get(f"/decision-makers/{dm_id}/notes", headers=MEMBER).json()
    assert [n["note_type"] for n in notes] == ["admin", "manager", "team", "personal"]


# ------------------------------------------------------------------ edit / delete permissions
def test_author_edits_and_deletes_own_personal_note(client):
    dm_id = _dm_id(client)
    note_id = client.post(f"/decision-makers/{dm_id}/notes", headers=MEMBER,
                          json={"note_type": "personal", "content": "draft"}).json()["id"]
    upd = client.patch(f"/decision-makers/{dm_id}/notes/{note_id}", headers=MEMBER,
                       json={"content": "updated"})
    assert upd.status_code == 200 and upd.json()["content"] == "updated"
    assert client.delete(f"/decision-makers/{dm_id}/notes/{note_id}", headers=MEMBER).status_code == 204
    # gone
    notes = client.get(f"/decision-makers/{dm_id}/notes", headers=MEMBER).json()
    assert all(n["id"] != note_id for n in notes)


def test_member_cannot_edit_team_note(client):
    dm_id = _dm_id(client)
    note_id = client.post(f"/decision-makers/{dm_id}/notes", headers=MANAGER,
                          json={"note_type": "team", "content": "team"}).json()["id"]
    assert client.patch(f"/decision-makers/{dm_id}/notes/{note_id}", headers=MEMBER,
                        json={"content": "hack"}).status_code == 403
    assert client.delete(f"/decision-makers/{dm_id}/notes/{note_id}", headers=MEMBER).status_code == 403


def test_user_cannot_touch_another_users_personal_note(client):
    """A personal note is invisible to others — edit/delete attempts 404 (don't leak existence)."""
    dm_id = _dm_id(client)
    note_id = client.post(f"/decision-makers/{dm_id}/notes", headers=MEMBER,
                          json={"note_type": "personal", "content": "secret"}).json()["id"]
    assert client.patch(f"/decision-makers/{dm_id}/notes/{note_id}", headers=MANAGER,
                        json={"content": "x"}).status_code == 404
    assert client.delete(f"/decision-makers/{dm_id}/notes/{note_id}", headers=MANAGER).status_code == 404


def test_manager_edits_team_note(client):
    dm_id = _dm_id(client)
    note_id = client.post(f"/decision-makers/{dm_id}/notes", headers=MANAGER,
                          json={"note_type": "team", "content": "v1"}).json()["id"]
    # a different manager-tier user (admin) may also edit team notes
    assert client.patch(f"/decision-makers/{dm_id}/notes/{note_id}", headers=ADMIN,
                        json={"content": "v2"}).status_code == 200


# ------------------------------------------------------------------ validation / 404
def test_empty_note_rejected(client):
    dm_id = _dm_id(client)
    assert client.post(f"/decision-makers/{dm_id}/notes", headers=MEMBER,
                       json={"note_type": "personal", "content": "   "}).status_code == 422


def test_notes_404_for_missing_dm(client):
    assert client.get("/decision-makers/99999/notes", headers=MEMBER).status_code == 404
    assert client.post("/decision-makers/99999/notes", headers=MEMBER,
                       json={"note_type": "personal", "content": "x"}).status_code == 404


# ------------------------------------------------------------------ enrichment detail
def test_detail_endpoint_surfaces_enrichment(client):
    """GET /decision-makers/{id} exposes enrichment read from profile_data (curated
    keys AND the raw fallback) with NO new columns; missing fields stay null."""
    with client.app.state.db.sessionmaker() as s:
        s.add(DecisionMaker(
            linkedin_url="https://l/cmo", company_domain="acme.com",
            first_name="Dana", last_name="Reed", current_title="CMO", seniority="c_level",
            work_email="dana@acme.com", email_status="verified",
            profile_data={
                "industry": "Semiconductors", "department": "Marketing",
                "summary": "20y in chip marketing.",
                "raw": {"skills": ["ABM", "Branding"], "languages": ["English", "German"],
                        "followers": 4200, "yearsInRole": "3 years", "personId": "p-1"},
            },
        ))
        s.commit()
    items = client.get("/decision-makers", headers=MEMBER).json()["items"]
    dm_id = next(d["id"] for d in items if d["current_title"] == "CMO")

    d = client.get(f"/decision-makers/{dm_id}", headers=MEMBER).json()
    assert d["industry"] == "Semiconductors"
    assert d["department"] == "Marketing"
    assert d["summary"].startswith("20y")
    assert d["skills"] == "ABM, Branding"          # raw list → comma-joined
    assert d["languages"] == "English, German"
    assert d["followers"] == "4200"                 # raw fallback, coerced to str
    assert d["years_in_role"] == "3 years"
    assert d["apify_person_id"] == "p-1"
    assert d["business_unit"] is None               # missing → null, never a placeholder


def test_detail_404_for_missing_dm(client):
    assert client.get("/decision-makers/99999", headers=MEMBER).status_code == 404
