"""Gmail sync service — import Gmail messages into the outreach module.

Converts raw Gmail messages (from GmailProvider.sync()) into OutreachMessage
rows, deduplicates by provider_message_id, and auto-associates replies with
existing conversations via the conversation engine (_assign_to_conversation).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import outreach_repo as orepo
from master_db.models import DecisionMaker, OutreachMessage

logger = logging.getLogger(__name__)


def sync_user_gmail(
    session: Session,
    account,
    *,
    incremental: bool = True,
) -> dict:
    """Sync all Gmail messages for one EmailProviderAccount row.

    Returns a summary dict: {ingested, skipped, next_cursor, error}.
    Caller is responsible for committing the session.
    """
    if account.provider_type != "gmail":
        return {"error": "not a gmail account", "ingested": 0, "skipped": 0}
    if account.connection_status != "connected":
        return {"error": "account not connected", "ingested": 0, "skipped": 0}

    from backend.email_providers.gmail import GmailProvider
    from backend.gmail_oauth import decrypt_tokens

    settings = _settings()
    config = decrypt_tokens(
        account.config_json or "{}",
        settings.gmail_token_encryption_key or None,
    )

    provider = GmailProvider(config_json=config)

    # Mark as syncing
    account.sync_status = "syncing"
    session.flush()

    try:
        cursor = (account.sync_cursor or "") if incremental else ""
        result = provider.sync(cursor=cursor)

        if result.error:
            account.sync_status = "error"
            account.sync_error = result.error[:500]
            session.flush()
            return {"error": result.error, "ingested": 0, "skipped": 0}

        ingested = 0
        skipped = 0
        for raw in result.messages:
            try:
                if _ingest_raw_message(session, raw):
                    ingested += 1
                else:
                    skipped += 1
            except Exception as exc:
                logger.warning("Failed to ingest Gmail message %s: %s",
                               raw.provider_message_id, exc)
                skipped += 1

        # Update sync state
        if result.next_cursor:
            account.sync_cursor = result.next_cursor
        account.sync_status = "idle"
        account.sync_error = ""
        account.last_sync_at = datetime.now(timezone.utc)
        session.flush()

        return {
            "ingested": ingested,
            "skipped": skipped,
            "next_cursor": result.next_cursor,
        }

    except Exception as exc:
        account.sync_status = "error"
        account.sync_error = str(exc)[:500]
        session.flush()
        logger.error("Gmail sync failed for account %s: %s", account.id, exc)
        return {"error": str(exc)[:200], "ingested": 0, "skipped": 0}


def _ingest_raw_message(session: Session, raw) -> bool:
    """Ingest one RawMessage into the DB.

    Returns True if a new OutreachMessage was created, False if skipped.
    """
    if not raw.provider_message_id:
        return False

    # Deduplication: skip if we already have this provider message
    existing = orepo.get_message_by_provider_id(session, raw.provider_message_id)
    if existing:
        return False

    # Find the outreach lead context for this message
    lead = _find_lead(session, raw)
    if lead is None:
        return False  # no associatable lead — skip

    folder = raw.folder or ("sent" if raw.direction == "outbound" else "inbox")
    status = "sent" if raw.direction == "outbound" else "replied"

    msg = orepo.create_message(
        session,
        outreach_lead_id=lead.id,
        direction=raw.direction,
        status=status,
        to_email=raw.to_email or "",
        from_email=raw.from_email or "",
        subject=raw.subject or "",
        body=raw.body or "",
        body_html=raw.body_html or "",
        thread_id=raw.thread_id or "",
        folder=folder,
        is_read=raw.is_read,
        provider="gmail",
        provider_message_id=raw.provider_message_id,
        sent_at=raw.date,
    )
    session.flush()

    # Auto-associate with conversation engine
    from backend.outreach_service import _assign_to_conversation
    _assign_to_conversation(session, msg, lead)

    # Ingest attachment metadata (bodies downloaded lazily on demand)
    for att in raw.attachments:
        orepo.create_attachment(
            session,
            outreach_message_id=msg.id,
            filename=att.get("filename", "attachment"),
            content_type=att.get("content_type", "application/octet-stream"),
            size_bytes=att.get("size_bytes", 0),
            status="uploaded",
            content="",   # populated later via download_attachment
        )

    return True


def _find_lead(session: Session, raw):
    """Find the best OutreachLead for a synced Gmail message.

    Strategy:
    1. Existing thread_id match (reply on a known thread)
    2. Email address match against a known decision maker
    """
    # 1. Thread match
    if raw.thread_id:
        existing = session.scalar(
            select(OutreachMessage)
            .where(OutreachMessage.thread_id == raw.thread_id)
            .limit(1)
        )
        if existing and existing.outreach_lead_id:
            return orepo.get_lead(session, existing.outreach_lead_id)

    # 2. Email match against decision makers
    contact_email = raw.from_email if raw.direction == "inbound" else raw.to_email
    if contact_email:
        dm = session.scalar(
            select(DecisionMaker)
            .where(DecisionMaker.work_email == contact_email)
            .limit(1)
        )
        if dm and dm.company_domain:
            return orepo.get_lead_by_domain(session, dm.company_domain)

    return None


def sync_all_connected_accounts(session: Session) -> dict:
    """Sync all connected Gmail accounts. Used by the scheduler tick."""
    from master_db.models import EmailProviderAccount

    accounts = list(session.scalars(
        select(EmailProviderAccount)
        .where(EmailProviderAccount.provider_type == "gmail")
        .where(EmailProviderAccount.connection_status == "connected")
    ))

    total_ingested = 0
    total_errors = 0
    for account in accounts:
        result = sync_user_gmail(session, account, incremental=True)
        total_ingested += result.get("ingested", 0)
        if result.get("error"):
            total_errors += 1

    return {"accounts_synced": len(accounts), "ingested": total_ingested, "errors": total_errors}


def refresh_expiring_tokens(session: Session) -> int:
    """Proactively refresh Gmail tokens that expire within 10 minutes.

    Returns the number of tokens refreshed.
    """
    from datetime import timedelta
    from master_db.models import EmailProviderAccount
    from backend.gmail_oauth import decrypt_tokens, encrypt_tokens, refresh_access_token, token_expiry

    settings = _settings()
    now = datetime.now(timezone.utc)
    threshold = now + timedelta(minutes=10)

    accounts = list(session.scalars(
        select(EmailProviderAccount)
        .where(EmailProviderAccount.provider_type == "gmail")
        .where(EmailProviderAccount.connection_status == "connected")
    ))

    refreshed = 0
    for account in accounts:
        expiry = account.token_expires_at
        if expiry is None:
            # Try to parse from config_json
            config = decrypt_tokens(
                account.config_json or "{}",
                settings.gmail_token_encryption_key or None,
            )
            expiry = token_expiry(config)

        if expiry is None or (expiry.tzinfo and expiry <= threshold) or (not expiry.tzinfo and expiry.replace(tzinfo=timezone.utc) <= threshold):
            try:
                config = decrypt_tokens(
                    account.config_json or "{}",
                    settings.gmail_token_encryption_key or None,
                )
                new_tokens = refresh_access_token(config)
                import json
                new_config = encrypt_tokens(
                    json.dumps(new_tokens),
                    settings.gmail_token_encryption_key or None,
                )
                account.config_json = new_config
                new_expiry = token_expiry(json.dumps(new_tokens))
                account.token_expires_at = new_expiry
                account.sync_error = ""
                session.flush()
                refreshed += 1
            except Exception as exc:
                logger.warning("Failed to refresh Gmail token for account %s: %s",
                               account.id, exc)
                account.sync_status = "error"
                account.sync_error = f"Token refresh failed: {exc}"[:500]
                account.connection_status = "error"
                session.flush()

    return refreshed


def _settings():
    from backend.config import get_settings
    return get_settings()
