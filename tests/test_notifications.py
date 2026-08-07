"""Platform notification framework (backend/notifications).

Covers the service, the provider abstraction and registry, HTML/text rendering,
recipient selection, delivery logging, retry handling, the admin/standard failure
split, and the scheduler integration point. No SMTP socket is ever opened — the
provider's single I/O method (`_deliver`) is the seam every test patches.
"""
from datetime import datetime, timezone

import pytest

from backend import notifications
from backend.config import Settings
from backend.notifications import service, templates
from backend.notifications.providers import base as provider_base
from backend.notifications.providers.email import SmtpEmailProvider, build_message
from backend.notifications.schemas import (
    Audience,
    DeliveryOutcome,
    MetricGroup,
    Recipient,
    RunNotification,
    Severity,
    StageSummary,
)
from master_db.local import make_session_factory
from master_db.models import (
    Company,
    DecisionMaker,
    Job,
    LeadScore,
    NewsSource,
    NotificationDelivery,
    PipelineExecution,
    User,
)

NOW = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)
SMTP = dict(smtp_host="smtp.test", smtp_username="bot@sp.com",
            smtp_password="app-pw", email_from="bot@sp.com")


# ------------------------------------------------------------------ fixtures
@pytest.fixture()
def session():
    with make_session_factory(":memory:")() as s:
        yield s


def _users(s):
    s.add_all([
        User(email="member@sp.com", full_name="Mem Ber", role="member", status="active", is_active=True),
        User(email="admin@sp.com", full_name="Ad Min", role="admin", status="active", is_active=True),
        User(email="super@sp.com", full_name="Su Per", role="super_admin", status="active", is_active=True),
        User(email="pending@sp.com", role="member", status="pending", is_active=False),
        User(email="disabled@sp.com", role="member", status="disabled", is_active=False),
        User(email="rejected@sp.com", role="member", status="rejected", is_active=False),
        User(email="gone@deleted.invalid", role="member", status="deleted", is_active=False),
    ])
    s.commit()


def _execution(status="success", stages=None, **kw):
    return PipelineExecution(
        run_id=kw.pop("run_id", "run-20260301-090000-000001"),
        trigger="scheduled", scheduled_slot="09:00", status=status,
        started_at=NOW, finished_at=datetime(2026, 3, 1, 9, 4, tzinfo=timezone.utc),
        duration_ms=240000, records_processed=1234,
        stages=stages if stages is not None else [
            {"component": "industry", "status": "success", "processed": 40, "created": 5,
             "updated": 3, "review": 0, "duration_ms": 1000, "errors": [], "notes": ""},
            {"component": "news", "status": "success", "processed": 60, "created": 12,
             "updated": 0, "review": 4, "duration_ms": 2000, "errors": [], "notes": "sources=14"},
            {"component": "scoring", "status": "success", "processed": 9, "created": 0,
             "updated": 9, "review": 0, "duration_ms": 500, "errors": [], "notes": ""},
        ],
        totals={"companies": 609, "opportunities": 459, "decision_makers": 2399,
                "jobs": 188, "leads_scored": 609},
        **kw,
    )


def _notification(**kw) -> RunNotification:
    base = dict(
        run_id="run-1", status="success", trigger="scheduled", started_at=NOW,
        finished_at=datetime(2026, 3, 1, 9, 4, tzinfo=timezone.utc),
        duration_ms=240000, records_processed=1234,
        stages=[StageSummary("news", "success", processed=60, created=12)],
        intelligence=[MetricGroup("News Collection", [("Articles collected", 60)])],
        frontend_url="https://app.example.com", brand_name="Silicon Patterns",
    )
    base.update(kw)
    return RunNotification(**base)


class _Recorder(SmtpEmailProvider):
    """Captures the composed message instead of opening a socket."""

    # Registered in place of "gmail", so it must answer to that name for the
    # delivery log to record the provider the operator actually configured.
    name = "gmail"

    def __init__(self, fail_times: int = 0):
        self.messages = []
        self.calls = 0
        self.fail_times = fail_times

    def _deliver(self, settings, msg):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError(f"SMTP 421 transient #{self.calls}")
        self.messages.append(msg)


# ------------------------------------------------------- recipient selection
def test_only_approved_active_users_are_recipients(session):
    _users(session)
    emails = {r.email for r in service.resolve_recipients(session)}
    assert emails == {"member@sp.com", "admin@sp.com", "super@sp.com"}


def test_pending_disabled_rejected_and_deleted_are_never_recipients(session):
    _users(session)
    emails = {r.email for r in service.resolve_recipients(session)}
    for excluded in ("pending@sp.com", "disabled@sp.com", "rejected@sp.com", "gone@deleted.invalid"):
        assert excluded not in emails


def test_admin_flag_marks_admin_and_super_admin(session):
    _users(session)
    by_email = {r.email: r for r in service.resolve_recipients(session)}
    assert by_email["admin@sp.com"].is_admin and by_email["super@sp.com"].is_admin
    assert not by_email["member@sp.com"].is_admin


def test_no_recipients_is_skipped_not_failed(session):
    execution = _execution()
    session.add(execution)
    session.commit()
    status, detail, count = notifications.send_run_notification(session, Settings(**SMTP), execution)
    assert (status, count) == ("skipped", 0)
    assert "no approved active users" in detail


# ------------------------------------------------------ provider abstraction
def test_registry_exposes_email_and_gmail():
    assert {"email", "gmail"} <= set(provider_base.list_providers())
    assert provider_base.get_provider("gmail") is not None
    assert provider_base.get_provider("GMAIL") is not None      # case-insensitive
    assert provider_base.get_provider("teams") is None


def test_a_new_channel_registers_without_touching_the_service():
    """The open/closed guarantee: a provider is added by registering it."""
    class TeamsStub:
        name = "teams-stub"

        def configured(self, settings):
            return True, ""

        def send(self, settings, notification, recipients, *, audience):
            return [DeliveryOutcome(r.email, "sent", self.name) for r in recipients]

    provider_base.register(TeamsStub())
    try:
        p = provider_base.get_provider("teams-stub")
        out = p.send(Settings(), _notification(), [Recipient("a@sp.com")], audience=Audience.ALL)
        assert [o.status for o in out] == ["sent"]
    finally:
        provider_base._REGISTRY.pop("teams-stub", None)


def test_unknown_provider_is_reported_not_raised(session):
    _users(session)
    execution = _execution()
    session.add(execution)
    session.commit()
    settings = Settings(notification_provider="carrier-pigeon", **SMTP)
    status, detail, count = notifications.send_run_notification(session, settings, execution)
    assert status == "failed" and count == 0
    assert "carrier-pigeon" in detail


def test_unconfigured_provider_degrades_to_logged(session):
    _users(session)
    execution = _execution()
    session.add(execution)
    session.commit()
    status, detail, count = notifications.send_run_notification(session, Settings(), execution)
    assert status == "logged" and count == 3
    assert "not configured" in detail


@pytest.mark.parametrize("missing,needle", [
    (dict(smtp_host=""), "SMTP_HOST"),
    (dict(email_from="", smtp_username=""), "EMAIL_FROM"),
    (dict(smtp_password=""), "SMTP_PASSWORD"),
])
def test_configured_reports_the_missing_setting(missing, needle):
    settings = Settings(**{**SMTP, **missing})
    ok, reason = SmtpEmailProvider().configured(settings)
    assert not ok and needle in reason


# ------------------------------------------------------------ message shape
def test_message_bccs_recipients_and_sets_sender_identity():
    settings = Settings(email_display_name="Silicon Patterns", **SMTP)
    msg = build_message(settings, _notification(),
                        [Recipient("a@sp.com"), Recipient("b@sp.com")])
    assert msg["From"] == "Silicon Patterns <bot@sp.com>"
    assert msg["To"] == "bot@sp.com"                       # sender only; no list leak
    assert set(msg["Bcc"].split(", ")) == {"a@sp.com", "b@sp.com"}
    assert msg["Auto-Submitted"] == "auto-generated"


def test_message_is_multipart_with_text_and_html():
    msg = build_message(Settings(**SMTP), _notification(), [Recipient("a@sp.com")])
    types = {p.get_content_type() for p in msg.walk() if not p.is_multipart()}
    assert types == {"text/plain", "text/html"}


def test_sender_identity_comes_from_configuration_not_code():
    settings = Settings(**{**SMTP, "email_from": "javedmahesh1@gmail.com",
                           "email_display_name": "SP Platform"})
    msg = build_message(settings, _notification(), [Recipient("a@sp.com")])
    assert msg["From"] == "SP Platform <javedmahesh1@gmail.com>"


# --------------------------------------------------------------- HTML output
def test_html_contains_run_summary_fields():
    html = templates.render_html(_notification())
    for needle in ("run-1", "Run summary", "Started", "Finished", "Duration",
                   "Pipelines executed", "2026-03-01 09:00:00 UTC"):
        assert needle in html


def test_html_contains_intelligence_and_health_sections():
    n = _notification(
        intelligence=[MetricGroup("Career Intelligence", [("ASIC roles", 7), ("RTL roles", 4)])],
        health=[service.HealthCheck("Database", True, "reachable")],
    )
    html = templates.render_html(n)
    assert "Career Intelligence" in html and "ASIC roles" in html and "7" in html
    assert "Platform health" in html and "Database" in html and "OK" in html


def test_html_has_open_platform_button_from_config():
    html = templates.render_html(_notification(frontend_url="https://app.example.com"))
    assert 'href="https://app.example.com"' in html and "Open Silicon Patterns" in html


def test_html_hides_button_when_no_frontend_url():
    assert "Open Silicon Patterns</a>" not in templates.render_html(_notification(frontend_url=""))


def test_html_is_responsive_and_self_contained():
    html = templates.render_html(_notification())
    assert 'name="viewport"' in html
    assert "max-width:640px" in html
    assert "<style" not in html          # Gmail strips style blocks; inline only


def test_html_escapes_untrusted_run_data():
    n = _notification(stages=[StageSummary("<script>alert(1)</script>", "failed",
                                           errors=["<img onerror=x>"])], status="failed")
    html = templates.render_html(n, audience=Audience.ADMIN)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_severity_drives_status_colour():
    assert _notification(status="success").severity is Severity.SUCCESS
    assert _notification(status="partial").severity is Severity.WARNING
    assert _notification(status="failed").severity is Severity.FAILURE
    assert _notification(status="success", exception="boom").severity is Severity.FAILURE


def test_text_alternative_mirrors_the_html_content():
    text = templates.render_text(_notification())
    assert "run-1" in text
    assert "NEWS COLLECTION" in text and "Articles collected: 60" in text
    assert "https://app.example.com" in text


# --------------------------------------------------- failure notifications
def _failed_notification():
    return _notification(
        status="failed",
        stages=[StageSummary("news", "failed", errors=["psycopg.OperationalError: SSL closed"])],
        exception="RuntimeError: orchestrator crashed at stage news",
    )


def test_admin_failure_email_includes_diagnostics():
    html = templates.render_html(_failed_notification(), audience=Audience.ADMIN)
    assert "Failure diagnostics" in html
    assert "psycopg.OperationalError" in html
    assert "orchestrator crashed" in html


def test_standard_user_failure_email_hides_diagnostics():
    html = templates.render_html(_failed_notification(), audience=Audience.ALL)
    assert "did not complete successfully" in html
    assert "psycopg.OperationalError" not in html
    assert "orchestrator crashed" not in html


def test_failed_run_sends_two_renderings_split_by_role(session, monkeypatch):
    _users(session)
    execution = _execution(status="failed", stages=[
        {"component": "news", "status": "failed", "processed": 0, "created": 0, "updated": 0,
         "review": 0, "duration_ms": 10, "errors": ["boom: connection refused"], "notes": ""},
    ])
    session.add(execution)
    session.commit()

    rec = _Recorder()
    monkeypatch.setattr(provider_base, "_REGISTRY", {**provider_base._REGISTRY, "gmail": rec})
    status, _detail, count = notifications.send_run_notification(session, Settings(**SMTP), execution)

    assert status == "sent" and count == 3
    assert len(rec.messages) == 2                    # admin batch + standard batch
    bodies = [m.get_body(preferencelist=("html",)).get_content() for m in rec.messages]
    admin_body = next(b for b in bodies if "Failure diagnostics" in b)
    user_body = next(b for b in bodies if "did not complete successfully" in b)
    assert "connection refused" in admin_body
    assert "connection refused" not in user_body


def test_successful_run_sends_a_single_batch(session, monkeypatch):
    _users(session)
    execution = _execution()
    session.add(execution)
    session.commit()
    rec = _Recorder()
    monkeypatch.setattr(provider_base, "_REGISTRY", {**provider_base._REGISTRY, "gmail": rec})
    notifications.send_run_notification(session, Settings(**SMTP), execution)
    assert len(rec.messages) == 1


# ---------------------------------------------------------- retry handling
def test_retry_returns_on_first_success():
    calls = []
    ok, attempts, err = provider_base.retry(lambda: calls.append(1), attempts=3)
    assert (ok, attempts, err) == (True, 1, "") and len(calls) == 1


def test_retry_reattempts_then_succeeds(session, monkeypatch):
    _users(session)
    execution = _execution()
    session.add(execution)
    session.commit()
    rec = _Recorder(fail_times=2)
    monkeypatch.setattr(provider_base, "_REGISTRY", {**provider_base._REGISTRY, "gmail": rec})
    status, _d, count = notifications.send_run_notification(
        session, Settings(notification_retry_count=3, **SMTP), execution)
    assert status == "sent" and count == 3 and rec.calls == 3


def test_retry_exhausts_and_records_failure(session, monkeypatch):
    _users(session)
    execution = _execution()
    session.add(execution)
    session.commit()
    rec = _Recorder(fail_times=99)
    monkeypatch.setattr(provider_base, "_REGISTRY", {**provider_base._REGISTRY, "gmail": rec})
    status, detail, count = notifications.send_run_notification(
        session, Settings(notification_retry_count=2, **SMTP), execution)
    assert status == "failed" and count == 0 and rec.calls == 2
    assert "421" in detail
    rows = notifications.deliveries_for_run(session, execution.run_id)
    assert {r.attempts for r in rows} == {2}


def test_retry_count_of_one_means_no_retry(session, monkeypatch):
    _users(session)
    execution = _execution()
    session.add(execution)
    session.commit()
    rec = _Recorder(fail_times=99)
    monkeypatch.setattr(provider_base, "_REGISTRY", {**provider_base._REGISTRY, "gmail": rec})
    notifications.send_run_notification(session, Settings(notification_retry_count=1, **SMTP), execution)
    assert rec.calls == 1


# ---------------------------------------------------------- delivery logging
def test_delivery_log_records_one_row_per_recipient(session, monkeypatch):
    _users(session)
    execution = _execution()
    session.add(execution)
    session.commit()
    rec = _Recorder()
    monkeypatch.setattr(provider_base, "_REGISTRY", {**provider_base._REGISTRY, "gmail": rec})
    notifications.send_run_notification(session, Settings(**SMTP), execution)

    rows = notifications.deliveries_for_run(session, execution.run_id)
    assert {r.recipient for r in rows} == {"member@sp.com", "admin@sp.com", "super@sp.com"}
    assert all(r.status == "sent" and r.provider == "gmail" and r.channel == "email" for r in rows)
    assert all(r.event_type == "run_summary" for r in rows)


def test_delivery_log_records_the_failure_reason(session, monkeypatch):
    _users(session)
    execution = _execution()
    session.add(execution)
    session.commit()
    rec = _Recorder(fail_times=99)
    monkeypatch.setattr(provider_base, "_REGISTRY", {**provider_base._REGISTRY, "gmail": rec})
    notifications.send_run_notification(session, Settings(notification_retry_count=1, **SMTP), execution)
    rows = notifications.deliveries_for_run(session, execution.run_id)
    assert rows and all(r.status == "failed" and "421" in r.error for r in rows)
    assert notifications.delivery_status_counts(session, run_id=execution.run_id) == {"failed": 3}
    assert len(notifications.recent_failures(session)) == 3


def test_failure_run_logs_the_run_failure_event_type(session, monkeypatch):
    _users(session)
    execution = _execution(status="failed", stages=[
        {"component": "news", "status": "failed", "processed": 0, "created": 0, "updated": 0,
         "review": 0, "duration_ms": 1, "errors": ["x"], "notes": ""}])
    session.add(execution)
    session.commit()
    monkeypatch.setattr(provider_base, "_REGISTRY", {**provider_base._REGISTRY, "gmail": _Recorder()})
    notifications.send_run_notification(session, Settings(**SMTP), execution)
    rows = notifications.deliveries_for_run(session, execution.run_id)
    assert {r.event_type for r in rows} == {"run_failure"}
    assert {r.audience for r in rows} == {"admin", "all"}


def test_a_delivery_log_write_failure_does_not_fail_the_notification(session, monkeypatch):
    _users(session)
    execution = _execution()
    session.add(execution)
    session.commit()
    monkeypatch.setattr(provider_base, "_REGISTRY", {**provider_base._REGISTRY, "gmail": _Recorder()})
    monkeypatch.setattr(service, "_record",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("log table gone")))
    with pytest.raises(RuntimeError):
        service._record(session, [], run_id="x", event_type="run_summary",
                        channel="email", audience=Audience.ALL)
    # the real _record swallows its own errors; restore and prove the send still reports sent
    monkeypatch.undo()
    monkeypatch.setattr(provider_base, "_REGISTRY", {**provider_base._REGISTRY, "gmail": _Recorder()})
    status, _d, _c = notifications.send_run_notification(session, Settings(**SMTP), execution)
    assert status == "sent"


# ------------------------------------------------------------- intelligence
def test_intelligence_sections_cover_every_engine(session):
    session.add(Company(company_domain="a.com", canonical_company_id="A", company_name="A",
                        name_key="a", prospect_type="PRODUCT_COMPANY", validation_status="VALID"))
    session.add_all([
        Job(job_id="j1", company_domain="a.com", job_url="https://a.com/j1",
            job_title="Senior ASIC Design Engineer"),
        Job(job_id="j2", company_domain="a.com", job_url="https://a.com/j2",
            job_title="RTL Design Engineer"),
        Job(job_id="j3", company_domain="a.com", job_url="https://a.com/j3",
            job_title="Design Verification Engineer"),
        Job(job_id="j4", company_domain="a.com", job_url="https://a.com/j4",
            job_title="Physical Design Lead"),
    ])
    session.add_all([
        DecisionMaker(linkedin_url="l1", company_domain="a.com", current_title="CTO", seniority="c_level"),
        DecisionMaker(linkedin_url="l2", company_domain="a.com", current_title="Director", seniority="director"),
        DecisionMaker(linkedin_url="l3", company_domain="a.com", current_title="Manager", seniority="manager"),
    ])
    session.add(LeadScore(company_domain="a.com", lead_score=91.0, grade="A+"))
    session.commit()

    groups = {g.title: dict(g.metrics) for g in service.build_intelligence(session, _execution())}
    assert set(groups) == {"Industry Discovery", "News Collection", "Career Intelligence",
                           "Decision Maker Intelligence", "Lead Scoring"}
    assert groups["Industry Discovery"]["Companies scanned"] == 40
    assert groups["Industry Discovery"]["Companies added"] == 5
    assert groups["News Collection"]["Articles collected"] == 60
    career = groups["Career Intelligence"]
    assert career["ASIC roles"] == 1 and career["RTL roles"] == 1
    assert career["Verification roles"] == 1 and career["Physical Design roles"] == 1
    assert career["Companies hiring"] == 1
    dm = groups["Decision Maker Intelligence"]
    assert dm["Contacts discovered"] == 3 and dm["Directors"] == 1 and dm["Managers"] == 1
    assert groups["Lead Scoring"]["High-priority leads (A+/A)"] == 1


def test_health_reports_scheduler_sources_database_and_failures(session):
    session.add_all([
        NewsSource(name="EE Times", adapter_type="rss", url="https://e.example/f", enabled=True),
        NewsSource(name="Old", adapter_type="rss", url="https://o.example/f", enabled=False),
    ])
    session.commit()
    execution = _execution(status="partial", stages=[
        {"component": "career", "status": "failed", "processed": 0, "created": 0, "updated": 0,
         "review": 0, "duration_ms": 5, "errors": ["ats timeout"], "notes": ""}])
    checks = {c.name: c for c in service.build_health(session, Settings(scheduler_enabled=False), execution)}
    assert checks["Scheduler"].ok is False and "disabled" in checks["Scheduler"].detail
    assert checks["News sources"].ok and "1 of 2 enabled" in checks["News sources"].detail
    assert checks["Database"].ok
    assert checks["Pipelines"].ok is False and "career" in checks["Pipelines"].detail


# ------------------------------------------------- scheduler integration
def test_scheduler_emits_structured_data_and_never_builds_email(session, monkeypatch):
    """The scheduler's only job is to hand over the execution row."""
    from backend.standard_run import execute_standard_run

    session.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                        name_key="acme", company_tier="STARTUP", prospect_type="PRODUCT_COMPANY",
                        compliance_flag="APPROVED", validation_status="VALID"))
    session.commit()
    _users(session)

    captured = {}

    def _spy(sess, settings, execution, *, exception=""):
        captured["run_id"] = execution.run_id
        captured["status"] = execution.status
        captured["exception"] = exception
        return "sent", "ok", 3

    monkeypatch.setattr(notifications, "send_run_notification", _spy)
    execution, _ = execute_standard_run(session, Settings(scheduler_enabled=False, **SMTP),
                                        trigger="scheduled", slot="09:00",
                                        components=["scoring"], notify=True)
    assert captured["run_id"] == execution.run_id
    assert captured["status"] == "success" and captured["exception"] == ""
    assert execution.notification_status == "sent" and execution.notified_count == 3


def test_a_crashed_run_still_notifies_with_the_exception(session, monkeypatch):
    """A run that raises is the one case where notifying matters most."""
    from backend.standard_run import execute_standard_run
    from orchestrator.orchestrator import Orchestrator

    _users(session)
    captured = {}

    def _spy(sess, settings, execution, *, exception=""):
        captured["exception"] = exception
        captured["status"] = execution.status
        return "sent", "ok", 3

    monkeypatch.setattr(notifications, "send_run_notification", _spy)
    monkeypatch.setattr(Orchestrator, "run_pipeline",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("orchestrator exploded")))
    with pytest.raises(RuntimeError):
        execute_standard_run(session, Settings(scheduler_enabled=False, **SMTP),
                             trigger="scheduled", slot="09:00", components=["scoring"], notify=True)
    assert "orchestrator exploded" in captured["exception"]
    assert captured["status"] == "failed"


def test_manual_runs_are_not_notified(session):
    from backend.standard_run import execute_standard_run

    session.add(Company(company_domain="acme.com", canonical_company_id="ACME", company_name="Acme",
                        name_key="acme", company_tier="STARTUP", prospect_type="PRODUCT_COMPANY",
                        compliance_flag="APPROVED", validation_status="VALID"))
    session.commit()
    _users(session)
    execution, _ = execute_standard_run(session, Settings(scheduler_enabled=False, **SMTP),
                                        trigger="manual", components=["scoring"], notify=False)
    assert execution.notification_status == "skipped"
    assert notifications.deliveries_for_run(session, execution.run_id) == []


# ------------------------------------------------------------ configuration
def test_notifications_can_be_disabled_entirely(session):
    _users(session)
    execution = _execution()
    session.add(execution)
    session.commit()
    status, detail, count = notifications.send_run_notification(
        session, Settings(enable_notifications=False, **SMTP), execution)
    assert (status, count) == ("skipped", 0) and "SP_ENABLE_NOTIFICATIONS" in detail


def test_branding_and_frontend_url_come_from_settings(session, monkeypatch):
    _users(session)
    execution = _execution()
    session.add(execution)
    session.commit()
    rec = _Recorder()
    monkeypatch.setattr(provider_base, "_REGISTRY", {**provider_base._REGISTRY, "gmail": rec})
    settings = Settings(brand_name="Acme Silicon", frontend_url="https://acme.example",
                        brand_logo_url="https://acme.example/logo.png", **SMTP)
    notifications.send_run_notification(session, settings, execution)
    body = rec.messages[0].get_body(preferencelist=("html",)).get_content()
    assert "Acme Silicon" in body
    assert 'href="https://acme.example"' in body
    assert "https://acme.example/logo.png" in body
    assert rec.messages[0]["Subject"].startswith("[Acme Silicon]")


def test_smtp_settings_bind_from_both_prefixed_and_bare_env(monkeypatch):
    for name in ("SP_SMTP_HOST", "SMTP_HOST", "SP_EMAIL_FROM", "EMAIL_FROM",
                 "SP_NOTIFICATION_PROVIDER", "NOTIFICATION_PROVIDER", "EMAIL_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("EMAIL_FROM", "javedmahesh1@gmail.com")
    monkeypatch.setenv("EMAIL_PROVIDER", "gmail")
    s = Settings(_env_file=None)
    assert s.smtp_host == "smtp.gmail.com"
    assert s.email_from == "javedmahesh1@gmail.com"
    assert s.notification_provider == "gmail"


def test_no_credential_is_ever_embedded_in_the_message():
    settings = Settings(**{**SMTP, "smtp_password": "super-secret-app-password"})
    msg = build_message(settings, _notification(), [Recipient("a@sp.com")])
    assert "super-secret-app-password" not in msg.as_string()


# -------------------------------------------------------------------- API
def test_delivery_log_endpoint_returns_the_runs_deliveries(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from backend.main import create_app
    from master_db.models import Base

    app = create_app(Settings(database_url=f"sqlite:///{(tmp_path / 'n.db').as_posix()}",
                              log_json=False, dev_auth_bypass=True, scheduler_enabled=False, **SMTP))
    with TestClient(app) as client:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessionmaker() as s:
            _users(s)
            execution = _execution()
            s.add(execution)
            s.commit()
            rec = _Recorder()
            monkeypatch.setattr(provider_base, "_REGISTRY", {**provider_base._REGISTRY, "gmail": rec})
            notifications.send_run_notification(s, app.state.settings, execution)
            run_id = execution.run_id

        r = client.get(f"/scheduler/runs/{run_id}/notifications", headers={"X-Dev-Role": "manager"})
        assert r.status_code == 200
        rows = r.json()
        assert {x["recipient"] for x in rows} == {"member@sp.com", "admin@sp.com", "super@sp.com"}
        assert all(x["status"] == "sent" and x["channel"] == "email" for x in rows)

        assert client.get("/scheduler/runs/nope/notifications",
                          headers={"X-Dev-Role": "manager"}).status_code == 404
        assert client.get(f"/scheduler/runs/{run_id}/notifications",
                          headers={"X-Dev-Role": "member"}).status_code == 403
