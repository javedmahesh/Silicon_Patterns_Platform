-- =====================================================================
-- 0003_platform_tables.sql  —  Platform-owned tables
-- PostgreSQL / Supabase dialect. Requires 0001_foundations.sql.
--
-- Produced by the NEW services, never by the four engines:
--   * lead_scores     — output of the Lead Scoring service (P3)
--   * ingestion_runs  — audit / incremental bookkeeping for the orchestrator (P5)
-- Defined now so the foundation schema is complete for review; the services
-- that populate them are built in later phases.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- lead_scores  [owner: Lead Scoring service]   one row per company (1:1)
-- Stores the final score, grade, and every component subscore + multiplier so a
-- grade is fully explainable in the UI. grade is A+/A/B/C.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lead_scores (
    company_domain       text PRIMARY KEY REFERENCES companies(company_domain) ON DELETE CASCADE,
    lead_score           double precision NOT NULL DEFAULT 0,
    grade                text             NOT NULL DEFAULT 'C',
    priority_rank        integer          NOT NULL DEFAULT 0,
    opportunity_subscore double precision NOT NULL DEFAULT 0,
    demand_subscore      double precision NOT NULL DEFAULT 0,
    readiness_subscore   double precision NOT NULL DEFAULT 0,
    dm_subscore          double precision NOT NULL DEFAULT 0,
    region_mult          double precision NOT NULL DEFAULT 1.0,
    prospect_mult        double precision NOT NULL DEFAULT 1.0,
    tier_mult            double precision NOT NULL DEFAULT 1.0,
    rationale            jsonb            NOT NULL DEFAULT '{}'::jsonb,
    model_version        text             NOT NULL DEFAULT '',
    scored_at            timestamptz      NOT NULL DEFAULT now(),
    CONSTRAINT ck_lead_grade CHECK (grade IN ('A+','A','B','C'))
);
CREATE INDEX IF NOT EXISTS ix_lead_scores_grade    ON lead_scores (grade);
CREATE INDEX IF NOT EXISTS ix_lead_scores_score    ON lead_scores (lead_score);
CREATE INDEX IF NOT EXISTS ix_lead_scores_priority ON lead_scores (priority_rank);

-- ---------------------------------------------------------------------
-- ingestion_runs  [owner: Orchestrator]   one row per engine/ingestion run
-- Powers incremental updates ("what changed since last run") and an audit trail.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    engine             text        NOT NULL,
    mode               text        NOT NULL DEFAULT 'standalone',  -- standalone | pipeline
    started_at         timestamptz NOT NULL DEFAULT now(),
    finished_at        timestamptz,
    status             text        NOT NULL DEFAULT 'running',
    rows_in            integer     NOT NULL DEFAULT 0,
    rows_upserted      integer     NOT NULL DEFAULT 0,
    rows_rejected      integer     NOT NULL DEFAULT 0,
    rows_review_queued integer     NOT NULL DEFAULT 0,
    source_path        text        NOT NULL DEFAULT '',
    notes              text        NOT NULL DEFAULT '',
    CONSTRAINT ck_ingestion_status CHECK (status IN ('running','success','failed','partial'))
);
CREATE INDEX IF NOT EXISTS ix_ingestion_engine  ON ingestion_runs (engine);
CREATE INDEX IF NOT EXISTS ix_ingestion_status  ON ingestion_runs (status);
CREATE INDEX IF NOT EXISTS ix_ingestion_started ON ingestion_runs (started_at);

COMMIT;
