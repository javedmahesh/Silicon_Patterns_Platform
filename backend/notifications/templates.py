"""HTML/text rendering for notifications.

Pure formatting over a :class:`RunNotification` — no DB, no network, no settings
lookups — so every template is unit-testable in isolation and a provider can render
without side effects.

Email-client constraints drive the markup: inline styles only (Gmail strips
``<style>`` blocks), tables for layout, no external CSS, and a max-width wrapper with
percentage-width cells so it degrades to a single column on a phone. Values are
escaped; nothing here interpolates unescaped run data.
"""
from __future__ import annotations

import html
from datetime import datetime

from backend.notifications.schemas import Audience, RunNotification, Severity

# Brand palette. Severity drives the header band and the status pill.
_ACCENT = "#0b5fff"
_INK = "#111827"
_MUTED = "#6b7280"
_LINE = "#e5e7eb"
_CANVAS = "#f6f7f9"

_SEVERITY_COLOR = {
    Severity.SUCCESS: "#0f7b3e",
    Severity.WARNING: "#a45c00",
    Severity.FAILURE: "#b3261e",
}
_STATUS_COLOR = {
    "success": "#0f7b3e", "partial": "#a45c00", "failed": "#b3261e",
    "skipped": _MUTED, "running": _ACCENT,
}


def _esc(v) -> str:
    return html.escape(str(v if v is not None else ""))


def fmt_dt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC") if dt else "—"


def fmt_duration(ms: int) -> str:
    s = max(0, ms or 0) / 1000
    if s < 60:
        return f"{s:.1f}s"
    m, rem = divmod(int(s), 60)
    if m < 60:
        return f"{m}m {rem}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


def subject(n: RunNotification) -> str:
    verb = {Severity.SUCCESS: "completed", Severity.WARNING: "completed with warnings",
            Severity.FAILURE: "FAILED"}[n.severity]
    return f"[{n.brand_name}] Platform run {verb} — {n.run_id}"


# --------------------------------------------------------------------- pieces
def _header(n: RunNotification) -> str:
    color = _SEVERITY_COLOR[n.severity]
    logo = (
        f'<img src="{_esc(n.logo_url)}" alt="{_esc(n.brand_name)}" width="36" height="36" '
        f'style="display:block;border:0;border-radius:8px" />'
        if n.logo_url else
        f'<div style="width:36px;height:36px;border-radius:8px;background:{_ACCENT};color:#fff;'
        f'font:700 16px/36px -apple-system,Segoe UI,Helvetica,Arial,sans-serif;text-align:center">SP</div>'
    )
    return f"""
<tr><td style="padding:22px 24px;border-bottom:4px solid {color}">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
    <td width="36" style="padding-right:12px;vertical-align:middle">{logo}</td>
    <td style="vertical-align:middle">
      <div style="font:600 16px/20px -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_INK}">{_esc(n.brand_name)}</div>
      <div style="font:400 13px/18px -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_MUTED}">Platform run report</div>
    </td>
    <td align="right" style="vertical-align:middle">
      <span style="display:inline-block;padding:5px 12px;border-radius:999px;background:{color};color:#fff;
                   font:700 11px/1 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;letter-spacing:.06em">
        {_esc(n.status.upper())}</span>
    </td>
  </tr></table>
</td></tr>"""


def _stat_cards(n: RunNotification) -> str:
    """Four headline numbers, two per row on narrow clients (50% width cells)."""
    cards = [
        ("Duration", fmt_duration(n.duration_ms)),
        ("Records processed", f"{n.records_processed:,}"),
        ("Pipelines executed", str(len(n.stages))),
        ("Failures", str(len(n.failed_stages))),
    ]
    cells = "".join(
        f'<td width="50%" style="padding:6px">'
        f'<div style="border:1px solid {_LINE};border-radius:10px;padding:12px 14px;background:#fff">'
        f'<div style="font:600 11px/1.4 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;'
        f'color:{_MUTED};text-transform:uppercase;letter-spacing:.05em">{_esc(label)}</div>'
        f'<div style="font:700 20px/1.3 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_INK}">{_esc(value)}</div>'
        f'</div></td>' + ("</tr><tr>" if i % 2 else "")
        for i, (label, value) in enumerate(cards)
    )
    return f'<tr><td style="padding:8px 18px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>{cells}</tr></table></td></tr>'


def _kv_table(rows: list[tuple[str, str]]) -> str:
    body = "".join(
        f'<tr><td style="padding:5px 0;font:400 13px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_MUTED};width:45%">{_esc(k)}</td>'
        f'<td style="padding:5px 0;font:600 13px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_INK}">{_esc(v)}</td></tr>'
        for k, v in rows
    )
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{body}</table>'


def _section(title: str, inner: str) -> str:
    return f"""
<tr><td style="padding:14px 24px 4px">
  <div style="font:700 13px/1.4 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_INK};
              text-transform:uppercase;letter-spacing:.06em;padding-bottom:8px">{_esc(title)}</div>
  {inner}
</td></tr>"""


def _run_summary(n: RunNotification) -> str:
    rows = [
        ("Run ID", n.run_id),
        ("Trigger", n.trigger + (f" @ {n.scheduled_slot}" if n.scheduled_slot else "")),
        ("Started", fmt_dt(n.started_at)),
        ("Finished", fmt_dt(n.finished_at)),
        ("Duration", fmt_duration(n.duration_ms)),
        ("Pipelines executed", ", ".join(n.pipelines_executed) or "—"),
    ]
    return _section("Run summary", _kv_table(rows))


def _intelligence(n: RunNotification) -> str:
    groups = [g for g in n.intelligence if not g.empty] or n.intelligence
    if not groups:
        return ""
    blocks = []
    for g in groups:
        rows = "".join(
            '<tr>'
            f'<td style="padding:4px 0;font:400 13px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_MUTED}">{_esc(k)}</td>'
            f'<td align="right" style="padding:4px 0;font:700 13px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_INK}">'
            f'{_esc(f"{v:,}" if isinstance(v, int) else v)}</td></tr>'
            for k, v in g.metrics
        )
        note = (f'<div style="font:400 12px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;'
                f'color:{_MUTED};padding-top:6px">{_esc(g.note)}</div>') if g.note else ""
        blocks.append(
            f'<div style="border:1px solid {_LINE};border-radius:10px;padding:12px 14px;margin-bottom:10px;background:#fff">'
            f'<div style="font:700 13px/1.4 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_INK};padding-bottom:6px">{_esc(g.title)}</div>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table>{note}</div>'
        )
    return _section("Platform intelligence", "".join(blocks))


def _stage_table(n: RunNotification) -> str:
    if not n.stages:
        return ""
    head = (
        f'<tr>'
        f'<th align="left" style="padding:7px 8px;border-bottom:2px solid {_LINE};font:600 11px/1.4 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_MUTED};text-transform:uppercase">Pipeline</th>'
        f'<th align="left" style="padding:7px 8px;border-bottom:2px solid {_LINE};font:600 11px/1.4 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_MUTED};text-transform:uppercase">Status</th>'
        f'<th align="right" style="padding:7px 8px;border-bottom:2px solid {_LINE};font:600 11px/1.4 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_MUTED};text-transform:uppercase">Processed</th>'
        f'<th align="right" style="padding:7px 8px;border-bottom:2px solid {_LINE};font:600 11px/1.4 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_MUTED};text-transform:uppercase">Time</th>'
        f'</tr>'
    )
    rows = "".join(
        f'<tr>'
        f'<td style="padding:7px 8px;border-bottom:1px solid {_LINE};font:400 13px/1.4 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_INK}">{_esc(s.component)}</td>'
        f'<td style="padding:7px 8px;border-bottom:1px solid {_LINE};font:600 13px/1.4 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_STATUS_COLOR.get(s.status, _INK)}">{_esc(s.status)}</td>'
        f'<td align="right" style="padding:7px 8px;border-bottom:1px solid {_LINE};font:400 13px/1.4 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_INK}">{s.processed:,}</td>'
        f'<td align="right" style="padding:7px 8px;border-bottom:1px solid {_LINE};font:400 13px/1.4 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_MUTED}">{_esc(fmt_duration(s.duration_ms))}</td>'
        f'</tr>'
        for s in n.stages
    )
    return _section("Pipelines", f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{head}{rows}</table>')


def _health(n: RunNotification) -> str:
    if not n.health:
        return ""
    rows = "".join(
        f'<tr>'
        f'<td style="padding:5px 0;font:400 13px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_MUTED};width:45%">{_esc(h.name)}</td>'
        f'<td style="padding:5px 0;font:600 13px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;'
        f'color:{"#0f7b3e" if h.ok else "#b3261e"}">{"OK" if h.ok else "ATTENTION"}'
        f'<span style="font-weight:400;color:{_MUTED}">{(" — " + _esc(h.detail)) if h.detail else ""}</span></td>'
        f'</tr>'
        for h in n.health
    )
    return _section("Platform health", f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table>')


def _failures(n: RunNotification, audience: Audience) -> str:
    """Admins see the exception text and per-stage errors; standard users see only
    which pipelines failed. Diagnostics can carry connection strings and stack
    fragments, so they never go to the whole user base."""
    if not n.failed_stages and not n.exception:
        return ""
    color = _SEVERITY_COLOR[Severity.FAILURE]
    if audience is Audience.ADMIN:
        items = "".join(
            f'<li style="margin-bottom:6px"><b>{_esc(s.component)}</b>: '
            f'{_esc("; ".join(s.errors)[:400] or s.notes or "failed")}</li>'
            for s in n.failed_stages
        )
        exc = (f'<div style="font:400 12px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;color:{_INK};'
               f'background:#fff;border:1px solid {_LINE};border-radius:8px;padding:10px;margin-top:8px;'
               f'white-space:pre-wrap;word-break:break-word">{_esc(n.exception[:1500])}</div>') if n.exception else ""
        inner = (f'<ul style="margin:0;padding-left:18px;font:400 13px/1.6 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_INK}">{items}</ul>{exc}')
    else:
        names = ", ".join(s.component for s in n.failed_stages) or "the platform run"
        inner = (f'<div style="font:400 13px/1.6 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_INK}">'
                 f'{_esc(names)} did not complete successfully. The platform team has been notified with '
                 f'full diagnostics; data from the last successful run is still available.</div>')
    return f"""
<tr><td style="padding:14px 24px 4px">
  <div style="border-left:4px solid {color};background:#fff;border:1px solid {_LINE};border-radius:10px;padding:12px 14px">
    <div style="font:700 13px/1.4 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{color};padding-bottom:6px">
      {"Failure diagnostics" if audience is Audience.ADMIN else "Run did not complete"}</div>
    {inner}
  </div>
</td></tr>"""


def _cta(n: RunNotification) -> str:
    if not n.frontend_url:
        return ""
    url = _esc(n.frontend_url)
    return f"""
<tr><td align="center" style="padding:20px 24px 6px">
  <a href="{url}" style="display:inline-block;background:{_ACCENT};color:#fff;text-decoration:none;
     padding:11px 22px;border-radius:8px;font:600 14px/1 -apple-system,Segoe UI,Helvetica,Arial,sans-serif">
     Open {_esc(n.brand_name)}</a>
</td></tr>"""


def _footer(n: RunNotification) -> str:
    return f"""
<tr><td style="padding:16px 24px 22px;border-top:1px solid {_LINE}">
  <div style="font:400 11px/1.6 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:{_MUTED}">
    {_esc(n.brand_name)} Platform · automated notification · please do not reply.<br/>
    You receive this because you have an active {_esc(n.brand_name)} account.
  </div>
</td></tr>"""


# --------------------------------------------------------------------- render
def render_html(n: RunNotification, *, audience: Audience = Audience.ALL) -> str:
    """The full responsive HTML body for one audience."""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{_esc(subject(n))}</title></head>
<body style="margin:0;padding:0;background:{_CANVAS}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{_CANVAS}">
<tr><td align="center" style="padding:20px 10px">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="max-width:640px;background:{_CANVAS};border:1px solid {_LINE};border-radius:14px;overflow:hidden">
    {_header(n)}
    {_stat_cards(n)}
    {_failures(n, audience)}
    {_run_summary(n)}
    {_intelligence(n)}
    {_stage_table(n)}
    {_health(n)}
    {_cta(n)}
    {_footer(n)}
  </table>
</td></tr></table>
</body></html>"""


def render_text(n: RunNotification, *, audience: Audience = Audience.ALL) -> str:
    """Plain-text alternative — required for a well-formed multipart email, and the
    only body some clients will show."""
    lines = [
        f"{n.brand_name} — platform run {n.status.upper()}",
        "",
        f"Run ID:    {n.run_id}",
        f"Trigger:   {n.trigger}" + (f" @ {n.scheduled_slot}" if n.scheduled_slot else ""),
        f"Started:   {fmt_dt(n.started_at)}",
        f"Finished:  {fmt_dt(n.finished_at)}",
        f"Duration:  {fmt_duration(n.duration_ms)}",
        f"Records:   {n.records_processed:,}",
        "",
    ]
    if n.failed_stages or n.exception:
        lines.append("FAILURES")
        if audience is Audience.ADMIN:
            for s in n.failed_stages:
                lines.append(f"  - {s.component}: {'; '.join(s.errors)[:300] or s.notes or 'failed'}")
            if n.exception:
                lines += ["", "Exception:", f"  {n.exception[:1000]}"]
        else:
            names = ", ".join(s.component for s in n.failed_stages) or "the platform run"
            lines.append(f"  {names} did not complete successfully. The platform team has full diagnostics.")
        lines.append("")
    for g in n.intelligence:
        if g.empty:
            continue
        lines.append(g.title.upper())
        lines += [f"  {k}: {v:,}" if isinstance(v, int) else f"  {k}: {v}" for k, v in g.metrics]
        lines.append("")
    if n.stages:
        lines.append("PIPELINES")
        lines += [f"  {s.component:<28} {s.status:<10} {s.processed:>8,}  {fmt_duration(s.duration_ms)}"
                  for s in n.stages]
        lines.append("")
    if n.health:
        lines.append("PLATFORM HEALTH")
        lines += [f"  {h.name}: {'OK' if h.ok else 'ATTENTION'}{(' — ' + h.detail) if h.detail else ''}"
                  for h in n.health]
        lines.append("")
    if n.frontend_url:
        lines += [f"Open {n.brand_name}: {n.frontend_url}", ""]
    lines.append(f"{n.brand_name} Platform · automated notification · please do not reply.")
    return "\n".join(lines)
