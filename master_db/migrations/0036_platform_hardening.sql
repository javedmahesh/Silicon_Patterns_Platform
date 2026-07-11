-- Migration 0036: Enterprise CRM Phase 13 — Production Deployment, Authentication &
-- Platform Hardening. No new tables — widens two existing CHECK constraints:
--   * user_audit_events.action gains 'logout' / 'session_refreshed' (session lifecycle,
--     added alongside the existing Google-SSO/JWT auth rather than a Supabase re-platform)
--   * system_settings.category gains 'platform' (feature-flag storage reuses the
--     existing generic key/value settings store from Phase 9 instead of new infra)

DO $$ BEGIN

ALTER TABLE user_audit_events DROP CONSTRAINT IF EXISTS ck_user_audit_action;
ALTER TABLE user_audit_events ADD CONSTRAINT ck_user_audit_action CHECK (action IN (
    'registered','login','approved','rejected','enabled','disabled',
    'role_changed','deleted','logout','session_refreshed'));

ALTER TABLE system_settings DROP CONSTRAINT IF EXISTS ck_system_setting_category;
ALTER TABLE system_settings ADD CONSTRAINT ck_system_setting_category CHECK (category IN (
    'crm','workflow','ai','email','notification','retention','platform'));

END $$;
