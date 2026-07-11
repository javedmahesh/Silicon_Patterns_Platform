-- Migration 0035: Enterprise CRM Phase 12 — Data Warehouse & Advanced Business Intelligence
-- Tables: warehouse_snapshots, kpis, kpi_values, custom_reports, report_schedules,
--         scheduled_report_runs

DO $$ BEGIN

-- warehouse_snapshots (historical point-in-time metric aggregates)
CREATE TABLE IF NOT EXISTS warehouse_snapshots (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    metric_type     VARCHAR(20) NOT NULL
                    CHECK (metric_type IN ('revenue','deals','customers','campaigns','activities','ai_metrics','workflow_metrics')),
    snapshot_date   TIMESTAMPTZ NOT NULL,
    metrics         JSONB       NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_warehouse_snapshots_type ON warehouse_snapshots(metric_type);
CREATE INDEX IF NOT EXISTS ix_warehouse_snapshots_date ON warehouse_snapshots(snapshot_date);

-- kpis
CREATE TABLE IF NOT EXISTS kpis (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(255) NOT NULL UNIQUE,
    category        VARCHAR(20)  NOT NULL
                    CHECK (category IN ('revenue','sales','customer','campaign','workflow','ai')),
    target_value    DOUBLE PRECISION,
    unit            VARCHAR(20)  NOT NULL DEFAULT '',
    created_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_kpis_category ON kpis(category);

-- kpi_values
CREATE TABLE IF NOT EXISTS kpi_values (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kpi_id      BIGINT NOT NULL REFERENCES kpis(id) ON DELETE CASCADE,
    value       DOUBLE PRECISION NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_kpi_values_kpi      ON kpi_values(kpi_id);
CREATE INDEX IF NOT EXISTS ix_kpi_values_recorded ON kpi_values(recorded_at);

-- custom_reports
CREATE TABLE IF NOT EXISTS custom_reports (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    entity_type VARCHAR(30)  NOT NULL,
    filters     JSONB        NOT NULL DEFAULT '{}',
    group_by    VARCHAR(60)  NOT NULL DEFAULT '',
    status      VARCHAR(10)  NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft','active','archived')),
    owner_id    BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_custom_reports_owner  ON custom_reports(owner_id);
CREATE INDEX IF NOT EXISTS ix_custom_reports_status ON custom_reports(status);

-- report_schedules
CREATE TABLE IF NOT EXISTS report_schedules (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_id           BIGINT NOT NULL REFERENCES custom_reports(id) ON DELETE CASCADE,
    frequency           VARCHAR(10) NOT NULL
                        CHECK (frequency IN ('daily','weekly','monthly','quarterly')),
    recipient_emails    JSONB       NOT NULL DEFAULT '[]',
    is_enabled          BOOLEAN     NOT NULL DEFAULT true,
    last_run_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_report_schedules_report ON report_schedules(report_id);

-- scheduled_report_runs
CREATE TABLE IF NOT EXISTS scheduled_report_runs (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    schedule_id BIGINT NOT NULL REFERENCES report_schedules(id) ON DELETE CASCADE,
    status      VARCHAR(10) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','sent','failed')),
    row_count   INTEGER     NOT NULL DEFAULT 0,
    detail      TEXT        NOT NULL DEFAULT '',
    run_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_scheduled_report_runs_schedule ON scheduled_report_runs(schedule_id);

END $$;
