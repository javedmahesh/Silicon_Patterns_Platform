-- =====================================================================
-- 0010_dm_contacts.sql  —  Professional contact details for decision makers
-- PostgreSQL / Supabase dialect. Requires 0002 (decision_makers) + 0007 (users).
--
-- Analyst-entered PROFESSIONAL contact info for senior decision makers — work
-- email / work phone only. NEVER personal home address / personal email /
-- personal phone (privacy + compliance). One row per decision maker.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS decision_maker_contacts (
    id                bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    decision_maker_id bigint      NOT NULL UNIQUE
                      REFERENCES decision_makers(id) ON DELETE CASCADE,
    work_email        text        NOT NULL DEFAULT '',
    work_phone        text        NOT NULL DEFAULT '',
    notes             text        NOT NULL DEFAULT '',
    added_by          bigint,                              -- users.id who recorded it
    added_by_email    text        NOT NULL DEFAULT '',
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

COMMIT;
