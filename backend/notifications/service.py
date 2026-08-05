"""The notification service — the only thing the scheduler talks to.

Responsibilities, in order:

1. Build a channel-neutral :class:`RunNotification` from a completed
   ``pipeline_executions`` row plus a few aggregate queries (the intelligence
   figures the stage JSON doesn't carry).
2. Resolve recipients from the user table — active + approved only.
3. Hand the payload to the configured provider, once per audience.
4. Record a :class:`NotificationDelivery` row per recipient.
5. Return a run-level ``(status, detail, count)`` rollup for the execution row.

Nothing here raises. A misconfigured provider, an SMTP outage, or a bad template
degrades to a recorded outcome — the scheduler's contract is that notification
never fails a run.
"""
from __future__ import annotations

import logging
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend import repositories as repo
from backend.config import Settings
from backend.notifications import providers as provider_registry
from backend.notifications.schemas import (
    Audience,
    DeliveryOutcome,
    HealthCheck,
    MetricGroup,
    Recipient,
    RunNotification,
    StageSummary,
)
from master_db.models import (
    Company,
    DecisionMaker,
    Job,
    LeadScore,
    NewsSource,
    NotificationDelivery,
    PipelineExecution,
)

logger = logging.getLogger("backend.notifications.service")

ADMIN_ROLES = ("admin", "super_admin")

# Engineering disciplines called out in the Career Intelligence block. Matched
# case-insensitively against job_title; a posting can count in more than one bucket
# ("RTL Design & Verification Engineer") because that is genuinely what it is.
_ROLE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ASIC roles", ("asic",)),
    ("RTL roles", ("rtl",)),
    ("Verification roles", ("verification", "dv engineer", "design verification")),
    ("Physical Design roles", ("physical design", "pnr", "place and route", "backend design")),
)


# --------------------------------------------------------------- recipients
def resolve_recipients(session: Session) -> list[Recipient]:
    """Approved, active users — and nobody else.

    ``repo.list_active_users`` is already the platform's definition of that
    (``status == 'active' AND is_active``), which excludes pending-approval,
    disabled, rejected and soft-deleted accounts. Reusing it means the notification
    audience can never drift from the authentication audience.
    """
    out: list[Recipient] = []
    for u in repo.list_active_users(session):
        email = (u.email or "").strip()
        if not email or email.endswith("@deleted.invalid"):
            continue
        out.append(Recipient(email=email, name=(u.full_name or "").strip(),
                             is_admin=u.role in ADMIN_ROLES))
    return out


# --------------------------------------------------------------- intelligence
def _stage_map(execution: PipelineExecution) -> dict[str, dict]:
    return {s.get("component", ""): s for s in (execution.stages or [])}


def _grade_counts(session: Session) -> dict[str, int]:
    rows = session.execute(select(LeadScore.grade, func.count()).group_by(LeadScore.grade)).all()
    return {g: n for g, n in rows}


def _career_metrics(session: Session, stage: dict) -> MetricGroup:
    total_jobs = session.scalar(select(func.count()).select_from(Job)) or 0
    hiring = session.scalar(select(func.count(func.distinct(Job.company_domain))).select_from(Job)) or 0
    titles = list(session.scalars(select(Job.job_title)))
    lowered = [(t or "").lower() for t in titles]
    metrics: list[tuple[str, int | str]] = [
        ("Jobs discovered this run", int(stage.get("created", 0) or 0)),
        ("Jobs tracked", total_jobs),
        ("Companies hiring", hiring),
    ]
    for label, needles in _ROLE_PATTERNS:
        metrics.append((label, sum(1 for t in lowered if any(nd in t for nd in needles))))
    return MetricGroup("Career Intelligence", metrics, note=stage.get("notes", "")[:200])


def _decision_maker_metrics(session: Session) -> MetricGroup:
    rows = session.execute(
        select(DecisionMaker.seniority, func.count()).group_by(DecisionMaker.seniority)
    ).all()
    by_seniority = Counter({(s or "").strip().lower(): n for s, n in rows})

    def band(*keys: str) -> int:
        return sum(n for k, n in by_seniority.items() if any(x in k for x in keys))

    total = sum(by_seniority.values())
    return MetricGroup(
        "Decision Maker Intelligence",
        [
            ("Contacts discovered", total),
            ("Executives", band("c_level", "clevel", "executive", "chief", "founder", "vp", "president")),
            ("Directors", band("director")),
            ("Managers", band("manager", "head")),
        ],
        note="Apify engine runs manually per company — figures are platform totals.",
    )


def build_intelligence(session: Session, execution: PipelineExecution) -> list[MetricGroup]:
    """The Platform Intelligence blocks.

    Per-run deltas come from the stage JSON already snapshotted on the execution row;
    absolute figures come from a handful of grouped aggregate queries. Every query is
    a COUNT or GROUP BY over an indexed column — this runs once per scheduled run,
    after the pipeline has finished, so it is never on a user-facing path.
    """
    stages = _stage_map(execution)
    totals = execution.totals or {}
    industry = stages.get("industry", {})
    news = stages.get("news", {})
    scoring = stages.get("scoring", {})
    grades = _grade_counts(session)
    high_priority = sum(n for g, n in grades.items() if g in ("A+", "A"))

    groups = [
        MetricGroup(
            "Industry Discovery",
            [
                ("Companies scanned", int(industry.get("processed", 0) or 0)),
                ("Companies added", int(industry.get("created", 0) or 0)),
                ("Companies updated", int(industry.get("updated", 0) or 0)),
                ("Companies tracked", int(totals.get("companies", 0) or 0)),
            ],
            note=industry.get("notes", "")[:200],
        ),
        MetricGroup(
            "News Collection",
            [
                ("Articles collected", int(news.get("processed", 0) or 0)),
                ("Opportunity signals created", int(news.get("created", 0) or 0)),
                ("Queued for review", int(news.get("review", 0) or 0)),
                ("Opportunities tracked", int(totals.get("opportunities", 0) or 0)),
            ],
            note=news.get("notes", "")[:200],
        ),
        _career_metrics(session, stages.get("career", {})),
        _decision_maker_metrics(session),
        MetricGroup(
            "Lead Scoring",
            [
                ("Companies rescored", int(scoring.get("updated", 0) or scoring.get("processed", 0) or 0)),
                ("High-priority leads (A+/A)", high_priority),
                ("Grade A+", grades.get("A+", 0)),
                ("Grade A", grades.get("A", 0)),
                ("Grade B", grades.get("B", 0)),
            ],
            note=scoring.get("notes", "")[:200],
        ),
    ]
    return groups


def build_health(session: Session, settings: Settings, execution: PipelineExecution) -> list[HealthCheck]:
    checks: list[HealthCheck] = []
    checks.append(HealthCheck(
        "Scheduler",
        settings.scheduler_enabled,
        "enabled" if settings.scheduler_enabled else "disabled (SP_SCHEDULER_ENABLED=false)",
    ))
    try:
        enabled = session.scalar(
            select(func.count()).select_from(NewsSource).where(NewsSource.enabled.is_(True))
        ) or 0
        total = session.scalar(select(func.count()).select_from(NewsSource)) or 0
        checks.append(HealthCheck("News sources", enabled > 0, f"{enabled} of {total} enabled"))
    except Exception as exc:      # noqa: BLE001 - health must never raise
        checks.append(HealthCheck("News sources", False, str(exc)[:120]))
    try:
        session.execute(select(func.count()).select_from(Company))
        checks.append(HealthCheck("Database", True, "reachable"))
    except Exception as exc:      # noqa: BLE001
        checks.append(HealthCheck("Database", False, str(exc)[:120]))

    failed = [s.get("component", "") for s in (execution.stages or []) if s.get("status") == "failed"]
    checks.append(HealthCheck(
        "Pipelines", not failed, ", ".join(failed) if failed else "all pipelines completed",
    ))
    return checks


def build_run_notification(
    session: Session, settings: Settings, execution: PipelineExecution, *, exception: str = "",
) -> RunNotification:
    """Assemble the full channel-neutral payload for one completed run."""
    stages = [
        StageSummary(
            component=str(s.get("component", "")),
            status=str(s.get("status", "")),
            processed=int(s.get("processed", 0) or 0),
            created=int(s.get("created", 0) or 0),
            updated=int(s.get("updated", 0) or 0),
            review=int(s.get("review", 0) or 0),
            duration_ms=int(s.get("duration_ms", 0) or 0),
            errors=list(s.get("errors", []) or []),
            notes=str(s.get("notes", "") or ""),
        )
        for s in (execution.stages or [])
    ]
    return RunNotification(
        run_id=execution.run_id,
        status=execution.status,
        trigger=execution.trigger,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        duration_ms=execution.duration_ms or 0,
        records_processed=execution.records_processed or 0,
        scheduled_slot=execution.scheduled_slot,
        stages=stages,
        intelligence=build_intelligence(session, execution),
        health=build_health(session, settings, execution),
        totals=dict(execution.totals or {}),
        frontend_url=settings.frontend_url,
        brand_name=settings.brand_name,
        logo_url=settings.brand_logo_url,
        exception=exception,
    )


# --------------------------------------------------------------- delivery log
def _record(session: Session, outcomes: list[DeliveryOutcome], *, run_id: str,
            event_type: str, channel: str, audience: Audience) -> None:
    """Persist one row per recipient. Isolated in its own try: losing the audit trail
    must not turn a successful send into a reported failure."""
    try:
        for o in outcomes:
            session.add(NotificationDelivery(
                run_id=run_id, event_type=event_type, channel=channel, provider=o.provider,
                recipient=o.recipient, audience=audience.value, status=o.status,
                attempts=o.attempts, error=o.error[:2000],
            ))
        session.commit()
    except Exception:      # noqa: BLE001
        logger.warning("[notify] could not record delivery log for run %s", run_id, exc_info=True)
        session.rollback()


# --------------------------------------------------------------- entry point
def notify_run_complete(
    session: Session, settings: Settings, execution: PipelineExecution, *, exception: str = "",
) -> tuple[str, str, int]:
    """Notify every approved active user that a run finished.

    Returns the run-level ``(status, detail, notified_count)`` rollup that
    ``pipeline_executions`` stores. Never raises.

    A failed run is split by audience: admins get the exception and per-stage errors,
    everyone else gets a concise notice. That is two provider calls with two renderings
    of the same payload — the split is a rendering concern, not a scheduler concern.
    """
    try:
        if not settings.enable_notifications:
            return "skipped", "notifications disabled (SP_ENABLE_NOTIFICATIONS=false)", 0
        # Backward compatibility: SP_NOTIFY_MODE=off was the kill switch before this
        # framework existed and may still be set on a deployed environment. Honour it
        # so an operator who disabled notifications does not get them back silently.
        if (settings.notify_mode or "").strip().lower() == "off":
            return "skipped", "notifications disabled (SP_NOTIFY_MODE=off)", 0

        recipients = resolve_recipients(session)
        if not recipients:
            return "skipped", "no approved active users to notify", 0

        provider = provider_registry.get_provider(settings.notification_provider)
        if provider is None:
            detail = (f"unknown notification provider '{settings.notification_provider}' "
                      f"(registered: {', '.join(provider_registry.list_providers())})")
            logger.warning("[notify] %s", detail)
            return "failed", detail, 0

        notification = build_run_notification(session, settings, execution, exception=exception)
        event_type = "run_failure" if notification.is_failure else "run_summary"

        ok, reason = provider.configured(settings)
        if not ok:
            logger.info("[notify] provider '%s' not configured (%s) — %d recipient(s) not mailed",
                        provider.name, reason, len(recipients))
            outcomes = [DeliveryOutcome(r.email, "logged", provider.name, 0, reason) for r in recipients]
            _record(session, outcomes, run_id=execution.run_id, event_type=event_type,
                    channel="email", audience=Audience.ALL)
            return "logged", f"provider '{provider.name}' not configured: {reason}", len(recipients)

        # Split only when there is something admin-only to say.
        if notification.is_failure:
            batches = [
                (Audience.ADMIN, [r for r in recipients if r.is_admin]),
                (Audience.ALL, [r for r in recipients if not r.is_admin]),
            ]
        else:
            batches = [(Audience.ALL, recipients)]

        all_outcomes: list[DeliveryOutcome] = []
        for audience, batch in batches:
            if not batch:
                continue
            outcomes = provider.send(settings, notification, batch, audience=audience)
            _record(session, outcomes, run_id=execution.run_id, event_type=event_type,
                    channel="email", audience=audience)
            all_outcomes.extend(outcomes)

        sent = sum(1 for o in all_outcomes if o.sent)
        failed = [o for o in all_outcomes if o.status == "failed"]
        if sent and not failed:
            logger.info("[notify] run %s summary sent to %d recipient(s) via %s",
                        execution.run_id, sent, provider.name)
            return "sent", f"sent to {sent} approved active user(s) via {provider.name}", sent
        if sent and failed:
            # 'sent' — NOTIFICATION_STATUSES has no partial state, and some mail did go
            # out. The per-recipient failures are in notification_deliveries.
            logger.warning("[notify] run %s: sent to %d, failed for %d",
                           execution.run_id, sent, len(failed))
            return "sent", f"sent to {sent}, failed for {len(failed)} — {failed[0].error[:200]}", sent
        detail = failed[0].error[:400] if failed else "no recipients accepted"
        logger.warning("[notify] run %s delivery failed: %s", execution.run_id, detail)
        return "failed", detail, 0

    except Exception as exc:      # noqa: BLE001 - a notification must never fail a run
        msg = str(exc)[:500]
        logger.warning("[notify] run %s notification raised (ignored): %s",
                       getattr(execution, "run_id", "?"), msg, exc_info=True)
        return "failed", msg, 0
