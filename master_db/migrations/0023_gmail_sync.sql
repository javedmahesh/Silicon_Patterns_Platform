-- 0023_gmail_sync.sql
-- Phase 4: Gmail integration — sync state on EmailProviderAccount,
-- provider_message_id on OutreachMessage for deduplication.
--
-- The EmailProviderAccount sync-state columns (email_address, oauth_state,
-- sync_cursor, sync_status, sync_error, token_expires_at) are not added here: the
-- email_provider_accounts table itself doesn't exist yet at this point in the
-- migration chain (it's created by 0037_outreach_gap_fix.sql), so ALTERing it here
-- fails with "relation does not exist" on a real Postgres replay. 0037's CREATE TABLE
-- already includes all of those columns natively (with token_expires_at correctly
-- typed TIMESTAMPTZ, not the DATETIME used in this file's original version — DATETIME
-- isn't a Postgres type), so nothing further is needed here.

-- Provider-level message ID for deduplication during Gmail sync
ALTER TABLE outreach_messages ADD COLUMN provider_message_id VARCHAR(200) DEFAULT '';
CREATE INDEX ix_outreach_msgs_prov_id ON outreach_messages(provider_message_id);
