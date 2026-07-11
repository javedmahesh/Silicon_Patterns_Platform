-- =====================================================================
-- 0005_review_actions.sql  —  Review-queue audit trail (P5.5)
-- PostgreSQL / Supabase dialect. Requires 0001_foundations.sql.
--
-- One row per resolution action taken on the review queue
-- (approve / merge / reject / create_alias) — who did what, when, and the
-- domain movement involved.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS review_actions (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    review_id   bigint,                                  -- resolution_review_queue.id acted on
    action      text        NOT NULL,                    -- approve | merge | reject | create_alias
    actor       text        NOT NULL DEFAULT 'api',
    from_domain text        NOT NULL DEFAULT '',
    to_domain   text        NOT NULL DEFAULT '',
    detail      text        NOT NULL DEFAULT '',
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_review_actions_review ON review_actions (review_id);

-- Also backfill the indexes §4 of the hardening review flagged as missing on the
-- review queue itself (the company-profile review lookup + idempotency guard).
CREATE INDEX IF NOT EXISTS ix_review_suggested_domain ON resolution_review_queue (suggested_domain);
CREATE INDEX IF NOT EXISTS ix_review_resolved_domain  ON resolution_review_queue (resolved_domain);
CREATE INDEX IF NOT EXISTS ix_review_source_ref       ON resolution_review_queue (source_engine, source_record_ref, status);
-- Fast case-insensitive substring search on company names (the /companies ?q= path).
CREATE INDEX IF NOT EXISTS ix_companies_name_trgm ON companies USING gin (company_name gin_trgm_ops);
-- Indexed sort target for /decision-makers.
CREATE INDEX IF NOT EXISTS ix_dm_match_score ON decision_makers (match_score);

COMMIT;
