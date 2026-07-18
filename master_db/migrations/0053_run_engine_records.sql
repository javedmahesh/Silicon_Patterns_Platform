-- =====================================================================
-- 0053_run_engine_records.sql — per-run, per-engine record provenance
-- PostgreSQL / Supabase dialect. Requires 0043_pipeline_executions.sql.
--
-- One lightweight row per canonical record a Standard Run's engine touched, so the
-- Run Details UI can drill from "Industry — 76 processed" down to the exact 76
-- companies THIS run processed (created/updated/existing/…), never the current DB
-- contents that merely belong to Industry. It is a REFERENCE, not a copy: it stores
-- the canonical table + id (join back for display) plus a tiny `detail` json for the
-- run-specific facts a later join can't recover (e.g. a lead's score at run time).
--
-- run_id == pipeline_executions.run_id == pipeline_runs.pipeline_id, so a run's
-- provenance, its execution row, and its per-stage rows all share one id. Historical
-- runs predating this table simply have no rows here -> the UI degrades to "detailed
-- record tracking unavailable" (never fabricated from live state).
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS run_engine_records (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id        text        NOT NULL REFERENCES pipeline_executions (run_id) ON DELETE CASCADE,
    engine        text        NOT NULL,      -- pipeline stage/component (industry, blog, career, …)
    entity_table  text        NOT NULL,      -- canonical table the id lives in
    entity_id     text        NOT NULL,      -- canonical PK as text (company_domain, opportunity_id, …)
    operation     text        NOT NULL,      -- created | updated | existing | duplicate | derived | scored | rejected | skipped
    detail        jsonb       NOT NULL DEFAULT '{}'::jsonb,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_rer_run_engine ON run_engine_records (run_id, engine);
CREATE INDEX IF NOT EXISTS ix_rer_run        ON run_engine_records (run_id);

COMMIT;
