"""Tests for the Apify Decision Maker Intelligence response-envelope fix.

Apify wraps every actor-run object in a top-level ``data`` key. Reading ``id``/
``status`` off the wrong (top) level -- the historical bug here -- silently
produces None for both, so a real actor start looks like a failure. These
tests pin: correct envelope parsing, the terminal/non-terminal state handling
it enables, the zero-record/quota-limit distinction, dataset-id safety, that
genuine transient failures still retry, and that no secret ever leaks into a
log/error message.

All HTTP is mocked via httpx.MockTransport (same pattern as
tests/test_supabase_adapter.py) -- no real network call, no Apify quota
consumed, ever. All DB access uses an isolated in-memory SQLite session
(same pattern as tests/test_orchestrator.py) -- master_local.db is never
touched.
"""
import json
import logging

import httpx
import pytest

import integration.ingestors.apify_source as apify_source
from integration.ingestors.apify_source import (
    ApifyError,
    _call_apify_actor,
    _parse_run_response,
    import_decision_makers,
)
from integration.normalizer import canonical_company_id, name_key
from master_db.local import make_session_factory
from master_db.models import ApifyActorRun, Company

ACTOR_ID = "test-actor"
API_TOKEN = "sekret-test-token-must-never-leak"


def _run_payload(run_id="run1", status="SUCCEEDED", dataset_id="ds1", status_message=None):
    data = {"id": run_id, "status": status}
    if dataset_id is not None:
        data["defaultDatasetId"] = dataset_id
    if status_message is not None:
        data["statusMessage"] = status_message
    return {"data": data}


def _mock_client(monkeypatch, handler):
    """Route every httpx.Client(...) construction in apify_source through
    *handler* via httpx.MockTransport -- no real network call is ever made."""
    real_client_cls = httpx.Client  # capture before patching so factory() doesn't recurse into itself
    def factory(*args, **kwargs):
        return real_client_cls(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(apify_source.httpx, "Client", factory)


def _no_sleep(monkeypatch):
    monkeypatch.setattr(apify_source.time, "sleep", lambda *_: None)


# --------------------------------------------------------- _parse_run_response
def test_parse_run_response_valid_extracts_id_status_dataset():
    run = _parse_run_response({"data": {"id": "r1", "status": "SUCCEEDED", "defaultDatasetId": "d1"}})
    assert run["id"] == "r1"
    assert run["status"] == "SUCCEEDED"
    assert run["defaultDatasetId"] == "d1"


def test_parse_run_response_extracts_status_message():
    run = _parse_run_response({"data": {"id": "r1", "status": "SUCCEEDED", "statusMessage": "quota exceeded"}})
    assert run["statusMessage"] == "quota exceeded"


def test_parse_run_response_missing_data_key():
    with pytest.raises(ApifyError, match="data"):
        _parse_run_response({"id": "r1", "status": "SUCCEEDED"})  # fields at the wrong (top) level


def test_parse_run_response_null_data():
    with pytest.raises(ApifyError, match="data"):
        _parse_run_response({"data": None})


def test_parse_run_response_non_object_data():
    with pytest.raises(ApifyError, match="data"):
        _parse_run_response({"data": "not-an-object"})
    with pytest.raises(ApifyError, match="data"):
        _parse_run_response({"data": [1, 2, 3]})


def test_parse_run_response_missing_id():
    with pytest.raises(ApifyError, match="id"):
        _parse_run_response({"data": {"status": "SUCCEEDED"}})


def test_parse_run_response_non_dict_payload():
    with pytest.raises(ApifyError):
        _parse_run_response(["not", "a", "dict"])


# --------------------------------------------------- _call_apify_actor: success
def test_call_apify_actor_succeeded_with_records(monkeypatch):
    records = [{"linkedin_url": "https://lnkd.in/x", "first_name": "A"}]
    calls = {"post": 0, "get": 0, "get_url": None}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            calls["post"] += 1
            return httpx.Response(201, json=_run_payload(run_id="r1", dataset_id="ds-correct"))
        calls["get"] += 1
        calls["get_url"] = str(request.url)
        return httpx.Response(200, json=records)

    _mock_client(monkeypatch, handler)
    out_records, run_info = _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], retries=1)

    assert out_records == records
    assert run_info["run_id"] == "r1"
    assert run_info["status"] == "SUCCEEDED"
    assert run_info["records_returned"] == 1
    assert calls["post"] == 1
    assert calls["get"] == 1
    assert "ds-correct" in calls["get_url"]  # dataset retrieval used the correctly parsed identifier


def test_call_apify_actor_succeeded_zero_records_no_retry(monkeypatch):
    calls = {"post": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            calls["post"] += 1
            return httpx.Response(201, json=_run_payload(dataset_id="ds1"))
        return httpx.Response(200, json=[])

    _mock_client(monkeypatch, handler)
    records, run_info = _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], retries=3)

    assert records == []
    assert run_info["status"] == "SUCCEEDED"
    assert run_info["records_returned"] == 0
    assert calls["post"] == 1  # a valid (empty) success must not retry the actor start


def test_call_apify_actor_quota_limit_message_surfaced_no_retry(monkeypatch):
    quota_msg = "You've exceeded your monthly run limit of 100 leads for Free Apify users."
    calls = {"post": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            calls["post"] += 1
            return httpx.Response(201, json=_run_payload(dataset_id="ds1", status_message=quota_msg))
        return httpx.Response(200, json=[])

    _mock_client(monkeypatch, handler)
    records, run_info = _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], retries=3)

    assert records == []
    assert run_info["status"] == "SUCCEEDED"
    assert run_info["status_message"] == quota_msg
    assert calls["post"] == 1  # quota-limited but a real success -- not a malformed-response retry


# ------------------------------------------------- terminal / non-terminal states
def test_call_apify_actor_failed_terminal_state_no_retry(monkeypatch):
    """A terminal FAILED status on the one run that WAS created must never spawn
    a second run — this is the core duplicate-run-prevention guarantee."""
    _no_sleep(monkeypatch)
    calls = {"post": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["post"] += 1
        return httpx.Response(201, json=_run_payload(status="FAILED"))

    _mock_client(monkeypatch, handler)
    with pytest.raises(ApifyError) as exc_info:
        _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], retries=3)

    assert exc_info.value.status == "FAILED"
    assert exc_info.value.run_id == "run1"  # the one run that was created
    assert calls["post"] == 1  # exactly ONE run created, regardless of `retries`


def test_call_apify_actor_aborted_terminal_state(monkeypatch):
    _no_sleep(monkeypatch)
    calls = {"post": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["post"] += 1
        return httpx.Response(201, json=_run_payload(status="ABORTED"))

    _mock_client(monkeypatch, handler)
    with pytest.raises(ApifyError) as exc_info:
        _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], retries=3)
    assert exc_info.value.status == "ABORTED"
    assert "ABORTED" in str(exc_info.value)
    assert calls["post"] == 1  # never retried — a run WAS created


def test_call_apify_actor_timed_out_terminal_state(monkeypatch):
    _no_sleep(monkeypatch)
    calls = {"post": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["post"] += 1
        return httpx.Response(201, json=_run_payload(status="TIMED-OUT"))

    _mock_client(monkeypatch, handler)
    with pytest.raises(ApifyError) as exc_info:
        _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], retries=3)
    assert exc_info.value.status == "TIMED-OUT"
    assert "TIMED-OUT" in str(exc_info.value)
    assert calls["post"] == 1  # never retried — a run WAS created


# ------------------------------------------------- READY/RUNNING: poll, don't retry
def test_call_apify_actor_ready_status_polls_same_run_until_succeeded(monkeypatch):
    """READY (the actor hasn't started executing yet) must be polled, not
    misclassified as an error — this was half of the original bug."""
    _no_sleep(monkeypatch)
    calls = {"post": 0, "get_status": 0, "get_dataset": 0}
    statuses = iter(["READY", "SUCCEEDED"])  # creation itself reports READY; then 2 polls

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            calls["post"] += 1
            return httpx.Response(201, json=_run_payload(run_id="run1", status="READY", dataset_id="ds1"))
        if "/actor-runs/" in str(request.url):
            calls["get_status"] += 1
            return httpx.Response(200, json=_run_payload(run_id="run1", status=next(statuses), dataset_id="ds1"))
        calls["get_dataset"] += 1
        return httpx.Response(200, json=[{"linkedin_url": "https://lnkd.in/x"}])

    _mock_client(monkeypatch, handler)
    records, run_info = _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], retries=3,
                                          poll_interval_seconds=0.01, max_wait_seconds=5)

    assert calls["post"] == 1        # exactly one run created
    assert calls["get_status"] == 2  # polled the SAME run: READY again, then SUCCEEDED
    assert calls["get_dataset"] == 1
    assert run_info["run_id"] == "run1"
    assert run_info["status"] == "SUCCEEDED"
    assert run_info["poll_count"] == 2
    assert len(records) == 1


def test_call_apify_actor_running_status_polls_same_run_until_succeeded(monkeypatch):
    """RUNNING must be polled, not misclassified as an error and retried with a
    brand-new actor run — the core bug this fix addresses."""
    _no_sleep(monkeypatch)
    calls = {"post": 0, "get_status": 0, "get_dataset": 0}
    statuses = iter(["RUNNING", "SUCCEEDED"])  # 2 polls: still running, then succeeded

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            calls["post"] += 1
            return httpx.Response(201, json=_run_payload(run_id="run1", status="RUNNING", dataset_id="ds1"))
        if "/actor-runs/" in str(request.url):
            calls["get_status"] += 1
            return httpx.Response(200, json=_run_payload(run_id="run1", status=next(statuses), dataset_id="ds1"))
        calls["get_dataset"] += 1
        return httpx.Response(200, json=[])

    _mock_client(monkeypatch, handler)
    records, run_info = _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], retries=3,
                                          poll_interval_seconds=0.01, max_wait_seconds=5)

    assert calls["post"] == 1        # exactly one run created — never a second one
    assert calls["get_status"] == 2  # polled the SAME run id every time
    assert run_info["run_id"] == "run1"
    assert run_info["status"] == "SUCCEEDED"
    assert run_info["poll_count"] == 2


def test_call_apify_actor_poll_timeout_does_not_create_new_run(monkeypatch):
    """A run still RUNNING after max_wait_seconds is a failure for THIS batch —
    never a reason to create a second run (cost protection)."""
    calls = {"post": 0, "get_status": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            calls["post"] += 1
            return httpx.Response(201, json=_run_payload(run_id="run1", status="RUNNING"))
        calls["get_status"] += 1
        return httpx.Response(200, json=_run_payload(run_id="run1", status="RUNNING"))

    _mock_client(monkeypatch, handler)
    with pytest.raises(ApifyError) as exc_info:
        _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], retries=3,
                          poll_interval_seconds=0.01, max_wait_seconds=0.03)

    assert exc_info.value.run_id == "run1"
    assert exc_info.value.status == "RUNNING"
    assert calls["post"] == 1  # still just the one run, despite never finishing
    assert calls["get_status"] >= 1  # it WAS polled before giving up


def test_call_apify_actor_poll_interval_and_max_wait_are_configurable(monkeypatch):
    """The polling interval and max wait are real, overridable parameters (env-var
    configurable defaults live in config/apify.py) — not hardcoded."""
    sleeps: list[float] = []
    monkeypatch.setattr(apify_source.time, "sleep", lambda s: sleeps.append(s))
    calls = {"get_status": 0}
    statuses = iter(["SUCCEEDED"])  # exactly 1 poll needed

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json=_run_payload(run_id="run1", status="RUNNING", dataset_id="ds1"))
        if "/actor-runs/" in str(request.url):
            calls["get_status"] += 1
            return httpx.Response(200, json=_run_payload(run_id="run1", status=next(statuses), dataset_id="ds1"))
        return httpx.Response(200, json=[])

    _mock_client(monkeypatch, handler)
    _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], poll_interval_seconds=1.75, max_wait_seconds=30)

    assert sleeps == [1.75]  # exactly one poll wait, at the configured interval
    assert calls["get_status"] == 1


def test_apify_config_poll_defaults_are_env_configurable(monkeypatch):
    """config/apify.py's polling defaults read from the environment, with sensible
    fallbacks when unset."""
    import importlib
    import config.apify as apify_config

    monkeypatch.setenv("APIFY_POLL_INTERVAL_SECONDS", "2.5")
    monkeypatch.setenv("APIFY_MAX_WAIT_SECONDS", "120")
    reloaded = importlib.reload(apify_config)
    try:
        assert reloaded.DEFAULT_POLL_INTERVAL_SECONDS == 2.5
        assert reloaded.DEFAULT_MAX_WAIT_SECONDS == 120
    finally:
        monkeypatch.delenv("APIFY_POLL_INTERVAL_SECONDS", raising=False)
        monkeypatch.delenv("APIFY_MAX_WAIT_SECONDS", raising=False)
        importlib.reload(apify_config)  # restore real defaults for any test after this one


# --------------------------------------------------- exactly one run per batch (cost protection)
def test_call_apify_actor_never_creates_second_run_across_full_lifecycle(monkeypatch):
    """End-to-end: READY -> RUNNING -> RUNNING -> SUCCEEDED, exactly one POST the
    entire time, no matter how many non-terminal states are reported in between."""
    _no_sleep(monkeypatch)
    calls = {"post": 0, "get_status": 0}
    # Creation itself reports READY; the 3 polls that follow report RUNNING, RUNNING,
    # SUCCEEDED — matching the docstring's "READY -> RUNNING -> RUNNING -> SUCCEEDED".
    statuses = iter(["RUNNING", "RUNNING", "SUCCEEDED"])

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            calls["post"] += 1
            return httpx.Response(201, json=_run_payload(run_id="run1", status="READY", dataset_id="ds1"))
        if "/actor-runs/" in str(request.url):
            calls["get_status"] += 1
            return httpx.Response(200, json=_run_payload(run_id="run1", status=next(statuses), dataset_id="ds1"))
        return httpx.Response(200, json=[])

    _mock_client(monkeypatch, handler)
    _, run_info = _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], poll_interval_seconds=0.01, max_wait_seconds=5)

    assert calls["post"] == 1
    assert run_info["run_id"] == "run1"
    assert run_info["poll_count"] == 3


# --------------------------------------------------------- malformed responses
def test_call_apify_actor_missing_data_envelope_fails_safely(monkeypatch):
    _no_sleep(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"id": "r1", "status": "SUCCEEDED"})  # old-bug shape: no "data"

    _mock_client(monkeypatch, handler)
    with pytest.raises(ApifyError) as exc_info:
        _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], retries=1)
    assert exc_info.value.status is None  # genuinely unknown, never misreported as a real terminal status


def test_call_apify_actor_null_data_fails_safely(monkeypatch):
    _no_sleep(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"data": None})

    _mock_client(monkeypatch, handler)
    with pytest.raises(ApifyError):
        _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], retries=1)


def test_call_apify_actor_succeeded_missing_dataset_id_never_fetches_dataset(monkeypatch):
    _no_sleep(monkeypatch)
    calls = {"post": 0, "get": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            calls["post"] += 1
            return httpx.Response(201, json={"data": {"id": "r1", "status": "SUCCEEDED"}})  # no defaultDatasetId
        calls["get"] += 1  # must never happen
        return httpx.Response(200, json=[])

    _mock_client(monkeypatch, handler)
    with pytest.raises(ApifyError, match="No dataset"):
        _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], retries=1)
    assert calls["get"] == 0  # dataset is never requested with a missing identifier


# --------------------------------------------------- transient failures still retry
def test_call_apify_actor_transient_http_error_still_retries(monkeypatch):
    _no_sleep(monkeypatch)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("boom", request=request)

    _mock_client(monkeypatch, handler)
    with pytest.raises(ApifyError):
        _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], retries=3)
    assert calls["n"] == 3  # genuine transport failures keep the existing retry count


# --------------------------------------------------------- secrets never leak
def test_call_apify_actor_never_logs_or_raises_the_token(monkeypatch, caplog):
    _no_sleep(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"data": None})  # malformed -> exercises the error/log path

    _mock_client(monkeypatch, handler)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ApifyError) as exc_info:
            _call_apify_actor(ACTOR_ID, API_TOKEN, ["acme.com"], retries=1)

    assert API_TOKEN not in str(exc_info.value)
    assert all(API_TOKEN not in record.getMessage() for record in caplog.records)


# --------------------------------------------------- import_decision_makers (integration)
@pytest.fixture()
def session():
    Session = make_session_factory(":memory:")
    with Session() as s:
        s.add(Company(company_domain="acme.com", canonical_company_id=canonical_company_id("acme.com", "Acme"),
                      company_name="Acme", name_key=name_key("Acme"), company_tier="STARTUP",
                      prospect_type="PRODUCT_COMPANY", compliance_flag="APPROVED", validation_status="VALID"))
        s.commit()
        yield s


def test_import_decision_makers_quota_limited_run_is_success_not_failure(session, monkeypatch):
    quota_msg = "You've exceeded your monthly run limit of 100 leads for Free Apify users."

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json=_run_payload(dataset_id="ds1", status_message=quota_msg))
        return httpx.Response(200, json=[])

    _mock_client(monkeypatch, handler)
    monkeypatch.setattr(apify_source, "load_apify_credentials", lambda: ("tok", ACTOR_ID))

    result = import_decision_makers(session)

    assert result.status == "success"  # a quota-limited-but-successful run is not a failure
    assert quota_msg in result.notes
    runs = session.query(ApifyActorRun).all()
    assert len(runs) == 1
    assert runs[0].status == "SUCCEEDED"  # not the generic "failed" bucket
    assert runs[0].error_message == quota_msg


def test_import_decision_makers_records_real_terminal_status(session, monkeypatch):
    _no_sleep(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json=_run_payload(status="ABORTED"))

    _mock_client(monkeypatch, handler)
    monkeypatch.setattr(apify_source, "load_apify_credentials", lambda: ("tok", ACTOR_ID))

    result = import_decision_makers(session)

    assert result.status == "failed"  # nothing fetched at all
    runs = session.query(ApifyActorRun).all()
    assert len(runs) == 1
    assert runs[0].status == "ABORTED"  # accurately represented, not a generic "failed" bucket
    assert runs[0].apify_run_id == "run1"  # the one run that WAS created, even though it failed


# --------------------------------------------------- benchmark mode (limit=)
def _seed_companies(session, n: int, prefix: str = "co") -> None:
    for i in range(n):
        domain = f"{prefix}{i}.example"
        session.add(Company(
            company_domain=domain, canonical_company_id=canonical_company_id(domain, f"Co {i}"),
            company_name=f"Co {i}", name_key=name_key(f"Co {i}"), company_tier="STARTUP",
            prospect_type="PRODUCT_COMPANY", compliance_flag="APPROVED", validation_status="VALID",
        ))
    session.commit()


def _domain_capturing_handler(seen: list[str], records=()):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            body = json.loads(request.content)
            seen.extend(body["companyDomain"])
            return httpx.Response(201, json=_run_payload(dataset_id="ds1"))
        return httpx.Response(200, json=list(records))
    return handler


def test_limit_caps_and_orders_companies_by_domain(session, monkeypatch):
    """Benchmark mode (limit=N) restricts the run to the first N companies, ordered
    by company_domain for a reproducible subset -- not the full universe."""
    _seed_companies(session, 5)  # co0..co4.example; fixture already seeded acme.com
    # alphabetical: acme.com, co0.example, co1.example, co2.example, co3.example, co4.example
    seen: list[str] = []
    _mock_client(monkeypatch, _domain_capturing_handler(seen))
    monkeypatch.setattr(apify_source, "load_apify_credentials", lambda: ("tok", ACTOR_ID))

    result = import_decision_makers(session, limit=3)

    assert seen == ["acme.com", "co0.example", "co1.example"]
    assert "BENCHMARK(limit=3)" in result.notes
    assert "companies=3" in result.notes
    assert "apify_invocations=1" in result.notes


def test_limit_none_processes_every_company_and_adds_no_benchmark_notes(session, monkeypatch):
    """The default (no --limit) is the unchanged production path: every company is
    included and no benchmark report is attached to notes."""
    _seed_companies(session, 3)
    seen: list[str] = []
    _mock_client(monkeypatch, _domain_capturing_handler(seen))
    monkeypatch.setattr(apify_source, "load_apify_credentials", lambda: ("tok", ACTOR_ID))

    result = import_decision_makers(session)  # limit omitted

    assert sorted(seen) == ["acme.com", "co0.example", "co1.example", "co2.example"]
    assert "BENCHMARK" not in result.notes


def test_benchmark_report_counts_inserted_vs_duplicates_ignored_within_run(session, monkeypatch):
    """Two records sharing a linkedin_url within the SAME run collapse to one row
    (a within-run duplicate, ignored) -- distinct from an update against a row that
    already existed before this run."""
    records = [
        {"linkedinUrl": "https://linkedin.com/in/a", "firstName": "Alice", "lastName": "A",
         "position": "VP Engineering", "organizationWebsite": "https://acme.com"},
        {"linkedinUrl": "https://linkedin.com/in/a", "firstName": "Alice", "lastName": "A2",
         "position": "VP Engineering (refreshed)", "organizationWebsite": "https://acme.com"},
        {"linkedinUrl": "https://linkedin.com/in/b", "firstName": "Bob", "lastName": "B",
         "position": "Director", "organizationWebsite": "https://acme.com"},
    ]
    _mock_client(monkeypatch, _domain_capturing_handler([], records=records))
    monkeypatch.setattr(apify_source, "load_apify_credentials", lambda: ("tok", ACTOR_ID))

    result = import_decision_makers(session, limit=1)

    assert "leads_returned=3" in result.notes
    assert "leads_inserted=2" in result.notes       # Alice (last occurrence) + Bob
    assert "leads_updated=0" in result.notes        # nothing pre-existed
    assert "duplicates_ignored=1" in result.notes   # Alice's first occurrence, collapsed


def test_benchmark_report_counts_updates_on_rerun(session, monkeypatch):
    """A record whose linkedin_url already exists (from a prior run) is reported as
    updated, not inserted, the second time it's ingested."""
    record = {"linkedinUrl": "https://linkedin.com/in/c", "firstName": "Carol", "lastName": "C",
              "position": "Director", "organizationWebsite": "https://acme.com"}
    _mock_client(monkeypatch, _domain_capturing_handler([], records=[record]))
    monkeypatch.setattr(apify_source, "load_apify_credentials", lambda: ("tok", ACTOR_ID))

    import_decision_makers(session, limit=1)  # first run: inserts Carol
    result2 = import_decision_makers(session, limit=1)  # second run: same person again

    assert "leads_inserted=0" in result2.notes
    assert "leads_updated=1" in result2.notes


def test_benchmark_report_shows_failed_batches(session, monkeypatch):
    """A benchmark run where every batch fails still gets a report (with
    failed_batches counted) -- not silently skipped just because the overall
    result is 'failed'."""
    _no_sleep(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json=_run_payload(status="ABORTED"))

    _mock_client(monkeypatch, handler)
    monkeypatch.setattr(apify_source, "load_apify_credentials", lambda: ("tok", ACTOR_ID))

    result = import_decision_makers(session, limit=1)

    assert result.status == "failed"
    assert "failed_batches=1" in result.notes
    assert "apify_invocations=1" in result.notes
    assert "runtime=" in result.notes
