-- =====================================================================
-- 0049_import_jobs.sql — reusable historical-import run tracking (Phase 3)
-- PostgreSQL / Supabase dialect. Additive; independent of every other table.
--
-- One row per historical-data import run (company + decision-maker synchronization
-- for one uploaded file). status='previewed' records a read-only reconciliation
-- preview (no companies/decision_makers written); the Phase-4 apply step reuses the
-- same row and counters (running -> completed/failed). `stats` holds the full preview
-- payload as jsonb for the Admin Import UI. See master_db.models.ImportJob.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS import_jobs (
    id                        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    import_id                 varchar(40)  NOT NULL UNIQUE,
    source                    varchar(60)  NOT NULL DEFAULT 'historical_excel',
    filename                  varchar(512) NOT NULL DEFAULT '',
    initiated_by              varchar(320) NOT NULL DEFAULT '',
    status                    text         NOT NULL DEFAULT 'previewed',
    companies_processed       integer      NOT NULL DEFAULT 0,
    decision_makers_processed integer      NOT NULL DEFAULT 0,
    created_count             integer      NOT NULL DEFAULT 0,
    updated_count             integer      NOT NULL DEFAULT 0,
    unchanged_count           integer      NOT NULL DEFAULT 0,
    duplicate_count           integer      NOT NULL DEFAULT 0,
    conflict_count            integer      NOT NULL DEFAULT 0,
    invalid_count             integer      NOT NULL DEFAULT 0,
    summary                   text         NOT NULL DEFAULT '',
    stats                     jsonb        NOT NULL DEFAULT '{}'::jsonb,
    started_at                timestamptz  NOT NULL DEFAULT now(),
    finished_at               timestamptz,
    duration_ms               integer      NOT NULL DEFAULT 0,
    created_at                timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT ck_import_job_status
        CHECK (status IN ('previewed','running','completed','partial','failed','cancelled'))
);
CREATE INDEX IF NOT EXISTS ix_import_jobs_status  ON import_jobs (status);
CREATE INDEX IF NOT EXISTS ix_import_jobs_created ON import_jobs (created_at);

COMMIT;
