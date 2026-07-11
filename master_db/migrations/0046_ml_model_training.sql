-- =====================================================================
-- 0046_ml_model_training.sql — Recommendation model training & evaluation
-- PostgreSQL / Supabase dialect. Requires 0045_ml_foundation.
--
-- Extends the model registry with a stored artifact + feature importance +
-- promotion timestamp, and adds:
--   * ml_model_events   — promote / reject / rollback audit trail,
--   * ml_recommendations — offline inference probabilities stored ALONGSIDE the
--                          existing lead score (lead_scores is never modified).
-- No feature-generation, lead-scoring, or scheduler object is touched.
-- =====================================================================

BEGIN;

ALTER TABLE ml_models ADD COLUMN IF NOT EXISTS artifact           text  NOT NULL DEFAULT '';
ALTER TABLE ml_models ADD COLUMN IF NOT EXISTS feature_importance jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE ml_models ADD COLUMN IF NOT EXISTS promoted_at        timestamptz;

CREATE TABLE IF NOT EXISTS ml_model_events (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    model_id      bigint REFERENCES ml_models(id) ON DELETE SET NULL,
    model_version varchar(40) NOT NULL DEFAULT '',
    action        varchar(20) NOT NULL,
    detail        text        NOT NULL DEFAULT '',
    metrics       jsonb       NOT NULL DEFAULT '{}'::jsonb,
    actor_email   varchar(320) NOT NULL DEFAULT '',
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ml_model_events_model ON ml_model_events (model_id);

CREATE TABLE IF NOT EXISTS ml_recommendations (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    model_id       bigint REFERENCES ml_models(id) ON DELETE SET NULL,
    model_version  varchar(40)  NOT NULL DEFAULT '',
    entity_type    varchar(20)  NOT NULL DEFAULT 'company',
    entity_id      varchar(255) NOT NULL,
    company_domain varchar(255) NOT NULL DEFAULT '',
    probability    double precision NOT NULL DEFAULT 0.0,
    created_at     timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT uq_ml_recommendation UNIQUE (model_version, entity_type, entity_id)
);
CREATE INDEX IF NOT EXISTS ix_ml_recommendations_domain ON ml_recommendations (company_domain);
CREATE INDEX IF NOT EXISTS ix_ml_recommendations_model  ON ml_recommendations (model_version);

COMMIT;
