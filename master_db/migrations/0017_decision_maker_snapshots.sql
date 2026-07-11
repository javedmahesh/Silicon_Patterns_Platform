-- =====================================================================
-- 0017_decision_maker_snapshots.sql  —  timestamped snapshots for leadership movement detection
-- PostgreSQL / Supabase dialect. Requires 0002_engine_tables.sql (decision_makers).
--
-- As we transition from LinkedIn scraper (which provided full career history)
-- to Apify (which provides current position only), we need to track decision-maker
-- position changes over time. This table captures a snapshot of each decision-maker's
-- current title, company, and seniority at the end of each Decision Maker Intelligence
-- engine run (typically daily).
--
-- Leadership signals derivation uses snapshot comparisons to detect:
--   * promotion       — same company, title rank increases
--   * role_change     — same company, title rank same or decreases
--   * new_hire        — different company, new role
--   * departure       — person no longer in current snapshot
--
-- Apify actor-run monitoring table is created by 0038_apify_actor_runs_fix.sql, not
-- here: this migration originally created it with an invalid PK/FK (`text`, referencing
-- pipeline_runs.run_id which is `bigint`) that Postgres rejects at CREATE TABLE time,
-- aborting this entire transaction on every real Postgres run and blocking every
-- migration after it. Removed rather than patched in place, since it never successfully
-- created anything on a real database — see 0038 for the corrected, sole definition.
-- =====================================================================

BEGIN;

-- Snapshots of decision-maker positions at point-in-time
CREATE TABLE IF NOT EXISTS decision_maker_snapshots (
    snapshot_id      BIGSERIAL PRIMARY KEY,
    decision_maker_id bigint NOT NULL REFERENCES decision_makers(id) ON DELETE CASCADE,
    company_domain   text        REFERENCES companies(company_domain) ON DELETE SET NULL,
    current_title    text        NOT NULL,
    current_company  text        NOT NULL,
    seniority        text        NOT NULL DEFAULT '',
    captured_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_dm_snapshot_date
    ON decision_maker_snapshots (decision_maker_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS ix_dm_snapshot_all_date
    ON decision_maker_snapshots (captured_at DESC);

-- Add new source type to leadership_signals
ALTER TABLE leadership_signals DROP CONSTRAINT IF EXISTS ck_ldr_source;
ALTER TABLE leadership_signals ADD CONSTRAINT ck_ldr_source
    CHECK (source IN ('linkedin_history','blog_event','snapshot_comparison'));

COMMIT;
