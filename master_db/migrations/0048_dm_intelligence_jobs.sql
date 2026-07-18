-- =====================================================================
-- 0048_dm_intelligence_jobs.sql — manual Decision Maker Intelligence jobs
-- PostgreSQL / Supabase dialect. Requires 0001_foundations (companies).
--
-- Decision Maker Intelligence is never scheduled (the Apify actor has a per-lead
-- cost). It is triggered manually from the Decision Makers page for a chosen set of
-- companies, each with its OWN requested lead count. A job runs the existing Apify
-- engine per company on a background thread and records live per-company progress.
--   * dm_intelligence_jobs       — one row per manual run (job-level status/totals),
--   * dm_intelligence_job_items  — one row per company (requested count + live
--     progress: queued -> running -> completed/failed, records found, timing, error).
-- Both are additive and independent of the automatic pipeline tables.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS dm_intelligence_jobs (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    status             text        NOT NULL DEFAULT 'queued',
    requested_by_id    integer,
    requested_by_email text        NOT NULL DEFAULT '',
    total_companies    integer     NOT NULL DEFAULT 0,
    total_requested    integer     NOT NULL DEFAULT 0,
    total_found        integer     NOT NULL DEFAULT 0,
    pipeline_run_id    integer,                                  -- soft link to pipeline_runs
    error              text        NOT NULL DEFAULT '',
    created_at         timestamptz NOT NULL DEFAULT now(),
    started_at         timestamptz,
    finished_at        timestamptz,
    duration_ms        integer     NOT NULL DEFAULT 0,
    CONSTRAINT ck_dm_job_status CHECK (status IN ('queued','running','completed','partial','failed'))
);
CREATE INDEX IF NOT EXISTS ix_dm_job_status  ON dm_intelligence_jobs (status);
CREATE INDEX IF NOT EXISTS ix_dm_job_created ON dm_intelligence_jobs (created_at);

CREATE TABLE IF NOT EXISTS dm_intelligence_job_items (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id          bigint      NOT NULL REFERENCES dm_intelligence_jobs (id) ON DELETE CASCADE,
    company_domain  varchar(255) NOT NULL DEFAULT '',
    company_name    varchar(255) NOT NULL DEFAULT '',
    requested_count integer     NOT NULL DEFAULT 0,
    status          text        NOT NULL DEFAULT 'queued',
    records_found   integer     NOT NULL DEFAULT 0,
    apify_run_id    varchar(128),
    error           text        NOT NULL DEFAULT '',
    started_at      timestamptz,
    finished_at     timestamptz,
    duration_ms     integer     NOT NULL DEFAULT 0,
    CONSTRAINT ck_dm_job_item_status CHECK (status IN ('queued','running','completed','failed'))
);
CREATE INDEX IF NOT EXISTS ix_dm_job_item_job ON dm_intelligence_job_items (job_id);

COMMIT;
