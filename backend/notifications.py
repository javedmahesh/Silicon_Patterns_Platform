"""Outlook / Microsoft Graph run-summary notifications.

After a SCHEDULED Standard Run, email a professional execution summary to every
ACTIVE Microsoft Entra user (pending/disabled/rejected/deleted are excluded). Sent
via Microsoft Graph ``sendMail`` using the client-credentials flow — reusing the
existing Entra app registration + client secret (backend/config.py). No new identity
infrastructure, and nothing here can fail the pipeline: every path is caught and
collapses to a recorded ``(status, detail, count)`` result.

Modes (Settings.notify_mode):
  * ``off``   — never send (records 'skipped').
  * ``graph`` — always attempt a real Graph send (records 'failed' with the reason
                if the app lacks Mail.Send / the mailbox isn't licensed).
  * ``auto``  — real send when a tenant + client id + secret + sender mailbox are all
                configured; otherwise log-only ('logged'). Default.

Real delivery requires the Entra app to hold the **Mail.Send application permission**
(admin-consented) and ``notify_sender_email`` to be a real licensed mailbox — an
external tenant configuration, not code. Until then 'auto' safely logs.
"""
from __future__ import annotations

import html
import logging

import httpx
from sqlalchemy.orm import Session

from backend import repositories as repo
from backend.config import Settings
from master_db.models import PipelineExecution

logger = logging.getLogger("backend.notifications")

_GRAPH = "https://graph.microsoft.com/v1.0"
_LOGIN = "https://login.microsoftonline.com"


def _sender(settings: Settings) -> str:
    return (settings.notify_sender_email or settings.bootstrap_admin_email or "").strip()


def _graph_configured(settings: Settings) -> bool:
    return bool(
        settings.microsoft_tenant_id
        and settings.microsoft_client_id
        and settings.microsoft_client_secret
        and _sender(settings)
    )


def send_run_notification(
    session: Session, settings: Settings, execution: PipelineExecution
) -> tuple[str, str, int]:
    """Return ``(notification_status, detail, notified_count)``. Never raises."""
    try:
        mode = (settings.notify_mode or "auto").strip().lower()
        if mode == "off":
            return "skipped", "notifications disabled (SP_NOTIFY_MODE=off)", 0

        recipients = [u.email for u in repo.list_active_users(session) if u.email]
        if not recipients:
            return "skipped", "no active users to notify", 0

        subject = _subject(execution)
        body_html = build_summary_html(execution)

        use_graph = mode == "graph" or (mode == "auto" and _graph_configured(settings))
        if not use_graph:
            logger.info(
                "[notify] log-only (mode=%s, graph not configured) — run %s summary for %d active users",
                mode, execution.run_id, len(recipients),
            )
            return "logged", (
                f"log-only (mode={mode}; Microsoft Graph sender/secret not configured) — "
                f"{len(recipients)} active recipients"
            ), len(recipients)

        _graph_send_mail(settings, recipients, subject, body_html)
        logger.info("[notify] sent run %s summary to %d active users", execution.run_id, len(recipients))
        return "sent", f"sent to {len(recipients)} active user(s) via {_sender(settings)}", len(recipients)

    except Exception as exc:  # never fail the pipeline
        msg = str(exc)[:500]
        logger.warning("[notify] failed to send run %s summary: %s", execution.run_id, msg)
        return "failed", msg, 0


# --------------------------------------------------------------- Microsoft Graph
def _graph_token(settings: Settings) -> str:
    url = f"{_LOGIN}/{settings.microsoft_tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": settings.microsoft_client_id,
        "client_secret": settings.microsoft_client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, data=data)
    if resp.status_code != 200:
        # AAD error bodies carry error/error_description, never our secret.
        raise RuntimeError(f"Graph token request failed ({resp.status_code}): {resp.text[:300]}")
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("Graph token response contained no access_token")
    return token


def _graph_send_mail(settings: Settings, recipients: list[str], subject: str, body_html: str) -> None:
    token = _graph_token(settings)
    sender = _sender(settings)
    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_html},
            # Sender mailbox as To; every active user BCC'd (no recipient list leaks).
            "toRecipients": [{"emailAddress": {"address": sender}}],
            "bccRecipients": [{"emailAddress": {"address": r}} for r in recipients],
        },
        "saveToSentItems": True,
    }
    url = f"{_GRAPH}/users/{sender}/sendMail"
    with httpx.Client(timeout=60) as client:
        resp = client.post(url, headers={"Authorization": f"Bearer {token}"}, json=message)
    if resp.status_code not in (202, 200):
        raise RuntimeError(f"Graph sendMail failed ({resp.status_code}): {resp.text[:300]}")


# --------------------------------------------------------------- email content
def _subject(e: PipelineExecution) -> str:
    return f"[Silicon Patterns] Standard Run {e.status.upper()} — {e.run_id}"


def _fmt_dt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC") if dt else "—"


def _fmt_duration(ms: int) -> str:
    s = (ms or 0) / 1000
    if s < 60:
        return f"{s:.1f}s"
    return f"{int(s // 60)}m {int(s % 60)}s"


_STATUS_COLOR = {"success": "#1a7f37", "partial": "#9a6700", "failed": "#cf222e",
                 "running": "#0969da", "skipped": "#6e7781"}


def build_summary_html(e: PipelineExecution) -> str:
    """A professional HTML execution summary. Pure formatting over the execution
    row's snapshotted fields — no DB access, so it's trivially unit-testable."""
    color = _STATUS_COLOR.get(e.status, "#24292f")
    totals = e.totals or {}
    stages = e.stages or []

    stage_rows = "".join(
        f"<tr>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eaecef'>{html.escape(str(s.get('component', '')))}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eaecef;color:{_STATUS_COLOR.get(s.get('status'), '#24292f')};font-weight:600'>{html.escape(str(s.get('status', '')))}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eaecef;text-align:right'>{s.get('processed', 0)}</td>"
        f"</tr>"
        for s in stages
    )

    def total_row(label: str, key: str) -> str:
        return (
            f"<tr><td style='padding:4px 10px'>{label}</td>"
            f"<td style='padding:4px 10px;text-align:right;font-weight:600'>{totals.get(key, 0):,}</td></tr>"
        )

    failure_block = ""
    if e.failure_count:
        failed = [s for s in stages if s.get("status") == "failed"]
        items = "".join(
            f"<li><b>{html.escape(str(s.get('component')))}</b>: "
            f"{html.escape('; '.join(s.get('errors', []))[:300] or 'failed')}</li>"
            for s in failed
        )
        failure_block = (
            f"<h3 style='color:#cf222e;margin:18px 0 6px'>Failures ({e.failure_count})</h3>"
            f"<ul style='margin:0;padding-left:20px;color:#57606a'>{items}</ul>"
        )

    return f"""\
<div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:640px;color:#24292f">
  <h2 style="margin:0 0 4px">Silicon Patterns — Standard Run summary</h2>
  <p style="margin:0 0 14px;color:#57606a">Automated pipeline execution report.</p>
  <table style="border-collapse:collapse;margin-bottom:8px">
    <tr><td style="padding:4px 10px;color:#57606a">Run ID</td><td style="padding:4px 10px;font-weight:600">{html.escape(e.run_id)}</td></tr>
    <tr><td style="padding:4px 10px;color:#57606a">Trigger</td><td style="padding:4px 10px">{html.escape(e.trigger)}{(' @ ' + html.escape(e.scheduled_slot)) if e.scheduled_slot else ''}</td></tr>
    <tr><td style="padding:4px 10px;color:#57606a">Overall status</td><td style="padding:4px 10px;color:{color};font-weight:700">{html.escape(e.status.upper())}</td></tr>
    <tr><td style="padding:4px 10px;color:#57606a">Start</td><td style="padding:4px 10px">{_fmt_dt(e.started_at)}</td></tr>
    <tr><td style="padding:4px 10px;color:#57606a">Finish</td><td style="padding:4px 10px">{_fmt_dt(e.finished_at)}</td></tr>
    <tr><td style="padding:4px 10px;color:#57606a">Duration</td><td style="padding:4px 10px">{_fmt_duration(e.duration_ms)}</td></tr>
    <tr><td style="padding:4px 10px;color:#57606a">Records processed</td><td style="padding:4px 10px">{e.records_processed:,}</td></tr>
  </table>

  <h3 style="margin:18px 0 6px">Engines</h3>
  <table style="border-collapse:collapse;width:100%;font-size:14px">
    <tr style="text-align:left;color:#57606a">
      <th style="padding:6px 10px;border-bottom:2px solid #d0d7de">Engine</th>
      <th style="padding:6px 10px;border-bottom:2px solid #d0d7de">Status</th>
      <th style="padding:6px 10px;border-bottom:2px solid #d0d7de;text-align:right">Records processed</th>
    </tr>
    {stage_rows}
  </table>

  <h3 style="margin:18px 0 6px">Platform totals</h3>
  <table style="border-collapse:collapse;font-size:14px">
    {total_row('Total companies', 'companies')}
    {total_row('Total opportunities', 'opportunities')}
    {total_row('Total decision makers', 'decision_makers')}
    {total_row('Total jobs', 'jobs')}
    {total_row('Total leads scored', 'leads_scored')}
  </table>
  {failure_block}
  <p style="margin:20px 0 0;color:#8b949e;font-size:12px">Silicon Patterns Platform · automated notification · do not reply.</p>
</div>"""
