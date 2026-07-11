-- Migration 0030: Enterprise CRM Phase 7 — Custom Objects, Forms & No-Code Platform
-- Tables: custom_objects, custom_fields, custom_forms, custom_records,
--         custom_record_audit, custom_data_jobs

DO $$ BEGIN

-- custom_objects
CREATE TABLE IF NOT EXISTS custom_objects (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    api_name        VARCHAR(100) NOT NULL UNIQUE,
    description     TEXT NOT NULL DEFAULT '',
    icon            VARCHAR(50)  NOT NULL DEFAULT '',
    status          VARCHAR(20)  NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft','active','archived')),
    version         INTEGER      NOT NULL DEFAULT 1,
    created_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_custom_objects_status ON custom_objects(status);

-- custom_fields
CREATE TABLE IF NOT EXISTS custom_fields (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    object_id       BIGINT NOT NULL REFERENCES custom_objects(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    api_name        VARCHAR(100) NOT NULL,
    field_type      VARCHAR(20)  NOT NULL
                    CHECK (field_type IN (
                        'text','long_text','integer','decimal','boolean','date','datetime',
                        'email','url','phone','currency','picklist','multiselect','lookup'
                    )),
    is_required     BOOLEAN      NOT NULL DEFAULT false,
    default_value   JSONB,
    validation      JSONB        NOT NULL DEFAULT '{}',
    picklist_options JSONB       NOT NULL DEFAULT '[]',
    lookup_object_id BIGINT REFERENCES custom_objects(id) ON DELETE SET NULL,
    display_order   INTEGER      NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (object_id, api_name)
);

CREATE INDEX IF NOT EXISTS ix_custom_fields_object ON custom_fields(object_id);

-- custom_forms
CREATE TABLE IF NOT EXISTS custom_forms (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    object_id       BIGINT NOT NULL REFERENCES custom_objects(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    layout          JSONB        NOT NULL DEFAULT '{}',
    is_default      BOOLEAN      NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_custom_forms_object ON custom_forms(object_id);

-- custom_records
CREATE TABLE IF NOT EXISTS custom_records (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    object_id       BIGINT NOT NULL REFERENCES custom_objects(id) ON DELETE CASCADE,
    data            JSONB        NOT NULL DEFAULT '{}',
    created_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_custom_records_object ON custom_records(object_id);

-- custom_record_audit
CREATE TABLE IF NOT EXISTS custom_record_audit (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    record_id       BIGINT NOT NULL REFERENCES custom_records(id) ON DELETE CASCADE,
    action          VARCHAR(10)  NOT NULL
                    CHECK (action IN ('created','updated','deleted')),
    changed_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    field_changes   JSONB        NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_custom_record_audit_record ON custom_record_audit(record_id);

-- custom_data_jobs (import + export, one shared table)
CREATE TABLE IF NOT EXISTS custom_data_jobs (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    object_id       BIGINT NOT NULL REFERENCES custom_objects(id) ON DELETE CASCADE,
    job_type        VARCHAR(10)  NOT NULL
                    CHECK (job_type IN ('import','export')),
    status          VARCHAR(20)  NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','running','completed','failed')),
    total_rows      INTEGER      NOT NULL DEFAULT 0,
    success_count   INTEGER      NOT NULL DEFAULT 0,
    error_count     INTEGER      NOT NULL DEFAULT 0,
    errors          JSONB        NOT NULL DEFAULT '[]',
    created_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_custom_data_jobs_object ON custom_data_jobs(object_id);

END $$;
