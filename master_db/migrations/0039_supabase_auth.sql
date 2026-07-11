-- Migration 0039: Supabase Auth support.
--
-- Adds users.google_sub (the immutable Google subject id, sourced from the Supabase
-- session's user_metadata.provider_id/.sub for a Google-provider identity, or the
-- legacy direct-Google path's own ID-token `sub`) so login can prefer this over email
-- once populated -- email can change at the identity provider, this can't.
--
-- Nullable: every pre-existing row predates this column. A plain UNIQUE index (not a
-- table-level UNIQUE constraint) is used so multiple NULLs are unambiguously allowed --
-- Postgres already treats NULL as distinct from NULL under a unique index, this is just
-- the more common idiom for "unique when present".

DO $$ BEGIN

ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_sub ON users(google_sub);

END $$;
