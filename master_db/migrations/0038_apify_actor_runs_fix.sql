-- Migration 0038: create apify_actor_runs correctly — found by
-- scripts/check_migration_model_parity.py.
--
-- 0017_decision_maker_snapshots.sql originally defined apify_actor_runs with `run_id
-- text PRIMARY KEY` and `pipeline_run_id text REFERENCES pipeline_runs(run_id)`.
-- pipeline_runs.run_id is (and always has been, per 0004_pipeline_runs.sql) `bigint
-- GENERATED ALWAYS AS IDENTITY` — a text column cannot reference a bigint column
-- (Postgres rejects the FK constraint outright at CREATE TABLE time: "incompatible
-- types: text and bigint"). That failure aborted 0017's entire transaction on every real
-- Postgres run (confirmed against a live Supabase database) and blocked every migration
-- after it from ever being reached — SQLite silently tolerated it (no type enforcement
-- on FK columns), which is exactly why this went uncaught for so long.
-- master_db.models.ApifyActorRun has always used `run_id: int` (autoincrement identity)
-- — the ORM was correct; only the SQL was wrong. It was also missing
-- apify_run_id/batch_index/company_count entirely.
--
-- Fixed at the source: 0017 no longer creates this table at all (see the note in that
-- file). This migration is now the sole, purely additive definition — CREATE TABLE IF
-- NOT EXISTS, no DROP needed, since the broken statement in 0017 could never have
-- succeeded against Postgres and so there is no pre-existing table on any real
-- deployment to drop.

DO $$ BEGIN

CREATE TABLE IF NOT EXISTS apify_actor_runs (
    run_id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id            VARCHAR(32)  NOT NULL,
    apify_run_id        VARCHAR(128),
    pipeline_run_id     BIGINT REFERENCES pipeline_runs(run_id) ON DELETE SET NULL,
    batch_index         INTEGER      NOT NULL DEFAULT 0,
    company_count       INTEGER      NOT NULL DEFAULT 0,
    status              VARCHAR(32)  NOT NULL DEFAULT 'unknown',
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ,
    records_returned    INTEGER      NOT NULL DEFAULT 0,
    error_message       TEXT
);

CREATE INDEX IF NOT EXISTS ix_apify_run_pipeline_id ON apify_actor_runs(pipeline_run_id);
CREATE INDEX IF NOT EXISTS ix_apify_run_started     ON apify_actor_runs(started_at);

END $$;
