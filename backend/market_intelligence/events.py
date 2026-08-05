"""Structured intelligence events.

Same architecture as :mod:`backend.market_discovery.events` — log-and-fan-out, with
:func:`subscribe` as the extension point — but a separate stream, because the two
layers must stay independently deployable. Putting intelligence vocabulary into the
discovery event enum would make the lower layer aware of the higher one.

Not persisted: there is no consumer yet, and the platform's rule is not to add schema
before there is one. Every event reaches the structured log, and a future sink (a
table writer, the notification service, a metrics counter) registers here without the
pipeline changing.

A subscriber that raises is logged and skipped. Emitting an event must never be able
to fail an intelligence run.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("market_intelligence.events")


class EventType(str, Enum):
    COMPANY_CLASSIFIED = "company_classified"
    TECHNOLOGY_IDENTIFIED = "technology_identified"
    SIGNAL_GENERATED = "signal_generated"
    PRIORITY_ASSIGNED = "priority_assigned"
    CANDIDATE_REJECTED = "candidate_rejected"
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"


@dataclass(slots=True)
class IntelligenceEvent:
    type: EventType
    run_id: str = ""
    candidate_key: str = ""
    company_name: str = ""
    company_domain: str = ""
    priority: str = ""
    confidence: float = 0.0
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["type"] = self.type.value
        out["occurred_at"] = self.occurred_at.isoformat()
        return out


Subscriber = Callable[[IntelligenceEvent], None]

_subscribers: list[Subscriber] = []

#: The one event an operator must not miss: a candidate the layer could not interpret.
_WARN_ON = {EventType.CANDIDATE_REJECTED}


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


def emit(event: IntelligenceEvent) -> IntelligenceEvent:
    """Log the event and fan it out. Never raises."""
    level = logging.WARNING if event.type in _WARN_ON else logging.INFO
    logger.log(
        level,
        "[intelligence] %s run=%s company=%s priority=%s confidence=%.2f%s",
        event.type.value, event.run_id or "-", event.company_name or "-",
        event.priority or "-", event.confidence,
        f" — {event.detail}" if event.detail else "",
    )
    for subscriber in list(_subscribers):
        try:
            subscriber(event)
        except Exception:      # noqa: BLE001 - a bad sink must not break a run
            logger.error("[intelligence] event subscriber %r raised (ignored)",
                         getattr(subscriber, "__name__", subscriber), exc_info=True)
    return event


# ------------------------------------------------------------------ shorthands
def _base(record) -> dict[str, Any]:
    return {"run_id": record.run_id, "candidate_key": record.candidate_key,
            "company_name": record.company_name, "company_domain": record.company_domain}


def company_classified(record) -> IntelligenceEvent:
    return emit(IntelligenceEvent(
        EventType.COMPANY_CLASSIFIED, **_base(record),
        detail=", ".join(record.classification_labels) or "unclassified",
        data={"classifications": list(record.classification_labels)},
    ))


def technology_identified(record) -> IntelligenceEvent:
    return emit(IntelligenceEvent(
        EventType.TECHNOLOGY_IDENTIFIED, **_base(record),
        detail=", ".join(record.technology_labels),
        data={"technologies": list(record.technology_labels)},
    ))


def signal_generated(record, signal) -> IntelligenceEvent:
    return emit(IntelligenceEvent(
        EventType.SIGNAL_GENERATED, **_base(record), confidence=signal.confidence,
        detail=f"{signal.label} ({signal.category.value})",
        data={"type": signal.type, "category": signal.category.value,
              "evidence": [e.as_dict() for e in signal.evidence]},
    ))


def priority_assigned(record) -> IntelligenceEvent:
    return emit(IntelligenceEvent(
        EventType.PRIORITY_ASSIGNED, **_base(record), priority=record.priority.value,
        confidence=record.confidence, detail=f"score {record.priority_score:.2f}",
        data={"score": record.priority_score,
              "factors": [f.as_dict() for f in record.factors],
              "reasons": list(record.reasons)},
    ))


def candidate_rejected(run_id: str, candidate_key: str, company_name: str,
                       reason: str) -> IntelligenceEvent:
    return emit(IntelligenceEvent(
        EventType.CANDIDATE_REJECTED, run_id=run_id, candidate_key=candidate_key,
        company_name=company_name, detail=reason[:500],
    ))


def pipeline_started(run_id: str, count: int, pack: str) -> IntelligenceEvent:
    return emit(IntelligenceEvent(
        EventType.PIPELINE_STARTED, run_id=run_id,
        detail=f"{count} candidate(s) with rule pack {pack}",
        data={"candidates": count, "rule_pack": pack},
    ))


def pipeline_completed(run_id: str, result) -> IntelligenceEvent:
    return emit(IntelligenceEvent(
        EventType.PIPELINE_COMPLETED, run_id=run_id, detail=result.summary(),
        data={"status": result.status, "evaluated": result.evaluated,
              "skipped": result.skipped, "failed": result.failed,
              "by_priority": result.by_priority, "duration_ms": result.duration_ms},
    ))
