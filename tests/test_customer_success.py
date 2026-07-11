"""Enterprise CRM Phase 4: Customer Success & Account Management tests."""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company, LeadScore

MGR = {"X-Dev-Role": "manager"}
MEM = {"X-Dev-Role": "member"}


def _seed(s):
    s.add(Company(
        company_domain="acme.com", canonical_company_id="ACME",
        company_name="Acme Corp", name_key="acme",
        prospect_type="PRODUCT_COMPANY", validation_status="VALID",
        company_tier="INCUMBENT",
    ))
    s.add(LeadScore(company_domain="acme.com", lead_score=88.0, grade="A", priority_rank=1))
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'cs.db').as_posix()}",
        log_json=False, dev_auth_bypass=True,
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _uid(client, headers=MGR) -> int:
    return client.get("/auth/me", headers=headers).json()["id"]


def _make_account(client, **kw) -> dict:
    return client.post("/cs/accounts", headers=MGR, json={
        "name": "Acme Customer", "company_domain": "acme.com",
        "tier": "enterprise", "arr": 120000.0, "mrr": 10000.0,
        "lifecycle_stage": "customer", **kw,
    }).json()


# =====================================================================
# Account CRUD
# =====================================================================
class TestAccountCRUD:
    def test_create_account(self, client):
        r = client.post("/cs/accounts", headers=MGR, json={
            "name": "Beta Corp",
            "tier": "mid_market",
            "arr": 60000.0,
            "mrr": 5000.0,
        })
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Beta Corp"
        assert body["arr"] == 60000.0
        assert body["tier"] == "mid_market"
        assert body["id"] > 0

    def test_list_accounts_empty_then_populated(self, client):
        r = client.get("/cs/accounts", headers=MGR)
        assert r.status_code == 200
        assert r.json()["total"] == 0
        _make_account(client)
        r = client.get("/cs/accounts", headers=MGR)
        assert r.json()["total"] == 1

    def test_get_account(self, client):
        a = _make_account(client)
        r = client.get(f"/cs/accounts/{a['id']}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["name"] == "Acme Customer"

    def test_get_account_not_found(self, client):
        assert client.get("/cs/accounts/9999", headers=MGR).status_code == 404

    def test_patch_account(self, client):
        a = _make_account(client)
        r = client.patch(f"/cs/accounts/{a['id']}", headers=MGR, json={"arr": 200000.0, "status": "at_risk"})
        assert r.status_code == 200
        assert r.json()["arr"] == 200000.0
        assert r.json()["status"] == "at_risk"

    def test_delete_account(self, client):
        a = _make_account(client)
        r = client.delete(f"/cs/accounts/{a['id']}", headers=MGR)
        assert r.status_code == 204
        assert client.get(f"/cs/accounts/{a['id']}", headers=MGR).status_code == 404

    def test_filter_by_status(self, client):
        _make_account(client, status="active", name="Active Co")
        _make_account(client, status="at_risk", name="At Risk Co")
        r = client.get("/cs/accounts?status=at_risk", headers=MGR)
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["status"] == "at_risk"

    def test_filter_by_tier(self, client):
        _make_account(client, tier="strategic", name="Strategic Co")
        _make_account(client, tier="smb", name="SMB Co")
        r = client.get("/cs/accounts?tier=strategic", headers=MGR)
        assert r.json()["total"] == 1

    def test_filter_by_lifecycle_stage(self, client):
        _make_account(client, lifecycle_stage="onboarding", name="New Customer")
        _make_account(client, lifecycle_stage="renewal", name="Renewal Customer")
        r = client.get("/cs/accounts?lifecycle_stage=onboarding", headers=MGR)
        assert r.json()["total"] == 1

    def test_pagination(self, client):
        for i in range(5):
            _make_account(client, name=f"Customer {i}")
        r = client.get("/cs/accounts?limit=3&offset=0", headers=MGR)
        assert len(r.json()["items"]) == 3
        assert r.json()["total"] == 5

    def test_member_can_read_accounts(self, client):
        _make_account(client)
        r = client.get("/cs/accounts", headers=MEM)
        assert r.status_code == 200


# =====================================================================
# Customer Contacts
# =====================================================================
class TestContacts:
    def test_create_contact(self, client):
        a = _make_account(client)
        r = client.post("/cs/contacts", headers=MGR, json={
            "account_id": a["id"],
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@acme.com",
            "role": "primary",
            "is_primary": True,
        })
        assert r.status_code == 201
        body = r.json()
        assert body["first_name"] == "Jane"
        assert body["role"] == "primary"
        assert body["is_primary"] is True

    def test_list_contacts_empty(self, client):
        a = _make_account(client)
        r = client.get(f"/cs/accounts/{a['id']}/contacts", headers=MGR)
        assert r.status_code == 200
        assert r.json() == []

    def test_list_contacts(self, client):
        a = _make_account(client)
        client.post("/cs/contacts", headers=MGR, json={
            "account_id": a["id"], "first_name": "A", "role": "primary",
        })
        client.post("/cs/contacts", headers=MGR, json={
            "account_id": a["id"], "first_name": "B", "role": "technical",
        })
        r = client.get(f"/cs/accounts/{a['id']}/contacts", headers=MGR)
        assert len(r.json()) == 2

    def test_patch_contact(self, client):
        a = _make_account(client)
        c = client.post("/cs/contacts", headers=MGR, json={
            "account_id": a["id"], "first_name": "Old", "role": "primary",
        }).json()
        r = client.patch(f"/cs/contacts/{c['id']}", headers=MGR, json={"first_name": "New"})
        assert r.status_code == 200
        assert r.json()["first_name"] == "New"

    def test_delete_contact(self, client):
        a = _make_account(client)
        c = client.post("/cs/contacts", headers=MGR, json={
            "account_id": a["id"], "first_name": "Temp", "role": "technical",
        }).json()
        r = client.delete(f"/cs/contacts/{c['id']}", headers=MGR)
        assert r.status_code == 204

    def test_contact_roles(self, client):
        a = _make_account(client)
        for role in ["primary", "executive_sponsor", "technical", "procurement"]:
            r = client.post("/cs/contacts", headers=MGR, json={
                "account_id": a["id"], "first_name": role, "role": role,
            })
            assert r.status_code == 201


# =====================================================================
# Health Scoring
# =====================================================================
class TestHealthScoring:
    def _signals(self, **overrides) -> dict:
        base = {
            "product_adoption": 80.0,
            "meeting_activity": 70.0,
            "email_activity": 60.0,
            "opportunity_activity": 75.0,
            "open_issues": 90.0,
            "renewal_status": 85.0,
            "executive_engagement": 65.0,
        }
        base.update(overrides)
        return base

    def test_score_account(self, client):
        a = _make_account(client)
        r = client.post(f"/cs/accounts/{a['id']}/health", headers=MGR, json=self._signals())
        assert r.status_code == 201
        body = r.json()
        assert "score" in body
        assert body["grade"] in ("A", "B", "C", "D", "F")
        assert body["trend"] in ("up", "stable", "down")
        assert 0 <= body["score"] <= 100

    def test_high_signals_yield_high_grade(self, client):
        a = _make_account(client)
        r = client.post(f"/cs/accounts/{a['id']}/health", headers=MGR, json=self._signals(
            product_adoption=100, meeting_activity=100, email_activity=100,
            opportunity_activity=100, open_issues=100, renewal_status=100,
            executive_engagement=100,
        ))
        assert r.json()["grade"] == "A"

    def test_low_signals_yield_low_grade(self, client):
        a = _make_account(client)
        r = client.post(f"/cs/accounts/{a['id']}/health", headers=MGR, json=self._signals(
            product_adoption=0, meeting_activity=0, email_activity=0,
            opportunity_activity=0, open_issues=0, renewal_status=0,
            executive_engagement=0,
        ))
        assert r.json()["grade"] == "F"

    def test_get_latest_health(self, client):
        a = _make_account(client)
        client.post(f"/cs/accounts/{a['id']}/health", headers=MGR, json=self._signals())
        r = client.get(f"/cs/accounts/{a['id']}/health", headers=MGR)
        assert r.status_code == 200
        assert "score" in r.json()

    def test_get_health_not_found(self, client):
        a = _make_account(client)
        r = client.get(f"/cs/accounts/{a['id']}/health", headers=MGR)
        assert r.status_code == 404

    def test_health_history(self, client):
        a = _make_account(client)
        client.post(f"/cs/accounts/{a['id']}/health", headers=MGR, json=self._signals())
        client.post(f"/cs/accounts/{a['id']}/health", headers=MGR, json=self._signals(product_adoption=50))
        r = client.get(f"/cs/accounts/{a['id']}/health/history", headers=MGR)
        assert len(r.json()) == 2

    def test_trend_computed_on_second_score(self, client):
        a = _make_account(client)
        # First score
        client.post(f"/cs/accounts/{a['id']}/health", headers=MGR, json=self._signals(
            product_adoption=20, meeting_activity=20, email_activity=20,
            opportunity_activity=20, open_issues=20, renewal_status=20, executive_engagement=20,
        ))
        # Second score much higher → trend should be "up"
        r = client.post(f"/cs/accounts/{a['id']}/health", headers=MGR, json=self._signals(
            product_adoption=100, meeting_activity=100, email_activity=100,
            opportunity_activity=100, open_issues=100, renewal_status=100, executive_engagement=100,
        ))
        assert r.json()["trend"] == "up"

    def test_account_out_includes_health(self, client):
        a = _make_account(client)
        client.post(f"/cs/accounts/{a['id']}/health", headers=MGR, json=self._signals())
        r = client.get(f"/cs/accounts/{a['id']}", headers=MGR)
        assert r.json()["health_score"] is not None
        assert r.json()["health_grade"] is not None


# =====================================================================
# Lifecycle Management
# =====================================================================
class TestLifecycle:
    def test_lifecycle_event_on_create(self, client):
        a = _make_account(client, lifecycle_stage="onboarding")
        r = client.get(f"/cs/accounts/{a['id']}/lifecycle", headers=MGR)
        assert r.status_code == 200
        events = r.json()
        assert len(events) == 1
        assert events[0]["stage"] == "onboarding"

    def test_lifecycle_event_on_stage_change(self, client):
        a = _make_account(client, lifecycle_stage="customer")
        client.patch(f"/cs/accounts/{a['id']}", headers=MGR, json={"lifecycle_stage": "renewal"})
        r = client.get(f"/cs/accounts/{a['id']}/lifecycle", headers=MGR)
        assert len(r.json()) == 2
        stages = {e["stage"] for e in r.json()}
        assert "renewal" in stages

    def test_no_duplicate_lifecycle_event_on_same_stage(self, client):
        a = _make_account(client, lifecycle_stage="customer")
        # Patch with the same stage → no new lifecycle event
        client.patch(f"/cs/accounts/{a['id']}", headers=MGR, json={"lifecycle_stage": "customer"})
        r = client.get(f"/cs/accounts/{a['id']}/lifecycle", headers=MGR)
        assert len(r.json()) == 1

    def test_lifecycle_ordering(self, client):
        a = _make_account(client, lifecycle_stage="customer")
        client.patch(f"/cs/accounts/{a['id']}", headers=MGR, json={"lifecycle_stage": "renewal"})
        client.patch(f"/cs/accounts/{a['id']}", headers=MGR, json={"lifecycle_stage": "expansion"})
        events = client.get(f"/cs/accounts/{a['id']}/lifecycle", headers=MGR).json()
        # Most recent first
        assert events[0]["stage"] == "expansion"


# =====================================================================
# Contracts & Renewals
# =====================================================================
class TestContracts:
    def test_create_contract(self, client):
        a = _make_account(client)
        r = client.post("/cs/contracts", headers=MGR, json={
            "account_id": a["id"],
            "name": "Enterprise License 2026",
            "status": "active",
            "value": 120000.0,
            "currency": "USD",
            "renewal_probability": 0.8,
        })
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Enterprise License 2026"
        assert body["value"] == 120000.0

    def test_list_contracts_empty(self, client):
        r = client.get("/cs/contracts", headers=MGR)
        assert r.json()["total"] == 0

    def test_list_contracts_for_account(self, client):
        a = _make_account(client)
        client.post("/cs/contracts", headers=MGR, json={
            "account_id": a["id"], "name": "C1", "value": 100.0,
        })
        client.post("/cs/contracts", headers=MGR, json={
            "account_id": a["id"], "name": "C2", "value": 200.0,
        })
        r = client.get(f"/cs/contracts?account_id={a['id']}", headers=MGR)
        assert r.json()["total"] == 2

    def test_filter_contracts_by_status(self, client):
        a = _make_account(client)
        client.post("/cs/contracts", headers=MGR, json={
            "account_id": a["id"], "name": "Active", "status": "active",
        })
        client.post("/cs/contracts", headers=MGR, json={
            "account_id": a["id"], "name": "Expired", "status": "expired",
        })
        r = client.get("/cs/contracts?status=expired", headers=MGR)
        assert r.json()["total"] == 1

    def test_patch_contract(self, client):
        a = _make_account(client)
        c = client.post("/cs/contracts", headers=MGR, json={
            "account_id": a["id"], "name": "Contract", "status": "active",
        }).json()
        r = client.patch(f"/cs/contracts/{c['id']}", headers=MGR, json={
            "status": "pending_renewal", "renewal_probability": 0.9,
        })
        assert r.status_code == 200
        assert r.json()["status"] == "pending_renewal"

    def test_delete_contract(self, client):
        a = _make_account(client)
        c = client.post("/cs/contracts", headers=MGR, json={
            "account_id": a["id"], "name": "Temp Contract",
        }).json()
        r = client.delete(f"/cs/contracts/{c['id']}", headers=MGR)
        assert r.status_code == 204


# =====================================================================
# Success Plans & Milestones
# =====================================================================
class TestSuccessPlans:
    def test_create_plan(self, client):
        a = _make_account(client)
        r = client.post("/cs/plans", headers=MGR, json={
            "account_id": a["id"],
            "name": "Q3 Success Plan",
            "status": "active",
            "goals": [{"goal": "Deploy to production", "target_date": "2026-09-30"}],
        })
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Q3 Success Plan"
        assert len(body["goals"]) == 1

    def test_list_plans_empty(self, client):
        a = _make_account(client)
        r = client.get(f"/cs/accounts/{a['id']}/plans", headers=MGR)
        assert r.json() == []

    def test_list_plans(self, client):
        a = _make_account(client)
        client.post("/cs/plans", headers=MGR, json={"account_id": a["id"], "name": "Plan 1"})
        client.post("/cs/plans", headers=MGR, json={"account_id": a["id"], "name": "Plan 2"})
        r = client.get(f"/cs/accounts/{a['id']}/plans", headers=MGR)
        assert len(r.json()) == 2

    def test_patch_plan(self, client):
        a = _make_account(client)
        p = client.post("/cs/plans", headers=MGR, json={
            "account_id": a["id"], "name": "Draft Plan", "status": "draft",
        }).json()
        r = client.patch(f"/cs/plans/{p['id']}", headers=MGR, json={"status": "active"})
        assert r.json()["status"] == "active"

    def test_delete_plan(self, client):
        a = _make_account(client)
        p = client.post("/cs/plans", headers=MGR, json={
            "account_id": a["id"], "name": "Temp Plan",
        }).json()
        r = client.delete(f"/cs/plans/{p['id']}", headers=MGR)
        assert r.status_code == 204

    def test_create_milestone(self, client):
        a = _make_account(client)
        p = client.post("/cs/plans", headers=MGR, json={
            "account_id": a["id"], "name": "Plan",
        }).json()
        r = client.post("/cs/milestones", headers=MGR, json={
            "plan_id": p["id"],
            "account_id": a["id"],
            "name": "Initial Setup Complete",
            "status": "pending",
        })
        assert r.status_code == 201
        assert r.json()["name"] == "Initial Setup Complete"

    def test_list_milestones(self, client):
        a = _make_account(client)
        p = client.post("/cs/plans", headers=MGR, json={
            "account_id": a["id"], "name": "Plan",
        }).json()
        client.post("/cs/milestones", headers=MGR, json={
            "plan_id": p["id"], "account_id": a["id"], "name": "M1",
        })
        client.post("/cs/milestones", headers=MGR, json={
            "plan_id": p["id"], "account_id": a["id"], "name": "M2",
        })
        r = client.get(f"/cs/plans/{p['id']}/milestones", headers=MGR)
        assert len(r.json()) == 2

    def test_complete_milestone_sets_completed_at(self, client):
        a = _make_account(client)
        p = client.post("/cs/plans", headers=MGR, json={
            "account_id": a["id"], "name": "Plan",
        }).json()
        m = client.post("/cs/milestones", headers=MGR, json={
            "plan_id": p["id"], "account_id": a["id"], "name": "Deploy",
        }).json()
        r = client.patch(f"/cs/milestones/{m['id']}", headers=MGR, json={"status": "completed"})
        assert r.json()["status"] == "completed"
        assert r.json()["completed_at"] is not None

    def test_delete_milestone(self, client):
        a = _make_account(client)
        p = client.post("/cs/plans", headers=MGR, json={
            "account_id": a["id"], "name": "Plan",
        }).json()
        m = client.post("/cs/milestones", headers=MGR, json={
            "plan_id": p["id"], "account_id": a["id"], "name": "MS",
        }).json()
        assert client.delete(f"/cs/milestones/{m['id']}", headers=MGR).status_code == 204


# =====================================================================
# Risks
# =====================================================================
class TestRisks:
    def test_create_risk(self, client):
        a = _make_account(client)
        r = client.post("/cs/risks", headers=MGR, json={
            "account_id": a["id"],
            "title": "Champion left the company",
            "severity": "high",
            "status": "open",
        })
        assert r.status_code == 201
        body = r.json()
        assert body["severity"] == "high"
        assert body["status"] == "open"

    def test_list_risks_empty(self, client):
        a = _make_account(client)
        r = client.get(f"/cs/accounts/{a['id']}/risks", headers=MGR)
        assert r.json() == []

    def test_list_risks(self, client):
        a = _make_account(client)
        client.post("/cs/risks", headers=MGR, json={
            "account_id": a["id"], "title": "Risk 1", "severity": "low",
        })
        client.post("/cs/risks", headers=MGR, json={
            "account_id": a["id"], "title": "Risk 2", "severity": "critical",
        })
        r = client.get(f"/cs/accounts/{a['id']}/risks", headers=MGR)
        assert len(r.json()) == 2

    def test_filter_risks_by_status(self, client):
        a = _make_account(client)
        client.post("/cs/risks", headers=MGR, json={
            "account_id": a["id"], "title": "Open Risk", "status": "open",
        })
        client.post("/cs/risks", headers=MGR, json={
            "account_id": a["id"], "title": "Closed Risk", "status": "closed",
        })
        r = client.get(f"/cs/accounts/{a['id']}/risks?status=open", headers=MGR)
        assert len(r.json()) == 1

    def test_patch_risk_to_mitigated_sets_resolved_at(self, client):
        a = _make_account(client)
        r_create = client.post("/cs/risks", headers=MGR, json={
            "account_id": a["id"], "title": "Bug Risk", "severity": "medium",
        })
        risk = r_create.json()
        r = client.patch(f"/cs/risks/{risk['id']}", headers=MGR, json={"status": "mitigated"})
        assert r.json()["status"] == "mitigated"
        assert r.json()["resolved_at"] is not None

    def test_delete_risk(self, client):
        a = _make_account(client)
        r_create = client.post("/cs/risks", headers=MGR, json={
            "account_id": a["id"], "title": "Temp Risk",
        })
        risk = r_create.json()
        assert client.delete(f"/cs/risks/{risk['id']}", headers=MGR).status_code == 204


# =====================================================================
# Customer Timeline
# =====================================================================
class TestTimeline:
    def test_timeline_structure(self, client):
        a = _make_account(client)
        r = client.get(f"/cs/accounts/{a['id']}/timeline", headers=MGR)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_timeline_includes_lifecycle_events(self, client):
        a = _make_account(client, lifecycle_stage="onboarding")
        client.patch(f"/cs/accounts/{a['id']}", headers=MGR, json={"lifecycle_stage": "adoption"})
        events = client.get(f"/cs/accounts/{a['id']}/timeline", headers=MGR).json()
        lifecycle_events = [e for e in events if e["event_type"] == "lifecycle"]
        assert len(lifecycle_events) >= 2

    def test_timeline_ordered_desc(self, client):
        a = _make_account(client)
        client.patch(f"/cs/accounts/{a['id']}", headers=MGR, json={"lifecycle_stage": "renewal"})
        client.patch(f"/cs/accounts/{a['id']}", headers=MGR, json={"lifecycle_stage": "expansion"})
        events = client.get(f"/cs/accounts/{a['id']}/timeline", headers=MGR).json()
        if len(events) > 1:
            ts = [e["timestamp"] for e in events]
            assert ts == sorted(ts, reverse=True)

    def test_timeline_pagination(self, client):
        a = _make_account(client)
        r = client.get(f"/cs/accounts/{a['id']}/timeline?limit=5&offset=0", headers=MGR)
        assert r.status_code == 200
        assert len(r.json()) <= 5


# =====================================================================
# Customer Dashboard
# =====================================================================
class TestDashboard:
    def test_dashboard_structure(self, client):
        r = client.get("/cs/dashboard", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        for key in [
            "total_accounts", "active_accounts", "at_risk_accounts",
            "churned_accounts", "total_arr", "total_mrr",
            "renewals_due_90d", "open_risks", "expansion_accounts",
            "open_tasks", "upcoming_meetings",
        ]:
            assert key in body, f"missing key: {key}"

    def test_dashboard_counts_accounts(self, client):
        _make_account(client, status="active", name="A1")
        _make_account(client, status="active", name="A2")
        _make_account(client, status="at_risk", name="AR")
        body = client.get("/cs/dashboard", headers=MGR).json()
        assert body["total_accounts"] == 3
        assert body["at_risk_accounts"] == 1

    def test_dashboard_sums_arr(self, client):
        _make_account(client, arr=100000.0, name="C1")
        _make_account(client, arr=50000.0, name="C2")
        body = client.get("/cs/dashboard", headers=MGR).json()
        assert body["total_arr"] == 150000.0

    def test_dashboard_open_risks(self, client):
        a = _make_account(client)
        client.post("/cs/risks", headers=MGR, json={
            "account_id": a["id"], "title": "Open Risk",
        })
        body = client.get("/cs/dashboard", headers=MGR).json()
        assert body["open_risks"] >= 1

    def test_dashboard_avg_health(self, client):
        a = _make_account(client)
        client.post(f"/cs/accounts/{a['id']}/health", headers=MGR, json={
            "product_adoption": 80, "meeting_activity": 80, "email_activity": 80,
            "opportunity_activity": 80, "open_issues": 80, "renewal_status": 80,
            "executive_engagement": 80,
        })
        body = client.get("/cs/dashboard", headers=MGR).json()
        assert body["avg_health_score"] is not None

    def test_member_can_see_dashboard(self, client):
        assert client.get("/cs/dashboard", headers=MEM).status_code == 200


# =====================================================================
# Analytics
# =====================================================================
class TestAnalytics:
    def test_analytics_structure(self, client):
        r = client.get("/cs/analytics", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        for key in [
            "total_arr", "total_mrr", "active_count", "churn_rate",
            "renewal_rate", "avg_health_score", "health_distribution",
            "expansion_account_count", "by_status",
        ]:
            assert key in body, f"missing key: {key}"

    def test_analytics_churn_rate_zero_with_no_churned(self, client):
        _make_account(client, status="active")
        body = client.get("/cs/analytics", headers=MGR).json()
        assert body["churn_rate"] == 0.0
        assert body["renewal_rate"] == 1.0

    def test_analytics_churn_rate_nonzero(self, client):
        _make_account(client, status="active", name="Active")
        _make_account(client, status="churned", name="Churned")
        body = client.get("/cs/analytics", headers=MGR).json()
        assert body["churn_rate"] == 0.5

    def test_analytics_health_distribution(self, client):
        a1 = _make_account(client, name="C1")
        a2 = _make_account(client, name="C2")
        client.post(f"/cs/accounts/{a1['id']}/health", headers=MGR, json={
            "product_adoption": 100, "meeting_activity": 100, "email_activity": 100,
            "opportunity_activity": 100, "open_issues": 100, "renewal_status": 100,
            "executive_engagement": 100,
        })
        client.post(f"/cs/accounts/{a2['id']}/health", headers=MGR, json={
            "product_adoption": 0, "meeting_activity": 0, "email_activity": 0,
            "opportunity_activity": 0, "open_issues": 0, "renewal_status": 0,
            "executive_engagement": 0,
        })
        body = client.get("/cs/analytics", headers=MGR).json()
        assert "A" in body["health_distribution"]
        assert "F" in body["health_distribution"]

    def test_analytics_expansion_count(self, client):
        _make_account(client, lifecycle_stage="expansion", name="Expand")
        body = client.get("/cs/analytics", headers=MGR).json()
        assert body["expansion_account_count"] >= 1

    def test_analytics_arr_sum(self, client):
        _make_account(client, arr=200000.0, name="Big")
        body = client.get("/cs/analytics", headers=MGR).json()
        assert body["total_arr"] == 200000.0

    def test_member_can_view_analytics(self, client):
        assert client.get("/cs/analytics", headers=MEM).status_code == 200


# =====================================================================
# Backward Compatibility
# =====================================================================
class TestBackwardCompatibility:
    def test_deals_still_work(self, client):
        assert client.get("/deals", headers=MGR).status_code == 200

    def test_campaigns_still_work(self, client):
        assert client.get("/campaigns", headers=MGR).status_code == 200

    def test_team_assignments_still_work(self, client):
        assert client.get("/team/work-queue", headers=MGR).status_code == 200

    def test_outreach_still_works(self, client):
        assert client.get("/outreach/leads", headers=MGR).status_code == 200

    def test_legacy_assignments_still_work(self, client):
        assert client.get("/assignments", headers=MGR).status_code == 200
