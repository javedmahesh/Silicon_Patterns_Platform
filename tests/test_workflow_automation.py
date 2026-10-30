"""Enterprise CRM Phase 6: Workflow Automation & Business Process Engine tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from backend.workflow_service import evaluate_conditions
from master_db.models import Base, Company, CsContract

MGR = {"X-Dev-Role": "manager"}
MEM = {"X-Dev-Role": "member"}

DEFAULT_STAGES = [
    {"name": "Prospect", "stage_type": "open",  "stage_order": 1, "probability": 10},
    {"name": "Won",       "stage_type": "won",  "stage_order": 2, "probability": 100},
    {"name": "Lost",      "stage_type": "lost", "stage_order": 3, "probability": 0},
]


def _seed(s):
    s.add(Company(
        company_domain="acme.com", canonical_company_id="ACME",
        company_name="Acme Corp", name_key="acme",
        prospect_type="PRODUCT_COMPANY", validation_status="VALID",
        company_tier="INCUMBENT",
    ))
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'workflows.db').as_posix()}",
        log_json=False, dev_auth_bypass=True,
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _uid(client, headers=MGR) -> int:
    return client.get("/auth/me", headers=headers).json()["id"]


def _make_pipeline(client):
    return client.post("/pipelines", headers=MGR, json={"name": "P", "stages": DEFAULT_STAGES}).json()


def _stages(p):
    return {s["stage_type"]: s for s in p["stages"]}


def _make_workflow(client, **kw):
    payload = {
        "name": "Test Workflow",
        "trigger_event": "deal_created",
        "conditions": {"logic": "AND", "groups": []},
        "actions": [],
        "status": "active",
        "is_enabled": True,
        **kw,
    }
    return client.post("/workflows", headers=MGR, json=payload).json()


def _make_deal(client, pipeline_id, stage_id, **kw):
    payload = {
        "title": kw.get("title", "Deal"),
        "company_domain": kw.get("company_domain", "acme.com"),
        "pipeline_id": pipeline_id,
        "stage_id": stage_id,
        "value": kw.get("value", 50_000.0),
        "probability": kw.get("probability", 25),
    }
    return client.post("/deals", headers=MGR, json=payload).json()


# =====================================================================
# Workflow CRUD
# =====================================================================
class TestWorkflowCRUD:
    def test_create_workflow(self, client):
        w = _make_workflow(client)
        assert w["id"] > 0
        assert w["status"] == "active"
        assert w["version"] == 1

    def test_create_workflow_manager_only(self, client):
        r = client.post("/workflows", headers=MEM, json={
            "name": "X", "trigger_event": "deal_created", "conditions": {}, "actions": [],
        })
        assert r.status_code == 403

    def test_list_workflows(self, client):
        _make_workflow(client, name="W1")
        _make_workflow(client, name="W2")
        r = client.get("/workflows", headers=MGR)
        assert r.json()["total"] == 2

    def test_list_filter_by_trigger(self, client):
        _make_workflow(client, trigger_event="deal_created")
        _make_workflow(client, trigger_event="deal_won")
        r = client.get("/workflows?trigger_event=deal_won", headers=MGR)
        assert r.json()["total"] == 1

    def test_get_workflow(self, client):
        w = _make_workflow(client)
        r = client.get(f"/workflows/{w['id']}", headers=MGR)
        assert r.status_code == 200
        assert r.json()["name"] == "Test Workflow"

    def test_get_workflow_not_found(self, client):
        assert client.get("/workflows/9999", headers=MGR).status_code == 404

    def test_patch_workflow_bumps_version(self, client):
        w = _make_workflow(client)
        r = client.patch(f"/workflows/{w['id']}", headers=MGR, json={"status": "paused"})
        assert r.status_code == 200
        assert r.json()["status"] == "paused"
        assert r.json()["version"] == 2

    def test_patch_workflow_manager_only(self, client):
        w = _make_workflow(client)
        assert client.patch(f"/workflows/{w['id']}", headers=MEM, json={"status": "paused"}).status_code == 403

    def test_delete_workflow(self, client):
        w = _make_workflow(client)
        assert client.delete(f"/workflows/{w['id']}", headers=MGR).status_code == 204
        assert client.get(f"/workflows/{w['id']}", headers=MGR).status_code == 404

    def test_delete_workflow_manager_only(self, client):
        w = _make_workflow(client)
        assert client.delete(f"/workflows/{w['id']}", headers=MEM).status_code == 403


# =====================================================================
# Condition Evaluation (pure function, unit-level)
# =====================================================================
class TestConditionEvaluation:
    def test_no_conditions_always_matches(self):
        assert evaluate_conditions({"value": 1}, {}) is True
        assert evaluate_conditions({"value": 1}, {"groups": []}) is True

    def test_single_rule_gte(self):
        conditions = {"groups": [{"logic": "AND", "rules": [{"field": "value", "op": "gte", "value": 100}]}]}
        assert evaluate_conditions({"value": 150}, conditions) is True
        assert evaluate_conditions({"value": 50}, conditions) is False

    def test_and_group_all_must_match(self):
        conditions = {"groups": [{"logic": "AND", "rules": [
            {"field": "value", "op": "gte", "value": 100},
            {"field": "tier", "op": "eq", "value": "enterprise"},
        ]}]}
        assert evaluate_conditions({"value": 150, "tier": "enterprise"}, conditions) is True
        assert evaluate_conditions({"value": 150, "tier": "smb"}, conditions) is False

    def test_or_group_any_matches(self):
        conditions = {"groups": [{"logic": "OR", "rules": [
            {"field": "tier", "op": "eq", "value": "enterprise"},
            {"field": "tier", "op": "eq", "value": "strategic"},
        ]}]}
        assert evaluate_conditions({"tier": "strategic"}, conditions) is True
        assert evaluate_conditions({"tier": "smb"}, conditions) is False

    def test_top_level_or_between_groups(self):
        conditions = {
            "logic": "OR",
            "groups": [
                {"logic": "AND", "rules": [{"field": "value", "op": "gte", "value": 1_000_000}]},
                {"logic": "AND", "rules": [{"field": "tier", "op": "eq", "value": "strategic"}]},
            ],
        }
        assert evaluate_conditions({"value": 10, "tier": "strategic"}, conditions) is True
        assert evaluate_conditions({"value": 10, "tier": "smb"}, conditions) is False

    def test_in_and_contains_ops(self):
        assert evaluate_conditions({"status": "won"}, {"groups": [{"rules": [
            {"field": "status", "op": "in", "value": ["won", "lost"]}
        ]}]}) is True
        assert evaluate_conditions({"tags": ["urgent", "vip"]}, {"groups": [{"rules": [
            {"field": "tags", "op": "contains", "value": "vip"}
        ]}]}) is True


# =====================================================================
# Trigger Execution (end-to-end via the real API)
# =====================================================================
class TestTriggerExecution:
    def test_deal_created_fires_workflow(self, client):
        _make_workflow(client, trigger_event="deal_created", actions=[
            {"type": "create_task", "params": {"title": "Follow up"}},
        ])
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        r = client.get("/workflows/executions/list", headers=MGR)
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["trigger_event"] == "deal_created"
        assert r.json()["items"][0]["status"] == "success"

    def test_deal_created_condition_gate(self, client):
        _make_workflow(client, trigger_event="deal_created", conditions={
            "groups": [{"rules": [{"field": "value", "op": "gte", "value": 999_999}]}]
        })
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"], value=1_000.0)
        r = client.get("/workflows/executions/list", headers=MGR)
        assert r.json()["total"] == 0

    def test_deal_won_fires_on_move_to_won_stage(self, client):
        _make_workflow(client, trigger_event="deal_won")
        _make_workflow(client, trigger_event="deal_stage_changed")
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        client.post(f"/deals/{d['id']}/move", headers=MGR, json={"stage_id": st["won"]["id"]})
        r = client.get("/workflows/executions/list?entity_type=deal", headers=MGR)
        events = {e["trigger_event"] for e in r.json()["items"]}
        assert "deal_won" in events
        assert "deal_stage_changed" in events

    def test_deal_lost_fires_on_move_to_lost_stage(self, client):
        _make_workflow(client, trigger_event="deal_lost")
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        client.post(f"/deals/{d['id']}/move", headers=MGR, json={"stage_id": st["lost"]["id"]})
        r = client.get("/workflows/executions/list", headers=MGR)
        events = {e["trigger_event"] for e in r.json()["items"]}
        assert "deal_lost" in events

    def test_customer_created_fires_workflow(self, client):
        _make_workflow(client, trigger_event="customer_created")
        client.post("/cs/accounts", headers=MGR, json={
            "name": "Acme CS", "company_domain": "acme.com", "tier": "enterprise",
        })
        r = client.get("/workflows/executions/list", headers=MGR)
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["trigger_event"] == "customer_created"

    def test_health_changed_fires_on_grade_change(self, client):
        _make_workflow(client, trigger_event="health_changed")
        acct = client.post("/cs/accounts", headers=MGR, json={
            "name": "Acme CS", "company_domain": "acme.com", "tier": "enterprise",
        }).json()
        client.post(f"/cs/accounts/{acct['id']}/health", headers=MGR, json={
            "product_adoption": 90, "meeting_activity": 90, "email_activity": 90,
            "opportunity_activity": 90, "open_issues": 0, "renewal_status": 90,
            "executive_engagement": 90,
        })
        r = client.get("/workflows/executions/list", headers=MGR)
        assert r.json()["total"] == 1

    def test_task_completed_fires_workflow(self, client):
        _make_workflow(client, trigger_event="task_completed")
        task = client.post("/outreach/tasks", headers=MGR, json={
            "title": "Call customer", "company_domain": "acme.com",
        }).json()
        client.patch(f"/outreach/tasks/{task['id']}", headers=MGR, json={"status": "completed"})
        r = client.get("/workflows/executions/list", headers=MGR)
        assert r.json()["total"] == 1

    def test_meeting_completed_fires_workflow(self, client):
        _make_workflow(client, trigger_event="meeting_completed")
        meeting = client.post("/outreach/meetings", headers=MGR, json={
            "company_domain": "acme.com", "meeting_type": "call",
            "scheduled_at": "2030-01-01T10:00:00Z",
        }).json()
        client.patch(f"/outreach/meetings/{meeting['id']}", headers=MGR, json={"outcome": "positive"})
        r = client.get("/workflows/executions/list", headers=MGR)
        assert r.json()["total"] == 1

    def test_campaign_status_changed_fires_workflow(self, client):
        _make_workflow(client, trigger_event="campaign_status_changed")
        camp = client.post("/campaigns", headers=MGR, json={"name": "Q1"}).json()
        client.patch(f"/campaigns/{camp['id']}", headers=MGR, json={"status": "active"})
        r = client.get("/workflows/executions/list", headers=MGR)
        assert r.json()["total"] == 1

    def test_lead_created_fires_workflow(self, client):
        _make_workflow(client, trigger_event="lead_created")
        uid = _uid(client, MEM)
        client.post("/assignments", headers=MGR, json={
            "company_domain": "acme.com", "user_id": uid,
        })
        r = client.get("/workflows/executions/list", headers=MGR)
        assert r.json()["total"] == 1

    def test_paused_workflow_does_not_fire(self, client):
        _make_workflow(client, trigger_event="deal_created", status="paused")
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        r = client.get("/workflows/executions/list", headers=MGR)
        assert r.json()["total"] == 0

    def test_disabled_workflow_does_not_fire(self, client):
        _make_workflow(client, trigger_event="deal_created", is_enabled=False)
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        r = client.get("/workflows/executions/list", headers=MGR)
        assert r.json()["total"] == 0


# =====================================================================
# Action Execution
# =====================================================================
class TestActionExecution:
    def test_create_task_action(self, client):
        _make_workflow(client, trigger_event="deal_created", actions=[
            {"type": "create_task", "params": {"title": "Do thing", "priority": "high"}},
        ])
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        exe = client.get("/workflows/executions/list", headers=MGR).json()["items"][0]
        assert exe["actions_executed"][0]["type"] == "create_task"
        assert exe["actions_executed"][0]["ok"] is True
        tasks = client.get("/outreach/tasks", headers=MGR).json()
        assert tasks["total"] == 1

    def test_assign_owner_action_on_deal(self, client):
        uid = _uid(client, MGR)
        _make_workflow(client, trigger_event="deal_created", actions=[
            {"type": "assign_owner", "params": {"user_id": uid, "role": "reviewer"}},
        ])
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        exe = client.get("/workflows/executions/list", headers=MGR).json()["items"][0]
        assert exe["actions_executed"][0]["ok"] is True
        assert "reviewer" in exe["actions_executed"][0]["detail"] or "assigned" in exe["actions_executed"][0]["detail"]

    def test_assign_owner_action_on_customer(self, client):
        uid = _uid(client, MGR)
        _make_workflow(client, trigger_event="customer_created", actions=[
            {"type": "assign_owner", "params": {"user_id": uid}},
        ])
        acct = client.post("/cs/accounts", headers=MGR, json={
            "name": "Acme CS", "company_domain": "acme.com",
        }).json()
        exe = client.get("/workflows/executions/list", headers=MGR).json()["items"][0]
        assert exe["actions_executed"][0]["ok"] is True
        got = client.get(f"/cs/accounts/{acct['id']}", headers=MGR).json()
        assert got["owner_id"] == uid

    def test_send_notification_action(self, client):
        uid = _uid(client, MGR)
        _make_workflow(client, trigger_event="deal_created", actions=[
            {"type": "send_notification", "params": {"user_id": uid, "title": "Big deal!"}},
        ])
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        exe = client.get("/workflows/executions/list", headers=MGR).json()["items"][0]
        assert exe["actions_executed"][0]["ok"] is True

    def test_update_fields_action_on_deal(self, client):
        _make_workflow(client, trigger_event="deal_created", actions=[
            {"type": "update_fields", "params": {"fields": {"notes": "auto-flagged"}}},
        ])
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        got = client.get(f"/deals/{d['id']}", headers=MGR).json()
        assert got["notes"] == "auto-flagged"

    def test_create_activity_action_on_deal(self, client):
        _make_workflow(client, trigger_event="deal_created", actions=[
            {"type": "create_activity", "params": {"detail": "auto note"}},
        ])
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        exe = client.get("/workflows/executions/list", headers=MGR).json()["items"][0]
        assert exe["actions_executed"][0]["ok"] is True

    def test_create_deal_action(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        _make_workflow(client, trigger_event="customer_created", actions=[
            {"type": "create_deal", "params": {"pipeline_id": p["id"], "stage_id": st["open"]["id"], "value": 1000}},
        ])
        client.post("/cs/accounts", headers=MGR, json={"name": "Acme CS", "company_domain": "acme.com"})
        deals = client.get("/deals", headers=MGR).json()
        assert deals["total"] == 1

    def test_create_opportunity_action_is_documented_noop(self, client):
        _make_workflow(client, trigger_event="deal_created", actions=[
            {"type": "create_opportunity", "params": {}},
        ])
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        exe = client.get("/workflows/executions/list", headers=MGR).json()["items"][0]
        assert exe["actions_executed"][0]["ok"] is False
        assert exe["status"] == "failed"

    def test_multiple_actions_partial_status(self, client):
        _make_workflow(client, trigger_event="deal_created", actions=[
            {"type": "create_task", "params": {"title": "ok action"}},
            {"type": "create_opportunity", "params": {}},
        ])
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        exe = client.get("/workflows/executions/list", headers=MGR).json()["items"][0]
        assert exe["status"] == "partial"

    def test_follow_up_and_reminder_and_success_task_create_tasks(self, client):
        _make_workflow(client, trigger_event="deal_created", actions=[
            {"type": "create_follow_up", "params": {}},
            {"type": "schedule_reminder", "params": {"remind_in_hours": 48}},
            {"type": "create_success_task", "params": {}},
        ])
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        tasks = client.get("/outreach/tasks", headers=MGR).json()
        assert tasks["total"] == 3


# =====================================================================
# Approval Workflows
# =====================================================================
class TestApprovalWorkflows:
    def test_create_approval_request(self, client):
        r = client.post("/workflows/approvals", headers=MGR, json={
            "approval_type": "large_deal", "entity_type": "deal", "entity_id": "1",
        })
        assert r.status_code == 201
        assert r.json()["status"] == "pending"

    def test_list_approvals(self, client):
        client.post("/workflows/approvals", headers=MGR, json={"approval_type": "discount"})
        r = client.get("/workflows/approvals/list", headers=MGR)
        assert r.json()["total"] == 1

    def test_list_filter_by_status(self, client):
        client.post("/workflows/approvals", headers=MGR, json={"approval_type": "discount"})
        r = client.get("/workflows/approvals/list?status=pending", headers=MGR)
        assert r.json()["total"] == 1
        r2 = client.get("/workflows/approvals/list?status=approved", headers=MGR)
        assert r2.json()["total"] == 0

    def test_decide_approval_approved(self, client):
        a = client.post("/workflows/approvals", headers=MGR, json={"approval_type": "contract_change"}).json()
        r = client.post(f"/workflows/approvals/{a['id']}/decide", headers=MGR, json={
            "decision": "approved", "comments": "looks fine",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "approved"
        assert r.json()["decision_reason"] == "looks fine"
        assert r.json()["decided_at"] is not None

    def test_decide_approval_rejected(self, client):
        a = client.post("/workflows/approvals", headers=MGR, json={"approval_type": "customer_escalation"}).json()
        r = client.post(f"/workflows/approvals/{a['id']}/decide", headers=MGR, json={"decision": "rejected"})
        assert r.json()["status"] == "rejected"

    def test_cannot_decide_twice(self, client):
        a = client.post("/workflows/approvals", headers=MGR, json={"approval_type": "large_deal"}).json()
        client.post(f"/workflows/approvals/{a['id']}/decide", headers=MGR, json={"decision": "approved"})
        r = client.post(f"/workflows/approvals/{a['id']}/decide", headers=MGR, json={"decision": "rejected"})
        assert r.status_code == 409

    def test_member_cannot_decide_someone_elses_approval(self, client):
        mgr_uid = _uid(client, MGR)
        a = client.post("/workflows/approvals", headers=MGR, json={
            "approval_type": "large_deal", "approver_id": mgr_uid,
        }).json()
        r = client.post(f"/workflows/approvals/{a['id']}/decide", headers=MEM, json={"decision": "approved"})
        assert r.status_code == 403

    def test_get_approval_not_found(self, client):
        assert client.get("/workflows/approvals/9999", headers=MGR).status_code == 404


# =====================================================================
# SLA Management
# =====================================================================
class TestSlaManagement:
    def _make_policy(self, client, **kw):
        payload = {"name": "Response SLA", "entity_type": "deal", "due_hours": 24, **kw}
        return client.post("/workflows/sla/policies", headers=MGR, json=payload).json()

    def test_create_policy(self, client):
        p = self._make_policy(client)
        assert p["id"] > 0
        assert p["due_hours"] == 24

    def test_create_policy_manager_only(self, client):
        r = client.post("/workflows/sla/policies", headers=MEM, json={"name": "X", "due_hours": 24})
        assert r.status_code == 403

    def test_list_policies(self, client):
        self._make_policy(client)
        r = client.get("/workflows/sla/policies", headers=MGR)
        assert len(r.json()) == 1

    def test_patch_policy(self, client):
        p = self._make_policy(client)
        r = client.patch(f"/workflows/sla/policies/{p['id']}", headers=MGR, json={"due_hours": 48})
        assert r.json()["due_hours"] == 48

    def test_create_tracker_default_due_at(self, client):
        p = self._make_policy(client, due_hours=10)
        r = client.post("/workflows/sla/trackers", headers=MGR, json={
            "policy_id": p["id"], "entity_type": "deal", "entity_id": "1",
        })
        assert r.status_code == 201
        assert r.json()["status"] == "on_track"

    def test_tick_marks_breached(self, client):
        p = self._make_policy(client, due_hours=1)
        past = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        client.post("/workflows/sla/trackers", headers=MGR, json={
            "policy_id": p["id"], "entity_type": "deal", "entity_id": "1", "due_at": past,
        })
        r = client.post("/workflows/sla/tick", headers=MGR)
        assert r.json()["newly_breached"] == 1
        trackers = client.get("/workflows/sla/trackers?status=breached", headers=MGR).json()
        assert trackers["total"] == 1

    def test_tick_marks_at_risk(self, client):
        p = self._make_policy(client, due_hours=10)
        soon = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        client.post("/workflows/sla/trackers", headers=MGR, json={
            "policy_id": p["id"], "entity_type": "deal", "entity_id": "1", "due_at": soon,
        })
        r = client.post("/workflows/sla/tick", headers=MGR)
        assert r.json()["newly_at_risk"] == 1

    def test_tick_escalates_after_grace_period(self, client):
        uid = _uid(client, MGR)
        p = self._make_policy(client, due_hours=1, escalate_after_hours=1, escalate_to_user_id=uid)
        past = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        client.post("/workflows/sla/trackers", headers=MGR, json={
            "policy_id": p["id"], "entity_type": "deal", "entity_id": "1", "due_at": past,
        })
        r = client.post("/workflows/sla/tick", headers=MGR)
        assert r.json()["newly_breached"] == 1
        assert r.json()["newly_escalated"] == 1

    def test_resolve_tracker(self, client):
        p = self._make_policy(client)
        t = client.post("/workflows/sla/trackers", headers=MGR, json={
            "policy_id": p["id"], "entity_type": "deal", "entity_id": "1",
        }).json()
        r = client.post(f"/workflows/sla/trackers/{t['id']}/resolve", headers=MGR)
        assert r.json()["status"] == "resolved"
        assert r.json()["resolved_at"] is not None

    def test_scan_renewals_fires_workflow(self, client):
        _make_workflow(client, trigger_event="contract_renewal_window")
        acct = client.post("/cs/accounts", headers=MGR, json={
            "name": "Acme CS", "company_domain": "acme.com",
        }).json()
        with client.app.state.db.sessionmaker() as s:
            s.add(CsContract(
                account_id=acct["id"], name="Renewal", status="active", value=1000.0,
                end_date=datetime.now(timezone.utc) + timedelta(days=10),
            ))
            s.commit()
        r = client.post("/workflows/scan/renewals", headers=MGR)
        assert r.json()["workflows_fired"] == 1
        exec_r = client.get("/workflows/executions/list", headers=MGR)
        assert exec_r.json()["total"] == 1


# =====================================================================
# Dashboard + Analytics
# =====================================================================
class TestDashboard:
    def test_dashboard_returns_200(self, client):
        r = client.get("/workflows/dashboard/summary", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        for key in ("active_workflows", "total_executions", "success_rate", "failure_count",
                    "pending_approvals", "sla_breaches", "recent_executions"):
            assert key in body

    def test_dashboard_reflects_active_workflows(self, client):
        _make_workflow(client, status="active")
        _make_workflow(client, status="draft")
        r = client.get("/workflows/dashboard/summary", headers=MGR)
        assert r.json()["active_workflows"] == 1

    def test_dashboard_success_rate(self, client):
        _make_workflow(client, trigger_event="deal_created")
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        r = client.get("/workflows/dashboard/summary", headers=MGR)
        assert r.json()["total_executions"] == 1
        assert r.json()["success_rate"] == 1.0

    def test_member_can_view_dashboard(self, client):
        assert client.get("/workflows/dashboard/summary", headers=MEM).status_code == 200


class TestAnalytics:
    def test_analytics_returns_200(self, client):
        r = client.get("/workflows/analytics/summary", headers=MGR)
        assert r.status_code == 200
        body = r.json()
        for key in ("execution_count", "success_count", "failure_count", "success_rate",
                    "failure_rate", "avg_execution_time_ms", "sla_compliance_rate", "most_used_workflows"):
            assert key in body

    def test_most_used_workflows_ranked(self, client):
        w = _make_workflow(client, trigger_event="deal_created")
        p = _make_pipeline(client)
        st = _stages(p)
        _make_deal(client, p["id"], st["open"]["id"])
        _make_deal(client, p["id"], st["open"]["id"], title="Deal 2")
        r = client.get("/workflows/analytics/summary", headers=MGR)
        usage = r.json()["most_used_workflows"]
        assert usage[0]["workflow_id"] == w["id"]
        assert usage[0]["execution_count"] == 2

    def test_sla_compliance_rate_default_when_no_data(self, client):
        r = client.get("/workflows/analytics/summary", headers=MGR)
        assert r.json()["sla_compliance_rate"] == 1.0


# =====================================================================
# Backward Compatibility
# =====================================================================
class TestBackwardCompatibility:
    def test_deals_endpoint(self, client):
        assert client.get("/deals", headers=MGR).status_code == 200

    def test_pipelines_endpoint(self, client):
        assert client.get("/pipelines", headers=MGR).status_code == 200

    def test_cs_accounts_endpoint(self, client):
        assert client.get("/cs/accounts", headers=MGR).status_code == 200

    def test_campaigns_endpoint(self, client):
        assert client.get("/campaigns", headers=MGR).status_code == 200

    def test_assignments_endpoint(self, client):
        assert client.get("/assignments", headers=MGR).status_code == 200

    def test_revops_executive_dashboard(self, client):
        assert client.get("/revops/executive-dashboard", headers=MGR).status_code == 200

    def test_outreach_leads(self, client):
        assert client.get("/outreach/leads", headers=MGR).status_code == 200

    def test_outreach_tasks_still_creatable(self, client):
        r = client.post("/outreach/tasks", headers=MGR, json={"title": "T", "company_domain": "acme.com"})
        assert r.status_code == 201

    def test_deal_create_and_move_unaffected_by_no_workflows(self, client):
        p = _make_pipeline(client)
        st = _stages(p)
        d = _make_deal(client, p["id"], st["open"]["id"])
        r = client.post(f"/deals/{d['id']}/move", headers=MGR, json={"stage_id": st["won"]["id"]})
        assert r.status_code == 200
        assert r.json()["stage_id"] == st["won"]["id"]

    def test_team_work_queue(self, client):
        assert client.get("/team/work-queue", headers=MGR).status_code == 200


class TestSlaTickSingleFlight:
    def test_sla_tick_rejects_concurrent_call(self, client):
        import threading
        from backend.tick_lock import _locks
        lock = _locks.setdefault("sla_tick", threading.Lock())
        assert lock.acquire(blocking=False)
        try:
            r = client.post("/workflows/sla/tick", headers=MGR)
            assert r.status_code == 409
        finally:
            lock.release()

    def test_sla_tick_succeeds_when_not_locked(self, client):
        assert client.post("/workflows/sla/tick", headers=MGR).status_code == 200
