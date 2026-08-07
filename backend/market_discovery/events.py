"""Structured discovery events.

Every meaningful thing the engine does emits one of these. They exist so that
notifications, analytics and audit logging can consume discovery activity later
*without* the pipeline having to know those consumers exist.

Deliberately not persisted to a table in this phase: there is no consumer yet, and
the platform's rule is not to add schema before there is one. Every event is written
to the structured log, and :func:`subscribe` is the extension point — a future sink
(a table writer, the notification service, a metrics counter) registers there and
the pipeline is untouched.

A subscriber that raises is logged and skipped. Emitting an event must never be able
to fail a discovery run.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("market_discovery.events")


class EventType(str, Enum):
    COMPANY_DISCOVERED = "company_discovered"
    COMPANY_UPDATED = "company_updated"
    DUPLICATE_DETECTED = "duplicate_detected"
    CANDIDATE_REJECTED = "candidate_rejected"
    SOURCE_STARTED = "source_started"
    SOURCE_COMPLETED = "source_completed"
    SOURCE_FAILED = "source_failed"
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"


@dataclass(slots=True)
class DiscoveryEvent:
    type: EventType
    run_id: str = ""
    source: str = ""
    candidate_key: str = ""
    company_name: str = ""
    company_domain: str = ""
    confidence: float = 0.0
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["type"] = self.type.value
        out["occurred_at"] = self.occurred_at.isoformat()
        return out


Subscriber = Callable[[DiscoveryEvent], None]

_subscribers: list[Subscriber] = []

#: Events worth a WARNING rather than INFO — the ones an operator must not miss.
_WARN_ON = {EventType.SOURCE_FAILED, EventType.CANDIDATE_REJECTED}


def subscribe(subscriber: Subscriber) -> Subscriber:
    """Register a sink. Usable as a decorator. Returns the subscriber for chaining."""
    _subscribers.append(subscriber)
    return subscriber


def unsubscribe(subscriber: Subscriber) -> None:
    try:
        _subscribers.remove(subscriber)
    except ValueError:
        pass


def clear_subscribers() -> None:
    """Drop every subscriber. For tests; not part of the runtime path."""
    _subscribers.clear()


def subscriber_count() -> int:
    return len(_subscribers)


def emit(event: DiscoveryEvent) -> DiscoveryEvent:
    """Log the event and fan it out. Never raises."""
    level = logging.WARNING if event.type in _WARN_ON else logging.INFO
    logger.log(
        level,
        "[discovery] %s run=%s source=%s company=%s domain=%s confidence=%.2f%s",
        event.type.value, event.run_id or "-", event.source or "-",
        event.company_name or "-", event.company_domain or "-", event.confidence,
        f" — {event.detail}" if event.detail else "",
    )
    for subscriber in list(_subscribers):
        try:
            subscriber(event)
        except Exception:      # noqa: BLE001 - a bad sink must not break discovery
            logger.error("[discovery] event subscriber %r raised (ignored)",
                         getattr(subscriber, "__name__", subscriber), exc_info=True)
    return event


# ------------------------------------------------------------------ shorthands
def company_discovered(run_id: str, candidate, confidence: float) -> DiscoveryEvent:
    return emit(DiscoveryEvent(
        EventType.COMPANY_DISCOVERED, run_id=run_id, source=candidate.source,
        candidate_key=candidate.candidate_key, company_name=candidate.company_name,
        company_domain=candidate.company_domain, confidence=confidence,
        data={"sources": list(candidate.sources)},
    ))


def company_updated(run_id: str, candidate, confidence: float) -> DiscoveryEvent:
    return emit(DiscoveryEvent(
        EventType.COMPANY_UPDATED, run_id=run_id, source=candidate.source,
        candidate_key=candidate.candidate_key, company_name=candidate.company_name,
        company_domain=candidate.company_domain, confidence=confidence,
        data={"sources": list(candidate.sources)},
    ))


def duplicate_detected(run_id: str, group) -> DiscoveryEvent:
    return emit(DiscoveryEvent(
        EventType.DUPLICATE_DETECTED, run_id=run_id,
        candidate_key=group.key, company_name=group.candidate.company_name,
        company_domain=group.candidate.company_domain,
        detail=f"{len(group.members)} sightings from {', '.join(group.source_names)}",
        data={"sources": list(group.source_names),
              "conflicts": [c.field for c in group.conflicts]},
    ))


def candidate_rejected(run_id: str, candidate, issues) -> DiscoveryEvent:
    return emit(DiscoveryEvent(
        EventType.CANDIDATE_REJECTED, run_id=run_id, source=candidate.source,
        candidate_key=candidate.candidate_key, company_name=candidate.company_name,
        detail="; ".join(f"{i.field}: {i.reason}" for i in issues),
    ))


def source_started(run_id: str, name: str) -> DiscoveryEvent:
    return emit(DiscoveryEvent(EventType.SOURCE_STARTED, run_id=run_id, source=name))


def source_completed(run_id: str, name: str, fetched: int, duration_ms: int) -> DiscoveryEvent:
    return emit(DiscoveryEvent(
        EventType.SOURCE_COMPLETED, run_id=run_id, source=name,
        detail=f"{fetched} candidate(s) in {duration_ms}ms",
        data={"fetched": fetched, "duration_ms": duration_ms},
    ))


def source_failed(run_id: str, name: str, error: str) -> DiscoveryEvent:
    return emit(DiscoveryEvent(EventType.SOURCE_FAILED, run_id=run_id, source=name,
                               detail=error[:500]))


def pipeline_started(run_id: str, source_count: int) -> DiscoveryEvent:
    return emit(DiscoveryEvent(EventType.PIPELINE_STARTED, run_id=run_id,
                               detail=f"{source_count} source(s)",
                               data={"source_count": source_count}))


def pipeline_completed(run_id: str, result) -> DiscoveryEvent:
    return emit(DiscoveryEvent(
        EventType.PIPELINE_COMPLETED, run_id=run_id, detail=result.summary(),
        data={"status": result.status, "fetched": result.fetched, "new": result.new,
              "updated": result.updated, "duplicates": result.duplicates,
              "rejected": result.rejected, "below_threshold": result.below_threshold,
              "duration_ms": result.duration_ms},
    ))
