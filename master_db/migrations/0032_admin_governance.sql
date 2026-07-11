-- Migration 0032: Enterprise CRM Phase 9 — Enterprise Administration, Security & Compliance
-- Tables: organizations, org_units, org_unit_members, system_settings, security_policies,
--         audit_events, compliance_records, api_keys

DO $$ BEGIN

-- Compliance: soft-delete flag on the generic custom-object record store (Phase 7).
ALTER TABLE custom_records ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT false;

-- organizations
CREATE TABLE IF NOT EXISTS organizations (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    industry        VARCHAR(100) NOT NULL DEFAULT '',
    size            VARCHAR(30)  NOT NULL DEFAULT '',
    settings        JSONB        NOT NULL DEFAULT '{}',
    feature_flags   JSONB        NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- org_units (business units / departments / teams — one hierarchy, type-discriminated)
CREATE TABLE IF NOT EXISTS org_units (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organization_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    unit_type       VARCHAR(20)  NOT NULL
                    CHECK (unit_type IN ('business_unit','department','team')),
    parent_id       BIGINT REFERENCES org_units(id) ON DELETE SET NULL,
    lead_user_id    BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_org_units_org    ON org_units(organization_id);
CREATE INDEX IF NOT EXISTS ix_org_units_parent ON org_units(parent_id);

-- org_unit_members
CREATE TABLE IF NOT EXISTS org_unit_members (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unit_id     BIGINT NOT NULL REFERENCES org_units(id) ON DELETE CASCADE,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        VARCHAR(10) NOT NULL DEFAULT 'member'
                CHECK (role IN ('member','lead')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (unit_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_org_unit_members_unit ON org_unit_members(unit_id);
CREATE INDEX IF NOT EXISTS ix_org_unit_members_user ON org_unit_members(user_id);

-- system_settings (generic key/value config store, one row per category+key)
CREATE TABLE IF NOT EXISTS system_settings (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category    VARCHAR(20) NOT NULL
                CHECK (category IN ('crm','workflow','ai','email','notification','retention')),
    key         VARCHAR(100) NOT NULL,
    value       JSONB       NOT NULL DEFAULT '{}',
    updated_by  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (category, key)
);

CREATE INDEX IF NOT EXISTS ix_system_settings_category ON system_settings(category);

-- security_policies (one row per policy_type)
CREATE TABLE IF NOT EXISTS security_policies (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_type VARCHAR(20) NOT NULL UNIQUE
                CHECK (policy_type IN (
                    'password','session','login_restriction','ip_allowlist','account_lockout','mfa'
                )),
    config      JSONB       NOT NULL DEFAULT '{}',
    is_enabled  BOOLEAN     NOT NULL DEFAULT true,
    updated_by  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- audit_events (immutable, insert-only; cross-cutting audit trail)
CREATE TABLE IF NOT EXISTS audit_events (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category    VARCHAR(30) NOT NULL
                CHECK (category IN (
                    'authentication','user_administration','permission_change','record_crud',
                    'workflow_change','configuration_change','ai_action','data_export'
                )),
    action      VARCHAR(50) NOT NULL,
    actor_id    BIGINT REFERENCES users(id) ON DELETE SET NULL,
    actor_email VARCHAR(320) NOT NULL DEFAULT '',
    entity_type VARCHAR(30) NOT NULL DEFAULT '',
    entity_id   VARCHAR(64) NOT NULL DEFAULT '',
    detail      JSONB       NOT NULL DEFAULT '{}',
    ip_address  VARCHAR(64) NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_audit_events_category ON audit_events(category);
CREATE INDEX IF NOT EXISTS ix_audit_events_actor     ON audit_events(actor_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_entity     ON audit_events(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_created    ON audit_events(created_at);

-- compliance_records (legal hold / consent / export & deletion requests)
CREATE TABLE IF NOT EXISTS compliance_records (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    record_type     VARCHAR(30) NOT NULL
                    CHECK (record_type IN ('legal_hold','consent','data_export_request','data_deletion_request')),
    entity_type     VARCHAR(30) NOT NULL DEFAULT '',
    entity_id       VARCHAR(64) NOT NULL DEFAULT '',
    status          VARCHAR(10) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','active','completed','rejected')),
    requested_by    BIGINT REFERENCES users(id) ON DELETE SET NULL,
    detail          JSONB       NOT NULL DEFAULT '{}',
    requested_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_compliance_type   ON compliance_records(record_type);
CREATE INDEX IF NOT EXISTS ix_compliance_status ON compliance_records(status);
CREATE INDEX IF NOT EXISTS ix_compliance_entity  ON compliance_records(entity_type, entity_id);

-- api_keys
CREATE TABLE IF NOT EXISTS api_keys (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    key_hash        VARCHAR(128) NOT NULL UNIQUE,
    key_prefix      VARCHAR(20)  NOT NULL DEFAULT '',
    scopes          JSONB        NOT NULL DEFAULT '[]',
    owner_id        BIGINT REFERENCES users(id) ON DELETE SET NULL,
    status          VARCHAR(10)  NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','revoked','expired')),
    request_count   INTEGER      NOT NULL DEFAULT 0,
    expires_at      TIMESTAMPTZ,
    last_used_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    revoked_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_api_keys_owner  ON api_keys(owner_id);
CREATE INDEX IF NOT EXISTS ix_api_keys_status ON api_keys(status);

END $$;
