-- =====================================================================
-- 0002_engine_tables.sql  —  Engine-owned tables
-- PostgreSQL / Supabase dialect. Requires 0001_foundations.sql.
--
-- One section per engine. Each engine writes ONLY its own table(s); every table
-- joins back to companies on company_domain. These mirror the real output
-- schemas of the four engines (verified against their models/exporters) so the
-- P1 ingestors map column-for-column.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- opportunities  [owner: Blog Crawler]   one row per article / market event
-- PK opportunity_id (OPP-<sha1>); company_domain is REQUIRED (resolver
-- guarantees a company/stub exists before an opportunity is written).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id              text PRIMARY KEY,
    company_domain              text    NOT NULL REFERENCES companies(company_domain) ON DELETE CASCADE,
    canonical_company_id        text    NOT NULL DEFAULT '',
    company_name                text    NOT NULL DEFAULT '',
    company_tier                text    NOT NULL DEFAULT 'UNKNOWN',
    prospect_type               text    NOT NULL DEFAULT 'UNKNOWN',
    country                     text    NOT NULL DEFAULT '',
    compliance_flag             text    NOT NULL DEFAULT 'UNKNOWN',
    article_title               text    NOT NULL DEFAULT '',
    article_url                 text    NOT NULL DEFAULT '',
    source                      text    NOT NULL DEFAULT '',
    source_type                 text    NOT NULL DEFAULT '',
    published_date              text    NOT NULL DEFAULT '',
    event_age_days              integer NOT NULL DEFAULT -1,
    opportunity_type            text    NOT NULL DEFAULT '',
    opportunity_category        text    NOT NULL DEFAULT '',
    funding_stage               text    NOT NULL DEFAULT '',
    funding_amount              text    NOT NULL DEFAULT '',
    product_mentioned           text    NOT NULL DEFAULT '',
    technology_mentioned        text    NOT NULL DEFAULT '',
    technology_focus            text    NOT NULL DEFAULT '',
    conference_mentioned        text    NOT NULL DEFAULT '',
    partnership_mentioned       text    NOT NULL DEFAULT '',
    expansion_mentioned         text    NOT NULL DEFAULT '',
    partner_company             text    NOT NULL DEFAULT '',
    foundry_partner             text    NOT NULL DEFAULT '',
    eda_partner                 text    NOT NULL DEFAULT '',
    opportunity_score           integer NOT NULL DEFAULT 0,
    effective_opportunity_score integer NOT NULL DEFAULT 0,
    recency_weight              double precision NOT NULL DEFAULT 1.0,
    confidence_score            integer NOT NULL DEFAULT 0,
    lead_readiness_score        integer NOT NULL DEFAULT 0,   -- Blog's own readiness (an INPUT to Lead Scoring)
    summary                     text    NOT NULL DEFAULT '',
    validation_status           text    NOT NULL DEFAULT 'REVIEW_REQUIRED',
    source_tier                 integer NOT NULL DEFAULT 0,
    discovery_date              text    NOT NULL DEFAULT '',
    ingested_at                 timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_opportunities_domain     ON opportunities (company_domain);
CREATE INDEX IF NOT EXISTS ix_opportunities_type       ON opportunities (opportunity_type);
CREATE INDEX IF NOT EXISTS ix_opportunities_validation ON opportunities (validation_status);
CREATE INDEX IF NOT EXISTS ix_opportunities_eff_score  ON opportunities (effective_opportunity_score);

-- ---------------------------------------------------------------------
-- jobs  [owner: Career Scraper]   one row per posting
-- PK job_id (hash of domain+job_url). geo_region is the Career "region_flag"
-- (a GEOGRAPHIC region) — deliberately a different column from compliance_flag.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    job_id                      text PRIMARY KEY,
    company_domain              text    NOT NULL REFERENCES companies(company_domain) ON DELETE CASCADE,
    company_name                text    NOT NULL DEFAULT '',
    company_tier                text    NOT NULL DEFAULT 'UNKNOWN',
    job_title                   text    NOT NULL DEFAULT '',
    job_category                text    NOT NULL DEFAULT '',
    department                  text    NOT NULL DEFAULT '',
    location                    text    NOT NULL DEFAULT '',
    country                     text    NOT NULL DEFAULT '',
    geo_region                  text    NOT NULL DEFAULT '',
    employment_type             text    NOT NULL DEFAULT '',
    posted_date                 text    NOT NULL DEFAULT '',
    ats_provider                text    NOT NULL DEFAULT '',
    technologies                text    NOT NULL DEFAULT '',
    seniority                   text    NOT NULL DEFAULT '',
    engineering_relevance_score integer NOT NULL DEFAULT 0,
    job_url                     text    NOT NULL DEFAULT '',
    source_url                  text    NOT NULL DEFAULT '',
    scrape_date                 text    NOT NULL DEFAULT '',
    ingested_at                 timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_jobs_domain_url UNIQUE (company_domain, job_url)
);
CREATE INDEX IF NOT EXISTS ix_jobs_domain    ON jobs (company_domain);
CREATE INDEX IF NOT EXISTS ix_jobs_category  ON jobs (job_category);
CREATE INDEX IF NOT EXISTS ix_jobs_seniority ON jobs (seniority);

-- ---------------------------------------------------------------------
-- demand_signals  [owner: Career Scraper]   one row per company (1:1)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS demand_signals (
    company_domain          text PRIMARY KEY REFERENCES companies(company_domain) ON DELETE CASCADE,
    canonical_company_id    text    NOT NULL DEFAULT '',
    company_name            text    NOT NULL DEFAULT '',
    country                 text    NOT NULL DEFAULT '',
    geo_region              text    NOT NULL DEFAULT '',
    rtl_jobs                integer NOT NULL DEFAULT 0,
    asic_jobs               integer NOT NULL DEFAULT 0,
    verification_jobs       integer NOT NULL DEFAULT 0,
    physical_design_jobs    integer NOT NULL DEFAULT 0,
    dft_jobs                integer NOT NULL DEFAULT 0,
    sta_jobs                integer NOT NULL DEFAULT 0,
    validation_jobs         integer NOT NULL DEFAULT 0,
    fpga_jobs               integer NOT NULL DEFAULT 0,
    embedded_jobs           integer NOT NULL DEFAULT 0,
    architecture_jobs       integer NOT NULL DEFAULT 0,
    total_engineering_jobs  integer NOT NULL DEFAULT 0,
    technologies_detected   text    NOT NULL DEFAULT '',
    primary_focus           text    NOT NULL DEFAULT '',
    demand_score            double precision NOT NULL DEFAULT 0,
    normalized_demand_score double precision NOT NULL DEFAULT 0,
    demand_signal           text    NOT NULL DEFAULT '',
    hiring_trend            text    NOT NULL DEFAULT '',
    lead_readiness_score    double precision NOT NULL DEFAULT 0,  -- Career's own readiness (an INPUT to Lead Scoring)
    newest_job_date         text    NOT NULL DEFAULT '',
    hiring_regions          text    NOT NULL DEFAULT '',
    india_hiring_flag       boolean NOT NULL DEFAULT false,
    ats_provider            text    NOT NULL DEFAULT '',
    last_updated            timestamptz,
    ingested_at             timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- company_rollups  [owner: Career Scraper]   company_intelligence.xlsx (1:1)
-- priority_rank here is Career's OWN A/B/C rank — distinct from lead_scores.grade.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS company_rollups (
    company_domain          text PRIMARY KEY REFERENCES companies(company_domain) ON DELETE CASCADE,
    company_name            text    NOT NULL DEFAULT '',
    company_tier            text    NOT NULL DEFAULT 'UNKNOWN',
    country                 text    NOT NULL DEFAULT '',
    geo_region              text    NOT NULL DEFAULT '',
    demand_score            double precision NOT NULL DEFAULT 0,
    lead_readiness_score    double precision NOT NULL DEFAULT 0,
    demand_signal           text    NOT NULL DEFAULT '',
    total_engineering_jobs  integer NOT NULL DEFAULT 0,
    primary_focus           text    NOT NULL DEFAULT '',
    technologies_detected   text    NOT NULL DEFAULT '',
    newest_job_date         text    NOT NULL DEFAULT '',
    hiring_regions          text    NOT NULL DEFAULT '',
    india_hiring_flag       boolean NOT NULL DEFAULT false,
    priority_rank           text    NOT NULL DEFAULT 'C',
    next_action             text    NOT NULL DEFAULT '',
    last_updated            timestamptz,
    ingested_at             timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- decision_makers  [owner: LinkedIn Scraper]
-- company_domain is NULLABLE here (the documented exception): LinkedIn carries
-- no domain natively, so the resolver attaches one best-effort and unresolved
-- rows keep NULL + a review-queue entry. ON DELETE SET NULL so deleting a
-- company never deletes a real person.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS decision_makers (
    id                    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    linkedin_url          text NOT NULL UNIQUE,
    company_domain        text REFERENCES companies(company_domain) ON DELETE SET NULL,
    resolved_company_name text             NOT NULL DEFAULT '',
    first_name            text             NOT NULL DEFAULT '',
    last_name             text             NOT NULL DEFAULT '',
    headline              text             NOT NULL DEFAULT '',
    current_title         text             NOT NULL DEFAULT '',
    seniority             text             NOT NULL DEFAULT '',
    location              text             NOT NULL DEFAULT '',
    match_score           double precision NOT NULL DEFAULT 0,
    agent_score           double precision,
    agent_reasoning       text             NOT NULL DEFAULT '',
    status                text             NOT NULL DEFAULT 'sourced',
    profile_data          jsonb            NOT NULL DEFAULT '{}'::jsonb,
    source                text             NOT NULL DEFAULT 'linkedin',
    captured_at           timestamptz,
    ingested_at           timestamptz      NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_dm_domain    ON decision_makers (company_domain);
CREATE INDEX IF NOT EXISTS ix_dm_status    ON decision_makers (status);
CREATE INDEX IF NOT EXISTS ix_dm_seniority ON decision_makers (seniority);

COMMIT;
