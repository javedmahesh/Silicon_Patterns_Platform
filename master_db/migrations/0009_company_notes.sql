-- =====================================================================
-- 0009_company_notes.sql  —  Free-text notes on a company (CRM-lite)
-- PostgreSQL / Supabase dialect. Requires 0001_foundations.sql + 0007_users.sql.
--
-- Analyst notes that, together with assignment events and lead re-scores, feed the
-- per-company Activity timeline on the Company Profile.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS company_notes (
    id             bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_domain text        NOT NULL REFERENCES companies(company_domain) ON DELETE CASCADE,
    author_user_id bigint,
    author_email   text        NOT NULL DEFAULT '',
    body           text        NOT NULL DEFAULT '',
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_company_notes_domain ON company_notes (company_domain);

COMMIT;
