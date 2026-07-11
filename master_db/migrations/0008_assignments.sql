-- =====================================================================
-- 0008_assignments.sql  —  Lead assignment + audit trail (CRM-lite)
-- PostgreSQL / Supabase dialect. Requires 0001_foundations.sql + 0007_users.sql.
--
-- A manager assigns a company (lead) to a user with a pipeline status; every change
-- is recorded in lead_assignment_events (mirrors the review_actions audit pattern).
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS lead_assignments (
    id             bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_domain text        NOT NULL REFERENCES companies(company_domain) ON DELETE CASCADE,
    user_id        bigint      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_by    bigint,
    status         text        NOT NULL DEFAULT 'assigned'
                   CHECK (status IN ('new','assigned','contacted','qualified','proposal','won','lost','on_hold')),
    note           text        NOT NULL DEFAULT '',
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (company_domain, user_id)
);
CREATE INDEX IF NOT EXISTS ix_assignments_user   ON lead_assignments (user_id);
CREATE INDEX IF NOT EXISTS ix_assignments_status ON lead_assignments (status);

CREATE TABLE IF NOT EXISTS lead_assignment_events (
    id             bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    assignment_id  bigint,                       -- lead_assignments.id (row may be gone after unassign)
    company_domain text        NOT NULL DEFAULT '',
    actor_user_id  bigint,
    action         text        NOT NULL,         -- assigned|reassigned|unassigned|status_changed|note_changed
    from_value     text        NOT NULL DEFAULT '',
    to_value       text        NOT NULL DEFAULT '',
    detail         text        NOT NULL DEFAULT '',
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_assignment_events_company ON lead_assignment_events (company_domain);

COMMIT;
