-- =====================================================================
-- 0015_review_score_adjustment.sql  —  Review-driven score adjustment (reconciled Change_05)
-- PostgreSQL / Supabase dialect. Requires 0003_platform_tables.sql (lead_scores)
-- and 0014_lead_reviews.sql (lead_reviews / lead_review_events).
--
-- A human review may OPTIONALLY influence scoring (config `review_feedback`, OFF by
-- default). The model lead_score/grade are NEVER changed — a SEPARATE adjusted
-- score/grade is stored alongside them, derived from the company's current review
-- status (strategic_account/approved boost + grade floor; disqualified penalty).
-- The adjustment never compounds (always computed from the pristine model score),
-- lapses when a review `expires_at`, and is fully auditable (snapshots + rationale).
-- =====================================================================

BEGIN;

-- The adjusted score/grade live BESIDE the model values (fully separated).
ALTER TABLE lead_scores ADD COLUMN IF NOT EXISTS adjusted_score double precision;
ALTER TABLE lead_scores ADD COLUMN IF NOT EXISTS adjusted_grade text NOT NULL DEFAULT '';

-- Reviewer attribution timestamp + optional expiry (after which the score effect lapses).
ALTER TABLE lead_reviews ADD COLUMN IF NOT EXISTS reviewed_at timestamptz;
ALTER TABLE lead_reviews ADD COLUMN IF NOT EXISTS expires_at  timestamptz;

-- Each audited review action also snapshots the model->adjusted delta at that moment.
ALTER TABLE lead_review_events ADD COLUMN IF NOT EXISTS adjusted_score double precision NOT NULL DEFAULT 0;
ALTER TABLE lead_review_events ADD COLUMN IF NOT EXISTS adjusted_grade text NOT NULL DEFAULT '';

COMMIT;
