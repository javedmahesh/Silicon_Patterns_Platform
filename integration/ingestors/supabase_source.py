"""Supabase adapter for the LinkedIn Scraper.

Reads the ``candidates`` table directly from the existing Supabase instance over
the same PostgREST endpoint the app uses (``GET /rest/v1/candidates?select=*``
with ``apikey`` + ``Bearer``), then feeds the rows through the existing
:class:`~integration.ingestors.linkedin.LinkedInIngestor` — so company resolution,
``decision_makers`` population and the review-queue behaviour are identical to
the file-based path.

This is **read-only**: it never writes to Supabase and never touches the LinkedIn
application, so existing LinkedIn Scraper functionality is fully preserved.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from integration.ingestors.base import IngestionResult
from integration.ingestors.linkedin import LinkedInIngestor
from integration.resolver import CompanyResolver

logger = logging.getLogger(__name__)

CANDIDATES_PATH = "/rest/v1/candidates"


class SupabaseError(RuntimeError):
    """Raised when the Supabase REST read fails or returns an unexpected shape."""


def fetch_candidates(
    url: str,
    key: str,
    *,
    page_size: int = 1000,
    timeout: float = 30.0,
    client: Any = None,
) -> list[dict[str, Any]]:
    """Fetch every row of the ``candidates`` table via PostgREST, paginating with
    ``limit``/``offset`` so tables larger than the server page cap are read fully.

    *client* is an optional pre-built ``httpx.Client`` (used by tests with a mock
    transport); otherwise one is created and closed here.
    """
    if not url or not key:
        raise SupabaseError("Supabase URL and key are required (set SP_SUPABASE_URL / SP_SUPABASE_KEY).")

    import httpx  # imported lazily so the rest of the platform doesn't require it

    base = url.rstrip("/")
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"}
    owns_client = client is None
    client = client or httpx.Client(timeout=timeout)
    rows: list[dict[str, Any]] = []
    try:
        offset = 0
        while True:
            resp = client.get(
                base + CANDIDATES_PATH,
                params={"select": "*", "limit": page_size, "offset": offset},
                headers=headers,
            )
            if resp.status_code >= 400:
                raise SupabaseError(
                    f"Supabase read failed (HTTP {resp.status_code}): {resp.text[:300]}"
                )
            batch = resp.json()
            if not isinstance(batch, list):
                raise SupabaseError(f"Unexpected Supabase response (not a list): {type(batch).__name__}")
            rows.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
    finally:
        if owns_client:
            client.close()

    logger.info("Fetched %d candidate(s) from Supabase", len(rows))
    return rows


def import_decision_makers(
    session: Session,
    url: str,
    key: str,
    *,
    resolver: CompanyResolver | None = None,
    page_size: int = 1000,
    client: Any = None,
) -> IngestionResult:
    """Pull candidates from Supabase and upsert them into ``decision_makers``.

    Company identity is resolved by name through the resolver + ``company_aliases``
    layer (``create_stub=False`` — a person never mints a company); unresolved
    employers are queued for review and the person is still imported with a NULL
    ``company_domain``.
    """
    rows = fetch_candidates(url, key, page_size=page_size, client=client)
    ingestor = LinkedInIngestor(
        session,
        resolver=resolver or CompanyResolver(session),
        create_stub=False,
        mode="pipeline",
    )
    return ingestor.ingest_rows(rows, source_label=f"supabase:{url.rstrip('/')}{CANDIDATES_PATH}")
