# Security

Covers the P5.5 hardening (API key, CORS, rate limiting, Supabase) **and** the
multi-user **authentication / authorization** model (Microsoft Entra ID, app JWTs,
role-based access control).

## 1. Authentication — Microsoft Entra ID + app JWT (`backend/security.py`, `backend/services.py`)
- **Sign-in is Microsoft Entra ID (Azure AD).** The SPA signs the user in with MSAL
  (`@azure/msal-browser`/`@azure/msal-react`, Authorization Code + PKCE — a public
  client, no secret ever reaches the browser) and posts the resulting Microsoft ID
  token to `POST /auth/microsoft`. The backend verifies that token's signature
  locally against the tenant's published JWKS (`security.verify_microsoft_id_token`
  — `https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys`, no network
  round trip to Microsoft per sign-in beyond key caching) and checks issuer,
  audience, expiry. Only `@siliconpatterns.com` email claims are accepted, enforced
  server-side. The backend then mints its **own** short-lived HS256 **app JWT**
  (`SP_JWT_SECRET`, TTL `SP_JWT_TTL_HOURS`, default 12) exactly as before — Browser
  calls send `Authorization: Bearer <app-jwt>`, unrelated to the Microsoft token
  itself past that one exchange.
- **First sign-in for an unseen email** creates a **pending** account
  (`services.login_with_microsoft`) — an admin must approve it (`/admin/users/*`,
  the Administration page) before a second sign-in succeeds.
- **Initial administrator bootstrap:** the first Microsoft sign-in matching
  `SP_BOOTSTRAP_ADMIN_EMAIL` (default `admin@siliconpatterns.com`) is provisioned
  **active** `super_admin` immediately, skipping the pending queue. Once that
  account exists, later sign-ins never touch its role again — a deliberate later
  disable/demotion by another admin can't be silently reversed just by signing in.
  `SP_ADMIN_EMAILS` similarly auto-approves as `admin` (not `super_admin`) on first
  sign-in.
- **Dependencies (the auth seams, unchanged by the identity-provider swap):**
  `get_current_user` (valid app JWT → active user, else 401 — also backs
  `/auth/me`, `/auth/logout`, `/auth/refresh`); `require_admin` / `require_manager`
  / `require_super_admin` (role gates → 403); `require_principal` (the
  data-endpoint gate — a valid app JWT **or** the legacy `X-API-Key` for
  service/CI).
- **Legacy API key** still works for service/CI clients via `require_principal`
  (`SP_API_KEY`, sent as `X-API-Key`). Mint one with
  `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
- **Dev bypass** (`DEV_AUTH_BYPASS=true`, or neither `SP_API_KEY` nor Microsoft
  configured): the API runs **open** for local dev/tests and a one-time warning is
  logged. A **Dev Role Switcher** (frontend) sends `X-Dev-Role: admin|manager|member`
  to exercise RBAC against synthetic
  `betatesting{admin,manager,member}@siliconpatterns.com` identities. **Never
  available when `ENVIRONMENT=production`**, regardless of the above — the API
  refuses to start at all if production has no strong `SP_JWT_SECRET`, or no
  `MICROSOFT_TENANT_ID`/`MICROSOFT_CLIENT_ID` (`backend/main.py` lifespan). **At
  deployment:** set `SP_JWT_SECRET`, `MICROSOFT_TENANT_ID`/`MICROSOFT_CLIENT_ID`/
  `MICROSOFT_CLIENT_SECRET`, `VITE_MICROSOFT_CLIENT_ID`/`VITE_MICROSOFT_TENANT_ID`,
  `SP_BOOTSTRAP_ADMIN_EMAIL`, `SP_ADMIN_EMAILS` → bypass auto-off; then remove the
  switcher and synthetic users.

## 1a. Authorization — roles (RBAC)
Three roles (`config/enums.py::USER_ROLES`), hierarchical: **admin ⊃ manager ⊃ member**.
- **admin** — everything, incl. user management (`/admin/*`: change role, activate/
  deactivate).
- **manager** — lead assignment + the workload dashboard (`/assignments/*`), and
  **editing professional contacts**.
- **member** — own assigned leads + full read access to all intelligence data.

**Principle: restrictions gate administrative/management _actions_, not _visibility_
of intelligence.** Every authenticated user (incl. members) can read all companies,
leads, opportunities, decision makers, contacts, and analytics. Writes are gated:
assignment/user management = manager/admin; **professional-contact edits
(`PUT /decision-makers/{id}/contact`) = `require_manager`** (members get 403; they
still read via `GET`).

## 1b. Accounts — lifecycle, approval workflow, audit (`0021`)
Every account has a **status** (`pending → active`, plus `disabled`, `rejected`,
`deleted`); only `active` may obtain a session (`get_current_user`/login both gate
on it, so disabling takes effect on the **next request** — existing JWTs are
re-checked every call).
- **Registration + approval:** `POST /auth/register` creates the account as
  **pending** (no access) and an admin must **approve** (→active) or **reject** it.
  `SP_ADMIN_EMAILS` bootstrap as active admins so there is always an approver.
- **Admin user management** (`/admin/users*`, admin-only, backend-enforced):
  approve / reject / enable / disable / promote / demote / soft-delete, plus an
  **audit log** (`user_audit_events`) of every action incl. `login`. `login_count`
  + `last_login_at` are tracked per account.
- **Soft delete only** — "delete" sets status `deleted`, scrubs PII and anonymizes
  the email, but **keeps the row** for audit/FK integrity (no hard delete).
- **Lockout guards:** an admin cannot disable/demote/delete **their own** account
  or the **last active admin**.
- **Dev bypass is production-disabled:** it is auto-off whenever `SP_API_KEY` is set
  and `DEV_AUTH_BYPASS` is unset, and unconditionally off whenever
  `ENVIRONMENT=production` (startup aborts if production has no strong
  `SP_JWT_SECRET` — see `backend/main.py` lifespan). It exists only for local
  dev/tests.

## 1c. Professional contacts — privacy scope
`decision_makers` and `decision_maker_contacts` hold **PII**. The contacts feature is
**strictly professional**: work email, work phone, and notes only — **no personal
home address, personal email, or personal phone**. This is enforced in the
`ContactIn` schema (no such fields exist) and stated in the UI. Honor access control,
retention, and deletion-on-request (GDPR/DPDP) for this data.

## 2. CORS
- `CORS_ORIGINS` now defaults to the dev frontend (`http://localhost:5173`), **not `*`**.
- In production set it to your deployed frontend origin(s). Credentials are only
  enabled when the list is not `*` (per the CORS spec).

## 3. Supabase — rotate the anon key  *(LEGACY)*
> **Legacy:** decision makers now come from the **Apify Decision Maker Intelligence**
> engine (`decision_maker_intelligence` stage); the LinkedIn Supabase `candidates`
> source is **no longer part of the pipeline**. The adapter
> (`integration/ingestors/supabase_source.py`) and this guidance remain only for
> anyone still operating that legacy source.

The LinkedIn `candidates` table currently runs with **RLS disabled**, so the anon
key is effectively full read/write to anyone who has the URL+key (and that key was
exposed in a screenshot). Rotate it:
1. Supabase dashboard → **Project Settings → API → Project API keys → Roll** the
   `anon` key (and the `service_role` key if it was ever exposed).
2. Update the recruiter app's stored key (its Settings modal / its env) and the
   backend's `SP_SUPABASE_*` env vars.
3. Never commit keys; never put the `service_role` key in any browser bundle.

## 4. Enable RLS + service-role adapter  *(LEGACY — see §3 note)*
- Apply `docs/supabase_rls.sql` to turn on row-level security on `candidates`.
- The **server-side adapter** (`integration/ingestors/supabase_source.py`) reads
  via `config/supabase.py::load_supabase_credentials`, which now **prefers a
  service-role key** (`SP_SUPABASE_SERVICE_KEY`) over the anon key — the service
  role bypasses RLS, so ingestion keeps working once RLS is on. Keep that key on
  the server only.
- Trade-off (the recruiter app is not modified): strict RLS that blocks anon
  writes will break the app's write path. Interim posture: anon **read-only**
  policy + service-role for the backend; longer term, move the app to
  authenticated writes. See the SQL for both options.

## 5. Secrets & transport
- `DATABASE_URL`, `SP_API_KEY`, `SP_SUPABASE_*` via env / a secret manager — never
  in the repo. `.env` is gitignored. `backend/database.py` masks credentials in logs.
- Serve over TLS; disable FastAPI debug in prod; run `pip-audit` / `npm audit`.
- `decision_makers` hold PII — enforce access control, retention, and deletion.
- **Outreach module (`outreach/`)** keeps its **own** secrets, never in the repo: `outreach/.env.local`
  is gitignored (`.env.example` ships placeholders only). Its `SUPABASE_SERVICE_ROLE_KEY` **bypasses RLS**
  — server-only (the `server-only` import keeps it out of client bundles); the shared-mailbox Gmail refresh
  token is stored **AES-256-GCM encrypted** (`TOKEN_ENCRYPTION_KEY`), and the reply-sync cron is gated by
  `CRON_SECRET`. *Note:* the incoming package shipped a real service-role key in **both** `.env.local` and
  `.env.example`; both were sanitized on vendoring. The demo Supabase project it referenced has since been
  deleted (DNS NXDOMAIN), so those keys are now inert — but treat any service-role key as live and rotate
  it if it ever lands in a shared file or commit.

## 6. Rate limiting
- Set `SP_RATE_LIMIT_PER_MINUTE` (e.g. `120`; the bare `RATE_LIMIT_PER_MINUTE` is also
  accepted) to cap requests per minute per client IP; `0` (default) disables it. Over the limit → `429` with a `Retry-After` header; `/health`
  is always exempt.
- It is an **in-memory, per-process** fixed window (`backend/main.py`). With multiple API
  instances, also enforce a limit at the gateway / load balancer or back it with a shared
  store (e.g. Redis). It complements — does not replace — the API-key gate.
