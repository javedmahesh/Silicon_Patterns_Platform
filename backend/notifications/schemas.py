"""Channel-neutral notification payloads.

These dataclasses are the contract between *producers* (the scheduler, via
:mod:`backend.notifications.service`) and *providers* (email today; Teams, Slack,
webhooks, in-app later). Nothing here knows about SMTP, HTML, or Microsoft Graph —
a provider renders a payload however its channel requires.

``RunNotification`` is deliberately a flat, already-computed snapshot rather than a
live ORM row: the service gathers everything once, so a provider can be retried,
queued, or run on another thread without touching the database.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Audience(str, Enum):
    """Who a rendering is for. Admins get diagnostics (exceptions, stage errors);
    everyone else gets the concise version. One notification can therefore produce
    two different bodies from the same payload."""

    ALL = "all"
    ADMIN = "admin"


class Severity(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"


@dataclass(slots=True)
class Recipient:
    email: str
    name: str = ""
    is_admin: bool = False


@dataclass(slots=True)
class StageSummary:
    """One pipeline stage as the notification cares about it."""

    component: str
    status: str
    processed: int = 0
    created: int = 0
    updated: int = 0
    review: int = 0
    duration_ms: int = 0
    errors: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def ok(self) -> bool:
        return self.status in ("success", "skipped")


@dataclass(slots=True)
class MetricGroup:
    """A titled block of label/value pairs — the Platform Intelligence sections.

    Kept generic so a new engine adds a group without touching any renderer.
    ``empty`` lets a renderer collapse a section that produced nothing this run
    instead of showing a wall of zeros.
    """

    title: str
    metrics: list[tuple[str, int | str]] = field(default_factory=list)
    note: str = ""

    @property
    def empty(self) -> bool:
        return all(v in (0, "", "0") for _, v in self.metrics)


@dataclass(slots=True)
class HealthCheck:
    name: str
    ok: bool
    detail: str = ""


@dataclass(slots=True)
class RunNotification:
    """Everything a channel needs to describe one completed platform run."""

    run_id: str
    status: str
    trigger: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int = 0
    records_processed: int = 0
    scheduled_slot: str | None = None
    stages: list[StageSummary] = field(default_factory=list)
    intelligence: list[MetricGroup] = field(default_factory=list)
    health: list[HealthCheck] = field(default_factory=list)
    totals: dict[str, int] = field(default_factory=dict)
    frontend_url: str = ""
    brand_name: str = "Silicon Patterns"
    logo_url: str = ""
    # Set when the run itself raised rather than completing with failed stages.
    exception: str = ""

    @property
    def severity(self) -> Severity:
        if self.status == "failed" or self.exception:
            return Severity.FAILURE
        if self.status == "partial" or self.failed_stages:
            return Severity.WARNING
        return Severity.SUCCESS

    @property
    def failed_stages(self) -> list[StageSummary]:
        return [s for s in self.stages if s.status == "failed"]

    @property
    def is_failure(self) -> bool:
        return self.severity is Severity.FAILURE

    @property
    def pipelines_executed(self) -> list[str]:
        return [s.component for s in self.stages]


@dataclass(slots=True)
class DeliveryOutcome:
    """One provider's result for one recipient — what gets logged."""

    recipient: str
    status: str            # sent | failed | logged | skipped
    provider: str
    attempts: int = 1
    error: str = ""

    @property
    def sent(self) -> bool:
        return self.status == "sent"
