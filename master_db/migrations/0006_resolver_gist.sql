-- =====================================================================
-- 0006_resolver_gist.sql  —  GiST trigram index for KNN nearest-match resolution
-- PostgreSQL / Supabase dialect. Requires 0001 (pg_trgm).
--
-- The validation phase found the planner would NOT use the GIN trigram index for
-- the resolver query `... ORDER BY similarity(name_key, :k) DESC LIMIT 1`: GIN
-- accelerates the `%` membership filter but cannot serve the similarity ORDER BY,
-- so it degraded to a Seq Scan + sort.
--
-- The resolver now issues a KNN query `... ORDER BY name_key <-> :k LIMIT 1`,
-- which a GiST gist_trgm_ops index serves as an INDEX-ORDERED scan (no full sort),
-- scale-independently. This migration swaps the GIN index on companies.name_key
-- for that GiST index. (The GIN index on companies.company_name used by the
-- `/companies ?q=` substring search, and the alias trigram index, are unchanged.)
-- =====================================================================

BEGIN;

-- Create the GiST KNN index first (no window without a name_key trigram index).
CREATE INDEX IF NOT EXISTS ix_companies_name_key_gist
    ON companies USING gist (name_key gist_trgm_ops);

-- Drop the now-superseded GIN index on name_key.
DROP INDEX IF EXISTS ix_companies_name_key_trgm;

COMMIT;
