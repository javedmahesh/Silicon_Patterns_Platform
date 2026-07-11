"""Standard Scheduled Runs: execution recording, overlap prevention, Outlook
notification (log/graph/failure paths, active-only recipients), scheduler due/dedup
logic, and the scheduler/run-history API. No real Apify or Graph network calls."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend import notifications
from backend import standard_run
from backend.config import Settings
from backend.main import create_app
from backend.scheduler import PipelineScheduler, _slot_today_utc
from backend.standard_run import RunInProgress, execute_standard_run
from master_db.local import make_session_factory
from master_db.models import Base, Company, DemandSignal, PipelineExecution, PipelineRun, User

MGR = {"X-Dev-Role": "manager"}
MEM = {"X-Dev-Role": "member"}
ADMIN = {"X-Dev-Role": "admin"}

OFF = dict(scheduler_enabled=False, notify_mode="off")


def _seed_scorable(s):
    s.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                  name_key="acme", company_tier="STARTUP", prospect_type="PRODUCT_COMPANY",
                  compliance_flag="APPROVED", validation_status="VALID"))
    s.add(DemandSignal(company_domain="acme.com", demand_score=90.0,
                       lead_readiness_score=70.0, total_engineering_jobs=30))
    s.commit()


@pytest.fixture()
def session():
    with make_session_factory(":memory:")() as s:
        _seed_scorable(s)
        yield s


# ------------------------------------------------------------- execution recording
def test_execute_standard_run_records_execution_row(session):
    settings = Settings(**OFF)
    execution, results = execute_standard_run(session, settings, trigger="manual",
                                              components=["scoring"], notify=False)
    assert execution.status == "success"
    assert execution.trigger == "manual"
    assert execution.run_id.startswith("run-")
    assert execution.finished_at is not None and execution.duration_ms >= 0
    # per-engine stats snapshotted
    comps = [s_["component"] for s_ in execution.stages]
    assert comps == ["scoring"]
    assert execution.stages[0]["status"] == "success"
    # platform totals snapshotted
    assert execution.totals["companies"] == 1 and execution.totals["leads_scored"] == 1
    # stage rows share the run id (pipeline_id join)
    stage_rows = session.query(PipelineRun).filter(PipelineRun.pipeline_id == execution.run_id).all()
    assert stage_rows and all(r.pipeline_id == execution.run_id for r in stage_rows)
    # manual runs are not notified
    assert execution.notification_status == "skipped"


def test_execute_standard_run_manual_matches_scheduled_pipeline(session):
    """Manual and scheduled runs execute the identical component pipeline."""
    settings = Settings(**OFF)
    m, _ = execute_standard_run(session, settings, trigger="manual", components=["scoring"])
    s2, _ = execute_standard_run(session, settings, trigger="scheduled", slot="09:00",
                                 components=["scoring"], notify=True)
    assert [x["component"] for x in m.stages] == [x["component"] for x in s2.stages]
    assert s2.trigger == "scheduled" and s2.scheduled_slot == "09:00"


# ------------------------------------------------------------- overlap prevention
def test_overlap_prevention_refuses_second_run(session):
    settings = Settings(**OFF)
    # Hold the in-process lock (as a run in flight would) → a new run is refused.
    assert standard_run._local_lock.acquire(blocking=False)
    try:
        with pytest.raises(RunInProgress):
            execute_standard_run(session, settings, components=["scoring"])
    finally:
        standard_run._local_lock.release()
    # lock released → runs work again
    execution, _ = execute_standard_run(session, settings, components=["scoring"])
    assert execution.status == "success"


# ------------------------------------------------------------- notifications
def _add_users(s):
    rows = [
        User(email="active1@siliconpatterns.com", role="member", status="active", is_active=True),
        User(email="active2@siliconpatterns.com", role="admin", status="active", is_active=True),
        User(email="pending@siliconpatterns.com", role="member", status="pending", is_active=False),
        User(email="disabled@siliconpatterns.com", role="member", status="disabled", is_active=False),
        User(email="rejected@siliconpatterns.com", role="member", status="rejected", is_active=False),
    ]
    for u in rows:
        s.add(u)
    s.commit()


def test_notification_only_targets_active_users(session, monkeypatch):
    _add_users(session)
    sent = {}
    monkeypatch.setattr(notifications, "_graph_send_mail",
                        lambda settings, recipients, subj, body: sent.update(to=list(recipients)))
    settings = Settings(scheduler_enabled=False, notify_mode="graph",
                        microsoft_tenant_id="t", microsoft_client_id="c",
                        microsoft_client_secret="sec", notify_sender_email="noreply@siliconpatterns.com")
    execution, _ = execute_standard_run(session, settings, trigger="scheduled", slot="09:00",
                                        components=["scoring"], notify=True)
    assert execution.notification_status == "sent"
    assert set(sent["to"]) == {"active1@siliconpatterns.com", "active2@siliconpatterns.com"}
    assert execution.notified_count == 2


def test_notification_failure_never_fails_the_run(session, monkeypatch):
    _add_users(session)

    def _boom(*a, **k):
        raise RuntimeError("graph 403 Forbidden: Mail.Send not consented")

    monkeypatch.setattr(notifications, "_graph_send_mail", _boom)
    settings = Settings(scheduler_enabled=False, notify_mode="graph",
                        microsoft_tenant_id="t", microsoft_client_id="c",
                        microsoft_client_secret="sec", notify_sender_email="noreply@siliconpatterns.com")
    execution, _ = execute_standard_run(session, settings, trigger="scheduled", slot="21:00",
                                        components=["scoring"], notify=True)
    assert execution.status == "success"                 # pipeline unaffected
    assert execution.notification_status == "failed"
    assert "403" in execution.notification_detail


def test_notification_log_only_when_graph_unconfigured(session):
    _add_users(session)
    settings = Settings(scheduler_enabled=False, notify_mode="auto")  # no graph creds
    execution, _ = execute_standard_run(session, settings, trigger="scheduled", slot="09:00",
                                        components=["scoring"], notify=True)
    assert execution.notification_status == "logged"
    assert execution.notified_count == 2


def test_notification_off_mode_skips(session):
    _add_users(session)
    settings = Settings(**OFF)
    execution, _ = execute_standard_run(session, settings, trigger="scheduled", slot="09:00",
                                        components=["scoring"], notify=True)
    assert execution.notification_status == "skipped"


def test_summary_html_contains_required_fields():
    e = PipelineExecution(
        run_id="run-20260101-090000", trigger="scheduled", scheduled_slot="09:00",
        started_at=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 1, 1, 9, 3, tzinfo=timezone.utc),
        duration_ms=180000, status="success", records_processed=42,
        stages=[{"component": "scoring", "status": "success", "processed": 42}],
        totals={"companies": 122, "opportunities": 50, "decision_makers": 288,
                "jobs": 188, "leads_scored": 122},
    )
    html = notifications.build_summary_html(e)
    for needle in ("run-20260101-090000", "scoring", "122", "288", "188",
                   "Total companies", "Total decision makers", "SUCCESS"):
        assert needle in html


# ------------------------------------------------------------- scheduler logic
def test_scheduler_disabled_does_not_start():
    sched = PipelineScheduler(make_session_factory(":memory:"), Settings(scheduler_enabled=False))
    sched.start()
    assert sched.is_running() is False


def test_schedule_times_parsing_and_defaults():
    assert Settings().schedule_times == ["09:00", "21:00"]
    assert Settings(schedule_times_raw="7:5, 21:00 ,09:00").schedule_times == ["07:05", "09:00", "21:00"]


def test_next_run_at_is_soonest_upcoming_slot():
    sched = PipelineScheduler(make_session_factory(":memory:"),
                              Settings(scheduler_enabled=False, schedule_times_raw="09:00,21:00"))
    nxt = sched.next_run_at()
    assert nxt is not None and nxt > datetime.now(timezone.utc)


def test_scheduler_dedup_skips_already_ran_slot(session):
    factory = make_session_factory(":memory:")
    sched = PipelineScheduler(factory, Settings(scheduler_enabled=False, schedule_times_raw="09:00"))
    now_local = datetime.now().astimezone()
    slot_utc = _slot_today_utc(now_local, "09:00")
    # no run yet → not deduped
    assert sched._already_ran(session, "09:00", slot_utc) is False
    # a scheduled run recorded at this slot → deduped
    session.add(PipelineExecution(run_id="run-x", trigger="scheduled", scheduled_slot="09:00",
                                  status="success", started_at=slot_utc + timedelta(minutes=1)))
    session.commit()
    assert sched._already_ran(session, "09:00", slot_utc) is True
    # yesterday's same-slot run does NOT dedup today's occurrence
    session.query(PipelineExecution).delete()
    session.add(PipelineExecution(run_id="run-y", trigger="scheduled", scheduled_slot="09:00",
                                  status="success", started_at=slot_utc - timedelta(days=1)))
    session.commit()
    assert sched._already_ran(session, "09:00", slot_utc) is False


# ------------------------------------------------------------- API
@pytest.fixture()
def client(tmp_path):
    app = create_app(Settings(
        database_url=f"sqlite:///{(tmp_path / 'sched.db').as_posix()}",
        log_json=False, dev_auth_bypass=True, scheduler_enabled=False, notify_mode="off",
    ))
    with TestClient(app) as c:
        Base.metadata.create_all(app.state.db.engine)
        yield c


def test_status_endpoint_reports_schedule(client):
    r = client.get("/scheduler/status", headers=MGR)
    assert r.status_code == 200
    body = r.json()
    assert body["schedule_times"] == ["09:00", "21:00"]
    assert body["enabled"] is False and body["running"] is False
    assert body["next_run"] is not None


def test_run_history_lists_executions(client):
    with client.app.state.db.sessionmaker() as s:
        _seed_scorable(s)
        execute_standard_run(s, client.app.state.settings, trigger="manual", components=["scoring"])
    r = client.get("/scheduler/runs", headers=MGR)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    run = body["items"][0]
    assert run["trigger"] == "manual" and run["status"] == "success"
    assert run["stages"][0]["component"] == "scoring"
    # detail endpoint
    d = client.get(f"/scheduler/runs/{run['run_id']}", headers=MGR)
    assert d.status_code == 200 and d.json()["run_id"] == run["run_id"]


def test_run_now_requires_manager(client):
    assert client.post("/scheduler/run-now", headers=MEM).status_code == 403


def test_run_now_busy_when_execution_running(client, monkeypatch):
    # a run already in progress → 409, and no second run is spawned
    with client.app.state.db.sessionmaker() as s:
        s.add(PipelineExecution(run_id="run-inflight", trigger="manual", status="running"))
        s.commit()
    called = {"n": 0}
    monkeypatch.setattr("backend.scheduler_service.execute_standard_run",
                        lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    r = client.post("/scheduler/run-now", headers=MGR)
    assert r.status_code == 409
    assert called["n"] == 0
