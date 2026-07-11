-- =====================================================================
-- 0013_engagement_recommendations.sql  —  sales-pitch recommendation (P-task 9)
-- PostgreSQL / Supabase dialect. Requires 0001_foundations.sql (companies).
--
-- One recommendation per company (1:1). Platform-derived (never an engine) from
-- the company's own signals — opportunities, leadership_signals, demand/jobs,
-- technology, partnerships, funding, company type, decision makers — into a
-- likely business need + the matching Silicon Patterns offering + a one-line
-- pitch, with a confidence score and a JSON rationale of the evidence used.
-- Evidence-grounded + deterministic (no LLM); recomputed by the `engagement`
-- orchestrator stage on every refresh.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS engagement_recommendations (
    company_domain   text PRIMARY KEY REFERENCES companies(company_domain) ON DELETE CASCADE,
    business_need    text        NOT NULL DEFAULT '',
    offering         text        NOT NULL DEFAULT '',
    pitch            text        NOT NULL DEFAULT '',
    confidence       integer     NOT NULL DEFAULT 0,
    confidence_label text        NOT NULL DEFAULT 'low',
    rationale        jsonb       NOT NULL DEFAULT '[]'::jsonb,
    signals_used     integer     NOT NULL DEFAULT 0,
    model_version    text        NOT NULL DEFAULT '',
    computed_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_engagement_confidence CHECK (confidence_label IN ('low','medium','high'))
);
CREATE INDEX IF NOT EXISTS ix_engagement_offering   ON engagement_recommendations (offering);
CREATE INDEX IF NOT EXISTS ix_engagement_confidence ON engagement_recommendations (confidence);

COMMIT;
