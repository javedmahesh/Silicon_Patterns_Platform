"""Notification delivery channels.

Importing this package registers every built-in provider. A future channel (Teams,
Slack, webhook, in-app) adds its module here and calls ``register()`` — no change to
the service or the scheduler.
"""
from __future__ import annotations

from backend.notifications.providers.base import (
    NotificationProvider,
    get_provider,
    list_providers,
    register,
    retry,
)
from backend.notifications.providers.email import (
    GmailEmailProvider,
    SmtpEmailProvider,
    build_message,
)

register(SmtpEmailProvider())
register(GmailEmailProvider())

__all__ = [
    "NotificationProvider",
    "SmtpEmailProvider",
    "GmailEmailProvider",
    "build_message",
    "get_provider",
    "list_providers",
    "register",
    "retry",
]
