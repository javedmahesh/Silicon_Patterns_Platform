-- Migration 0029: Enterprise CRM Phase 6 — Workflow Automation & Business Process Engine
-- Tables: workflows, workflow_executions, approval_requests, sla_policies, sla_trackers

DO $$ BEGIN

-- workflows
CREATE TABLE IF NOT EXISTS workflows (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    status          VARCHAR(20) NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft','active','paused','archived')),
    trigger_event   VARCHAR(40) NOT NULL
                    CHECK (trigger_event IN (
                        'lead_created','opportunity_created','deal_created','deal_stage_changed',
                        'deal_won','deal_lost','customer_created','health_changed',
                        'contract_renewal_window','task_completed','meeting_completed',
                        'campaign_status_changed'
                    )),
    conditions      JSONB       NOT NULL DEFAULT '{}',
    actions         JSONB       NOT NULL DEFAULT '[]',
    version         INTEGER     NOT NULL DEFAULT 1,
    is_enabled      BOOLEAN     NOT NULL DEFAULT true,
    created_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_workflows_trigger ON workflows(trigger_event);
CREATE INDEX IF NOT EXISTS ix_workflows_status  ON workflows(status);

-- workflow_executions
CREATE TABLE IF NOT EXISTS workflow_executions (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    workflow_id         BIGINT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    trigger_event       VARCHAR(40) NOT NULL,
    entity_type         VARCHAR(30) NOT NULL DEFAULT '',
    entity_id           VARCHAR(64) NOT NULL DEFAULT '',
    status              VARCHAR(10) NOT NULL DEFAULT 'success'
                        CHECK (status IN ('success','failed','partial')),
    actions_executed    JSONB       NOT NULL DEFAULT '[]',
    error_detail        TEXT        NOT NULL DEFAULT '',
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ,
    duration_ms         INTEGER     NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_wfexec_workflow ON workflow_executions(workflow_id);
CREATE INDEX IF NOT EXISTS ix_wfexec_entity   ON workflow_executions(entity_type, entity_id);

-- approval_requests
CREATE TABLE IF NOT EXISTS approval_requests (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    approval_type           VARCHAR(30) NOT NULL
                            CHECK (approval_type IN ('large_deal','discount','contract_change','customer_escalation')),
    entity_type             VARCHAR(30) NOT NULL DEFAULT '',
    entity_id               VARCHAR(64) NOT NULL DEFAULT '',
    requested_by            BIGINT REFERENCES users(id) ON DELETE SET NULL,
    approver_id             BIGINT REFERENCES users(id) ON DELETE SET NULL,
    status                  VARCHAR(10) NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','approved','rejected','cancelled')),
    decision_reason         TEXT NOT NULL DEFAULT '',
    workflow_execution_id   BIGINT REFERENCES workflow_executions(id) ON DELETE SET NULL,
    requested_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at              TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_approvals_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS ix_approvals_entity ON approval_requests(entity_type, entity_id);

-- sla_policies
CREATE TABLE IF NOT EXISTS sla_policies (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                    VARCHAR(255) NOT NULL,
    entity_type             VARCHAR(30) NOT NULL DEFAULT '',
    trigger_event           VARCHAR(40) NOT NULL DEFAULT '',
    due_hours               INTEGER NOT NULL DEFAULT 24,
    escalate_after_hours    INTEGER,
    escalate_to_user_id     BIGINT REFERENCES users(id) ON DELETE SET NULL,
    is_enabled              BOOLEAN NOT NULL DEFAULT true,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_sla_policies_entity ON sla_policies(entity_type);

-- sla_trackers
CREATE TABLE IF NOT EXISTS sla_trackers (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_id       BIGINT NOT NULL REFERENCES sla_policies(id) ON DELETE CASCADE,
    entity_type     VARCHAR(30) NOT NULL DEFAULT '',
    entity_id       VARCHAR(64) NOT NULL DEFAULT '',
    due_at          TIMESTAMPTZ NOT NULL,
    status          VARCHAR(10) NOT NULL DEFAULT 'on_track'
                    CHECK (status IN ('on_track','at_risk','breached','resolved','escalated')),
    escalated_at    TIMESTAMPTZ,
    breached_at     TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_sla_trackers_status ON sla_trackers(status);
CREATE INDEX IF NOT EXISTS ix_sla_trackers_entity ON sla_trackers(entity_type, entity_id);

END $$;
