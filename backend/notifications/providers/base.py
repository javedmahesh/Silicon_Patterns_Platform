"""Notification provider contract + registry.

A provider owns exactly one delivery channel. It receives a rendered subject/body
and a recipient list and reports a :class:`DeliveryOutcome` per recipient — it never
decides *who* gets notified, *whether* notifications are on, or *what* the run did.
That all lives in :mod:`backend.notifications.service`.

Adding a channel = one subclass + one ``register()`` call. The scheduler, the
service, and every existing provider are untouched (open/closed) — the same pattern
the News Collection Engine uses for source adapters.
"""
from __future__ import annotations

import logging
from typing import Callable, Protocol, runtime_checkable

from backend.config import Settings
from backend.notifications.schemas import Audience, DeliveryOutcome, Recipient, RunNotification

logger = logging.getLogger("backend.notifications.providers")


@runtime_checkable
class NotificationProvider(Protocol):
    """One delivery channel."""

    name: str

    def configured(self, settings: Settings) -> tuple[bool, str]:
        """``(is_configured, reason_if_not)``. A provider that isn't configured is
        never called — the service records 'logged' instead, so a missing credential
        degrades to a no-op rather than a failure."""
        ...

    def send(
        self,
        settings: Settings,
        notification: RunNotification,
        recipients: list[Recipient],
        *,
        audience: Audience,
    ) -> list[DeliveryOutcome]:
        """Deliver to every recipient. Must not raise — return failed outcomes."""
        ...


_REGISTRY: dict[str, NotificationProvider] = {}


def register(provider: NotificationProvider) -> None:
    _REGISTRY[provider.name] = provider


def get_provider(name: str) -> NotificationProvider | None:
    return _REGISTRY.get((name or "").strip().lower())


def list_providers() -> list[str]:
    return sorted(_REGISTRY)


def retry(fn: Callable[[], None], *, attempts: int, on_error: Callable[[int, Exception], None] | None = None) -> tuple[bool, int, str]:
    """Run ``fn`` up to ``attempts`` times. Returns ``(ok, attempts_used, last_error)``.

    Deliberately has no sleep: a scheduled run must not be held open by a backoff,
    and SMTP failures here are overwhelmingly configuration errors (bad credential,
    blocked port) that a delay would not fix. Transient-failure backoff belongs in a
    queue worker, which is the natural home if this ever needs one.
    """
    last = ""
    for i in range(1, max(1, attempts) + 1):
        try:
            fn()
            return True, i, ""
        except Exception as exc:      # noqa: BLE001 - reported, never propagated
            last = str(exc)[:500]
            if on_error:
                on_error(i, exc)
    return False, max(1, attempts), last
