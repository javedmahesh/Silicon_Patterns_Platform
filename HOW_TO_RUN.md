# HOW TO RUN — Silicon Patterns Platform

A complete guide to running the Silicon Patterns lead-generation platform locally: from a fresh clone through the full data pipeline (four engines → master database → lead scoring) to the website (FastAPI backend + React frontend) and production deployment.

> **Platform:** Python 3.13 backend + SQLAlchemy + FastAPI; React 18 + TypeScript + Vite frontend; PostgreSQL (prod) / SQLite (dev).

---

## 0. Prerequisites

| Tool | Min version | Notes |
|---|---|---|
| Python | 3.11 (3.13 tested) | for pipeline, scoring, API, orchestrator |
| Node.js + npm | 18 (24 tested) | for frontend website build |
| PostgreSQL | 12+ | production only; dev uses local SQLite `master_local.db` |
| Git | any | to clone the repo |

**Platform:** Windows PowerShell, macOS/Linux bash/zsh. Commands below are PowerShell; on macOS/Linux, replace `.\.venv\Scripts\Activate.ps1` with `source .venv/bin/activate`.

---

## 1. One-time setup (fresh clone)

```powershell
# Clone the repo
git clone <repo-url>
cd Silicon_Patterns_Platform

# Create and activate a Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate          # macOS/Linux

# Install backend + pipeline dependencies
pip install -r requirements.txt

# Optional: install with the sp-platform CLI command (instead of python -m orchestrator.cli ...)
# pip install -e .

# Install frontend dependencies
cd frontend
npm install
cd ..
```

**Expected output:**
- Python venv created and activated (prompt shows `(.venv)`)
- pip install completes without errors (SQLAlchemy, FastAPI, Typer, pytest, etc.)
- npm install completes; `frontend/node_modules/` exists
- Master DB already ships with `master_local.db` (~5.8 MB) — no migration needed to start

---

## 2. Environment configuration

### Create `.env` from `.env.example`

```powershell
cp .env.example .env
# Edit .env in your editor
```

### Environment variables (required vs optional)

#### **Required for dev (leave these defaults)**

- `APIFY_API_TOKEN` — leave empty locally (the `decision_maker_intelligence` stage will skip)
- Everything else is **optional** for local dev; see below

#### **Optional for dev**

- `DATABASE_URL` — leave unset to use local SQLite (`master_local.db`). Set only when testing against Postgres.
- `SP_API_KEY` — leave unset (API is open in dev). Set in production to gate the API.
- `CORS_ORIGINS` — leave unset (dev defaults to localhost). Set in production to restrict origins.

#### **For production (deploy time)**

- `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db` — the master Postgres (Supabase session pooler).
- `SP_BOOTSTRAP_ADMIN_EMAIL` — initial administrator bootstrap (see §10).
- `MICROSOFT_TENANT_ID` / `MICROSOFT_CLIENT_ID` / `MICROSOFT_CLIENT_SECRET` — Entra App Registration (see §10).
- `SP_JWT_SECRET` — strong random string (≥32 bytes) to sign session JWTs.
- `SP_ADMIN_EMAILS` — comma-separated seed admins (e.g., `you@siliconpatterns.com,manager@siliconpatterns.com`).
- `SP_API_KEY` — service/CI clients send this as `X-API-Key` header.
- `CORS_ORIGINS=["https://your-frontend.example"]` — JSON list (not comma-separated; pydantic parses it).

#### **Apify (Decision Maker Intelligence engine)**

- `APIFY_API_TOKEN` — your Apify API token (only set to run the `decision_maker_intelligence` stage with live data).
- `APIFY_ACTOR_ID` — optional override; defaults to the Apify Decision Maker Intelligence actor ID (see `config/apify.py`).

#### **Gmail (Outreach module mail mode)**

- `OUTREACH_MAIL_MODE` — default `mock` (all email actions are simulated). Set to `gmail` for real email (deploy-time only; needs OAuth + origin).

#### **Legacy (unused)**

- `SP_SUPABASE_*` — LinkedIn source deprecated; ignored (kept only for backward compatibility).

---

## 3. Database & migrations

### Local SQLite (dev default)

The repo ships a pre-populated `master_local.db` with:
- 122 companies
- 50 opportunities (43 Blog + 3 Annual Lists + 4 Company News)
- 188 decision makers (from Apify)
- 188 jobs (from Career Scraper)
- 122 lead scores (grades: A+ 17 / A 13 / B 10 / C 82)
- Full audit trails + leadership signals

**No migration step is needed** — just run the platform.

#### Rebuild the local DB from fixtures (if needed)

If you want a fresh DB from scratch:

```powershell
python scripts/seed_master_db.py                    # rebuild master_local.db (idempotent)
python scripts/seed_master_db.py --db custom.db    # build a different file
```

This populates the DB with companies, opportunities (incl. annual lists & company news), demand signals, decision makers, lead scores, leadership signals, and engagement recommendations — from bundled fixtures in `tests/fixtures/`.

#### Production PostgreSQL (Supabase / Neon)

Create a dedicated Postgres project, then apply all 55 migrations:

```powershell
# Set the database URL
$env:DATABASE_URL = "postgresql+psycopg://user:pass@host:5432/silicon_patterns"

# Apply migrations in order (0001–0055)
for ($i = 1; $i -le 55; $i++) {
    $num = "{0:D4}" -f $i
    $file = "master_db/migrations/${num}_*.sql"
    psql $env:DATABASE_URL -f $file
}
# Or paste each file manually in the Supabase / Neon SQL editor

# Do NOT run scripts/validate_postgres.py against production — it truncates tables
```

**Verification:** `psql $env:DATABASE_URL -c "\dt"` lists 128 tables (data layer + multi-user layer + CRM/outreach/ML layers).

---

---

## 3a. Scheduled-run email notifications (optional)

After every **scheduled** run the platform emails an HTML report to every **approved,
active** user. Pending-approval, disabled, rejected and deleted accounts are never
notified. A delivery failure is recorded in `notification_deliveries` and never fails
the pipeline.

The scheduler does not talk to a mail server — it hands the finished run to the
notification service, which renders the report and passes it to the configured
provider (`backend/notifications/`). Swapping Gmail for Teams/Slack later is a new
provider plus one environment variable; no scheduler change.

**Gmail setup** (any RFC-compliant SMTP server works by changing host/port):

1. Enable 2-Step Verification on the sending Google account.
2. Google Account -> Security -> **App passwords** -> generate one for "Mail".
   Gmail rejects the account password for SMTP; you must use the 16-character app
   password.
3. Set these on the host (Railway -> Variables). Never commit them:

```powershell
$env:EMAIL_PROVIDER      = "gmail"
$env:EMAIL_FROM          = "javedmahesh1@gmail.com"
$env:EMAIL_DISPLAY_NAME  = "Silicon Patterns"
$env:SMTP_HOST           = "smtp.gmail.com"
$env:SMTP_PORT           = "587"
$env:SMTP_USERNAME       = "javedmahesh1@gmail.com"
$env:SMTP_PASSWORD       = "<16-char app password>"
$env:FRONTEND_URL        = "https://your-app.vercel.app"
```

Until `SMTP_PASSWORD` is set the provider reports "not configured" and every run is
recorded as `logged` — built and counted, but not delivered. That is the safe default,
not an error.

| Variable | Default | Purpose |
|---|---|---|
| `ENABLE_NOTIFICATIONS` | `true` | Master switch for every channel |
| `NOTIFICATION_PROVIDER` / `EMAIL_PROVIDER` | `gmail` | Registered provider (`email`, `gmail`) |
| `NOTIFICATION_RETRY_COUNT` | `3` | Total send attempts (1 = no retry) |
| `FRONTEND_URL` | *(empty)* | "Open Silicon Patterns" button; hidden when blank |
| `BRAND_NAME` | `Silicon Patterns` | Subject line, header, footer |
| `BRAND_LOGO_URL` | *(empty)* | Absolute URL; blank renders a built-in monogram |
| `SMTP_USE_STARTTLS` / `SMTP_USE_SSL` | `true` / `false` | Port 587 vs implicit TLS on 465 |

A failed run notifies in two versions from the same payload: **admins** get the
exception and per-stage errors, **everyone else** gets a concise notice — diagnostics
can carry connection strings, so they never go to the whole user base.

Check who was notified for a run:

```
GET /scheduler/runs/{run_id}/notifications      (manager+)
```

## 4. Run the data pipeline

The orchestrator ingests data from the four engines, resolves companies on `company_domain`, scores leads, derives leadership signals, and recommends engagement strategies. **It is idempotent** — safe to run repeatedly.

### Full pipeline (ingest + score)

```powershell
python -m orchestrator.cli run all
```

**What it does:**
1. Ingests each engine's **output** (no live crawling by default)
2. Resolves companies on canonical `company_domain`
3. Scores leads (coverage-normalized, with Low/Med/High confidence)
4. Derives person-level leadership signals (director+ moves)
5. Recommends sales pitches per company

**Expected output:**
```
Pipeline run
component                          status    processed  created  updated  review  ms       notes
─────────────────────────────────────────────────────────────────────────────────────────────────
industry                           success   122        0        0        0       45       122 companies
blog                               success   43         7        36       0       89       43 opportunities
annual_list                        success   0          0        0        0       8        feed not present (no-op)
company_news                        success   0          0        0        0       7        feed not present (no-op)
career                             success   6          0        6        0       34       6 demand signals
decision_maker_intelligence        skipped   -          -        -        -       -        APIFY_API_TOKEN not set
scoring                            success   122        0        122      0       156      grades: A+ 17 / A 13 / B 10 / C 82
leadership                         success   122        0        8        0       23       8 director+ signals derived
engagement                         success   122        0        122      0       67       engagement strategies recommended
```

### Individual stages

```powershell
# Run one stage at a time (for development / debugging)
python -m orchestrator.cli run industry
python -m orchestrator.cli run blog
python -m orchestrator.cli run annual_list      # no-op if feed not present
python -m orchestrator.cli run company_news     # no-op if feed not present
python -m orchestrator.cli run career
python -m orchestrator.cli run decision_maker_intelligence  # skipped without APIFY_API_TOKEN
python -m orchestrator.cli run market_discovery   # no-op unless a source is enabled
python -m orchestrator.cli run market_intelligence  # interprets discovered companies
python -m orchestrator.cli run scoring
python -m orchestrator.cli run leadership
python -m orchestrator.cli run engagement
```

> **Fresh crawl by default for a single component.** Running one crawler-backed
> stage (`run industry` / `run blog` / `run career`) now **executes that engine
> (a fresh crawl) first, then ingests its new output** — so `run industry` performs
> genuine discovery of the latest company universe instead of re-importing a stale
> CSV. Add **`--no-run-engine`** for a fast ingest-only re-import of the existing
> output. `run all` is unchanged: **ingest-only by default**, add `--run-engine` to
> crawl every engine first (the scheduler/CI contract). Stages with no engine
> (`scoring`, `leadership`, `engagement`, `decision_maker_intelligence`,
> `annual_list`, `company_news`, `market_discovery`, `market_intelligence`) are
> unaffected — they always just run.

### Recovery & resume

```powershell
# Re-run only the stages that didn't succeed last time
python -m orchestrator.cli run all --resume

# Re-run a single failed stage
python -m orchestrator.cli rerun career

# Resume the last pipeline's failed stages (shorthand for --resume)
python -m orchestrator.cli rerun failed
```

### Pipeline health & audit trail

```powershell
# Health: last status, duration, next scheduled run per component
python -m orchestrator.cli status

# Recent pipeline runs (audit trail)
python -m orchestrator.cli runs
python -m orchestrator.cli runs --limit 50     # show last 50 runs
```

### Refresh Opportunities through the News Intelligence engine

Regenerate every opportunity through the upgraded News Collection Engine (multi-signal
extraction + intelligent dedup + rich AI fields). Deletes **only** opportunities/news
signals — companies, users, lead scores, career data and config are never touched.

```powershell
python scripts/refresh_news_opportunities.py --dry-run   # preview counts, roll back
python scripts/refresh_news_opportunities.py             # live refresh (uses DATABASE_URL)
```

Opportunities also enrich automatically during `run all` (the blog + company-news stages
backfill any missing AI intelligence in place, count-preserving).

### Live news sources (RSS / Google Alerts)

News sources are **database-driven**. Seed the curated production feeds (EE Times,
Semiconductor Engineering, AnandTech, NVIDIA newsroom, …), then enable/add more:

```powershell
python scripts/seed_news_sources.py          # seed curated feeds (idempotent)
python scripts/seed_news_sources.py --list    # show configured sources + on/off + URL
```

Manage at runtime via the API (manager role): `GET/POST /opportunities/news-sources`,
`PATCH /opportunities/news-sources/{id}` (enable/disable/edit), `POST /opportunities/news-sources/seed`.

The **`news`** pipeline stage (between `blog` and `annual_list`) collects from every
enabled source and runs each article through multi-signal extraction → opportunities.
It is part of `run all`, so the **Scheduler and Standard Run pick it up automatically**.
Collection is **incremental** (`If-Modified-Since` conditional GET + published-date
filter + article-hash dedup), so a re-run only processes genuinely new articles.

**Google Alerts:** create an alert at <https://www.google.com/alerts>, set *Deliver to:
RSS feed*, copy the feed URL onto the pre-seeded `Google Alerts — …` row (or a new
`adapter_type=google_alerts` source), and enable it.

---

## 5. Engine convergence (strengthen leads with multi-signal companies)

Out of the box, the engines crawl different company universes, so most companies carry only **one signal** and scores stay low. To unlock multi-signal A/B leads, re-crawl the engines over the **same company seed**:

```powershell
# 1. Export a seed of companies that still lack hiring-demand data
python scripts/build_convergence_seed.py            # -> convergence_career_seed.csv

# 2. Re-crawl Career demand (in the Career_Scraper_FINAL folder, with its own environment)
cd "..\Career_Scraper_FINAL\career scrapper"
python -m career_scraper run <full-path>\convergence_career_seed.csv --output .
cd "..\..\Silicon_Patterns_Platform"

# 3. Re-ingest + re-score
python -m orchestrator.cli run all

# 4. Optional: run Apify Decision Maker Intelligence over those companies (needs APIFY_API_TOKEN)
$env:APIFY_API_TOKEN = "<your-token>"
python -m orchestrator.cli run decision_maker_intelligence
```

Check **Analytics → Company coverage** to see the improvement: companies with all three signals should rise, and new A/B leads appear.

---

## 6. Lead scoring & tuning

### Recompute lead scores (coverage-normalized, with confidence)

```powershell
python -m lead_scoring.run                          # score master_local.db
python -m lead_scoring.run path\to\other.db       # score a different DB

# Sample output:
# companies: 122 · lead_scores: 122 · coverage: avg 1.8/3 signals per company
# grades: A+ 17 / A 13 / B 10 / C 82
# coverage_normalization: 0.25 (1.25 multiplier for single-signal companies)
# confidence: Low 44 / Medium 38 / High 40
```

### Tune lead scoring weights

Edit `config/lead_scoring.json`:

```json
{
  "weights": {
    "opportunity": 0.30,
    "demand": 0.30,
    "readiness": 0.20,
    "decision_maker": 0.20
  },
  "coverage_normalization": 0.25,
  "grade_bands": {"A+": 70, "A": 50, "B": 30},
  "confidence_bands": {"low": 1, "medium": 2, "high": 3},
  "multipliers": {
    "region": {...},
    "prospect": {...},
    "tier": {...}
  }
}
```

Then re-score:

```powershell
python -m lead_scoring.run
```

**What's tunable:**
- `weights` — sub-score contributions (sum = 1.0).
- `coverage_normalization` — penalty for missing signals (0 = legacy unweighted average; 0.25 = coverage-aware).
- `grade_bands` — thresholds (A+ ≥ 70, A ≥ 50, B ≥ 30, C otherwise).
- `multipliers` — fit penalties for region, prospect type, company tier.

### Backfill missing company classifications (no re-crawl)

Companies the engines surfaced without a tier/prospect/compliance can be classified from their *own* ingested rows:

```powershell
python scripts/backfill_classification.py            # dry-run: show what would be filled
python scripts/backfill_classification.py --apply    # write tier/prospect/compliance, then re-score:
python -m lead_scoring.run
```

---

## 7. Platform derivations (leadership signals & engagement recommendations)

### Derive person-level leadership signals (director+ movement)

Director+ promotions, role changes, executive hires/departures, board & founder changes are automatically derived from decision-maker snapshots and company-news feeds. The `leadership` stage runs on every refresh; this script is for ad-hoc rebuilds:

```powershell
python scripts/derive_leadership_signals.py              # rebuild + summary
python scripts/derive_leadership_signals.py --window 60  # widen recency window (default 36 months)
```

**Surfaces as:**
- A collapsible **Leadership Signals** dropdown on Company Profile (grouped by company, sorted by recency).
- A **Leadership Signals** feed on the Decision Makers page.
- Automatic part of the orchestrator pipeline (`sp-platform run all` includes the `leadership` stage).

### Recommend sales pitches per company (engagement engine)

Each company gets a likely business need + Silicon Patterns offering + one-line pitch + confidence + rationale. Evidence-grounded, deterministic (no LLM); runs automatically in every refresh:

```powershell
python scripts/recommend_engagements.py              # rebuild + summary
python scripts/recommend_engagements.py --show 8    # print example pitches for 8 companies
```

**Surfaces as:**
- **Recommended Engagement Strategy** section on Company Profile.
- Automatic part of the orchestrator pipeline (`engagement` stage).

---

## 8. Curated feeds (annual lists & company news)

### Ingest annual lists / rankings

Drop a feed file at the platform root or in `data/` with columns: `company_name` / `company_domain`, `list_name`, `list_year`, `list_rank`, `list_publisher`, `article_url`, etc. Supported formats: `.jsonl`, `.csv`, `.xlsx`.

```powershell
# Run the annual_list ingestion stage
python -m orchestrator.cli run annual_list

# Then re-score (so annual-list appearances nudge the opportunity sub-score)
python -m orchestrator.cli run scoring
```

**Result:**
- Annual-list appearances become `ANNUAL_LIST` opportunities.
- Rank is stored in `company_news_signal` column.
- Shows in **Opportunities** (filter `?annual_lists_only=true`).
- Appears as **Recognition & rankings** card on Company Profile.

No feed present → the stage is a clean no-op.

### Ingest company news / people moves

Drop a feed file at the platform root or in `data/` with columns: company identifier + `news_type` ∈ {EXECUTIVE_HIRE, LEADERSHIP_CHANGE, ROLE_CHANGE, COMPANY_NEWS}, plus `person_name` / `person_title` / `previous_title` / `new_role` / etc. Supported formats: `.jsonl`, `.csv`, `.xlsx`.

```powershell
# Run the company_news ingestion stage
python -m orchestrator.cli run company_news

# Derive person-level leadership signals (director+ moves feed Leadership Signals)
python -m orchestrator.cli run leadership

# Re-score (so news moves nudge the opportunity sub-score)
python -m orchestrator.cli run scoring
```

**Result:**
- People-move events become `EXECUTIVE_HIRE` / `LEADERSHIP_CHANGE` / `ROLE_CHANGE` / `COMPANY_NEWS` opportunities.
- One-liner summary stored in `company_news_signal` column.
- Shows in **Opportunities** (filter `?company_news_only=true`).
- Director+ moves automatically feed the **Leadership Signals** dropdown.
- Timeline visible on Company Profile.

No feed present → the stage is a clean no-op.

---

## 9. Run the website

Open **two terminals**, both from the platform root (with the venv activated).

### Terminal 1 — Backend API

```powershell
python -m uvicorn backend.main:app --reload --port 8000
```

**Output:**
```
INFO     uvicorn.server:Started server process
INFO     uvicorn.server:Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

**Available endpoints:**
- API: `http://127.0.0.1:8000`
- Interactive API docs: `http://127.0.0.1:8000/docs` (Swagger UI)
- Health check: `http://127.0.0.1:8000/health`

### Terminal 2 — Frontend

```powershell
cd frontend
npm run dev
```

**Output:**
```
VITE v8.0.16  ready in 234 ms
➜  Local:   http://localhost:5173/
➜  press h to show help
```

**Access the website:**
- Open `http://localhost:5173`

The frontend automatically proxies `/api` → `http://127.0.0.1:8000` in dev mode, so no extra configuration is needed.

---

## 10. Authentication & user management (dev vs production)

Sign-in is Microsoft Entra ID (Azure AD) — MSAL on the frontend (Authorization Code
+ PKCE), the backend verifies the resulting Microsoft ID token locally against the
tenant's JWKS (`backend/security.py::verify_microsoft_id_token`) and mints its own
session JWT exactly as before. No password storage anywhere in the app.

### Dev mode (default — no setup)

When neither `SP_API_KEY` nor Microsoft is configured, the **auth bypass** is on:
- The API is **open** (no login required).
- The website loads without a login as a synthetic **admin**.
- The top-bar **Dev Role Switcher** lets you preview each role (admin / manager / member) against synthetic users `betatestingadmin@siliconpatterns.com`, etc.

**To enable explicitly:**
```powershell
$env:DEV_AUTH_BYPASS = "true"
python -m uvicorn backend.main:app --reload --port 8000
```

`ENVIRONMENT=production` hard-disables the bypass regardless of the above, and the API
refuses to start at all unless `SP_JWT_SECRET` is a strong (32+ char) value AND
`MICROSOFT_TENANT_ID`/`MICROSOFT_CLIENT_ID` are set — see
`backend/security.py::_bypass_on`.

### Production mode

#### Step 1: Create the Entra App Registration

In the Azure Portal → Entra ID → App registrations → New registration: platform
type **Single-Page Application**, redirect URI = your deployed frontend origin
(e.g. `https://app.yourhost.com`, or `http://localhost:5173` for local prod-mode
testing). Note the **Application (client) ID** and **Directory (tenant) ID** —
optionally create a client secret too, though the current sign-in flow (local JWKS
verification) doesn't require one.

#### Step 2: Set environment variables

```powershell
# Backend (server)
$env:ENVIRONMENT = "production"
$env:SP_JWT_SECRET = "<strong-random-string-32-bytes>"   # signs this app's session JWTs
$env:SP_ADMIN_EMAILS = "you@siliconpatterns.com,manager@siliconpatterns.com"  # auto-approved as admin on first sign-in
$env:ALLOWED_EMAIL_DOMAIN = "siliconpatterns.com"  # optional; defaults to this
$env:SP_JWT_TTL_HOURS = "12"  # optional; session TTL in hours

# Microsoft Entra ID — from the App Registration above
$env:MICROSOFT_TENANT_ID = "<directory-tenant-id>"
$env:MICROSOFT_CLIENT_ID = "<application-client-id>"
$env:MICROSOFT_CLIENT_SECRET = "<client-secret>"  # accepted for completeness; not required by the current flow
$env:MICROSOFT_REDIRECT_URI = "https://app.yourhost.com"

# Initial administrator bootstrap: this email is provisioned active super_admin the
# first time it signs in via Microsoft, skipping the pending queue.
$env:SP_BOOTSTRAP_ADMIN_EMAIL = "admin@siliconpatterns.com"

# Restart the backend
python -m uvicorn backend.main:app --reload --port 8000
```

```powershell
# Frontend (frontend/.env or the host's env-var UI)
VITE_MICROSOFT_CLIENT_ID=<application-client-id>
VITE_MICROSOFT_TENANT_ID=<directory-tenant-id>
```

**Result:**
- **Auth bypass is auto-off** (`ENVIRONMENT=production` forces this regardless of
  other settings).
- The login page shows a single **Sign in with Microsoft** button.
- Dev Role Switcher is removed.
- Synthetic test users are removed.
- Sign in as `SP_BOOTSTRAP_ADMIN_EMAIL` via Microsoft — you land as an active
  `super_admin` immediately, no separate password/approval step.
- `GET /platform/config/readiness` reports `ready: true` once a strong `SP_JWT_SECRET`
  is set, `MICROSOFT_TENANT_ID`/`MICROSOFT_CLIENT_ID` are configured, and an active
  super_admin exists (see §9 above).

#### Step 3: User lifecycle & approval

1. **First sign-in:** a new `@siliconpatterns.com` user signs in with Microsoft →
   account is created as `pending` (no access yet).
2. **Admin approval:** an admin (from `SP_ADMIN_EMAILS`, or the bootstrap
   administrator) navigates to **Administration → Users** and clicks **Approve**.
3. **User can now sign in** (status → `active`) with the same Microsoft account.

#### Roles

- **admin** — everything: lead assignment, user management, review verdicts (score-affecting).
- **manager** — lead assignment, team console, workload dashboard, professional contact edits, score-affecting review verdicts.
- **member** — own assigned leads, full read access, comment/take notes, neutral review verdicts.

**Manage users via CLI** (if needed):
```powershell
python -m orchestrator.cli users list
python -m orchestrator.cli users promote <email> --role admin
python -m orchestrator.cli users deactivate <email>  # no hard delete; audit trail survives
python -m orchestrator.cli users activate <email>
```

---

## 11. Outreach module (native — no separate setup)

The Outreach module is a **native part of the platform**: same FastAPI backend, same React SPA, same master DB, same login/roles. No separate app, iframe, or Supabase project.

### Email modes

#### Mock mail (default — for dev/demo)

```powershell
# Outreach is already in mock mode if OUTREACH_MAIL_MODE is unset or "mock"
# All email actions are simulated: draft → approval → send → reply fully exercisable
```

No credentials needed. Use this for:
- Local development.
- Manager pitch / demos.

#### Real Gmail (production only)

```powershell
# Set mail mode
$env:OUTREACH_MAIL_MODE = "gmail"

# Provide Google OAuth credentials (see backend/outreach_mail.py for details)
# This requires: a deployed origin (not localhost) + Gmail OAuth setup (future work)
```

Currently stub; full Gmail implementation deferred to launch.

### Using Outreach

1. **Navigate to Outreach:** click the **Outreach** nav group (Overview, Leads, Pipeline, Approvals, Templates, Inbox).
2. **Populate from Discovery (admin/manager only):** click **"Sync from Discovery"** on Outreach Leads, or call:
   ```powershell
   curl -X POST "http://127.0.0.1:8000/outreach/leads/sync?limit=60"
   ```
   Qualifies the top 60 lead-scored companies into the outreach pipeline (idempotent).
3. **Manage the pipeline:** drag leads between stages, draft emails, approve/send, track replies (all simulated in mock mode).

---

## 12. Running tests

```powershell
# Run all tests (180 total; all pass)
python -m pytest -v

# Run tests in a single module
python -m pytest tests/test_orchestrator.py -v

# Run a single test
python -m pytest tests/test_lead_scoring.py::test_coverage_normalization -v

# Run with coverage
pip install pytest-cov
python -m pytest --cov=backend --cov=lead_scoring --cov=integration tests/
```

**Expected:** All 180 tests pass. If any fail:
- Check database state: `python -m orchestrator.cli status`
- Re-seed if needed: `python scripts/seed_master_db.py`
- Check error logs: pytest output includes the stack trace.

---

## 13. Regenerating frontend API types

The frontend's API contract is **generated from the backend's OpenAPI schema**; if you change a response schema, regenerate the frontend types:

```powershell
cd frontend
npm run gen:api-schema     # rewrite src/lib/api/schema.ts from backend OpenAPI
npm run check:api-schema   # guard: fails if schema.ts is out of date (good for CI)
npm run build              # tsc surfaces breaking contract changes as type errors
```

No running server is needed.

---

## 14. Production deployment (summary)

**Full architecture** (Vercel + dedicated Postgres + twice-daily GitHub Actions refresh, with secrets, schedule, engine bundling) is in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). Quick checklist:

1. **Master database:** Create a dedicated Postgres (Supabase / Neon), apply migrations 0001–0055, set `DATABASE_URL`.
2. **Backend API:** Deploy on a container host (Render / Railway / Fly / Cloud Run) with `Dockerfile`. Set `ENVIRONMENT=production`, `SP_JWT_SECRET`, `MICROSOFT_TENANT_ID`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `SP_BOOTSTRAP_ADMIN_EMAIL`, `SP_ADMIN_EMAILS`, `CORS_ORIGINS`, `DATABASE_URL`.
3. **Frontend:** Deploy on Vercel (or static host). Set `VITE_API_BASE_URL` (deployed API origin).
4. **Pipeline:** GitHub Actions workflow runs `sp-platform run all` twice daily via cron. Set `DATABASE_URL`, `APIFY_API_TOKEN` (if using Apify) in repo secrets.
5. **Validation:** Run `python scripts/validate_postgres.py` against a **throwaway** database to test against real Postgres (it truncates).

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for full steps, secrets, cron scheduling, and the freshness safeguard.

---

## 15. Verify everything is working

### 1. Pipeline health

```powershell
python -m orchestrator.cli status
```

Every component should show `success` (or `skipped` for `decision_maker_intelligence` if no Apify token).

### 2. Website

Open `http://localhost:5173`:

- **Dashboard** shows non-zero counts (122 companies, 50 opportunities, 122 leads, 188 decision makers).
- **Connection badge** (top-right) reads **Online** in green.
- **Companies → open Tenstorrent** → profile shows:
  - Lead score: A+ 99.1 (coverage-normalized).
  - Score explanation: opportunity + decision-maker signals.
  - Hiring demand: 6 roles.
  - Timeline: leadership signals + news.
  - Recognition & rankings: annual lists (if feed present).
  - Engagement strategy: recommended pitch + confidence.
- **Human Review & Assessment** panel: set a human verdict (Approved / Needs Review / Strategic Account / Disqualified / Watchlist) + reason.
  - Model grade and adjusted grade shown side-by-side (when review status has a score effect).
  - Both values stay separate (model score never changes).
- **Analytics → Company coverage**: matrix of which companies have which signals.
- **Analytics → Review insights**: model-vs-human disagreements, overrides, strategic accounts (if reviews exist).

### 3. API

Open `http://127.0.0.1:8000/docs` (Swagger UI):

- Try `GET /analytics/summary` → returns lead grades + opportunities.
- Try `GET /analytics/coverage` → engine-coverage matrix.
- Try `GET /companies/tenstorrent.com` → full unified profile.
- Try `GET /pipeline/health` → per-component freshness.

---

## 16. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'orchestrator'` | Check venv is activated (`.\.venv\Scripts\Activate.ps1`). Or use `python -m orchestrator.cli ...` instead of `sp-platform ...`. |
| `master DB not found: master_local.db` | Run `python scripts/seed_master_db.py` to rebuild, or copy a backup. The repo ships a populated DB. |
| Website says **Offline** / "API unreachable" | The backend isn't running. Start Terminal 1: `python -m uvicorn backend.main:app --reload --port 8000`. |
| `decision_maker_intelligence` stage **skipped** | Expected without `APIFY_API_TOKEN`. Set it if you want to crawl Apify. Otherwise it's a no-op. |
| Frontend edits don't show / blank page | Hard-reload the tab (Ctrl+Shift+R on Windows, Cmd+Shift+R on macOS). HMR can be flaky on Windows; restart npm if needed. |
| `CORS error: blocked by CORS policy` | The frontend origin and `CORS_ORIGINS` env don't match. In dev, unset `CORS_ORIGINS` (defaults to localhost). In prod, set it to your frontend URL. |
| Tests fail: `AssertionError: expected 122, got 0` | The master DB is empty or corrupted. Rebuild: `python scripts/seed_master_db.py`. Or check that the path is correct. |
| `career` / `blog` find "no output" with `--run-engine` | The scraper found nothing (bots blocked by sites, network issues, etc.). This is an engine limitation, not the platform. |
| `ImportError: cannot import name 'Orchestrator'` | Check the file exists: `orchestrator/orchestrator.py`. Reinstall if needed: `pip install -e .`. |

---

## 17. Full startup order (from fresh clone to running)

```powershell
# 1. Clone + setup
git clone <repo>
cd Silicon_Patterns_Platform
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. Seed database (optional; already shipped populated)
python scripts/seed_master_db.py

# 3. Run pipeline (ingest + score)
python -m orchestrator.cli run all

# 4. Start backend (Terminal 1)
python -m uvicorn backend.main:app --reload --port 8000

# 5. Start frontend (Terminal 2)
cd frontend && npm run dev

# 6. Open in browser
# http://localhost:5173

# 7. Verify
python -m orchestrator.cli status
# Check Dashboard: 122 companies, 50 opportunities, etc.
# Check Analytics: company coverage matrix
```

---

## 18. Key files & commands reference

| Task | Command | File |
|---|---|---|
| List all migrations | `ls master_db/migrations/0*.sql` | `master_db/migrations/` |
| Review schema | `cat docs/SCHEMA.md` | `docs/SCHEMA.md` |
| Tune scoring | Edit JSON + `python -m lead_scoring.run` | `config/lead_scoring.json` |
| Check API contract | `npm run gen:api-schema` | `frontend/src/lib/api/schema.ts` |
| Deploy architecture | Read full guide | `docs/DEPLOYMENT.md` |
| Security (auth, SSO, RBAC) | Read full guide | `docs/SECURITY.md` |
| Frontend design | Read full guide | `docs/FRONTEND_DESIGN.md` |
| Test coverage | `python -m pytest --cov` | `tests/` |

---

## Next steps

- **Manager pitch / demo:** Backend + frontend are ready. Navigate to **Companies → Tenstorrent** to showcase annual lists, news, leadership signals, and engagement recommendations.
- **Phase 2 (prod launch):** See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for full production checklist.
- **Apify live crawling:** Set `APIFY_API_TOKEN` and re-run `decision_maker_intelligence` stage to populate with live decision-maker data.
- **Engine convergence:** Run `python scripts/build_convergence_seed.py` to unlock multi-signal A/B leads.
