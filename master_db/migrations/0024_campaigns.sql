-- Migration 0024: Enterprise CRM Phase 1 — Campaign & Sequence Management
-- Adds campaigns, campaign_members, outreach_sequences, sequence_steps,
-- sequence_enrollments, sequence_step_executions.

-- -------------------------------------------------------------------------
-- campaigns
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaigns (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                TEXT NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    campaign_type       TEXT NOT NULL DEFAULT 'cold_outreach'
                        CHECK (campaign_type IN ('cold_outreach','nurture','followup','reengagement','event')),
    status              TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft','active','paused','completed','archived')),
    owner_id            BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_by          BIGINT REFERENCES users(id) ON DELETE SET NULL,
    start_date          TIMESTAMPTZ,
    end_date            TIMESTAMPTZ,
    goal                TEXT NOT NULL DEFAULT '',
    budget              DOUBLE PRECISION,
    tags                JSONB NOT NULL DEFAULT '[]',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_campaigns_owner  ON campaigns (owner_id);
CREATE INDEX IF NOT EXISTS ix_campaigns_status ON campaigns (status);

-- -------------------------------------------------------------------------
-- campaign_members
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaign_members (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id         BIGINT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    company_domain      TEXT REFERENCES companies(company_domain) ON DELETE CASCADE,
    decision_maker_id   BIGINT REFERENCES decision_makers(id) ON DELETE SET NULL,
    opportunity_id      TEXT REFERENCES opportunities(opportunity_id) ON DELETE SET NULL,
    outreach_lead_id    BIGINT REFERENCES outreach_leads(id) ON DELETE SET NULL,
    joined_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    current_stage       TEXT NOT NULL DEFAULT 'pending',
    last_activity_at    TIMESTAMPTZ,
    engagement_status   TEXT NOT NULL DEFAULT 'active'
                        CHECK (engagement_status IN ('active','paused','completed','removed')),
    campaign_outcome    TEXT NOT NULL DEFAULT ''
                        CHECK (campaign_outcome = '' OR campaign_outcome IN ('converted','lost','no_response','disqualified')),
    notes               TEXT NOT NULL DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (campaign_id, company_domain)
);

CREATE INDEX IF NOT EXISTS ix_campaign_members_campaign ON campaign_members (campaign_id);
CREATE INDEX IF NOT EXISTS ix_campaign_members_domain   ON campaign_members (company_domain);

-- -------------------------------------------------------------------------
-- outreach_sequences
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS outreach_sequences (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_by  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_outreach_sequences_active ON outreach_sequences (is_active);

-- -------------------------------------------------------------------------
-- sequence_steps
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sequence_steps (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sequence_id BIGINT NOT NULL REFERENCES outreach_sequences(id) ON DELETE CASCADE,
    step_order  INTEGER NOT NULL,
    action      TEXT NOT NULL
                CHECK (action IN ('email','follow_up','meeting_request','call','task','wait','manual_review')),
    name        TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    delay_days  INTEGER NOT NULL DEFAULT 0,
    template_id BIGINT REFERENCES outreach_templates(id) ON DELETE SET NULL,
    config      JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (sequence_id, step_order)
);

CREATE INDEX IF NOT EXISTS ix_sequence_steps_seq ON sequence_steps (sequence_id);

-- -------------------------------------------------------------------------
-- sequence_enrollments
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sequence_enrollments (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sequence_id         BIGINT NOT NULL REFERENCES outreach_sequences(id) ON DELETE CASCADE,
    campaign_member_id  BIGINT REFERENCES campaign_members(id) ON DELETE CASCADE,
    outreach_lead_id    BIGINT NOT NULL REFERENCES outreach_leads(id) ON DELETE CASCADE,
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active','paused','completed','cancelled','failed')),
    current_step        INTEGER NOT NULL DEFAULT 0,
    next_step_at        TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    enrolled_by         BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_enrollments_sequence ON sequence_enrollments (sequence_id);
CREATE INDEX IF NOT EXISTS ix_enrollments_lead     ON sequence_enrollments (outreach_lead_id);
CREATE INDEX IF NOT EXISTS ix_enrollments_status   ON sequence_enrollments (status);
CREATE INDEX IF NOT EXISTS ix_enrollments_next     ON sequence_enrollments (next_step_at);

-- -------------------------------------------------------------------------
-- sequence_step_executions
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sequence_step_executions (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    enrollment_id       BIGINT NOT NULL REFERENCES sequence_enrollments(id) ON DELETE CASCADE,
    step_id             BIGINT NOT NULL REFERENCES sequence_steps(id) ON DELETE CASCADE,
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','completed','skipped','failed')),
    scheduled_at        TIMESTAMPTZ,
    executed_at         TIMESTAMPTZ,
    outreach_message_id BIGINT REFERENCES outreach_messages(id) ON DELETE SET NULL,
    -- outreach_task_id/outreach_meeting_id: outreach_tasks/outreach_meetings don't
    -- exist yet at this point in the migration chain (they're created in
    -- 0037_outreach_gap_fix.sql) -- FK constraints for these two columns are added
    -- there, once both target tables exist. Plain BIGINT here, not unconstrained
    -- forever.
    outreach_task_id    BIGINT,
    outreach_meeting_id BIGINT,
    notes               TEXT NOT NULL DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_step_execs_enrollment ON sequence_step_executions (enrollment_id);
CREATE INDEX IF NOT EXISTS ix_step_execs_status     ON sequence_step_executions (status);
CREATE INDEX IF NOT EXISTS ix_step_execs_scheduled  ON sequence_step_executions (scheduled_at);

-- updated_at triggers (Postgres only — SQLite uses Python onupdate)
CREATE OR REPLACE FUNCTION _set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'campaigns_updated_at') THEN
    CREATE TRIGGER campaigns_updated_at BEFORE UPDATE ON campaigns
      FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'campaign_members_updated_at') THEN
    CREATE TRIGGER campaign_members_updated_at BEFORE UPDATE ON campaign_members
      FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'outreach_sequences_updated_at') THEN
    CREATE TRIGGER outreach_sequences_updated_at BEFORE UPDATE ON outreach_sequences
      FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'sequence_enrollments_updated_at') THEN
    CREATE TRIGGER sequence_enrollments_updated_at BEFORE UPDATE ON sequence_enrollments
      FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
  END IF;
END $$;
