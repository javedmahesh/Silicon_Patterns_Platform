-- =====================================================================
-- 0041_password_auth.sql  —  First-party email/password authentication
-- PostgreSQL / Supabase dialect. Requires 0040_super_admin_bootstrap.sql.
--
-- Replaces the Google/Supabase-OAuth sign-in path with first-party
-- email/password: users.password_hash (scrypt, see backend/password.py) +
-- users.must_change_password (forces a password change before any other
-- authenticated endpoint serves the request — set on the initial admin
-- bootstrap). Additive only: no existing column/table is touched or dropped.
-- Widens the user_audit_events action CHECK for the 3 new auditable events
-- this flow introduces (login_failed, password_changed,
-- forced_password_change_completed).
-- =====================================================================

BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE user_audit_events DROP CONSTRAINT IF EXISTS ck_user_audit_action;
ALTER TABLE user_audit_events ADD CONSTRAINT ck_user_audit_action
    CHECK (action IN (
        'registered','login','login_failed','approved','rejected','enabled','disabled',
        'role_changed','deleted','logout','session_refreshed',
        'super_admin_bootstrap','denied','password_changed','forced_password_change_completed'));

COMMIT;
