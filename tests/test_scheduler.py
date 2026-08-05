"""Standard Scheduled Runs: execution recording, overlap prevention, the scheduler's
contract with the notification framework (active-only recipients, failure isolation,
unconfigured degradation, kill switch), scheduler due/dedup logic, and the
scheduler/run-history API. No real Apify calls and no real SMTP connection."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend import notifications
from backend import standard_run
from backend.config import Settings
from backend.main import create_app
from backend.scheduler import PipelineScheduler, _slot_today_utc
from backend.notifications.providers.email import SmtpEmailProvider
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


def test_local_lock_released_when_run_body_raises(session):
    """SQLite/local path: an exception propagating out of the run must not strand the
    process-local lock (the next run would be refused forever)."""
    settings = Settings(**OFF)
    with pytest.raises(RuntimeError):
        with standard_run._RunLock(session):
            raise RuntimeError("boom")
    assert standard_run._local_lock.acquire(blocking=False)   # was released
    standard_run._local_lock.release()
    execution, _ = execute_standard_run(session, settings, components=["scoring"])
    assert execution.status == "success"


def test_manual_and_scheduled_runs_are_mutually_exclusive(session):
    """Both triggers go through the identical _RunLock, so one blocks the other."""
    settings = Settings(**OFF)
    with standard_run._RunLock(session):                       # a scheduled run in flight
        with pytest.raises(RunInProgress):
            execute_standard_run(session, settings, trigger="manual", components=["scoring"])
    # …and the reverse, once the lock is free
    execution, _ = execute_standard_run(session, settings, trigger="scheduled", slot="03:30",
                                        components=["scoring"], notify=False)
    assert execution.status == "success"


# ---------------------------------------------- Postgres advisory-lock ownership
# A session-level advisory lock belongs to the PHYSICAL connection that took it. The
# ORM Session releases its connection on every commit (a Standard Run commits many
# times), so lock and unlock must NOT ride on the Session — these fakes fail loudly
# if they ever do.
class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeConn:
    """Records every statement executed on THIS physical connection."""

    def __init__(self, engine, acquired: bool = True, unlock_raises: bool = False):
        self.engine = engine
        self.acquired = acquired
        self.unlock_raises = unlock_raises
        self.statements: list[str] = []
        self.closed = False
        self.invalidated = False
        self.options: dict = {}

    def execution_options(self, **kw):
        self.options.update(kw)
        return self

    def execute(self, stmt, params=None):
        sql = str(stmt)
        self.statements.append(sql)
        if "pg_try_advisory_lock" in sql:
            return _FakeResult(1 if self.acquired else 0)
        if "pg_advisory_unlock" in sql and self.unlock_raises:
            raise RuntimeError("connection is dead")
        return _FakeResult(None)

    def close(self):
        self.closed = True

    def invalidate(self):
        self.invalidated = True


class _FakeEngine:
    def __init__(self, acquired: bool = True, unlock_raises: bool = False):
        self.dialect = type("D", (), {"name": "postgresql"})()
        self.handed_out: list[_FakeConn] = []
        self._acquired = acquired
        self._unlock_raises = unlock_raises

    @property
    def engine(self):
        return self

    def connect(self):
        conn = _FakeConn(self, self._acquired, self._unlock_raises)
        self.handed_out.append(conn)
        return conn


class _FakeSession:
    """A Session that would hand back a DIFFERENT connection every time — so any use
    of the Session for lock/unlock shows up as a cross-connection bug."""

    def __init__(self, engine):
        self._engine = engine
        self.statements: list[str] = []

    def get_bind(self):
        return self._engine

    def execute(self, stmt, params=None):
        self.statements.append(str(stmt))
        return _FakeResult(None)

    def commit(self):
        pass


def test_pg_lock_and_unlock_use_the_same_dedicated_connection():
    engine = _FakeEngine()
    session = _FakeSession(engine)
    with standard_run._RunLock(session):
        assert len(engine.handed_out) == 1
        conn = engine.handed_out[0]
        assert any("pg_try_advisory_lock" in s for s in conn.statements)
        assert not conn.closed                    # held for the whole protected run
        assert conn.options.get("isolation_level") == "AUTOCOMMIT"   # never idle-in-transaction
    conn = engine.handed_out[0]
    # exactly ONE connection was ever used, and it did both halves
    assert len(engine.handed_out) == 1
    assert [("pg_try_advisory_lock" in s, "pg_advisory_unlock" in s) for s in conn.statements] \
        == [(True, False), (False, True)]
    assert conn.closed and not conn.invalidated
    assert session.statements == []               # the ORM Session never touched the lock


def test_pg_lock_released_on_propagated_exception():
    engine = _FakeEngine()
    with pytest.raises(RuntimeError):
        with standard_run._RunLock(_FakeSession(engine)):
            raise RuntimeError("stage blew up")
    conn = engine.handed_out[0]
    assert any("pg_advisory_unlock" in s for s in conn.statements) and conn.closed
    assert standard_run._local_lock.acquire(blocking=False)
    standard_run._local_lock.release()


def test_pg_lock_contention_raises_run_in_progress_and_frees_everything():
    """Another process holds it → RunInProgress, and this process leaks nothing."""
    engine = _FakeEngine(acquired=False)
    with pytest.raises(RunInProgress):
        with standard_run._RunLock(_FakeSession(engine)):
            pytest.fail("body must not run")
    conn = engine.handed_out[0]
    assert conn.closed                                        # connection returned
    assert not any("pg_advisory_unlock" in s for s in conn.statements)   # never held it
    assert standard_run._local_lock.acquire(blocking=False)   # local lock released too
    standard_run._local_lock.release()


def test_pg_connection_invalidated_when_unlock_fails():
    """If unlock can't run, the physical connection is dropped — ending its Postgres
    backend and with it every advisory lock — rather than returned still-locked."""
    engine = _FakeEngine(unlock_raises=True)
    with standard_run._RunLock(_FakeSession(engine)):
        pass
    conn = engine.handed_out[0]
    assert conn.invalidated and conn.closed
    assert standard_run._local_lock.acquire(blocking=False)
    standard_run._local_lock.release()


def test_lock_is_reacquirable_immediately_after_a_run(session):
    """No cooldown/stranding: the very next run acquires cleanly."""
    settings = Settings(**OFF)
    first, _ = execute_standard_run(session, settings, components=["scoring"])
    second, _ = execute_standard_run(session, settings, components=["scoring"])
    assert first.status == "success" and second.status == "success"
    assert first.run_id != second.run_id


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


# The notification framework itself is covered end-to-end in
# tests/test_notifications.py. These cases pin the SCHEDULER's contract with it:
# recipients, failure isolation, unconfigured degradation, and the off switch.
SMTP = dict(smtp_host="smtp.test", smtp_username="bot@siliconpatterns.com",
            smtp_password="app-password", email_from="bot@siliconpatterns.com")


def test_notification_only_targets_active_users(session, monkeypatch):
    _add_users(session)
    seen: dict = {}

    def _capture(self, settings, msg):
        seen["bcc"] = msg["Bcc"]

    monkeypatch.setattr(SmtpEmailProvider, "_deliver", _capture)
    settings = Settings(scheduler_enabled=False, **SMTP)
    execution, _ = execute_standard_run(session, settings, trigger="scheduled", slot="09:00",
                                        components=["scoring"], notify=True)
    assert execution.notification_status == "sent"
    assert set(seen["bcc"].split(", ")) == {"active1@siliconpatterns.com", "active2@siliconpatterns.com"}
    assert execution.notified_count == 2


def test_notification_failure_never_fails_the_run(session, monkeypatch):
    _add_users(session)

    def _boom(self, settings, msg):
        raise RuntimeError("SMTP 535 auth failed: bad app password")

    monkeypatch.setattr(SmtpEmailProvider, "_deliver", _boom)
    settings = Settings(scheduler_enabled=False, notification_retry_count=2, **SMTP)
    execution, _ = execute_standard_run(session, settings, trigger="scheduled", slot="21:00",
                                        components=["scoring"], notify=True)
    assert execution.status == "success"                 # pipeline unaffected
    assert execution.notification_status == "failed"
    assert "535" in execution.notification_detail


def test_notification_log_only_when_provider_unconfigured(session):
    _add_users(session)
    settings = Settings(scheduler_enabled=False)          # no SMTP credentials
    execution, _ = execute_standard_run(session, settings, trigger="scheduled", slot="09:00",
                                        components=["scoring"], notify=True)
    assert execution.notification_status == "logged"
    assert execution.notified_count == 2


def test_notification_disabled_skips(session):
    _add_users(session)
    settings = Settings(scheduler_enabled=False, enable_notifications=False)
    execution, _ = execute_standard_run(session, settings, trigger="scheduled", slot="09:00",
                                        components=["scoring"], notify=True)
    assert execution.notification_status == "skipped"


def test_legacy_notify_mode_off_still_disables(session):
    """SP_NOTIFY_MODE=off predates the framework and may still be set in a deployed
    environment; it must keep working as a kill switch."""
    _add_users(session)
    settings = Settings(scheduler_enabled=False, notify_mode="off", **SMTP)
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
    for needle in ("run-20260101-090000", "scoring", "SUCCESS", "Run summary", "Pipelines"):
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


def test_update_config_persists_and_overrides_env(client):
    # A saved override wins over the env default (fixture is scheduler_enabled=False).
    r = client.put("/scheduler/config", headers=MGR,
                   json={"schedule_times": ["7:5", "23:30", "07:05"], "enabled": True, "grace_minutes": 60})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["schedule_times"] == ["07:05", "23:30"]   # normalized + deduped + sorted
    assert body["enabled"] is True and body["grace_minutes"] == 60
    # persisted: a fresh status read reflects it, not the env default
    st = client.get("/scheduler/status", headers=MGR).json()
    assert st["schedule_times"] == ["07:05", "23:30"] and st["grace_minutes"] == 60 and st["enabled"] is True


def test_update_config_rejects_bad_time(client):
    r = client.put("/scheduler/config", headers=MGR,
                   json={"schedule_times": ["25:00"], "enabled": True, "grace_minutes": 30})
    assert r.status_code == 422


def test_update_config_requires_manager(client):
    body = {"schedule_times": ["09:00"], "enabled": True, "grace_minutes": 30}
    assert client.put("/scheduler/config", headers={"X-Dev-Role": "member"}, json=body).status_code == 403
    assert client.put("/scheduler/config", headers=MGR, json=body).status_code == 200


def test_disable_via_config(client):
    client.put("/scheduler/config", headers=MGR,
               json={"schedule_times": ["09:00"], "enabled": False, "grace_minutes": 30})
    assert client.get("/scheduler/status", headers=MGR).json()["enabled"] is False


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
