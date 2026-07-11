"""Authentication & authorization — Microsoft Entra ID + app session JWTs.

Flow: the SPA signs the user in with Microsoft (MSAL, Authorization Code + PKCE —
see frontend/src/lib/auth/msal.ts) and posts the resulting Microsoft ID token to
``POST /auth/microsoft``. The backend verifies that token's signature locally
against the tenant's published JWKS (``verify_microsoft_id_token`` below — a public
SPA client, so no client secret is involved), extracts the user's email/name/object
id, and maps it onto the existing :class:`User` model exactly as the prior
Google-SSO and password mechanisms did before it. A successful sign-in mints our
own short-lived HS256 JWT. Browser calls then send ``Authorization: Bearer <app-jwt>``.

Dependencies:
- ``get_current_user`` — requires a valid app JWT → an active :class:`User` (else 401).
  Backs ``/auth/me``, ``/auth/logout``, ``/auth/refresh``.
- ``require_admin`` / ``require_manager`` / ``require_super_admin`` — role gates (403
  otherwise).
- ``require_principal`` — the data-endpoint gate: accepts a valid app JWT **or** the
  legacy ``X-API-Key`` (service/CI). When neither auth is configured (no
  ``SP_API_KEY``) it stays open for local dev/tests, logging a one-time warning.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from backend import repositories as repo
from backend.config import Settings
from backend.dependencies import get_session
from master_db.models import User

logger = logging.getLogger("backend.auth")
_warned_open = False

_UNAUTH = {"WWW-Authenticate": "Bearer"}

# Dev-bypass synthetic identities, for validating the role hierarchy without a real
# account. The active one is chosen client-side via the X-Dev-Role header (the
# DevRoleSwitcher).
_DEV_USERS: dict[str, tuple[str, str]] = {
    "admin": ("betatestingadmin@siliconpatterns.com", "Beta Admin (dev)"),
    "manager": ("betatestingmanager@siliconpatterns.com", "Beta Manager (dev)"),
    "member": ("betatestingmember@siliconpatterns.com", "Beta Member (dev)"),
}


def _bypass_on(settings: Settings) -> bool:
    """Dev bypass: NEVER available when settings.environment == 'production' (closes
    the fail-open gap where a misconfigured prod deploy silently served an open API
    under a synthetic admin) — regardless of this flag. Outside production: an
    explicit opt-in (DEV_AUTH_BYPASS=true), OR — the existing zero-config local-dev/
    test convenience — neither SP_API_KEY nor Microsoft Entra is configured. Real
    auth being *available* isn't the same as "auth is configured": a fresh
    Settings() with none of these set would otherwise have no way to authenticate at
    all, breaking the X-Dev-Role-header pattern most of this test suite relies on;
    conversely, a deployment (or test) that DOES configure Microsoft wants real
    enforcement even before ENVIRONMENT=production is set."""
    if settings.is_production:
        return False
    microsoft_configured = bool(settings.microsoft_tenant_id and settings.microsoft_client_id)
    return settings.dev_auth_bypass or not (settings.api_key or microsoft_configured)


@lru_cache(maxsize=8)
def _jwks_client(tenant_id: str) -> PyJWKClient:
    return PyJWKClient(f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys")


def verify_microsoft_id_token(id_token: str, settings: Settings) -> dict:
    """Verify a Microsoft Entra ID token's signature, issuer, audience and expiry
    against the tenant's published JWKS — a public SPA client (Authorization Code +
    PKCE), so no client secret is involved in verification, and no network round
    trip to Microsoft per sign-in beyond JWKS key caching. Returns the decoded
    claims (``email``/``name``/``oid`` are what callers use). Raises on any
    failure (malformed token, bad signature, wrong tenant/audience, expired) —
    callers should catch broadly, since PyJWT's JWKS-lookup and decode errors are
    not all one exception family."""
    tenant_id = settings.microsoft_tenant_id
    signing_key = _jwks_client(tenant_id).get_signing_key_from_jwt(id_token)
    return jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.microsoft_client_id,
        issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0",
    )


def _dev_user(session: Session, role: str | None) -> User:
    """Get-or-create the synthetic dev identity for *role* (dev bypass only)."""
    key = role if role in _DEV_USERS else "admin"
    email, name = _DEV_USERS[key]
    user = repo.get_user_by_email(session, email)
    if user is None:
        user = repo.create_user(session, email=email, full_name=name, role=key)
        session.commit()
    return user


# ------------------------------------------------------------------- app JWTs
def issue_app_token(user: User, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.email,
        "uid": user.id,
        "role": user.role,
        "name": user.full_name,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_ttl_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_app_token(token: str, settings: Settings) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def _bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


# ----------------------------------------------------------------- dependencies
def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    x_dev_role: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User:
    """Resolve the signed-in user from the Bearer app JWT, or 401.

    Under the dev bypass no token is required: the synthetic identity for the
    ``X-Dev-Role`` header (admin|manager|member) is returned instead.
    """
    settings: Settings = request.app.state.settings
    token = _bearer(authorization)
    if not token:
        if _bypass_on(settings):
            user = _dev_user(session, x_dev_role)
            repo.touch_last_seen(session, user)
            return user
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required", headers=_UNAUTH)
    try:
        payload = decode_app_token(token, settings)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token", headers=_UNAUTH)
    user = repo.get_user_by_email(session, str(payload.get("sub", "")))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "account not found or deactivated", headers=_UNAUTH)
    repo.touch_last_seen(session, user)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Admin or super_admin (super_admin is a strict superset of admin)."""
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin role required")
    return user


def require_manager(user: User = Depends(get_current_user)) -> User:
    """Admin, super_admin, or manager (managers run lead assignment + the workload dashboard)."""
    if user.role not in ("admin", "manager", "super_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "manager role required")
    return user


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    """Gate for the handful of actions only the platform's top role may take — granting/
    revoking super_admin itself and touching another super_admin's role/active-state/
    deletion (see backend/services.py::_guard_super_admin_tier)."""
    if user.role != "super_admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "super_admin role required")
    return user


def require_principal(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User | None:
    """Gate for data endpoints: a valid app JWT (→ user) OR a valid API key (→ service)."""
    global _warned_open
    settings: Settings = request.app.state.settings

    if _bypass_on(settings):
        if not _warned_open:
            logger.warning("Auth bypass ACTIVE (DEV_AUTH_BYPASS) — API is OPEN. Dev only.")
            _warned_open = True
        return None

    token = _bearer(authorization)
    if token:
        try:
            payload = decode_app_token(token, settings)
        except jwt.PyJWTError:
            payload = None
        if payload is not None:
            user = repo.get_user_by_email(session, str(payload.get("sub", "")))
            if user is not None and user.is_active:
                return user
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "account not found or deactivated", headers=_UNAUTH)

    if settings.api_key and x_api_key and x_api_key == settings.api_key:
        return None

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required", headers=_UNAUTH)
