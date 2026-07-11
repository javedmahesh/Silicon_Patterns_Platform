-- =====================================================================
-- 0042_microsoft_auth.sql — Microsoft Entra ID authentication
-- PostgreSQL / Supabase dialect. Requires 0041_password_auth.sql.
--
-- Replaces the first-party password sign-in path with Microsoft Entra ID (Azure
-- AD) OAuth (Authorization Code + PKCE, verified locally via the tenant's JWKS —
-- see backend/security.py::verify_microsoft_id_token). Adds users.microsoft_oid,
-- the immutable Entra object id, mirroring how users.google_sub was added for the
-- prior Google-SSO mechanism.
--
-- Additive only: no existing column/table is touched or dropped. password_hash and
-- must_change_password are left in place, unused, matching how google_sub was left
-- in place after the Google -> password swap.
-- =====================================================================

BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS microsoft_oid VARCHAR(255);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_microsoft_oid ON users(microsoft_oid);

COMMIT;
