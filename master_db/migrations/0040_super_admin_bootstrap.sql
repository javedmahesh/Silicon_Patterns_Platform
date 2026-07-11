-- =====================================================================
-- 0040_super_admin_bootstrap.sql  —  Enterprise User Approval & Access Governance
-- PostgreSQL / Supabase dialect. Requires 0021_user_lifecycle_audit.sql.
--
-- Additive only: the pending/active/disabled/rejected/deleted lifecycle,
-- user_audit_events, login_count and deleted_at already exist (0021). This widens
-- two CHECK constraints so a new "super_admin" role and two new audit actions
-- ("super_admin_bootstrap", "denied") are valid — no new tables/columns.
--
-- The live constraint name on `role` is the auto-generated `users_role_check`
-- (from 0007's inline CHECK, never explicitly named); re-added here as the
-- explicitly-named `ck_users_role` to match master_db/models.py going forward.
-- =====================================================================

BEGIN;

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role;
ALTER TABLE users ADD CONSTRAINT ck_users_role
    CHECK (role IN ('super_admin','admin','manager','member'));

ALTER TABLE user_audit_events DROP CONSTRAINT IF EXISTS ck_user_audit_action;
ALTER TABLE user_audit_events ADD CONSTRAINT ck_user_audit_action
    CHECK (action IN (
        'registered','login','approved','rejected','enabled','disabled',
        'role_changed','deleted','logout','session_refreshed',
        'super_admin_bootstrap','denied'));

COMMIT;
