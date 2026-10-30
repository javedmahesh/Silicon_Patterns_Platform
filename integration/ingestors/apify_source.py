"""Apify API adapter for Decision Maker Intelligence engine.

Orchestrates Apify actor calls, handles batching, and integrates with the
ApifyIngestor for bulk upsert to decision_makers table.

Execution lifecycle (per batch): start exactly ONE actor run, store its Run ID,
then poll that SAME run (``GET /actor-runs/{id}``) until it reaches a terminal
state. READY and RUNNING are normal, expected, non-terminal states — they are
polled, and NEVER cause a new run to be created. A new run is only ever created
when the run genuinely COULDN'T be created in the first place (network failure,
HTTP error, or a malformed create-response with no run id), retried up to
``retries`` times. Once a run id exists, this module commits to that run for the
rest of its life: a terminal failure (FAILED/ABORTED/TIMED-OUT) or a poll timeout
ends the batch as a failure, but never spawns a second run for it — see
:func:`_call_apify_actor`.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from config.apify import (
    APIFY_BASE_URL,
    APIFY_DIRECTOR_SENIORITY,
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_WAIT_SECONDS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_RETRIES,
    DEFAULT_RETRY_BACKOFF,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TOTAL_RESULTS,
    load_apify_credentials,
)
from integration.ingestors.apify import ApifyIngestor
from integration.ingestors.base import IngestionResult
from master_db.models import ApifyActorRun, Company

logger = logging.getLogger(__name__)


class ApifyError(Exception):
    """Raised when an Apify API call fails, or an actor run does not succeed.

    ``status``, when known, carries the actor run's real terminal/non-terminal
    status (e.g. "FAILED", "ABORTED", "TIMED-OUT") so callers can record it
    accurately instead of collapsing every failure into one generic bucket.
    ``None`` means the status is genuinely unknown (transport error, malformed
    response, or the run couldn't be created at all).

    ``run_id``, when known, is the ONE run this batch created (see module
    docstring) — present whenever the failure happened AFTER a run was
    successfully created (terminal failure / poll timeout), absent when the
    failure happened BEFORE any run existed (creation itself failed).
    """

    def __init__(self, message: str, *, status: str | None = None, run_id: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.run_id = run_id


def _batch_companies(companies: list[Company], batch_size: int = DEFAULT_BATCH_SIZE) -> list[list[Company]]:
    """Split companies into batches for sequential Apify calls."""
    return [companies[i : i + batch_size] for i in range(0, len(companies), batch_size)]


# Apify actor-run terminal states. READY and RUNNING are deliberately absent —
# they are the normal non-terminal states a fresh/in-progress run reports, and
# are handled by polling, never by treating them as an error (that was the bug).
# Any OTHER status Apify may report (e.g. "ABORTING", "TIMING-OUT") is likewise
# treated as non-terminal (kept polling) rather than guessed at.
_TERMINAL_FAILURE_STATUSES = frozenset({"FAILED", "ABORTED", "TIMED-OUT"})
_TERMINAL_STATUSES = _TERMINAL_FAILURE_STATUSES | {"SUCCEEDED"}


def _parse_run_response(payload: Any) -> dict[str, Any]:
    """Extract and validate the actor-run object from an Apify API response.

    Apify wraps the run object in a top-level ``data`` envelope, e.g.
    ``{"data": {"id": ..., "status": ..., "defaultDatasetId": ..., ...}}`` — for
    BOTH the run-creation response and the run-status-poll response (same
    shape). Reading fields off the wrong level silently produces ``None`` for
    everything and makes a real actor start look like a failure — so this
    always raises :class:`ApifyError` on a missing/null/malformed envelope
    rather than returning a dict with missing fields.
    """
    if not isinstance(payload, dict):
        raise ApifyError("Malformed Apify response: expected a JSON object")
    run = payload.get("data")
    if not isinstance(run, dict):
        raise ApifyError("Malformed Apify response: missing or invalid 'data' object")
    if not run.get("id"):
        raise ApifyError("Malformed Apify response: run object has no 'id'")
    return run


def _create_run(
    actor_id: str, actor_input: dict[str, Any], headers: dict[str, str], timeout_seconds: int,
) -> dict[str, Any]:
    """POST once to start a new actor run. Returns the parsed run object.

    This is the ONLY function in the module that creates a run — and the ONLY
    failure mode a caller's retry loop may respond to by trying again (a fresh
    POST). Raises :class:`ApifyError` (``status=None``, ``run_id=None``) on a
    transport error, non-2xx response, or a malformed/id-less response body.
    """
    url = f"{APIFY_BASE_URL}/acts/{actor_id}/runs"
    with httpx.Client(timeout=timeout_seconds) as client:
        resp = client.post(url, json=actor_input, headers=headers)
        resp.raise_for_status()
    try:
        payload = resp.json()
    except ValueError as e:
        raise ApifyError(f"Malformed Apify response: invalid JSON ({e})") from e
    return _parse_run_response(payload)


def _get_run_status(run_id: str, headers: dict[str, str], timeout_seconds: int) -> dict[str, Any]:
    """GET the current state of an EXISTING run by id. Never creates a run —
    run ids are unique platform-wide, so no actor id is needed to look one up."""
    url = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
    with httpx.Client(timeout=timeout_seconds) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
    try:
        payload = resp.json()
    except ValueError as e:
        raise ApifyError(f"Malformed Apify response: invalid JSON ({e})") from e
    return _parse_run_response(payload)


def _fetch_dataset_items(dataset_id: str, headers: dict[str, str], timeout_seconds: int) -> list[dict[str, Any]]:
    """GET dataset items. Only ever called after a run reaches SUCCEEDED — never
    while the actor is still executing."""
    url = f"{APIFY_BASE_URL}/datasets/{dataset_id}/items?format=json"
    with httpx.Client(timeout=timeout_seconds) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
    return resp.json()


def _call_apify_actor(
    actor_id: str,
    api_token: str,
    company_domains: list[str],
    seniority_levels: list[str] | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    retries: int = DEFAULT_RETRIES,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    max_wait_seconds: int = DEFAULT_MAX_WAIT_SECONDS,
    batch_label: str = "",
    total_results: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run exactly ONE Apify actor run for this batch, and poll it to completion.

    Lifecycle (fixes the duplicate-run bug — see module docstring):

    1. CREATE (retried up to ``retries`` times, ONLY on a transport/HTTP/
       malformed-response failure — i.e. before any run id exists).
    2. Once a run id exists: POLL that SAME run (``GET /actor-runs/{id}``) every
       ``poll_interval_seconds``, up to a total of ``max_wait_seconds``.
       READY/RUNNING (or any other non-terminal status Apify may report) just
       keep the poll going — never creates a new run.
    3. SUCCEEDED -> fetch the dataset (only now, never while still executing).
       FAILED/ABORTED/TIMED-OUT, or a poll timeout -> raise, batch fails — still
       never creates a second run for this batch.

    Args:
        timeout_seconds: per-HTTP-call timeout (create / each poll / dataset fetch).
        retries: max run-CREATION attempts (not poll attempts).
        poll_interval_seconds: delay between status polls of the one run.
        max_wait_seconds: total budget to wait for that one run to finish.
        batch_label: short prefix (e.g. "[batch 2/5]") for log attribution.

    Returns:
        (records, run_info). ``run_info`` additionally carries ``poll_count``.

    Raises:
        ApifyError: creation failed after ``retries`` attempts (``run_id=None``),
        or the one run that WAS created ended in terminal failure / poll timeout
        (``run_id=<that run's id>`` — never retried as a new run).
    """
    if not api_token or not actor_id:
        raise ApifyError("Apify credentials not configured (set APIFY_API_TOKEN and APIFY_ACTOR_ID)")

    if not company_domains:
        return [], {}

    # Default to director+ filtering, using THIS actor's exact enum vocabulary.
    if seniority_levels is None:
        seniority_levels = list(APIFY_DIRECTOR_SENIORITY)

    # The actor caps companyDomain at 10 items and wants bare domains (no www/scheme).
    normalized_domains = []
    for d in company_domains:
        d = (d or "").strip().lower()
        if d.startswith("www."):
            d = d[4:]
        if d:
            normalized_domains.append(d)
    normalized_domains = list(dict.fromkeys(normalized_domains))[:10]  # de-dupe, cap at 10

    # Construct Apify actor input (field names + enum values verified against the
    # leads-scraper-ppe build input schema). ``total_results`` is the per-run lead
    # cap; the manual per-company job passes each company's requested count here (one
    # domain per run), clamped to the actor's documented 1..30000 range.
    requested = DEFAULT_TOTAL_RESULTS if total_results is None else max(1, min(int(total_results), 30000))
    actor_input = {
        "companyDomain": normalized_domains,
        "seniority": seniority_levels,
        "includeEmails": True,
        "totalResults": requested,
    }
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    label = f" {batch_label}" if batch_label else ""

    started_at = datetime.now(timezone.utc)
    last_error: ApifyError | None = None

    # ---- Phase 1: create exactly one run — retried only if creation itself fails.
    run_id: str | None = None
    status: str | None = None
    status_message = ""
    run: dict[str, Any] = {}
    for attempt in range(1, retries + 1):
        try:
            logger.info(
                f"[Apify]{label} CREATING actor run (attempt {attempt}/{retries}, "
                f"{len(normalized_domains)} companies)"
            )
            run = _create_run(actor_id, actor_input, headers, timeout_seconds)
            run_id = run["id"]
            status = run.get("status")
            status_message = run.get("statusMessage") or ""
            logger.info(f"[Apify]{label} run {run_id} created — status={status}")
            break
        except (ApifyError, httpx.HTTPError) as e:
            last_error = e if isinstance(e, ApifyError) else ApifyError(f"HTTP error creating run: {e}")
            if attempt < retries:
                backoff = DEFAULT_RETRY_BACKOFF ** (attempt - 1)
                logger.warning(
                    f"[Apify]{label} RETRY — run creation failed (attempt {attempt}/{retries}): "
                    f"{last_error}. Creating a NEW run attempt in {backoff:.1f}s..."
                )
                time.sleep(backoff)
            else:
                logger.error(f"[Apify]{label} could not create a run after {retries} attempts: {last_error}")

    if run_id is None:
        raise last_error or ApifyError(f"Failed to create a run after {retries} attempts")

    # ---- Phase 2: poll THIS SAME run until terminal. Never creates another run.
    poll_count = 0
    deadline = time.monotonic() + max_wait_seconds
    while status not in _TERMINAL_STATUSES:
        if time.monotonic() >= deadline:
            raise ApifyError(
                f"Run {run_id} still {status} after {max_wait_seconds}s — poll timeout "
                f"(not retried as a new run)",
                status=status, run_id=run_id,
            )
        logger.info(
            f"[Apify]{label} run {run_id} status={status} — WAITING {poll_interval_seconds}s "
            f"before poll #{poll_count + 1}"
        )
        time.sleep(poll_interval_seconds)
        poll_count += 1
        run = _get_run_status(run_id, headers, timeout_seconds)
        status = run.get("status")
        status_message = run.get("statusMessage") or status_message
        logger.info(f"[Apify]{label} POLLING run {run_id} (#{poll_count}): status={status}")

    if status in _TERMINAL_FAILURE_STATUSES:
        detail = f" ({status_message})" if status_message else ""
        raise ApifyError(f"Run {run_id} ended with status {status}{detail}", status=status, run_id=run_id)

    # status == SUCCEEDED — fetch the dataset now, and only now.
    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        raise ApifyError(f"No dataset in run {run_id}", status=status, run_id=run_id)

    records = _fetch_dataset_items(dataset_id, headers, timeout_seconds)
    runtime = (datetime.now(timezone.utc) - started_at).total_seconds()
    logger.info(
        f"[Apify]{label} run {run_id} SUCCEEDED — {len(records)} records from dataset {dataset_id} "
        f"(polls={poll_count}, runtime={runtime:.1f}s)"
    )
    if status_message:
        logger.info(f"[Apify]{label} run {run_id} statusMessage: {status_message}")

    run_info = {
        "run_id": run_id,
        "status": status,
        "status_message": status_message,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc),
        "records_returned": len(records),
        "poll_count": poll_count,
    }
    return records, run_info


def import_decision_makers(session: Session, *, limit: int | None = None) -> IngestionResult:
    """Ingest decision makers from Apify for companies in the database.

    Steps:
    1. Load companies from master DB (all, or the first `limit` in benchmark mode)
    2. Batch companies (100 per call)
    3. Call Apify actor for each batch
    4. Collect all results
    5. Bulk upsert to decision_makers table via ApifyIngestor

    Args:
        limit: Benchmark mode. When set, restricts the run to the first `limit`
            companies (ordered by company_domain, for a reproducible subset) instead
            of the full company universe — for measuring real Apify yield/cost
            before running across everything. `None` (the default) is the unchanged
            production path: every company in the database. Writes still go through
            the same `session` — whatever database that's bound to (the configured
            runtime DB) is what benchmark mode writes to as well; nothing about
            *where* data is written changes.

    Returns:
        IngestionResult with counts and status. In benchmark mode, `notes` is
        prefixed with a compact yield/cost summary (companies/invocations/returned/
        inserted/updated/duplicates-ignored/failed-batches/runtime); the same
        numbers are also logged at INFO level as a labeled report.
    """
    start = time.perf_counter()
    api_token, actor_id = load_apify_credentials()
    if not api_token:
        result = IngestionResult(engine="decision_maker_intelligence")
        result.status = "skipped"
        result.notes = "No Apify API token (set APIFY_API_TOKEN)"
        return result

    # Fetch companies from DB — the full universe in production, or a deterministic
    # first-N subset (ordered by company_domain, so the same subset is picked every
    # run) when benchmarking.
    query = session.query(Company).order_by(Company.company_domain)
    if limit is not None:
        query = query.limit(limit)
    companies = query.all()
    if not companies:
        result = IngestionResult(engine="decision_maker_intelligence")
        result.notes = "No companies in database"
        return result

    mode_note = f" (BENCHMARK MODE: limit={limit})" if limit is not None else ""
    logger.info(f"[Apify] Starting Decision Maker Intelligence ingest for {len(companies)} companies{mode_note}")

    # Batch companies and call Apify
    batches = _batch_companies(companies, DEFAULT_BATCH_SIZE)
    all_records: list[dict[str, Any]] = []
    batch_errors: list[str] = []
    status_messages: list[str] = []
    actor_runs: list[ApifyActorRun] = []

    for i, batch in enumerate(batches, 1):
        domains = [c.company_domain for c in batch if c.company_domain]
        batch_label = f"[batch {i}/{len(batches)}]"
        logger.info(f"[Apify] {batch_label} starting — {len(domains)} companies")

        try:
            records, run_info = _call_apify_actor(
                actor_id=actor_id,
                api_token=api_token,
                company_domains=domains,
                batch_label=batch_label,
            )
            all_records.extend(records)

            status_message = run_info.get("status_message") or ""
            if status_message:
                status_messages.append(status_message)

            batch_runtime = 0.0
            if run_info.get("started_at") and run_info.get("finished_at"):
                batch_runtime = (run_info["finished_at"] - run_info["started_at"]).total_seconds()
            logger.info(
                f"[Apify] BATCH REPORT {batch_label}: companies={len(domains)} "
                f"run_id={run_info.get('run_id')} polls={run_info.get('poll_count', 0)} "
                f"runtime={batch_runtime:.1f}s leads_returned={len(records)}"
            )

            # Record the Apify actor run (a successful run with zero records —
            # e.g. an account/quota limit — still carries its statusMessage here).
            actor_run = ApifyActorRun(
                actor_id=actor_id,
                apify_run_id=run_info.get("run_id"),
                batch_index=i,
                company_count=len(domains),
                status=run_info.get("status", "unknown"),
                started_at=run_info.get("started_at"),
                finished_at=run_info.get("finished_at"),
                records_returned=run_info.get("records_returned", 0),
                error_message=status_message or None,
            )
            actor_runs.append(actor_run)

        except ApifyError as e:
            logger.error(
                f"[Apify] BATCH REPORT {batch_label}: companies={len(domains)} "
                f"run_id={e.run_id or '(none created)'} FAILED: {e}"
            )
            batch_errors.append(str(e))
            # Record the failed run attempt — the real terminal/non-terminal
            # status when known (FAILED/ABORTED/TIMED-OUT), else the generic
            # "failed" bucket for transport/malformed-response/poll-timeout
            # errors. apify_run_id is populated whenever a run WAS created
            # (e.run_id) even though it didn't end in success.
            actor_run = ApifyActorRun(
                actor_id=actor_id,
                apify_run_id=e.run_id,
                batch_index=i,
                company_count=len(domains),
                status=e.status or "failed",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                records_returned=0,
                error_message=str(e),
            )
            actor_runs.append(actor_run)

    # Write actor run records
    for run in actor_runs:
        session.add(run)
    session.commit()

    logger.info(f"[Apify] Collected {len(all_records)} total records. Ingesting...")

    # Ingest all records in bulk
    ingestor = ApifyIngestor(session, create_stub=False, mode="pipeline")
    result = ingestor.ingest_rows(all_records, source_label="apify")

    # Reflect batch outcomes in the result. If every batch failed and nothing was
    # fetched, this is a hard failure — not a hollow "success" with 0 rows.
    if batch_errors:
        result.errors.extend(batch_errors)
        if not all_records:
            result.status = "failed"
        elif result.status == "success":
            result.status = "partial"

    # Surface an informative statusMessage (e.g. a quota/usage-limit notice) even
    # when every batch technically succeeded with zero records, so that case isn't
    # silently indistinguishable from "nothing to ingest."
    if status_messages and not result.notes:
        result.notes = "Apify: " + "; ".join(dict.fromkeys(status_messages))

    # Always-on run summary (pure logging — never touches result/notes/status for
    # the production path, so this cannot change existing behaviour). Benchmark
    # mode gets its own richer, unchanged report below in addition to this.
    _inserted = max(0, result.rows_upserted - result.rows_duplicate)
    logger.info(
        f"[Apify] RUN SUMMARY: batches={len(batches)} companies={len(companies)} "
        f"leads_returned={result.rows_in} leads_inserted={_inserted} "
        f"leads_updated={result.rows_duplicate} failed_batches={len(batch_errors)} "
        f"runtime={time.perf_counter() - start:.2f}s"
    )

    if limit is not None:
        _log_benchmark_report(
            limit=limit, companies=companies, batches=batches, batch_errors=batch_errors,
            result=result, runtime_seconds=time.perf_counter() - start,
        )

    # Capture snapshots only when we actually fetched fresh records this run;
    # re-snapshotting unchanged rows after a failed fetch just pollutes history.
    if result.status in ("success", "partial") and all_records:
        _capture_decision_maker_snapshots(session)

    return result


@dataclass(slots=True)
class CompanyDmResult:
    """Outcome of running the Apify actor for ONE company (manual per-company job)."""
    company_domain: str
    records_returned: int
    inserted: int
    updated: int
    apify_run_id: str | None
    status: str          # "success" | "failed"
    error: str = ""

    @property
    def records_found(self) -> int:
        return self.inserted + self.updated


def import_decision_makers_for_company(
    session: Session, *, company: Company, requested_count: int,
    actor_id: str | None = None, api_token: str | None = None,
    pipeline_run_id: int | None = None,
) -> CompanyDmResult:
    """Run the Decision Maker Intelligence engine for ONE company with a per-company
    lead count, record the ApifyActorRun, and bulk-upsert the results.

    Reuses the EXACT same primitives as the pipeline stage — :func:`_call_apify_actor`
    (create-once / poll, retry + logging) and :class:`ApifyIngestor` (the same upsert)
    — so there is no duplicated scraper logic. Each call runs a single domain with its
    own ``totalResults``, which is how the manual job supports a different requested
    count per company. Never raises: a failure is captured on the returned result and
    recorded as an ApifyActorRun so the progress UI can show it.
    """
    if not api_token or not actor_id:
        _tok, _act = load_apify_credentials()
        api_token = api_token or _tok
        actor_id = actor_id or _act

    domain = (company.company_domain or "").strip()
    started = datetime.now(timezone.utc)
    try:
        records, run_info = _call_apify_actor(
            actor_id=actor_id, api_token=api_token, company_domains=[domain],
            batch_label=f"[dm {domain}]", total_results=requested_count,
        )
    except ApifyError as e:
        session.add(ApifyActorRun(
            actor_id=actor_id, apify_run_id=e.run_id, pipeline_run_id=pipeline_run_id,
            batch_index=0, company_count=1, status=e.status or "failed",
            started_at=started, finished_at=datetime.now(timezone.utc),
            records_returned=0, error_message=str(e)[:2000],
        ))
        session.commit()
        return CompanyDmResult(domain, 0, 0, 0, e.run_id, "failed", str(e))

    # Respect the user's desired number exactly: keep at most `requested_count` leads
    # for this company (the paid actor may return more than asked; we don't ingest the
    # surplus, so records_found never exceeds the requested count).
    capped = records[: max(0, int(requested_count))] if requested_count else records
    session.add(ApifyActorRun(
        actor_id=actor_id, apify_run_id=run_info.get("run_id"), pipeline_run_id=pipeline_run_id,
        batch_index=0, company_count=1, status=run_info.get("status", "unknown"),
        started_at=run_info.get("started_at"), finished_at=run_info.get("finished_at"),
        records_returned=len(capped), error_message=(run_info.get("status_message") or None),
    ))
    ingestor = ApifyIngestor(session, create_stub=False, mode="pipeline")
    result = ingestor.ingest_rows(capped, source_label="apify")
    session.commit()
    inserted = max(0, result.rows_upserted - result.rows_duplicate)
    return CompanyDmResult(
        company_domain=domain, records_returned=len(capped), inserted=inserted,
        updated=result.rows_duplicate, apify_run_id=run_info.get("run_id"), status="success",
    )


def _log_benchmark_report(
    *, limit: int, companies: list[Company], batches: list[list[Company]],
    batch_errors: list[str], result: IngestionResult, runtime_seconds: float,
) -> None:
    """Log (and prepend to ``result.notes``) a yield/cost report for a benchmark
    run — only ever called from the ``limit is not None`` path in
    :func:`import_decision_makers`, so it never touches the production run.

    Every count here is derived from fields ``ApifyIngestor``/``BaseIngestor``
    already compute on ``result`` (no extra DB round trip):
      - ``leads_inserted`` = rows_upserted - rows_duplicate (rows_duplicate is the
        subset of upserted rows that matched a linkedin_url already in the table
        from a *prior* run — i.e. "updated", not "new").
      - ``duplicates_ignored`` = rows that Apify returned more than once *within
        this run* (e.g. the same person surfacing across overlapping company
        batches) and were collapsed before ever reaching the database — distinct
        from "updated", which means "matched something already stored".
    """
    inserted = max(0, result.rows_upserted - result.rows_duplicate)
    updated = result.rows_duplicate
    duplicates_ignored = max(0, (result.rows_in - result.rows_rejected) - result.rows_upserted)

    summary = (
        f"BENCHMARK(limit={limit}): companies={len(companies)} "
        f"apify_invocations={len(batches)} leads_returned={result.rows_in} "
        f"leads_inserted={inserted} leads_updated={updated} "
        f"duplicates_ignored={duplicates_ignored} failed_batches={len(batch_errors)} "
        f"runtime={runtime_seconds:.2f}s"
    )
    result.notes = summary if not result.notes else f"{summary} | {result.notes}"

    logger.info("=" * 70)
    logger.info(f"[Apify] DECISION MAKER INTELLIGENCE — BENCHMARK REPORT (limit={limit})")
    logger.info(f"[Apify]   companies processed:       {len(companies)}")
    logger.info(f"[Apify]   apify actor invocations:   {len(batches)}")
    logger.info(f"[Apify]   leads returned:             {result.rows_in}")
    logger.info(f"[Apify]   leads inserted (new):       {inserted}")
    logger.info(f"[Apify]   leads updated (existing):   {updated}")
    logger.info(f"[Apify]   duplicate leads ignored:    {duplicates_ignored}")
    logger.info(f"[Apify]   failed batches:             {len(batch_errors)}")
    for i, err in enumerate(batch_errors, 1):
        logger.info(f"[Apify]     failed batch {i}: {err[:200]}")
    logger.info(f"[Apify]   runtime:                    {runtime_seconds:.2f}s")
    logger.info("=" * 70)


def _capture_decision_maker_snapshots(session: Session) -> None:
    """Capture current state of all decision makers for snapshot comparison.

    Leadership signals use snapshot comparisons to detect movement between runs.
    This is called after each decision_maker_intelligence ingest.
    """
    from datetime import datetime, timezone

    from master_db.models import DecisionMaker, DecisionMakerSnapshot

    snapshots_created = 0
    try:
        all_dms = session.query(DecisionMaker).all()
        now = datetime.now(timezone.utc)

        for dm in all_dms:
            snapshot = DecisionMakerSnapshot(
                decision_maker_id=dm.id,
                company_domain=dm.company_domain,
                current_title=dm.current_title,
                current_company=dm.resolved_company_name,
                seniority=dm.seniority,
                captured_at=now,
            )
            session.add(snapshot)
            snapshots_created += 1

        session.commit()
        logger.info(f"[Apify] Captured {snapshots_created} decision-maker snapshots")

    except Exception as e:
        logger.error(f"[Apify] Failed to capture snapshots: {e}")
        session.rollback()
        # Don't fail the ingest; snapshots are advisory
