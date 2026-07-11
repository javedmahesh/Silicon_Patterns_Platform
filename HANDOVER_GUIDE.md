# Silicon Patterns Platform — Engineer Handover Guide

> **Audience:** an engineer who has never seen this platform before. This is the single
> orientation document — read it top to bottom once, then use the deep-dive docs it links to
> (`README.md`, `HOW_TO_RUN.md`, `docs/SCHEMA.md`, `docs/DEPLOYMENT.md`, `docs/FRONTEND_DESIGN.md`,
> `docs/ENGAGEMENT_DEPENDENCIES.md`) as references.

**What the platform is, in one sentence:** it unifies four independent scraper "engines" into one
ranked, explainable view of which semiconductor / AI-silicon companies Silicon Patterns should pursue
and *why* — joined on a single key, **`company_domain`** (never company name).

**Golden rules (internalize these first):**
1. The **four engines are never modified.** The platform reads their outputs in place.
2. **`company_domain` is the universal join key.** Names are messy; domains are canonical.
3. Everything derived (scores, leadership signals, pitches) is **deterministic and explainable** —
   no LLM in the pipeline. Every output stores a `rationale`.
4. **Idempotent everywhere.** Re-running any stage upserts; it never duplicates.
5. **The pipeline never blocks.** Unmatched records become stubs in a review queue; failed stages are
   logged, not fatal.

---

## 1. Platform Architecture

Five data producers feed one master database, which a read-only API serves to a React console.

```
 Industry Discovery → Blog Crawler → Career Scraper → Decision Maker Intelligence (the 4 engines)
        (companies)    (opportunities)  (hiring demand)  (decision makers, Apify)
            │               │                │                │
            └───────────────┴────────────────┴────────────────┘
                                   │
                    integration (normalize + resolve + ingest)
                                   │
                         ┌─────────▼──────────┐
                         │   MASTER DATABASE   │   Postgres (prod) / SQLite (dev)
                         │  joined on domain   │   single source of truth
                         └─────────┬──────────┘
                                   │  (platform derivations, in order)
                   Lead Scoring → Leadership Signals → Engagement Recommendations
                                   │
                         backend API (FastAPI, read-only)
                                   │
                         frontend (React + Vite console)

 orchestrator (sp-platform CLI) drives: engines → ingest → score → derive, with run tracking + health
```

**Two kinds of producer — know the difference:**
- **Engines** (external, in sibling folders) — actually crawl the internet. Owned tables:
  `companies`, `opportunities`, `jobs`/`demand_signals`/`company_rollups`, `decision_makers`.
- **Platform derivations** (in *this* repo, pure functions over the master DB) — `lead_scoring`,
  `leadership_signals`, `engagement`. They need **no re-crawl**, so they run on every refresh even when
  the engines aren't checked out.

**Repository layout (where things live):**

| Folder | What it does |
|---|---|
| `backend/` | FastAPI app: `routers → services → repositories → database`, plus `config` + security (SSO/JWT/RBAC) |
| `integration/` | `normalizer` (domain canonicalization) · `resolver` (name→domain) · `merge` · `ingestors/` (one per engine) |
| `master_db/` | SQLAlchemy `models.py` + hand-written SQL `migrations/` (`0001`–`0016`) + `local.py` (SQLite self-heal) |
| `lead_scoring/` | `config` (tunable weights) · `scorer` (pure math) · `service` · `run` |
| `leadership_signals/` | `seniority` (director+ gate) · `derive` (the rules) |
| `engagement/` | `recommend` (the sales-pitch rules) |
| `orchestrator/` | `sp-platform` CLI · `stages.py` (the pipeline registry) · run tracking · health |
| `frontend/` | React + Vite + TS website (the analyst console) — incl. the **native Outreach module** pages under `src/pages/outreach/` |
| `config/` | engine paths · canonical enums · scoring weights · Supabase creds |
| `scripts/` | one-off drivers (`seed_master_db.py` — fixtures → a full dev DB, `derive_leadership_signals.py`, `recommend_engagements.py`, `backfill_classification.py`, `validate_postgres.py`, `dump_openapi.py`, …) |
| `.github/workflows/refresh.yml` | the twice-daily scheduled pipeline |
| `tests/` | pytest suite (180 tests) |

**Tech stack:** Python 3.13 · SQLAlchemy 2.0 · FastAPI · Typer + Rich (CLI) · pydantic-settings ·
React 18 + TypeScript + Vite + Tailwind v4 + TanStack Query/Table + Recharts. The frontend API
contract (`frontend/src/lib/api/schema.ts`) is **generated from the backend OpenAPI** (`npm run
gen:api-schema`), so client types cannot drift from `backend/schemas.py` (`npm run check:api-schema`
guards it in CI).

**Downstream: the Outreach module (native).** Beyond discovery/scoring, the Outreach module turns
already-qualified leads into outreach — `{{variable}}` email templates (no AI), an approval queue,
(mock or Gmail) sending, reply/inbox tracking, a service-sales CRM pipeline and funnel analytics. It is a
**native** part of the platform: FastAPI routes (`backend/routers/outreach.py` → `outreach_service.py` /
`outreach_repo.py` / `outreach_mail.py`), React pages (`frontend/src/pages/outreach/`), and five master-DB
tables (`outreach_leads`, `outreach_templates`, `outreach_messages`, `outreach_activities`; migration
`0020`). It **reuses** companies / decision_makers / lead_scores / engagement_recommendations / users — it
does not duplicate them — and the platform's Google-SSO + roles (admin/manager approve & manage; members
draft). `POST /outreach/leads/sync` qualifies the top `lead_scores` companies. Mail mode is set by
`OUTREACH_MAIL_MODE` (`mock` default; `gmail` is a drop-in). Run steps: HOW_TO_RUN §3.

---

## 2. Database Schema Overview

One Postgres (prod) / SQLite (dev) database, two layers, **everything joined on `company_domain`**.
Full column-level DDL is in `docs/SCHEMA.md` + `master_db/migrations/*.sql`; this is the map.

**Data layer (engine + derivation tables):**

| Table | Owner | Key facts |
|---|---|---|
| `companies` | Industry Discovery | **The hub. PK `company_domain`.** Identity, geography, classification, provenance. May hold low-confidence **stub** rows (`is_stub=true`) for domains other engines saw first. |
| `company_sources` | Industry Discovery | Provenance, many per company |
| `company_aliases` | resolution layer | `name_key → company_domain`; powers canonical resolution; grows automatically |
| `resolution_review_queue` | resolution layer | Unresolved/stub records awaiting human confirm/merge |
| `opportunities` | Blog Crawler | One row per article/event. `company_domain` **NOT NULL**. Funding/product/partnership signals |
| `jobs` | Career Scraper | One row per posting |
| `demand_signals` | Career Scraper | **1:1 per company.** Per-discipline job counts (rtl/asic/verification/physical_design/dft/…), `hiring_trend` |
| `company_rollups` | Career Scraper | 1:1 sales-ready demand summary |
| `decision_makers` | Decision Maker Intelligence (Apify) | PK `id`; `linkedin_url` unique. `company_domain` **NULLABLE** (resolved from org website). `profile_data` JSONB holds the Apify person/org metadata |
| `lead_scores` | Lead Scoring (derivation) | 1:1. `lead_score`, `grade` (A+/A/B/C), 4 subscores, 3 multipliers, `coverage`, `confidence`, `rationale` JSON |
| `leadership_signals` | Leadership Signals (derivation) | Person-level director+ movement. `company_domain` **NULLABLE**. (`0012`) |
| `engagement_recommendations` | Engagement (derivation) | 1:1 sales pitch per company. `business_need`/`offering`/`pitch`/`confidence`/`rationale`. (`0013`) |
| `lead_reviews` | Human review (platform) | 1:1 human assessment, **separate from `lead_scores`** — `review_status` + `human_notes` + attribution. (`0014`) |
| `lead_review_events` | Human review (platform) | Append-only **feedback/audit trail**; snapshots the model grade/score at each action. (`0014`) |
| `ingestion_runs` / `pipeline_runs` | Orchestrator | One row per ingestion/pipeline run (counts, status, timing). Powers audit + freshness |
| `review_actions` | review layer | Append-only audit of review-queue decisions |

**Multi-user layer (migrations `0007`–`0010`):** `users` (accounts, roles admin/manager/member,
deactivated-never-deleted) · `lead_assignments` (a company assigned to a user) ·
`lead_assignment_events` (append-only assignment audit) · `company_notes` · `decision_maker_contacts`
(**work** email/phone only — no personal data).

**Migrations are hand-written SQL, mirrored by the ORM.** Apply with
`for f in master_db/migrations/0*.sql; do psql "$DATABASE_URL" -f "$f"; done`. On **SQLite dev**,
`master_db/local.py::ensure_local_schema` auto-creates new tables (`create_all`) and adds missing
columns, so dev needs no manual migration. **Key convenience:** `pipeline_runs.component` is free text
(no CHECK), so adding a new pipeline stage needs **no migration**.

**Canonical enums** live in `config/enums.py` and are mirrored by SQL `CHECK` constraints — e.g.
`company_tier` ∈ {STARTUP, SCALEUP, ESTABLISHED, INCUMBENT, UNKNOWN}, `grade` ∈ {A+, A, B, C}.
`EXCLUDED_PROSPECT_TYPES = {SERVICE_PROVIDER}` — service-provider competitors are **blocked at
ingestion and never stored**.

---

## 3. Pipeline Flow

One command runs the whole thing: **`sp-platform run all`** (alias for `python -m orchestrator.cli run
all`). The stage registry is `orchestrator/stages.py`; order is fixed in `PIPELINE_ORDER`:

```
1. industry     → ingest companies           (engine: Industry Discovery)
2. blog         → ingest opportunities        (engine: Blog Crawler)
3. annual_list  → ingest ANNUAL_LIST opps     (curated feed, no crawler — no-op when absent)
4. company_news → ingest people-move opps      (curated feed — EXECUTIVE_HIRE/LEADERSHIP_CHANGE/…; feeds leadership)
5. career       → ingest jobs/demand/rollups   (engine: Career Scraper)
6. decision_maker_intelligence → ingest decision_makers  (Apify actor via API — needs APIFY_API_TOKEN)
7. scoring      → compute lead_scores          (derivation — pure math)
8. leadership   → derive leadership_signals    (derivation — over decision-maker snapshots + blog/company-news events)
9. engagement   → recommend engagements        (derivation — over every other signal, so it runs LAST)
```
> **company_news → leadership synergy:** director+ moves ingested as `EXECUTIVE_HIRE`/`LEADERSHIP_CHANGE`/
> `ROLE_CHANGE` opportunities are parsed (from their structured `company_news_signal`) by the
> `leadership` stage's blog-event feeder into person-level `leadership_signals` — which is why
> `company_news` runs before `leadership`.

**Each stage:**
- Optionally runs the upstream engine first (`--run-engine`), then **ingests** its output into the
  master DB through `integration/ingestors/`.
- Ingestion is **idempotent**: bulk `ON CONFLICT` upserts keyed on `company_domain` / `opportunity_id`
  / `job_id` / `linkedin_url` (~60× faster than per-row on Postgres).
- Records a `pipeline_runs` row (rows in/upserted/rejected/review-queued, status, timing) — **even on
  failure**. A stage that throws is caught and logged; the pipeline continues.
- Unresolved records (e.g. a decision maker whose company isn't catalogued) become **stubs** + a
  `resolution_review_queue` entry rather than failing.

**Why the order matters:** derivations 5–7 read what 1–4 produced. Engagement (7) reads *all* signals,
so it's last. Steps 5–7 are pure functions — they always run, even in CI without the engines vendored.

**Run-engine default (who crawls before ingesting):** a **single-component** run of a
crawler-backed stage — `run industry` / `run blog` / `run career` — **runs that engine
(a fresh crawl) first, then ingests** its new output (so e.g. `run industry` does genuine
fresh discovery rather than re-importing a stale CSV); pass `--no-run-engine` for a fast
ingest-only re-import. A full **`run all`** stays **ingest-only by default** (engines may be
absent in CI, Apify costs money, crawls are slow) — add `--run-engine` to crawl every engine
first. The switch is `orchestrator.cli._effective_run_engine`; the orchestrator only runs an
engine for a stage that declares an `EngineSpec` (`industry`/`blog`/`career`), so engine-less
derivation stages are unaffected.

**Ingest-only run** (skip crawling, just re-ingest existing files + re-derive):
`sp-platform run all` (without `--run-engine`), or any single stage with `--no-run-engine`.

---

## 4. Scheduled Jobs

**Principle: a scheduler is a *trigger*, not a *runtime*.** The heavy pipeline runs on a real job
runner (GitHub Actions), never inside Vercel/Supabase cron.

- **File:** `.github/workflows/refresh.yml`.
- **Schedule:** `cron: "0 9,21 * * *"` — **twice daily, in UTC.** Adjust for timezone (e.g. 09:00/21:00
  IST = `"30 3,15 * * *"`).
- **What it runs:** `python -m orchestrator.cli run all --run-engine --trigger daily`, writing to the
  dedicated master Postgres (`DATABASE_URL` secret). `workflow_dispatch` allows a manual run, with a
  `run_engine` toggle (off = ingest/score only).
- **Concurrency guard:** a `concurrency` group prevents two refreshes overlapping (keeps idempotency +
  freshness clean).
- **Secrets:** `DATABASE_URL` (master Postgres), `APIFY_API_TOKEN` (Decision Maker Intelligence
  engine), optionally `ENGINES_TOKEN` (to check out private engine repos).
- **Engines in CI:** they must be made available under `$SP_ENGINES_DIR` (`./engines`) — either
  vendored into the repo or checked out as extra steps (template is in the workflow). **Without them,
  the `--run-engine` stages fail-and-log, but the derivation stages (scoring/leadership/engagement)
  still run over existing data.**
- **Failure alerting:** an `if: failure()` step opens or comments on a **deduped GitHub issue** labeled
  `pipeline-failure` (built-in `GITHUB_TOKEN`). ⚠️ This only fires on a **process-level** failure (a
  step exited non-zero). Stage failures the orchestrator catches and *logs* don't trip it — watch
  `GET /pipeline/status` or `orchestrator.cli runs` for those.
- **Caveat:** shared CI IPs sometimes get bot-blocked by career sites. If crawling is unreliable from
  Actions, move the run to a scheduled container job (Cloud Run Jobs / Render Cron / Fly Machines) —
  same command, friendlier IPs.

The two derivation-only stages (leadership, engagement) are what keep the platform fresh **automatically
on every scheduled run** with zero extra wiring — they're plain pipeline stages.

---

## 5. Lead Scoring Logic

Pure math (`lead_scoring/scorer.py`, `CompanyInputs → ScoreResult`, no DB/IO). Tunable in
`config/lead_scoring.json`; re-run with `python -m lead_scoring.run`.

**Four 0–100 subscores** (each from one engine's data):
- **opportunity** (Blog) — best opportunity score + a small multi-opportunity bonus.
- **demand** (Career) — normalized demand score against a reference.
- **readiness** — max of opportunity/demand/rollup readiness.
- **decision_maker** (Decision Maker Intelligence) — points per senior/other DM, capped.

**Blend → base → final:**
```
weighted_sum   = 0.30·opportunity + 0.30·demand + 0.20·readiness + 0.20·decision_maker
present_weight = sum of the weights whose signal was actually PRESENT
base           = weighted_sum / (present_weight ^ coverage_normalization)
final          = clamp( base × region_mult × prospect_mult × tier_mult , 0, 100 )
grade:  A+ ≥ 70 · A ≥ 50 · B ≥ 30 · C otherwise
```

**The key idea — coverage normalization.** Absent signals are **not** counted as zeros. Dividing by the
*present* weight (raised to a tunable strength) means a perfect-fit company with one strong signal
ranks on merit (e.g. Tenstorrent → A+) instead of being diluted to a B by the engines that simply
haven't covered it yet. Set `coverage_normalization: 0` for the legacy weighted average; full-coverage
companies are unaffected either way.

**Confidence (separate from the score):** counts how many of the **3 engine signals** (opportunity /
demand / decision-makers) backed the score → **Low / Med / High** badge. This distinguishes a
thin-evidence A+ from a fully-backed one — the score says *how good a fit*, confidence says *how much we
know*.

**Fit multipliers** (`region × prospect × tier`) down-weight poor-fit companies. Companies surfaced
without a tier are backfilled from their own ingested rows (`scripts/backfill_classification.py`)
before scoring.

Every subscore, weight, multiplier, coverage/confidence, missing input and the final value is stored in
the `lead_scores.rationale` JSON — exactly what the website's **Score explanation** panel renders, so
every grade is auditable.

---

## 6. Leadership Signals Logic

Person-level, **director-and-above only** leadership movement — a platform *derivation*, deliberately
distinct from the Blog Crawler's company-level "Leadership Change" *opportunity*. Code:
`leadership_signals/seniority.py` (the gate) + `leadership_signals/derive.py` (the rules). Stored in
`leadership_signals`; rebuilt by the `leadership` pipeline stage (idempotent, per-source delete+insert).

**The director+ gate** (`classify_seniority(title) -> (band, function) | None`): the single chokepoint
enforcing scope. Matched most-senior/most-specific first so edge cases resolve right ("vice president" =
VP not President; "managing/senior director" outrank plain "director"; "evp/svp" outrank "vp").
- **IN:** Director, Senior Director, VP/SVP/EVP, C-level, President, Founder/Co-Founder, Managing
  Director, board roles, and **Heads of** Engineering/Product/Technology/Business Development only.
- **OUT (→ None):** Manager, Senior Manager, Lead, Principal, Staff, Associate/Assistant/Deputy
  Director, and all individual contributors. (It is intentionally **separate** from the coarse
  `decision_makers.seniority` binary flag, which is left untouched.)

**Three feeders write the same table:**
- **`from_decision_maker_snapshots` (the Apify-era backbone, `source='snapshot_comparison'`).** Each
  `decision_maker_intelligence` run captures a snapshot (title/company/seniority) per decision maker;
  this compares the two most recent snapshots per person, gates to director+, and emits movement:
  - same company, title rank ↑ → **promotion**; rank ↓ → **role_change**;
  - a director+ now at a *different* company → **new_executive_hire**;
  - a director+ present in the previous snapshot but absent from the latest → **executive_departure**.
  - (Movement detection needs **≥ 2 runs** — the first run only establishes the baseline.)
- **`from_blog_events` (`source='blog_event'`, yields data once crawls populate).** Regex-extracts
  person + role + movement from `Leadership Change` opportunities ("appoints X as Y", "X promoted to
  Y", "X steps down", "named to the board"), gates + classifies.
- **`from_decision_makers` (legacy, `source='linkedin_history'`).** Where a decision maker's
  `profile_data` still carries a `positions`/`experience` career history, walks it for in-window
  director+ moves (promotion / role_change / new_executive_hire / executive_departure / founder_change
  / board_appointment / executive_reshuffle). Apify records have no career history, so this contributes
  only from earlier-sourced rows.

**Confidence:** high (band + dates + company resolved) / medium (unresolved company or coarse date) /
low (heuristic or blog-extracted). Each signal carries `movement_type`, `seniority_band`, `from_title`/
`to_title`, `effective_date`, `event_age_days`, `confidence`, `source`, `summary`.

**In the UI:** a collapsible **Leadership Signals** dropdown on the Company Profile and above the
Decision Makers directory (grouped by company). Treated as *person-level intelligence*, not a company
opportunity.

---

## 7. Engagement Recommendation Logic

The sales-pitch engine: for each company, one **Recommended Engagement Strategy** = a likely business
need + the matching Silicon Patterns offering + a one-line pitch, with a confidence score and the
evidence used. Code: `engagement/recommend.py` (`MODEL_VERSION = "engagement-v1"`). Stored 1:1 in
`engagement_recommendations`; rebuilt by the `engagement` pipeline stage (runs **last**).

**Design: rule-based, deterministic, evidence-grounded — no LLM.** Chosen because the requirements are
evidence-only + explicit rationale + auto-refresh + no marketing boilerplate, and the pipeline has no
LLM key. `recommend_for_company(...)` is a **pure function** over already-fetched rows, so it's
DB-free and unit-testable.

**How it decides:**
- **Offering** comes from the per-discipline hiring mix in `demand_signals` (verification / rtl /
  physical_design / dft / fpga / asic / embedded), nudged by `primary_focus` and tech hints. No
  discipline signal → **staffing** fallback (if any funding/product/expansion/eng-leadership event) →
  **enablement** fallback (always low confidence).
- **Trigger framing** ("why now") comes from the strongest event, highest first: funding round →
  product/tapeout → expansion → new engineering leadership → growing hiring trend.
- **Confidence (0–100, label low/med/high at 40/70):** base 25 + per-discipline hiring depth
  (up to +35) + GROWING trend (+10) + corroborating opportunities (up to +20) + eng-leadership hire
  (+10) + any decision maker (+5).
- **Companies with zero signals get no row** (honest by construction).

**Dependencies & graceful degradation** are documented in full in
`docs/ENGAGEMENT_DEPENDENCIES.md` — the short version: needs **≥1 of Career / Blog / Decision Maker
Intelligence**; **Career decides _what_ to pitch** (and contributes the most confidence); **Blog/Decision
Maker Intelligence decide _why now_**; Industry Discovery is the anchor but never sufficient alone. Remove any one source and the
engine keeps running with a more generic, lower-confidence pitch — it never crashes or blocks.

**In the UI:** a dedicated **Recommended Engagement Strategy** panel at the top of the Company Profile
(need · offering · quoted pitch · confidence badge · collapsible "Why this pitch" rationale).

---

## 8. Human Review System

The platform **never blocks** on bad/ambiguous data — it quarantines it for a human. There are
**three** review surfaces (note the naming: `review.py`/`/review-queue` is data resolution;
`reviews.py`/`/reviews` is the human *lead* assessment — different workflows):

**A. Resolution review queue** (`resolution_review_queue` table + `backend/routers/review.py`). When
the resolver can't confidently map a record to a canonical company (e.g. a decision maker whose
employer isn't catalogued, or a fuzzy near-match), it:
1. inserts a low-confidence **stub** company (`is_stub=true`, `validation_status='STUB'`) so downstream
   joins still work, and
2. queues a review item with the raw name/domain, source engine, suggested domain, match type, and
   confidence.

A reviewer (in the website's **Review queue** page) resolves each item via these endpoints — every
action is recorded in the append-only `review_actions` audit trail:

| Endpoint | Action |
|---|---|
| `POST /review-queue/{id}/approve` | Confirm the stub as a real company |
| `POST /review-queue/{id}/merge` | Merge the stub into an existing canonical company |
| `POST /review-queue/{id}/reject` | Not a prospect — reject |
| `POST /review-queue/{id}/alias` | Create a `name → domain` alias (so the spelling auto-resolves next time) |
| `GET /review-queue` · `/{id}` · `/{id}/actions` | List · detail · audit trail |

Creating an alias is the highest-leverage action: it teaches `company_aliases` permanently, so the same
variant resolves automatically forever after.

**B. Human lead review & feedback** (`lead_reviews` + `lead_review_events` tables +
`backend/routers/reviews.py` + `lead_scoring/human_review.py`). Lets an analyst override the *model's*
verdict when it misclassifies a prospect — **without ever overwriting the model score**. The model
grade/score stays in `lead_scores`; the human verdict (`review_status` ∈ approved / needs_review /
strategic_account / disqualified / watchlist, plus a reason) lives separately in `lead_reviews`, and
the two are shown side by side. Key points for a new engineer:
- **`PUT /reviews/{domain}`** records the assessment and appends a `lead_review_events` row — the
  **feedback table** — which snapshots the model grade/score *at that moment*. This is deliberately the
  store a future model could learn from; **today the platform only records it, it never retrains or
  changes scores.**
- **Ranking** (`GET /leads?sort=model|human|combined`): `model` = the model's `priority_rank`; `human`
  = grouped by status tier (strategic top … disqualified bottom); `combined` = the **adjusted score**
  (model when the adjustment is off).
- **Optional review→score adjustment (reconciled Change_05, OFF by default — `config/lead_scoring.json`
  `review_feedback`).** The model `lead_score`/`grade` are **never** changed; a SEPARATE
  `lead_scores.adjusted_score`/`adjusted_grade` is derived from the company's `review_status`
  (`strategic_account`/`approved` → boost + grade floor; `disqualified` → penalty). It's computed in
  `lead_scoring/human_review.adjusted_score` (pure, **always from the pristine model score — never
  compounds**), persisted by `score_all` and recomputed for one company on `PUT /reviews/{domain}`, and
  lapses when a review `expires_at`. When enabled, a score-affecting status **requires a reason +
  manager/admin**; `rationale.adjustment` + the `lead_review_events` snapshot keep it auditable. Both
  values show in the UI. **Still no auto-learning** — see below.
- **Reports** (`GET /reviews/reports`, surfaced on Analytics): model-vs-human disagreements, frequently
  overridden companies, strategic accounts, and false positives/negatives — where `disagreement()`
  classifies a high-grade-but-disqualified lead as a false positive and a low-grade-but-strategic lead
  as a false negative.
- Open to **any authenticated user** (analyst feedback, like company notes), with full attribution;
  reads are open, the history is append-only.

**C. CRM / assignment review** (multi-user layer). Managers assign leads to members with a note; every
assign/reassign/unassign/status/note change writes a `lead_assignment_events` row. Company notes +
activity timeline give a full audit. Accounts are deactivated, never hard-deleted, so history survives.
Access is **role-gated** (admin/manager/member) — RBAC restricts *actions*, not visibility.

---

## 9. Deployment Instructions

Full detail in `docs/DEPLOYMENT.md`; this is the shape. Three pieces, only one of which ever "fetches":

| Component | Runs on | Always on? |
|---|---|---|
| Frontend | Vercel (static Vite build) | Yes |
| Read API (FastAPI) | Managed container (Render/Railway/Fly/Cloud Run) | Yes (on-demand) |
| Master DB | **Dedicated** Postgres (Supabase/Neon) | Yes |
| Refresh pipeline | GitHub Actions cron | No (ephemeral) |

**One-time setup checklist:**
1. **Database** — create a **dedicated** Postgres for the master DB. Apply migrations in order:
   `for f in master_db/migrations/0*.sql; do psql
   "$DATABASE_URL" -f "$f"; done`. On Supabase use the **session pooler** host. *(Never run
   `scripts/validate_postgres.py` against prod — it truncates.)*
2. **API** — deploy the included `Dockerfile` / `render.yaml` (it runs the exact local app,
   `uvicorn backend.main:app`, no engines). Set secrets: `DATABASE_URL`, `ENVIRONMENT=production`,
   `SP_JWT_SECRET` (≥32 bytes), `SP_BOOTSTRAP_ADMIN_EMAIL` + `SP_BOOTSTRAP_ADMIN_PASSWORD`
   (initial administrator — first-party email/password, no external identity provider),
   `SP_ADMIN_EMAILS`, `CORS_ORIGINS` (**JSON list**), `SP_RATE_LIMIT_PER_MINUTE`. Health check `/health`.
3. **Frontend** — Vercel, root dir `frontend`, preset Vite. Env: `VITE_API_BASE_URL` (the API origin)
   — sign-in is first-party email/password, no frontend auth env vars needed.
4. **Scheduler** — add the GitHub repo secrets (§4); make the engines available; tweak the cron
   timezone. Trigger once manually to seed.
5. **Outreach module** — nothing extra to deploy: it ships with the backend + frontend + master DB above
   (migration `0020` creates its tables). Optionally set `OUTREACH_MAIL_MODE=gmail` (+ Google OAuth creds
   for the Gmail *sending* integration — unrelated to sign-in) for real mail; the default `mock` needs
   no setup. Seed the pipeline post-deploy with `POST /outreach/leads/sync` (admin/manager).

**⚠️ Auth gotcha:** the dev auth bypass is ON whenever `SP_API_KEY` is absent. **Setting `SP_API_KEY`,
or `ENVIRONMENT=production`, turns the bypass off** — which is exactly what you want in prod.
`ENVIRONMENT=production` additionally refuses to start at all unless `SP_JWT_SECRET` is a strong
(32+ char) value. Leave `DEV_AUTH_BYPASS` unset in prod.

**Known limitation (documented, not a bug):** writes commit per stage, so *during* a run the DB is
briefly mixed. The frontend's connection badge anchors "Data as of …" to `last_successful_refresh` and
warns on a failed/in-progress run, so users never silently see a partial refresh. A strict atomic
snapshot would need a staging-schema swap (a noted future enhancement); given the twice-daily cadence,
eventual consistency is acceptable.

---

## 10. Recovery Procedures

Everything is idempotent and logged, so recovery is low-drama.

**Inspect state:**
- `GET /pipeline/health` · `GET /pipeline/status` (reports `last_successful_refresh` + whether the
  latest run failed/in-progress) · `GET /pipeline/runs`.
- CLI equivalents (against `DATABASE_URL`): `python -m orchestrator.cli status` / `runs`.
- The `pipeline_runs` table logs every stage outcome, including caught stage failures.

**Recover a failed/partial run:**
- `python -m orchestrator.cli run all --resume` — re-runs **only** the stages that didn't succeed.
- `python -m orchestrator.cli rerun <component>` — re-run a single stage (e.g. `rerun scoring`).
- A re-run **upserts** (never duplicates); the next scheduled run also self-heals a partial one.

**Rebuild a single derivation by hand** (no re-crawl needed):
- Lead scores: `python -m lead_scoring.run`
- Leadership signals: `python scripts/derive_leadership_signals.py`
- Engagement pitches: `python scripts/recommend_engagements.py`

**Common situations:**
- *Engines bot-blocked in CI* → run the pipeline from a scheduled container job instead (same command).
- *A stage failed but the issue alert didn't fire* → it was a caught stage failure (logged, not
  process-level). Check `/pipeline/status` and `pipeline_runs`, then `--resume`.
- *Bad data slipped in* → it's quarantined in the review queue, not in scored output; resolve there.
- *Wrong company mapping* → fix via a review-queue **alias** so it resolves correctly going forward.

---

## 11. Data Sources

| Source | Engine / origin | Owned master tables | How the platform reads it |
|---|---|---|---|
| **Industry Discovery** | `..\Industry_Discovery_Scraper_FINAL` | `companies` | `master_company_universe.xlsx` / CSV file output |
| **Blog Crawler** | `..\Blog_Scraper_FINAL` | `opportunities` | `blog_opportunities.jsonl` / CSV / xlsx file output |
| **Career Scraper** | `..\Career_Scraper_FINAL` | `jobs`, `demand_signals`, `company_rollups` | `career_*.xlsx`, `company_intelligence.xlsx` file output |
| **Decision Maker Intelligence** | Apify actor (API) | `decision_makers` | **Apify Decision Maker Intelligence engine over its API** (`APIFY_API_TOKEN`; see `config/apify.py`) |
| **Curated feeds** *(no crawler)* | hand-maintained `annual_lists.*` + `company_news.*` (Change_04/03) | `opportunities` (`ANNUAL_LIST` · `EXECUTIVE_HIRE`/`LEADERSHIP_CHANGE`/`ROLE_CHANGE`/`COMPANY_NEWS`) | file feed at the platform root / `data/` / Blog dir (`config/sources.py`); the `annual_list` + `company_news` stages ingest them (no-op when absent). Column contracts: HOW_TO_RUN §2 |

**Important distinctions:**
- The first three engines hand off via **files** the platform ingests. Decision Maker Intelligence is
  different — the platform calls the **Apify actor over its API** and ingests the returned records.
- Apify decision makers report the employer as a website (`organizationWebsite`); it's normalized to a
  bare `company_domain` and resolved against `companies` (kept NULL when the org isn't a tracked
  company). That's why `decision_makers.company_domain` is nullable.
- **Integration hazards the layer already reconciles:** `canonical_company_id` was computed two ways →
  recomputed centrally; `region_flag` means *compliance* (Industry/Blog) vs *geography* (Career) → two
  separate columns; Career dedups on `website` not `domain`, and three divergent domain normalizers
  existed → one canonical public-suffix-aware normalizer; service-provider competitors are dropped at
  ingestion.

The three **derivation** "sources" (scoring, leadership, engagement) are not external — they read the
master DB and write back derived tables.

---

## 12. Future Apify Migration Plan

**Context for the new engineer:** the **Decision Maker Intelligence** engine has **already been migrated
to [Apify](https://apify.com)** (the `decision_maker_intelligence` stage calls an Apify actor over its
API — see `config/apify.py` + `integration/ingestors/apify_source.py`). It is the **reference
implementation** for moving the remaining three crawlers (Industry / Blog / Career, still bespoke
Python with file outputs) onto managed Apify actors. This section is the migration *plan* for those
remaining engines.

**Why the platform is already well-positioned for this:**
- The platform reads engine **outputs**, never their internals (golden rule #1). Apify changes *how the
  data is produced*, not *what the master DB expects*.
- Ingestion is isolated behind `integration/ingestors/` (one ingestor per source) — the swap surface is
  small and well-bounded.
- The derivation stages (scoring, leadership, engagement) read only the master DB, so **they are
  completely unaffected** by an Apify migration.

**Recommended migration approach (incremental, one engine at a time):**
1. **Pick the friendliest engine first** — Career Scraper is the usual pain point (CI IP bot-blocks),
   so it's the best first candidate and the highest-value win.
2. **Build an Apify actor** that produces the **same output schema** the existing ingestor already
   consumes (e.g. the Career `*.xlsx` columns, or the Blog `jsonl` shape). Keeping the output contract
   identical means the ingestor needs **zero** changes — you're only changing the producer.
3. **Add a thin Apify client** that triggers the actor run and fetches its dataset, then either (a)
   writes the same file the ingestor reads, or (b) feeds records straight into the existing ingestor.
   Prefer (b) for direct sources — see `integration/ingestors/apify_source.py` for the working pattern.
4. **Wire it into the orchestrator as the stage's `EngineSpec`** — `orchestrator/stages.py` already
   models "how to run the upstream engine" per stage (`EngineSpec(cmd, cwd, …)`). Replace that command
   with the Apify trigger; the ingest half of the stage is untouched.
5. **Secrets:** add `APIFY_TOKEN` (and per-actor IDs) to the GitHub Actions secrets and
   `docs/DEPLOYMENT.md`'s secrets table, mirroring how `SP_SUPABASE_*` is handled.
6. **Cut over per engine, verified by `pipeline_runs`** — run the Apify-backed stage alongside the old
   one, compare row counts/quality in `pipeline_runs` + the coverage matrix, then retire the old
   crawler. Because ingestion is idempotent, running both during cutover just upserts.

**What to watch / decide:**
- **Output-schema fidelity is the whole game.** The migration is "safe" exactly to the degree the Apify
  actor reproduces the existing output columns. Any drift surfaces as ingestion rejects (logged in
  `pipeline_runs.rows_rejected`) — watch that number during cutover.
- **Scheduling ownership.** Apify has its own scheduler. You can either keep GitHub Actions as the
  trigger (it calls Apify, waits, ingests) or let Apify run on its schedule and have the pipeline ingest
  the latest dataset. The former keeps one source of truth for "a refresh happened"; prefer it unless
  Apify-native scheduling is specifically wanted.
- **The engagement engine's behavior under partial sources** is already documented
  (`docs/ENGAGEMENT_DEPENDENCIES.md`) — useful while one engine is mid-migration and its data is
  temporarily stale/empty: the platform degrades gracefully rather than breaking.
- **Cost/rate limits** move from "your IPs get blocked" to "your Apify bill / concurrency limits" —
  a better problem, but budget for it.

**Bottom line for the migration:** keep the engine *output contract* fixed, swap the *producer* behind
each `integration/ingestors/` boundary one engine at a time, drive it through the existing
`EngineSpec`/orchestrator seam, and verify via `pipeline_runs`. The master DB, the derivations, the
API, and the frontend should not need to change at all.

---

## Where to go next

| You want to… | Read |
|---|---|
| Run it locally | `HOW_TO_RUN.md` |
| Understand every column | `docs/SCHEMA.md` + `docs/ERD.md` |
| Deploy / operate it | `docs/DEPLOYMENT.md` (incl. operational runbook §7) |
| Change the website | `docs/FRONTEND_DESIGN.md` |
| Understand engagement-engine dependencies | `docs/ENGAGEMENT_DEPENDENCIES.md` |
| Tune lead-score weights | `config/lead_scoring.json` |
| See the big picture / status | `README.md` |
