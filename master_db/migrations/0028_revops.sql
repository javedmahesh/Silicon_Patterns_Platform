-- Migration 0028: Enterprise CRM Phase 5 — Revenue Operations, Forecasting & Executive Analytics
-- Adds: crm_deals.lost_reason / won_reason; tables: revenue_targets, forecast_snapshots

DO $$ BEGIN

ALTER TABLE crm_deals ADD COLUMN IF NOT EXISTS lost_reason VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE crm_deals ADD COLUMN IF NOT EXISTS won_reason  VARCHAR(255) NOT NULL DEFAULT '';

-- revenue_targets
CREATE TABLE IF NOT EXISTS revenue_targets (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scope           VARCHAR(20) NOT NULL DEFAULT 'company'
                    CHECK (scope IN ('company','team','individual')),
    owner_id        BIGINT REFERENCES users(id) ON DELETE SET NULL,
    pipeline_id     BIGINT REFERENCES crm_pipelines(id) ON DELETE CASCADE,
    period_type     VARCHAR(20) NOT NULL DEFAULT 'monthly'
                    CHECK (period_type IN ('monthly','quarterly','annual')),
    period_start    TIMESTAMPTZ NOT NULL,
    period_end      TIMESTAMPTZ NOT NULL,
    target_amount   DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency        VARCHAR(3)  NOT NULL DEFAULT 'USD',
    notes           TEXT        NOT NULL DEFAULT '',
    created_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_revenue_targets_owner    ON revenue_targets(owner_id);
CREATE INDEX IF NOT EXISTS ix_revenue_targets_pipeline ON revenue_targets(pipeline_id);
CREATE INDEX IF NOT EXISTS ix_revenue_targets_period   ON revenue_targets(period_type, period_start);

-- forecast_snapshots
CREATE TABLE IF NOT EXISTS forecast_snapshots (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pipeline_id         BIGINT REFERENCES crm_pipelines(id) ON DELETE CASCADE,
    period_type         VARCHAR(20) NOT NULL DEFAULT 'monthly'
                        CHECK (period_type IN ('monthly','quarterly','annual')),
    period_key          VARCHAR(20) NOT NULL,
    category            VARCHAR(20) NOT NULL DEFAULT 'pipeline'
                        CHECK (category IN ('pipeline','weighted','best_case','commit')),
    forecasted_amount   DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_by          BIGINT REFERENCES users(id) ON DELETE SET NULL,
    snapshot_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_forecast_snapshots_pipeline ON forecast_snapshots(pipeline_id);
CREATE INDEX IF NOT EXISTS ix_forecast_snapshots_period   ON forecast_snapshots(period_type, period_key);

END $$;
