-- =====================================================================
-- 0051_import_review.sql — human review & approval of an import (Phase 5)
-- PostgreSQL / Supabase dialect. Additive; extends 0049/0050 (import_jobs).
--
-- import_review_items : one reviewable record per preview row, with an explicit state
--   and per-field keep-platform/accept-historical decisions. Only 'approved'/'resolved'
--   items reach the transaction engine at commit.
-- import_review_events: immutable audit trail of every review decision (never deleted).
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS import_review_items (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id          bigint       NOT NULL REFERENCES import_jobs (id) ON DELETE CASCADE,
    record_kind     varchar(20)  NOT NULL,
    source_ref      varchar(120) NOT NULL,
    category        varchar(30)  NOT NULL,
    state           varchar(20)  NOT NULL DEFAULT 'pending',
    field_decisions jsonb        NOT NULL DEFAULT '{}'::jsonb,
    label           varchar(255) NOT NULL DEFAULT '',
    reviewer        varchar(320) NOT NULL DEFAULT '',
    reason          text         NOT NULL DEFAULT '',
    decided_at      timestamptz,
    created_at      timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT uq_review_item_ref UNIQUE (job_id, record_kind, source_ref),
    CONSTRAINT ck_review_item_kind     CHECK (record_kind IN ('company','decision_maker')),
    CONSTRAINT ck_review_item_category CHECK (category IN (
        'new_company','updated_company','new_decision_maker','updated_decision_maker',
        'conflict','duplicate','invalid','unchanged')),
    CONSTRAINT ck_review_item_state    CHECK (state IN (
        'pending','approved','rejected','skipped','resolved'))
);
CREATE INDEX IF NOT EXISTS ix_review_items_job   ON import_review_items (job_id);
CREATE INDEX IF NOT EXISTS ix_review_items_state ON import_review_items (job_id, state);

CREATE TABLE IF NOT EXISTS import_review_events (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id         bigint       NOT NULL REFERENCES import_jobs (id) ON DELETE CASCADE,
    review_item_id bigint       REFERENCES import_review_items (id) ON DELETE SET NULL,
    record_kind    varchar(20)  NOT NULL DEFAULT '',
    source_ref     varchar(120) NOT NULL DEFAULT '',
    action         varchar(30)  NOT NULL,
    field          varchar(120) NOT NULL DEFAULT '',
    previous_value text         NOT NULL DEFAULT '',
    approved_value text         NOT NULL DEFAULT '',
    reviewer       varchar(320) NOT NULL DEFAULT '',
    reason         text         NOT NULL DEFAULT '',
    created_at     timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_review_events_job  ON import_review_events (job_id);
CREATE INDEX IF NOT EXISTS ix_review_events_item ON import_review_events (review_item_id);

COMMIT;
