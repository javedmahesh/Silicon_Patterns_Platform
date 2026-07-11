-- =====================================================================
-- 0043_pipeline_executions.sql — Standard Run history (scheduler)
-- PostgreSQL / Supabase dialect. Requires 0004_pipeline_runs.sql.
--
-- One row per Standard Run (a full `run all`), fired by the scheduler
-- (trigger='scheduled') or manually (trigger='manual'). Run-level companion to
-- pipeline_runs (one row PER STAGE): run_id here == pipeline_runs.pipeline_id, so
-- the stage rows join back to their execution. Per-engine stats + platform totals
-- are snapshotted as jsonb, and the Outlook-notification outcome is recorded (it
-- never blocks the pipeline).
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS pipeline_executions (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id              text        NOT NULL UNIQUE,             -- == pipeline_runs.pipeline_id
    trigger             text        NOT NULL DEFAULT 'manual',   -- manual | scheduled
    scheduled_slot      text,                                    -- e.g. '09:00' (scheduled runs)
    started_at          timestamptz NOT NULL DEFAULT now(),
    finished_at         timestamptz,
    duration_ms         integer     NOT NULL DEFAULT 0,
    status              text        NOT NULL DEFAULT 'running',
    records_processed   integer     NOT NULL DEFAULT 0,
    failure_count       integer     NOT NULL DEFAULT 0,
    warning_count       integer     NOT NULL DEFAULT 0,
    stages              jsonb       NOT NULL DEFAULT '[]'::jsonb,   -- per-engine stats
    totals              jsonb       NOT NULL DEFAULT '{}'::jsonb,   -- platform totals snapshot
    notification_status text        NOT NULL DEFAULT 'pending',
    notification_detail text        NOT NULL DEFAULT '',
    notified_count      integer     NOT NULL DEFAULT 0,
    created_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_pexec_trigger CHECK (trigger IN ('manual','scheduled')),
    CONSTRAINT ck_pexec_status  CHECK (status IN ('running','success','partial','failed','skipped'))
);
CREATE INDEX IF NOT EXISTS ix_pexec_started ON pipeline_executions (started_at);
CREATE INDEX IF NOT EXISTS ix_pexec_status  ON pipeline_executions (status);

COMMIT;
