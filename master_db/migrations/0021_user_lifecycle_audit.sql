-- =====================================================================
-- 0021_user_lifecycle_audit.sql  —  account lifecycle + user-management audit
-- PostgreSQL / Supabase dialect. Requires 0007_users.sql.
--
-- Enterprise auth: accounts now have a lifecycle (pending → active, plus disabled
-- / rejected / soft-deleted) on top of the existing is_active gate, a login_count,
-- a deleted_at (soft delete — PII scrubbed, row kept), and an append-only
-- user_audit_events trail of admin actions. Identity stays Google-SSO (no change).
-- =====================================================================

BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS status      text    NOT NULL DEFAULT 'active';
ALTER TABLE users ADD COLUMN IF NOT EXISTS login_count integer NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at  timestamptz;

-- Existing accounts are already in use → treat them as approved/active.
UPDATE users SET status = CASE WHEN is_active THEN 'active' ELSE 'disabled' END
 WHERE status IS NULL OR status = '';

ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_status;
ALTER TABLE users ADD CONSTRAINT ck_users_status
    CHECK (status IN ('pending','active','disabled','rejected','deleted'));
CREATE INDEX IF NOT EXISTS ix_users_status ON users (status);

CREATE TABLE IF NOT EXISTS user_audit_events (
    id             bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    target_user_id bigint      REFERENCES users(id) ON DELETE SET NULL,
    target_email   text        NOT NULL DEFAULT '',
    actor_user_id  bigint      REFERENCES users(id) ON DELETE SET NULL,
    actor_email    text        NOT NULL DEFAULT '',
    action         text        NOT NULL,
    detail         text        NOT NULL DEFAULT '',
    created_at     timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_user_audit_action CHECK (action IN (
        'registered','login','approved','rejected','enabled','disabled',
        'role_changed','deleted'))
);
CREATE INDEX IF NOT EXISTS ix_user_audit_target  ON user_audit_events (target_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_user_audit_created ON user_audit_events (created_at DESC);

COMMIT;
