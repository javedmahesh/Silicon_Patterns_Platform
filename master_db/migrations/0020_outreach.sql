-- =====================================================================
-- 0020_outreach.sql  —  native Outreach module tables
-- PostgreSQL / Supabase dialect. Requires 0001 (companies) + 0002
-- (decision_makers) + 0007 (users).
--
-- Outreach is a FIRST-CLASS native module, not a separate app. It layers an
-- engagement *cycle* on top of the existing intelligence tables and never
-- duplicates them: score/grade/priority come from lead_scores, the recommended
-- pitch from engagement_recommendations, contacts from decision_makers, the
-- company from companies, identity/roles from users. These tables hold ONLY the
-- outreach-specific state: pipeline, drafts/approvals, mock-mail, activity.
-- =====================================================================

BEGIN;

-- ─── outreach_leads (one engagement cycle per company) ──────────────────────
CREATE TABLE IF NOT EXISTS outreach_leads (
    id                   bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_domain       text        NOT NULL UNIQUE
                         REFERENCES companies(company_domain) ON DELETE CASCADE,
    owner_id             bigint      REFERENCES users(id) ON DELETE SET NULL,
    primary_dm_id        bigint      REFERENCES decision_makers(id) ON DELETE SET NULL,
    stage                text        NOT NULL DEFAULT 'research_complete',
    service_interest     text,
    source               text        NOT NULL DEFAULT 'discovery',
    qualification_reason text        NOT NULL DEFAULT '',
    qualified_at         timestamptz,
    last_activity_at     timestamptz,
    next_action_at       timestamptz,
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_outreach_stage CHECK (stage IN (
        'research_complete','outreach_ready','contacted','replied',
        'interested','meeting_scheduled','proposal_sent','won','lost')),
    CONSTRAINT ck_outreach_lead_source CHECK (source IN ('discovery','manual')),
    CONSTRAINT ck_outreach_service CHECK (
        service_interest IN ('staffing','engineering','training'))
);
CREATE INDEX IF NOT EXISTS ix_outreach_leads_stage ON outreach_leads (stage);
CREATE INDEX IF NOT EXISTS ix_outreach_leads_owner ON outreach_leads (owner_id);

-- ─── outreach_templates ({{variable}}-based, deterministic) ──────────────────
CREATE TABLE IF NOT EXISTS outreach_templates (
    id          bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        text        NOT NULL,
    category    text        NOT NULL DEFAULT '',
    subject     text        NOT NULL DEFAULT '',
    body        text        NOT NULL DEFAULT '',
    is_active   boolean     NOT NULL DEFAULT true,
    created_by  bigint      REFERENCES users(id) ON DELETE SET NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_outreach_templates_active ON outreach_templates (is_active);

-- ─── outreach_messages (draft → approval → sent(mock) → replied) ─────────────
CREATE TABLE IF NOT EXISTS outreach_messages (
    id                bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    outreach_lead_id  bigint      NOT NULL REFERENCES outreach_leads(id) ON DELETE CASCADE,
    decision_maker_id bigint      REFERENCES decision_makers(id) ON DELETE SET NULL,
    template_id       bigint      REFERENCES outreach_templates(id) ON DELETE SET NULL,
    created_by        bigint      REFERENCES users(id) ON DELETE SET NULL,
    approved_by       bigint      REFERENCES users(id) ON DELETE SET NULL,
    direction         text        NOT NULL DEFAULT 'outbound',
    status            text        NOT NULL DEFAULT 'draft',
    to_email          text        NOT NULL DEFAULT '',
    from_email        text        NOT NULL DEFAULT '',
    subject           text        NOT NULL DEFAULT '',
    body              text        NOT NULL DEFAULT '',
    thread_id         text        NOT NULL DEFAULT '',
    failed_reason     text        NOT NULL DEFAULT '',
    approved_at       timestamptz,
    sent_at           timestamptz,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_outreach_msg_status CHECK (status IN (
        'draft','pending_approval','approved','queued','sent','failed','replied')),
    CONSTRAINT ck_outreach_msg_dir CHECK (direction IN ('outbound','inbound'))
);
CREATE INDEX IF NOT EXISTS ix_outreach_msgs_lead   ON outreach_messages (outreach_lead_id);
CREATE INDEX IF NOT EXISTS ix_outreach_msgs_status ON outreach_messages (status);
CREATE INDEX IF NOT EXISTS ix_outreach_msgs_thread ON outreach_messages (thread_id);

-- ─── outreach_activities (append-only timeline / audit log) ──────────────────
CREATE TABLE IF NOT EXISTS outreach_activities (
    id               bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    outreach_lead_id bigint      NOT NULL REFERENCES outreach_leads(id) ON DELETE CASCADE,
    actor_id         bigint      REFERENCES users(id) ON DELETE SET NULL,
    actor_email      text        NOT NULL DEFAULT '',
    type             text        NOT NULL,
    detail           text        NOT NULL DEFAULT '',
    created_at       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_outreach_activity_type CHECK (type IN (
        'lead_created','stage_changed','owner_changed','draft_created',
        'submitted_for_approval','approved','sent','reply_received','note_added'))
);
CREATE INDEX IF NOT EXISTS ix_outreach_activities_lead
    ON outreach_activities (outreach_lead_id, created_at DESC);

COMMIT;
