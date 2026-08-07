"""SMTP email provider (Gmail by default).

Renders a :class:`RunNotification` to a multipart/alternative message and delivers it
over SMTP+STARTTLS. Everything — host, port, credentials, sender identity — comes
from :class:`backend.config.Settings`, i.e. environment variables; nothing is
hardcoded and no credential is ever logged or included in an error string.

Gmail specifics that are not Gmail-only code: port 587 + STARTTLS, and an App
Password rather than the account password (Google rejects plain passwords for SMTP
on accounts with 2FA, which is all of them now). Pointing ``SMTP_HOST``/``SMTP_PORT``
at any other RFC-compliant server works unchanged — that is why this class is
``SmtpEmailProvider`` and registered under the generic name ``email`` as well as
``gmail``.

Recipients are BCC'd: one message per run, and no recipient sees the platform's
full user list.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from backend.config import Settings
from backend.notifications import templates
from backend.notifications.providers.base import retry
from backend.notifications.schemas import Audience, DeliveryOutcome, Recipient, RunNotification

logger = logging.getLogger("backend.notifications.providers.email")

_TIMEOUT_SECONDS = 30


def _sender_address(settings: Settings) -> str:
    return (settings.email_from or settings.smtp_username or "").strip()


def build_message(
    settings: Settings,
    notification: RunNotification,
    recipients: list[Recipient],
    *,
    audience: Audience = Audience.ALL,
) -> EmailMessage:
    """Compose the multipart message. Separated from delivery so tests can assert on
    headers and both body parts without opening a socket."""
    msg = EmailMessage()
    msg["Subject"] = templates.subject(notification)
    msg["From"] = formataddr((settings.email_display_name or notification.brand_name,
                              _sender_address(settings)))
    # The sender is the only visible To; real recipients are BCC'd.
    msg["To"] = _sender_address(settings)
    if recipients:
        msg["Bcc"] = ", ".join(r.email for r in recipients)
    msg["Message-ID"] = make_msgid(domain=(_sender_address(settings).split("@")[-1] or "localhost"))
    msg["Auto-Submitted"] = "auto-generated"      # RFC 3834: suppresses vacation auto-replies
    msg["X-Auto-Response-Suppress"] = "All"
    msg.set_content(templates.render_text(notification, audience=audience))
    msg.add_alternative(templates.render_html(notification, audience=audience), subtype="html")
    return msg


class SmtpEmailProvider:
    """Delivers notifications over SMTP. Registered as both ``email`` and ``gmail``."""

    name = "email"

    def configured(self, settings: Settings) -> tuple[bool, str]:
        if not settings.smtp_host:
            return False, "SMTP_HOST is not set"
        if not _sender_address(settings):
            return False, "EMAIL_FROM (or SMTP_USERNAME) is not set"
        if not settings.smtp_password:
            return False, "SMTP_PASSWORD is not set"
        return True, ""

    # ------------------------------------------------------------------ send
    def _deliver(self, settings: Settings, msg: EmailMessage) -> None:
        """One SMTP conversation. Raises on any failure; the caller retries."""
        if settings.smtp_use_ssl:
            client = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port,
                                      timeout=_TIMEOUT_SECONDS, context=ssl.create_default_context())
        else:
            client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=_TIMEOUT_SECONDS)
        try:
            client.ehlo()
            if settings.smtp_use_starttls and not settings.smtp_use_ssl:
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
            if settings.smtp_username and settings.smtp_password:
                client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(msg)
        finally:
            try:
                client.quit()
            except Exception:      # noqa: BLE001 - a failed QUIT must not mask a successful send
                client.close()

    def send(
        self,
        settings: Settings,
        notification: RunNotification,
        recipients: list[Recipient],
        *,
        audience: Audience = Audience.ALL,
    ) -> list[DeliveryOutcome]:
        if not recipients:
            return []
        msg = build_message(settings, notification, recipients, audience=audience)

        def _attempt() -> None:
            self._deliver(settings, msg)

        ok, attempts, error = retry(
            _attempt,
            attempts=settings.notification_retry_count,
            on_error=lambda i, exc: logger.warning(
                "[notify] SMTP attempt %d/%d failed for run %s: %s",
                i, settings.notification_retry_count, notification.run_id, str(exc)[:200],
            ),
        )
        # One SMTP transaction covers every BCC'd recipient, so its result applies to
        # all of them — recorded per recipient so the delivery log stays per-person.
        status = "sent" if ok else "failed"
        return [DeliveryOutcome(recipient=r.email, status=status, provider=self.name,
                                attempts=attempts, error=error)
                for r in recipients]


class GmailEmailProvider(SmtpEmailProvider):
    """Alias so ``EMAIL_PROVIDER=gmail`` resolves. Gmail is plain SMTP — the defaults
    in Settings (smtp.gmail.com:587, STARTTLS) are all that differs."""

    name = "gmail"
