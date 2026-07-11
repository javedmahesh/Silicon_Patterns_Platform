-- =====================================================================
-- 0019_dm_functional_area.sql  —  functional area on decision_makers (from Apify)
-- PostgreSQL / Supabase dialect. Requires 0002 (decision_makers).
--
-- The Apify actor returns a `functional` area (e.g. "Engineering", "Operations").
-- Promote it to its own NULLABLE column alongside the other structured professional
-- fields from 0018 so it can be queried/displayed directly. NULL when absent — no
-- placeholder. The full raw actor record remains in profile_data.raw.
-- =====================================================================

BEGIN;

ALTER TABLE decision_makers ADD COLUMN IF NOT EXISTS functional_area text;

COMMIT;
