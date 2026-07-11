-- =====================================================================
-- 0012_leadership_signals.sql  —  person-level director+ leadership movement
-- PostgreSQL / Supabase dialect. Requires 0001_foundations.sql (companies) and
-- 0002_engine_tables.sql (decision_makers).
--
-- Person-level intelligence about *who moved* — promotions, role changes,
-- executive hires/departures, board appointments, founder changes — for
-- director-level and above ONLY (manager-level and ICs are gated out upstream).
-- Distinct from the Blog Crawler's company-level "Leadership Change" opportunity
-- (that an event happened). Platform-derived, never produced by the engines:
--   * source 'linkedin_history' — from a decision maker's own career history
--   * source 'blog_event'       — extracted from Leadership Change opportunities
-- company_domain is NULLABLE (the documented LinkedIn exception): a historical
-- employer may not resolve to a catalogued company.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS leadership_signals (
    signal_id         text PRIMARY KEY,
    company_domain    text        REFERENCES companies(company_domain) ON DELETE CASCADE,
    company_name      text        NOT NULL DEFAULT '',
    decision_maker_id bigint      REFERENCES decision_makers(id) ON DELETE SET NULL,
    linkedin_url      text        NOT NULL DEFAULT '',
    person_name       text        NOT NULL DEFAULT '',
    movement_type     text        NOT NULL,
    from_title        text        NOT NULL DEFAULT '',
    to_title          text        NOT NULL DEFAULT '',
    seniority_band    text        NOT NULL,
    role_function     text        NOT NULL DEFAULT '',
    effective_date    text        NOT NULL DEFAULT '',   -- YYYY-MM
    event_age_days    integer     NOT NULL DEFAULT -1,
    confidence        text        NOT NULL DEFAULT 'low',
    source            text        NOT NULL DEFAULT 'linkedin_history',
    source_ref        text        NOT NULL DEFAULT '',
    summary           text        NOT NULL DEFAULT '',
    computed_at       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_ldr_movement   CHECK (movement_type IN (
        'promotion','role_change','new_executive_hire','executive_departure',
        'board_appointment','founder_change','executive_reshuffle')),
    CONSTRAINT ck_ldr_band       CHECK (seniority_band IN (
        'c_level','president','founder','managing_director','evp','svp','vp',
        'senior_director','director','head_of')),
    CONSTRAINT ck_ldr_source     CHECK (source IN ('linkedin_history','blog_event')),
    CONSTRAINT ck_ldr_confidence CHECK (confidence IN ('low','medium','high'))
);
CREATE INDEX IF NOT EXISTS ix_ldr_domain    ON leadership_signals (company_domain);
CREATE INDEX IF NOT EXISTS ix_ldr_movement  ON leadership_signals (movement_type);
CREATE INDEX IF NOT EXISTS ix_ldr_band      ON leadership_signals (seniority_band);
CREATE INDEX IF NOT EXISTS ix_ldr_source    ON leadership_signals (source);
CREATE INDEX IF NOT EXISTS ix_ldr_effective ON leadership_signals (effective_date);

COMMIT;
