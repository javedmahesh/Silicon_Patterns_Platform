-- Migration 0031: Enterprise CRM Phase 8 — AI Intelligence & Copilot
-- Tables: ai_insights, ai_recommendations, ai_risk_scores, ai_engagement_scores,
--         ai_briefings, ai_copilot_queries
-- Deterministic/rules-based, no external LLM tables or credentials.

DO $$ BEGIN

-- ai_insights
CREATE TABLE IF NOT EXISTS ai_insights (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    insight_type    VARCHAR(20) NOT NULL
                    CHECK (insight_type IN ('deal','customer','opportunity','campaign','pipeline','revenue')),
    entity_type     VARCHAR(30) NOT NULL DEFAULT '',
    entity_id       VARCHAR(64) NOT NULL DEFAULT '',
    title           VARCHAR(255) NOT NULL,
    detail          TEXT        NOT NULL DEFAULT '',
    severity        VARCHAR(10) NOT NULL DEFAULT 'medium'
                    CHECK (severity IN ('low','medium','high','critical')),
    confidence      VARCHAR(10) NOT NULL DEFAULT 'medium'
                    CHECK (confidence IN ('low','medium','high')),
    status          VARCHAR(10) NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','dismissed','resolved')),
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ai_insights_type   ON ai_insights(insight_type);
CREATE INDEX IF NOT EXISTS ix_ai_insights_status ON ai_insights(status);
CREATE INDEX IF NOT EXISTS ix_ai_insights_entity ON ai_insights(entity_type, entity_id);

-- ai_recommendations
CREATE TABLE IF NOT EXISTS ai_recommendations (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recommendation_type VARCHAR(30) NOT NULL
                        CHECK (recommendation_type IN (
                            'next_best_action','follow_up','deal_acceleration','customer_retention',
                            'expansion_opportunity','renewal_action'
                        )),
    entity_type         VARCHAR(30) NOT NULL DEFAULT '',
    entity_id           VARCHAR(64) NOT NULL DEFAULT '',
    title               VARCHAR(255) NOT NULL,
    detail              TEXT        NOT NULL DEFAULT '',
    priority            VARCHAR(10) NOT NULL DEFAULT 'medium',
    status              VARCHAR(10) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','dismissed','completed')),
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    dismissed_at        TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    completed_by        BIGINT REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_ai_recs_type   ON ai_recommendations(recommendation_type);
CREATE INDEX IF NOT EXISTS ix_ai_recs_status ON ai_recommendations(status);
CREATE INDEX IF NOT EXISTS ix_ai_recs_entity ON ai_recommendations(entity_type, entity_id);

-- ai_risk_scores
CREATE TABLE IF NOT EXISTS ai_risk_scores (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    risk_type       VARCHAR(20) NOT NULL
                    CHECK (risk_type IN (
                        'stalled_deal','at_risk_customer','low_engagement','missed_sla',
                        'forecast_variance','renewal_risk'
                    )),
    entity_type     VARCHAR(30) NOT NULL DEFAULT '',
    entity_id       VARCHAR(64) NOT NULL DEFAULT '',
    score           DOUBLE PRECISION NOT NULL DEFAULT 0,
    severity        VARCHAR(10) NOT NULL DEFAULT 'medium'
                    CHECK (severity IN ('low','medium','high','critical')),
    detail          JSONB       NOT NULL DEFAULT '{}',
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ai_risks_type   ON ai_risk_scores(risk_type);
CREATE INDEX IF NOT EXISTS ix_ai_risks_entity ON ai_risk_scores(entity_type, entity_id);

-- ai_engagement_scores
CREATE TABLE IF NOT EXISTS ai_engagement_scores (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type             VARCHAR(30) NOT NULL DEFAULT '',
    entity_id               VARCHAR(64) NOT NULL DEFAULT '',
    score                   DOUBLE PRECISION NOT NULL DEFAULT 0,
    email_activity_score    DOUBLE PRECISION NOT NULL DEFAULT 0,
    meeting_activity_score  DOUBLE PRECISION NOT NULL DEFAULT 0,
    task_completion_score   DOUBLE PRECISION NOT NULL DEFAULT 0,
    trend                   VARCHAR(10) NOT NULL DEFAULT 'stable'
                            CHECK (trend IN ('up','stable','down')),
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ai_engagement_entity ON ai_engagement_scores(entity_type, entity_id);

-- ai_briefings
CREATE TABLE IF NOT EXISTS ai_briefings (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    period          VARCHAR(20) NOT NULL DEFAULT '',
    sections        JSONB       NOT NULL DEFAULT '{}',
    generated_by    BIGINT REFERENCES users(id) ON DELETE SET NULL,
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ai_briefings_generated ON ai_briefings(generated_at);

-- ai_copilot_queries (usage log for Copilot Usage analytics)
CREATE TABLE IF NOT EXISTS ai_copilot_queries (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    query_type          VARCHAR(30) NOT NULL
                        CHECK (query_type IN (
                            'entity_summary','customer_summary','deal_summary','pipeline_summary',
                            'executive_summary','activity_summary'
                        )),
    entity_type         VARCHAR(30) NOT NULL DEFAULT '',
    entity_id           VARCHAR(64) NOT NULL DEFAULT '',
    user_id             BIGINT REFERENCES users(id) ON DELETE SET NULL,
    response_summary    TEXT        NOT NULL DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ai_copilot_type ON ai_copilot_queries(query_type);
CREATE INDEX IF NOT EXISTS ix_ai_copilot_created ON ai_copilot_queries(created_at);

END $$;
