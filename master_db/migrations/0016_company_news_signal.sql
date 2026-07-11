-- =====================================================================
-- 0016_company_news_signal.sql  —  shared opportunities.company_news_signal column
-- PostgreSQL / Supabase dialect. Requires 0002_engine_tables.sql (opportunities).
--
-- A one-line human-readable signal on an opportunity row, shared by two incoming
-- features: Change_04 annual-lists (rank, "Rank: N") and Change_03 company-news
-- (a one-line summary of an executive move). Change_04 lands first, so it adds the
-- column; Change_03 reuses it. (Renumbered from the colleague's 0011 — that number
-- is already taken by 0011_lead_score_confidence in this tree.) Idempotent.
-- =====================================================================

BEGIN;

ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS company_news_signal varchar(512) NOT NULL DEFAULT '';

-- Partial index over the news / list opportunity_types both features query by.
CREATE INDEX IF NOT EXISTS ix_opportunities_news_type
    ON opportunities (opportunity_type)
    WHERE opportunity_type IN (
        'ANNUAL_LIST', 'EXECUTIVE_HIRE', 'LEADERSHIP_CHANGE', 'ROLE_CHANGE', 'COMPANY_NEWS'
    );

COMMIT;
