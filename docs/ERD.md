# Master Database — Entity Relationships

The **data layer** is keyed on **`company_domain`**, with `companies` as the hub and each
engine owning the spokes it writes. The **multi-user layer** (migrations `0007`–`0010`) adds a
second hub — `users` — plus lead assignments, company notes, an audit trail, and per-person
professional contacts (diagram + cardinalities below).

```
                          ┌──────────────────────────┐
                          │        companies         │   PK company_domain
                          │  (Industry Discovery +    │   ← universal join key
                          │   resolver stubs)         │
                          └────────────┬─────────────┘
            ┌──────────────┬───────────┼───────────┬──────────────┬─────────────┐
            │ 1:N          │ 1:N       │ 1:1       │ 1:1          │ 0..N        │ 1:1
            ▼              ▼           ▼           ▼              ▼             ▼
     opportunities      jobs     demand_signals company_rollups decision_makers lead_scores
       (Blog)         (Career)     (Career)      (Career)       (Apify DMI)   (Lead Scoring)
            │                                                       ▲
            │ FK company_domain (NOT NULL, CASCADE)                 │ FK company_domain
            │                                                       │ (NULLABLE, SET NULL)
            └───────────────────────────────────────────────────────┘

  Resolution-layer (support):
     company_aliases  ──FK──► companies      (name_key → company_domain; Groq/Groq Inc./GROQ → groq.com)
     company_sources  ──FK──► companies      (provenance: who surfaced the company)
     resolution_review_queue                 (standalone; stub + unresolved records for human review)

  Platform derivations (spokes off companies, recomputed every refresh):
     leadership_signals       ──FK──► companies  (1:N · company_domain NULLABLE · CASCADE; person-level director+ moves)
     engagement_recommendations ─FK─► companies  (1:1 · PK = company_domain · CASCADE; one sales-pitch recommendation)

  Human review (spokes off companies; SEPARATE from lead_scores — never overwrites it):
     lead_reviews             ──FK──► companies  (1:1 · PK = company_domain · CASCADE; current human assessment)
     lead_review_events                          (standalone feedback/audit log; soft company ref, snapshots model grade/score)

  Platform-layer (audit):
     ingestion_runs                          (standalone; one row per engine/ingestion run)
     pipeline_runs                           (standalone; one row per orchestrator stage run)
     review_actions                          (standalone; append-only review-queue decision log)
```

### Multi-user layer (migrations `0007`–`0010`)

A second hub — `users` — sits beside `companies`. Managers assign leads, analysts leave notes,
and per-person professional contacts hang off `decision_makers`; every assignment change is
written to an append-only audit log.

```
        users                                   companies  (data-layer hub)
     PK id · email UNIQUE                     PK company_domain
     role ∈ {admin,manager,member}                  │
     deactivated, never deleted                     ├──── 1:N (CASCADE) ──► company_notes
            │                                        │                       (author_user_id:
            │  1:N (CASCADE)        1:N (CASCADE)     │                        soft ref, no FK)
            └───────────────┐   ┌────────────────────┘
                            ▼   ▼
                       lead_assignments
                       UNIQUE(company_domain, user_id) · status new→…→won/lost
                            │
                            │  every change appends →
                            ▼
                       lead_assignment_events
                       standalone audit · soft assignment_id / actor_user_id / company_domain
                       (NO FK — the trail survives unassign and company/user deletes)

        decision_makers ──── 1:1 (UNIQUE, CASCADE) ──► decision_maker_contacts
                                                       work email / phone / notes —
                                                       PROFESSIONAL only · added_by: soft ref
```

## Cardinalities

| Parent | Child | Type | FK nullability | On delete |
|---|---|---|---|---|
| companies | opportunities | 1 : N | NOT NULL | CASCADE |
| companies | jobs | 1 : N | NOT NULL | CASCADE |
| companies | demand_signals | 1 : 1 | PK = FK | CASCADE |
| companies | company_rollups | 1 : 1 | PK = FK | CASCADE |
| companies | decision_makers | 1 : N | **NULLABLE** | **SET NULL** |
| companies | lead_scores | 1 : 1 | PK = FK | CASCADE |
| companies | leadership_signals | 1 : N | **NULLABLE** | CASCADE |
| companies | engagement_recommendations | 1 : 1 | PK = FK | CASCADE |
| companies | lead_reviews | 1 : 1 | PK = FK | CASCADE |
| companies | company_aliases | 1 : N | NOT NULL | CASCADE |
| companies | company_sources | 1 : N | NOT NULL | CASCADE |
| users | lead_assignments | 1 : N | NOT NULL | CASCADE |
| companies | lead_assignments | 1 : N | NOT NULL | CASCADE |
| companies | company_notes | 1 : N | NOT NULL | CASCADE |
| decision_makers | decision_maker_contacts | 1 : 1 | NOT NULL · UNIQUE | CASCADE |

`lead_assignments` also carries `UNIQUE (company_domain, user_id)` — a given user holds at most
one assignment per company. Audit/ownership ids (`lead_assignment_events.assignment_id` /
`actor_user_id` / `company_domain`, `lead_assignments.assigned_by`, `company_notes.author_user_id`,
`decision_maker_contacts.added_by`) are **soft references with no FK** — see below.

## Why `decision_makers` is the exception

The Apify Decision Maker Intelligence engine reports the employer as a website
(`organizationWebsite`). It's normalized to a bare `company_domain` and resolved
against `companies`; when the org isn't a tracked company, the row keeps `NULL`. A
person is a real, independently valuable record, so deleting a company
`SET NULL`s the link rather than deleting the person.

## Audit & ownership rows use soft references (no FK)

`lead_assignment_events` is an append-only audit log: `assignment_id`, `actor_user_id`, and
`company_domain` are plain columns with **no foreign key**, so an event survives after its
`lead_assignments` row is deleted on unassign (and after a company or user is removed). The same
soft-reference pattern covers `lead_assignments.assigned_by`, `company_notes.author_user_id`, and
`decision_maker_contacts.added_by` — the *who/when* of an action is preserved even once the
referenced row is gone. This mirrors the data layer's `review_actions` / `ingestion_runs` logs.

## `decision_maker_contacts` is professional data only

One row per decision maker (1:1 via a `UNIQUE` FK, `CASCADE` on delete), holding **work email /
work phone / notes only** — never a personal home address, personal email, or personal phone.
View is open to any signed-in user; edit is restricted to **admin / manager**.
