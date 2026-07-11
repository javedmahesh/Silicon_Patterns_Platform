# Deployment architecture

How the platform runs in production: an always-on **website**, a **dedicated database**, and a
**scheduled refresh** that fetches data twice a day. The key principle — a scheduler is a
*trigger*, not a *runtime* — so the heavy pipeline runs on a real job runner (GitHub Actions),
not inside Supabase/Vercel cron.

```
 ┌──────────────────────────┐        ┌─────────────────────────┐        ┌──────────────────────┐
 │  GitHub Actions (cron)    │  write │   Master Postgres        │  read  │  Vercel              │
 │  09:00 & 21:00 · run all  ├───────▶│   (dedicated Supabase /   │◀───────┤  frontend (+ read    │
 │  engines→ingest→score     │        │    Neon)                 │        │  API)  — 24/7        │
 └──────────────────────────┘        └─────────────────────────┘        └──────────────────────┘
        the only "fetch"                 single source of truth              what users open
```

| Component | Runs on | Always on? | Notes |
|---|---|---|---|
| Frontend | Vercel | Yes | Static Vite build; `frontend/vercel.json` |
| Read API (FastAPI) | Managed host *or* Vercel | Yes (on-demand) | Read-only over the DB |
| Master DB | Dedicated Postgres (Supabase/Neon) | Yes | The platform's own database |
| Refresh pipeline | GitHub Actions (cron) | No (ephemeral job) | `.github/workflows/refresh.yml` |

---

## 1. Master database (dedicated Postgres)

- Create a **dedicated** Postgres — a Supabase project (or Neon) that is the platform's own master
  database (all 22 tables).
- Connection string → `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db`. On Supabase use
  the **session pooler** host (`...pooler.supabase.com:5432`) — the direct host is IPv6-only.
- **One-time:** apply the migrations in order (`0001`–`0016` — the data tables plus the
  multi-user/CRM tables `users`/`lead_assignments`/`lead_assignment_events`/`company_notes`/
  `decision_maker_contacts`, lead-score coverage/confidence, `pg_trgm`, GiST index, the
  `leadership_signals` (`0012`) and `engagement_recommendations` (`0013`) derivation tables, the
  `lead_reviews`/`lead_review_events` human-review tables (`0014`), the review→score adjustment
  columns (`0015`), plus the shared `opportunities.company_news_signal` column (`0016`)):
  ```bash
  for f in master_db/migrations/0*.sql; do psql "$DATABASE_URL" -f "$f"; done
  ```
  (or paste each file into the Supabase SQL editor). Do **not** use `scripts/validate_postgres.py`
  against prod — it truncates.
- First data load: the first refresh run populates it; or import your local `master_local.db`.

## 2. Frontend (Vercel)

- Project root directory → `frontend`. Framework preset → Vite. Build `npm run build`, output `dist`
  (already encoded in `frontend/vercel.json`).
- Environment variables (Vercel → Settings → Environment Variables):
  - `VITE_API_BASE_URL` → the deployed API origin, e.g. `https://api.yourhost.com` (no trailing slash).
  - Sign-in is Microsoft Entra ID (`LoginPage.tsx`, MSAL) — set `VITE_MICROSOFT_CLIENT_ID` and
    `VITE_MICROSOFT_TENANT_ID` from the App Registration. The deployed origin must be added as a
    redirect URI on that App Registration (Single-Page Application platform).
  - `VITE_API_KEY` → only for service/CI clients if the API enforces `SP_API_KEY` (not used by regular users).
  - *(Outreach needs no frontend env — it's a native part of this SPA. See §8.)*
- Redeploys on every push; SPA deep links work via the `vercel.json` rewrite.

## 3. Read API (FastAPI)

The API is read-only over the DB, so it ships as a small container (no engines). Deploy artifacts
are included: **`Dockerfile`** + **`render.yaml`**. It runs the *exact* app you run locally —
`uvicorn backend.main:app` — with no serverless adapter.

**Recommended — managed container host** (Render / Railway / Fly / Cloud Run):
1. **Render:** New → **Blueprint** → point at this repo (uses `render.yaml`). Any other host: build
   the `Dockerfile` (`docker build -t sp-api . && docker run -p 8000:8000 --env-file .env sp-api`).
2. Set env (secrets):
   - `DATABASE_URL` → `postgresql+psycopg://…` (Supabase **session pooler** host).
   - **Auth (Microsoft Entra ID) — required in prod so the dev bypass is OFF:**
     - `ENVIRONMENT` → `production`. Hard-disables the dev bypass and refuses to start at
       all unless `SP_JWT_SECRET` is a strong (32+ char) value AND `MICROSOFT_TENANT_ID`/
       `MICROSOFT_CLIENT_ID` are set — there is no implicit open-API fallback, and no other
       sign-in path in production.
     - `SP_JWT_SECRET` → strong random secret signing this app's session JWTs (≥32 bytes).
     - `MICROSOFT_TENANT_ID` / `MICROSOFT_CLIENT_ID` / `MICROSOFT_CLIENT_SECRET` → from the
       Entra App Registration (Single-Page Application platform, Authorization Code + PKCE).
       The backend verifies Microsoft ID tokens locally against the tenant's JWKS — the
       client secret is accepted for completeness but isn't required by that verification.
     - `SP_BOOTSTRAP_ADMIN_EMAIL` → the initial administrator: this email is provisioned
       active `super_admin` the first time it signs in via Microsoft
       (`services.login_with_microsoft`), skipping the pending queue.
     - `SP_ADMIN_EMAILS` → comma-separated seed admins, e.g. `you@siliconpatterns.com`
       (auto-approved on first sign-in).
     - `ALLOWED_EMAIL_DOMAIN` → optional; defaults to `siliconpatterns.com`.
     - `SP_JWT_TTL_HOURS` → optional; session length, default `12`.
     - ⚠️ Leave `DEV_AUTH_BYPASS` **unset/false** in prod. The bypass is on whenever
       `SP_API_KEY` is unset — configuring it (or deploying with `ENVIRONMENT=production`)
       turns the bypass off.
   - `SP_API_KEY` → optional, for service/CI clients only (sent as `X-API-Key`); regular
     users don't need it.
   - `CORS_ORIGINS` → a **JSON list**, e.g. `["https://your-frontend.vercel.app"]`
     (pydantic-settings parses list envs as JSON — *not* comma-separated).
   - `SP_RATE_LIMIT_PER_MINUTE` → e.g. `120` (already set in `render.yaml`).
   - `ANALYTICS_CACHE_SECONDS` → optional; analytics `Cache-Control` max-age (default `300`).
3. Health check is `/health`. Note the service URL.
4. In Vercel, set the frontend's **`VITE_API_BASE_URL`** to that URL and **`VITE_API_KEY`** to the
   same `SP_API_KEY`. Redeploy the frontend.

**Alternative — all-on-Vercel (Python serverless):** possible (the API is fast DB reads) but needs
an `api/` ASGI handler, serverless DB pooling (Supabase **transaction** pooler + NullPool), and path
rewrites — more footguns, and not testable from here. The container path above is the tested,
reliable default; ask if you specifically want the serverless variant and I'll scaffold it.

> The API never runs the pipeline and never needs the engines — it only reads the DB. The image
> excludes the engines, `master_local.db`, tests, and the frontend (see `.dockerignore`).

## 4. Refresh pipeline (GitHub Actions) — the scheduled job

`.github/workflows/refresh.yml` runs `sp-platform run all` twice daily and writes to the Postgres.

- **Schedule:** `cron: "0 9,21 * * *"` — **UTC**. Adjust for your timezone (09:00/21:00 **IST** =
  `"30 3,15 * * *"`).
- **Repo secrets** (Settings → Secrets and variables → Actions):
  | Secret | Purpose |
  |---|---|
  | `DATABASE_URL` | the dedicated master Postgres |
  | `APIFY_API_TOKEN` | Decision Maker Intelligence engine (Apify) |
  | `ENGINES_TOKEN` | (only if checking the engines out from private repos) |
- **Engines must be present** for live crawling. The workflow expects them under `$SP_ENGINES_DIR`
  (`./engines` in CI). Either **vendor** the four engine folders into the repo, or **check them out**
  as extra steps (template included in the workflow). `config/sources.py` honors `SP_ENGINES_DIR`.
- **Idempotent + logged:** re-runs upsert (no duplicates); every stage is recorded in `pipeline_runs`
  (including failures). A `concurrency` group prevents two refreshes overlapping.
- **Failure alerting:** a final `if: failure()` step opens (or comments on) a **deduped GitHub issue**
  labeled `pipeline-failure` using the built-in `GITHUB_TOKEN` (the job declares `issues: write`) — so a
  broken refresh is visible without watching the Actions tab. Prefer Slack/email? A commented
  `SLACK_WEBHOOK_URL` variant is in the workflow. Note: this fires on a **process-level** failure (a step
  exited non-zero); stage failures the orchestrator catches and only logs to `pipeline_runs` won't trip
  it — watch `/pipeline/status` (or `orchestrator.cli runs`) for those.
- **Caveat:** shared CI IPs sometimes get bot-blocked by career sites (an engine limitation). If
  crawling is unreliable from Actions, move the run to a **scheduled container job** (Cloud Run Jobs,
  Render Cron, Fly Machines) — same command, friendlier IPs. No always-on VM either way.
- **Supabase Cron as dispatcher (optional):** if you'd rather Supabase own the schedule, a `pg_cron`
  + `pg_net` job can call GitHub's `workflow_dispatch` API to trigger this workflow. Supabase still
  can't *run* the pipeline — it only fires the trigger.

## 5. Data freshness & the "last successful refresh" safeguard

Requirement: *the frontend should always reflect the most recent **successfully** refreshed data.*

What's implemented:
- **`GET /pipeline/status`** reports `last_successful_refresh` (the time the last full pipeline
  completed — i.e. the last successful `scoring` stage), plus whether the latest run failed or is
  in progress.
- The **connection badge** anchors its "Data as of …" to that timestamp and shows a **warning** when
  the latest run failed or is mid-flight — so users always see when the data was last cleanly
  refreshed, and are told if they're looking at a partial/failed run.
- **Idempotent upserts** mean a re-run never duplicates; the next scheduled run self-heals a partial
  one. **`pipeline_runs`** logs every outcome. The **concurrency guard** prevents overlapping writes.
- **Cached reads track the refresh:** `/analytics/summary` + `/analytics/coverage` tag responses with an
  **ETag keyed on `last_successful_refresh`** and memoize per version. Between refreshes, clients get
  instant (or 304) responses; the moment a refresh completes the key advances and everyone revalidates to
  fresh data — caching never serves data older than the last good refresh. Tune via `ANALYTICS_CACHE_SECONDS`.

Known limitation (documented, not a bug): writes commit per stage, so *during* a run the DB is
briefly mixed. We intentionally do **not** wrap the whole multi-minute pipeline in one transaction
(long transactions hold locks/bloat). For a **strict** atomic snapshot (never serve mixed data), the
recommended future enhancement is a **staging-schema swap**: load into a staging schema, then swap
it in atomically. Given the twice-daily cadence and the freshness signaling above, eventual
consistency is acceptable for now.

## 6. One-time setup checklist
1. Create the dedicated Postgres; apply migrations (§1).
2. Deploy the API (host or Vercel); set its env (§3).
3. Deploy the frontend on Vercel; set `VITE_API_BASE_URL` (§2).
4. Add the GitHub repo secrets; make the engines available; (optionally) tweak the cron timezone (§4).
5. Trigger the workflow once manually (Actions → Refresh pipeline → Run workflow) to seed data, then
   confirm the site shows it and the badge reads a fresh "Data as of …".
6. *(Outreach ships with the platform — no separate deploy. See §8 for mail mode.)*

## 7. Operational runbook
- **Manual refresh:** Actions → *Refresh pipeline* → *Run workflow* (toggle `run_engine` off for an
  ingest-only/score-only run).
- **Check health/history:** `GET /pipeline/health`, `GET /pipeline/status`, `GET /pipeline/runs`
  (or `python -m orchestrator.cli status` / `runs` against `DATABASE_URL`).
- **Recover a failed run:** `python -m orchestrator.cli run all --resume` (re-runs only the stages
  that didn't succeed) or `rerun <component>`.

## 8. Outreach module (native — ships with the platform)
Outreach is **not** a separate deploy. It is part of the same FastAPI backend, React SPA and master DB:
- **DB:** migration `0020_outreach.sql` creates `outreach_leads` / `outreach_templates` /
  `outreach_messages` / `outreach_activities` in the master database (applied with the other migrations).
- **Backend:** routes under `/outreach/*` (already registered); reuses companies / decision_makers /
  lead_scores / engagement_recommendations / users and the platform's Google-SSO + roles.
- **Mail:** `OUTREACH_MAIL_MODE` (default `mock` — drafts/approvals/sends/replies simulated, no creds).
  For live email set `OUTREACH_MAIL_MODE=gmail` and provide Google OAuth credentials + a deployed origin,
  then implement the `GmailSender` in `backend/outreach_mail.py` (interface is in place).
- **Seed:** after deploy, `POST /outreach/leads/sync` (admin/manager) qualifies the top `lead_scores`
  companies into the pipeline.
