-- =====================================================================
-- 0058_market_intelligence.sql — Market Intelligence Layer record store
-- PostgreSQL / Supabase dialect. Requires 0057 (discovery_candidates) only
-- conceptually; there is no foreign key between them (see below).
--
-- The ONE table the Market Intelligence Layer needs. It holds the platform's
-- INTERPRETATION of a discovered company — classification, technologies, market
-- signals, opportunity priority and the explanation behind it — which is a
-- different thing, changing for different reasons, from the discovery engine's
-- record of what it saw:
--
--   * a rule-pack change re-derives every row here and touches no candidate;
--   * a re-crawl refreshes a candidate without invalidating an interpretation
--     that is still correct.
--
-- Everything else is REUSED, not duplicated:
--   * discovery_candidates  — the input; read, never written by this layer.
--   * companies             — the canonical record; intelligence never promotes.
--   * lead_scores           — untouched; this layer feeds it, it does not replace it.
--
-- candidate_key is the discovery engine's deterministic identity (domain ->
-- LinkedIn slug -> comparison name, hashed), so an interpretation always lands on
-- the same row no matter which source reported the company. UNIQUE enforces
-- one-interpretation-per-company in the DB, not just in application code.
--
-- It is deliberately NOT a foreign key: intelligence must survive its candidate
-- being merged, re-keyed or removed, exactly as discovery_candidates.company_domain
-- is not a foreign key to companies.
--
-- priority / priority_score / confidence are real columns because the executive
-- dashboard and lead scoring filter and rank on them. classifications /
-- technologies / signals / factors / reasons / enrichment are JSON-encoded TEXT:
-- identical behaviour on SQLite (dev/tests) and Postgres, and nothing queries
-- inside them.
--
-- Additive only. Nothing existing reads or writes this table.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS market_intelligence (
    id                     bigserial PRIMARY KEY,
    candidate_key          varchar(64)  NOT NULL UNIQUE,
    company_name           varchar(255) NOT NULL DEFAULT '',
    company_domain         varchar(255) NOT NULL DEFAULT '',
    website                varchar(512) NOT NULL DEFAULT '',
    source                 varchar(60)  NOT NULL DEFAULT '',
    primary_classification varchar(120) NOT NULL DEFAULT '',
    classifications        text         NOT NULL DEFAULT '[]',
    technologies           text         NOT NULL DEFAULT '[]',
    signals                text         NOT NULL DEFAULT '[]',
    signal_types           text         NOT NULL DEFAULT '[]',
    classification_count   integer      NOT NULL DEFAULT 0,
    technology_count       integer      NOT NULL DEFAULT 0,
    signal_count           integer      NOT NULL DEFAULT 0,
    priority               varchar(12)  NOT NULL DEFAULT 'low',
    priority_score         double precision NOT NULL DEFAULT 0.0,
    confidence             double precision NOT NULL DEFAULT 0.0,
    factors                text         NOT NULL DEFAULT '[]',
    reasons                text         NOT NULL DEFAULT '[]',
    explanation            text         NOT NULL DEFAULT '',
    rule_pack              varchar(60)  NOT NULL DEFAULT '',
    rule_pack_version      varchar(40)  NOT NULL DEFAULT '',
    enrichment             text         NOT NULL DEFAULT '{}',
    run_id                 varchar(80)  NOT NULL DEFAULT '',
    evaluated_at           timestamptz  NOT NULL DEFAULT now(),
    created_at             timestamptz  NOT NULL DEFAULT now()
);

ALTER TABLE market_intelligence DROP CONSTRAINT IF EXISTS ck_market_intelligence_priority;
ALTER TABLE market_intelligence ADD CONSTRAINT ck_market_intelligence_priority
    CHECK (priority IN ('critical','high','medium','low'));

CREATE INDEX IF NOT EXISTS ix_market_intelligence_priority  ON market_intelligence (priority);
CREATE INDEX IF NOT EXISTS ix_market_intelligence_domain    ON market_intelligence (company_domain);
CREATE INDEX IF NOT EXISTS ix_market_intelligence_evaluated ON market_intelligence (evaluated_at);
CREATE INDEX IF NOT EXISTS ix_market_intelligence_run       ON market_intelligence (run_id);

COMMIT;
