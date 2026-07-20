"""Canonical vocabularies for the master database — the single source of truth.

The engines use overlapping-but-inconsistent enum values (casing differs, and
``region_flag`` means a *compliance* flag in Industry/Blog but a *geographic*
region in Career). The master DB pins one canonical set; the SQL ``CHECK``
constraints in ``master_db/migrations`` mirror these exact tuples, and the P1
ingestors will coerce raw engine values through the ``normalize_*`` helpers
below before writing.

Keeping the allowed values here (Python) *and* as ``CHECK`` constraints (SQL)
is deliberate: the database stays the hard gate, while application code shares
one definition. If you add a value, update both this file and the matching
migration.
"""
from __future__ import annotations

# --- Company dimensions ----------------------------------------------------
COMPANY_TIERS: tuple[str, ...] = ("STARTUP", "SCALEUP", "ESTABLISHED", "INCUMBENT", "UNKNOWN")
PROSPECT_TYPES: tuple[str, ...] = (
    "PRODUCT_COMPANY", "SERVICE_PROVIDER", "EDA_VENDOR", "FOUNDRY",
    "INVESTOR", "PUBLISHER", "ACADEMIC", "UNKNOWN",
)
# Competitor prospect types the platform must never ingest or store. Enforced at
# ingestion (industry ingestor, employer seeds, resolver) + purgeable via
# scripts/purge_service_providers.py. See integration/competitors.py.
EXCLUDED_PROSPECT_TYPES: tuple[str, ...] = ("SERVICE_PROVIDER",)
# Compliance flag (Industry Discovery / Blog Crawler). NOT a geographic region.
COMPLIANCE_FLAGS: tuple[str, ...] = ("APPROVED", "EXCLUDED_REGION", "REVIEW_REQUIRED", "UNKNOWN")
VALIDATION_STATUSES: tuple[str, ...] = ("VALID", "REVIEW_REQUIRED", "REJECTED", "STUB", "PENDING")

# --- Accounts / RBAC -------------------------------------------------------
# Internal role ids. NOTE: "member" is surfaced in the UI as "Employee".
# "super_admin" sits above "admin": the only role that may grant/revoke super_admin
# itself or touch another super_admin's role/active-state/deletion (see
# backend/services.py::_guard_super_admin_tier). Reached only via the SP_SUPER_ADMIN_EMAIL
# bootstrap (backend/services.py::_maybe_bootstrap_super_admin) or promotion by an
# existing super_admin — never self-granted.
USER_ROLES: tuple[str, ...] = ("super_admin", "admin", "manager", "member")
# Account lifecycle. Only `active` may obtain a session / access the platform.
#   pending  — registered via SSO, awaiting admin approval (no access yet)
#   active   — approved + enabled
#   disabled — was active, an admin turned it off (reversible)
#   rejected — an admin denied the pending request
#   deleted  — soft-deleted (PII scrubbed, row kept for audit/FK integrity)
USER_STATUSES: tuple[str, ...] = ("pending", "active", "disabled", "rejected", "deleted")
# Admin user-management audit trail. "super_admin_bootstrap" fires at most once (the
# initial SUPER_ADMIN handoff); "denied" logs a blocked lifecycle/privilege-escalation
# attempt (see `detail` for which guard tripped). "login_failed" is recorded for a
# wrong-password attempt against a real account (no email-enumeration in the API
# response, but still visible to admins in the audit trail).
USER_AUDIT_ACTIONS: tuple[str, ...] = (
    "registered", "login", "login_failed", "approved", "rejected", "enabled", "disabled",
    "role_changed", "deleted", "logout", "session_refreshed",
    "super_admin_bootstrap", "denied", "password_changed", "forced_password_change_completed",
)

# --- Lead assignment (CRM-lite) --------------------------------------------
ASSIGNMENT_STATUSES: tuple[str, ...] = (
    "new", "assigned", "contacted", "qualified", "proposal", "won", "lost", "on_hold",
)
ASSIGNMENT_EVENTS: tuple[str, ...] = (
    "assigned", "reassigned", "unassigned", "status_changed", "note_changed",
)

# --- Decision-maker collaboration notes ------------------------------------
# Four-tier notes on a decision maker. The tuple order is also the canonical
# DISPLAY order (admin → manager → team → personal): admin/manager/team are
# visible to every authenticated user; personal is private to its author.
#   admin    — authority guidance; created by admins only; pinned first.
#   manager  — authority guidance; created by admin/manager; below admin.
#   team     — shared note any authenticated user may add; visible to everyone.
#   personal — private to the author (any user); only the author may edit/delete.
# Create:  admin→admin, manager→admin/manager, team/personal→any user.
# Edit/delete:  admin→admin-tier or author; manager/team→manager-tier or author;
#               personal→author only.  (See backend.services + DmNotes.tsx.)
DM_NOTE_TYPES: tuple[str, ...] = ("admin", "manager", "team", "personal")

# --- Lead scoring ----------------------------------------------------------
LEAD_GRADES: tuple[str, ...] = ("A+", "A", "B", "C")
# Shared low/medium/high confidence label (lead_scores + leadership_signals).
CONFIDENCE_LEVELS: tuple[str, ...] = ("low", "medium", "high")

# --- Human lead review / feedback (P-task viii) ----------------------------
# A human analyst's assessment of a lead, kept STRICTLY SEPARATE from the model
# score (it never overwrites lead_scores). Stored as the current state in
# `lead_reviews` (1:1 per company) plus an append-only `lead_review_events`
# feedback/audit trail. NOTE: distinct from the resolution-layer REVIEW_STATUSES
# below (which govern stub-company confirmation/merge — a different workflow).
LEAD_REVIEW_STATUSES: tuple[str, ...] = (
    "approved", "needs_review", "strategic_account", "disqualified", "watchlist",
)

# --- Leadership signals (person-level director+ movement; P-task 8) ---------
# A leadership-movement signal is person-level intelligence (who moved), distinct
# from the Blog Crawler's company-level "Leadership Change" *opportunity* (that an
# event happened). Derived by the platform from LinkedIn career history and, when
# crawls populate them, blog leadership events.
LEADERSHIP_MOVEMENT_TYPES: tuple[str, ...] = (
    "promotion", "role_change", "new_executive_hire", "executive_departure",
    "board_appointment", "founder_change", "executive_reshuffle",
)
# Director+ seniority bands we DO track (manager-level and ICs are gated out).
LEADERSHIP_SENIORITY_BANDS: tuple[str, ...] = (
    "c_level", "president", "founder", "managing_director", "evp", "svp", "vp",
    "senior_director", "director", "head_of",
)
LEADERSHIP_SIGNAL_SOURCES: tuple[str, ...] = ("linkedin_history", "blog_event", "snapshot_comparison")
# Reusable priority routing (leadership_signals/priority.py) — startup/India-relevant
# movement is high; unrelated overseas movement at a large company is low (kept, not deleted).
LEADERSHIP_PRIORITY_TIERS: tuple[str, ...] = ("high", "medium", "low")

# --- Signal categories (first-class grouping of opportunities) --------------
# Every opportunity belongs to exactly one signal_category. LEADERSHIP is a
# first-class category of its own: people-movement events (executive hires,
# leadership & role changes) are separated OUT of the general NEWS feed so they
# can be filtered, counted, and charted independently everywhere in the platform.
# The category is derived deterministically from opportunity_type (see
# signal_category_for) and persisted on the row (master_db.models.Opportunity).
SIGNAL_CATEGORIES: tuple[str, ...] = ("LEADERSHIP", "PROJECT", "NEWS")
# The opportunity_types that constitute the LEADERSHIP category (company-level
# people-movement events). Everything else is NEWS (or PROJECT, below).
LEADERSHIP_OPPORTUNITY_TYPES: tuple[str, ...] = ("EXECUTIVE_HIRE", "LEADERSHIP_CHANGE", "ROLE_CHANGE")
# The opportunity_types that constitute the PROJECT category — structured New
# Semiconductor Project Intelligence (integration/news/project_intel.py). Kept in sync
# with project_intel.PROJECT_EVENT_TYPES; separated OUT of the general NEWS feed so
# project intelligence is independently filterable/countable everywhere.
PROJECT_OPPORTUNITY_TYPES: tuple[str, ...] = (
    "NEW_CHIP_PROGRAM", "NEW_ASIC_SOC", "TAPEOUT", "DESIGN_WIN", "DESIGN_CENTER",
    "RND_CENTER", "FAB_NEW", "FAB_EXPANSION", "OSAT_ATMP", "CAPACITY_EXPANSION",
    "FACILITY_EXPANSION",
)


def signal_category_for(opportunity_type: str | None) -> str:
    """Classify an opportunity into its first-class signal category.

    Deterministic and dependency-free so every writer (news engine, ingestors) and
    the DB backfill agree. Leadership people-movement types are their OWN category;
    structured semiconductor-project events are the PROJECT category; all other market
    events are NEWS."""
    t = (opportunity_type or "").upper()
    if t in LEADERSHIP_OPPORTUNITY_TYPES:
        return "LEADERSHIP"
    if t in PROJECT_OPPORTUNITY_TYPES:
        return "PROJECT"
    return "NEWS"


# --- Outreach (native module) ----------------------------------------------
# Outreach is a first-class platform module (not a separate app): it layers an
# engagement *cycle* on top of the existing companies / decision_makers /
# lead_scores / engagement_recommendations rather than duplicating them. These
# enums govern the outreach-specific state (pipeline, drafts/approvals, mail).
OUTREACH_STAGES: tuple[str, ...] = (
    "research_complete", "outreach_ready", "contacted", "replied",
    "interested", "meeting_scheduled", "proposal_sent", "won", "lost",
)
# Stages that count as an active (open) pipeline opportunity.
OUTREACH_OPEN_STAGES: tuple[str, ...] = (
    "research_complete", "outreach_ready", "contacted", "replied",
    "interested", "meeting_scheduled", "proposal_sent",
)
OUTREACH_SERVICE_LINES: tuple[str, ...] = ("staffing", "engineering", "training")
OUTREACH_MESSAGE_STATUSES: tuple[str, ...] = (
    "draft", "pending_approval", "approved",
    "scheduled", "queued", "sending", "sent",
    "delivered", "failed", "bounced", "cancelled", "replied",
)
EMAIL_PROVIDER_TYPES: tuple[str, ...] = ("mock", "smtp", "gmail", "outlook")
EMAIL_CONNECTION_STATUSES: tuple[str, ...] = ("connected", "disconnected", "error", "pending")
EMAIL_ATTACHMENT_STATUSES: tuple[str, ...] = ("pending", "uploaded", "failed")
GMAIL_SYNC_STATUSES: tuple[str, ...] = ("idle", "syncing", "error", "paused")
# Conversation / inbox folders (computed, not stored as a CHECK constraint)
EMAIL_FOLDERS: tuple[str, ...] = ("inbox", "sent", "drafts", "scheduled", "failed", "archived", "trash")
# Label colours — subset used in UI chips
EMAIL_LABEL_COLORS: tuple[str, ...] = ("gray", "blue", "green", "red", "yellow", "purple", "orange")
# System labels (auto-seeded, cannot be deleted)
SYSTEM_LABEL_NAMES: tuple[str, ...] = ("follow-up", "prospect", "customer", "internal", "important")
OUTREACH_MESSAGE_DIRECTIONS: tuple[str, ...] = ("outbound", "inbound")
OUTREACH_LEAD_SOURCES: tuple[str, ...] = ("discovery", "manual")
# Activity-timeline event types (audit log of a lead's outreach lifecycle).
OUTREACH_ACTIVITY_TYPES: tuple[str, ...] = (
    "lead_created", "stage_changed", "owner_changed", "draft_created",
    "submitted_for_approval", "approved", "sent", "reply_received", "note_added",
    "task_created", "task_completed", "meeting_scheduled", "meeting_completed", "call_logged",
    "message_scheduled", "message_cancelled",
)
OUTREACH_TASK_STATUSES: tuple[str, ...] = ("pending", "in_progress", "completed", "cancelled")
OUTREACH_TASK_PRIORITIES: tuple[str, ...] = ("low", "medium", "high", "urgent")
OUTREACH_MEETING_TYPES: tuple[str, ...] = ("call", "video", "in_person", "demo", "follow_up")
OUTREACH_MEETING_OUTCOMES: tuple[str, ...] = ("positive", "neutral", "negative", "no_show", "reschedule")

# --- Customer Success & Account Management (Enterprise CRM Phase 4) ---------
CS_ACCOUNT_STATUSES: tuple[str, ...] = ("prospect", "active", "at_risk", "churned", "inactive")
CS_ACCOUNT_TIERS: tuple[str, ...] = ("strategic", "enterprise", "mid_market", "smb", "startup")
CS_CONTACT_ROLES: tuple[str, ...] = (
    "primary", "executive_sponsor", "technical", "procurement", "finance", "champion",
)
CS_LIFECYCLE_STAGES: tuple[str, ...] = (
    "prospect", "customer", "onboarding", "adoption", "growth",
    "renewal", "expansion", "at_risk", "churned",
)
CS_HEALTH_GRADES: tuple[str, ...] = ("A", "B", "C", "D", "F")
CS_HEALTH_TRENDS: tuple[str, ...] = ("up", "stable", "down")
CS_CONTRACT_STATUSES: tuple[str, ...] = (
    "draft", "active", "expired", "renewed", "terminated", "pending_renewal",
)
CS_PLAN_STATUSES: tuple[str, ...] = ("draft", "active", "completed", "cancelled")
CS_MILESTONE_STATUSES: tuple[str, ...] = ("pending", "in_progress", "completed", "at_risk", "missed")
CS_RISK_SEVERITIES: tuple[str, ...] = ("low", "medium", "high", "critical")
CS_RISK_STATUSES: tuple[str, ...] = ("open", "mitigated", "accepted", "closed")

# --- Team Collaboration & Work Management (Enterprise CRM Phase 3) ----------
# Entity types that can receive assignments / comments / notifications.
COLLAB_ENTITY_TYPES: tuple[str, ...] = ("deal", "campaign", "opportunity", "task", "meeting")
# Roles a user can hold on an entity.
COLLAB_ROLES: tuple[str, ...] = ("owner", "assignee", "reviewer", "manager", "watcher")
# Notification event types.
COLLAB_NOTIF_TYPES: tuple[str, ...] = (
    "assignment", "deal_moved", "campaign_update", "reply_received",
    "meeting_scheduled", "task_due", "mention", "approval_needed", "comment",
)
# Assignment audit actions.
COLLAB_ASSIGNMENT_ACTIONS: tuple[str, ...] = ("assigned", "reassigned", "removed", "role_changed")
# Entity types for saved views.
SAVED_VIEW_ENTITY_TYPES: tuple[str, ...] = ("deals", "campaigns", "contacts", "opportunities")

# --- CRM Pipeline & Deal Management (Enterprise CRM Phase 2) ----------------
DEAL_PIPELINE_STAGE_TYPES: tuple[str, ...] = ("open", "won", "lost")
DEAL_FORECAST_CATEGORIES: tuple[str, ...] = ("pipeline", "best_case", "commit", "won", "omitted")
DEAL_CURRENCIES: tuple[str, ...] = ("USD", "EUR", "GBP", "INR", "JPY", "CAD", "AUD", "SGD")

# --- Campaign & Sequence management (Enterprise CRM Phase 1) ---------------
CAMPAIGN_STATUSES: tuple[str, ...] = ("draft", "active", "paused", "completed", "archived")
CAMPAIGN_TYPES: tuple[str, ...] = ("cold_outreach", "nurture", "followup", "reengagement", "event")
CAMPAIGN_MEMBER_STATUSES: tuple[str, ...] = ("active", "paused", "completed", "removed")
CAMPAIGN_OUTCOMES: tuple[str, ...] = ("converted", "lost", "no_response", "disqualified")
SEQUENCE_STEP_ACTIONS: tuple[str, ...] = (
    "email", "follow_up", "meeting_request", "call", "task", "wait", "manual_review"
)
SEQUENCE_ENROLLMENT_STATUSES: tuple[str, ...] = (
    "active", "paused", "completed", "cancelled", "failed"
)
SEQUENCE_STEP_STATUSES: tuple[str, ...] = ("pending", "completed", "skipped", "failed")

# --- Revenue Operations, Forecasting & Executive Analytics (Phase 5) --------
REVOPS_TARGET_SCOPES: tuple[str, ...] = ("company", "team", "individual")
REVOPS_PERIOD_TYPES: tuple[str, ...] = ("monthly", "quarterly", "annual")
REVOPS_FORECAST_SNAPSHOT_CATEGORIES: tuple[str, ...] = ("pipeline", "weighted", "best_case", "commit")

# --- Workflow Automation & Business Process Engine (Phase 6) ---------------
WORKFLOW_STATUSES: tuple[str, ...] = ("draft", "active", "paused", "archived")
WORKFLOW_TRIGGER_EVENTS: tuple[str, ...] = (
    "lead_created", "opportunity_created", "deal_created", "deal_stage_changed",
    "deal_won", "deal_lost", "customer_created", "health_changed",
    "contract_renewal_window", "task_completed", "meeting_completed",
    "campaign_status_changed",
)
WORKFLOW_ACTION_TYPES: tuple[str, ...] = (
    "create_task", "assign_owner", "send_notification", "update_fields",
    "create_activity", "create_follow_up", "schedule_reminder",
    "create_opportunity", "create_deal", "create_success_task",
)
WORKFLOW_EXECUTION_STATUSES: tuple[str, ...] = ("success", "failed", "partial")
WORKFLOW_APPROVAL_TYPES: tuple[str, ...] = (
    "large_deal", "discount", "contract_change", "customer_escalation",
)
WORKFLOW_APPROVAL_STATUSES: tuple[str, ...] = ("pending", "approved", "rejected", "cancelled")
WORKFLOW_SLA_STATUSES: tuple[str, ...] = ("on_track", "at_risk", "breached", "resolved", "escalated")

# --- Custom Objects, Forms & No-Code Platform (Phase 7) ---------------------
CUSTOM_OBJECT_STATUSES: tuple[str, ...] = ("draft", "active", "archived")
CUSTOM_FIELD_TYPES: tuple[str, ...] = (
    "text", "long_text", "integer", "decimal", "boolean", "date", "datetime",
    "email", "url", "phone", "currency", "picklist", "multiselect", "lookup",
)
CUSTOM_RECORD_AUDIT_ACTIONS: tuple[str, ...] = ("created", "updated", "deleted")
CUSTOM_DATA_JOB_TYPES: tuple[str, ...] = ("import", "export")
CUSTOM_DATA_JOB_STATUSES: tuple[str, ...] = ("pending", "running", "completed", "failed")

# --- AI Intelligence & Copilot (Phase 8) ------------------------------------
# Deterministic, rules-based "AI" — no external LLM calls. Reuses CONFIDENCE_LEVELS
# (low/medium/high) for insight confidence and CS_HEALTH_TRENDS (up/stable/down) for
# engagement trend rather than duplicating those vocabularies.
AI_INSIGHT_TYPES: tuple[str, ...] = ("deal", "customer", "opportunity", "campaign", "pipeline", "revenue")
AI_INSIGHT_SEVERITIES: tuple[str, ...] = ("low", "medium", "high", "critical")
AI_INSIGHT_STATUSES: tuple[str, ...] = ("active", "dismissed", "resolved")
AI_RECOMMENDATION_TYPES: tuple[str, ...] = (
    "next_best_action", "follow_up", "deal_acceleration", "customer_retention",
    "expansion_opportunity", "renewal_action",
)
AI_RECOMMENDATION_STATUSES: tuple[str, ...] = ("pending", "dismissed", "completed")
AI_RISK_TYPES: tuple[str, ...] = (
    "stalled_deal", "at_risk_customer", "low_engagement", "missed_sla",
    "forecast_variance", "renewal_risk",
)
AI_COPILOT_QUERY_TYPES: tuple[str, ...] = (
    "entity_summary", "customer_summary", "deal_summary", "pipeline_summary",
    "executive_summary", "activity_summary",
)

# --- Enterprise Administration, Security & Compliance (Phase 9) ------------
ORG_UNIT_TYPES: tuple[str, ...] = ("business_unit", "department", "team")
ORG_UNIT_MEMBER_ROLES: tuple[str, ...] = ("member", "lead")
SETTINGS_CATEGORIES: tuple[str, ...] = ("crm", "workflow", "ai", "email", "notification", "retention", "platform")
SECURITY_POLICY_TYPES: tuple[str, ...] = (
    "password", "session", "login_restriction", "ip_allowlist", "account_lockout", "mfa",
)
# Cross-cutting audit taxonomy. Authentication + user_administration events are largely
# already captured by the existing user_audit_events table (Phase 0); audit_service reads
# both tables into one unified, filterable view rather than duplicating that data.
AUDIT_CATEGORIES: tuple[str, ...] = (
    "authentication", "user_administration", "permission_change", "record_crud",
    "workflow_change", "configuration_change", "ai_action", "data_export",
)
COMPLIANCE_RECORD_TYPES: tuple[str, ...] = (
    "legal_hold", "consent", "data_export_request", "data_deletion_request",
)
COMPLIANCE_STATUSES: tuple[str, ...] = ("pending", "active", "completed", "rejected")
API_KEY_STATUSES: tuple[str, ...] = ("active", "revoked", "expired")

# --- Integration Platform & Developer Ecosystem (Phase 10) -----------------
INTEGRATION_CATEGORIES: tuple[str, ...] = (
    "crm", "communication", "analytics", "productivity", "finance", "custom",
)
INTEGRATION_STATUSES: tuple[str, ...] = ("active", "inactive", "error", "pending_setup")
INTEGRATION_HEALTH_STATUSES: tuple[str, ...] = ("healthy", "degraded", "down", "unknown")
WEBHOOK_STATUSES: tuple[str, ...] = ("enabled", "disabled")
WEBHOOK_DELIVERY_STATUSES: tuple[str, ...] = ("pending", "success", "failed", "retrying")
OAUTH_CREDENTIAL_STATUSES: tuple[str, ...] = ("active", "revoked", "expired")
# Event Bus categories. event_type itself is free-form (like AuditEvent.action) so it can
# carry any existing vocabulary value (a WORKFLOW_TRIGGER_EVENTS value, an audit action, or
# a caller-defined name) without duplicating those enums here.
EVENT_BUS_CATEGORIES: tuple[str, ...] = ("crm", "workflow", "customer", "revenue", "ai", "administration")
CONNECTOR_TYPES: tuple[str, ...] = ("http", "rest", "webhook", "scheduled")
CONNECTOR_STATUSES: tuple[str, ...] = ("active", "inactive", "error")
CONNECTOR_RUN_STATUSES: tuple[str, ...] = ("running", "success", "failed")
PLUGIN_STATUSES: tuple[str, ...] = ("enabled", "disabled")
PLUGIN_EXECUTION_STATUSES: tuple[str, ...] = ("success", "failed", "skipped")
PLUGIN_HOOK_TYPES: tuple[str, ...] = (
    "before_create", "after_create", "before_update", "after_update",
    "before_delete", "after_delete", "on_event",
)

# --- Enterprise Search & Knowledge Platform (Phase 11) ----------------------
# Global Search entity types (the 12 the spec lists).
GLOBAL_SEARCH_ENTITY_TYPES: tuple[str, ...] = (
    "company", "contact", "deal", "customer", "opportunity", "campaign",
    "workflow", "custom_object", "activity", "task", "meeting", "ai_insight",
)
# Additional Full-Text Search targets (spec section 5), searched via the same
# per-type registry as Global Search but not surfaced as "global" record types.
FULL_TEXT_ENTITY_TYPES: tuple[str, ...] = ("kb_article", "note", "comment", "ai_summary")
SEARCH_ENTITY_TYPES: tuple[str, ...] = GLOBAL_SEARCH_ENTITY_TYPES + FULL_TEXT_ENTITY_TYPES
KB_CATEGORY_TYPES: tuple[str, ...] = ()  # reserved — categories are free-form, hierarchy only
KB_ARTICLE_STATUSES: tuple[str, ...] = ("draft", "pending_approval", "published", "archived")

# --- Data Warehouse & Advanced Business Intelligence (Phase 12) -------------
WAREHOUSE_METRIC_TYPES: tuple[str, ...] = (
    "revenue", "deals", "customers", "campaigns", "activities", "ai_metrics", "workflow_metrics",
)
KPI_CATEGORIES: tuple[str, ...] = ("revenue", "sales", "customer", "campaign", "workflow", "ai")
KPI_STATUSES: tuple[str, ...] = ("on_track", "at_risk", "off_track", "no_target")
REPORT_STATUSES: tuple[str, ...] = ("draft", "active", "archived")
REPORT_SCHEDULE_FREQUENCIES: tuple[str, ...] = ("daily", "weekly", "monthly", "quarterly")
SCHEDULED_REPORT_RUN_STATUSES: tuple[str, ...] = ("pending", "sent", "failed")
BI_DASHBOARD_TYPES: tuple[str, ...] = (
    "revenue_overview", "pipeline_overview", "customer_overview",
    "operations_overview", "ai_overview", "organization_overview",
)

# --- Resolution layer ------------------------------------------------------
MATCH_TYPES: tuple[str, ...] = ("EXACT_DOMAIN", "ALIAS", "FUZZY_NAME", "NEW_STUB", "UNRESOLVED")
REVIEW_STATUSES: tuple[str, ...] = ("pending", "approved", "rejected", "merged")

# --- Orchestration ---------------------------------------------------------
INGESTION_STATUSES: tuple[str, ...] = ("running", "success", "failed", "partial")
PIPELINE_STATUSES: tuple[str, ...] = ("running", "success", "failed", "partial", "skipped")
PIPELINE_COMPONENTS: tuple[str, ...] = ("industry", "blog", "news", "annual_list", "company_news", "career", "decision_maker_intelligence", "scoring", "leadership", "engagement")

# --- Standard Run executions (scheduler + run history) ---------------------
# One PipelineExecution row per Standard Run (a full `run all`), whether fired by
# the scheduler or a manual CLI invocation. Higher level than pipeline_runs (which
# stays one row PER STAGE): this is the run-level record the Run History UI reads.
EXECUTION_TRIGGERS: tuple[str, ...] = ("manual", "scheduled")
EXECUTION_STATUSES: tuple[str, ...] = ("running", "success", "partial", "failed", "skipped")
# Outlook notification outcome for a scheduled run. "logged" = built + logged only
# (no Graph mail configured); "skipped" = nothing to send / manual run; "sent" /
# "failed" = a real Graph sendMail was attempted. Never blocks the pipeline.
NOTIFICATION_STATUSES: tuple[str, ...] = ("pending", "sent", "failed", "skipped", "logged")

# --- Decision Maker Intelligence — MANUAL per-company jobs -------------------
# DM intelligence is never scheduled (the Apify actor has a per-lead cost); it is
# run manually from the Decision Makers page for a chosen set of companies, each
# with its OWN requested lead count. A job tracks live progress at the job level
# and per company. See master_db.models.DmIntelligenceJob / DmIntelligenceJobItem
# and backend/dm_intelligence_jobs.py.
DM_JOB_STATUSES: tuple[str, ...] = ("queued", "running", "completed", "partial", "failed")
DM_JOB_ITEM_STATUSES: tuple[str, ...] = ("queued", "running", "completed", "failed")

# --- Historical import jobs (reusable import-run tracking; Phase 3) ----------
# One row per historical-data import run (company + decision-maker synchronization).
# "previewed" = a read-only reconciliation preview was generated (no data written yet);
# running/completed/failed/cancelled cover the later apply step. See master_db.models
# .ImportJob and backend/import_repo.py.
IMPORT_JOB_STATUSES: tuple[str, ...] = (
    "previewed", "running", "completed", "partial", "failed", "rolled_back", "cancelled",
)
# Ordered stages of a transactional import (Phase 4). Recorded on ImportJob.current_stage.
IMPORT_STAGES: tuple[str, ...] = (
    "create_companies", "update_companies", "create_decision_makers",
    "update_decision_makers", "refresh_relationships", "post_import_hooks",
)

# --- Import review & approval (Phase 5) -------------------------------------
# Every record in a preview carries one explicit review state; only 'approved' and
# 'resolved' records reach the transaction engine at commit time.
REVIEW_STATES: tuple[str, ...] = ("pending", "approved", "rejected", "skipped", "resolved")
# Which review bucket a record belongs to (derived from its sync classification).
REVIEW_CATEGORIES: tuple[str, ...] = (
    "new_company", "updated_company", "new_decision_maker", "updated_decision_maker",
    "conflict", "duplicate", "invalid", "unchanged",
)
REVIEW_KINDS: tuple[str, ...] = ("company", "decision_maker")
# Per-field decision on an update/conflict field.
REVIEW_FIELD_CHOICES: tuple[str, ...] = ("keep_platform", "accept_historical")
# Audit-trail action verbs.
REVIEW_EVENT_ACTIONS: tuple[str, ...] = (
    "approve", "reject", "skip", "resolve_field", "bulk_approve", "bulk_reject", "reset",
)
# Review states whose records are applied by the import engine.
REVIEW_IMPORTABLE_STATES: tuple[str, ...] = ("approved", "resolved")

# --- News Intelligence (multi-source ingestion + rich opportunities) --------
# Source adapters the News Collection Engine can pull from. "file" is the existing
# blog/company-news JSONL/CSV feed; "rss"/"google_alerts" are live feed adapters.
NEWS_ADAPTER_TYPES: tuple[str, ...] = ("rss", "google_alerts", "file", "manual")
# Opportunity lifecycle — an event's state as analysts work it. NEW on creation;
# ACTIVE once being pursued; MONITORING when watched but not active; RESOLVED when
# closed out; ARCHIVED when set aside. Independent of validation_status (data trust)
# and of the AI outputs (never overwritten by a lifecycle change).
OPPORTUNITY_LIFECYCLE_STATUSES: tuple[str, ...] = (
    "NEW", "ACTIVE", "MONITORING", "RESOLVED", "ARCHIVED",
)
# Manual-review actions recorded (append-only) in opportunity_reviews. Each is
# stored as history and NEVER overwrites the AI extraction outputs.
OPPORTUNITY_REVIEW_ACTIONS: tuple[str, ...] = (
    "not_relevant", "merge", "split", "change_type", "archive", "restore", "note",
)

# --- Machine Learning Foundation (feature store + feedback + registries) ----
# User feedback interactions captured for future model training (no model trained
# yet). Positive/negative weighting is applied by the dataset builder, not here.
ML_INTERACTION_TYPES: tuple[str, ...] = (
    "thumbs_up", "thumbs_down", "export", "contact", "ignore",
)
# Entities an interaction / feature row can reference.
ML_ENTITY_TYPES: tuple[str, ...] = ("opportunity", "company", "lead", "decision_maker")
# Model registry lifecycle (infrastructure only — the classifier is not implemented).
ML_MODEL_STATUSES: tuple[str, ...] = ("draft", "training", "active", "archived", "failed")
# Opportunity categories that get independent time-decay profiles.
ML_DECAY_CATEGORIES: tuple[str, ...] = ("layoffs", "hiring", "projects", "funding", "default")
# Model-registry lifecycle audit actions (candidate -> promoted/rejected/rolled back).
ML_MODEL_EVENT_ACTIONS: tuple[str, ...] = (
    "trained", "evaluated", "promoted", "rejected", "rolled_back", "archived",
)

# Synonym maps used by ingestion to coerce raw engine values -> canonical.
_TIER_SYNONYMS = {
    "STARTUP": "STARTUP", "SEED": "STARTUP", "EARLY": "STARTUP",
    "SCALEUP": "SCALEUP", "SCALE-UP": "SCALEUP", "GROWTH": "SCALEUP",
    "ESTABLISHED": "ESTABLISHED", "MATURE": "ESTABLISHED",
    "INCUMBENT": "INCUMBENT", "ENTERPRISE": "INCUMBENT",
}
_PROSPECT_SYNONYMS = {
    "PRODUCT_COMPANY": "PRODUCT_COMPANY", "PRODUCT": "PRODUCT_COMPANY",
    "SERVICE_PROVIDER": "SERVICE_PROVIDER", "SERVICE": "SERVICE_PROVIDER",
    "EDA_VENDOR": "EDA_VENDOR", "EDA": "EDA_VENDOR",
    "FOUNDRY": "FOUNDRY", "INVESTOR": "INVESTOR", "VC": "INVESTOR",
    "PUBLISHER": "PUBLISHER", "MEDIA": "PUBLISHER",
    "ACADEMIC": "ACADEMIC", "UNIVERSITY": "ACADEMIC",
}
_COMPLIANCE_SYNONYMS = {
    "APPROVED": "APPROVED",
    "EXCLUDED_REGION": "EXCLUDED_REGION", "EXCLUDED": "EXCLUDED_REGION",
    "REVIEW_REQUIRED": "REVIEW_REQUIRED", "REVIEW": "REVIEW_REQUIRED",
}


def _coerce(value: str | None, synonyms: dict[str, str], allowed: tuple[str, ...]) -> str:
    if not value:
        return "UNKNOWN" if "UNKNOWN" in allowed else allowed[-1]
    key = value.strip().upper().replace(" ", "_")
    if key in synonyms:
        return synonyms[key]
    if key in allowed:
        return key
    return "UNKNOWN" if "UNKNOWN" in allowed else allowed[-1]


def normalize_tier(value: str | None) -> str:
    return _coerce(value, _TIER_SYNONYMS, COMPANY_TIERS)


def normalize_prospect_type(value: str | None) -> str:
    return _coerce(value, _PROSPECT_SYNONYMS, PROSPECT_TYPES)


def is_excluded_prospect(value: str | None) -> bool:
    """True if *value* normalizes to a competitor type the platform refuses to store."""
    return normalize_prospect_type(value) in EXCLUDED_PROSPECT_TYPES


def normalize_compliance_flag(value: str | None) -> str:
    """Coerce an Industry/Blog ``region_flag`` to a canonical compliance flag.

    NOTE: never pass a Career ``region_flag`` here — that field is a geographic
    region ("North America", "India", …) and belongs in ``geo_region``.
    """
    return _coerce(value, _COMPLIANCE_SYNONYMS, COMPLIANCE_FLAGS)
