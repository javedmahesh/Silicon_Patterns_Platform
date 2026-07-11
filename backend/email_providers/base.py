"""Abstract base for email providers — swap mock/SMTP/Gmail without touching the service layer."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SendResult:
    ok: bool
    thread_id: str
    provider_message_id: str = ""
    error: str = ""


@dataclass
class DraftResult:
    ok: bool
    draft_id: str = ""
    thread_id: str = ""
    provider_message_id: str = ""
    error: str = ""


@dataclass
class AttachmentData:
    ok: bool
    data_b64: str = ""
    filename: str = ""
    content_type: str = ""
    size_bytes: int = 0
    error: str = ""


@dataclass
class RawMessage:
    """Normalized message returned from a provider sync or receive operation."""

    provider_message_id: str
    thread_id: str
    subject: str
    body: str
    body_html: str
    from_email: str
    to_email: str
    date: datetime | None
    direction: str  # "inbound" or "outbound"
    folder: str     # "inbox", "sent", "drafts", etc.
    is_read: bool
    labels: list[str] = field(default_factory=list)
    attachments: list[dict] = field(default_factory=list)  # {filename, content_type, size_bytes, attachment_id}


@dataclass
class SyncResult:
    """Result from a provider sync() call."""

    messages: list[RawMessage] = field(default_factory=list)
    next_cursor: str = ""  # Gmail historyId / page token for next incremental sync
    error: str = ""


@dataclass
class ProviderCapabilities:
    can_send: bool = True
    can_receive: bool = False
    can_schedule: bool = False
    supports_attachments: bool = True
    supports_threading: bool = True
    supports_drafts: bool = False
    supports_sync: bool = False
    max_attachment_bytes: int = 25 * 1024 * 1024  # 25 MB default
    extra: dict = field(default_factory=dict)


class EmailProvider(ABC):
    """Contract every email provider must satisfy.

    Core methods (send, capabilities) are abstract and required.
    Sync/receive/draft methods are optional — they raise NotImplementedError
    by default and subclasses override them as needed.
    """

    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Short identifier, e.g. 'mock', 'smtp', 'gmail'."""

    @abstractmethod
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
        """Send an email. attachments: list of {filename, content_type, content_b64}."""

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """What this provider can do."""

    def validate_config(self, config_json: str) -> bool:
        """Return True if the config is sufficient to connect. Override in real providers."""
        try:
            json.loads(config_json or "{}")
            return True
        except (json.JSONDecodeError, TypeError):
            return False

    # ------------------------------------------------------------------
    # Optional extended interface — raise NotImplementedError by default
    # ------------------------------------------------------------------

    def sync(self, cursor: str = "") -> SyncResult:
        """Incremental sync. cursor is a provider-specific opaque token.

        Returns new messages since the cursor, plus the next cursor.
        """
        raise NotImplementedError(f"{self.provider_type!r} does not support sync")

    def receive(self, limit: int = 50) -> list[RawMessage]:
        """Fetch inbox messages (non-incremental)."""
        raise NotImplementedError(f"{self.provider_type!r} does not support receive")

    def create_draft(
        self,
        *,
        to_email: str,
        from_email: str,
        subject: str,
        body: str,
        body_html: str = "",
        thread_id: str = "",
    ) -> DraftResult:
        raise NotImplementedError(f"{self.provider_type!r} does not support create_draft")

    def update_draft(
        self,
        *,
        draft_id: str,
        to_email: str,
        from_email: str,
        subject: str,
        body: str,
        body_html: str = "",
    ) -> DraftResult:
        raise NotImplementedError(f"{self.provider_type!r} does not support update_draft")

    def delete_draft(self, *, draft_id: str) -> bool:
        raise NotImplementedError(f"{self.provider_type!r} does not support delete_draft")

    def send_draft(self, *, draft_id: str) -> SendResult:
        raise NotImplementedError(f"{self.provider_type!r} does not support send_draft")

    def download_attachment(self, *, message_id: str, attachment_id: str) -> AttachmentData:
        raise NotImplementedError(f"{self.provider_type!r} does not support download_attachment")

    def upload_attachment(
        self, *, filename: str, content_type: str, data_b64: str
    ) -> AttachmentData:
        raise NotImplementedError(f"{self.provider_type!r} does not support upload_attachment")

    def list_threads(
        self, *, q: str = "", page_token: str = "", max_results: int = 50
    ) -> tuple[list[dict], str]:
        """Returns (thread_list, next_page_token)."""
        raise NotImplementedError(f"{self.provider_type!r} does not support list_threads")
