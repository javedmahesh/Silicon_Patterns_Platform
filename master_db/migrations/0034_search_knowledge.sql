-- Migration 0034: Enterprise CRM Phase 11 — Enterprise Search & Knowledge Platform
-- Tables: saved_searches, search_history, kb_categories, kb_articles, kb_article_versions,
--         kb_attachments, kb_article_views

DO $$ BEGIN

-- saved_searches
CREATE TABLE IF NOT EXISTS saved_searches (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    query       JSONB        NOT NULL DEFAULT '{}',
    owner_id    BIGINT REFERENCES users(id) ON DELETE SET NULL,
    is_favorite BOOLEAN      NOT NULL DEFAULT false,
    is_shared   BOOLEAN      NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_saved_searches_owner ON saved_searches(owner_id);

-- search_history (Recent Searches + Search Analytics)
CREATE TABLE IF NOT EXISTS search_history (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id             BIGINT REFERENCES users(id) ON DELETE SET NULL,
    query_text          VARCHAR(500) NOT NULL DEFAULT '',
    entity_types        JSONB        NOT NULL DEFAULT '[]',
    result_count        INTEGER      NOT NULL DEFAULT 0,
    response_time_ms    INTEGER      NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_search_history_user    ON search_history(user_id);
CREATE INDEX IF NOT EXISTS ix_search_history_created ON search_history(created_at);

-- kb_categories (self-referential hierarchy)
CREATE TABLE IF NOT EXISTS kb_categories (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    description TEXT         NOT NULL DEFAULT '',
    parent_id   BIGINT REFERENCES kb_categories(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_kb_categories_parent ON kb_categories(parent_id);

-- kb_articles
CREATE TABLE IF NOT EXISTS kb_articles (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_id     BIGINT REFERENCES kb_categories(id) ON DELETE SET NULL,
    title           VARCHAR(500) NOT NULL,
    body            TEXT         NOT NULL DEFAULT '',
    status          VARCHAR(20)  NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft','pending_approval','published','archived')),
    tags            JSONB        NOT NULL DEFAULT '[]',
    owner_id        BIGINT REFERENCES users(id) ON DELETE SET NULL,
    version         INTEGER      NOT NULL DEFAULT 1,
    view_count      INTEGER      NOT NULL DEFAULT 0,
    created_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    published_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_kb_articles_category ON kb_articles(category_id);
CREATE INDEX IF NOT EXISTS ix_kb_articles_status   ON kb_articles(status);
CREATE INDEX IF NOT EXISTS ix_kb_articles_owner    ON kb_articles(owner_id);

-- kb_article_versions
CREATE TABLE IF NOT EXISTS kb_article_versions (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    article_id  BIGINT NOT NULL REFERENCES kb_articles(id) ON DELETE CASCADE,
    version     INTEGER      NOT NULL,
    title       VARCHAR(500) NOT NULL DEFAULT '',
    body        TEXT         NOT NULL DEFAULT '',
    edited_by   BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_kb_article_versions_article ON kb_article_versions(article_id);

-- kb_attachments (metadata only)
CREATE TABLE IF NOT EXISTS kb_attachments (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    article_id      BIGINT NOT NULL REFERENCES kb_articles(id) ON DELETE CASCADE,
    filename        VARCHAR(255) NOT NULL,
    content_type    VARCHAR(100) NOT NULL DEFAULT '',
    size_bytes      INTEGER      NOT NULL DEFAULT 0,
    uploaded_by     BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_kb_attachments_article ON kb_attachments(article_id);

-- kb_article_views
CREATE TABLE IF NOT EXISTS kb_article_views (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    article_id  BIGINT NOT NULL REFERENCES kb_articles(id) ON DELETE CASCADE,
    viewed_by   BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_kb_article_views_article ON kb_article_views(article_id);
CREATE INDEX IF NOT EXISTS ix_kb_article_views_created ON kb_article_views(created_at);

END $$;
