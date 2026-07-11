-- Migration 0037: Outreach Phase 3/4 model <-> migration parity fix.
--
-- Found by scripts/check_migration_model_parity.py (added in this same change): the
-- Conversation & Inbox Engine + Gmail sync + Tasks/Meetings additions to the Outreach
-- module (master_db/models.py) were never given a SQL migration — only 0020_outreach.sql
-- (the original pre-Phase-3 schema) exists. SQLite tests never caught this because
-- Base.metadata.create_all() builds the full current schema directly from the models
-- every time; Postgres/Supabase (owned solely by these migrations) was never able to
-- create these tables or columns at all. This migration closes that gap without editing
-- 0020_outreach.sql itself (never edit an already-shipped migration).

DO $$ BEGIN

-- outreach_messages: 18 columns added by Phase 2/3 (scheduling+delivery tracking,
-- conversation engine, message state flags) that never made it into a migration.
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS scheduled_at        TIMESTAMPTZ;
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS cancel_at           TIMESTAMPTZ;
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS delivered_at        TIMESTAMPTZ;
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS bounced_at          TIMESTAMPTZ;
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS retry_count         INTEGER NOT NULL DEFAULT 0;
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS retry_at            TIMESTAMPTZ;
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS max_retries         INTEGER NOT NULL DEFAULT 3;
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS provider            VARCHAR(32) NOT NULL DEFAULT 'mock';
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS provider_message_id VARCHAR(200) NOT NULL DEFAULT '';
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS parent_message_id   BIGINT REFERENCES outreach_messages(id) ON DELETE SET NULL;
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS body_html           TEXT NOT NULL DEFAULT '';
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS folder              VARCHAR(20) NOT NULL DEFAULT 'inbox';
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS is_read             BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS is_starred          BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS is_archived         BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS is_trashed          BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS is_important        BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS is_pinned           BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS ix_outreach_msgs_provider_msg ON outreach_messages(provider_message_id);

-- outreach_messages.status: 0020 only allowed the pre-Phase-2 subset; widen to the full
-- OUTREACH_MESSAGE_STATUSES set (adds scheduled/sending/delivered/bounced/cancelled).
ALTER TABLE outreach_messages DROP CONSTRAINT IF EXISTS ck_outreach_msg_status;
ALTER TABLE outreach_messages ADD CONSTRAINT ck_outreach_msg_status CHECK (status IN (
    'draft','pending_approval','approved','scheduled','queued','sending','sent',
    'delivered','failed','bounced','cancelled','replied'));

-- outreach_activities.type: 0020 only allowed the pre-Phase-3 subset; widen to the full
-- OUTREACH_ACTIVITY_TYPES set (adds task/meeting/call/message-scheduling event types).
ALTER TABLE outreach_activities DROP CONSTRAINT IF EXISTS ck_outreach_activity_type;
ALTER TABLE outreach_activities ADD CONSTRAINT ck_outreach_activity_type CHECK (type IN (
    'lead_created','stage_changed','owner_changed','draft_created',
    'submitted_for_approval','approved','sent','reply_received','note_added',
    'task_created','task_completed','meeting_scheduled','meeting_completed',
    'call_logged','message_scheduled','message_cancelled'));

-- outreach_tasks (structured follow-up tasks — never had a migration)
CREATE TABLE IF NOT EXISTS outreach_tasks (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title               VARCHAR(512) NOT NULL,
    description         TEXT         NOT NULL DEFAULT '',
    company_domain      VARCHAR(255) REFERENCES companies(company_domain) ON DELETE SET NULL,
    decision_maker_id   BIGINT REFERENCES decision_makers(id) ON DELETE SET NULL,
    outreach_lead_id    BIGINT REFERENCES outreach_leads(id) ON DELETE CASCADE,
    assigned_to         BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_by          BIGINT REFERENCES users(id) ON DELETE SET NULL,
    due_at              TIMESTAMPTZ,
    priority            VARCHAR(10) NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('low','medium','high','urgent')),
    status              VARCHAR(16) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','in_progress','completed','cancelled')),
    completed_by        BIGINT REFERENCES users(id) ON DELETE SET NULL,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_outreach_tasks_lead     ON outreach_tasks(outreach_lead_id);
CREATE INDEX IF NOT EXISTS ix_outreach_tasks_assigned ON outreach_tasks(assigned_to);
CREATE INDEX IF NOT EXISTS ix_outreach_tasks_status   ON outreach_tasks(status);
CREATE INDEX IF NOT EXISTS ix_outreach_tasks_due       ON outreach_tasks(due_at);

-- outreach_meetings (meeting/call records — never had a migration)
CREATE TABLE IF NOT EXISTS outreach_meetings (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    outreach_lead_id    BIGINT REFERENCES outreach_leads(id) ON DELETE CASCADE,
    company_domain      VARCHAR(255) REFERENCES companies(company_domain) ON DELETE SET NULL,
    decision_maker_id   BIGINT REFERENCES decision_makers(id) ON DELETE SET NULL,
    meeting_type        VARCHAR(16) NOT NULL DEFAULT 'call'
                        CHECK (meeting_type IN ('call','video','in_person','demo','follow_up')),
    title               VARCHAR(512) NOT NULL DEFAULT '',
    scheduled_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    duration_minutes    INTEGER     NOT NULL DEFAULT 30,
    participants        JSONB       NOT NULL DEFAULT '[]',
    notes               TEXT        NOT NULL DEFAULT '',
    outcome             VARCHAR(16) NOT NULL DEFAULT ''
                        CHECK (outcome = '' OR outcome IN ('positive','neutral','negative','no_show','reschedule')),
    next_action         TEXT        NOT NULL DEFAULT '',
    created_by          BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_outreach_meetings_lead      ON outreach_meetings(outreach_lead_id);
CREATE INDEX IF NOT EXISTS ix_outreach_meetings_scheduled ON outreach_meetings(scheduled_at);
CREATE INDEX IF NOT EXISTS ix_outreach_meetings_domain    ON outreach_meetings(company_domain);

-- 0024_campaigns.sql created sequence_step_executions.outreach_task_id/
-- outreach_meeting_id as plain BIGINT (outreach_tasks/outreach_meetings didn't exist
-- yet at that point in the chain). Both tables exist now -- add the FK constraints
-- here, using the same names Postgres would have auto-generated for an inline
-- REFERENCES, so this is a no-op for anyone who already has them.
ALTER TABLE sequence_step_executions DROP CONSTRAINT IF EXISTS sequence_step_executions_outreach_task_id_fkey;
ALTER TABLE sequence_step_executions ADD CONSTRAINT sequence_step_executions_outreach_task_id_fkey
    FOREIGN KEY (outreach_task_id) REFERENCES outreach_tasks(id) ON DELETE SET NULL;
ALTER TABLE sequence_step_executions DROP CONSTRAINT IF EXISTS sequence_step_executions_outreach_meeting_id_fkey;
ALTER TABLE sequence_step_executions ADD CONSTRAINT sequence_step_executions_outreach_meeting_id_fkey
    FOREIGN KEY (outreach_meeting_id) REFERENCES outreach_meetings(id) ON DELETE SET NULL;

-- email_provider_accounts (per-user email provider config, incl. Gmail sync state)
CREATE TABLE IF NOT EXISTS email_provider_accounts (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id             BIGINT REFERENCES users(id) ON DELETE SET NULL,
    provider_type       VARCHAR(20) NOT NULL DEFAULT 'mock'
                        CHECK (provider_type IN ('mock','smtp','gmail','outlook')),
    connection_status   VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (connection_status IN ('connected','disconnected','error','pending')),
    config_json         TEXT        NOT NULL DEFAULT '{}',
    email_address       VARCHAR(512) NOT NULL DEFAULT '',
    oauth_state         TEXT        NOT NULL DEFAULT '',
    sync_cursor         TEXT,
    sync_status         VARCHAR(20) NOT NULL DEFAULT 'idle'
                        CHECK (sync_status IN ('idle','syncing','error','paused')),
    sync_error          TEXT        NOT NULL DEFAULT '',
    token_expires_at    TIMESTAMPTZ,
    last_sync_at        TIMESTAMPTZ,
    error_message       TEXT        NOT NULL DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_email_provider_user ON email_provider_accounts(user_id);

-- email_conversations (provider-independent thread grouping)
CREATE TABLE IF NOT EXISTS email_conversations (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    outreach_lead_id    BIGINT REFERENCES outreach_leads(id) ON DELETE SET NULL,
    company_domain      VARCHAR(255) REFERENCES companies(company_domain) ON DELETE SET NULL,
    decision_maker_id   BIGINT REFERENCES decision_makers(id) ON DELETE SET NULL,
    subject             VARCHAR(1000) NOT NULL DEFAULT '',
    thread_id           VARCHAR(80)  NOT NULL DEFAULT '',
    folder              VARCHAR(20)  NOT NULL DEFAULT 'inbox',
    message_count       INTEGER      NOT NULL DEFAULT 0,
    unread_count        INTEGER      NOT NULL DEFAULT 0,
    last_message_at     TIMESTAMPTZ,
    is_starred          BOOLEAN      NOT NULL DEFAULT false,
    is_archived         BOOLEAN      NOT NULL DEFAULT false,
    is_trashed          BOOLEAN      NOT NULL DEFAULT false,
    is_pinned           BOOLEAN      NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_email_conv_lead   ON email_conversations(outreach_lead_id);
CREATE INDEX IF NOT EXISTS ix_email_conv_domain ON email_conversations(company_domain);
CREATE INDEX IF NOT EXISTS ix_email_conv_last   ON email_conversations(last_message_at);
CREATE INDEX IF NOT EXISTS ix_email_conv_thread ON email_conversations(thread_id);
CREATE INDEX IF NOT EXISTS ix_email_conv_folder ON email_conversations(folder);

-- Now that email_conversations exists, the FK this migration's own earlier ALTER
-- implicitly depends on is satisfiable — outreach_messages.conversation_id references it.
ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS conversation_id BIGINT
    REFERENCES email_conversations(id) ON DELETE SET NULL;

-- email_attachments (file attachments on an outreach message)
CREATE TABLE IF NOT EXISTS email_attachments (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    outreach_message_id BIGINT NOT NULL REFERENCES outreach_messages(id) ON DELETE CASCADE,
    filename            VARCHAR(512) NOT NULL,
    content_type        VARCHAR(128) NOT NULL DEFAULT 'application/octet-stream',
    size_bytes          INTEGER      NOT NULL DEFAULT 0,
    status              VARCHAR(16)  NOT NULL DEFAULT 'uploaded'
                        CHECK (status IN ('pending','uploaded','failed')),
    content             TEXT         NOT NULL DEFAULT '',
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_email_attachments_msg ON email_attachments(outreach_message_id);

-- email_labels (system or user-defined)
CREATE TABLE IF NOT EXISTS email_labels (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(80) NOT NULL,
    color       VARCHAR(16) NOT NULL DEFAULT 'gray'
                CHECK (color IN ('gray','blue','green','red','yellow','purple','orange')),
    is_system   BOOLEAN     NOT NULL DEFAULT false,
    created_by  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_email_labels_creator ON email_labels(created_by);

-- conversation_labels (many-to-many junction: conversations <-> labels)
CREATE TABLE IF NOT EXISTS conversation_labels (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES email_conversations(id) ON DELETE CASCADE,
    label_id        BIGINT NOT NULL REFERENCES email_labels(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (conversation_id, label_id)
);

END $$;
