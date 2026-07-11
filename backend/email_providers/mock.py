"""Mock email provider — always succeeds, no network, no credentials."""
from __future__ import annotations

import uuid

from .base import EmailProvider, ProviderCapabilities, SendResult


class MockEmailProvider(EmailProvider):
    """Simulates sending for dev/test. Returns a stable thread id so replies can be threaded."""

    provider_type = "mock"

    def send(
        self,
        *,
        to_email: str,
        from_email: str,
        subject: str,
        body: str,
        thread_id: str = "",
        attachments: list[dict] | None = None,
    ) -> SendResult:
        if not to_email:
            return SendResult(ok=False, thread_id=thread_id, error="no recipient email")
        tid = thread_id or f"mock-{uuid.uuid4().hex[:16]}"
        return SendResult(
            ok=True,
            thread_id=tid,
            provider_message_id=f"mock-{uuid.uuid4().hex[:20]}",
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            can_send=True,
            can_receive=False,
            can_schedule=False,
            supports_attachments=True,
            supports_threading=True,
        )
