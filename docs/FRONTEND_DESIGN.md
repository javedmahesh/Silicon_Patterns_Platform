# Frontend design spec (P6) — approved, build gated

Status: **IMPLEMENTED (2026-06-13).** The app lives in `../frontend/` (React 18.3 + Vite + TS + Tailwind v4 +
TanStack Query/Table + React Router + Recharts). Run: backend `python -m uvicorn backend.main:app --app-dir .. --port 8000`,
then `npm install && npm run dev` in `frontend/` (Vite proxies `/api` → :8000). This document remains the design
source of truth; the sections below describe what was built.
The backend API it consumes is `backend/` (schemas in `backend/schemas.py`).

## Build decisions (locked)
- **New `frontend/` app** under `Silicon_Patterns_Platform/frontend/` — separate from the
  LinkedIn recruiter app. Talks to the FastAPI over HTTP.
- **Stack:** React + TypeScript + Vite · TanStack Query (server state) · TanStack Table
  (virtualized grids) · React Router · Tailwind configured with the custom tokens below
  (no default theme / no UI kit) · lucide-react icons · Recharts (Analytics). Bespoke design
  system — not a template.
- **Build order:** foundations (scaffold + tokens + app shell + typed API client) →
  **Company Profile first** (the hub) → list pages → Dashboard/Analytics.
- API base via `VITE_API_BASE_URL` (dev: Vite proxy `/api` → `http://127.0.0.1:8000`).
  Send `X-API-Key` when the backend sets `SP_API_KEY`.

## Aesthetic
Dark enterprise — graphite/slate, high information density, hairline‑defined panels,
monospaced tabular numerals, one restrained azure accent. Reference points: Palantir Foundry,
Bloomberg Terminal, Apollo.io, Crunchbase Enterprise. **Avoid:** colorful cards, bootstrap
look, marketing layouts, generic admin dashboards.

## 4. Design system tokens
| Group | Tokens |
|---|---|
| Graphite bg | base `#0B0E12` · canvas `#0F1318` · surface `#161B22` · raised `#1C232C` · control `#222B35` |
| Hairlines | border `#262E38` · strong `#313B47` (borders define structure; almost no shadow) |
| Text | primary `#E7ECF2` · secondary `#97A3B2` · tertiary `#5C6878` |
| Accent | azure `#4C9AED` (interactive/active, used sparingly) |
| Grades | A+ `#3FB68B` · A `#5AA9E6` · B `#D2A33B` · C `#6B7785` |
| Semantic | positive `#3FB68B` · warning `#D9A33A` · danger `#E0625B` · info `#4C9AED` |
| Type | UI: Inter / system-ui · numerics: monospaced with **tabular figures** (scores/ids/counts) |
| Scale | 22/18/15 headers · 13 body · 12 dense table · 11 micro-label · weights **400/500 only** |
| Form | 4px grid · **28px table rows** · radii 2–6px (sharp) · motion 120–160ms, no bounce |

## 1. Information architecture
```
Triage:      Dashboard · Lead rankings (/leads)
Universe:    Companies (/companies) → Company profile (/companies/{domain})  ← the hub
Signals:     Opportunities (/opportunities) · Decision makers (/decision-makers)
Intelligence: Analytics (/analytics/summary)
System (ops): Review queue (/review-queue) · Pipeline health (pipeline_runs)
Outreach:    Overview · Leads · Pipeline · Approvals · Templates · Inbox (/outreach/* — native pages)
```
Every entity is a spoke; **Company Profile is where all five engines converge.** The **Outreach**
group is a **native** part of this SPA (`src/pages/outreach/*`) — no iframe, no separate app. Its pages
use the same design system, query layer (`useOutreach*` hooks) and `useAuth` role gating as the rest of
the console, and the same FastAPI backend (`/outreach/*`), reusing companies / decision makers / lead
scores / engagement — nothing duplicated.

## 2. Page hierarchy
- L0 app shell (nav rail · top bar · command palette ⌘K)
- L1 workspace pages (Dashboard, Lead rankings, Companies, Opportunities,
  Decision makers, Analytics)
- L2 detail: **Company profile** (the hero)
- L3 transient: entity peek drawer · filter panel · score-explanation popover · review/merge modal

## 3. Navigation
Collapsible left rail (56px icon → 220px labeled), grouped (Triage / Universe / Signals /
Intelligence / System), active = 2px left accent. Top bar: global search / command palette
(⌘K → jump to any company/person), a connection + pipeline-freshness badge (from `/health` +
`pipeline_runs`), saved views, density toggle. Row click → right-side peek drawer (triage
without leaving the list); "Open profile" navigates. URL-synced filters (shareable).

## 5. Component library
- Primitives: Button (primary/ghost/danger), IconButton, Input, Combobox, Select, Checkbox,
  Toggle, Tooltip, Chip, Badge.
- Data: `DataTable` (virtualized, sticky header, column manager, density toggle, multi-sort,
  inline filters, row select), `StatStrip` (thin KPI row — not big cards), `Sparkline`,
  `ScoreBar`, `GradeBadge`, `DistributionBar`, `TrendDelta`, `NumericCell` (tabular).
- Score: `ScoreExplanation` (4 subscore bars + weights → multiplier chips → final, waterfall),
  `MultiplierChip`, `MissingInputsCallout`, `RationaleViewer` (humanizes the `rationale` JSON).
- Profile: `ProfileHeader`, `SignalTimeline` (dated event feed), `SectionPanel`, `KeyValueGrid`,
  `DecisionMakerRow`, `OpportunityRow`, `LeadershipSignalRow`, `EngagementStrategy`,
  `LeadReviewPanel` (the Human Review & Assessment panel — model vs human + editor + audit trail),
  `RecognitionCard` (annual-list / ranking appearances, Change_04), `CollapsibleSection`,
  `DataCoverage` (which engines contributed + freshness).
- Human review: `HumanStatusBadge` (review-status pill, shared by the lead table / profile / reports),
  `ReviewInsights` (the model-vs-human reports + **score-adjustment analytics** on Analytics). Status
  labels/tones + the score-affecting set live in `lib/reviewStatus.ts`. The lead table also shows an
  **Adj.** grade column (the adjusted grade when a review moved it).
- Shell: `AppShell`, `NavRail`, `TopBar`, `PageHeader`, `FilterBar`, `PeekDrawer`,
  `CommandPalette`, `EmptyState`, `Skeleton`, `Toast`.
- System: `ReviewQueueItem`, `PipelineHealthStrip`, `ConnectionBadge`.

## 6. User flows
1. Triage: Dashboard → top A/B leads + fresh signals → open lead → profile → read score
   explanation → action (watch/list/export).
2. Prospecting: Companies → filter (tier, prospect, grade ≥ B, has decision-makers) → save
   view → profile → people → export.
3. Signal-driven: Opportunities (new funding) → company → people → prioritize.
4. Leadership-driven: Decision makers → recent director+ moves (Leadership Signals) → company → outreach.
5. People-driven: Decision makers → seniority + company → outreach.
6. Data quality: Review queue → approve/merge/reject/alias (the `/review-queue` endpoints).
7. Analytics: Analytics → grade distribution / coverage / funnel → click segment → filtered list.

## 7. Desktop layouts
- List pages: PageHeader + sticky FilterBar (chips) + full-height virtualized DataTable +
  right peek drawer on row click.
- Dashboard: thin stat strip (companies/leads/grades/opps/decision-makers/leadership-moves) →
  grid of priority-leads table · latest-opportunities feed · recent-leadership-signals feed ·
  pipeline-health strip · grade-distribution mini chart.
- Analytics: chart grid (grade dist · coverage matrix · pipeline funnel · tech-focus heatmap ·
  geography) with cross-filtering (click a segment → drill to a filtered list).

## Company Profile — the hero (most important page)
Header band: monogram · name · domain (↗) · chips (tier, prospect_type, compliance·country,
validation) | **Lead score block** (big grade + score + priority rank) | actions (watch, add to
list, export). In-page tabs: Overview · Score · Opportunities · People · Timeline. The Overview hosts a
collapsible **Leadership Signals** dropdown (director+ moves).

- **Recommended Engagement Strategy** (top, full-width): the sales-pitch recommendation — likely
  business need · recommended offering · one-line pitch · confidence · rationale (the evidence used).
- **Human Review & Assessment** (top, full-width): the **model** verdict, the **adjusted** verdict
  (the optional review→score adjustment — model when off), and the **human** verdict (review status +
  reason) side by side — the human assessment never overwrites the model score — with a status picker
  (Approved / Needs Review / Strategic Account / Disqualified / Watchlist) + reason editor (required +
  manager-gated for score-affecting statuses when enabled), an optional expiry, an "expired" indicator,
  and the append-only review-history audit trail (snapshotting model→adjusted).
- Left column (~60%):
  - **Score explanation**: 4 subscore bars (opportunity/demand/readiness/decision-maker) with
    weights → multiplier chips (region/prospect/tier) → `base × mults = final → grade`, plus a
    "missing inputs" callout. (Drives from `lead_score.rationale`.)
  - **Signal timeline**: dated event feed (scored, classified, opportunities…).
- Right column (~40%):
  - **Company facts** (KeyValueGrid: HQ, founded, category, tech focus, website, source, confidence).
  - **Decision makers** (compact rows; honest empty state when none resolved — with a "run
    Decision Maker Intelligence" CTA).
  - **Data coverage**: which engines contributed (Industry/Blog/Career/Decision Maker Intelligence) + last scored.

It must combine: company data · lead score · opportunity signals · leadership signals · decision
makers · timeline · score explanation — on one screen. The profile should surface data *gaps*
(missing inputs, empty states), not hide them.

## 8. Mobile strategy
Desktop-first analytical tool; mobile = companion/triage.
- ≥1440 optimal density (60/40 profile split, peek drawer) · 1024–1440 rail auto-collapses ·
  768–1024 (tablet) 2-col→1-col, drawer→full-width sheet · <768 (phone) bottom tab bar
  (Dashboard·Leads·Companies·Search·More), **tables → stacked record cards** (grade/score/tier +
  key signal), profile sections → accordion, heavy analytics deferred to desktop, ⌘K → full-screen search.

## API mapping (pages → endpoints; all return paginated `{items,total,page,page_size,pages}`)
Dashboard → `/analytics/summary` + `/leads` · Lead rankings →
`/leads?grade&tier&prospect_type&sort` (`sort=model|human|combined`) · Companies →
`/companies?q&domain&tier&prospect_type&grade&sort&order` · Company profile →
`/companies/{domain}` (the unified bundle — includes `lead_review` + `lead_review_history`) ·
Opportunities → `/opportunities?opportunity_type&company_domain&date_from&date_to` ·
Decision makers → `/decision-makers?company_domain&seniority` · Leadership signals →
`/leadership-signals?company_domain&movement_type&seniority_band&source` · Human review →
`GET/PUT /reviews/{domain}` (+ `/{domain}/history`, `/reports`) · Analytics →
`/analytics/summary` + `/reviews/reports` · Review queue → `/review-queue` (+ approve/merge/reject/alias POSTs).

## Mockups delivered (rendered in the design review)
1. Design-system tile (tokens + components). 2. Lead-rankings table (nav rail · filter chips ·
dense table · multi-engine signal dots). 3. Company-profile hero (all regions above). These were
visual artifacts in the review; this doc is their textual spec.
