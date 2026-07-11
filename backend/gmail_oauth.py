"""Gmail OAuth 2.0 helpers — authorization URL, code exchange, token refresh, encryption.

All Google library imports are guarded; the module loads cleanly without
google-auth-oauthlib installed (a RuntimeError is raised only when an OAuth
function is called).
"""
from __future__ import annotations

import json
import logging
import secrets
import warnings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_TOKEN_URI = "https://oauth2.googleapis.com/token"
_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def generate_state() -> str:
    """Return a CSRF-safe random state token."""
    return secrets.token_urlsafe(32)


def get_auth_url(*, client_id: str, redirect_uri: str, state: str) -> str:
    """Build the Google OAuth2 authorization URL for Gmail access.

    The user is sent here to grant consent. Google redirects back to
    redirect_uri with ``code`` and ``state`` query parameters.
    """
    if not client_id:
        raise ValueError("GMAIL_CLIENT_ID is not configured")
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        raise RuntimeError(
            "Gmail OAuth requires google-auth-oauthlib. "
            "Install with: pip install google-auth-oauthlib"
        )
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": "PLACEHOLDER",   # not needed for auth URL
                "redirect_uris": [redirect_uri],
                "auth_uri": _AUTH_URI,
                "token_uri": _TOKEN_URI,
            }
        },
        scopes=GMAIL_SCOPES,
        redirect_uri=redirect_uri,
    )
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=state,
        prompt="consent",   # always re-prompt so we get a refresh token
    )
    return url


def exchange_code(
    *,
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
) -> dict:
    """Exchange an authorization code for access + refresh tokens.

    Returns a dict suitable for storing in EmailProviderAccount.config_json.
    """
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        raise RuntimeError("pip install google-auth-oauthlib")
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": [redirect_uri],
                "auth_uri": _AUTH_URI,
                "token_uri": _TOKEN_URI,
            }
        },
        scopes=GMAIL_SCOPES,
        redirect_uri=redirect_uri,
    )
    flow.fetch_token(code=code)
    return _creds_to_dict(flow.credentials, client_id=client_id, client_secret=client_secret)


def refresh_access_token(config_json: str) -> dict:
    """Refresh the access token using the stored refresh_token.

    Returns an updated token dict with the new access_token and expiry.
    Raises RuntimeError if google-auth is not installed.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        raise RuntimeError("pip install google-auth")
    data = json.loads(config_json or "{}")
    creds = Credentials(
        token=data.get("access_token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", _TOKEN_URI),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes", GMAIL_SCOPES),
    )
    creds.refresh(Request())
    return _creds_to_dict(
        creds,
        client_id=data.get("client_id", ""),
        client_secret=data.get("client_secret", ""),
    )


def get_gmail_address(config_json: str) -> str:
    """Return the Gmail address associated with a set of tokens.

    Returns empty string if the call fails or google-api-python-client is absent.
    """
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
    except ImportError:
        return ""
    data = json.loads(config_json or "{}")
    creds = Credentials(
        token=data.get("access_token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", _TOKEN_URI),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes", GMAIL_SCOPES),
    )
    try:
        svc = build("gmail", "v1", credentials=creds, cache_discovery=False)
        profile = svc.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "")
    except Exception as exc:
        logger.warning("Failed to retrieve Gmail address: %s", exc)
        return ""


def encrypt_tokens(tokens_json: str, key: str | None) -> str:
    """Fernet-encrypt the token JSON string if *key* is set; return plaintext otherwise.

    The key must be a valid URL-safe base64-encoded 32-byte Fernet key.
    Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """
    if not key:
        return tokens_json
    try:
        from cryptography.fernet import Fernet
        f = Fernet(key.encode() if isinstance(key, str) else key)
        return f.encrypt(tokens_json.encode("utf-8")).decode("utf-8")
    except ImportError:
        warnings.warn(
            "cryptography package not installed — Gmail tokens stored unencrypted. "
            "Install cryptography for token encryption at rest.",
            stacklevel=2,
        )
        return tokens_json
    except Exception as exc:
        logger.error("Gmail token encryption failed (storing unencrypted): %s", exc)
        return tokens_json


def decrypt_tokens(encrypted: str, key: str | None) -> str:
    """Fernet-decrypt a token JSON string.

    Falls back to returning the value unchanged when:
    - key is absent (dev mode, no encryption)
    - cryptography is not installed
    - decryption fails (e.g. dev data that was never encrypted)
    """
    if not key:
        return encrypted
    try:
        from cryptography.fernet import Fernet
        f = Fernet(key.encode() if isinstance(key, str) else key)
        return f.decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except ImportError:
        return encrypted
    except Exception as exc:
        logger.debug("Decryption failed (could be unencrypted dev data): %s", exc)
        return encrypted


def token_expiry(config_json: str) -> datetime | None:
    """Extract the token expiry datetime from stored config JSON."""
    try:
        data = json.loads(config_json or "{}")
        expiry_str = data.get("expiry")
        if not expiry_str:
            return None
        dt = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception as exc:
        logger.debug("Failed to parse token expiry: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _creds_to_dict(creds, *, client_id: str, client_secret: str) -> dict:
    """Convert google.oauth2.credentials.Credentials to a JSON-serialisable dict."""
    expiry_iso: str | None = None
    if hasattr(creds, "expiry") and creds.expiry:
        expiry_iso = creds.expiry.replace(tzinfo=timezone.utc).isoformat()
    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": getattr(creds, "token_uri", None) or _TOKEN_URI,
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": list(getattr(creds, "scopes", None) or GMAIL_SCOPES),
        "expiry": expiry_iso,
    }
