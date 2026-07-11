"""Phase 4: Gmail integration tests.

All Google API calls are mocked — no real credentials required.
Tests cover: OAuth flow, token refresh, send, receive/sync,
draft management, attachment download, thread sync, reply detection,
background sync, failure recovery.
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from master_db.models import Base, Company, DecisionMaker, EngagementRecommendation, LeadScore

# ---------------------------------------------------------------------- helpers

MGR = {"X-Dev-Role": "manager"}
MEM = {"X-Dev-Role": "member"}

_FAKE_TOKENS = {
    "access_token": "ya29.fake_access_token",
    "refresh_token": "1//fake_refresh_token",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": "fake-client-id.apps.googleusercontent.com",
    "client_secret": "fake-client-secret",
    "scopes": ["https://www.googleapis.com/auth/gmail.modify"],
    "expiry": "2099-01-01T00:00:00",
}

_GMAIL_SETTINGS = dict(
    gmail_client_id="fake-client-id.apps.googleusercontent.com",
    gmail_client_secret="fake-client-secret",
    gmail_redirect_uri="http://localhost:8000/outreach/gmail/callback",
)


def _seed(s):
    s.add(Company(
        company_domain="nvidia.com", canonical_company_id="NV",
        company_name="NVIDIA", name_key="nvidia",
        prospect_type="PRODUCT_COMPANY", validation_status="VALID",
    ))
    s.flush()
    s.add_all([
        LeadScore(company_domain="nvidia.com", lead_score=92.0, grade="A+", priority_rank=1),
        EngagementRecommendation(
            company_domain="nvidia.com", business_need="Scaling RTL",
            offering="Engineering staffing", pitch="We can place 5 engineers.",
            confidence=0.8, confidence_label="high",
        ),
        DecisionMaker(
            linkedin_url="https://l/cto", company_domain="nvidia.com",
            first_name="Jensen", last_name="Huang", current_title="CEO",
            seniority="senior", work_email="jensen@nvidia.com", match_score=95,
        ),
    ])
    s.commit()


@pytest.fixture()
def client(tmp_path):
    _settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'g.db').as_posix()}",
        log_json=False, dev_auth_bypass=True,
        **_GMAIL_SETTINGS,
    )
    app = create_app(_settings)
    # get_settings() is @lru_cache and returns a global singleton, so patch the call site
    with patch("backend.outreach_service.get_settings", return_value=_settings):
        with TestClient(app) as c:
            Base.metadata.create_all(app.state.db.engine)
            with app.state.db.sessionmaker() as s:
                _seed(s)
            yield c


def _fake_service():
    """Build a comprehensive mock Gmail API service."""
    svc = MagicMock()

    # users().messages().send()
    svc.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "gm_sent_001",
        "threadId": "gt_thread_001",
    }

    # users().messages().list()
    svc.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": [{"id": "gm_inbox_001"}],
    }

    # users().messages().get() — returns a simple plain-text inbox message
    raw_body = base64.urlsafe_b64encode(b"Hello from nvidia!").decode()
    svc.users.return_value.messages.return_value.get.return_value.execute.return_value = {
        "id": "gm_inbox_001",
        "threadId": "gt_thread_001",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "jensen@nvidia.com"},
                {"name": "To", "value": "outreach@siliconpatterns.com"},
                {"name": "Subject", "value": "Re: Engineering staffing"},
                {"name": "Date", "value": "Mon, 01 Jan 2024 10:00:00 +0000"},
            ],
            "body": {"data": raw_body, "size": len(b"Hello from nvidia!")},
        },
    }

    # users().drafts().create()
    svc.users.return_value.drafts.return_value.create.return_value.execute.return_value = {
        "id": "draft_001",
        "message": {"id": "gm_draft_001", "threadId": "gt_thread_002"},
    }

    # users().drafts().update()
    svc.users.return_value.drafts.return_value.update.return_value.execute.return_value = {
        "id": "draft_001",
        "message": {"id": "gm_draft_001", "threadId": "gt_thread_002"},
    }

    # users().drafts().send()
    svc.users.return_value.drafts.return_value.send.return_value.execute.return_value = {
        "id": "gm_sent_002",
        "threadId": "gt_thread_002",
    }

    # users().messages().attachments().get()
    att_data = base64.urlsafe_b64encode(b"PDF content here").decode()
    svc.users.return_value.messages.return_value.attachments.return_value.get.return_value.execute.return_value = {
        "data": att_data,
        "size": 16,
    }

    # users().threads().list()
    svc.users.return_value.threads.return_value.list.return_value.execute.return_value = {
        "threads": [{"id": "gt_thread_001", "historyId": "99999"}],
        "nextPageToken": "",
    }

    # users().getProfile()
    svc.users.return_value.getProfile.return_value.execute.return_value = {
        "emailAddress": "outreach@siliconpatterns.com",
        "historyId": "12345",
    }

    # users().history().list() — incremental sync
    svc.users.return_value.history.return_value.list.return_value.execute.return_value = {
        "history": [],
        "historyId": "12346",
    }

    return svc


def _patch_service(fake_svc=None):
    """Return a context-manager that patches googleapiclient.discovery.build."""
    svc = fake_svc or _fake_service()
    return patch("backend.email_providers.gmail.GmailProvider._service", return_value=svc)


# ====================================================================
# Provider: unit tests (no HTTP client needed)
# ====================================================================

def test_gmail_provider_send_success():
    """GmailProvider.send() calls the API and returns a populated SendResult."""
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    svc = _fake_service()
    with patch.object(provider, "_service", return_value=svc):
        result = provider.send(
            to_email="jensen@nvidia.com",
            from_email="outreach@siliconpatterns.com",
            subject="Hello",
            body="Test body",
        )
    assert result.ok
    assert result.provider_message_id == "gm_sent_001"
    assert result.thread_id == "gt_thread_001"


def test_gmail_provider_send_no_recipient():
    """Send with no recipient returns an error without hitting the API."""
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    result = provider.send(
        to_email="", from_email="outreach@sp.com", subject="Hi", body="Hi",
    )
    assert not result.ok
    assert "recipient" in result.error.lower()


def test_gmail_provider_send_thread_continuation():
    """Sending with an existing thread_id passes threadId to the API."""
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    svc = _fake_service()
    with patch.object(provider, "_service", return_value=svc):
        result = provider.send(
            to_email="jensen@nvidia.com",
            from_email="out@sp.com",
            subject="Re: Hello",
            body="Reply",
            thread_id="gt_thread_existing",
        )
    assert result.ok
    call_kwargs = svc.users.return_value.messages.return_value.send.call_args[1]["body"]
    assert "threadId" in call_kwargs


def test_gmail_provider_create_draft():
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    svc = _fake_service()
    with patch.object(provider, "_service", return_value=svc):
        result = provider.create_draft(
            to_email="j@nvidia.com", from_email="out@sp.com",
            subject="Draft subject", body="Draft body",
        )
    assert result.ok
    assert result.draft_id == "draft_001"
    assert result.thread_id == "gt_thread_002"


def test_gmail_provider_update_draft():
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    svc = _fake_service()
    with patch.object(provider, "_service", return_value=svc):
        result = provider.update_draft(
            draft_id="draft_001",
            to_email="j@nvidia.com", from_email="out@sp.com",
            subject="Updated", body="Updated body",
        )
    assert result.ok
    assert result.draft_id == "draft_001"


def test_gmail_provider_delete_draft():
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    svc = _fake_service()
    with patch.object(provider, "_service", return_value=svc):
        ok = provider.delete_draft(draft_id="draft_001")
    assert ok is True


def test_gmail_provider_send_draft():
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    svc = _fake_service()
    with patch.object(provider, "_service", return_value=svc):
        result = provider.send_draft(draft_id="draft_001")
    assert result.ok
    assert result.provider_message_id == "gm_sent_002"


def test_gmail_provider_download_attachment():
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    svc = _fake_service()
    with patch.object(provider, "_service", return_value=svc):
        result = provider.download_attachment(
            message_id="gm_inbox_001", attachment_id="att_001"
        )
    assert result.ok
    decoded = base64.b64decode(result.data_b64)
    assert decoded == b"PDF content here"


def test_gmail_provider_list_threads():
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    svc = _fake_service()
    with patch.object(provider, "_service", return_value=svc):
        threads, next_tok = provider.list_threads(max_results=10)
    assert len(threads) == 1
    assert threads[0]["id"] == "gt_thread_001"
    assert next_tok == ""


def test_gmail_provider_receive():
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    svc = _fake_service()
    with patch.object(provider, "_service", return_value=svc):
        messages = provider.receive(limit=10)
    assert len(messages) == 1
    msg = messages[0]
    assert msg.provider_message_id == "gm_inbox_001"
    assert msg.from_email == "jensen@nvidia.com"
    assert msg.subject == "Re: Engineering staffing"
    assert msg.direction == "inbound"
    assert msg.folder == "inbox"
    assert not msg.is_read


def test_gmail_provider_bootstrap_sync():
    """sync() with no cursor performs a bootstrap sync and returns a historyId cursor."""
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    svc = _fake_service()
    with patch.object(provider, "_service", return_value=svc):
        result = provider.sync(cursor="")
    assert not result.error
    assert result.next_cursor == "12345"   # from getProfile historyId
    assert len(result.messages) >= 1


def test_gmail_provider_incremental_sync():
    """sync() with a cursor uses history.list for incremental updates."""
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    svc = _fake_service()
    with patch.object(provider, "_service", return_value=svc):
        result = provider.sync(cursor="12340")
    assert not result.error
    assert result.next_cursor == "12346"
    # No new messages in this history batch
    assert len(result.messages) == 0


def test_gmail_provider_capabilities():
    from backend.email_providers.gmail import GmailProvider
    caps = GmailProvider().capabilities()
    assert caps.can_send
    assert caps.can_receive
    assert caps.supports_drafts
    assert caps.supports_sync


def test_gmail_provider_validate_config_good():
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider()
    assert provider.validate_config(json.dumps(_FAKE_TOKENS)) is True


def test_gmail_provider_validate_config_missing_refresh():
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider()
    bad = {**_FAKE_TOKENS, "refresh_token": ""}
    assert provider.validate_config(json.dumps(bad)) is False


def test_gmail_provider_validate_config_empty():
    from backend.email_providers.gmail import GmailProvider
    assert GmailProvider().validate_config("{}") is False


# ====================================================================
# Error recovery
# ====================================================================

def test_gmail_send_401_returns_descriptive_error():
    """HTTP 401 from Gmail API maps to a reconnect message."""
    from backend.email_providers.gmail import GmailProvider
    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        pytest.skip("google-api-python-client not installed")

    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    fake_resp = MagicMock()
    fake_resp.status = 401
    exc = HttpError(resp=fake_resp, content=b"Unauthorized")

    svc = MagicMock()
    svc.users.return_value.messages.return_value.send.return_value.execute.side_effect = exc

    with patch.object(provider, "_service", return_value=svc):
        result = provider.send(
            to_email="j@nvidia.com", from_email="out@sp.com",
            subject="Hi", body="Hello",
        )
    assert not result.ok
    assert "reconnect" in result.error.lower() or "revoked" in result.error.lower()


def test_gmail_send_429_rate_limit():
    """HTTP 429 from Gmail API is reported as rate limit error."""
    from backend.email_providers.gmail import GmailProvider
    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        pytest.skip("google-api-python-client not installed")

    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    fake_resp = MagicMock()
    fake_resp.status = 429
    exc = HttpError(resp=fake_resp, content=b"Too Many Requests")

    svc = MagicMock()
    svc.users.return_value.messages.return_value.send.return_value.execute.side_effect = exc

    with patch.object(provider, "_service", return_value=svc):
        result = provider.send(
            to_email="j@nvidia.com", from_email="out@sp.com",
            subject="Hi", body="Hello",
        )
    assert not result.ok
    assert "rate limit" in result.error.lower()


def test_gmail_send_network_failure():
    """Generic exception during send is caught and returned as error."""
    from backend.email_providers.gmail import GmailProvider
    provider = GmailProvider(config_json=json.dumps(_FAKE_TOKENS))
    svc = MagicMock()
    svc.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
        ConnectionError("Network unreachable")
    )
    with patch.object(provider, "_service", return_value=svc):
        result = provider.send(
            to_email="j@nvidia.com", from_email="out@sp.com",
            subject="Hi", body="Hello",
        )
    assert not result.ok
    assert "Network" in result.error or "unreachable" in result.error


# ====================================================================
# OAuth helpers (unit tests)
# ====================================================================

def test_encrypt_decrypt_tokens_roundtrip():
    """Encrypted tokens can be decrypted back to the original."""
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        pytest.skip("cryptography not installed")
    from backend.gmail_oauth import decrypt_tokens, encrypt_tokens

    key = Fernet.generate_key().decode()
    original = json.dumps(_FAKE_TOKENS)
    encrypted = encrypt_tokens(original, key)
    assert encrypted != original
    decrypted = decrypt_tokens(encrypted, key)
    assert json.loads(decrypted) == _FAKE_TOKENS


def test_encrypt_no_key_passthrough():
    """Without an encryption key, tokens are stored as plaintext."""
    from backend.gmail_oauth import encrypt_tokens, decrypt_tokens
    original = json.dumps({"access_token": "ya29.x"})
    assert encrypt_tokens(original, None) == original
    assert decrypt_tokens(original, None) == original


def test_decrypt_unencrypted_data_with_key():
    """Decrypting plaintext with a key should fall back gracefully."""
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        pytest.skip("cryptography not installed")
    from backend.gmail_oauth import decrypt_tokens

    key = Fernet.generate_key().decode()
    plain = json.dumps({"access_token": "ya29.x", "refresh_token": "rt"})
    # Should return plain without raising
    result = decrypt_tokens(plain, key)
    # Result is either original or plain (fallback)
    assert "access_token" in result or result == plain


def test_generate_state_is_random():
    from backend.gmail_oauth import generate_state
    states = {generate_state() for _ in range(10)}
    assert len(states) == 10  # all unique


def test_token_expiry_parsing():
    from backend.gmail_oauth import token_expiry
    tokens = {**_FAKE_TOKENS, "expiry": "2099-06-15T12:00:00"}
    expiry = token_expiry(json.dumps(tokens))
    assert expiry is not None
    assert expiry.year == 2099
    assert expiry.tzinfo is not None


def test_token_expiry_missing():
    from backend.gmail_oauth import token_expiry
    tokens = {**_FAKE_TOKENS}
    tokens.pop("expiry", None)
    assert token_expiry(json.dumps(tokens)) is None


def test_get_auth_url_requires_client_id():
    from backend.gmail_oauth import get_auth_url
    with pytest.raises((ValueError, RuntimeError)):
        get_auth_url(client_id="", redirect_uri="http://localhost/cb", state="abc")


# ====================================================================
# OAuth API endpoints (via TestClient)
# ====================================================================

def test_gmail_status_no_account(client):
    r = client.get("/outreach/gmail/status", headers=MGR)
    assert r.status_code == 200
    body = r.json()
    assert body["provider_type"] in ("mock", "gmail")


@patch("backend.gmail_oauth.get_auth_url", return_value="https://accounts.google.com/o/oauth2/auth?state=teststate")
@patch("backend.gmail_oauth.generate_state", return_value="teststate123")
def test_gmail_get_auth_url(mock_state, mock_url, client):
    r = client.get("/outreach/gmail/auth-url", headers=MGR)
    assert r.status_code == 200
    body = r.json()
    assert "auth_url" in body
    assert "state" in body
    assert body["state"] == "teststate123"


@patch("backend.gmail_oauth.get_auth_url", return_value="https://accounts.google.com/auth")
@patch("backend.gmail_oauth.generate_state", return_value="csrf_state_abc")
@patch("backend.gmail_oauth.exchange_code", return_value=_FAKE_TOKENS)
@patch("backend.gmail_oauth.get_gmail_address", return_value="outreach@siliconpatterns.com")
@patch("backend.gmail_oauth.token_expiry", return_value=datetime(2099, 1, 1, tzinfo=timezone.utc))
def test_gmail_connect_flow(mock_expiry, mock_addr, mock_exchange, mock_state, mock_url, client):
    # Step 1: get auth URL (stores state)
    r1 = client.get("/outreach/gmail/auth-url", headers=MGR)
    assert r1.status_code == 200

    # Step 2: callback with matching state
    r2 = client.get(
        "/outreach/gmail/callback",
        params={"code": "4/auth_code_here", "state": "csrf_state_abc"},
        headers=MGR,
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["connection_status"] == "connected"
    assert body["email_address"] == "outreach@siliconpatterns.com"


@patch("backend.gmail_oauth.get_auth_url", return_value="https://accounts.google.com/auth")
@patch("backend.gmail_oauth.generate_state", return_value="csrf_state_xyz")
@patch("backend.gmail_oauth.exchange_code", return_value=_FAKE_TOKENS)
@patch("backend.gmail_oauth.get_gmail_address", return_value="user@sp.com")
@patch("backend.gmail_oauth.token_expiry", return_value=None)
def test_gmail_callback_wrong_state(mock_e, mock_a, mock_ex, mock_s, mock_u, client):
    # Get auth URL (stores state "csrf_state_xyz")
    client.get("/outreach/gmail/auth-url", headers=MGR)
    # Callback with wrong state
    r = client.get(
        "/outreach/gmail/callback",
        params={"code": "code123", "state": "wrong_state"},
        headers=MGR,
    )
    assert r.status_code == 400


@patch("backend.gmail_oauth.get_auth_url", return_value="https://accounts.google.com/auth")
@patch("backend.gmail_oauth.generate_state", return_value="state_for_disconnect")
@patch("backend.gmail_oauth.exchange_code", return_value=_FAKE_TOKENS)
@patch("backend.gmail_oauth.get_gmail_address", return_value="user@sp.com")
@patch("backend.gmail_oauth.token_expiry", return_value=None)
def test_gmail_disconnect(mock_e, mock_a, mock_ex, mock_s, mock_u, client):
    # Connect first
    client.get("/outreach/gmail/auth-url", headers=MGR)
    client.get(
        "/outreach/gmail/callback",
        params={"code": "code_disconnect", "state": "state_for_disconnect"},
        headers=MGR,
    )
    # Disconnect
    r = client.post("/outreach/gmail/disconnect", headers=MGR)
    assert r.status_code == 200
    body = r.json()
    assert body["connection_status"] == "disconnected"


# ====================================================================
# Token refresh endpoint
# ====================================================================

@patch("backend.gmail_oauth.get_auth_url", return_value="https://accounts.google.com/auth")
@patch("backend.gmail_oauth.generate_state", return_value="state_refresh")
@patch("backend.gmail_oauth.exchange_code", return_value=_FAKE_TOKENS)
@patch("backend.gmail_oauth.get_gmail_address", return_value="user@sp.com")
@patch("backend.gmail_oauth.token_expiry", return_value=None)
def test_gmail_refresh_token(mock_e, mock_a, mock_ex, mock_s, mock_u, client):
    # Connect first
    client.get("/outreach/gmail/auth-url", headers=MGR)
    client.get(
        "/outreach/gmail/callback",
        params={"code": "code_for_refresh", "state": "state_refresh"},
        headers=MGR,
    )
    new_tokens = {**_FAKE_TOKENS, "access_token": "ya29.refreshed", "expiry": "2099-12-31T00:00:00"}
    with patch("backend.gmail_oauth.refresh_access_token", return_value=new_tokens):
        with patch("backend.gmail_oauth.token_expiry",
                   return_value=datetime(2099, 12, 31, tzinfo=timezone.utc)):
            r = client.post("/outreach/gmail/refresh-token", headers=MGR)
    assert r.status_code == 200
    body = r.json()
    assert body["refreshed"] is True


# ====================================================================
# Gmail sync endpoint
# ====================================================================

@patch("backend.gmail_oauth.get_auth_url", return_value="https://accounts.google.com/auth")
@patch("backend.gmail_oauth.generate_state", return_value="state_sync")
@patch("backend.gmail_oauth.exchange_code", return_value=_FAKE_TOKENS)
@patch("backend.gmail_oauth.get_gmail_address", return_value="user@sp.com")
@patch("backend.gmail_oauth.token_expiry", return_value=None)
def test_gmail_sync_endpoint(mock_e, mock_a, mock_ex, mock_s, mock_u, client):
    # Connect
    client.get("/outreach/gmail/auth-url", headers=MGR)
    client.get(
        "/outreach/gmail/callback",
        params={"code": "code_sync", "state": "state_sync"},
        headers=MGR,
    )
    # Sync (with mocked provider)
    sync_result_mock = MagicMock()
    sync_result_mock.error = ""
    sync_result_mock.messages = []
    sync_result_mock.next_cursor = "99999"

    with patch("backend.email_providers.gmail.GmailProvider.sync", return_value=sync_result_mock):
        r = client.post("/outreach/gmail/sync?incremental=true", headers=MGR)
    assert r.status_code == 200
    body = r.json()
    assert "ingested" in body
    assert "skipped" in body


# ====================================================================
# Reply detection via gmail_sync._ingest_raw_message
# ====================================================================

def test_gmail_sync_reply_detection(client):
    """Inbound Gmail message matching a known DM email associates with existing lead."""
    from backend.email_providers.base import RawMessage
    from backend.gmail_sync import _ingest_raw_message

    # First sync from discovery to create a lead
    client.post("/outreach/leads/sync", headers=MGR)

    with client.app.state.db.sessionmaker() as session:
        # Find the outreach lead
        from master_db.models import OutreachLead
        from sqlalchemy import select
        lead = session.scalar(select(OutreachLead).limit(1))
        assert lead is not None

        raw = RawMessage(
            provider_message_id="gm_reply_unique_001",
            thread_id="gt_thread_reply",
            subject="Re: Engineering staffing",
            body="Sounds great, let's talk!",
            body_html="",
            from_email="jensen@nvidia.com",   # matches DecisionMaker.work_email
            to_email="outreach@siliconpatterns.com",
            date=datetime.now(timezone.utc),
            direction="inbound",
            folder="inbox",
            is_read=False,
        )
        ingested = _ingest_raw_message(session, raw)
        session.commit()

    assert ingested is True


def test_gmail_sync_deduplication(client):
    """Syncing the same provider_message_id twice inserts only one row."""
    from backend.email_providers.base import RawMessage
    from backend.gmail_sync import _ingest_raw_message

    client.post("/outreach/leads/sync", headers=MGR)

    with client.app.state.db.sessionmaker() as session:
        raw = RawMessage(
            provider_message_id="gm_dedup_unique_001",
            thread_id="gt_thread_dedup",
            subject="Duplicate test",
            body="Hello",
            body_html="",
            from_email="jensen@nvidia.com",
            to_email="out@sp.com",
            date=datetime.now(timezone.utc),
            direction="inbound",
            folder="inbox",
            is_read=False,
        )
        first = _ingest_raw_message(session, raw)
        session.flush()
        second = _ingest_raw_message(session, raw)
        session.commit()

    assert first is True
    assert second is False   # deduplicated


# ====================================================================
# send_message uses Gmail when provider is connected
# ====================================================================

@patch("backend.gmail_oauth.get_auth_url", return_value="https://accounts.google.com/auth")
@patch("backend.gmail_oauth.generate_state", return_value="state_send")
@patch("backend.gmail_oauth.exchange_code", return_value=_FAKE_TOKENS)
@patch("backend.gmail_oauth.get_gmail_address", return_value="outreach@siliconpatterns.com")
@patch("backend.gmail_oauth.token_expiry", return_value=None)
def test_send_message_uses_gmail_provider(mock_e, mock_a, mock_ex, mock_s, mock_u, client):
    """When Gmail is connected, send_message() routes through GmailProvider."""
    # Connect Gmail
    client.get("/outreach/gmail/auth-url", headers=MGR)
    client.get(
        "/outreach/gmail/callback",
        params={"code": "code_send_test", "state": "state_send"},
        headers=MGR,
    )

    # Sync + draft pipeline
    client.post("/outreach/leads/sync", headers=MGR)
    lid = client.get("/outreach/leads", headers=MGR).json()["items"][0]["id"]
    tmpl_id = client.post(
        "/outreach/templates", headers=MGR,
        json={"name": "t1", "category": "intro", "subject": "Hello {{company}}",
              "body": "Hi {{first_name}}", "is_active": True},
    ).json()["id"]
    mid = client.post(
        f"/outreach/leads/{lid}/messages", headers=MGR,
        json={"template_id": tmpl_id},
    ).json()["id"]
    client.post(f"/outreach/messages/{mid}/submit", headers=MGR)
    client.post(f"/outreach/messages/{mid}/approve", headers=MGR)

    fake_svc = _fake_service()
    with patch("backend.email_providers.gmail.GmailProvider._service", return_value=fake_svc):
        r = client.post(f"/outreach/messages/{mid}/send", headers=MGR)

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "sent"
    assert body["provider"] == "gmail"
    assert body["provider_message_id"] == "gm_sent_001"


# ====================================================================
# Background sync: scheduler tick includes Gmail
# ====================================================================

def test_scheduler_tick_includes_gmail(client):
    """Scheduler tick response includes gmail_synced and gmail_tokens_refreshed counts."""
    r = client.post("/outreach/scheduler/tick", headers=MGR)
    assert r.status_code == 200
    body = r.json()
    assert "gmail_synced" in body
    assert "gmail_tokens_refreshed" in body
    assert isinstance(body["gmail_synced"], int)
    assert isinstance(body["gmail_tokens_refreshed"], int)


# ====================================================================
# MIME helpers
# ====================================================================

def test_build_raw_message_produces_valid_mime():
    """_build_raw_message returns URL-safe base64-encoded RFC 2822 content."""
    from backend.email_providers.gmail import _build_raw_message
    from email import message_from_bytes

    raw = _build_raw_message(
        to_email="to@example.com",
        from_email="from@example.com",
        subject="Test Subject",
        body="Plain text body",
    )
    decoded = base64.urlsafe_b64decode(raw + "==")
    msg = message_from_bytes(decoded)
    assert msg["Subject"] == "Test Subject"
    assert msg["To"] == "to@example.com"


def test_parse_gmail_message_inbound():
    """_parse_gmail_message correctly identifies inbound messages."""
    from backend.email_providers.gmail import _parse_gmail_message
    raw_body = base64.urlsafe_b64encode(b"Message body").decode()
    msg_dict = {
        "id": "msg1",
        "threadId": "thread1",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recv@example.com"},
                {"name": "Subject", "value": "Hello"},
                {"name": "Date", "value": "Mon, 01 Jan 2024 12:00:00 +0000"},
            ],
            "body": {"data": raw_body, "size": 12},
        },
    }
    raw = _parse_gmail_message(msg_dict)
    assert raw.provider_message_id == "msg1"
    assert raw.thread_id == "thread1"
    assert raw.from_email == "sender@example.com"
    assert raw.direction == "inbound"
    assert raw.folder == "inbox"
    assert not raw.is_read


def test_parse_gmail_message_sent():
    """_parse_gmail_message identifies SENT messages as outbound."""
    from backend.email_providers.gmail import _parse_gmail_message
    raw_body = base64.urlsafe_b64encode(b"Sent message").decode()
    msg_dict = {
        "id": "sent1",
        "threadId": "thread2",
        "labelIds": ["SENT"],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "me@sp.com"},
                {"name": "To", "value": "dest@example.com"},
                {"name": "Subject", "value": "Outbound"},
                {"name": "Date", "value": "Mon, 01 Jan 2024 12:00:00 +0000"},
            ],
            "body": {"data": raw_body, "size": 12},
        },
    }
    raw = _parse_gmail_message(msg_dict)
    assert raw.direction == "outbound"
    assert raw.folder == "sent"
    assert raw.is_read  # SENT messages don't have UNREAD label


def test_registry_get_provider_for_user_gmail():
    """get_provider_for_user('gmail', config) returns a GmailProvider instance."""
    from backend.email_providers.registry import get_provider_for_user
    from backend.email_providers.gmail import GmailProvider

    provider = get_provider_for_user("gmail", json.dumps(_FAKE_TOKENS))
    assert isinstance(provider, GmailProvider)


def test_registry_get_provider_for_user_mock():
    """get_provider_for_user('mock', ...) returns the MockEmailProvider singleton."""
    from backend.email_providers.registry import get_provider_for_user
    from backend.email_providers.mock import MockEmailProvider

    provider = get_provider_for_user("mock", "{}")
    assert isinstance(provider, MockEmailProvider)
