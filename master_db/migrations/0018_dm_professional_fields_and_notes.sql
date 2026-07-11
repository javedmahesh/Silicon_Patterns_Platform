-- =====================================================================
-- 0018_dm_professional_fields_and_notes.sql
--   (1) Structured professional fields on decision_makers (from Apify)
--   (2) decision_maker_notes — two-tier collaboration notes (team / personal)
-- PostgreSQL / Supabase dialect. Requires 0002 (decision_makers) + 0007 (users).
--
-- (1) The Decision Maker Intelligence (Apify) engine returns far more professional
--     contact metadata than we previously stored. We now persist each field in its
--     own column so the UI can display it without re-ingesting, while profile_data
--     keeps the full raw actor response. Columns are NULLABLE: a field the actor did
--     not return stays NULL rather than carrying a placeholder.
--
-- (2) Notes become a shared collaboration feature instead of a single text blob:
--       personal — private to the author (any user); author-only edit/delete.
--       team     — company-wide guidance (admin/manager only); visible to everyone.
--     The legacy decision_maker_contacts.notes column is retained for back-compat
--     but is no longer surfaced in the UI.
-- =====================================================================

BEGIN;

-- (1) Structured professional fields sourced from the engine -----------------
ALTER TABLE decision_makers ADD COLUMN IF NOT EXISTS full_name             text;
ALTER TABLE decision_makers ADD COLUMN IF NOT EXISTS work_email            text;
ALTER TABLE decision_makers ADD COLUMN IF NOT EXISTS email_status          text;
ALTER TABLE decision_makers ADD COLUMN IF NOT EXISTS work_phone            text;
ALTER TABLE decision_makers ADD COLUMN IF NOT EXISTS city                  text;
ALTER TABLE decision_makers ADD COLUMN IF NOT EXISTS state_region          text;
ALTER TABLE decision_makers ADD COLUMN IF NOT EXISTS country               text;
ALTER TABLE decision_makers ADD COLUMN IF NOT EXISTS organization_website  text;
ALTER TABLE decision_makers ADD COLUMN IF NOT EXISTS organization_linkedin text;

-- (2) Two-tier collaboration notes ------------------------------------------
CREATE TABLE IF NOT EXISTS decision_maker_notes (
    id                bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    decision_maker_id bigint      NOT NULL
                      REFERENCES decision_makers(id) ON DELETE CASCADE,
    note_type         text        NOT NULL DEFAULT 'personal',
    created_by        bigint      REFERENCES users(id) ON DELETE SET NULL,
    author_email      text        NOT NULL DEFAULT '',
    content           text        NOT NULL DEFAULT '',
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_dm_note_type CHECK (note_type IN ('team','personal'))
);

CREATE INDEX IF NOT EXISTS ix_dm_notes_dm     ON decision_maker_notes (decision_maker_id);
CREATE INDEX IF NOT EXISTS ix_dm_notes_author ON decision_maker_notes (created_by);

COMMIT;
