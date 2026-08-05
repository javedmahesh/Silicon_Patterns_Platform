# Master Database — Schema Reference

**131 tables** (join key everywhere **`company_domain`**, normalized registrable
domain). The two layers documented below are the **data layer** — engine outputs +
resolution + scoring + the platform-intelligence tables (leadership signals,
engagement recommendations, human reviews) + orchestrator audit — and the
**multi-user layer** (accounts, lead-assignment CRM, professional contacts — added
by migrations `0007`–`0010`). The remainder are the later Enterprise CRM, outreach,
historical-import, ML, notification, market-discovery and market-intelligence layers
(migrations `0011`–`0058`), which are not detailed
here; see `master_db/migrations/*.sql` for the exact DDL and `master_db/models.py`
for the authoritative definitions. Owners in brackets. `docs/ERD.md` covers
relationships.

## companies  *[Industry Discovery]*
The hub. PK `company_domain`. Holds identity, geography, classification,
provenance and quality. The resolver may insert low-confidence **stub** rows
(`is_stub=true`, `validation_status='STUB'`) for domains seen by other engines
before Industry Discovery catalogues them.

Key columns: `company_domain` (PK), `canonical_company_id`, `company_name`,
`name_key`, `website`, `company_linkedin`, `country`/`city`/`headquarters`,
`compliance_flag`*, `industry_category`, `technology_focus`, `prospect_type`,
`company_tier`, `company_status`, `confidence_score`, `validation_status`,
`is_stub`, `created_at`, `updated_at`.

\* `compliance_flag` ∈ {APPROVED, EXCLUDED_REGION, REVIEW_REQUIRED, UNKNOWN} —
a compliance signal, **not** a geographic region.

## company_sources  *[Industry Discovery]*
Provenance, many per company. `(company_domain, source_name)` unique.

## company_aliases  *[resolution layer]*
`name_key → company_domain`. Powers canonical resolution; `(name_key,
company_domain)` unique. Grows automatically as new spellings are matched.

## resolution_review_queue  *[resolution layer]*
Stub-created and unresolved records awaiting human confirm/merge. Columns:
`raw_name`, `raw_domain`, `raw_website`, `source_engine`, `source_record_ref`,
`suggested_domain`, `match_type`, `confidence`, `status`, `resolved_domain`.

## opportunities  *[Blog Crawler]*
One row per article/event. PK `opportunity_id` (`OPP-<sha1>`). `company_domain`
**NOT NULL**. Carries event provenance, opportunity classification, funding/tech
mentions, ecosystem partners, scores, and Blog's own `lead_readiness_score`
(an *input* to Lead Scoring). Also home to platform-curated **annual-list
appearances** (Change_04: `opportunity_type='ANNUAL_LIST'`, `opportunity_category`
= the list name, `LST-<sha1>` PK) so rankings flow into the same views + the
opportunity sub-score. `0016` adds a shared **`company_news_signal`** column — a
one-line signal: the list rank ("Rank: N") for annual lists, and (Change_03) a
one-line summary for company-news moves.

## jobs  *[Career Scraper]*
One row per posting. PK `job_id` (hash of domain+url). `(company_domain,
job_url)` unique. `geo_region` is the Career "region_flag" (a **geographic**
region) — a different column from `companies.compliance_flag`.

## demand_signals  *[Career Scraper]*
1:1 per company (PK = `company_domain`). Per-discipline job counts
(rtl/asic/verification/physical_design/dft/sta/validation/fpga/embedded/
architecture), `demand_score`, `normalized_demand_score`, `hiring_trend`,
`lead_readiness_score` (Career's own — an *input* to Lead Scoring).

## company_rollups  *[Career Scraper]*
1:1 per company. Maps `company_intelligence.xlsx` — the sales-ready demand
summary. `priority_rank` here is Career's own A/B/C, distinct from
`lead_scores.grade`.

## decision_makers  *[Apify Decision Maker Intelligence]*
PK `id`; `linkedin_url` unique. `company_domain` **NULLABLE** (resolved from the
org website; `ON DELETE SET NULL`). Person fields + `profile_data` JSONB +
`match_score`/`agent_score`/`status`. `0018`/`0019` add **structured professional
columns** sourced from the actor — `full_name`, `functional_area`, `work_email`,
`email_status`, `work_phone`, `city`, `state_region`, `country`,
`organization_website`, `organization_linkedin` — all **NULLABLE** (a field the actor
doesn't return stays NULL, never a placeholder). The full, unmodified actor record is
preserved in `profile_data.raw` for future enrichment (plus curated keys incl.
`organization_id`, `industry`, `company_size`, `functional`, `all_emails`).

## lead_scores  *[Lead Scoring service]*
1:1 per company. `lead_score`, `grade` (A+/A/B/C), `priority_rank`, the four
component subscores (`opportunity`/`demand`/`readiness`/`dm`), the three
multipliers (`region`/`prospect`/`tier`), `coverage` (0-3 engine signals that
backed the score) + `confidence` (low/medium/high — `0011`), and a `rationale`
JSONB so every grade is explainable. The base is **coverage-normalized** (divided
by the weight of the signals actually present), so a strong company is not diluted
by the engines it is missing. *Populated in P3.* — `0015` adds **`adjusted_score`** +
**`adjusted_grade`** (the optional human-review adjustment, reconciled Change_05): a
SEPARATE value derived from the company's `lead_reviews.review_status` — the model
`lead_score`/`grade` are **never** modified. `adjusted_*` is NULL/'' (== model) unless
`review_feedback` is enabled in `config/lead_scoring.json` (OFF by default); when set,
`rationale.adjustment` snapshots the boost/penalty/floor + reason + reviewer.

## leadership_signals  *[Leadership Signals — platform, P-task 8]*  — `0012`
Person-level **director+ leadership movement** (*who* moved) — distinct from the
Blog Crawler's company-level `Leadership Change` *opportunity* (that an event
happened). PK `signal_id`; `company_domain` **NULLABLE** (`ON DELETE CASCADE`);
optional `decision_maker_id` FK→decision_makers (`SET NULL`). `movement_type`
(promotion / role_change / new_executive_hire / executive_departure /
board_appointment / founder_change / executive_reshuffle), `seniority_band`
(c_level / president / founder / managing_director / evp / svp / vp /
senior_director / director / head_of), `from_title`/`to_title`, `effective_date`
(YYYY-MM), `event_age_days`, `confidence` (low/medium/high), `source`
(`snapshot_comparison` — movement detected between consecutive decision-maker
snapshots from the Apify engine · `blog_event` — extracted from the legacy
`Leadership Change` opportunity AND the Change_03 company-news people-move types
`EXECUTIVE_HIRE`/`LEADERSHIP_CHANGE`/`ROLE_CHANGE`, parsed from their structured
`company_news_signal` · `linkedin_history` — legacy, derived from a decision
maker's `profile_data` career history where present). **Director-level
and above only** (manager-level and ICs are gated out). Derived (idempotent, no
re-crawl) by `scripts/derive_leadership_signals.py`.

## engagement_recommendations  *[Engagement engine — platform, P-task 9]*  — `0013`
One sales-pitch recommendation per company (1:1). Platform-derived from the company's own signals
(opportunities, leadership, demand/jobs, technology, partnerships, funding, company type, decision
makers) into `business_need` + `offering` (a Silicon Patterns service) + a one-line `pitch`, with
`confidence` (0-100) + `confidence_label` (low/medium/high) + a `rationale` JSON array of the evidence
used + `signals_used`. **Evidence-grounded + deterministic (no LLM)**; companies with no signals get no
row. Recomputed every refresh by the `engagement` orchestrator stage
(`scripts/recommend_engagements.py`). Signal dependencies + graceful-degradation behaviour (what
happens if Career / Decision Maker Intelligence / Blog / Apify are unavailable): `docs/ENGAGEMENT_DEPENDENCIES.md`.

## lead_reviews  *[Human review — platform, P-task viii]*  — `0014`
A human analyst's assessment of a lead (1:1 per company), kept **strictly separate
from `lead_scores`** — it never overwrites the model score/grade. `company_domain`
PK FK→companies (`ON DELETE CASCADE`), `review_status` ∈ LEAD_REVIEW_STATUSES
(approved / needs_review / strategic_account / disqualified / watchlist),
`human_notes` (the reason), `reviewed_by`/`reviewed_by_email` (attribution),
`created_at`/`updated_at`, plus (`0015`) **`reviewed_at`** and an optional
**`expires_at`** (after which the *score* effect lapses — the assessment + audit
remain). Open to any authenticated user (analyst feedback, like `company_notes`) —
**except** that, when `review_feedback` is enabled, a **score-affecting** status
(strategic_account / approved / disqualified) requires a **reason + manager/admin**.
The model verdict and the human verdict are read side by side.

## lead_review_events  *[Human review feedback/audit — platform, P-task viii]*  — `0014`
Append-only **feedback + audit trail** for human lead reviews (the "feedback table"
of the task). One row per review action: `company_domain`, `actor_user_id`/
`actor_email`, `from_status`→`to_status`, `notes`, and a **snapshot of the model
`model_grade`/`model_score`** — plus (`0015`) the **`adjusted_grade`/`adjusted_score`**
— at the time of the action (so disagreement + adjustment reports stay correct as the
model re-scores, and a future version can learn from the feedback — today the platform
only records it, it never retrains or modifies scores). Soft references (no FK) so the
trail survives user/company removal.

## ingestion_runs  *[Orchestrator]*
One row per engine/ingestion run: counts (`rows_in`/`upserted`/`rejected`/
`review_queued`), `status`, timing. Powers incremental updates + audit.
*Populated in P5.*

---

## Multi-user layer (accounts · CRM · contacts) — migrations `0007`–`0010`

### users  *[auth]*  — `0007`, lifecycle `0021`
App accounts. `id` PK; `email` unique (lower-cased); `full_name`, `picture`;
`role` CHECK ∈ USER_ROLES (default `member`; UI label "Employee"); `created_at`,
`last_login_at`, `last_seen_at`. `0021` adds the **account lifecycle**: `status`
CHECK ∈ USER_STATUSES (pending/active/disabled/rejected/deleted), `login_count`,
`deleted_at`. `is_active` is kept as the fast auth gate, held true only when
`status='active'`. Provisioned on first Google sign-in (`@siliconpatterns.com`
only) as **pending** awaiting admin approval — except `SP_ADMIN_EMAILS`, which
bootstrap as active admins. Deletion is a **soft delete** (status `deleted`, PII
scrubbed, row retained for audit/FK integrity).

### user_audit_events  *[auth audit]*  — `0021`
Append-only trail of account actions. `id` PK; `target_user_id`/`actor_user_id`
FK→users (SET NULL) + denormalized emails; `action` CHECK ∈ USER_AUDIT_ACTIONS
(registered/login/approved/rejected/enabled/disabled/role_changed/deleted);
`detail`; `created_at`. Surfaced in the admin User Management → Audit log.

### lead_assignments  *[CRM]*  — `0008`
A company assigned to a user. `id` PK; `company_domain` FK→companies (CASCADE);
`user_id` FK→users (CASCADE); `assigned_by`; `status` CHECK ∈ ASSIGNMENT_STATUSES
(default `assigned`); `note`; `created_at`/`updated_at`; **UNIQUE(company_domain,
user_id)**.

### lead_assignment_events  *[CRM audit]*  — `0008`
Append-only audit trail (mirrors `review_actions`). `id` PK; `assignment_id` /
`company_domain`; `actor_user_id`; `action` ∈ ASSIGNMENT_EVENTS; `from_value`,
`to_value`, `detail`; `created_at`. Every assign / reassign / unassign / status or
note change writes one row — **retained even if the user is later deactivated**.

### company_notes  *[CRM]*  — `0009`
Free-text notes on a company. `id` PK; `company_domain` FK→companies (CASCADE);
`author_user_id`; `body`; `created_at`. Surfaced (with assignment events) in the
company's `/companies/{domain}/activity` timeline.

### decision_maker_contacts  *[contacts]*  — `0010`
**Professional** contact details for a decision maker (1:1). `id` PK;
`decision_maker_id` FK→decision_makers (CASCADE, **UNIQUE**); `work_email`,
`work_phone`, `notes`; `added_by` / `added_by_email` (audit); `created_at`/
`updated_at`. **Work email/phone only — no personal addresses, personal email, or
personal phone** (privacy/legal scope). View: any authenticated user; **edit:
admin/manager only**. When no row exists, `GET …/contact` falls back to the
decision maker's engine-sourced `work_email`/`work_phone` (`from_source=true`). The
legacy `notes` blob is retained but superseded by `decision_maker_notes` (below).

### decision_maker_notes  *[collaboration notes]*  — `0018`, tiers widened `0022`
Four-tier notes on a decision maker. `id` PK; `decision_maker_id` FK→decision_makers
(CASCADE); `note_type` ∈ {`admin`,`manager`,`team`,`personal`} (`CHECK`, widened in
`0022`); `created_by` FK→users (`SET NULL`); `author_email`; `content`;
`created_at`/`updated_at`. Visibility/create/edit (app-enforced in `backend.services`):
**`admin`** — create by admins; pinned first; visible to all. **`manager`** — create by
admin/manager; visible to all. **`team`** — create by **any** authenticated user;
visible to all. **`personal`** — private to its author; author-only edit/delete (others
never see it). Edit/delete: admin→admin-tier or author; manager/team→manager-tier or
author; personal→author only. `GET …/notes` returns admin/manager/team + the caller's
own personal notes, ordered **admin → manager → team → personal**; each note carries a
computed `can_edit` plus the author's `author_role` for display. Heavier Apify
enrichment (photo, summary, skills, languages, followers, …) is **not** stored here or
as new columns — it is read from `decision_makers.profile_data` (see that table) and
served by `GET /decision-makers/{id}` (DecisionMakerDetailOut).

---

## Outreach module (native)  — `0020`
A first-class module that layers an engagement *cycle* on top of the existing
intelligence — it **reuses** companies / decision_makers / lead_scores /
engagement_recommendations / users and never duplicates them. Four tables:

### outreach_leads  *[Outreach]*
One engagement cycle per company. PK `id`; `company_domain` FK→companies (CASCADE,
**UNIQUE**); `owner_id` FK→users (SET NULL); `primary_dm_id` FK→decision_makers
(SET NULL); `stage` (`CHECK` OUTREACH_STAGES); `service_interest`
(staffing/engineering/training); `source` (discovery/manual); `qualification_reason`;
`qualified_at`/`last_activity_at`/`next_action_at`. Score/grade/priority/pitch are
**read live** from lead_scores + engagement_recommendations, not stored here.

### outreach_templates  *[Outreach]*
`{{variable}}`-based email templates (deterministic, no LLM). `name`, `category`,
`subject`, `body`, `is_active`, `created_by` FK→users. Variables are parsed from
the subject/body at read time.

### outreach_messages  *[Outreach]*
An email through its lifecycle. PK `id`; `outreach_lead_id` FK→outreach_leads
(CASCADE); `decision_maker_id` FK→decision_makers (SET NULL, the recipient);
`template_id` FK→outreach_templates (SET NULL); `created_by`/`approved_by`
FK→users; `direction` (`CHECK` outbound/inbound); `status` (`CHECK`
draft/pending_approval/approved/queued/sent/failed/replied); `to_email`/`from_email`,
`subject`, `body`, `thread_id` (groups replies), `sent_at`/`approved_at`.

### outreach_activities  *[Outreach]*
Append-only timeline/audit per lead. `outreach_lead_id` FK→outreach_leads (CASCADE);
`actor_id` FK→users (SET NULL); `actor_email`; `type` (`CHECK` OUTREACH_ACTIVITY_TYPES);
`detail`; `created_at`.

---

### Canonical enums (`config/enums.py` ↔ SQL `CHECK`)
- `company_tier`: STARTUP, SCALEUP, ESTABLISHED, INCUMBENT, UNKNOWN
- `prospect_type`: PRODUCT_COMPANY, SERVICE_PROVIDER, EDA_VENDOR, FOUNDRY, INVESTOR, PUBLISHER, ACADEMIC, UNKNOWN
- `compliance_flag`: APPROVED, EXCLUDED_REGION, REVIEW_REQUIRED, UNKNOWN
- `validation_status`: VALID, REVIEW_REQUIRED, REJECTED, STUB, PENDING
- `lead_scores.grade`: A+, A, B, C
- `lead_reviews.review_status` (LEAD_REVIEW_STATUSES): approved, needs_review, strategic_account, disqualified, watchlist
- `resolution_review_queue.match_type`: EXACT_DOMAIN, ALIAS, FUZZY_NAME, NEW_STUB, UNRESOLVED
- `users.role` (USER_ROLES): admin, manager, member  *(member = "Employee" in the UI)*
- `users.status` (USER_STATUSES): pending, active, disabled, rejected, deleted
- `user_audit_events.action` (USER_AUDIT_ACTIONS): registered, login, approved, rejected, enabled, disabled, role_changed, deleted
- `lead_assignments.status` (ASSIGNMENT_STATUSES): new, assigned, contacted, qualified, proposal, won, lost, on_hold
- `lead_assignment_events.action` (ASSIGNMENT_EVENTS): assigned, reassigned, unassigned, status_changed, note_changed
- `outreach_leads.stage` (OUTREACH_STAGES): research_complete, outreach_ready, contacted, replied, interested, meeting_scheduled, proposal_sent, won, lost
- `outreach_messages.status` (OUTREACH_MESSAGE_STATUSES): draft, pending_approval, approved, queued, sent, failed, replied
- `EXCLUDED_PROSPECT_TYPES` (blocked at ingestion — competitors): SERVICE_PROVIDER
