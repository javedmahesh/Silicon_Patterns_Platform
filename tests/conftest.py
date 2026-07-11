"""Shared pytest fixtures."""
import os
from pathlib import Path

# --- Hermetic test environment ---------------------------------------------
# backend.config.Settings auto-reads a developer-local `.env` (pydantic-settings,
# env_file=".env"), and os.environ takes precedence over that file. A real `.env`
# (e.g. one holding APIFY_API_TOKEN and real Microsoft Entra credentials for local
# setup, copied from .env.example with a placeholder DATABASE_URL) would otherwise
# flip the suite out of local/dev mode: a non-SQLite database_url, an enabled
# API-key gate (401 on every endpoint), and the dev auth bypass silently turning
# off (security._bypass_on treats a configured Microsoft app the same as a
# configured API key — "real auth is available" — so any test relying on the
# zero-config bypass would start getting real 401s instead of a synthetic user).
# Pin these OFF and the DB to the local SQLite default so tests never depend on the
# developer's .env. Tests that need a temp DB or real Microsoft config still
# override database_url / microsoft_tenant_id / microsoft_client_id explicitly via
# Settings(...) kwargs, which always win over os.environ.
_PLATFORM_ROOT = Path(__file__).resolve().parent.parent
os.environ["SP_API_KEY"] = ""
os.environ["API_KEY"] = ""
os.environ["MICROSOFT_TENANT_ID"] = ""
os.environ["MICROSOFT_CLIENT_ID"] = ""
os.environ["MICROSOFT_CLIENT_SECRET"] = ""
os.environ["DATABASE_URL"] = f"sqlite:///{(_PLATFORM_ROOT / 'master_local.db').as_posix()}"
# Never spin up the Standard Run scheduler thread under the test suite (a TestClient
# app is created many times over). Tests that exercise the scheduler enable it
# explicitly via Settings(scheduler_enabled=True).
os.environ["SP_SCHEDULER_ENABLED"] = "false"

import pytest

from backend import cache


@pytest.fixture(autouse=True)
def _clear_response_cache():
    """Analytics responses are memoized per-process; isolate every test from the
    previous one's cached payloads (and from a stale version key)."""
    cache.clear()
    yield
    cache.clear()
