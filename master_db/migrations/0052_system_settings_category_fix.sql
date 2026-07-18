-- =====================================================================
-- 0052_system_settings_category_fix.sql — fix the 'platform' category CHECK
-- PostgreSQL / Supabase dialect. Additive; corrects 0036.
--
-- 0036 tried to widen system_settings.category to allow 'platform' (for the
-- Scheduler page's runtime-editable schedule, backend/scheduler_config.py) via
-- `DROP CONSTRAINT IF EXISTS ck_system_setting_category`. But the constraint
-- 0032 actually created was an inline, unnamed CHECK — Postgres auto-named it
-- `system_settings_category_check` — so that DROP silently no-op'd (IF EXISTS)
-- and 0036 added a SECOND, differently-named constraint alongside the original.
-- Both are enforced together, so the untouched original (no 'platform') still
-- rejected every scheduler-config save with a CheckViolation → 500. Same class
-- of bug 0040 already fixed for users.role; same fix shape here.
-- =====================================================================

BEGIN;

ALTER TABLE system_settings DROP CONSTRAINT IF EXISTS system_settings_category_check;
ALTER TABLE system_settings DROP CONSTRAINT IF EXISTS ck_system_setting_category;
ALTER TABLE system_settings ADD CONSTRAINT ck_system_setting_category
    CHECK (category IN ('crm','workflow','ai','email','notification','retention','platform'));

COMMIT;
