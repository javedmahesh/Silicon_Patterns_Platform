-- 0026_collaboration.sql  Enterprise CRM Phase 3: Team Collaboration
-- Mirrors: CrmAssignment / CrmAssignmentHistory / CrmComment / CrmNotification / CrmSavedView

-- -----------------------------------------------------------------------
-- crm_assignments
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_assignments (
    id          SERIAL PRIMARY KEY,
    entity_type VARCHAR(20)  NOT NULL
                    CHECK (entity_type IN ('deal','campaign','opportunity','task','meeting')),
    entity_id   VARCHAR(64)  NOT NULL,
    user_id     INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        VARCHAR(20)  NOT NULL DEFAULT 'assignee'
                    CHECK (role IN ('owner','assignee','reviewer','manager','watcher')),
    assigned_by INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    note        TEXT         NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (entity_type, entity_id, user_id, role)
);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='crm_assignments' AND indexname='ix_crm_assignments_user') THEN
        CREATE INDEX ix_crm_assignments_user   ON crm_assignments(user_id);
        CREATE INDEX ix_crm_assignments_entity ON crm_assignments(entity_type, entity_id);
    END IF;
END $$;

-- -----------------------------------------------------------------------
-- crm_assignment_history
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_assignment_history (
    id          SERIAL PRIMARY KEY,
    entity_type VARCHAR(20)  NOT NULL,
    entity_id   VARCHAR(64)  NOT NULL,
    user_id     INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    role        VARCHAR(20)  NOT NULL DEFAULT 'assignee',
    action      VARCHAR(20)  NOT NULL
                    CHECK (action IN ('assigned','reassigned','removed','role_changed')),
    changed_by  INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    detail      TEXT         NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='crm_assignment_history' AND indexname='ix_assign_history_entity') THEN
        CREATE INDEX ix_assign_history_entity ON crm_assignment_history(entity_type, entity_id);
        CREATE INDEX ix_assign_history_user   ON crm_assignment_history(user_id);
    END IF;
END $$;

-- -----------------------------------------------------------------------
-- crm_comments
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_comments (
    id          SERIAL PRIMARY KEY,
    entity_type VARCHAR(20)  NOT NULL
                    CHECK (entity_type IN ('deal','campaign','opportunity','task','meeting')),
    entity_id   VARCHAR(64)  NOT NULL,
    author_id   INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    body        TEXT         NOT NULL DEFAULT '',
    mentions    JSONB        NOT NULL DEFAULT '[]',
    parent_id   INTEGER      REFERENCES crm_comments(id) ON DELETE CASCADE,
    is_edited   BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='crm_comments' AND indexname='ix_crm_comments_entity') THEN
        CREATE INDEX ix_crm_comments_entity ON crm_comments(entity_type, entity_id);
        CREATE INDEX ix_crm_comments_author ON crm_comments(author_id);
        CREATE INDEX ix_crm_comments_parent ON crm_comments(parent_id);
    END IF;
END $$;

-- -----------------------------------------------------------------------
-- crm_notifications
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_notifications (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notif_type  VARCHAR(30)  NOT NULL
                    CHECK (notif_type IN (
                        'assignment','deal_moved','campaign_update','reply_received',
                        'meeting_scheduled','task_due','mention','approval_needed','comment'
                    )),
    title       VARCHAR(255) NOT NULL DEFAULT '',
    body        TEXT         NOT NULL DEFAULT '',
    entity_type VARCHAR(20),
    entity_id   VARCHAR(64),
    is_read     BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='crm_notifications' AND indexname='ix_crm_notifs_user_unread') THEN
        CREATE INDEX ix_crm_notifs_user_unread ON crm_notifications(user_id, is_read);
        CREATE INDEX ix_crm_notifs_entity      ON crm_notifications(entity_type, entity_id);
    END IF;
END $$;

-- -----------------------------------------------------------------------
-- crm_saved_views
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crm_saved_views (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    entity_type VARCHAR(20)  NOT NULL
                    CHECK (entity_type IN ('deals','campaigns','contacts','opportunities')),
    owner_id    INTEGER      REFERENCES users(id) ON DELETE CASCADE,
    is_shared   BOOLEAN      NOT NULL DEFAULT FALSE,
    filters     JSONB        NOT NULL DEFAULT '{}',
    sort_by     VARCHAR(64)  NOT NULL DEFAULT '',
    sort_dir    VARCHAR(4)   NOT NULL DEFAULT 'desc',
    columns     JSONB        NOT NULL DEFAULT '[]',
    grouping    VARCHAR(64)  NOT NULL DEFAULT '',
    search      VARCHAR(255) NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='crm_saved_views' AND indexname='ix_crm_views_owner') THEN
        CREATE INDEX ix_crm_views_owner  ON crm_saved_views(owner_id);
        CREATE INDEX ix_crm_views_shared ON crm_saved_views(is_shared);
    END IF;
END $$;
