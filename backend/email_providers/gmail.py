"""Gmail API email provider — production send/receive/sync via Google's REST API.

Runtime dependencies (optional — not required for mock/test mode):
    google-api-python-client>=2.100
    google-auth>=2.0
    google-auth-oauthlib>=1.0

All Google API calls are guarded with ImportError so the rest of the platform
boots fine when these packages are absent (dev / CI without Google deps).
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders as _email_encoders

from .base import (
    AttachmentData,
    DraftResult,
    EmailProvider,
    ProviderCapabilities,
    RawMessage,
    SendResult,
    SyncResult,
)

logger = logging.getLogger(__name__)

_TOKEN_URI = "https://oauth2.googleapis.com/token"

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

# Gmail system label IDs
_LABEL_INBOX = "INBOX"
_LABEL_SENT = "SENT"
_LABEL_DRAFTS = "DRAFT"
_LABEL_UNREAD = "UNREAD"
_LABEL_TRASH = "TRASH"
_LABEL_SPAM = "SPAM"


class GmailProvider(EmailProvider):
    """Per-user Gmail API provider.

    Must be instantiated with the user's decrypted config_json (OAuth tokens).
    Stateless after construction — thread-safe to use concurrently.
    """

    provider_type = "gmail"

    def __init__(self, config_json: str = "{}") -> None:
        self._config: dict = {}
        try:
            self._config = json.loads(config_json or "{}")
        except json.JSONDecodeError:
            pass

    # ------------------------------------------------------------------ internal

    def _credentials(self):
        """Build google.oauth2.credentials.Credentials from stored token data."""
        try:
            from google.oauth2.credentials import Credentials
        except ImportError:
            raise RuntimeError(
                "Gmail provider requires google-auth. "
                "Install with: pip install google-auth google-auth-oauthlib"
            )
        return Credentials(
            token=self._config.get("access_token"),
            refresh_token=self._config.get("refresh_token"),
            token_uri=self._config.get("token_uri", _TOKEN_URI),
            client_id=self._config.get("client_id"),
            client_secret=self._config.get("client_secret"),
            scopes=self._config.get("scopes", GMAIL_SCOPES),
        )

    def _service(self):
        """Build and return an authorized Gmail API service client."""
        try:
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request
        except ImportError:
            raise RuntimeError(
                "Gmail provider requires google-api-python-client. "
                "Install with: pip install google-api-python-client"
            )
        creds = self._credentials()
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def _handle_http_error(self, exc, thread_id: str = "") -> SendResult:
        """Translate googleapiclient.errors.HttpError to a descriptive SendResult."""
        try:
            from googleapiclient.errors import HttpError
            if isinstance(exc, HttpError):
                code = exc.resp.status
                if code == 401:
                    return SendResult(ok=False, thread_id=thread_id,
                                      error="Gmail credentials revoked — please reconnect your account")
                if code == 429:
                    return SendResult(ok=False, thread_id=thread_id,
                                      error="Gmail rate limit exceeded — retry after a delay")
                if code == 403:
                    return SendResult(ok=False, thread_id=thread_id,
                                      error="Gmail quota exceeded or operation forbidden")
                if code == 404:
                    return SendResult(ok=False, thread_id=thread_id,
                                      error="Gmail resource not found")
        except ImportError:
            pass
        return SendResult(ok=False, thread_id=thread_id, error=str(exc)[:500])

    # ------------------------------------------------------------------ base interface

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            can_send=True,
            can_receive=True,
            can_schedule=False,
            supports_attachments=True,
            supports_threading=True,
            supports_drafts=True,
            supports_sync=True,
        )

    def validate_config(self, config_json: str) -> bool:
        """Config is valid when access_token and refresh_token are present."""
        try:
            data = json.loads(config_json or "{}")
            return bool(data.get("access_token") and data.get("refresh_token"))
        except (json.JSONDecodeError, TypeError):
            return False

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
        """Send an email via Gmail API."""
        if not to_email:
            return SendResult(ok=False, thread_id=thread_id, error="no recipient email")
        try:
            service = self._service()
            raw = _build_raw_message(
                to_email=to_email, from_email=from_email,
                subject=subject, body=body, attachments=attachments,
            )
            body_dict: dict = {"raw": raw}
            if thread_id:
                body_dict["threadId"] = thread_id
            result = service.users().messages().send(userId="me", body=body_dict).execute()
            return SendResult(
                ok=True,
                thread_id=result.get("threadId", thread_id),
                provider_message_id=result.get("id", ""),
            )
        except Exception as exc:
            logger.warning("Gmail send failed: %s", exc)
            return self._handle_http_error(exc, thread_id)

    # ------------------------------------------------------------------ drafts

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
        try:
            service = self._service()
            raw = _build_raw_message(
                to_email=to_email, from_email=from_email,
                subject=subject, body=body, body_html=body_html,
            )
            draft_body: dict = {"message": {"raw": raw}}
            if thread_id:
                draft_body["message"]["threadId"] = thread_id
            result = service.users().drafts().create(userId="me", body=draft_body).execute()
            msg = result.get("message", {})
            return DraftResult(
                ok=True,
                draft_id=result.get("id", ""),
                thread_id=msg.get("threadId", thread_id),
                provider_message_id=msg.get("id", ""),
            )
        except Exception as exc:
            logger.warning("Gmail create_draft failed: %s", exc)
            sr = self._handle_http_error(exc)
            return DraftResult(ok=False, error=sr.error)

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
        try:
            service = self._service()
            raw = _build_raw_message(
                to_email=to_email, from_email=from_email,
                subject=subject, body=body, body_html=body_html,
            )
            result = service.users().drafts().update(
                userId="me", id=draft_id,
                body={"message": {"raw": raw}},
            ).execute()
            msg = result.get("message", {})
            return DraftResult(
                ok=True,
                draft_id=result.get("id", draft_id),
                thread_id=msg.get("threadId", ""),
                provider_message_id=msg.get("id", ""),
            )
        except Exception as exc:
            logger.warning("Gmail update_draft failed: %s", exc)
            sr = self._handle_http_error(exc)
            return DraftResult(ok=False, error=sr.error)

    def delete_draft(self, *, draft_id: str) -> bool:
        try:
            service = self._service()
            service.users().drafts().delete(userId="me", id=draft_id).execute()
            return True
        except Exception as exc:
            logger.warning("Gmail delete_draft failed: %s", exc)
            return False

    def send_draft(self, *, draft_id: str) -> SendResult:
        try:
            service = self._service()
            result = service.users().drafts().send(
                userId="me", body={"id": draft_id}
            ).execute()
            return SendResult(
                ok=True,
                thread_id=result.get("threadId", ""),
                provider_message_id=result.get("id", ""),
            )
        except Exception as exc:
            logger.warning("Gmail send_draft failed: %s", exc)
            return self._handle_http_error(exc)

    # ------------------------------------------------------------------ attachments

    def download_attachment(self, *, message_id: str, attachment_id: str) -> AttachmentData:
        try:
            service = self._service()
            result = service.users().messages().attachments().get(
                userId="me", messageId=message_id, id=attachment_id
            ).execute()
            data = result.get("data", "")
            # Gmail returns URL-safe base64; convert to standard base64
            data_std = base64.urlsafe_b64decode(data + "==")
            data_b64 = base64.b64encode(data_std).decode()
            return AttachmentData(
                ok=True,
                data_b64=data_b64,
                size_bytes=result.get("size", len(data_std)),
            )
        except Exception as exc:
            logger.warning("Gmail download_attachment failed: %s", exc)
            sr = self._handle_http_error(exc)
            return AttachmentData(ok=False, error=sr.error)

    def upload_attachment(
        self, *, filename: str, content_type: str, data_b64: str
    ) -> AttachmentData:
        # Gmail doesn't have a standalone upload; attachments are part of messages.
        # Return the data unchanged — caller embeds it in send/create_draft.
        return AttachmentData(
            ok=True, data_b64=data_b64, filename=filename, content_type=content_type
        )

    # ------------------------------------------------------------------ threads

    def list_threads(
        self, *, q: str = "", page_token: str = "", max_results: int = 50
    ) -> tuple[list[dict], str]:
        """Returns (threads, next_page_token)."""
        try:
            service = self._service()
            params: dict = {"userId": "me", "maxResults": min(max_results, 500)}
            if q:
                params["q"] = q
            if page_token:
                params["pageToken"] = page_token
            result = service.users().threads().list(**params).execute()
            return result.get("threads", []), result.get("nextPageToken", "")
        except Exception as exc:
            logger.warning("Gmail list_threads failed: %s", exc)
            return [], ""

    # ------------------------------------------------------------------ receive / sync

    def receive(self, limit: int = 50) -> list[RawMessage]:
        """Fetch recent inbox messages."""
        try:
            service = self._service()
            result = service.users().messages().list(
                userId="me",
                labelIds=[_LABEL_INBOX],
                maxResults=min(limit, 500),
            ).execute()
            messages = []
            for stub in result.get("messages", []):
                raw = self._fetch_message(service, stub["id"])
                if raw:
                    messages.append(raw)
            return messages
        except Exception as exc:
            logger.warning("Gmail receive failed: %s", exc)
            return []

    def sync(self, cursor: str = "") -> SyncResult:
        """Incremental sync using Gmail historyId.

        If cursor is empty, performs a bootstrap sync (last 200 inbox + sent messages).
        Returns SyncResult with messages and the next cursor.
        """
        try:
            service = self._service()
            if cursor:
                return self._incremental_sync(service, cursor)
            return self._bootstrap_sync(service)
        except Exception as exc:
            logger.warning("Gmail sync failed: %s", exc)
            return SyncResult(error=str(exc)[:500])

    def _bootstrap_sync(self, service) -> SyncResult:
        """First-time sync: fetch last 200 messages from INBOX + SENT."""
        messages: list[RawMessage] = []
        history_id = ""

        for label in [_LABEL_INBOX, _LABEL_SENT]:
            result = service.users().messages().list(
                userId="me", labelIds=[label], maxResults=100
            ).execute()
            for stub in result.get("messages", []):
                raw = self._fetch_message(service, stub["id"])
                if raw:
                    messages.append(raw)
                    # Track highest historyId
                    if not history_id:
                        # Get it from the first full message
                        pass

        # Fetch the current historyId for future incremental syncs
        profile = service.users().getProfile(userId="me").execute()
        next_cursor = str(profile.get("historyId", ""))

        return SyncResult(messages=messages, next_cursor=next_cursor)

    def _incremental_sync(self, service, start_history_id: str) -> SyncResult:
        """Incremental sync: fetch changes since start_history_id."""
        messages: list[RawMessage] = []
        next_history_id = start_history_id
        page_token = ""

        while True:
            params: dict = {
                "userId": "me",
                "startHistoryId": start_history_id,
                "historyTypes": ["messageAdded"],
            }
            if page_token:
                params["pageToken"] = page_token

            result = service.users().history().list(**params).execute()
            next_history_id = result.get("historyId", start_history_id)

            for history_item in result.get("history", []):
                for added in history_item.get("messagesAdded", []):
                    msg_stub = added.get("message", {})
                    msg_id = msg_stub.get("id", "")
                    if msg_id:
                        raw = self._fetch_message(service, msg_id)
                        if raw:
                            messages.append(raw)

            page_token = result.get("nextPageToken", "")
            if not page_token:
                break

        return SyncResult(messages=messages, next_cursor=next_history_id)

    def _fetch_message(self, service, message_id: str) -> RawMessage | None:
        """Fetch and parse a single Gmail message by ID."""
        try:
            msg = service.users().messages().get(
                userId="me", id=message_id, format="full"
            ).execute()
            return _parse_gmail_message(msg)
        except Exception as exc:
            logger.warning("Failed to fetch Gmail message %s: %s", message_id, exc)
            return None


# ---------------------------------------------------------------------------
# MIME helpers
# ---------------------------------------------------------------------------

def _build_raw_message(
    *,
    to_email: str,
    from_email: str,
    subject: str,
    body: str,
    body_html: str = "",
    attachments: list[dict] | None = None,
) -> str:
    """Build a URL-safe base64-encoded RFC 2822 message."""
    if attachments:
        msg = MIMEMultipart("mixed")
        inner = MIMEMultipart("alternative")
        inner.attach(MIMEText(body or "", "plain", "utf-8"))
        if body_html:
            inner.attach(MIMEText(body_html, "html", "utf-8"))
        msg.attach(inner)
        for att in attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(base64.b64decode(att.get("content_b64", "")))
            _email_encoders.encode_base64(part)
            fname = att.get("filename", "attachment")
            part.add_header("Content-Disposition", "attachment", filename=fname)
            part.add_header("Content-Type", att.get("content_type", "application/octet-stream"),
                            name=fname)
            msg.attach(part)
    elif body_html:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body or "", "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))
    else:
        msg = MIMEText(body or "", "plain", "utf-8")

    msg["To"] = to_email
    msg["From"] = from_email
    msg["Subject"] = subject
    raw_bytes = msg.as_bytes()
    return base64.urlsafe_b64encode(raw_bytes).decode()


def _parse_gmail_message(msg: dict) -> RawMessage:
    """Convert a Gmail API full-format message dict into a RawMessage."""
    headers = {h["name"].lower(): h["value"]
               for h in msg.get("payload", {}).get("headers", [])}

    subject = headers.get("subject", "")
    from_email = _extract_email(headers.get("from", ""))
    to_email = _extract_email(headers.get("to", ""))
    date_str = headers.get("date", "")
    date = _parse_date(date_str)

    label_ids = msg.get("labelIds", [])
    is_read = _LABEL_UNREAD not in label_ids
    direction = "outbound" if _LABEL_SENT in label_ids else "inbound"

    if _LABEL_TRASH in label_ids:
        folder = "trash"
    elif _LABEL_DRAFTS in label_ids:
        folder = "drafts"
    elif _LABEL_SENT in label_ids:
        folder = "sent"
    elif _LABEL_INBOX in label_ids:
        folder = "inbox"
    else:
        folder = "inbox"

    body_plain, body_html, attachments = _extract_parts(msg.get("payload", {}))

    return RawMessage(
        provider_message_id=msg.get("id", ""),
        thread_id=msg.get("threadId", ""),
        subject=subject,
        body=body_plain,
        body_html=body_html,
        from_email=from_email,
        to_email=to_email,
        date=date,
        direction=direction,
        folder=folder,
        is_read=is_read,
        labels=label_ids,
        attachments=attachments,
    )


def _extract_email(header_value: str) -> str:
    """Extract bare email address from 'Name <email>' or plain 'email' string."""
    if "<" in header_value and ">" in header_value:
        start = header_value.rfind("<") + 1
        end = header_value.rfind(">")
        return header_value[start:end].strip()
    return header_value.strip()


def _parse_date(date_str: str) -> datetime | None:
    """Parse RFC 2822 date string to UTC datetime."""
    if not date_str:
        return None
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _extract_parts(payload: dict) -> tuple[str, str, list[dict]]:
    """Recursively extract (body_plain, body_html, attachments) from MIME payload."""
    body_plain = ""
    body_html = ""
    attachments: list[dict] = []
    _walk_parts(payload, body_plain, body_html, attachments)

    # Direct body (non-multipart)
    if not body_plain and not body_html:
        mime = payload.get("mimeType", "")
        data = payload.get("body", {}).get("data", "")
        if data:
            decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            if mime == "text/html":
                body_html = decoded
            else:
                body_plain = decoded

    return body_plain, body_html, attachments


def _walk_parts(payload: dict, body_plain_ref: str, body_html_ref: str,
                attachments: list[dict]) -> tuple[str, str]:
    """Walk MIME parts recursively, mutating attachments list in place."""
    bp = body_plain_ref
    bh = body_html_ref
    mime = payload.get("mimeType", "")
    parts = payload.get("parts", [])

    if mime.startswith("multipart/"):
        for part in parts:
            new_bp, new_bh = _walk_parts(part, bp, bh, attachments)
            if new_bp and not bp:
                bp = new_bp
            if new_bh and not bh:
                bh = new_bh
    else:
        data = payload.get("body", {}).get("data", "")
        att_id = payload.get("body", {}).get("attachmentId", "")
        filename = ""
        ct = mime
        for h in payload.get("headers", []):
            n = h.get("name", "").lower()
            if n == "content-disposition":
                for part in h.get("value", "").split(";"):
                    part = part.strip()
                    if part.startswith("filename="):
                        filename = part[9:].strip('"').strip("'")
            if n == "content-type":
                ct = h.get("value", "").split(";")[0].strip()

        if att_id:
            attachments.append({
                "filename": filename or "attachment",
                "content_type": ct,
                "size_bytes": payload.get("body", {}).get("size", 0),
                "attachment_id": att_id,
            })
        elif data:
            decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            if mime == "text/html":
                bh = decoded
            elif mime == "text/plain" or not mime:
                bp = decoded

    return bp, bh
