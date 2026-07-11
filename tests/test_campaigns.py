"""Enterprise CRM Phase 1: Campaign & Sequence Management tests."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company, DecisionMaker, LeadScore

MGR = {"X-Dev-Role": "manager"}
MEM = {"X-Dev-Role": "member"}


def _seed(s):
    s.add(Company(
        company_domain="acme.com", canonical_company_id="ACME",
        company_name="Acme Corp", name_key="acme",
        prospect_type="PRODUCT_COMPANY", validation_status="VALID",
        company_tier="INCUMBENT",
    ))
    s.add(Company(
        company_domain="beta.com", canonical_company_id="BETA",
        company_name="Beta Inc", name_key="beta",
        prospect_type="PRODUCT_COMPANY", validation_status="VALID",
        company_tier="SCALEUP",
    ))
    s.flush()
    s.add_all([
        LeadScore(company_domain="acme.com", lead_score=88.0, grade="A", priority_rank=1),
        DecisionMaker(
            linkedin_url="https://l/cto_acme", company_domain="acme.com",
            first_name="Alice", last_name="Smith", current_title="CTO",
            seniority="senior", work_email="alice@acme.com", match_score=90,
        ),
    ])
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'crm.db').as_posix()}",
        log_json=False, dev_auth_bypass=True,
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


# =====================================================================
# Campaign CRUD
# =====================================================================
class TestCampaignCRUD:
    def test_create_campaign(self, client):
        r = client.post("/campaigns", headers=MGR, json={
            "name": "Q1 Outreach", "description": "Q1 cold outreach",
            "campaign_type": "cold_outreach",
        })
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Q1 Outreach"
        assert body["status"] == "draft"
        assert body["campaign_type"] == "cold_outreach"
        assert body["id"] > 0

    def test_member_can_create_campaign(self, client):
        r = client.post("/campaigns", headers=MEM, json={"name": "Member Campaign"})
        assert r.status_code == 201

    def test_list_campaigns_empty(self, client):
        r = client.get("/campaigns", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["items"] == []

    def test_list_campaigns_populated(self, client):
        client.post("/campaigns", headers=MGR, json={"name": "C1"})
        client.post("/campaigns", headers=MGR, json={"name": "C2"})
        r = client.get("/campaigns", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 2

    def test_get_campaign(self, client):
        cr = client.post("/campaigns", headers=MGR, json={"name": "My Campaign"})
        cid = cr.json()["id"]
        r = client.get(f"/campaigns/{cid}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["id"] == cid
        assert r.json()["name"] == "My Campaign"

    def test_get_nonexistent_campaign(self, client):
        r = client.get("/campaigns/999", headers=MGR)
        assert r.status_code == 404

    def test_patch_campaign(self, client):
        cr = client.post("/campaigns", headers=MGR, json={"name": "Orig"})
        cid = cr.json()["id"]
        r = client.patch(f"/campaigns/{cid}", headers=MGR, json={
            "name": "Updated", "status": "active",
        })
        assert r.status_code == 200
        assert r.json()["name"] == "Updated"
        assert r.json()["status"] == "active"

    def test_archive_campaign(self, client):
        cr = client.post("/campaigns", headers=MGR, json={"name": "To Archive"})
        cid = cr.json()["id"]
        r = client.delete(f"/campaigns/{cid}", headers=MGR)
        assert r.status_code == 204
        # Verify archived
        r2 = client.get(f"/campaigns/{cid}", headers=MGR)
        assert r2.json()["status"] == "archived"

    def test_archive_requires_manager(self, client):
        cr = client.post("/campaigns", headers=MGR, json={"name": "Protected"})
        cid = cr.json()["id"]
        r = client.delete(f"/campaigns/{cid}", headers=MEM)
        assert r.status_code == 403

    def test_campaign_with_tags(self, client):
        r = client.post("/campaigns", headers=MGR, json={
            "name": "Tagged", "tags": ["q1", "enterprise"],
        })
        assert r.status_code == 201
        assert "q1" in r.json()["tags"]

    def test_campaign_with_budget(self, client):
        r = client.post("/campaigns", headers=MGR, json={
            "name": "Budgeted", "budget": 5000.0,
        })
        assert r.status_code == 201
        assert r.json()["budget"] == 5000.0


# =====================================================================
# Campaign Search & Filtering
# =====================================================================
class TestCampaignSearch:
    def test_filter_by_status(self, client):
        client.post("/campaigns", headers=MGR, json={"name": "Draft One"})
        client.post("/campaigns", headers=MGR, json={
            "name": "Active One", "status": "draft",
        })
        # Activate one
        r = client.get("/campaigns", headers=MGR)
        items = r.json()["items"]
        first_id = items[0]["id"]
        client.patch(f"/campaigns/{first_id}", headers=MGR, json={"status": "active"})

        r = client.get("/campaigns?status=active", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_filter_by_type(self, client):
        client.post("/campaigns", headers=MGR, json={
            "name": "Nurture", "campaign_type": "nurture",
        })
        client.post("/campaigns", headers=MGR, json={
            "name": "Cold", "campaign_type": "cold_outreach",
        })
        r = client.get("/campaigns?campaign_type=nurture", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["name"] == "Nurture"

    def test_search_by_name(self, client):
        client.post("/campaigns", headers=MGR, json={"name": "Alpha Campaign"})
        client.post("/campaigns", headers=MGR, json={"name": "Beta Run"})
        r = client.get("/campaigns?search=Alpha", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_pagination(self, client):
        for i in range(5):
            client.post("/campaigns", headers=MGR, json={"name": f"Campaign {i}"})
        r = client.get("/campaigns?limit=2&offset=0", headers=MGR)
        assert r.status_code == 200
        assert len(r.json()["items"]) == 2
        assert r.json()["total"] == 5


# =====================================================================
# Campaign Members
# =====================================================================
class TestCampaignMembers:
    def _create_campaign(self, client):
        r = client.post("/campaigns", headers=MGR, json={"name": "Test Campaign"})
        return r.json()["id"]

    def test_add_member_by_domain(self, client):
        cid = self._create_campaign(client)
        r = client.post(f"/campaigns/{cid}/members", headers=MGR, json={
            "company_domain": "acme.com",
        })
        assert r.status_code == 201
        assert r.json()["company_domain"] == "acme.com"
        assert r.json()["engagement_status"] == "active"

    def test_add_member_with_lead(self, client):
        # Create outreach lead first
        lead_r = client.post("/outreach/leads", headers=MGR, json={"company_domain": "acme.com"})
        assert lead_r.status_code in (200, 201)
        lead_id = lead_r.json()["id"]

        cid = self._create_campaign(client)
        r = client.post(f"/campaigns/{cid}/members", headers=MGR, json={
            "company_domain": "acme.com", "outreach_lead_id": lead_id,
        })
        assert r.status_code == 201
        assert r.json()["outreach_lead_id"] == lead_id

    def test_duplicate_member_rejected(self, client):
        cid = self._create_campaign(client)
        client.post(f"/campaigns/{cid}/members", headers=MGR, json={"company_domain": "acme.com"})
        r = client.post(f"/campaigns/{cid}/members", headers=MGR, json={"company_domain": "acme.com"})
        assert r.status_code == 409

    def test_list_members(self, client):
        cid = self._create_campaign(client)
        client.post(f"/campaigns/{cid}/members", headers=MGR, json={"company_domain": "acme.com"})
        client.post(f"/campaigns/{cid}/members", headers=MGR, json={"company_domain": "beta.com"})
        r = client.get(f"/campaigns/{cid}/members", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 2

    def test_patch_member(self, client):
        cid = self._create_campaign(client)
        mr = client.post(f"/campaigns/{cid}/members", headers=MGR, json={"company_domain": "acme.com"})
        mid = mr.json()["id"]
        r = client.patch(f"/campaigns/{cid}/members/{mid}", headers=MGR, json={
            "current_stage": "contacted", "campaign_outcome": "converted",
        })
        assert r.status_code == 200
        assert r.json()["current_stage"] == "contacted"
        assert r.json()["campaign_outcome"] == "converted"

    def test_remove_member(self, client):
        cid = self._create_campaign(client)
        mr = client.post(f"/campaigns/{cid}/members", headers=MGR, json={"company_domain": "acme.com"})
        mid = mr.json()["id"]
        r = client.delete(f"/campaigns/{cid}/members/{mid}", headers=MGR)
        assert r.status_code == 204

    def test_member_company_name_populated(self, client):
        cid = self._create_campaign(client)
        client.post(f"/campaigns/{cid}/members", headers=MGR, json={"company_domain": "acme.com"})
        r = client.get(f"/campaigns/{cid}/members", headers=MGR)
        assert r.status_code == 200
        member = r.json()["items"][0]
        assert member["company_name"] == "Acme Corp"

    def test_member_stats_reflected_in_campaign(self, client):
        cid = self._create_campaign(client)
        client.post(f"/campaigns/{cid}/members", headers=MGR, json={"company_domain": "acme.com"})
        r = client.get(f"/campaigns/{cid}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["member_count"] == 1
        assert r.json()["active_count"] == 1


# =====================================================================
# Sequences
# =====================================================================
class TestSequences:
    def test_create_sequence(self, client):
        r = client.post("/sequences", headers=MGR, json={
            "name": "Cold Outreach Sequence", "description": "5-touch sequence",
        })
        assert r.status_code == 201
        assert r.json()["name"] == "Cold Outreach Sequence"
        assert r.json()["is_active"] is True
        assert r.json()["step_count"] == 0

    def test_list_sequences(self, client):
        client.post("/sequences", headers=MGR, json={"name": "Seq A"})
        client.post("/sequences", headers=MGR, json={"name": "Seq B"})
        r = client.get("/sequences", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 2

    def test_get_sequence(self, client):
        sr = client.post("/sequences", headers=MGR, json={"name": "My Seq"})
        sid = sr.json()["id"]
        r = client.get(f"/sequences/{sid}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["id"] == sid

    def test_patch_sequence(self, client):
        sr = client.post("/sequences", headers=MGR, json={"name": "Old Name"})
        sid = sr.json()["id"]
        r = client.patch(f"/sequences/{sid}", headers=MGR, json={"name": "New Name"})
        assert r.status_code == 200
        assert r.json()["name"] == "New Name"

    def test_delete_sequence_requires_manager(self, client):
        sr = client.post("/sequences", headers=MGR, json={"name": "Protected Seq"})
        sid = sr.json()["id"]
        r = client.delete(f"/sequences/{sid}", headers=MEM)
        assert r.status_code == 403

    def test_delete_sequence(self, client):
        sr = client.post("/sequences", headers=MGR, json={"name": "To Delete"})
        sid = sr.json()["id"]
        r = client.delete(f"/sequences/{sid}", headers=MGR)
        assert r.status_code == 204

    def test_active_only_filter(self, client):
        client.post("/sequences", headers=MGR, json={"name": "Active Seq"})
        sr = client.post("/sequences", headers=MGR, json={"name": "Inactive Seq"})
        sid = sr.json()["id"]
        client.delete(f"/sequences/{sid}", headers=MGR)

        r = client.get("/sequences?active_only=true", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["name"] == "Active Seq"


# =====================================================================
# Sequence Steps
# =====================================================================
class TestSequenceSteps:
    def _make_seq(self, client):
        r = client.post("/sequences", headers=MGR, json={"name": "Test Seq"})
        return r.json()["id"]

    def test_add_step(self, client):
        sid = self._make_seq(client)
        r = client.post(f"/sequences/{sid}/steps", headers=MGR, json={
            "step_order": 1, "action": "email", "name": "Initial Email",
            "delay_days": 0, "description": "First touch",
        })
        assert r.status_code == 201
        assert r.json()["action"] == "email"
        assert r.json()["step_order"] == 1
        assert r.json()["delay_days"] == 0

    def test_add_multiple_steps(self, client):
        sid = self._make_seq(client)
        for i, action in enumerate(["email", "follow_up", "call"], start=1):
            client.post(f"/sequences/{sid}/steps", headers=MGR, json={
                "step_order": i, "action": action, "delay_days": (i - 1) * 3,
            })
        r = client.get(f"/sequences/{sid}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["step_count"] == 3
        orders = [s["step_order"] for s in r.json()["steps"]]
        assert orders == sorted(orders)

    def test_step_actions(self, client):
        sid = self._make_seq(client)
        for i, action in enumerate(
            ["email", "follow_up", "meeting_request", "call", "task", "wait", "manual_review"],
            start=1,
        ):
            r = client.post(f"/sequences/{sid}/steps", headers=MGR, json={
                "step_order": i, "action": action,
            })
            assert r.status_code == 201, f"action {action} failed: {r.text}"

    def test_patch_step(self, client):
        sid = self._make_seq(client)
        sr = client.post(f"/sequences/{sid}/steps", headers=MGR, json={
            "step_order": 1, "action": "email", "delay_days": 0,
        })
        step_id = sr.json()["id"]
        r = client.patch(f"/sequences/{sid}/steps/{step_id}", headers=MGR, json={
            "delay_days": 3, "name": "Updated Step",
        })
        assert r.status_code == 200
        assert r.json()["delay_days"] == 3
        assert r.json()["name"] == "Updated Step"

    def test_delete_step(self, client):
        sid = self._make_seq(client)
        sr = client.post(f"/sequences/{sid}/steps", headers=MGR, json={
            "step_order": 1, "action": "email",
        })
        step_id = sr.json()["id"]
        r = client.delete(f"/sequences/{sid}/steps/{step_id}", headers=MGR)
        assert r.status_code == 204
        # Sequence step count should now be 0
        r2 = client.get(f"/sequences/{sid}", headers=MGR)
        assert r2.json()["step_count"] == 0


# =====================================================================
# Enrollment List
# =====================================================================
class TestEnrollmentList:
    def _setup(self, client, domain="acme.com"):
        """Returns (campaign_id, member_id, lead_id, sequence_id)."""
        lead_r = client.post("/outreach/leads", headers=MGR, json={"company_domain": domain})
        lead_id = lead_r.json()["id"]
        cid = client.post("/campaigns", headers=MGR, json={"name": f"Campaign {domain}"}).json()["id"]
        mid = client.post(f"/campaigns/{cid}/members", headers=MGR, json={
            "company_domain": domain, "outreach_lead_id": lead_id,
        }).json()["id"]
        sid = client.post("/sequences", headers=MGR, json={"name": f"Seq {domain}"}).json()["id"]
        client.post(f"/sequences/{sid}/steps", headers=MGR, json={
            "step_order": 1, "action": "email", "delay_days": 0,
        })
        return cid, mid, lead_id, sid

    def test_list_empty(self, client):
        r = client.get("/enrollments", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["items"] == []

    def test_list_populated_with_display_fields(self, client):
        cid, mid, lead_id, sid = self._setup(client)
        er = client.post(f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR)
        eid = er.json()["id"]
        r = client.get("/enrollments", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 1
        item = r.json()["items"][0]
        assert item["id"] == eid
        assert item["sequence_id"] == sid
        assert item["sequence_name"] == "Seq acme.com"
        assert item["step_count"] == 1
        assert item["campaign_id"] == cid
        assert item["campaign_name"] == "Campaign acme.com"
        assert item["company_domain"] == "acme.com"
        assert item["company_name"] == "Acme Corp"

    def test_filter_by_sequence(self, client):
        cid1, mid1, _, sid1 = self._setup(client, "acme.com")
        cid2, mid2, _, sid2 = self._setup(client, "beta.com")
        client.post(f"/campaigns/{cid1}/members/{mid1}/enroll?sequence_id={sid1}", headers=MGR)
        client.post(f"/campaigns/{cid2}/members/{mid2}/enroll?sequence_id={sid2}", headers=MGR)

        r = client.get(f"/enrollments?sequence_id={sid1}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["sequence_id"] == sid1

    def test_filter_by_campaign(self, client):
        cid, mid, _, sid = self._setup(client)
        client.post(f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR)
        r = client.get(f"/enrollments?campaign_id={cid}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_filter_by_campaign_with_no_members_returns_empty(self, client):
        cid = client.post("/campaigns", headers=MGR, json={"name": "Empty"}).json()["id"]
        r = client.get(f"/enrollments?campaign_id={cid}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_filter_by_status(self, client):
        cid, mid, _, sid = self._setup(client)
        er = client.post(f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR)
        eid = er.json()["id"]
        client.post(f"/enrollments/{eid}/pause", headers=MGR)

        r = client.get("/enrollments?status=paused", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 1
        r2 = client.get("/enrollments?status=active", headers=MGR)
        assert r2.json()["total"] == 0

    def test_search_by_company(self, client):
        cid, mid, _, sid = self._setup(client, "acme.com")
        client.post(f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR)
        r = client.get("/enrollments?search=Acme", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 1
        r2 = client.get("/enrollments?search=NoSuchCompany", headers=MGR)
        assert r2.json()["total"] == 0

    def test_pagination(self, client):
        cid1, mid1, _, sid1 = self._setup(client, "acme.com")
        cid2, mid2, _, sid2 = self._setup(client, "beta.com")
        client.post(f"/campaigns/{cid1}/members/{mid1}/enroll?sequence_id={sid1}", headers=MGR)
        client.post(f"/campaigns/{cid2}/members/{mid2}/enroll?sequence_id={sid2}", headers=MGR)

        r = client.get("/enrollments?limit=1&offset=0", headers=MGR)
        assert r.status_code == 200
        assert len(r.json()["items"]) == 1
        assert r.json()["total"] == 2
        r2 = client.get("/enrollments?limit=1&offset=1", headers=MGR)
        assert len(r2.json()["items"]) == 1
        assert r2.json()["items"][0]["id"] != r.json()["items"][0]["id"]

    def test_member_not_yet_enrolled_is_absent(self, client):
        self._setup(client)  # creates campaign/member/sequence but never enrolls
        r = client.get("/enrollments", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 0


# =====================================================================
# Sequence Enrollment
# =====================================================================
class TestSequenceEnrollment:
    def _setup(self, client):
        """Returns (campaign_id, member_id, lead_id, sequence_id)."""
        lead_r = client.post("/outreach/leads", headers=MGR, json={"company_domain": "acme.com"})
        assert lead_r.status_code in (200, 201)
        lead_id = lead_r.json()["id"]

        cid = client.post("/campaigns", headers=MGR, json={"name": "Enroll Campaign"}).json()["id"]
        mid = client.post(f"/campaigns/{cid}/members", headers=MGR, json={
            "company_domain": "acme.com", "outreach_lead_id": lead_id,
        }).json()["id"]

        sid = client.post("/sequences", headers=MGR, json={"name": "Enroll Seq"}).json()["id"]
        client.post(f"/sequences/{sid}/steps", headers=MGR, json={
            "step_order": 1, "action": "email", "delay_days": 0,
        })
        client.post(f"/sequences/{sid}/steps", headers=MGR, json={
            "step_order": 2, "action": "follow_up", "delay_days": 3,
        })
        return cid, mid, lead_id, sid

    def test_enroll_member(self, client):
        cid, mid, lead_id, sid = self._setup(client)
        r = client.post(
            f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR
        )
        assert r.status_code == 201
        body = r.json()
        assert body["sequence_id"] == sid
        assert body["outreach_lead_id"] == lead_id
        assert body["status"] == "active"
        assert body["current_step"] == 1

    def test_duplicate_enroll_rejected(self, client):
        cid, mid, lead_id, sid = self._setup(client)
        client.post(f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR)
        r = client.post(
            f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR
        )
        assert r.status_code == 409

    def test_pause_enrollment(self, client):
        cid, mid, lead_id, sid = self._setup(client)
        er = client.post(f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR)
        eid = er.json()["id"]
        r = client.post(f"/enrollments/{eid}/pause", headers=MGR)
        assert r.status_code == 200
        assert r.json()["status"] == "paused"

    def test_resume_enrollment(self, client):
        cid, mid, lead_id, sid = self._setup(client)
        er = client.post(f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR)
        eid = er.json()["id"]
        client.post(f"/enrollments/{eid}/pause", headers=MGR)
        r = client.post(f"/enrollments/{eid}/resume", headers=MGR)
        assert r.status_code == 200
        assert r.json()["status"] == "active"

    def test_cancel_enrollment(self, client):
        cid, mid, lead_id, sid = self._setup(client)
        er = client.post(f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR)
        eid = er.json()["id"]
        r = client.post(f"/enrollments/{eid}/cancel", headers=MGR)
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"
        assert r.json()["completed_at"] is not None

    def test_advance_enrollment(self, client):
        cid, mid, lead_id, sid = self._setup(client)
        er = client.post(f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR)
        eid = er.json()["id"]
        assert er.json()["current_step"] == 1
        r = client.post(f"/enrollments/{eid}/advance", headers=MGR)
        assert r.status_code == 200
        assert r.json()["current_step"] == 2

    def test_advance_past_last_step_completes(self, client):
        cid, mid, lead_id, sid = self._setup(client)
        er = client.post(f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR)
        eid = er.json()["id"]
        # advance twice (2-step sequence)
        client.post(f"/enrollments/{eid}/advance", headers=MGR)
        r = client.post(f"/enrollments/{eid}/advance", headers=MGR)
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

    def test_skip_step(self, client):
        cid, mid, lead_id, sid = self._setup(client)
        er = client.post(f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR)
        eid = er.json()["id"]
        # Get the step id from the sequence
        seq_r = client.get(f"/sequences/{sid}", headers=MGR)
        step_id = seq_r.json()["steps"][0]["id"]
        r = client.post(f"/enrollments/{eid}/steps/{step_id}/skip", headers=MGR)
        assert r.status_code == 200

    def test_member_without_lead_cannot_enroll(self, client):
        cid = client.post("/campaigns", headers=MGR, json={"name": "No Lead Campaign"}).json()["id"]
        mid = client.post(f"/campaigns/{cid}/members", headers=MGR, json={
            "company_domain": "acme.com",
        }).json()["id"]
        sid = client.post("/sequences", headers=MGR, json={"name": "Seq"}).json()["id"]
        r = client.post(f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR)
        assert r.status_code == 400


# =====================================================================
# Campaign Analytics
# =====================================================================
class TestCampaignAnalytics:
    def test_analytics_empty_campaign(self, client):
        cid = client.post("/campaigns", headers=MGR, json={"name": "Empty"}).json()["id"]
        r = client.get(f"/campaigns/{cid}/analytics", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert body["campaign_id"] == cid
        assert body["emails_sent"] == 0
        assert body["total_members"] == 0
        assert body["reply_rate"] == 0.0

    def test_analytics_with_members(self, client):
        cid = client.post("/campaigns", headers=MGR, json={"name": "With Members"}).json()["id"]
        client.post(f"/campaigns/{cid}/members", headers=MGR, json={"company_domain": "acme.com"})
        client.post(f"/campaigns/{cid}/members", headers=MGR, json={"company_domain": "beta.com"})
        r = client.get(f"/campaigns/{cid}/analytics", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total_members"] == 2
        assert r.json()["companies_contacted"] == 2

    def test_analytics_404_for_nonexistent(self, client):
        r = client.get("/campaigns/999/analytics", headers=MGR)
        assert r.status_code == 404

    def test_analytics_conversion_rate(self, client):
        cid = client.post("/campaigns", headers=MGR, json={"name": "Conversion Test"}).json()["id"]
        mr = client.post(f"/campaigns/{cid}/members", headers=MGR, json={"company_domain": "acme.com"})
        mid = mr.json()["id"]
        client.patch(f"/campaigns/{cid}/members/{mid}", headers=MGR, json={
            "campaign_outcome": "converted",
        })
        r = client.get(f"/campaigns/{cid}/analytics", headers=MGR)
        assert r.status_code == 200
        assert r.json()["converted"] == 1
        assert r.json()["conversion_rate"] == 1.0

    def test_analytics_sequence_completion(self, client):
        lead_r = client.post("/outreach/leads", headers=MGR, json={"company_domain": "acme.com"})
        lead_id = lead_r.json()["id"]
        cid = client.post("/campaigns", headers=MGR, json={"name": "Seq Analytics"}).json()["id"]
        mid = client.post(f"/campaigns/{cid}/members", headers=MGR, json={
            "company_domain": "acme.com", "outreach_lead_id": lead_id,
        }).json()["id"]
        sid = client.post("/sequences", headers=MGR, json={"name": "Single Step"}).json()["id"]
        client.post(f"/sequences/{sid}/steps", headers=MGR, json={
            "step_order": 1, "action": "email", "delay_days": 0,
        })
        er = client.post(f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR)
        eid = er.json()["id"]
        # Complete the enrollment by advancing past the one step
        client.post(f"/enrollments/{eid}/advance", headers=MGR)
        r = client.get(f"/campaigns/{cid}/analytics", headers=MGR)
        assert r.status_code == 200
        assert r.json()["sequence_completion_rate"] == 1.0


# =====================================================================
# Campaign Timeline
# =====================================================================
class TestCampaignTimeline:
    def test_timeline_empty(self, client):
        cid = client.post("/campaigns", headers=MGR, json={"name": "No Timeline"}).json()["id"]
        r = client.get(f"/campaigns/{cid}/timeline", headers=MGR)
        assert r.status_code == 200
        assert r.json() == []

    def test_timeline_404_for_nonexistent(self, client):
        r = client.get("/campaigns/999/timeline", headers=MGR)
        assert r.status_code == 404

    def test_timeline_with_outreach_activity(self, client):
        lead_r = client.post("/outreach/leads", headers=MGR, json={"company_domain": "acme.com"})
        lead_id = lead_r.json()["id"]
        cid = client.post("/campaigns", headers=MGR, json={"name": "Timeline Test"}).json()["id"]
        client.post(f"/campaigns/{cid}/members", headers=MGR, json={
            "company_domain": "acme.com", "outreach_lead_id": lead_id,
        })
        r = client.get(f"/campaigns/{cid}/timeline", headers=MGR)
        assert r.status_code == 200
        # lead_created event should appear (logged when lead was created)
        events = r.json()
        assert isinstance(events, list)


# =====================================================================
# Campaign Dashboard
# =====================================================================
class TestCampaignDashboard:
    def test_dashboard_empty(self, client):
        r = client.get("/campaigns/dashboard", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert body["active_campaigns"] == 0
        assert body["emails_sent"] == 0
        assert body["campaigns"] == []

    def test_dashboard_with_active_campaign(self, client):
        cr = client.post("/campaigns", headers=MGR, json={"name": "Active"})
        cid = cr.json()["id"]
        client.patch(f"/campaigns/{cid}", headers=MGR, json={"status": "active"})
        r = client.get("/campaigns/dashboard", headers=MGR)
        assert r.status_code == 200
        assert r.json()["active_campaigns"] == 1
        assert len(r.json()["campaigns"]) == 1

    def test_dashboard_only_shows_active(self, client):
        client.post("/campaigns", headers=MGR, json={"name": "Draft Camp"})
        cr = client.post("/campaigns", headers=MGR, json={"name": "Active Camp"})
        cid = cr.json()["id"]
        client.patch(f"/campaigns/{cid}", headers=MGR, json={"status": "active"})
        r = client.get("/campaigns/dashboard", headers=MGR)
        assert r.status_code == 200
        assert r.json()["active_campaigns"] == 1


# =====================================================================
# Scheduler Integration
# =====================================================================
class TestSchedulerIntegration:
    def test_scheduler_tick_includes_sequences(self, client):
        r = client.post("/outreach/scheduler/tick", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        # New field added by Phase 1
        assert "sequences_advanced" in body
        assert body["sequences_advanced"] >= 0

    def test_scheduler_advances_ready_steps(self, client):
        """Enroll a lead with immediate step (delay_days=0) and verify scheduler advances it."""
        lead_r = client.post("/outreach/leads", headers=MGR, json={"company_domain": "acme.com"})
        lead_id = lead_r.json()["id"]
        cid = client.post("/campaigns", headers=MGR, json={"name": "Sched Campaign"}).json()["id"]
        mid = client.post(f"/campaigns/{cid}/members", headers=MGR, json={
            "company_domain": "acme.com", "outreach_lead_id": lead_id,
        }).json()["id"]
        sid = client.post("/sequences", headers=MGR, json={"name": "Sched Seq"}).json()["id"]
        client.post(f"/sequences/{sid}/steps", headers=MGR, json={
            "step_order": 1, "action": "email", "delay_days": 0,
        })
        client.post(f"/sequences/{sid}/steps", headers=MGR, json={
            "step_order": 2, "action": "follow_up", "delay_days": 0,
        })
        client.post(f"/campaigns/{cid}/members/{mid}/enroll?sequence_id={sid}", headers=MGR)

        # Tick should advance step 1 → step 2
        r = client.post("/outreach/scheduler/tick", headers=MGR)
        assert r.status_code == 200
        assert r.json()["sequences_advanced"] >= 1


# =====================================================================
# Backward Compatibility
# =====================================================================
class TestBackwardCompatibility:
    def test_outreach_leads_still_work(self, client):
        r = client.get("/outreach/leads", headers=MGR)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_outreach_templates_still_work(self, client):
        r = client.get("/outreach/templates", headers=MGR)
        assert r.status_code == 200

    def test_existing_scheduler_fields_present(self, client):
        r = client.post("/outreach/scheduler/tick", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        assert "scheduled_to_queued" in body
        assert "cancelled_by_deadline" in body
        assert "gmail_synced" in body
        assert "gmail_tokens_refreshed" in body

    def test_campaign_filter_by_company(self, client):
        cid1 = client.post("/campaigns", headers=MGR, json={"name": "C1"}).json()["id"]
        cid2 = client.post("/campaigns", headers=MGR, json={"name": "C2"}).json()["id"]
        client.post(f"/campaigns/{cid1}/members", headers=MGR, json={"company_domain": "acme.com"})
        r = client.get("/campaigns?company_domain=acme.com", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["id"] == cid1

    def test_campaign_filter_by_dm(self, client):
        # Create a DM and link it to a campaign member
        cid = client.post("/campaigns", headers=MGR, json={"name": "DM Filter"}).json()["id"]
        # DM id 1 was seeded
        client.post(f"/campaigns/{cid}/members", headers=MGR, json={
            "company_domain": "acme.com", "decision_maker_id": 1,
        })
        r = client.get("/campaigns?decision_maker_id=1", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 1
