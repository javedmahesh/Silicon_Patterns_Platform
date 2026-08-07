-- =====================================================================
-- 0057_discovery_candidates.sql — Market Discovery Engine candidate store
-- PostgreSQL / Supabase dialect. No prerequisites beyond a fresh schema.
--
-- The ONE table the Market Discovery Engine needs. A discovery candidate is not a
-- company: it may be unresolved, below the confidence threshold, or later rejected,
-- so writing every sighting into `companies` would fill the canonical table with
-- speculative rows. This is the engine's cross-run memory — how a scheduled run
-- distinguishes "new" from "seen yesterday", which no existing table records.
--
-- Everything else is REUSED, not duplicated:
--   * companies                — canonical record; written only via the existing
--                                integration.resolver.CompanyResolver on promotion.
--   * company_sources          — per-source provenance (already modelled + indexed).
--   * resolution_review_queue  — the existing "a human should look at this" queue.
--
-- company_domain is deliberately NOT a foreign key: a candidate usually has no
-- company row yet, and must survive one being merged away or removed.
--
-- candidate_key is the engine's deterministic identity (domain -> LinkedIn slug ->
-- comparison name, hashed), so the same company always lands on the same row no
-- matter which source reported it. UNIQUE enforces the dedup guarantee in the DB,
-- not just in application code.
--
-- technologies / markets / sources / raw_payload / metadata_json are JSON-encoded
-- TEXT rather than json columns: identical behaviour on SQLite (dev/tests) and
-- Postgres, and nothing queries inside them.
--
-- Additive only. Nothing existing reads or writes this table.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS discovery_candidates (
    id             bigserial PRIMARY KEY,
    candidate_key  varchar(64)  NOT NULL UNIQUE,
    company_name   varchar(255) NOT NULL DEFAULT '',
    company_domain varchar(255) NOT NULL DEFAULT '',
    website        varchar(512) NOT NULL DEFAULT '',
    linkedin_url   varchar(512) NOT NULL DEFAULT '',
    description    text         NOT NULL DEFAULT '',
    industry       varchar(120) NOT NULL DEFAULT '',
    headquarters   varchar(255) NOT NULL DEFAULT '',
    country        varchar(120) NOT NULL DEFAULT '',
    founded_year   varchar(8)   NOT NULL DEFAULT '',
    employee_count varchar(40)  NOT NULL DEFAULT '',
    funding_stage  varchar(60)  NOT NULL DEFAULT '',
    technologies   text         NOT NULL DEFAULT '[]',
    markets        text         NOT NULL DEFAULT '[]',
    source         varchar(60)  NOT NULL DEFAULT '',
    source_id      varchar(255) NOT NULL DEFAULT '',
    source_url     varchar(512) NOT NULL DEFAULT '',
    sources        text         NOT NULL DEFAULT '[]',
    status         varchar(20)  NOT NULL DEFAULT 'new',
    confidence     double precision NOT NULL DEFAULT 0.0,
    times_seen     integer      NOT NULL DEFAULT 1,
    run_id         varchar(80)  NOT NULL DEFAULT '',
    raw_payload    text         NOT NULL DEFAULT '{}',
    metadata_json  text         NOT NULL DEFAULT '{}',
    first_seen     timestamptz  NOT NULL DEFAULT now(),
    last_seen      timestamptz  NOT NULL DEFAULT now(),
    created_at     timestamptz  NOT NULL DEFAULT now()
);

ALTER TABLE discovery_candidates DROP CONSTRAINT IF EXISTS ck_discovery_status;
ALTER TABLE discovery_candidates ADD CONSTRAINT ck_discovery_status
    CHECK (status IN ('new','updated','duplicate','rejected','below_threshold','promoted'));

CREATE INDEX IF NOT EXISTS ix_discovery_candidates_status    ON discovery_candidates (status);
CREATE INDEX IF NOT EXISTS ix_discovery_candidates_domain    ON discovery_candidates (company_domain);
CREATE INDEX IF NOT EXISTS ix_discovery_candidates_last_seen ON discovery_candidates (last_seen);
CREATE INDEX IF NOT EXISTS ix_discovery_candidates_run       ON discovery_candidates (run_id);

COMMIT;
