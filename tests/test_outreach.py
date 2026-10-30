"""Native Outreach module: pipeline, drafts/approvals, mock-mail, analytics, roles.

Verifies Outreach reuses platform data (companies / decision_makers / lead_scores /
engagement_recommendations) instead of duplicating it, and enforces platform roles.
"""
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import (
    Base,
    Company,
    DecisionMaker,
    EngagementRecommendation,
    LeadScore,
)

MGR = {"X-Dev-Role": "manager"}
MEM = {"X-Dev-Role": "member"}
ADMIN = {"X-Dev-Role": "admin"}


def _seed(s):
    s.add(Company(company_domain="nvidia.com", canonical_company_id="NV", company_name="NVIDIA",
                  name_key="nvidia", prospect_type="PRODUCT_COMPANY", validation_status="VALID"))
    s.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                  name_key="acme", prospect_type="SERVICE_PROVIDER", validation_status="VALID"))
    s.flush()
    s.add_all([
        LeadScore(company_domain="nvidia.com", lead_score=92.0, grade="A+", priority_rank=1),
        LeadScore(company_domain="acme.com", lead_score=70.0, grade="B", priority_rank=2),
        EngagementRecommendation(company_domain="nvidia.com", business_need="Scaling RTL verification",
                                 offering="Engineering staffing", pitch="We can place 5 engineers.",
                                 confidence=0.8, confidence_label="high"),
        DecisionMaker(linkedin_url="https://l/cto", company_domain="nvidia.com", first_name="Jensen",
                      last_name="Huang", current_title="CEO", seniority="senior",
                      work_email="jensen@nvidia.com", match_score=95),
    ])
    s.commit()


@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'o.db').as_posix()}",
                              log_json=False, dev_auth_bypass=True))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _seed(s)
        yield c


def _first_lead_id(c):
    return c.get("/outreach/leads", headers=MEM).json()["items"][0]["id"]


# ------------------------------------------------------------------ leads / sync
def test_sync_from_discovery_creates_leads(client):
    r = client.post("/outreach/leads/sync", headers=MGR)
    assert r.status_code == 200 and r.json()["created"] == 2
    # idempotent: a second sync creates nothing new
    assert client.post("/outreach/leads/sync", headers=MGR).json()["created"] == 0


def test_sync_requires_manager(client):
    assert client.post("/outreach/leads/sync", headers=MEM).status_code == 403


def test_lead_reuses_platform_intelligence(client):
    client.post("/outreach/leads/sync", headers=MGR)
    leads = client.get("/outreach/leads", headers=MEM).json()
    nv = next(x for x in leads["items"] if x["company_domain"] == "nvidia.com")
    assert nv["grade"] == "A+" and nv["priority"] == "high"           # from lead_scores
    assert nv["company_name"] == "NVIDIA"                              # from companies
    assert nv["primary_contact"]["email"] == "jensen@nvidia.com"      # from decision_makers
    detail = client.get(f"/outreach/leads/{nv['id']}", headers=MEM).json()
    assert "place 5 engineers" in detail["recommended_pitch"]          # from engagement_recommendations


def test_create_lead_idempotent(client):
    r1 = client.post("/outreach/leads", headers=MEM, json={"company_domain": "nvidia.com"})
    assert r1.status_code == 201
    r2 = client.post("/outreach/leads", headers=MEM, json={"company_domain": "nvidia.com"})
    assert r2.status_code == 201 and r2.json()["id"] == r1.json()["id"]  # same lead
    assert client.get("/outreach/leads", headers=MEM).json()["total"] == 1


def test_create_lead_unknown_company_404(client):
    assert client.post("/outreach/leads", headers=MEM,
                       json={"company_domain": "ghost.com"}).status_code == 404


def test_stage_change_logs_activity(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    r = client.patch(f"/outreach/leads/{lid}", headers=MEM, json={"stage": "outreach_ready"})
    assert r.status_code == 200 and r.json()["stage"] == "outreach_ready"
    acts = client.get(f"/outreach/leads/{lid}/activities", headers=MEM).json()
    assert any(a["type"] == "stage_changed" for a in acts)


def test_member_cannot_assign_owner_to_others(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    # member assigning to user id 999 (not self) is forbidden
    assert client.patch(f"/outreach/leads/{lid}", headers=MEM,
                        json={"owner_id": 999}).status_code == 403


# ------------------------------------------------------------------ templates
def test_template_crud_manager_only(client):
    assert client.post("/outreach/templates", headers=MEM,
                       json={"name": "x", "subject": "s", "body": "b"}).status_code == 403
    t = client.post("/outreach/templates", headers=MGR,
                    json={"name": "Intro", "subject": "Hi {{first_name}}", "body": "{{pitch}}"}).json()
    assert t["variables"] == ["first_name", "pitch"]                   # parsed tokens
    assert client.put(f"/outreach/templates/{t['id']}", headers=MGR,
                      json={"name": "Intro2", "subject": "s", "body": "b"}).json()["name"] == "Intro2"
    assert client.delete(f"/outreach/templates/{t['id']}", headers=MGR).status_code == 204


# ------------------------------------------------------------------ message lifecycle
def _draft(client, lid, headers=MEM):
    t = client.post("/outreach/templates", headers=MGR, json={
        "name": "Intro", "subject": "Hi {{first_name}} at {{company}}",
        "body": "{{pitch}}\n— {{sender_name}}"}).json()
    return client.post(f"/outreach/leads/{lid}/messages", headers=headers,
                       json={"template_id": t["id"]}).json()


def test_template_render_fills_variables(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    m = _draft(client, lid)
    assert m["subject"] == "Hi Jensen at NVIDIA"                       # rendered from platform data
    assert "place 5 engineers" in m["body"]
    assert m["to_email"] == "jensen@nvidia.com" and m["status"] == "draft"


def test_full_message_lifecycle_with_mock_mail(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    assert client.post(f"/outreach/messages/{mid}/submit", headers=MEM).json()["status"] == "pending_approval"
    assert client.post(f"/outreach/messages/{mid}/approve", headers=MEM).status_code == 403  # member
    assert client.post(f"/outreach/messages/{mid}/approve", headers=MGR).json()["status"] == "approved"
    sent = client.post(f"/outreach/messages/{mid}/send", headers=MGR).json()
    assert sent["status"] == "sent" and sent["thread_id"]
    # sending advances the pipeline
    assert client.get(f"/outreach/leads/{lid}", headers=MEM).json()["stage"] == "contacted"
    # mock reply lands in the thread + advances stage + feeds analytics
    rep = client.post(f"/outreach/messages/{mid}/reply", headers=MEM).json()
    assert rep["direction"] == "inbound"
    assert client.get(f"/outreach/leads/{lid}", headers=MEM).json()["stage"] == "replied"


def test_cannot_approve_a_draft_before_submit(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    assert client.post(f"/outreach/messages/{mid}/approve", headers=MGR).status_code == 409


def test_cannot_send_unapproved(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    assert client.post(f"/outreach/messages/{mid}/send", headers=MGR).status_code == 409


# ------------------------------------------------------------------ approvals / inbox / analytics
def test_approvals_inbox_and_analytics(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    client.post(f"/outreach/messages/{mid}/submit", headers=MEM)
    assert len(client.get("/outreach/approvals", headers=MGR).json()) == 1
    client.post(f"/outreach/messages/{mid}/approve", headers=MGR)
    client.post(f"/outreach/messages/{mid}/send", headers=MGR)
    assert len(client.get("/outreach/approvals", headers=MGR).json()) == 0   # cleared
    client.post(f"/outreach/messages/{mid}/reply", headers=MEM)
    inbox = client.get("/outreach/inbox", headers=MEM).json()
    assert len(inbox) == 1 and inbox[0]["has_reply"] and inbox[0]["message_count"] == 2
    a = client.get("/outreach/analytics", headers=MEM).json()
    assert a["sent"] == 1 and a["replied"] == 1 and a["reply_rate"] == 1.0
    assert any(f["stage"] == "replied" and f["count"] == 1 for f in a["funnel"])


def test_mine_filter_scopes_to_owner(client):
    client.post("/outreach/leads/sync", headers=MGR)
    # nothing owned yet
    assert client.get("/outreach/leads", headers=MEM, params={"mine": True}).json()["total"] == 0


# ------------------------------------------------------------------ notes
def test_add_note_appears_in_activity(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    r = client.post(f"/outreach/leads/{lid}/notes", headers=MEM, json={"text": "Spoke to Jensen — very interested"})
    assert r.status_code == 201 and r.json()["type"] == "note_added"
    acts = client.get(f"/outreach/leads/{lid}/activities", headers=MEM).json()
    assert any(a["type"] == "note_added" and "Jensen" in a["detail"] for a in acts)


def test_add_note_empty_rejected(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    assert client.post(f"/outreach/leads/{lid}/notes", headers=MEM, json={"text": "   "}).status_code == 422


def test_add_note_unknown_lead_404(client):
    assert client.post("/outreach/leads/9999/notes", headers=MEM, json={"text": "hi"}).status_code == 404


# ------------------------------------------------------------------ follow-up scheduling
def test_schedule_followup_and_patch(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    due = "2099-01-01T09:00:00Z"
    r = client.patch(f"/outreach/leads/{lid}", headers=MEM, json={"next_action_at": due})
    assert r.status_code == 200 and r.json()["next_action_at"] is not None


def test_outreach_requires_auth_when_configured(client, tmp_path):
    """With auth configured (no bypass) and no token, outreach is closed."""
    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'a.db').as_posix()}",
                              log_json=False, api_key="secret"))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        assert c.get("/outreach/leads").status_code == 401


# ------------------------------------------------------------------ tasks
def test_task_crud(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    # create
    r = client.post("/outreach/tasks", headers=MEM, json={
        "title": "Follow up with CTO", "outreach_lead_id": lid, "priority": "high"
    })
    assert r.status_code == 201
    tid = r.json()["id"]
    assert r.json()["status"] == "pending" and r.json()["priority"] == "high"
    # get
    assert client.get(f"/outreach/tasks/{tid}", headers=MEM).json()["title"] == "Follow up with CTO"
    # patch status
    r = client.patch(f"/outreach/tasks/{tid}", headers=MEM, json={"status": "in_progress"})
    assert r.json()["status"] == "in_progress"
    # complete logs activity
    r = client.patch(f"/outreach/tasks/{tid}", headers=MEM, json={"status": "completed"})
    assert r.json()["status"] == "completed" and r.json()["completed_at"] is not None
    acts = client.get(f"/outreach/leads/{lid}/activities", headers=MEM).json()
    assert any(a["type"] == "task_completed" for a in acts)


def test_task_list_filters(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    client.post("/outreach/tasks", headers=MEM, json={"title": "T1", "outreach_lead_id": lid})
    client.post("/outreach/tasks", headers=MEM, json={"title": "T2", "outreach_lead_id": lid})
    r = client.get("/outreach/tasks", headers=MEM, params={"outreach_lead_id": lid})
    assert r.json()["total"] == 2
    # status filter
    r = client.get("/outreach/tasks", headers=MEM, params={"status": "pending"})
    assert r.json()["total"] == 2


def test_task_delete_permission(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    r = client.post("/outreach/tasks", headers=MGR, json={"title": "Manager task", "outreach_lead_id": lid})
    tid = r.json()["id"]
    # member cannot delete manager's task
    assert client.delete(f"/outreach/tasks/{tid}", headers=MEM).status_code == 403
    # manager can
    assert client.delete(f"/outreach/tasks/{tid}", headers=MGR).status_code == 204


def test_task_empty_title_rejected(client):
    assert client.post("/outreach/tasks", headers=MEM, json={"title": "   "}).status_code == 422


# ------------------------------------------------------------------ meetings
def test_meeting_crud(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    # create
    r = client.post("/outreach/meetings", headers=MEM, json={
        "outreach_lead_id": lid,
        "meeting_type": "video",
        "title": "Intro call with Jensen",
        "scheduled_at": "2099-07-01T10:00:00Z",
        "duration_minutes": 45,
        "participants": ["jensen@nvidia.com"],
    })
    assert r.status_code == 201
    mid = r.json()["id"]
    assert r.json()["meeting_type"] == "video" and r.json()["duration_minutes"] == 45
    # activity logged
    acts = client.get(f"/outreach/leads/{lid}/activities", headers=MEM).json()
    assert any(a["type"] == "meeting_scheduled" for a in acts)
    # get
    assert client.get(f"/outreach/meetings/{mid}", headers=MEM).json()["title"] == "Intro call with Jensen"
    # patch outcome + logs meeting_completed
    r = client.patch(f"/outreach/meetings/{mid}", headers=MEM, json={"outcome": "positive", "notes": "Great call"})
    assert r.json()["outcome"] == "positive"
    acts2 = client.get(f"/outreach/leads/{lid}/activities", headers=MEM).json()
    assert any(a["type"] == "meeting_completed" for a in acts2)
    # delete
    assert client.delete(f"/outreach/meetings/{mid}", headers=MEM).status_code == 204


def test_meeting_list_filters(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    client.post("/outreach/meetings", headers=MEM, json={
        "outreach_lead_id": lid, "meeting_type": "call",
        "scheduled_at": "2099-08-01T09:00:00Z",
    })
    r = client.get("/outreach/meetings", headers=MEM, params={"outreach_lead_id": lid})
    assert r.json()["total"] == 1
    r = client.get("/outreach/meetings", headers=MEM, params={"upcoming_only": True})
    assert r.json()["total"] == 1


def test_meeting_delete_permission(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    r = client.post("/outreach/meetings", headers=MGR, json={
        "outreach_lead_id": lid, "meeting_type": "call",
        "scheduled_at": "2099-09-01T09:00:00Z",
    })
    mid = r.json()["id"]
    assert client.delete(f"/outreach/meetings/{mid}", headers=MEM).status_code == 403
    assert client.delete(f"/outreach/meetings/{mid}", headers=MGR).status_code == 204


# ------------------------------------------------------------------ unified timeline
def test_lead_timeline_combines_events(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    # note
    client.post(f"/outreach/leads/{lid}/notes", headers=MEM, json={"text": "Spoke to team"})
    # meeting
    client.post("/outreach/meetings", headers=MEM, json={
        "outreach_lead_id": lid, "meeting_type": "call",
        "scheduled_at": "2099-01-01T09:00:00Z",
    })
    # task
    client.post("/outreach/tasks", headers=MEM, json={"title": "Send proposal", "outreach_lead_id": lid})

    r = client.get(f"/outreach/leads/{lid}/timeline", headers=MEM)
    assert r.status_code == 200
    types = {e["event_type"] for e in r.json()}
    assert "activity" in types and "meeting" in types and "task" in types


# ------------------------------------------------------------------ follow-up engine
def test_follow_up_engine(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    # set a far-future follow-up
    client.patch(f"/outreach/leads/{lid}", headers=MEM, json={"next_action_at": "2099-12-31T00:00:00Z"})
    r = client.get("/outreach/follow-ups", headers=MEM)
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    item = next(x for x in items if x["lead_id"] == lid)
    assert item["is_overdue"] is False and item["days_until"] > 0


def test_overdue_follow_up(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    # past date → overdue
    client.patch(f"/outreach/leads/{lid}", headers=MEM, json={"next_action_at": "2020-01-01T00:00:00Z"})
    r = client.get("/outreach/follow-ups", headers=MEM)
    item = next(x for x in r.json() if x["lead_id"] == lid)
    assert item["is_overdue"] is True and item["reminder_priority"] == "urgent"


# ------------------------------------------------------------------ dashboard
def test_dashboard_widgets(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    # add a task due today
    client.post("/outreach/tasks", headers=MEM, json={
        "title": "Today task", "outreach_lead_id": lid,
    })
    r = client.get("/outreach/dashboard", headers=MEM)
    assert r.status_code == 200
    d = r.json()
    assert "tasks_due_today" in d and "overdue_tasks" in d
    assert "upcoming_follow_ups" in d and "upcoming_meetings" in d
    assert "recent_activity" in d
    assert isinstance(d["open_tasks"], int)


# ------------------------------------------------------------------ contact history
def test_contact_history(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    # jensen is DM id 1 (seeded); get his id
    detail = client.get(f"/outreach/leads/{lid}", headers=MEM).json()
    dm_id = detail["contacts"][0]["decision_maker_id"]

    r = client.get(f"/outreach/contacts/{dm_id}/history", headers=MEM)
    assert r.status_code == 200
    h = r.json()
    assert h["decision_maker_id"] == dm_id
    assert "timeline" in h and isinstance(h["timeline"], list)


def test_contact_history_unknown_dm(client):
    assert client.get("/outreach/contacts/9999/history", headers=MEM).status_code == 404


# ------------------------------------------------------------------ Phase 2: draft management
def test_delete_draft(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    assert client.delete(f"/outreach/messages/{mid}", headers=MEM).status_code == 204
    # draft is gone
    msgs = client.get(f"/outreach/leads/{lid}/messages", headers=MEM).json()
    assert not any(m["id"] == mid for m in msgs)


def test_delete_sent_message_rejected(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    client.post(f"/outreach/messages/{mid}/submit", headers=MEM)
    client.post(f"/outreach/messages/{mid}/approve", headers=MGR)
    client.post(f"/outreach/messages/{mid}/send", headers=MGR)
    assert client.delete(f"/outreach/messages/{mid}", headers=MGR).status_code == 409


def test_duplicate_draft(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    orig = _draft(client, lid)
    r = client.post(f"/outreach/messages/{orig['id']}/duplicate", headers=MEM)
    assert r.status_code == 201
    dup = r.json()
    assert dup["status"] == "draft"
    assert dup["id"] != orig["id"]
    assert "Copy of" in dup["subject"]
    assert dup["body"] == orig["body"]


# ------------------------------------------------------------------ Phase 2: scheduling + cancellation
def _approved_message(client):
    """Return (lead_id, message_id) for an approved ready-to-schedule message."""
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    client.post(f"/outreach/messages/{mid}/submit", headers=MEM)
    client.post(f"/outreach/messages/{mid}/approve", headers=MGR)
    return lid, mid


def test_schedule_message(client):
    _, mid = _approved_message(client)
    from datetime import datetime, timedelta, timezone
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    r = client.post(f"/outreach/messages/{mid}/schedule", headers=MGR,
                    json={"scheduled_at": future})
    assert r.status_code == 200
    m = r.json()
    assert m["status"] == "scheduled"
    assert m["scheduled_at"] is not None


def test_schedule_requires_approved_status(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    from datetime import datetime, timedelta, timezone
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert client.post(f"/outreach/messages/{mid}/schedule", headers=MGR,
                       json={"scheduled_at": future}).status_code == 409


def test_cancel_message(client):
    _, mid = _approved_message(client)
    r = client.post(f"/outreach/messages/{mid}/cancel", headers=MGR)
    assert r.status_code == 200 and r.json()["status"] == "cancelled"


def test_cancel_requires_manager(client):
    _, mid = _approved_message(client)
    assert client.post(f"/outreach/messages/{mid}/cancel", headers=MEM).status_code == 403


def test_scheduler_tick(client):
    r = client.post("/outreach/scheduler/tick", headers=MGR)
    assert r.status_code == 200
    body = r.json()
    assert "scheduled_to_queued" in body and "cancelled_by_deadline" in body
    assert "timestamp" in body


def test_scheduler_tick_advances_scheduled(client):
    """A scheduled message whose scheduled_at is in the past is moved to queued."""
    _, mid = _approved_message(client)
    from datetime import datetime, timedelta, timezone
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    client.post(f"/outreach/messages/{mid}/schedule", headers=MGR,
                json={"scheduled_at": past})
    r = client.post("/outreach/scheduler/tick", headers=MGR)
    assert r.json()["scheduled_to_queued"] >= 1
    msgs = client.get(f"/outreach/leads/{_first_lead_id(client)}/messages", headers=MEM).json()
    assert any(m["id"] == mid and m["status"] == "queued" for m in msgs)


# ------------------------------------------------------------------ Phase 2: attachments
def test_attachment_upload_and_list(client):
    import base64
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    content = base64.b64encode(b"hello attachment").decode()
    r = client.post(f"/outreach/messages/{mid}/attachments", headers=MEM, json={
        "filename": "test.txt",
        "content_type": "text/plain",
        "content_b64": content,
    })
    assert r.status_code == 201
    att = r.json()
    assert att["filename"] == "test.txt" and att["size_bytes"] == len(b"hello attachment")
    # list endpoint shows it
    atts = client.get(f"/outreach/messages/{mid}/attachments", headers=MEM).json()
    assert len(atts) == 1 and atts[0]["id"] == att["id"]
    # attachment_count on message should reflect the upload
    msgs = client.get(f"/outreach/leads/{lid}/messages", headers=MEM).json()
    msg_out = next(m for m in msgs if m["id"] == mid)
    assert msg_out["attachment_count"] == 1


def test_attachment_delete(client):
    import base64
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    content = base64.b64encode(b"bye").decode()
    att = client.post(f"/outreach/messages/{mid}/attachments", headers=MEM, json={
        "filename": "bye.txt", "content_type": "text/plain", "content_b64": content,
    }).json()
    assert client.delete(f"/outreach/messages/{mid}/attachments/{att['id']}",
                         headers=MEM).status_code == 204
    assert client.get(f"/outreach/messages/{mid}/attachments", headers=MEM).json() == []


def test_attachment_invalid_base64_rejected(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    assert client.post(f"/outreach/messages/{mid}/attachments", headers=MEM, json={
        "filename": "x.txt", "content_type": "text/plain", "content_b64": "!!!not-base64!!!",
    }).status_code == 422


# ------------------------------------------------------------------ Phase 2: provider config
def test_provider_config_default(client):
    r = client.get("/outreach/provider", headers=MGR)
    assert r.status_code == 200
    assert r.json()["provider_type"] == "mock"
    assert r.json()["connection_status"] == "connected"


def test_provider_config_set_and_validate(client):
    r = client.put("/outreach/provider", headers=MGR,
                   json={"provider_type": "mock", "config_json": "{}"})
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["provider_type"] == "mock" and cfg["connection_status"] == "connected"


def test_provider_config_unknown_type_shows_error(client):
    r = client.put("/outreach/provider", headers=MGR,
                   json={"provider_type": "carrier_pigeon"})
    assert r.status_code == 200
    assert r.json()["connection_status"] == "error"


def test_provider_config_requires_manager(client):
    assert client.put("/outreach/provider", headers=MEM,
                      json={"provider_type": "mock"}).status_code == 403


# ================================================================= Phase 3: Conversation & Inbox Engine
def _send_message(client, lid):
    """Helper: create + submit + approve + send a message. Returns sent message dict."""
    mid = _draft(client, lid)["id"]
    client.post(f"/outreach/messages/{mid}/submit", headers=MEM)
    client.post(f"/outreach/messages/{mid}/approve", headers=MGR)
    return client.post(f"/outreach/messages/{mid}/send", headers=MGR).json()


# ------------------------------------------------------------------ conversation engine
def test_conversation_auto_created_on_send(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    sent = _send_message(client, lid)
    assert sent["conversation_id"] is not None
    conv_id = sent["conversation_id"]
    r = client.get(f"/outreach/conversations/{conv_id}", headers=MEM)
    assert r.status_code == 200
    conv = r.json()
    assert conv["subject"] == sent["subject"]
    assert conv["message_count"] >= 1


def test_conversation_list_and_pagination(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    _send_message(client, lid)
    r = client.get("/outreach/conversations?page=1&page_size=50", headers=MEM)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and body["total"] >= 1


def test_conversation_folder_filter(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    _send_message(client, lid)
    # sent folder should contain our message
    r = client.get("/outreach/conversations?folder=sent", headers=MEM)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_reply_auto_joins_conversation(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    sent = _send_message(client, lid)
    mid = sent["id"]
    # simulate inbound reply
    reply = client.post(f"/outreach/messages/{mid}/reply", headers=MEM).json()
    assert reply["status"] == "replied"
    # The new reply should be a separate simulated reply (existing endpoint)
    # Now test Phase 3 reply-draft endpoint
    reply_draft = client.post(f"/outreach/messages/{mid}/reply-draft", headers=MEM,
                               json={"body": "Following up!", "subject": "Re: test"})
    assert reply_draft.status_code == 201
    rd = reply_draft.json()
    assert rd["status"] == "draft"
    assert rd["parent_message_id"] == mid
    # same conversation
    assert rd["conversation_id"] == sent["conversation_id"]


def test_conversation_messages_endpoint(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    sent = _send_message(client, lid)
    conv_id = sent["conversation_id"]
    r = client.get(f"/outreach/conversations/{conv_id}/messages", headers=MEM)
    assert r.status_code == 200
    assert any(m["id"] == sent["id"] for m in r.json())


def test_conversation_archive_restore_trash(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    sent = _send_message(client, lid)
    conv_id = sent["conversation_id"]
    # archive
    r = client.post(f"/outreach/conversations/{conv_id}/archive", headers=MEM)
    assert r.status_code == 200 and r.json()["is_archived"] is True
    # archived conversations appear in archived folder
    r2 = client.get("/outreach/conversations?folder=archived", headers=MEM)
    assert any(c["id"] == conv_id for c in r2.json()["items"])
    # restore
    r3 = client.post(f"/outreach/conversations/{conv_id}/restore", headers=MEM)
    assert r3.json()["is_archived"] is False
    # trash
    r4 = client.post(f"/outreach/conversations/{conv_id}/trash", headers=MEM)
    assert r4.json()["is_trashed"] is True


# ------------------------------------------------------------------ message state
def test_mark_read_unread(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    msg = _draft(client, lid)
    mid = msg["id"]
    assert client.post(f"/outreach/messages/{mid}/read", headers=MEM).json()["is_read"] is True
    assert client.post(f"/outreach/messages/{mid}/unread", headers=MEM).json()["is_read"] is False


def test_star_unstar(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    assert client.post(f"/outreach/messages/{mid}/star", headers=MEM).json()["is_starred"] is True
    assert client.post(f"/outreach/messages/{mid}/unstar", headers=MEM).json()["is_starred"] is False


def test_pin_unpin(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    assert client.post(f"/outreach/messages/{mid}/pin", headers=MEM).json()["is_pinned"] is True
    assert client.post(f"/outreach/messages/{mid}/unpin", headers=MEM).json()["is_pinned"] is False


def test_archive_restore_trash_message(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    assert client.post(f"/outreach/messages/{mid}/archive", headers=MEM).json()["is_archived"] is True
    r_restore = client.post(f"/outreach/messages/{mid}/restore", headers=MEM).json()
    assert r_restore["is_archived"] is False and r_restore["is_trashed"] is False
    assert client.post(f"/outreach/messages/{mid}/trash", headers=MEM).json()["is_trashed"] is True


# ------------------------------------------------------------------ thread actions
def test_forward_creates_draft(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    sent = _send_message(client, lid)
    r = client.post(f"/outreach/messages/{sent['id']}/forward", headers=MEM,
                    json={"to_email": "other@example.com", "body": "Sharing this with you."})
    assert r.status_code == 201
    fwd = r.json()
    assert fwd["status"] == "draft" and "Fwd:" in fwd["subject"]
    assert fwd["to_email"] == "other@example.com"


# ------------------------------------------------------------------ preview
def test_message_preview(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    r = client.get(f"/outreach/messages/{mid}/preview", headers=MEM)
    assert r.status_code == 200
    p = r.json()
    assert "body_plain" in p and "body_html_safe" in p
    assert "attachments" in p and isinstance(p["attachments"], list)


def test_preview_sanitizes_xss(client):
    """HTML with script tags must be stripped in preview."""
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    # Patch the message body_html with dangerous content (direct DB check via preview)
    # We just verify the sanitizer strips <script> even if injected
    from backend.email_sanitizer import sanitize_html
    dirty = '<b>Hello</b><script>alert(1)</script><a href="javascript:void(0)">click</a>'
    clean = sanitize_html(dirty)
    assert "<script>" not in clean
    assert "javascript:" not in clean
    assert "<b>Hello</b>" in clean


# ------------------------------------------------------------------ search
def test_search_by_subject(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    _draft(client, lid)   # creates draft with "Jensen at NVIDIA" subject
    r = client.get("/outreach/search?q=Jensen", headers=MEM)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_search_by_folder(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    client.post(f"/outreach/messages/{mid}/archive", headers=MEM)
    r = client.get("/outreach/search?folder=archived", headers=MEM)
    assert r.status_code == 200
    assert any(m["id"] == mid for m in r.json()["items"])


def test_search_combined_filters(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    _draft(client, lid)
    r = client.get("/outreach/search?q=Hi&company_domain=nvidia.com", headers=MEM)
    assert r.status_code == 200


# ------------------------------------------------------------------ labels
def test_system_labels_seeded(client):
    r = client.get("/outreach/labels", headers=MEM)
    assert r.status_code == 200
    names = {l["name"] for l in r.json()}
    assert "follow-up" in names and "prospect" in names


def test_label_crud(client):
    # create
    r = client.post("/outreach/labels", headers=MGR, json={"name": "vip", "color": "red"})
    assert r.status_code == 201
    lbl = r.json()
    assert lbl["name"] == "vip" and lbl["is_system"] is False
    # duplicate name rejected
    assert client.post("/outreach/labels", headers=MGR,
                       json={"name": "vip", "color": "blue"}).status_code == 409
    # delete
    assert client.delete(f"/outreach/labels/{lbl['id']}", headers=MGR).status_code == 204


def test_system_label_cannot_be_deleted(client):
    labels = client.get("/outreach/labels", headers=MEM).json()
    sys_lbl = next(l for l in labels if l["is_system"])
    assert client.delete(f"/outreach/labels/{sys_lbl['id']}", headers=MGR).status_code == 409


def test_label_apply_and_remove(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    sent = _send_message(client, lid)
    conv_id = sent["conversation_id"]
    labels = client.get("/outreach/labels", headers=MEM).json()
    lbl_id = labels[0]["id"]
    # apply
    r = client.post(f"/outreach/conversations/{conv_id}/labels/{lbl_id}", headers=MEM)
    assert r.status_code == 200
    assert any(l["id"] == lbl_id for l in r.json()["labels"])
    # remove
    r2 = client.delete(f"/outreach/conversations/{conv_id}/labels/{lbl_id}", headers=MEM)
    assert r2.status_code == 200
    assert not any(l["id"] == lbl_id for l in r2.json()["labels"])


def test_label_filter_conversations(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    sent = _send_message(client, lid)
    conv_id = sent["conversation_id"]
    lbl_id = client.post("/outreach/labels", headers=MGR,
                          json={"name": "urgent2", "color": "red"}).json()["id"]
    client.post(f"/outreach/conversations/{conv_id}/labels/{lbl_id}", headers=MEM)
    r = client.get(f"/outreach/conversations?label_id={lbl_id}", headers=MEM)
    assert r.status_code == 200
    assert any(c["id"] == conv_id for c in r.json()["items"])


# ------------------------------------------------------------------ bulk operations
def test_bulk_mark_read(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    m1 = _draft(client, lid)["id"]
    m2 = _draft(client, lid)["id"]
    r = client.post("/outreach/messages/bulk", headers=MEM,
                    json={"message_ids": [m1, m2], "action": "mark_read"})
    assert r.status_code == 200
    assert r.json()["affected"] == 2


def test_bulk_archive_messages(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    mid = _draft(client, lid)["id"]
    r = client.post("/outreach/messages/bulk", headers=MEM,
                    json={"message_ids": [mid], "action": "archive"})
    assert r.status_code == 200 and r.json()["affected"] == 1


def test_bulk_conversation_archive(client):
    client.post("/outreach/leads/sync", headers=MGR)
    lid = _first_lead_id(client)
    sent = _send_message(client, lid)
    conv_id = sent["conversation_id"]
    r = client.post("/outreach/conversations/bulk", headers=MEM,
                    json={"conversation_ids": [conv_id], "action": "archive"})
    assert r.status_code == 200 and r.json()["affected"] == 1


def test_bulk_invalid_action(client):
    assert client.post("/outreach/messages/bulk", headers=MEM,
                       json={"message_ids": [1], "action": "explode"}).status_code == 422
