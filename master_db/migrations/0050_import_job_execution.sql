-- =====================================================================
-- 0050_import_job_execution.sql — extend import_jobs for transactional apply (Phase 4)
-- PostgreSQL / Supabase dialect. Additive; extends 0049_import_jobs.
--
-- Adds execution-tracking columns and the full serialized synchronization preview
-- (`preview`) so the commit step consumes the Phase-2/3 results WITHOUT reconciling
-- again. Adds the 'rolled_back' status for a transaction that was applied then
-- deliberately or by an error rolled back (no partial import ever persists).
-- =====================================================================

BEGIN;

ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS preview           jsonb       NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS current_stage     varchar(40) NOT NULL DEFAULT '';
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS records_processed integer     NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS total_records     integer     NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS progress_pct      integer     NOT NULL DEFAULT 0;
ALTER TABLE import_jobs ADD COLUMN IF NOT EXISTS error_message     text        NOT NULL DEFAULT '';

-- widen the status check to include 'rolled_back'
ALTER TABLE import_jobs DROP CONSTRAINT IF EXISTS ck_import_job_status;
ALTER TABLE import_jobs ADD  CONSTRAINT ck_import_job_status
    CHECK (status IN ('previewed','running','completed','partial','failed','rolled_back','cancelled'));

COMMIT;
