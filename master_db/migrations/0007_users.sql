-- =====================================================================
-- 0007_users.sql  —  Platform user accounts (Google Workspace SSO)
-- PostgreSQL / Supabase dialect. Requires 0001_foundations.sql.
--
-- One row per signed-in user. Identity comes from Google SSO (no passwords): the
-- API verifies Google's ID token and issues its own session JWT. Accounts are
-- DEACTIVATED (is_active=false), never hard-deleted, to preserve audit trails.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS users (
    id            bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         text        NOT NULL UNIQUE,             -- lower-cased company email
    full_name     text        NOT NULL DEFAULT '',
    picture       text        NOT NULL DEFAULT '',         -- Google avatar URL
    role          text        NOT NULL DEFAULT 'member'
                  CHECK (role IN ('admin','manager','member')),
    is_active     boolean     NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    last_login_at timestamptz,
    last_seen_at  timestamptz                                  -- throttled "recently active" stamp
);
CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);

COMMIT;
