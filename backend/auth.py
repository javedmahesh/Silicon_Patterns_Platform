"""API-key authentication dependency.

When ``SP_API_KEY`` is set, every data endpoint requires a matching ``X-API-Key``
header. When it is empty (local/dev/tests), auth is disabled and a one-time
warning is logged so it can't silently ship open.
"""
from __future__ import annotations

import logging

from fastapi import Header, HTTPException, Request, status

logger = logging.getLogger("backend.auth")
_warned = False


def require_api_key(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    global _warned
    configured: str = request.app.state.settings.api_key
    if not configured:
        if not _warned:
            logger.warning("SP_API_KEY is unset — API authentication is DISABLED (dev mode).")
            _warned = True
        return
    if not x_api_key or x_api_key != configured:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
