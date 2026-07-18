-- =====================================================================
-- 0047_signal_category.sql — Leadership as a first-class signal category
-- PostgreSQL / Supabase dialect. Requires 0002_opportunities (opportunities).
--
-- Adds opportunities.signal_category (LEADERSHIP | NEWS), the first-class grouping
-- that separates people-movement events (executive hires, leadership & role changes)
-- OUT of the general NEWS feed everywhere in the platform (filtering, dashboard,
-- charts, counts). The value is derived from opportunity_type (see
-- config.enums.signal_category_for) and kept in sync on every write by the ORM
-- listener in master_db/models.py.
--
-- Additive with a default, and existing leadership rows are preserved (only their
-- category label is backfilled) — every existing opportunity and API keeps working.
-- =====================================================================

BEGIN;

ALTER TABLE opportunities
    ADD COLUMN IF NOT EXISTS signal_category varchar(20) NOT NULL DEFAULT 'NEWS';

-- Backfill: reclassify the leadership people-movement types into their own category.
-- Preserves the underlying rows — only the grouping label changes.
UPDATE opportunities
   SET signal_category = 'LEADERSHIP'
 WHERE opportunity_type IN ('EXECUTIVE_HIRE', 'LEADERSHIP_CHANGE', 'ROLE_CHANGE');

CREATE INDEX IF NOT EXISTS ix_opportunities_signal_category
    ON opportunities (signal_category);

COMMIT;
