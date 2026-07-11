-- =====================================================================
-- 0045_ml_foundation.sql — Machine Learning Foundation (infrastructure only)
-- PostgreSQL / Supabase dialect.
--
-- Prepares the platform for a future recommendation model. NO classifier is
-- trained here — these tables only capture, cache, and version the inputs:
--   * ml_feature_rows   — feature-store cache (one vector per entity+version,
--                         source_hash enables incremental skip-if-unchanged),
--   * role_embeddings   — cached role/title embeddings (skip re-embedding),
--   * user_interactions — feedback dataset (thumbs/export/contact/ignore) stored
--                         SEPARATELY from opportunities, with sample_weight,
--   * ml_feature_versions / ml_models / ml_training_runs — versioning + metadata
--                         registries (feature / model / training).
-- None of this is wired into the Standard Run or scheduler.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS ml_feature_rows (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type     varchar(20)  NOT NULL DEFAULT 'company',
    entity_id       varchar(255) NOT NULL,
    feature_version varchar(40)  NOT NULL DEFAULT 'fs-1',
    features        jsonb        NOT NULL DEFAULT '{}'::jsonb,
    source_hash     varchar(64)  NOT NULL DEFAULT '',
    computed_at     timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT uq_ml_feature_row UNIQUE (entity_type, entity_id, feature_version),
    CONSTRAINT ck_ml_feature_entity CHECK (entity_type IN ('opportunity','company','lead','decision_maker'))
);
CREATE INDEX IF NOT EXISTS ix_ml_feature_rows_version ON ml_feature_rows (feature_version);

CREATE TABLE IF NOT EXISTS role_embeddings (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title_hash  varchar(64)  NOT NULL,
    title_norm  varchar(512) NOT NULL DEFAULT '',
    model_name  varchar(80)  NOT NULL DEFAULT '',
    dim         integer      NOT NULL DEFAULT 0,
    vector      jsonb        NOT NULL DEFAULT '[]'::jsonb,
    created_at  timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT uq_role_embedding UNIQUE (title_hash, model_name)
);
CREATE INDEX IF NOT EXISTS ix_role_embeddings_hash ON role_embeddings (title_hash);

CREATE TABLE IF NOT EXISTS user_interactions (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id          bigint REFERENCES users(id) ON DELETE SET NULL,
    user_email       varchar(320) NOT NULL DEFAULT '',
    interaction_type varchar(20)  NOT NULL,
    entity_type      varchar(20)  NOT NULL DEFAULT 'opportunity',
    entity_id        varchar(255) NOT NULL,
    company_domain   varchar(255) NOT NULL DEFAULT '',
    sample_weight    double precision NOT NULL DEFAULT 1.0,
    context          jsonb        NOT NULL DEFAULT '{}'::jsonb,
    created_at       timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT ck_ml_interaction_type CHECK (interaction_type IN
        ('thumbs_up','thumbs_down','export','contact','ignore')),
    CONSTRAINT ck_ml_interaction_entity CHECK (entity_type IN
        ('opportunity','company','lead','decision_maker'))
);
CREATE INDEX IF NOT EXISTS ix_user_interactions_entity  ON user_interactions (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_user_interactions_created ON user_interactions (created_at);

CREATE TABLE IF NOT EXISTS ml_feature_versions (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version       varchar(40) NOT NULL UNIQUE,
    spec          jsonb       NOT NULL DEFAULT '{}'::jsonb,
    feature_count integer     NOT NULL DEFAULT 0,
    notes         text        NOT NULL DEFAULT '',
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ml_models (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            varchar(80)  NOT NULL DEFAULT 'lead_recommender',
    version         varchar(40)  NOT NULL,
    status          varchar(20)  NOT NULL DEFAULT 'draft',
    model_type      varchar(60)  NOT NULL DEFAULT '',
    feature_version varchar(40)  NOT NULL DEFAULT '',
    artifact_path   varchar(512) NOT NULL DEFAULT '',
    metrics         jsonb        NOT NULL DEFAULT '{}'::jsonb,
    model_metadata  jsonb        NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT uq_ml_model_version UNIQUE (name, version),
    CONSTRAINT ck_ml_model_status CHECK (status IN ('draft','training','active','archived','failed'))
);
CREATE INDEX IF NOT EXISTS ix_ml_models_status ON ml_models (status);

CREATE TABLE IF NOT EXISTS ml_training_runs (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    model_id        bigint REFERENCES ml_models(id) ON DELETE SET NULL,
    dataset_version varchar(60) NOT NULL DEFAULT '',
    feature_version varchar(40) NOT NULL DEFAULT '',
    window_days     integer     NOT NULL DEFAULT 0,
    row_count       integer     NOT NULL DEFAULT 0,
    positive_count  integer     NOT NULL DEFAULT 0,
    negative_count  integer     NOT NULL DEFAULT 0,
    status          varchar(20) NOT NULL DEFAULT 'dataset_built',
    params          jsonb       NOT NULL DEFAULT '{}'::jsonb,
    metrics         jsonb       NOT NULL DEFAULT '{}'::jsonb,
    notes           text        NOT NULL DEFAULT '',
    created_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz
);
CREATE INDEX IF NOT EXISTS ix_ml_training_runs_created ON ml_training_runs (created_at);

COMMIT;
