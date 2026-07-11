-- =====================================================================
-- 0011_lead_score_confidence.sql  —  coverage + confidence on lead_scores
-- PostgreSQL / Supabase dialect. Requires 0003_platform_tables.sql (lead_scores).
--
-- The scorer is coverage-normalized (a strong company is not diluted by the
-- signals it is missing). `coverage` records how many of the 3 engine signals
-- (opportunity / demand / decision-makers) actually backed the score (0-3), and
-- `confidence` is its label — so the UI can show a low/medium/high indicator
-- next to the grade and distinguish a thin-evidence A+ from a fully-backed one.
-- =====================================================================

BEGIN;

ALTER TABLE lead_scores ADD COLUMN IF NOT EXISTS coverage integer NOT NULL DEFAULT 0;
ALTER TABLE lead_scores ADD COLUMN IF NOT EXISTS confidence text NOT NULL DEFAULT 'low'
    CHECK (confidence IN ('low', 'medium', 'high'));

COMMIT;
