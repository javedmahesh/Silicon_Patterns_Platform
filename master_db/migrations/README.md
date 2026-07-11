# Master DB migrations

PostgreSQL / Supabase DDL for the master company database. **Authoritative schema
source of truth.** Apply in numeric order:

| # | File | Creates |
|---|------|---------|
| 0001 | `0001_foundations.sql` | extensions (`pg_trgm`, `citext`), `set_updated_at()` trigger, **companies**, **company_sources**, **company_aliases**, **resolution_review_queue** |
| 0002 | `0002_engine_tables.sql` | **opportunities** (Blog), **jobs** + **demand_signals** + **company_rollups** (Career), **decision_makers** (Decision Maker Intelligence / Apify) |
| 0003 | `0003_platform_tables.sql` | **lead_scores** (Lead Scoring), **ingestion_runs** (Orchestrator) |
| 0004 | `0004_pipeline_runs.sql` | **pipeline_runs** (Orchestrator — one row per stage run; `component` is free text) |
| 0005 | `0005_review_actions.sql` | **review_actions** (append-only review-queue decision log) |
| 0006 | `0006_resolver_gist.sql` | GiST trigram (`gin_trgm_ops`) KNN index for the fuzzy resolver |
| 0007 | `0007_users.sql` | **users** (accounts, roles admin/manager/member; deactivated, never deleted) |
| 0008 | `0008_assignments.sql` | **lead_assignments** + **lead_assignment_events** (CRM + audit) |
| 0009 | `0009_company_notes.sql` | **company_notes** (free-text notes on a company) |
| 0010 | `0010_dm_contacts.sql` | **decision_maker_contacts** (work email/phone/notes — professional only) |
| 0011 | `0011_lead_score_confidence.sql` | `lead_scores` **coverage** + **confidence** columns (coverage-normalized scoring) |
| 0012 | `0012_leadership_signals.sql` | **leadership_signals** (person-level director+ movement — platform derivation) |
| 0013 | `0013_engagement_recommendations.sql` | **engagement_recommendations** (1:1 sales-pitch recommendation — platform derivation) |
| 0014 | `0014_lead_reviews.sql` | **lead_reviews** + **lead_review_events** (human assessment + feedback/audit trail — kept separate from `lead_scores`) |
| 0015 | `0015_review_score_adjustment.sql` | `lead_scores` **adjusted_score/adjusted_grade** + `lead_reviews` **reviewed_at/expires_at** + `lead_review_events` **adjusted snapshot** (optional, OFF-by-default review→score adjustment — model score untouched) |
| 0016 | `0016_company_news_signal.sql` | `opportunities` **company_news_signal** column + partial index (shared by Change_04 annual-lists "Rank: N" and Change_03 company-news) |
| 0017 | `0017_decision_maker_snapshots.sql` | **decision_maker_snapshots** + **apify_actor_runs** (snapshot-comparison leadership signals + Apify run monitoring); adds `snapshot_comparison` to the `leadership_signals.source` CHECK |
| 0018 | `0018_dm_professional_fields_and_notes.sql` | `decision_makers` **structured professional columns** (full_name, work_email, email_status, work_phone, city, state_region, country, organization_website, organization_linkedin — all NULLABLE) + **decision_maker_notes** (two-tier team/personal collaboration notes) |
| 0019 | `0019_dm_functional_area.sql` | `decision_makers` **functional_area** column (Apify job-function area; NULLABLE) |
| 0020 | `0020_outreach.sql` | **outreach_leads** + **outreach_templates** + **outreach_messages** + **outreach_activities** (native Outreach module — engagement cycle reusing companies/decision_makers/lead_scores/engagement/users) |
| 0021 | `0021_user_lifecycle_audit.sql` | `users` **status / login_count / deleted_at** (account lifecycle: pending→active, disabled, rejected, soft-delete) + **user_audit_events** (admin user-management audit trail) |
| 0022 | `0022_dm_note_roles.sql` | widen `decision_maker_notes.note_type` `CHECK` from {team,personal} to **{admin,manager,team,personal}** (four-tier collaboration notes). No table/column changes; richer Apify profile fields are read from `decision_makers.profile_data`, not new columns |

Every file is wrapped in a transaction and uses `CREATE ... IF NOT EXISTS` (plus a
guarded trigger), so re-running during review is safe and order-stable.

## Applying (later — NOT part of P0)

> P0 does **not** connect to Supabase. These commands are for when you choose to
> apply the reviewed schema.

**Supabase SQL editor:** paste each file's contents in order and run.

**psql / CLI** (apply every migration in numeric order):
```bash
for f in master_db/migrations/0*.sql; do psql "$DATABASE_URL" -f "$f"; done
```

## Local review without Postgres

The resolution-layer tables (companies, company_aliases, resolution_review_queue)
are mirrored as SQLAlchemy models in `master_db/models.py`. To exercise them on a
throwaway SQLite DB with no credentials:

```bash
pip install -r requirements.txt
pytest            # 180 tests: normalizer, resolver, ingestors (+annual-lists, +company-news), scoring (+review adjustment), leadership, engagement, human review, seed script, API, auth/RBAC
```

The Postgres-only features (`GENERATED ALWAYS AS IDENTITY`, `jsonb`,
`gin_trgm_ops`, `plpgsql` trigger) are intentionally not exercised on SQLite —
they belong to production and are reviewed as SQL here.

## Conventions

- **Join key:** every table references `companies(company_domain)`.
- **Ownership:** each engine writes only its own table(s); cross-engine data lives
  in separate tables, never merged into another engine's.
- **Cascade:** child rows `ON DELETE CASCADE`, except `decision_makers.company_domain`
  which is `ON DELETE SET NULL` (a person record outlives a company row).
- **Enums:** enforced as `CHECK (... IN (...))`, mirrored in `config/enums.py`.
  Change both together.
