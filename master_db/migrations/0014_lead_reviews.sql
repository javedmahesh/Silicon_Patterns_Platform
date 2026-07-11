-- =====================================================================
-- 0014_lead_reviews.sql  —  Human lead review + feedback/audit trail (P-task viii)
-- PostgreSQL / Supabase dialect. Requires 0001_foundations.sql + 0003_platform_tables.sql.
--
-- A human analyst's assessment of a lead, kept STRICTLY SEPARATE from the model
-- score: lead_reviews never touches lead_scores (the model grade/score is
-- preserved untouched). Every change is appended to lead_review_events — the
-- feedback table — which snapshots the model grade/score AT THE TIME of the human
-- action, so model-vs-human disagreement reports stay correct as the model
-- re-scores, and a future version can learn from the feedback. (Mirrors the
-- lead_assignments / lead_assignment_events audit pattern.)
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS lead_reviews (
    company_domain  text        PRIMARY KEY REFERENCES companies(company_domain) ON DELETE CASCADE,
    review_status   text        NOT NULL DEFAULT 'needs_review'
                    CHECK (review_status IN ('approved','needs_review','strategic_account','disqualified','watchlist')),
    human_notes     text        NOT NULL DEFAULT '',
    reviewed_by     bigint,                       -- users.id (soft ref; survives user deactivation)
    reviewed_by_email text      NOT NULL DEFAULT '',
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_lead_reviews_status ON lead_reviews (review_status);

CREATE TABLE IF NOT EXISTS lead_review_events (
    id             bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_domain text        NOT NULL DEFAULT '',
    actor_user_id  bigint,                        -- soft ref (audit survives deactivation)
    actor_email    text        NOT NULL DEFAULT '',
    from_status    text        NOT NULL DEFAULT '',
    to_status      text        NOT NULL DEFAULT '',
    notes          text        NOT NULL DEFAULT '',
    model_grade    text        NOT NULL DEFAULT '',   -- snapshot of lead_scores.grade at review time
    model_score    double precision NOT NULL DEFAULT 0,  -- snapshot of lead_scores.lead_score at review time
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_lead_review_events_company ON lead_review_events (company_domain);

COMMIT;
