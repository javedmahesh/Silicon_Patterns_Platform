-- LEGACY: decision makers now come from the Apify Decision Maker Intelligence
-- engine; the LinkedIn `candidates` Supabase source is no longer part of the
-- pipeline. This script remains only for anyone still operating that legacy source.
--
-- Enable Row-Level Security on the LinkedIn `candidates` table (run in the
-- Supabase SQL editor). The server-side adapter uses the service-role key, which
-- BYPASSES RLS, so ingestion keeps working after this is applied.

ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;

-- Option A (recommended): anon can READ, nobody writes via anon.
-- The backend writes with the service-role key (bypasses RLS); analytics/read
-- clients using the anon key keep working read-only.
DROP POLICY IF EXISTS candidates_anon_read ON candidates;
CREATE POLICY candidates_anon_read
    ON candidates FOR SELECT
    TO anon
    USING (true);

-- Option B (only if the recruiter app MUST keep writing with the anon key and you
-- cannot move it to authenticated writes yet — weaker, re-opens anon write):
-- DROP POLICY IF EXISTS candidates_anon_write ON candidates;
-- CREATE POLICY candidates_anon_write
--     ON candidates FOR ALL
--     TO anon
--     USING (true) WITH CHECK (true);

-- Verify:
--   SELECT relrowsecurity FROM pg_class WHERE relname = 'candidates';   -- t
--   SELECT polname, polcmd FROM pg_policy
--     WHERE polrelid = 'candidates'::regclass;
