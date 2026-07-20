-- =====================================================================
-- 0055_opportunity_project_intel.sql — geography + priority_tier on opportunities
-- PostgreSQL / Supabase dialect. Requires 0044_news_intelligence (opportunities).
--
-- New Semiconductor Project Intelligence (Phase 3): the News Collection Engine now
-- also emits structured PROJECT_INTEL opportunities (new chip/ASIC/SoC programs,
-- tapeouts, design wins, design/R&D centers, new/expanding fabs, OSAT/ATMP, capacity/
-- facility expansions — see integration/news/project_intel.py). These two additive
-- columns persist the article-derived location and buying-intent priority so project
-- intelligence is filterable/sortable/surfaced on the existing Opportunities API/UI:
--   geography      — India-city aware ("Bengaluru, India" / "India"); "" when the
--                    article gives no location evidence (never inferred from the feed).
--   priority_tier  — high | medium | low (project_intel.project_priority): startup/
--                    India/high-intent project types -> high; softer expansions ->
--                    medium; low-actionability -> low. Lower tiers are KEPT, not dropped.
-- Additive with defaults, so every existing opportunity (and every non-project row) is
-- unaffected — priority_tier simply defaults to 'medium', geography to ''.
-- =====================================================================

BEGIN;

ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS geography     varchar(120) NOT NULL DEFAULT '';
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS priority_tier varchar(10)  NOT NULL DEFAULT 'medium';

ALTER TABLE opportunities DROP CONSTRAINT IF EXISTS ck_opp_priority_tier;
ALTER TABLE opportunities ADD CONSTRAINT ck_opp_priority_tier
    CHECK (priority_tier IN ('high','medium','low'));

CREATE INDEX IF NOT EXISTS ix_opportunities_priority ON opportunities (priority_tier);

COMMIT;
