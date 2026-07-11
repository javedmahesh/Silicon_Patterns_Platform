-- =====================================================================
-- 0004_pipeline_runs.sql  —  Orchestrator run tracking (P5)
-- PostgreSQL / Supabase dialect. Requires 0001_foundations.sql.
--
-- One row per orchestrated stage execution (industry/blog/career/linkedin/
-- scoring). Higher level than ingestion_runs: a stage may run the upstream
-- engine AND ingest its output. pipeline_id groups the stages of one `run all`.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pipeline_id       text        NOT NULL DEFAULT '',   -- groups one `run all`
    component         text        NOT NULL,              -- industry|blog|career|linkedin|scoring
    mode              text        NOT NULL DEFAULT 'ingest',   -- ingest|full|scoring
    trigger           text        NOT NULL DEFAULT 'manual',   -- manual|daily|weekly
    started_at        timestamptz NOT NULL DEFAULT now(),
    finished_at       timestamptz,
    duration_ms       integer     NOT NULL DEFAULT 0,
    status            text        NOT NULL DEFAULT 'running',
    records_processed integer     NOT NULL DEFAULT 0,
    records_created   integer     NOT NULL DEFAULT 0,
    records_updated   integer     NOT NULL DEFAULT 0,
    records_review    integer     NOT NULL DEFAULT 0,
    error_count       integer     NOT NULL DEFAULT 0,
    errors            text        NOT NULL DEFAULT '',   -- JSON array of error strings
    notes             text        NOT NULL DEFAULT '',
    CONSTRAINT ck_pipeline_status CHECK (status IN ('running','success','failed','partial','skipped'))
);
CREATE INDEX IF NOT EXISTS ix_pipeline_component ON pipeline_runs (component);
CREATE INDEX IF NOT EXISTS ix_pipeline_status    ON pipeline_runs (status);
CREATE INDEX IF NOT EXISTS ix_pipeline_started   ON pipeline_runs (started_at);
CREATE INDEX IF NOT EXISTS ix_pipeline_group     ON pipeline_runs (pipeline_id);

COMMIT;
