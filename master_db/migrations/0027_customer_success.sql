-- Migration 0027: Enterprise CRM Phase 4 — Customer Success & Account Management
-- Tables: cs_accounts, cs_contacts, cs_health_scores, cs_lifecycle_events,
--         cs_contracts, cs_success_plans, cs_milestones, cs_risks

DO $$ BEGIN

-- cs_accounts
CREATE TABLE IF NOT EXISTS cs_accounts (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    company_domain  TEXT REFERENCES companies(company_domain) ON DELETE SET NULL,
    owner_id        BIGINT REFERENCES users(id) ON DELETE SET NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                    CHECK (status IN ('prospect','active','at_risk','churned','inactive')),
    tier            VARCHAR(20) NOT NULL DEFAULT 'mid_market'
                    CHECK (tier IN ('strategic','enterprise','mid_market','smb','startup')),
    industry        VARCHAR(100) NOT NULL DEFAULT '',
    arr             DOUBLE PRECISION NOT NULL DEFAULT 0,
    mrr             DOUBLE PRECISION NOT NULL DEFAULT 0,
    contract_value  DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency        VARCHAR(3)  NOT NULL DEFAULT 'USD',
    renewal_date    TIMESTAMPTZ,
    lifecycle_stage VARCHAR(20) NOT NULL DEFAULT 'customer',
    notes           TEXT        NOT NULL DEFAULT '',
    tags            JSONB       NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_cs_accounts_domain   ON cs_accounts(company_domain);
CREATE INDEX IF NOT EXISTS ix_cs_accounts_owner    ON cs_accounts(owner_id);
CREATE INDEX IF NOT EXISTS ix_cs_accounts_status   ON cs_accounts(status);
CREATE INDEX IF NOT EXISTS ix_cs_accounts_renewal  ON cs_accounts(renewal_date);

-- cs_contacts
CREATE TABLE IF NOT EXISTS cs_contacts (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id  BIGINT NOT NULL REFERENCES cs_accounts(id) ON DELETE CASCADE,
    first_name  VARCHAR(100) NOT NULL DEFAULT '',
    last_name   VARCHAR(100) NOT NULL DEFAULT '',
    email       VARCHAR(255) NOT NULL DEFAULT '',
    phone       VARCHAR(50)  NOT NULL DEFAULT '',
    title       VARCHAR(255) NOT NULL DEFAULT '',
    role        VARCHAR(20)  NOT NULL DEFAULT 'primary'
                CHECK (role IN ('primary','executive_sponsor','technical','procurement','finance','champion')),
    is_primary  BOOLEAN      NOT NULL DEFAULT FALSE,
    owner_id    BIGINT REFERENCES users(id) ON DELETE SET NULL,
    notes       TEXT         NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_cs_contacts_account ON cs_contacts(account_id);
CREATE INDEX IF NOT EXISTS ix_cs_contacts_email   ON cs_contacts(email);

-- cs_health_scores
CREATE TABLE IF NOT EXISTS cs_health_scores (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id           BIGINT NOT NULL REFERENCES cs_accounts(id) ON DELETE CASCADE,
    score                DOUBLE PRECISION NOT NULL DEFAULT 0,
    grade                VARCHAR(2)  NOT NULL DEFAULT 'C'
                         CHECK (grade IN ('A','B','C','D','F')),
    trend                VARCHAR(10) NOT NULL DEFAULT 'stable'
                         CHECK (trend IN ('up','stable','down')),
    product_adoption     DOUBLE PRECISION NOT NULL DEFAULT 0,
    meeting_activity     DOUBLE PRECISION NOT NULL DEFAULT 0,
    email_activity       DOUBLE PRECISION NOT NULL DEFAULT 0,
    opportunity_activity DOUBLE PRECISION NOT NULL DEFAULT 0,
    open_issues          DOUBLE PRECISION NOT NULL DEFAULT 0,
    renewal_status       DOUBLE PRECISION NOT NULL DEFAULT 0,
    executive_engagement DOUBLE PRECISION NOT NULL DEFAULT 0,
    detail               JSONB       NOT NULL DEFAULT '{}',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_cs_health_account ON cs_health_scores(account_id);
CREATE INDEX IF NOT EXISTS ix_cs_health_created ON cs_health_scores(created_at);

-- cs_lifecycle_events
CREATE TABLE IF NOT EXISTS cs_lifecycle_events (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id  BIGINT      NOT NULL REFERENCES cs_accounts(id) ON DELETE CASCADE,
    stage       VARCHAR(20) NOT NULL
                CHECK (stage IN ('prospect','customer','onboarding','adoption','growth',
                                 'renewal','expansion','at_risk','churned')),
    from_stage  VARCHAR(20) NOT NULL DEFAULT '',
    changed_by  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    note        TEXT        NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_cs_lc_account ON cs_lifecycle_events(account_id);

-- cs_contracts
CREATE TABLE IF NOT EXISTS cs_contracts (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id          BIGINT NOT NULL REFERENCES cs_accounts(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    status              VARCHAR(20)  NOT NULL DEFAULT 'active'
                        CHECK (status IN ('draft','active','expired','renewed','terminated','pending_renewal')),
    value               DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency            VARCHAR(3)   NOT NULL DEFAULT 'USD',
    start_date          TIMESTAMPTZ,
    end_date            TIMESTAMPTZ,
    auto_renew          BOOLEAN      NOT NULL DEFAULT FALSE,
    renewal_probability DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    owner_id            BIGINT REFERENCES users(id) ON DELETE SET NULL,
    notes               TEXT         NOT NULL DEFAULT '',
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_cs_contracts_account ON cs_contracts(account_id);
CREATE INDEX IF NOT EXISTS ix_cs_contracts_end     ON cs_contracts(end_date);
CREATE INDEX IF NOT EXISTS ix_cs_contracts_status  ON cs_contracts(status);

-- cs_success_plans
CREATE TABLE IF NOT EXISTS cs_success_plans (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id  BIGINT      NOT NULL REFERENCES cs_accounts(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    status      VARCHAR(20)  NOT NULL DEFAULT 'active'
                CHECK (status IN ('draft','active','completed','cancelled')),
    owner_id    BIGINT REFERENCES users(id) ON DELETE SET NULL,
    goals       JSONB        NOT NULL DEFAULT '[]',
    notes       TEXT         NOT NULL DEFAULT '',
    due_date    TIMESTAMPTZ,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_cs_plans_account ON cs_success_plans(account_id);
CREATE INDEX IF NOT EXISTS ix_cs_plans_owner   ON cs_success_plans(owner_id);

-- cs_milestones
CREATE TABLE IF NOT EXISTS cs_milestones (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plan_id      BIGINT      NOT NULL REFERENCES cs_success_plans(id) ON DELETE CASCADE,
    account_id   BIGINT      NOT NULL REFERENCES cs_accounts(id) ON DELETE CASCADE,
    name         VARCHAR(255) NOT NULL,
    status       VARCHAR(20)  NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending','in_progress','completed','at_risk','missed')),
    due_date     TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    owner_id     BIGINT REFERENCES users(id) ON DELETE SET NULL,
    notes        TEXT         NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_cs_milestones_plan    ON cs_milestones(plan_id);
CREATE INDEX IF NOT EXISTS ix_cs_milestones_account ON cs_milestones(account_id);

-- cs_risks
CREATE TABLE IF NOT EXISTS cs_risks (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id  BIGINT      NOT NULL REFERENCES cs_accounts(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL,
    description TEXT         NOT NULL DEFAULT '',
    severity    VARCHAR(10)  NOT NULL DEFAULT 'medium'
                CHECK (severity IN ('low','medium','high','critical')),
    status      VARCHAR(20)  NOT NULL DEFAULT 'open'
                CHECK (status IN ('open','mitigated','accepted','closed')),
    owner_id    BIGINT REFERENCES users(id) ON DELETE SET NULL,
    due_date    TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_cs_risks_account ON cs_risks(account_id);
CREATE INDEX IF NOT EXISTS ix_cs_risks_status  ON cs_risks(status);

END $$;
