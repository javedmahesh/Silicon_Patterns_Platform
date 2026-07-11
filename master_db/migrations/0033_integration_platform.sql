-- Migration 0033: Enterprise CRM Phase 10 — Integration Platform & Developer Ecosystem
-- Tables: integrations, webhooks, webhook_deliveries, oauth_credentials, integration_events,
--         connectors, connector_runs, plugins, plugin_executions

DO $$ BEGIN

-- integrations (registry)
CREATE TABLE IF NOT EXISTS integrations (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    provider        VARCHAR(100) NOT NULL DEFAULT '',
    category        VARCHAR(20)  NOT NULL
                    CHECK (category IN ('crm','communication','analytics','productivity','finance','custom')),
    status          VARCHAR(20)  NOT NULL DEFAULT 'pending_setup'
                    CHECK (status IN ('active','inactive','error','pending_setup')),
    version         VARCHAR(30)  NOT NULL DEFAULT '1.0.0',
    configuration   JSONB        NOT NULL DEFAULT '{}',
    health_status   VARCHAR(10)  NOT NULL DEFAULT 'unknown'
                    CHECK (health_status IN ('healthy','degraded','down','unknown')),
    created_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_integrations_category ON integrations(category);
CREATE INDEX IF NOT EXISTS ix_integrations_status   ON integrations(status);

-- webhooks (outbound subscriptions)
CREATE TABLE IF NOT EXISTS webhooks (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(255)  NOT NULL,
    event_type      VARCHAR(60)   NOT NULL,
    target_url      VARCHAR(1000) NOT NULL,
    secret          VARCHAR(128)  NOT NULL DEFAULT '',
    retry_policy    JSONB         NOT NULL DEFAULT '{}',
    status          VARCHAR(10)   NOT NULL DEFAULT 'enabled'
                    CHECK (status IN ('enabled','disabled')),
    created_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_webhooks_event_type ON webhooks(event_type);
CREATE INDEX IF NOT EXISTS ix_webhooks_status     ON webhooks(status);

-- webhook_deliveries (delivery history)
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    webhook_id          BIGINT NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    event_type          VARCHAR(60) NOT NULL,
    payload             JSONB       NOT NULL DEFAULT '{}',
    status              VARCHAR(10) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','success','failed','retrying')),
    response_code       INTEGER,
    attempt_count       INTEGER     NOT NULL DEFAULT 0,
    error_detail        TEXT        NOT NULL DEFAULT '',
    last_attempted_at   TIMESTAMPTZ,
    delivered_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_webhook_deliveries_webhook ON webhook_deliveries(webhook_id);
CREATE INDEX IF NOT EXISTS ix_webhook_deliveries_status  ON webhook_deliveries(status);

-- oauth_credentials (registration only — see integration_service module docstring)
CREATE TABLE IF NOT EXISTS oauth_credentials (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                VARCHAR(255) NOT NULL,
    provider            VARCHAR(100) NOT NULL,
    client_id           VARCHAR(255) NOT NULL DEFAULT '',
    client_secret_hash  VARCHAR(128) NOT NULL,
    scopes              JSONB        NOT NULL DEFAULT '[]',
    owner_id            BIGINT REFERENCES users(id) ON DELETE SET NULL,
    status              VARCHAR(10)  NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active','revoked','expired')),
    request_count       INTEGER      NOT NULL DEFAULT 0,
    expires_at          TIMESTAMPTZ,
    last_used_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    revoked_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_oauth_credentials_owner ON oauth_credentials(owner_id);

-- integration_events (Event Bus log)
CREATE TABLE IF NOT EXISTS integration_events (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category    VARCHAR(20) NOT NULL
                CHECK (category IN ('crm','workflow','customer','revenue','ai','administration')),
    event_type  VARCHAR(60) NOT NULL,
    entity_type VARCHAR(30) NOT NULL DEFAULT '',
    entity_id   VARCHAR(64) NOT NULL DEFAULT '',
    payload     JSONB       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_integration_events_category ON integration_events(category);
CREATE INDEX IF NOT EXISTS ix_integration_events_type     ON integration_events(event_type);
CREATE INDEX IF NOT EXISTS ix_integration_events_entity   ON integration_events(entity_type, entity_id);

-- connectors
CREATE TABLE IF NOT EXISTS connectors (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    connector_type  VARCHAR(20)  NOT NULL
                    CHECK (connector_type IN ('http','rest','webhook','scheduled')),
    config          JSONB        NOT NULL DEFAULT '{}',
    schedule_cron   VARCHAR(50)  NOT NULL DEFAULT '',
    status          VARCHAR(10)  NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','inactive','error')),
    last_run_at     TIMESTAMPTZ,
    last_run_status VARCHAR(10)  NOT NULL DEFAULT '',
    created_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_connectors_type   ON connectors(connector_type);
CREATE INDEX IF NOT EXISTS ix_connectors_status ON connectors(status);

-- connector_runs
CREATE TABLE IF NOT EXISTS connector_runs (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    connector_id    BIGINT NOT NULL REFERENCES connectors(id) ON DELETE CASCADE,
    status          VARCHAR(10) NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running','success','failed')),
    duration_ms     INTEGER     NOT NULL DEFAULT 0,
    result_detail   JSONB       NOT NULL DEFAULT '{}',
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_connector_runs_connector ON connector_runs(connector_id);

-- plugins
CREATE TABLE IF NOT EXISTS plugins (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    version         VARCHAR(30)  NOT NULL DEFAULT '1.0.0',
    plugin_metadata JSONB        NOT NULL DEFAULT '{}',
    permissions     JSONB        NOT NULL DEFAULT '[]',
    execution_hooks JSONB        NOT NULL DEFAULT '[]',
    status          VARCHAR(10)  NOT NULL DEFAULT 'enabled'
                    CHECK (status IN ('enabled','disabled')),
    created_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (name, version)
);

CREATE INDEX IF NOT EXISTS ix_plugins_status ON plugins(status);

-- plugin_executions
CREATE TABLE IF NOT EXISTS plugin_executions (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plugin_id   BIGINT NOT NULL REFERENCES plugins(id) ON DELETE CASCADE,
    hook_name   VARCHAR(30) NOT NULL,
    status      VARCHAR(10) NOT NULL DEFAULT 'success'
                CHECK (status IN ('success','failed','skipped')),
    detail      JSONB       NOT NULL DEFAULT '{}',
    executed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_plugin_executions_plugin ON plugin_executions(plugin_id);
CREATE INDEX IF NOT EXISTS ix_plugin_executions_hook   ON plugin_executions(hook_name);

END $$;
