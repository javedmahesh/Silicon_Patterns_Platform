-- =====================================================================
-- 0022_dm_note_roles.sql  —  expand decision-maker notes to four role tiers
-- PostgreSQL / Supabase dialect. Requires 0018 (decision_maker_notes).
--
-- Phase 1 enterprise enrichment turns the two-tier collaboration notes
-- (team / personal) into four ordered tiers:
--     admin    — created by admins only; pinned first; visible to everyone.
--     manager  — created by admin/manager; below admin; visible to everyone.
--     team     — any authenticated user may add; visible to everyone.
--     personal — private to the author; author-only edit/delete.
-- Visibility/permission rules live in the application (backend.services); the
-- DB stays the hard gate on the allowed VALUES via this CHECK. Existing
-- 'team'/'personal' rows remain valid — this only widens the allowed set.
--
-- No column changes are needed for the richer profile fields (photo, summary,
-- skills, languages, followers, etc.): they are read from the raw Apify record
-- already preserved in decision_makers.profile_data (profile_data["raw"]).
-- =====================================================================

BEGIN;

ALTER TABLE decision_maker_notes DROP CONSTRAINT IF EXISTS ck_dm_note_type;
ALTER TABLE decision_maker_notes
    ADD CONSTRAINT ck_dm_note_type
    CHECK (note_type IN ('admin', 'manager', 'team', 'personal'));

COMMIT;
