/**
 * Public API types for the client — the single import surface the app uses.
 *
 * These are DERIVED from `schema.ts`, which is auto-generated from the backend's
 * OpenAPI document (see `npm run gen:api-schema`). Deriving (instead of hand-writing)
 * means the contract can't silently drift from `backend/schemas.py`: regenerate the
 * schema and any breaking change shows up here as a type error.
 *
 * A few types are hand-shaped on purpose, because OpenAPI can't express them as
 * richly as the UI needs: `ScoreRationale` (free-form JSON column) and `ProfileCounts`
 * (a `dict[str,int]` on the backend). The generic `Page<T>` wrapper is kept generic
 * here (the backend emits one concrete `Page_X_` schema per item type).
 *
 * Datetime fields arrive as ISO strings over JSON.
 */
import type { components } from "./schema";

type Schemas = components["schemas"];

/**
 * Response fields are always present in the payload, so strip the optional `?` that
 * the generator adds for fields defaulting to null — while preserving genuine `| null`.
 */
type Concrete<T> = { [K in keyof T]-?: Exclude<T[K], undefined> };

// ----------------------------------------------------------------- pagination
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ------------------------------------------------- entities (derived 1:1)
export type CompanySummary = Concrete<Schemas["CompanySummary"]>;
export type CompanyOut = Concrete<Schemas["CompanyOut"]>;
export type OpportunityOut = Concrete<Schemas["OpportunityOut"]>;
export type OpportunityDetailOut = Concrete<Schemas["OpportunityDetailOut"]>;
export type OpportunitySourceOut = Concrete<Schemas["OpportunitySourceOut"]>;
export type OpportunityReviewOut = Concrete<Schemas["OpportunityReviewOut"]>;
export type OpportunityTimelineItemOut = Concrete<Schemas["OpportunityTimelineItemOut"]>;
export type OpportunityReviewIn = Schemas["OpportunityReviewIn"];
export type NewsSourceOut = Concrete<Schemas["NewsSourceOut"]>;
export type NewsSourceIn = Schemas["NewsSourceIn"];
export type NewsSourcePatch = Schemas["NewsSourcePatch"];
export type NewsSeedResult = Concrete<Schemas["NewsSeedResult"]>;
export type JobOut = Concrete<Schemas["JobOut"]>;
export type DemandSignalOut = Concrete<Schemas["DemandSignalOut"]>;
export type DecisionMakerOut = Concrete<Schemas["DecisionMakerOut"]>;
export type DecisionMakerDetailOut = Concrete<Schemas["DecisionMakerDetailOut"]>;
export type CompanyContactsOut = Concrete<Schemas["CompanyContactsOut"]>;
export type RankedContactOut = Concrete<Schemas["RankedContactOut"]>;
export type ContactGroupOut = Concrete<Schemas["ContactGroupOut"]>;
export type HierarchyLevelOut = Concrete<Schemas["HierarchyLevelOut"]>;
export type CompanyIntelligenceOut = Concrete<Schemas["CompanyIntelligenceOut"]>;
export type CompanyRelationshipsOut = Concrete<Schemas["CompanyRelationshipsOut"]>;
export type NextBestContactOut = Concrete<Schemas["NextBestContactOut"]>;
export type OppIntelOut = Concrete<Schemas["OppIntelOut"]>;
export type AlertOut = Concrete<Schemas["AlertOut"]>;
export type RelationshipGraphOut = Concrete<Schemas["RelationshipGraphOut"]>;
export type GraphNodeOut = Concrete<Schemas["GraphNodeOut"]>;
export type GraphEdgeOut = Concrete<Schemas["GraphEdgeOut"]>;
export type LeadershipSignalOut = Concrete<Schemas["LeadershipSignalOut"]>;
export type EngagementOut = Concrete<Schemas["EngagementOut"]>;
export type DecisionMakerCompany = Concrete<Schemas["DecisionMakerCompany"]>;
export type DecisionMakerCompanies = Concrete<Schemas["DecisionMakerCompanies"]>;
export type LeadOut = Concrete<Schemas["LeadOut"]>;
export type LeadReviewOut = Concrete<Schemas["LeadReviewOut"]>;
export type LeadReviewIn = Schemas["LeadReviewIn"];
export type LeadReviewEventOut = Concrete<Schemas["LeadReviewEventOut"]>;
export type ReviewReportRow = Concrete<Schemas["ReviewReportRow"]>;
export type ReviewReports = Concrete<Schemas["ReviewReports"]>;
export type ReviewStatusOut = Concrete<Schemas["ReviewStatusOut"]>;
export type ReviewItemOut = Concrete<Schemas["ReviewItemOut"]>;
export type ReviewActionOut = Concrete<Schemas["ReviewActionOut"]>;
export type ReviewActionResult = Concrete<Schemas["ReviewActionResult"]>;
export type PipelineRunOut = Concrete<Schemas["PipelineRunOut"]>;
export type PipelineComponentHealth = Concrete<Schemas["PipelineComponentHealth"]>;
export type AnalyticsCoverage = Concrete<Schemas["AnalyticsCoverage"]>;
export type HealthOut = Concrete<Schemas["HealthOut"]>;
export type UserOut = Concrete<Schemas["UserOut"]>;
/** `user` re-pointed at the exported UserOut alias (Concrete — no optional undefined). */
export type AuthResult = { token: string; user: UserOut };
export type UserPatch = Schemas["UserPatch"];
export type UserAuditOut = Concrete<Schemas["UserAuditOut"]>;
export type AssignmentOut = Concrete<Schemas["AssignmentOut"]>;
export type AssignmentCreate = Schemas["AssignmentCreate"];
export type AssignmentPatch = Schemas["AssignmentPatch"];
export type WorkloadEntry = Concrete<Schemas["WorkloadEntry"]>;
export type WorkloadOut = { users: WorkloadEntry[]; unassigned_high_grade: number };
export type CompanyNoteOut = Concrete<Schemas["CompanyNoteOut"]>;
export type ActivityItem = Concrete<Schemas["ActivityItem"]>;
export type ContactOut = Concrete<Schemas["ContactOut"]>;
export type ContactIn = Schemas["ContactIn"];
export type DecisionMakerNoteOut = Concrete<Schemas["DecisionMakerNoteOut"]>;
export type DecisionMakerNoteIn = Schemas["DecisionMakerNoteIn"];
export type DecisionMakerNoteUpdate = Schemas["DecisionMakerNoteUpdate"];

// ----------------------------------------------------------------- outreach
export type OutreachContactOut = Concrete<Schemas["OutreachContactOut"]>;
export type OutreachSignalOut = Concrete<Schemas["OutreachSignalOut"]>;
export type OutreachLeadOut = Concrete<Schemas["OutreachLeadOut"]>;
export type OutreachLeadDetail = Concrete<Schemas["OutreachLeadDetail"]>;
export type OutreachLeadCreate = Schemas["OutreachLeadCreate"];
export type OutreachLeadPatch = Schemas["OutreachLeadPatch"];
export type OutreachSyncResult = Concrete<Schemas["OutreachSyncResult"]>;
export type OutreachTemplateOut = Concrete<Schemas["OutreachTemplateOut"]>;
export type OutreachTemplateIn = Schemas["OutreachTemplateIn"];
export type OutreachMessageOut = Concrete<Schemas["OutreachMessageOut"]>;
export type OutreachMessageCreate = Schemas["OutreachMessageCreate"];
export type OutreachMessagePatch = Schemas["OutreachMessagePatch"];
export type OutreachThreadOut = Concrete<Schemas["OutreachThreadOut"]>;
export type OutreachActivityOut = Concrete<Schemas["OutreachActivityOut"]>;
export type OutreachAnalytics = Concrete<Schemas["OutreachAnalytics"]>;
export type OutreachStageCount = Concrete<Schemas["OutreachStageCount"]>;

// ----- CRM Foundation (Phase 1) — hand-shaped (not yet in generated schema) -----
export interface OutreachTaskOut {
  id: number;
  title: string;
  description: string;
  company_domain: string | null;
  decision_maker_id: number | null;
  outreach_lead_id: number | null;
  assigned_to: number | null;
  created_by: number | null;
  due_at: string | null;
  priority: string;
  status: string;
  completed_by: number | null;
  completed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  is_overdue: boolean;
  assigned_to_email: string;
  created_by_email: string;
  company_name: string;
  decision_maker_name: string;
}

export interface OutreachMeetingOut {
  id: number;
  outreach_lead_id: number | null;
  company_domain: string | null;
  decision_maker_id: number | null;
  meeting_type: string;
  title: string;
  scheduled_at: string;
  duration_minutes: number;
  participants: string[];
  notes: string;
  outcome: string;
  next_action: string;
  created_by: number | null;
  created_at: string | null;
  updated_at: string | null;
  company_name: string;
  decision_maker_name: string;
  created_by_email: string;
  is_upcoming: boolean;
}

export interface UnifiedTimelineEvent {
  event_id: string;
  event_type: string;
  type: string;
  label: string;
  detail: string;
  actor: string;
  timestamp: string;
}

export interface OutreachFollowUpItem {
  lead_id: number;
  company_name: string;
  company_domain: string;
  due_at: string;
  days_until: number;
  is_overdue: boolean;
  days_since_activity: number | null;
  reminder_priority: string;
  stage: string;
}

export interface OutreachDashboardOut {
  tasks_due_today: OutreachTaskOut[];
  overdue_tasks: OutreachTaskOut[];
  upcoming_follow_ups: OutreachFollowUpItem[];
  upcoming_meetings: OutreachMeetingOut[];
  recent_activity: OutreachActivityOut[];
  open_tasks: number;
  total_meetings_this_week: number;
  overdue_follow_ups: number;
}

export interface ContactHistoryOut {
  decision_maker_id: number;
  full_name: string;
  title: string;
  company_domain: string;
  company_name: string;
  emails_sent: number;
  emails_received: number;
  meetings_count: number;
  notes_count: number;
  tasks_count: number;
  last_contacted_at: string | null;
  timeline: UnifiedTimelineEvent[];
}

export interface OutreachTaskIn {
  title: string;
  description?: string;
  company_domain?: string | null;
  decision_maker_id?: number | null;
  outreach_lead_id?: number | null;
  assigned_to?: number | null;
  due_at?: string | null;
  priority?: string;
}

export interface OutreachTaskPatch {
  title?: string;
  description?: string;
  assigned_to?: number | null;
  due_at?: string | null;
  priority?: string;
  status?: string;
}

export interface OutreachMeetingIn {
  outreach_lead_id?: number | null;
  company_domain?: string | null;
  decision_maker_id?: number | null;
  meeting_type?: string;
  title?: string;
  scheduled_at: string;
  duration_minutes?: number;
  participants?: string[];
  notes?: string;
  outcome?: string;
  next_action?: string;
}

export interface OutreachMeetingPatch {
  meeting_type?: string;
  title?: string;
  scheduled_at?: string;
  duration_minutes?: number;
  participants?: string[];
  notes?: string;
  outcome?: string;
  next_action?: string;
}

/** Canonical pipeline stages (mirrors config.enums.OUTREACH_STAGES), in order. */
export const OUTREACH_STAGES = [
  "research_complete",
  "outreach_ready",
  "contacted",
  "replied",
  "interested",
  "meeting_scheduled",
  "proposal_sent",
  "won",
  "lost",
] as const;
export type OutreachStage = (typeof OUTREACH_STAGES)[number];

/** Backend schema name is `PipelineStatusOut`; the client calls it `PipelineStatus`. */
export type PipelineStatus = Concrete<Schemas["PipelineStatusOut"]>;

// ----------------------------------------------------------------- campaigns (Enterprise CRM Phase 1)
export type CampaignOut = Concrete<Schemas["CampaignOut"]>;
export type CampaignCreate = Schemas["CampaignCreate"];
export type CampaignPatch = Schemas["CampaignPatch"];
export type CampaignMemberOut = Concrete<Schemas["CampaignMemberOut"]>;
export type CampaignMemberIn = Schemas["CampaignMemberIn"];
export type CampaignMemberPatch = Schemas["CampaignMemberPatch"];
export type CampaignAnalyticsOut = Concrete<Schemas["CampaignAnalyticsOut"]>;
export type CampaignDashboardOut = Omit<Concrete<Schemas["CampaignDashboardOut"]>, "campaigns"> & {
  campaigns: CampaignOut[];
};
export type CrmSequenceOut = Concrete<Schemas["CrmSequenceOut"]>;
export type CrmSequenceCreate = Schemas["CrmSequenceCreate"];
export type CrmSequencePatch = Schemas["CrmSequencePatch"];
export type CrmSequenceStepOut = Concrete<Schemas["CrmSequenceStepOut"]>;
export type CrmSequenceStepIn = Schemas["CrmSequenceStepIn"];
export type CrmSequenceStepPatch = Schemas["CrmSequenceStepPatch"];
export type CrmEnrollmentOut = Concrete<Schemas["CrmEnrollmentOut"]>;

/** Canonical campaign/sequence vocabularies (mirrors config.enums). */
export const CAMPAIGN_STATUSES = ["draft", "active", "paused", "completed", "archived"] as const;
export const CAMPAIGN_TYPES = ["cold_outreach", "nurture", "followup", "reengagement", "event"] as const;
export const CAMPAIGN_MEMBER_STATUSES = ["active", "paused", "completed", "removed"] as const;
export const CAMPAIGN_OUTCOMES = ["converted", "lost", "no_response", "disqualified"] as const;
export const SEQUENCE_STEP_ACTIONS = [
  "email", "follow_up", "meeting_request", "call", "task", "wait", "manual_review",
] as const;
export const SEQUENCE_ENROLLMENT_STATUSES = ["active", "paused", "completed", "cancelled", "failed"] as const;

// ----------------------------------------------------------------- deals & pipelines (Enterprise CRM Phase 2)
export type PipelineOut = Concrete<Schemas["PipelineOut"]>;
export type PipelineCreate = Schemas["PipelineCreate"];
export type PipelinePatch = Schemas["PipelinePatch"];
export type PipelineStageOut = Concrete<Schemas["PipelineStageOut"]>;
export type PipelineStageCreate = Schemas["PipelineStageCreate"];
export type PipelineStagePatch = Schemas["PipelineStagePatch"];
export type DealOut = Concrete<Schemas["DealOut"]>;
export type DealCreate = Schemas["DealCreate"];
export type DealPatch = Schemas["DealPatch"];
export type DealStageHistoryOut = Concrete<Schemas["DealStageHistoryOut"]>;
export type KanbanOut = Concrete<Schemas["KanbanOut"]>;
export type KanbanColumnOut = Concrete<Schemas["KanbanColumnOut"]>;
export type ForecastOut = Concrete<Schemas["ForecastOut"]>;
export type DealAnalyticsOut = Concrete<Schemas["DealAnalyticsOut"]>;
export type DealDashboardOut = Concrete<Schemas["DealDashboardOut"]>;
export type DealIntelligenceOut = Concrete<Schemas["DealIntelligenceOut"]>;

export const DEAL_PIPELINE_STAGE_TYPES = ["open", "won", "lost"] as const;
export const DEAL_FORECAST_CATEGORIES = ["pipeline", "best_case", "commit", "won", "omitted"] as const;
export const DEAL_CURRENCIES = ["USD", "EUR", "GBP", "INR", "JPY", "CAD", "AUD", "SGD"] as const;

// ----------------------------------------------------------------- customer success (Enterprise CRM Phase 4)
export type CsAccountOut = Concrete<Schemas["CsAccountOut"]>;
export type CsAccountCreate = Schemas["CsAccountCreate"];
export type CsAccountPatch = Schemas["CsAccountPatch"];
export type CsContactOut = Concrete<Schemas["CsContactOut"]>;
export type CsContactCreate = Schemas["CsContactCreate"];
export type CsContactPatch = Schemas["CsContactPatch"];
export type CsHealthScoreOut = Concrete<Schemas["CsHealthScoreOut"]>;
export type CsHealthScoreCreate = Schemas["CsHealthScoreCreate"];
export type CsLifecycleEventOut = Concrete<Schemas["CsLifecycleEventOut"]>;
export type CsContractOut = Concrete<Schemas["CsContractOut"]>;
export type CsContractCreate = Schemas["CsContractCreate"];
export type CsContractPatch = Schemas["CsContractPatch"];
export type CsSuccessPlanOut = Concrete<Schemas["CsSuccessPlanOut"]>;
export type CsSuccessPlanCreate = Schemas["CsSuccessPlanCreate"];
export type CsSuccessPlanPatch = Schemas["CsSuccessPlanPatch"];
export type CsMilestoneOut = Concrete<Schemas["CsMilestoneOut"]>;
export type CsMilestoneCreate = Schemas["CsMilestoneCreate"];
export type CsMilestonePatch = Schemas["CsMilestonePatch"];
export type CsRiskOut = Concrete<Schemas["CsRiskOut"]>;
export type CsRiskCreate = Schemas["CsRiskCreate"];
export type CsRiskPatch = Schemas["CsRiskPatch"];
export type CsTimelineEvent = Concrete<Schemas["CsTimelineEvent"]>;
export type CsDashboardOut = Concrete<Schemas["CsDashboardOut"]>;
export type CsAnalyticsOut = Concrete<Schemas["CsAnalyticsOut"]>;

export const CS_ACCOUNT_STATUSES = ["prospect", "active", "at_risk", "churned", "inactive"] as const;
export const CS_ACCOUNT_TIERS = ["strategic", "enterprise", "mid_market", "smb", "startup"] as const;
export const CS_CONTACT_ROLES = [
  "primary", "executive_sponsor", "technical", "procurement", "finance", "champion",
] as const;
export const CS_LIFECYCLE_STAGES = [
  "prospect", "customer", "onboarding", "adoption", "growth", "renewal", "expansion", "at_risk", "churned",
] as const;
export const CS_CONTRACT_STATUSES = [
  "draft", "active", "expired", "renewed", "terminated", "pending_renewal",
] as const;
export const CS_PLAN_STATUSES = ["draft", "active", "completed", "cancelled"] as const;
export const CS_MILESTONE_STATUSES = ["pending", "in_progress", "completed", "at_risk", "missed"] as const;
export const CS_RISK_SEVERITIES = ["low", "medium", "high", "critical"] as const;
export const CS_RISK_STATUSES = ["open", "mitigated", "accepted", "closed"] as const;

// ------------------------------------------------------- hand-shaped types
/** The explainable scoring trace (lead_scoring/scorer.py -> `rationale` dict). All
 *  fields optional/defensive — it is a free-form JSON column the API types as `dict`. */
export interface ScoreRationale {
  subscores?: {
    opportunity?: number;
    demand?: number;
    readiness?: number;
    decision_maker?: number;
  };
  weights?: {
    opportunity?: number;
    demand?: number;
    readiness?: number;
    decision_maker?: number;
  };
  weighted_base?: number;
  multipliers?: {
    region?: number;
    prospect?: number;
    tier?: number;
    combined?: number;
  };
  inputs?: {
    opportunities?: number;
    demand_score?: number;
    engineering_jobs?: number;
    decision_makers?: number;
    senior_decision_makers?: number;
    company_tier?: string;
    prospect_type?: string;
    compliance_flag?: string;
  };
  missing_inputs?: string[];
  final_lead_score?: number;
  grade?: string;
  /** Human-review score adjustment (reconciled Change_05) — present only when applied. */
  adjustment?: {
    status?: string;
    boost?: number;
    penalty?: number;
    floor_grade?: string;
    model_score?: number;
    model_grade?: string;
    adjusted_score?: number;
    adjusted_grade?: string;
    reason?: string;
    reviewed_by?: string;
    reviewed_at?: string | null;
    expires_at?: string | null;
    expired?: boolean;
  };
}

/** Per-engine row counts on a profile (backend types this as `dict[str,int]`). */
export interface ProfileCounts {
  opportunities: number;
  jobs: number;
  decision_makers: number;
  demand_signal: number;
  leadership_signals: number;
  review_events: number;
}

/** Generated `rationale` is opaque JSON; override it with the richer trace shape. */
export type LeadScoreOut = Omit<Concrete<Schemas["LeadScoreOut"]>, "rationale"> & {
  rationale: ScoreRationale;
};

/** `top_companies` re-pointed at the exported `LeadOut` alias (structurally identical). */
export type AnalyticsSummary = Omit<Concrete<Schemas["AnalyticsSummary"]>, "top_companies"> & {
  top_companies: LeadOut[];
};

/** The unified view — every engine's data for one company, joined on domain.
 *  Reconstructed so nested members use the exported aliases (incl. the rich
 *  `LeadScoreOut` and named `ProfileCounts`). */
export interface CompanyProfile {
  company: CompanyOut;
  lead_score: LeadScoreOut | null;
  review_status: ReviewStatusOut;
  counts: ProfileCounts;
  opportunities: OpportunityOut[];
  jobs: JobOut[];
  demand_signal: DemandSignalOut | null;
  decision_makers: DecisionMakerOut[];
  leadership_signals: LeadershipSignalOut[];
  engagement: EngagementOut | null;
  lead_review: LeadReviewOut | null;
  lead_review_history: LeadReviewEventOut[];
  review_feedback_enabled: boolean;
}

// ------------------------------------------------- scheduler / run history
export type ExecutionStageOut = Concrete<Schemas["ExecutionStageOut"]>;
export type ExecutionOut = Concrete<Schemas["ExecutionOut"]>;
export type SchedulerStatusOut = Concrete<Schemas["SchedulerStatusOut"]>;
export type RunNowResult = Concrete<Schemas["RunNowResult"]>;
