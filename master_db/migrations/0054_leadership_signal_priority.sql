-- =====================================================================
-- 0054_leadership_signal_priority.sql — geography + priority_tier on leadership_signals
-- PostgreSQL / Supabase dialect. Requires 0012_leadership_signals.sql.
--
-- News phase 2 (leadership & decision-maker movement): a text-derived location signal
-- (India-city aware — Bengaluru, Hyderabad, Noida, Chennai, Pune, Gujarat, or generic
-- "India"; empty when nothing recognizable) and the reusable priority tier it drives
-- together with the signal's company tier (leadership_signals/priority.py):
--   startup/scaleup company            -> high (globally relevant movement matters early)
--   India-relevant movement            -> high, regardless of company size
--   established/incumbent, non-India   -> low  (kept, deprioritized — never discarded)
--   unknown company tier, no India hit -> medium
-- Additive only; both columns default so every existing row and feeder is unaffected.
-- =====================================================================

BEGIN;

ALTER TABLE leadership_signals ADD COLUMN IF NOT EXISTS geography     varchar(120) NOT NULL DEFAULT '';
ALTER TABLE leadership_signals ADD COLUMN IF NOT EXISTS priority_tier varchar(10)  NOT NULL DEFAULT 'medium';

ALTER TABLE leadership_signals DROP CONSTRAINT IF EXISTS ck_ldr_priority;
ALTER TABLE leadership_signals ADD CONSTRAINT ck_ldr_priority
    CHECK (priority_tier IN ('high','medium','low'));

CREATE INDEX IF NOT EXISTS ix_ldr_priority ON leadership_signals (priority_tier);

COMMIT;
