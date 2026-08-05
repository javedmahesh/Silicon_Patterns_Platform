-- =====================================================================
-- 0056_notification_deliveries.sql — per-recipient notification delivery log
-- PostgreSQL / Supabase dialect. No prerequisites beyond a fresh schema.
--
-- Phase 1 of the platform notification framework (backend/notifications).
-- pipeline_executions already carries a RUN-LEVEL rollup (notification_status /
-- notification_detail / notified_count); this table is the per-recipient audit
-- behind it: who was notified, on which channel, by which provider, how many
-- attempts it took, and the error if it failed.
--
-- Deliberately channel-neutral so Teams / Slack / webhook / in-app deliveries land
-- here too without another migration — `channel` and `provider` are free strings.
--
-- run_id is intentionally NOT a foreign key to pipeline_executions: a failure
-- notification can be emitted for a run that crashed before its execution row was
-- written, and a delivery record must outlive run-history pruning.
--
-- Additive only. Nothing reads this table on the hot path; the scheduler never
-- blocks on it, and a write failure here is caught and never fails a run.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS notification_deliveries (
    id          bigserial PRIMARY KEY,
    run_id      varchar(80)  NOT NULL DEFAULT '',
    event_type  varchar(40)  NOT NULL DEFAULT 'run_summary',
    channel     varchar(20)  NOT NULL DEFAULT 'email',
    provider    varchar(40)  NOT NULL DEFAULT '',
    recipient   varchar(320) NOT NULL DEFAULT '',
    audience    varchar(10)  NOT NULL DEFAULT 'all',
    status      varchar(20)  NOT NULL DEFAULT 'pending',
    attempts    integer      NOT NULL DEFAULT 0,
    error       text         NOT NULL DEFAULT '',
    created_at  timestamptz  NOT NULL DEFAULT now()
);

ALTER TABLE notification_deliveries DROP CONSTRAINT IF EXISTS ck_notif_delivery_status;
ALTER TABLE notification_deliveries ADD CONSTRAINT ck_notif_delivery_status
    CHECK (status IN ('pending','sent','failed','skipped','logged'));

CREATE INDEX IF NOT EXISTS ix_notif_delivery_run     ON notification_deliveries (run_id);
CREATE INDEX IF NOT EXISTS ix_notif_delivery_created ON notification_deliveries (created_at);
CREATE INDEX IF NOT EXISTS ix_notif_delivery_status  ON notification_deliveries (status);

COMMIT;
