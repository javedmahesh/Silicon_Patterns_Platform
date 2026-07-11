-- =====================================================================
-- 0001_foundations.sql  —  Resolution-layer foundation
-- PostgreSQL / Supabase dialect. Apply FIRST.
--
-- Creates: extensions, the shared updated_at trigger, and the four
-- resolution-layer tables: companies, company_sources, company_aliases,
-- resolution_review_queue.
--
-- Idempotent: CREATE ... IF NOT EXISTS + guarded trigger, so re-running while
-- you review is safe. NOTHING here connects to or depends on the four engines.
-- =====================================================================

BEGIN;

-- pg_trgm  -> GIN trigram indexes for fast fuzzy company-name resolution at
--             scale (the resolver's difflib pass is only the local/P0 fallback).
-- citext   -> available for future case-insensitive columns if desired.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS citext;

-- Shared trigger that stamps updated_at on every UPDATE.
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- companies  [owner: Industry Discovery]
-- Master record. PK = normalized company_domain (the universal join key).
-- The resolver may also create low-confidence STUB rows (is_stub=true) for
-- domains other engines surface before Industry Discovery catalogues them.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
    company_domain        text PRIMARY KEY,
    canonical_company_id  text             NOT NULL DEFAULT '',
    company_name          text             NOT NULL DEFAULT '',
    name_key              text             NOT NULL DEFAULT '',
    website               text             NOT NULL DEFAULT '',
    company_linkedin      text             NOT NULL DEFAULT '',
    country               text             NOT NULL DEFAULT '',
    city                  text             NOT NULL DEFAULT '',
    headquarters          text             NOT NULL DEFAULT '',
    -- compliance flag (APPROVED / EXCLUDED_REGION / …) — NOT a geographic region
    compliance_flag       text             NOT NULL DEFAULT 'UNKNOWN',
    industry_category     text             NOT NULL DEFAULT '',
    sub_category          text             NOT NULL DEFAULT '',
    industry_type         text             NOT NULL DEFAULT '',
    technology_focus      text             NOT NULL DEFAULT '',
    prospect_type         text             NOT NULL DEFAULT 'UNKNOWN',
    company_tier          text             NOT NULL DEFAULT 'UNKNOWN',
    company_status        text             NOT NULL DEFAULT '',
    company_type          text             NOT NULL DEFAULT 'UNKNOWN',
    description           text             NOT NULL DEFAULT '',
    founded_year          text             NOT NULL DEFAULT '',
    source                text             NOT NULL DEFAULT '',
    source_type           text             NOT NULL DEFAULT '',
    discovery_date        text             NOT NULL DEFAULT '',
    confidence_score      double precision NOT NULL DEFAULT 0,
    validation_status     text             NOT NULL DEFAULT 'PENDING',
    is_stub               boolean          NOT NULL DEFAULT false,
    created_at            timestamptz      NOT NULL DEFAULT now(),
    updated_at            timestamptz      NOT NULL DEFAULT now(),

    CONSTRAINT ck_companies_tier       CHECK (company_tier      IN ('STARTUP','SCALEUP','ESTABLISHED','INCUMBENT','UNKNOWN')),
    CONSTRAINT ck_companies_prospect   CHECK (prospect_type     IN ('PRODUCT_COMPANY','SERVICE_PROVIDER','EDA_VENDOR','FOUNDRY','INVESTOR','PUBLISHER','ACADEMIC','UNKNOWN')),
    CONSTRAINT ck_companies_compliance CHECK (compliance_flag   IN ('APPROVED','EXCLUDED_REGION','REVIEW_REQUIRED','UNKNOWN')),
    CONSTRAINT ck_companies_validation CHECK (validation_status IN ('VALID','REVIEW_REQUIRED','REJECTED','STUB','PENDING')),
    -- The join key must already be normalized: lowercase, no scheme/path, has a dot.
    CONSTRAINT ck_companies_domain_normalized CHECK (
        company_domain = lower(company_domain)
        AND company_domain NOT LIKE '%/%'
        AND position('.' in company_domain) > 1
    )
);

CREATE INDEX IF NOT EXISTS ix_companies_name_key      ON companies (name_key);
CREATE INDEX IF NOT EXISTS ix_companies_canonical_id  ON companies (canonical_company_id);
CREATE INDEX IF NOT EXISTS ix_companies_prospect_type ON companies (prospect_type);
CREATE INDEX IF NOT EXISTS ix_companies_company_tier  ON companies (company_tier);
CREATE INDEX IF NOT EXISTS ix_companies_validation    ON companies (validation_status);
CREATE INDEX IF NOT EXISTS ix_companies_compliance    ON companies (compliance_flag);
CREATE INDEX IF NOT EXISTS ix_companies_name_key_trgm ON companies USING gin (name_key gin_trgm_ops);

DROP TRIGGER IF EXISTS trg_companies_updated_at ON companies;
CREATE TRIGGER trg_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------
-- company_sources  [owner: Industry Discovery]  provenance (many per company)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS company_sources (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_domain text        NOT NULL REFERENCES companies(company_domain) ON DELETE CASCADE,
    source_name    text        NOT NULL,
    source_type    text        NOT NULL DEFAULT '',
    source_tier    integer     NOT NULL DEFAULT 99,
    source_url     text        NOT NULL DEFAULT '',
    discovered_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_company_source UNIQUE (company_domain, source_name)
);
CREATE INDEX IF NOT EXISTS ix_company_sources_domain ON company_sources (company_domain);

-- ---------------------------------------------------------------------
-- company_aliases  [owner: resolution layer]
-- name_key -> company_domain. "Groq", "Groq Inc.", "GROQ" all map to groq.com.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS company_aliases (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alias          text             NOT NULL,
    name_key       text             NOT NULL,
    company_domain text             NOT NULL REFERENCES companies(company_domain) ON DELETE CASCADE,
    source         text             NOT NULL DEFAULT '',
    confidence     double precision NOT NULL DEFAULT 1.0,
    created_at     timestamptz      NOT NULL DEFAULT now(),
    CONSTRAINT uq_alias_namekey_domain UNIQUE (name_key, company_domain)
);
CREATE INDEX IF NOT EXISTS ix_aliases_name_key      ON company_aliases (name_key);
CREATE INDEX IF NOT EXISTS ix_aliases_name_key_trgm ON company_aliases USING gin (name_key gin_trgm_ops);

-- ---------------------------------------------------------------------
-- resolution_review_queue  [owner: resolution layer]
-- Stub-created and unresolved records park here for human confirm/merge.
-- The pipeline NEVER blocks on resolution — it queues and moves on.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resolution_review_queue (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    raw_name          text             NOT NULL DEFAULT '',
    raw_domain        text             NOT NULL DEFAULT '',
    raw_website       text             NOT NULL DEFAULT '',
    source_engine     text             NOT NULL DEFAULT '',
    source_record_ref text             NOT NULL DEFAULT '',
    suggested_domain  text             NOT NULL DEFAULT '',
    match_type        text             NOT NULL DEFAULT 'UNRESOLVED',
    confidence        double precision NOT NULL DEFAULT 0,
    status            text             NOT NULL DEFAULT 'pending',
    resolved_domain   text             NOT NULL DEFAULT '',
    notes             text             NOT NULL DEFAULT '',
    created_at        timestamptz      NOT NULL DEFAULT now(),
    reviewed_at       timestamptz,
    CONSTRAINT ck_review_match_type CHECK (match_type IN ('EXACT_DOMAIN','ALIAS','FUZZY_NAME','NEW_STUB','UNRESOLVED')),
    CONSTRAINT ck_review_status     CHECK (status     IN ('pending','approved','rejected','merged'))
);
CREATE INDEX IF NOT EXISTS ix_review_status        ON resolution_review_queue (status);
CREATE INDEX IF NOT EXISTS ix_review_source_engine ON resolution_review_queue (source_engine);

COMMIT;
