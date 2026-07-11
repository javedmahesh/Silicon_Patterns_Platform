# Silicon Patterns Platform

Unifies the four existing scraper engines into **one intelligence platform**, joined on the
universal key **`company_domain`** (never `company_name`). It turns four disconnected data
sources into a single, ranked, explainable view of which semiconductor / AI-silicon companies
to pursue and *why*.

```
Industry Discovery → Blog Crawler → Career Scraper → Decision Maker Intelligence → Lead Scoring → Leadership Signals → Sales-Pitch Recommendations → Website
   (finds            (finds          (finds            (Apify: finds              (ranks        (unified
    companies)       opportunities)  hiring demand)    decision makers)           leads A–C)     console)
```

The upstream engines are **never modified** — the platform reads the three crawlers' outputs in
place and calls the Apify Decision Maker Intelligence engine for decision makers, resolves
everything to a canonical company, scores it, serves it over an API, and presents it in a
dark, dense analyst web console.

> **▶ To run it, see [`HOW_TO_RUN.md`](HOW_TO_RUN.md).** This file explains *what it is*; that
> file explains *how to run it*. To **deploy** it (Vercel + dedicated Postgres + a twice-daily
> scheduled refresh), see [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
>
> **▶ New to the codebase?** Start with [`HANDOVER_GUIDE.md`](HANDOVER_GUIDE.md) — a single
> orientation doc (architecture, schema, pipeline, scoring/leadership/engagement logic, review
> system, deploy/recovery, data sources, and the future Apify migration plan).

---

## What you get

- **Master company database** — one row per company (`company_domain` PK), with every engine's
  data attached: opportunities, jobs, demand signals, decision makers, leadership signals, and a lead score.
- **Canonical resolution** — "Groq", "Groq Inc.", "GROQ" all resolve to `groq.com`; unmatched
  records become low-confidence stubs in a **review queue** so the pipeline never blocks.
- **Lead scoring** — a transparent, tunable formula → grades **A+ / A / B / C**, with a full
  rationale for every score.
- **Sales-pitch recommendations** — for each company, an evidence-grounded **Recommended Engagement
  Strategy**: a likely business need, the matching Silicon Patterns offering, and a one-line pitch,
  with a confidence score and the signals that produced it (deterministic — no LLM, no boilerplate).
- **Human review & feedback** — analysts can record a **human assessment** of any lead (Approved /
  Needs Review / Strategic Account / Disqualified / Watchlist) with a reason — **stored separately, so
  the model score is never overwritten**. Both verdicts show side by side (lead table + Company
  Profile), leads can be ranked by **model · human · combined priority**, every change is kept in an
  append-only **feedback/audit trail** (snapshotting the model grade at the time), and Analytics
  reports the **model-vs-human disagreements, frequent overrides, strategic accounts, and false
  positives/negatives**. Optionally (config `review_feedback`, **OFF by default**) a review can drive a
  **separate adjusted score/grade** (strategic/approved → boost + grade floor; disqualified → penalty)
  — the model score still never changes; score-affecting verdicts then require a reason + manager/admin,
  can carry an expiry, and never compound.
- **Backend API** — FastAPI over the master DB; the `/companies/{domain}` endpoint returns the
  whole unified profile in one call. Ops/analytics endpoints: `/analytics/coverage`
  (engine-coverage matrix), `/pipeline/health` + `/pipeline/runs` (run freshness/history).
  Optional API-key gate + per-IP rate limit for production. Analytics responses carry an **ETag**
  and are memoized on the last-refresh timestamp — repeat loads return instantly (or a 304)
  between refreshes, since the data only changes twice a day.
- **Website** — a React analyst console: Dashboard, Lead rankings, Companies + Company Profile
  (the hub), Opportunities, **Decision makers** (the senior decision makers —
  CxO / founder / VP / director — grouped by company; the people to reach out to, plus a
  **Leadership signals** feed of director+ moves — hires, departures, promotions), Review queue,
  Analytics, Workspace, a side-by-side **Company Compare** (pin companies → compare), plus
  **My leads** and a manager **Team** console.
- **Outreach module** — a **native** module on the platform stack (FastAPI + the React SPA + the master
  DB), under `/outreach/*`: a CRM pipeline, `{{variable}}` email templates, draft → approval → send →
  reply, an inbox and funnel analytics. It **reuses** the platform's companies, decision makers, lead
  scores and engagement recommendations (no duplicated data) and the platform's Google-SSO/roles (no
  separate auth). "Sync from Discovery" qualifies top-scored companies into the pipeline. Email send/receive
  is **mock by default** (`OUTREACH_MAIL_MODE=mock`); real Gmail is a drop-in behind the same interface.
- **Accounts & access** — Microsoft Entra ID sign-in (company domain only) + app JWTs; roles
  **admin / manager / member**. A manager **Team console** (assign leads **with a note for the
  assignee**, workload dashboard, expanded pipeline statuses) with a full **assignment audit
  trail**, **company notes + an activity timeline**, and **My leads** per user — where each
  assignee sees that note and who assigned it. Accounts are deactivated, never deleted, so the
  audit history survives. *(In dev, an auth bypass + role switcher runs without Microsoft — see HOW_TO_RUN §10.)*
- **Professional contacts** — capture **work email / phone / notes** for senior decision makers
  (view: any signed-in user; **edit: admin/manager**). Professional fields only — no personal
  addresses, emails, or phone numbers.
- **Annual lists / rankings** — a curated feed (Fortune 500, Forbes AI 50, CNBC Disruptor 50, EE Times
  Silicon 100, …) is ingested as `ANNUAL_LIST` opportunities (rank in `company_news_signal`), so it
  flows into the Opportunities views + the opportunity sub-score and surfaces as a **Recognition &
  rankings** card on the Company Profile.
- **Company news / people moves** — a Blog-enrichment feed ingests executive hires, leadership & role
  changes (`EXECUTIVE_HIRE` / `LEADERSHIP_CHANGE` / `ROLE_CHANGE` / `COMPANY_NEWS`) as opportunities, so
  they show in the timeline + nudge the opportunity sub-score — and **director+ moves automatically feed
  the person-level Leadership Signals** (the blog-event path).
- **News Intelligence** — the News Collection Engine (`integration/news/`) adds pluggable **multi-source
  adapters** (RSS, Google Alerts, file, future), **intelligent deduplication** (canonical URL + normalized
  title + semantic similarity + company + time + entities — all reporting sources kept under one
  opportunity; different events stay separate), and **deterministic multi-signal AI extraction** (one
  article → several opportunities: acquisition + expansion + hiring). Each opportunity carries executive/AI
  summaries, why-this-matters, business impact, technologies/products/people/organizations/countries/keywords,
  type + subtype, confidence + per-factor breakdown, source credibility, and AI reasoning — shown in an
  expandable **opportunity detail modal**. A **lifecycle** (New/Active/Monitoring/Resolved/Archived) and
  **manual review** (mark not-relevant, merge, split, change type, archive/restore, internal notes — recorded
  as history, never overwriting the AI outputs) round it out. Refresh regenerates only Opportunities/news
  signals via `python scripts/refresh_news_opportunities.py` (companies, users, lead scores, career data,
  and config are never touched).
- **Competitor exclusion** — service-provider competitors are blocked at ingestion and never
  stored (plus a purge script for any that predate the rule).
- **Orchestrator** — one command (`sp-platform run all`) runs the engines → ingest → score → derive leadership signals → recommend engagements, with
  run tracking, health, resume/recovery, and scheduling help.

---

## The four engines (three crawlers in sibling folders + Apify Decision Maker Intelligence)

| Engine | Folder | Owns (master tables) | Source the platform reads |
|---|---|---|---|
| Industry Discovery | `..\Industry_Discovery_Scraper_FINAL` | `companies` | `master_company_universe.xlsx` / CSV |
| Blog Crawler | `..\Blog_Scraper_FINAL` | `opportunities` | `blog_opportunities.jsonl` / CSV / xlsx |
| Career Scraper | `..\Career_Scraper_FINAL` | `jobs`, `demand_signals`, `company_rollups` | `career_*.xlsx`, `company_intelligence.xlsx` |
| Decision Maker Intelligence | Apify actor (API) | `decision_makers` | Apify Decision Maker Intelligence engine (`APIFY_API_TOKEN`) |
| **Lead Scoring** (new) | this folder | `lead_scores` | consumes all of the above |

Each engine stays independently executable; the platform also runs them as one pipeline.
**Service-provider competitors are filtered out at ingestion** (`prospect_type =
SERVICE_PROVIDER`) and never stored in the master DB.

---

## Architecture

```
 engines ──► integration (ingest + resolve) ──► master DB ──► lead scoring
                                                    │
                                          backend API (FastAPI)
                                                    │
                                          frontend (React website)

 orchestrator (sp-platform) drives engines → ingest → score, with run tracking + health
```

- **Master DB** → its **own dedicated PostgreSQL** in production (`DATABASE_URL`); local dev
  falls back to a SQLite file (`master_local.db`). Separate from every engine's storage.
- **Decision Maker Intelligence (Apify)** → the platform's decision-maker engine. The
  `decision_maker_intelligence` stage calls the Apify actor (`APIFY_API_TOKEN`) and ingests the
  results into `decision_makers`. See `.env.example` / `config/apify.py`.
- **Resolver** → exact-domain / alias / fuzzy match; fuzzy uses difflib on SQLite and a
  **GiST trigram KNN** index on Postgres (migration `0006`). Unmatched ⇒ stub + review queue.
- **Idempotent ingestion** → upserts keyed on `company_domain` · `opportunity_id` · `job_id` ·
  `linkedin_url`; bulk `ON CONFLICT` upserts (~60× faster than per-row on Postgres).

---

## Tech stack

- **Backend / pipeline:** Python 3.13, SQLAlchemy 2.0, FastAPI, Typer + Rich (CLI), pydantic-settings, openpyxl.
- **Database:** PostgreSQL (prod) / SQLite (dev), hand-written SQL migrations mirrored by SQLAlchemy ORM.
- **Frontend:** React 18 + TypeScript + Vite, Tailwind v4 (custom graphite tokens), TanStack
  Query + Table, React Router, Recharts, lucide-react. Dark enterprise theme. The API contract
  (`src/lib/api/schema.ts`) is **generated from the backend OpenAPI schema** (`npm run gen:api-schema`),
  so the client types can't drift from `backend/schemas.py`.

---

## Repository layout

```
Silicon_Patterns_Platform/
├── backend/          FastAPI app: routers → services → repositories → database → config + security (SSO/JWT/RBAC)
│   └── routers/      health · auth · companies · leads · opportunities · demand-signals · decision-makers · leadership-signals · analytics · pipeline · review · reviews · admin · assignments · crm
├── integration/      normalizer · resolver · merge · per-engine ingestors
│   └── ingestors/
├── master_db/        SQLAlchemy models + SQL migrations (0001–0016) + chunked bulk upsert
│   └── migrations/
├── lead_scoring/     config (tunable weights) · scorer (pure math) · service · run
├── orchestrator/     sp-platform CLI · pipeline stages · run tracking · health
├── frontend/         the website (React + Vite + TS) — see frontend/ and docs/FRONTEND_DESIGN.md
├── config/           engine paths · canonical enums · scoring weights · employer/enrichment seeds · supabase creds
├── scripts/          seed_master_db.py (fixtures -> full dev DB) · validate_postgres.py · build_convergence_seed.py · dump_openapi.py (OpenAPI -> TS types) · purge_service_providers.py · backfill_classification.py · derive_leadership_signals.py · recommend_engagements.py
├── docs/             SCHEMA · ERD · SECURITY · DEPLOYMENT · FRONTEND_DESIGN · supabase_rls.sql
├── .github/workflows/ refresh.yml (twice-daily scheduled pipeline)
├── Dockerfile · render.yaml · .dockerignore   read-API container (Render/Railway/Fly/Cloud Run)
├── tests/            pytest suite (180 tests)
├── master_local.db   local SQLite master DB (dev seed data — ships with the repo)
├── requirements.txt  pip deps  ·  pyproject.toml  (installable; exposes `sp-platform`)
├── README.md         this file
└── HOW_TO_RUN.md     run instructions
```

## Master schema — data layer + multi-user layer (all joined on `company_domain`)

**Data layer:** `companies` · `company_sources` · `company_aliases` · `resolution_review_queue` ·
`opportunities` · `jobs` · `demand_signals` · `company_rollups` · `decision_makers` ·
`leadership_signals` · `engagement_recommendations` · `lead_scores` · `lead_reviews` ·
`lead_review_events` · `ingestion_runs` · `pipeline_runs` · `review_actions`.
**Multi-user layer (migrations `0007`–`0010`):** `users` · `lead_assignments` ·
`lead_assignment_events` · `company_notes` · `decision_maker_contacts`.
Full DDL in `master_db/migrations/`; column-level notes in `docs/SCHEMA.md` + `docs/ERD.md`.

---

## Lead scoring (how grades are produced)

```
weighted = 0.30·opportunity + 0.30·demand + 0.20·readiness + 0.20·decision_maker
base     = weighted / (present_signal_weight ^ coverage_normalization)   # coverage-normalized
final    = clamp( base × region_mult × prospect_mult × tier_mult , 0, 100 )
grades:  A+ ≥ 70 · A ≥ 50 · B ≥ 30 · C otherwise
```

- **Coverage-normalized** — absent signals aren't counted as zeros, so a perfect-fit company with
  one strong signal ranks on merit (e.g. Tenstorrent → A+) instead of being capped at B. Full-coverage
  companies are unchanged; set `coverage_normalization: 0` for the legacy weighted average.
- **Confidence** — each score records how many of the 3 engine signals (opportunity / demand /
  decision-makers) backed it → a **Low / Medium / High** badge in the UI, so a thin-evidence A+ is
  told apart from a fully-backed one.
- **Fit multipliers** (`region × prospect × tier`) down-weight poor-fit companies. Companies the
  engines surfaced without a tier are backfilled from their own ingested rows
  (`scripts/backfill_classification.py`) before scoring.

Every subscore, multiplier, coverage/confidence, missing input, and the final value is stored in a
`rationale` JSON — exactly what the website's **Score explanation** panel renders, so every grade is
auditable. All weights / multipliers / bands are tunable in `config/lead_scoring.json` (re-run
`python -m lead_scoring.run`).

---

## Integration hazards the layer handles

- `canonical_company_id` was computed two different ways across engines → recomputed centrally.
- `region_flag` = a **compliance flag** (Industry/Blog) vs a **geographic region** (Career) → two columns.
- Career dedups on `website`, not `domain`; three divergent domain normalizers existed → one
  canonical, public-suffix-aware normalizer.
- Apify decision makers report the org as a website (`organizationWebsite`) → normalized to a bare
  `company_domain` and resolved against `companies` (kept NULL if the org isn't a tracked company).

---

## Status

**Complete (P0–P6) + the multi-user epic + person-level leadership signals + engagement
recommendations.** Integration, resolver, lead scoring, FastAPI backend, orchestrator CLI, and the
React website are all built and working. On top of that the platform is now **multi-user**: Google
Workspace SSO + app JWTs; **admin / manager / member** roles; a manager **Team console** (lead
assignment, workload, pipeline statuses) with a full assignment **audit trail**; **company notes +
an activity timeline**; **My leads**; **professional contacts** for decision makers (view: any
signed-in user; edit: admin/manager); and **service-provider competitor exclusion** enforced at
ingestion. Lead scoring is **coverage-normalized with a Low/Med/High confidence flag** (a strong
company isn't buried for missing a signal). Two platform derivations layer on top — **person-level
director+ leadership signals** and an evidence-grounded **engagement (sales-pitch) recommendation**
per company — each running as an automatic pipeline stage. A **human review & feedback** layer lets
analysts override the model's verdict **without overwriting the score** (separate human assessment +
status, combined ranking, an append-only feedback trail, model-vs-human reports, and an optional
OFF-by-default **adjusted score** that boosts/penalises a *separate* grade). An **annual-lists**
ingestor adds ranking appearances as opportunities (with a Recognition card), and a **company-news**
ingestor adds people moves (feeding the Leadership Signals). The backend (migrations `0001`–`0016`,
pg_trgm resolver, bulk upserts, API, scoring, orchestrator) is **validated end-to-end against real
PostgreSQL**; the frontend is built and verified live against the local master DB. **180 tests pass.** *(Dev runs behind an auth bypass + role switcher until Google SSO is wired at
deployment — see [`HOW_TO_RUN.md`](HOW_TO_RUN.md) §8.)*

Local sample data (`master_local.db`): 122 companies (competitor-free) · 43 opportunities · 188
jobs · 6 demand signals · 188 decision makers · 122 scored leads · grades **A+ = 17 / A = 13 /
B = 10 / C = 82** (top: Tenstorrent, A+ 99.1 — coverage-normalized, flagged *Low* confidence as it
has a single strong signal).

**Improving lead quality:** with the current sample data the engines cover *different* companies,
so most carry only one signal and scores stay low — visible in **Analytics → Company coverage**.
Run `python scripts/build_convergence_seed.py` and re-crawl the engines over the shared seed to
converge them (see `HOW_TO_RUN.md` → *Engine convergence*); multi-signal A/B leads follow.

See `HOW_TO_RUN.md` to run it, and `docs/` for schema, security, and frontend design.
