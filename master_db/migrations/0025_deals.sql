-- 0025_deals.sql  Enterprise CRM Phase 2: Pipeline & Deal Management
-- Mirrors master_db/models.py CrmPipeline / CrmPipelineStage / CrmDeal / CrmDealStageHistory.

-- -----------------------------------------------------------------------
-- crm_pipelines
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_pipelines (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    description TEXT         NOT NULL DEFAULT '',
    is_default  BOOLEAN      NOT NULL DEFAULT FALSE,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='crm_pipelines' AND indexname='ix_crm_pipelines_active') THEN
        CREATE INDEX ix_crm_pipelines_active ON crm_pipelines(is_active);
    END IF;
END $$;

-- -----------------------------------------------------------------------
-- crm_pipeline_stages
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_pipeline_stages (
    id          SERIAL PRIMARY KEY,
    pipeline_id INTEGER      NOT NULL REFERENCES crm_pipelines(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    stage_type  VARCHAR(20)  NOT NULL DEFAULT 'open'
                    CHECK (stage_type IN ('open','won','lost')),
    stage_order INTEGER      NOT NULL,
    probability INTEGER      NOT NULL DEFAULT 0
                    CHECK (probability >= 0 AND probability <= 100),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (pipeline_id, stage_order)
);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='crm_pipeline_stages' AND indexname='ix_crm_stages_pipeline') THEN
        CREATE INDEX ix_crm_stages_pipeline ON crm_pipeline_stages(pipeline_id);
    END IF;
END $$;

-- -----------------------------------------------------------------------
-- crm_deals
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_deals (
    id                   SERIAL PRIMARY KEY,
    title                VARCHAR(255) NOT NULL,
    company_domain       VARCHAR(255) NOT NULL REFERENCES companies(company_domain) ON DELETE CASCADE,
    opportunity_id       VARCHAR(64)  REFERENCES opportunities(opportunity_id) ON DELETE SET NULL,
    pipeline_id          INTEGER      NOT NULL REFERENCES crm_pipelines(id) ON DELETE CASCADE,
    stage_id             INTEGER      NOT NULL REFERENCES crm_pipeline_stages(id) ON DELETE RESTRICT,
    owner_id             INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    created_by           INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    value                DOUBLE PRECISION,
    currency             VARCHAR(3)   NOT NULL DEFAULT 'USD'
                             CHECK (currency IN ('USD','EUR','GBP','INR','JPY','CAD','AUD','SGD')),
    probability          INTEGER      NOT NULL DEFAULT 0
                             CHECK (probability >= 0 AND probability <= 100),
    forecast_category    VARCHAR(20)  NOT NULL DEFAULT 'pipeline'
                             CHECK (forecast_category IN ('pipeline','best_case','commit','won','omitted')),
    expected_close_date  TIMESTAMPTZ,
    last_activity_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    tags                 JSONB        NOT NULL DEFAULT '[]',
    notes                TEXT         NOT NULL DEFAULT '',
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='crm_deals' AND indexname='ix_crm_deals_company') THEN
        CREATE INDEX ix_crm_deals_company  ON crm_deals(company_domain);
        CREATE INDEX ix_crm_deals_stage    ON crm_deals(stage_id);
        CREATE INDEX ix_crm_deals_owner    ON crm_deals(owner_id);
        CREATE INDEX ix_crm_deals_pipeline ON crm_deals(pipeline_id);
    END IF;
END $$;

CREATE OR REPLACE FUNCTION trg_crm_deals_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_crm_deals_updated_at') THEN
        CREATE TRIGGER trg_crm_deals_updated_at
            BEFORE UPDATE ON crm_deals
            FOR EACH ROW EXECUTE FUNCTION trg_crm_deals_updated_at();
    END IF;
END $$;

-- -----------------------------------------------------------------------
-- crm_deal_stage_history
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_deal_stage_history (
    id                    SERIAL PRIMARY KEY,
    deal_id               INTEGER     NOT NULL REFERENCES crm_deals(id) ON DELETE CASCADE,
    from_stage_id         INTEGER     REFERENCES crm_pipeline_stages(id) ON DELETE SET NULL,
    to_stage_id           INTEGER     NOT NULL REFERENCES crm_pipeline_stages(id) ON DELETE CASCADE,
    entered_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exited_at             TIMESTAMPTZ,
    time_in_stage_seconds INTEGER,
    changed_by            INTEGER     REFERENCES users(id) ON DELETE SET NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='crm_deal_stage_history' AND indexname='ix_deal_history_deal') THEN
        CREATE INDEX ix_deal_history_deal  ON crm_deal_stage_history(deal_id);
        CREATE INDEX ix_deal_history_stage ON crm_deal_stage_history(to_stage_id);
    END IF;
END $$;
