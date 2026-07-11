-- =====================================================================
-- 0044_news_intelligence.sql — News Intelligence upgrade
-- PostgreSQL / Supabase dialect. Requires 0002_opportunities (opportunities).
--
-- Upgrades the News Collection Engine -> Opportunities path:
--   * rich AI-extraction columns on opportunities (deterministic, no LLM),
--   * dedup / relationship keys (canonical_url, normalized_title,
--     entity_fingerprint, related_group_id) + lifecycle + manual-review flags,
--   * news_sources     — configured RSS / Google-Alerts / file feeds,
--   * news_articles    — collected raw articles (source metadata, dedup hash),
--   * opportunity_articles — every reporting source under one opportunity
--     (also links one article to many opportunities for multi-signal),
--   * opportunity_reviews  — append-only manual-review history (AI never
--     overwritten).
-- Every opportunities column is additive with a default, so existing rows and the
-- existing API keep working unchanged.
-- =====================================================================

BEGIN;

-- ---- rich AI extraction (opportunities) ----------------------------------
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS executive_summary   text    NOT NULL DEFAULT '';
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS ai_summary          text    NOT NULL DEFAULT '';
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS why_this_matters    text    NOT NULL DEFAULT '';
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS business_impact     text    NOT NULL DEFAULT '';
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS ai_reasoning        text    NOT NULL DEFAULT '';
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS opportunity_subtype varchar(64)  NOT NULL DEFAULT '';
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS technologies        jsonb   NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS products            jsonb   NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS people              jsonb   NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS organizations       jsonb   NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS countries           jsonb   NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS keywords            jsonb   NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS confidence_breakdown jsonb  NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS source_credibility  integer NOT NULL DEFAULT 0;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS lifecycle_status    varchar(20)  NOT NULL DEFAULT 'NEW';
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS is_relevant         boolean NOT NULL DEFAULT true;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS merged_into         varchar(64)  NOT NULL DEFAULT '';
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS canonical_url       varchar(1024) NOT NULL DEFAULT '';
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS normalized_title    varchar(512) NOT NULL DEFAULT '';
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS entity_fingerprint  varchar(64)  NOT NULL DEFAULT '';
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS related_group_id    varchar(64)  NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS ix_opportunities_lifecycle   ON opportunities (lifecycle_status);
CREATE INDEX IF NOT EXISTS ix_opportunities_related     ON opportunities (related_group_id);
CREATE INDEX IF NOT EXISTS ix_opportunities_fingerprint ON opportunities (entity_fingerprint);

-- ---- news_sources --------------------------------------------------------
CREATE TABLE IF NOT EXISTS news_sources (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name              varchar(255) NOT NULL DEFAULT '',
    adapter_type      varchar(30)  NOT NULL DEFAULT 'rss',
    url               varchar(1024) NOT NULL DEFAULT '',
    publisher         varchar(255) NOT NULL DEFAULT '',
    credibility       integer      NOT NULL DEFAULT 50,
    enabled           boolean      NOT NULL DEFAULT true,
    last_collected_at timestamptz,
    created_at        timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT ck_news_sources_adapter CHECK (adapter_type IN ('rss','google_alerts','file','manual'))
);

-- ---- news_articles -------------------------------------------------------
CREATE TABLE IF NOT EXISTS news_articles (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id        bigint REFERENCES news_sources(id) ON DELETE SET NULL,
    adapter_type     varchar(30)  NOT NULL DEFAULT 'file',
    publisher        varchar(255) NOT NULL DEFAULT '',
    source_name      varchar(255) NOT NULL DEFAULT '',
    url              varchar(1024) NOT NULL DEFAULT '',
    canonical_url    varchar(1024) NOT NULL DEFAULT '',
    title            text         NOT NULL DEFAULT '',
    normalized_title varchar(512) NOT NULL DEFAULT '',
    body             text         NOT NULL DEFAULT '',
    company_domain   varchar(255) NOT NULL DEFAULT '',
    company_name     varchar(255) NOT NULL DEFAULT '',
    entities         jsonb        NOT NULL DEFAULT '{}'::jsonb,
    content_hash     varchar(64)  NOT NULL DEFAULT '' UNIQUE,
    published_at     varchar(64)  NOT NULL DEFAULT '',
    collected_at     timestamptz  NOT NULL DEFAULT now(),
    processed        boolean      NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS ix_news_articles_domain    ON news_articles (company_domain);
CREATE INDEX IF NOT EXISTS ix_news_articles_canonical ON news_articles (canonical_url);

-- ---- opportunity_articles (reporting sources <-> opportunities) ----------
CREATE TABLE IF NOT EXISTS opportunity_articles (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    opportunity_id varchar(64) NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    article_id     bigint REFERENCES news_articles(id) ON DELETE SET NULL,
    url            varchar(1024) NOT NULL DEFAULT '',
    canonical_url  varchar(1024) NOT NULL DEFAULT '',
    publisher      varchar(255) NOT NULL DEFAULT '',
    source_name    varchar(255) NOT NULL DEFAULT '',
    source_type    varchar(60)  NOT NULL DEFAULT '',
    title          text         NOT NULL DEFAULT '',
    credibility    integer      NOT NULL DEFAULT 0,
    published_at   varchar(64)  NOT NULL DEFAULT '',
    collected_at   timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT uq_opp_article_url UNIQUE (opportunity_id, canonical_url)
);
CREATE INDEX IF NOT EXISTS ix_opp_articles_opp ON opportunity_articles (opportunity_id);

-- ---- opportunity_reviews (append-only manual-review history) --------------
CREATE TABLE IF NOT EXISTS opportunity_reviews (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    opportunity_id varchar(64) NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    action         varchar(30) NOT NULL,
    actor_email    varchar(255) NOT NULL DEFAULT '',
    detail         text         NOT NULL DEFAULT '',
    before_snapshot jsonb       NOT NULL DEFAULT '{}'::jsonb,
    after_snapshot  jsonb       NOT NULL DEFAULT '{}'::jsonb,
    created_at     timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT ck_opp_review_action CHECK (action IN
        ('not_relevant','merge','split','change_type','archive','restore','note'))
);
CREATE INDEX IF NOT EXISTS ix_opp_reviews_opp ON opportunity_reviews (opportunity_id);

COMMIT;
