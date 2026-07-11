"""Supabase credential loading for the LinkedIn adapter.

Credentials are NEVER hardcoded or stored in this repo. The LinkedIn app keeps
them in the browser's localStorage (entered via its Settings UI), so for the
server-side adapter we read them from environment variables instead:

    SP_SUPABASE_URL   (or SUPABASE_URL / VITE_SUPABASE_URL)
    SP_SUPABASE_KEY   (or SUPABASE_KEY / SUPABASE_ANON_KEY / VITE_SUPABASE_KEY)

The anon key (the same one the app uses) is sufficient for a read, provided the
``candidates`` table has RLS disabled as the app's setup SQL specifies.
"""
from __future__ import annotations

import os

_URL_VARS = ("SP_SUPABASE_URL", "SUPABASE_URL", "VITE_SUPABASE_URL")
_ANON_KEY_VARS = ("SP_SUPABASE_KEY", "SUPABASE_KEY", "SUPABASE_ANON_KEY", "VITE_SUPABASE_KEY")
# Service-role key — server-side ONLY, bypasses RLS. Never ship this to a browser.
_SERVICE_KEY_VARS = ("SP_SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY")


def load_supabase_credentials(*, prefer_service: bool = True) -> tuple[str | None, str | None]:
    """Return (url, key). Prefers the service-role key (so the adapter keeps
    working once RLS is enabled on the candidates table), falling back to the
    anon key. Set ``prefer_service=False`` to force anon."""
    url = next((os.environ[k] for k in _URL_VARS if os.environ.get(k)), None)
    service = next((os.environ[k] for k in _SERVICE_KEY_VARS if os.environ.get(k)), None)
    anon = next((os.environ[k] for k in _ANON_KEY_VARS if os.environ.get(k)), None)
    key = (service or anon) if prefer_service else (anon or service)
    return url, key
