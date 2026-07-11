import { request } from "./client";
import type {
  AnalyticsCoverage,
  AnalyticsSummary,
  AuthResult,
  CompanyProfile,
  CompanySummary,
  DecisionMakerCompanies,
  AlertOut,
  CompanyContactsOut,
  CompanyIntelligenceOut,
  CompanyRelationshipsOut,
  DecisionMakerOut,
  DecisionMakerDetailOut,
  DemandSignalOut,
  HealthOut,
  LeadOut,
  LeadReviewOut,
  LeadReviewIn,
  LeadReviewEventOut,
  ReviewReports,
  LeadershipSignalOut,
  OpportunityOut,
  OpportunityDetailOut,
  OpportunityReviewIn,
  NewsSourceOut,
  NewsSourceIn,
  NewsSourcePatch,
  NewsSeedResult,
  Page,
  PipelineComponentHealth,
  PipelineRunOut,
  PipelineStatus,
  ReviewActionOut,
  ReviewActionResult,
  ReviewItemOut,
  UserOut,
  UserPatch,
  UserAuditOut,
  AssignmentOut,
  AssignmentCreate,
  AssignmentPatch,
  WorkloadOut,
  CompanyNoteOut,
  ActivityItem,
  ContactIn,
  ContactOut,
  DecisionMakerNoteOut,
  DecisionMakerNoteIn,
  DecisionMakerNoteUpdate,
  OutreachLeadOut,
  OutreachLeadDetail,
  OutreachLeadCreate,
  OutreachLeadPatch,
  OutreachSyncResult,
  OutreachTemplateOut,
  OutreachTemplateIn,
  OutreachMessageOut,
  OutreachMessageCreate,
  OutreachMessagePatch,
  OutreachThreadOut,
  OutreachActivityOut,
  OutreachAnalytics,
  OutreachTaskOut,
  OutreachTaskIn,
  OutreachTaskPatch,
  OutreachMeetingOut,
  OutreachMeetingIn,
  OutreachMeetingPatch,
  OutreachDashboardOut,
  OutreachFollowUpItem,
  UnifiedTimelineEvent,
  ContactHistoryOut,
  CampaignOut,
  CampaignCreate,
  CampaignPatch,
  CampaignMemberOut,
  CampaignMemberIn,
  CampaignMemberPatch,
  CampaignAnalyticsOut,
  CampaignDashboardOut,
  CrmSequenceOut,
  CrmSequenceCreate,
  CrmSequencePatch,
  CrmSequenceStepOut,
  CrmSequenceStepIn,
  CrmSequenceStepPatch,
  CrmEnrollmentOut,
  PipelineOut,
  PipelineCreate,
  PipelinePatch,
  PipelineStageOut,
  PipelineStageCreate,
  PipelineStagePatch,
  DealOut,
  DealCreate,
  DealPatch,
  DealStageHistoryOut,
  KanbanOut,
  ForecastOut,
  DealAnalyticsOut,
  DealDashboardOut,
  DealIntelligenceOut,
  CsAccountOut,
  CsAccountCreate,
  CsAccountPatch,
  CsContactOut,
  CsContactCreate,
  CsContactPatch,
  CsHealthScoreOut,
  CsHealthScoreCreate,
  CsLifecycleEventOut,
  CsContractOut,
  CsContractCreate,
  CsContractPatch,
  CsSuccessPlanOut,
  CsSuccessPlanCreate,
  CsSuccessPlanPatch,
  CsMilestoneOut,
  CsMilestoneCreate,
  CsMilestonePatch,
  CsRiskOut,
  CsRiskCreate,
  CsRiskPatch,
  CsTimelineEvent,
  CsDashboardOut,
  CsAnalyticsOut,
  SchedulerStatusOut,
  ExecutionOut,
  RunNowResult,
} from "./types";

export type CompanyListParams = {
  page?: number;
  page_size?: number;
  q?: string;
  domain?: string;
  tier?: string;
  prospect_type?: string;
  grade?: string;
  sort?: string;
  order?: "asc" | "desc";
}

export type LeadListParams = {
  page?: number;
  page_size?: number;
  grade?: string;
  tier?: string;
  prospect_type?: string;
  sort?: "model" | "human" | "combined";
}

export type OpportunityListParams = {
  page?: number;
  page_size?: number;
  opportunity_type?: string;
  company_domain?: string;
  date_from?: string;
  date_to?: string;
  lifecycle_status?: string;
  hide_archived?: boolean;
  sort?: "newest" | "oldest" | "score";
}

export type DemandListParams = {
  page?: number;
  page_size?: number;
  min_demand_score?: number;
  technology_focus?: string;
}

export type DecisionMakerListParams = {
  page?: number;
  page_size?: number;
  company_domain?: string;
  seniority?: string;
  senior?: boolean;
}

export type ReviewListParams = {
  page?: number;
  page_size?: number;
  status?: string;
  source_engine?: string;
  match_type?: string;
}

export type LeadershipSignalListParams = {
  page?: number;
  page_size?: number;
  company_domain?: string;
  movement_type?: string;
  seniority_band?: string;
  source?: string;
}

export type CampaignListParams = {
  owner_id?: number;
  status?: string;
  campaign_type?: string;
  company_domain?: string;
  decision_maker_id?: number;
  tag?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export type SequenceListParams = {
  active_only?: boolean;
  limit?: number;
  offset?: number;
}

export type EnrollmentListParams = {
  sequence_id?: number;
  campaign_id?: number;
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export type PipelineListParams = {
  active_only?: boolean;
  limit?: number;
  offset?: number;
}

export type DealListParams = {
  pipeline_id?: number;
  stage_id?: number;
  owner_id?: number;
  company_domain?: string;
  forecast_category?: string;
  search?: string;
  closing_before?: string;
  closing_after?: string;
  limit?: number;
  offset?: number;
}

export type CsAccountListParams = {
  status?: string;
  tier?: string;
  lifecycle_stage?: string;
  limit?: number;
  offset?: number;
}

export type CsContractListParams = {
  account_id?: number;
  status?: string;
  limit?: number;
  offset?: number;
}

function actorHeader(actor?: string): Record<string, string> {
  return actor ? { "X-Actor": actor } : {};
}

/** Typed function per endpoint. Routers/params mirror backend/routers/*. */
export const api = {
  health: () => request<HealthOut>("/health"),

  auth: {
    microsoft: (id_token: string) =>
      request<AuthResult>("/auth/microsoft", { method: "POST", body: { id_token } }),
    me: () => request<UserOut>("/auth/me"),
    logout: () => request<{ status: string }>("/auth/logout", { method: "POST" }),
  },

  companies: (p: CompanyListParams = {}) =>
    request<Page<CompanySummary>>("/companies", { params: p }),
  companyProfile: (domain: string) =>
    request<CompanyProfile>(`/companies/${encodeURIComponent(domain)}`),

  leads: (p: LeadListParams = {}) => request<Page<LeadOut>>("/leads", { params: p }),

  opportunities: (p: OpportunityListParams = {}) =>
    request<Page<OpportunityOut>>("/opportunities", { params: p }),
  opportunity: (id: string) =>
    request<OpportunityDetailOut>(`/opportunities/${encodeURIComponent(id)}`),
  reviewOpportunity: (id: string, body: OpportunityReviewIn) =>
    request<OpportunityDetailOut>(`/opportunities/${encodeURIComponent(id)}/review`, {
      method: "POST",
      body,
    }),
  setOpportunityLifecycle: (id: string, lifecycle_status: string) =>
    request<OpportunityDetailOut>(`/opportunities/${encodeURIComponent(id)}/lifecycle`, {
      method: "POST",
      params: { lifecycle_status },
    }),
  newsSources: () => request<NewsSourceOut[]>("/opportunities/news-sources"),
  createNewsSource: (body: NewsSourceIn) =>
    request<NewsSourceOut>("/opportunities/news-sources", { method: "POST", body }),
  updateNewsSource: (id: number, patch: NewsSourcePatch) =>
    request<NewsSourceOut>(`/opportunities/news-sources/${id}`, { method: "PATCH", body: patch }),
  seedNewsSources: () =>
    request<NewsSeedResult>("/opportunities/news-sources/seed", { method: "POST" }),

  demandSignals: (p: DemandListParams = {}) =>
    request<Page<DemandSignalOut>>("/demand-signals", { params: p }),

  decisionMakers: (p: DecisionMakerListParams = {}) =>
    request<Page<DecisionMakerOut>>("/decision-makers", { params: p }),

  leadershipSignals: (p: LeadershipSignalListParams = {}) =>
    request<Page<LeadershipSignalOut>>("/leadership-signals", { params: p }),
  decisionMakerCompanies: () =>
    request<DecisionMakerCompanies>("/decision-makers/companies"),
  companyContacts: (domain: string) =>
    request<CompanyContactsOut>(`/decision-makers/company/${encodeURIComponent(domain)}`),
  companyIntelligence: (domain: string) =>
    request<CompanyIntelligenceOut>(`/decision-makers/company/${encodeURIComponent(domain)}/intelligence`),
  companyRelationships: (domain: string) =>
    request<CompanyRelationshipsOut>(`/decision-makers/company/${encodeURIComponent(domain)}/relationships`),
  alerts: (limit = 25) => request<AlertOut[]>("/alerts", { params: { limit } }),
  dmDetail: (id: number) =>
    request<DecisionMakerDetailOut>(`/decision-makers/${id}`),
  dmContact: (id: number) =>
    request<ContactOut | null>(`/decision-makers/${id}/contact`),
  putDmContact: (id: number, body: ContactIn) =>
    request<ContactOut>(`/decision-makers/${id}/contact`, { method: "PUT", body }),

  dmNotes: (id: number) =>
    request<DecisionMakerNoteOut[]>(`/decision-makers/${id}/notes`),
  createDmNote: (id: number, body: DecisionMakerNoteIn) =>
    request<DecisionMakerNoteOut>(`/decision-makers/${id}/notes`, { method: "POST", body }),
  updateDmNote: (id: number, noteId: number, body: DecisionMakerNoteUpdate) =>
    request<DecisionMakerNoteOut>(`/decision-makers/${id}/notes/${noteId}`, {
      method: "PATCH",
      body,
    }),
  deleteDmNote: (id: number, noteId: number) =>
    request<null>(`/decision-makers/${id}/notes/${noteId}`, { method: "DELETE" }),

  analyticsSummary: () => request<AnalyticsSummary>("/analytics/summary"),
  analyticsCoverage: () => request<AnalyticsCoverage>("/analytics/coverage"),

  pipelineRuns: (limit = 20) => request<PipelineRunOut[]>("/pipeline/runs", { params: { limit } }),
  pipelineHealth: () => request<PipelineComponentHealth[]>("/pipeline/health"),
  pipelineStatus: () => request<PipelineStatus>("/pipeline/status"),

  reviewQueue: (p: ReviewListParams = {}) =>
    request<Page<ReviewItemOut>>("/review-queue", { params: p }),
  reviewItem: (id: number) => request<ReviewItemOut>(`/review-queue/${id}`),
  reviewActions: (id: number) => request<ReviewActionOut[]>(`/review-queue/${id}/actions`),

  approve: (id: number, actor?: string) =>
    request<ReviewActionResult>(`/review-queue/${id}/approve`, {
      method: "POST",
      headers: actorHeader(actor),
    }),
  merge: (id: number, target_domain: string, actor?: string) =>
    request<ReviewActionResult>(`/review-queue/${id}/merge`, {
      method: "POST",
      body: { target_domain },
      headers: actorHeader(actor),
    }),
  reject: (id: number, reason?: string, actor?: string) =>
    request<ReviewActionResult>(`/review-queue/${id}/reject`, {
      method: "POST",
      body: { reason: reason ?? null },
      headers: actorHeader(actor),
    }),
  createAlias: (id: number, name: string, company_domain: string, actor?: string) =>
    request<ReviewActionResult>(`/review-queue/${id}/alias`, {
      method: "POST",
      body: { name, company_domain },
      headers: actorHeader(actor),
    }),

  // --- accounts / CRM (Phase 2) ---
  adminUsers: (p: { status?: string; q?: string; limit?: number; offset?: number } = {}) =>
    request<Page<UserOut>>("/admin/users", { params: p }),
  updateUser: (id: number, patch: UserPatch) =>
    request<UserOut>(`/admin/users/${id}`, { method: "PATCH", body: patch }),
  approveUser: (id: number) => request<UserOut>(`/admin/users/${id}/approve`, { method: "POST" }),
  rejectUser: (id: number) => request<UserOut>(`/admin/users/${id}/reject`, { method: "POST" }),
  deleteUser: (id: number) => request<UserOut>(`/admin/users/${id}`, { method: "DELETE" }),
  userAudit: (limit = 100) => request<UserAuditOut[]>("/admin/users/audit", { params: { limit } }),

  assignments: (p: { user_id?: number; status?: string } = {}) =>
    request<AssignmentOut[]>("/assignments", { params: p }),
  myAssignments: () => request<AssignmentOut[]>("/assignments/mine"),
  assignableUsers: () => request<UserOut[]>("/assignments/users"),
  workload: () => request<WorkloadOut>("/assignments/workload"),
  createAssignment: (body: AssignmentCreate) =>
    request<AssignmentOut>("/assignments", { method: "POST", body }),
  updateAssignment: (id: number, patch: AssignmentPatch) =>
    request<AssignmentOut>(`/assignments/${id}`, { method: "PATCH", body: patch }),
  unassign: (id: number) => request<null>(`/assignments/${id}`, { method: "DELETE" }),

  companyNotes: (domain: string) =>
    request<CompanyNoteOut[]>(`/companies/${encodeURIComponent(domain)}/notes`),
  addCompanyNote: (domain: string, body: string) =>
    request<CompanyNoteOut>(`/companies/${encodeURIComponent(domain)}/notes`, {
      method: "POST",
      body: { body },
    }),
  companyActivity: (domain: string) =>
    request<ActivityItem[]>(`/companies/${encodeURIComponent(domain)}/activity`),

  // --- human lead review / feedback (P-task viii) ---
  leadReview: (domain: string) =>
    request<LeadReviewOut | null>(`/reviews/${encodeURIComponent(domain)}`),
  putLeadReview: (domain: string, body: LeadReviewIn) =>
    request<LeadReviewOut>(`/reviews/${encodeURIComponent(domain)}`, { method: "PUT", body }),
  leadReviewHistory: (domain: string) =>
    request<LeadReviewEventOut[]>(`/reviews/${encodeURIComponent(domain)}/history`),
  reviewReports: () => request<ReviewReports>("/reviews/reports"),

  // --- outreach (native module) ---
  outreach: {
    leads: (p: {
      stage?: string;
      mine?: boolean;
      open_only?: boolean;
      search?: string;
      page?: number;
      page_size?: number;
    } = {}) => request<Page<OutreachLeadOut>>("/outreach/leads", { params: p }),
    lead: (id: number) => request<OutreachLeadDetail>(`/outreach/leads/${id}`),
    createLead: (body: OutreachLeadCreate) =>
      request<OutreachLeadDetail>("/outreach/leads", { method: "POST", body }),
    patchLead: (id: number, body: OutreachLeadPatch) =>
      request<OutreachLeadDetail>(`/outreach/leads/${id}`, { method: "PATCH", body }),
    sync: (limit = 40) =>
      request<OutreachSyncResult>("/outreach/leads/sync", { method: "POST", params: { limit } }),
    activities: (id: number) =>
      request<OutreachActivityOut[]>(`/outreach/leads/${id}/activities`),
    addNote: (leadId: number, text: string) =>
      request<OutreachActivityOut>(`/outreach/leads/${leadId}/notes`, { method: "POST", body: { text } }),

    messages: (id: number) => request<OutreachMessageOut[]>(`/outreach/leads/${id}/messages`),
    createMessage: (id: number, body: OutreachMessageCreate) =>
      request<OutreachMessageOut>(`/outreach/leads/${id}/messages`, { method: "POST", body }),
    patchMessage: (id: number, body: OutreachMessagePatch) =>
      request<OutreachMessageOut>(`/outreach/messages/${id}`, { method: "PATCH", body }),
    submitMessage: (id: number) =>
      request<OutreachMessageOut>(`/outreach/messages/${id}/submit`, { method: "POST" }),
    approveMessage: (id: number) =>
      request<OutreachMessageOut>(`/outreach/messages/${id}/approve`, { method: "POST" }),
    sendMessage: (id: number) =>
      request<OutreachMessageOut>(`/outreach/messages/${id}/send`, { method: "POST" }),
    replyMessage: (id: number) =>
      request<OutreachMessageOut>(`/outreach/messages/${id}/reply`, { method: "POST" }),

    templates: (activeOnly = false) =>
      request<OutreachTemplateOut[]>("/outreach/templates", { params: { active_only: activeOnly } }),
    createTemplate: (body: OutreachTemplateIn) =>
      request<OutreachTemplateOut>("/outreach/templates", { method: "POST", body }),
    updateTemplate: (id: number, body: OutreachTemplateIn) =>
      request<OutreachTemplateOut>(`/outreach/templates/${id}`, { method: "PUT", body }),
    deleteTemplate: (id: number) =>
      request<null>(`/outreach/templates/${id}`, { method: "DELETE" }),

    approvals: () => request<OutreachMessageOut[]>("/outreach/approvals"),
    inbox: () => request<OutreachThreadOut[]>("/outreach/inbox"),
    analytics: () => request<OutreachAnalytics>("/outreach/analytics"),

    // CRM Foundation
    dashboard: () => request<OutreachDashboardOut>("/outreach/dashboard"),
    followUps: (limit = 30) =>
      request<OutreachFollowUpItem[]>("/outreach/follow-ups", { params: { limit } }),
    timeline: (leadId: number, limit = 50) =>
      request<UnifiedTimelineEvent[]>(`/outreach/leads/${leadId}/timeline`, { params: { limit } }),

    tasks: (p: {
      outreach_lead_id?: number;
      company_domain?: string;
      decision_maker_id?: number;
      assigned_to?: number;
      mine?: boolean;
      status?: string;
      overdue_only?: boolean;
      page?: number;
      page_size?: number;
    } = {}) => request<Page<OutreachTaskOut>>("/outreach/tasks", { params: p }),
    task: (id: number) => request<OutreachTaskOut>(`/outreach/tasks/${id}`),
    createTask: (body: OutreachTaskIn) =>
      request<OutreachTaskOut>("/outreach/tasks", { method: "POST", body }),
    patchTask: (id: number, body: OutreachTaskPatch) =>
      request<OutreachTaskOut>(`/outreach/tasks/${id}`, { method: "PATCH", body }),
    deleteTask: (id: number) =>
      request<null>(`/outreach/tasks/${id}`, { method: "DELETE" }),

    meetings: (p: {
      outreach_lead_id?: number;
      company_domain?: string;
      decision_maker_id?: number;
      upcoming_only?: boolean;
      page?: number;
      page_size?: number;
    } = {}) => request<Page<OutreachMeetingOut>>("/outreach/meetings", { params: p }),
    meeting: (id: number) => request<OutreachMeetingOut>(`/outreach/meetings/${id}`),
    createMeeting: (body: OutreachMeetingIn) =>
      request<OutreachMeetingOut>("/outreach/meetings", { method: "POST", body }),
    patchMeeting: (id: number, body: OutreachMeetingPatch) =>
      request<OutreachMeetingOut>(`/outreach/meetings/${id}`, { method: "PATCH", body }),
    deleteMeeting: (id: number) =>
      request<null>(`/outreach/meetings/${id}`, { method: "DELETE" }),

    contactHistory: (dmId: number) =>
      request<ContactHistoryOut>(`/outreach/contacts/${dmId}/history`),
  },

  // --- Enterprise CRM Phase 1: campaigns / sequences / enrollments ---
  campaigns: {
    list: (p: CampaignListParams = {}) => request<Page<CampaignOut>>("/campaigns", { params: p }),
    get: (id: number) => request<CampaignOut>(`/campaigns/${id}`),
    create: (body: CampaignCreate) => request<CampaignOut>("/campaigns", { method: "POST", body }),
    patch: (id: number, body: CampaignPatch) =>
      request<CampaignOut>(`/campaigns/${id}`, { method: "PATCH", body }),
    archive: (id: number) => request<null>(`/campaigns/${id}`, { method: "DELETE" }),
    dashboard: () => request<CampaignDashboardOut>("/campaigns/dashboard"),
    analytics: (id: number) => request<CampaignAnalyticsOut>(`/campaigns/${id}/analytics`),
    timeline: (id: number, p: { limit?: number; offset?: number } = {}) =>
      request<UnifiedTimelineEvent[]>(`/campaigns/${id}/timeline`, { params: p }),

    members: (id: number, p: { limit?: number; offset?: number } = {}) =>
      request<Page<CampaignMemberOut>>(`/campaigns/${id}/members`, { params: p }),
    addMember: (id: number, body: CampaignMemberIn) =>
      request<CampaignMemberOut>(`/campaigns/${id}/members`, { method: "POST", body }),
    patchMember: (id: number, memberId: number, body: CampaignMemberPatch) =>
      request<CampaignMemberOut>(`/campaigns/${id}/members/${memberId}`, { method: "PATCH", body }),
    removeMember: (id: number, memberId: number) =>
      request<null>(`/campaigns/${id}/members/${memberId}`, { method: "DELETE" }),
    enrollMember: (id: number, memberId: number, sequenceId: number) =>
      request<CrmEnrollmentOut>(`/campaigns/${id}/members/${memberId}/enroll`, {
        method: "POST",
        params: { sequence_id: sequenceId },
      }),
  },

  sequences: {
    list: (p: SequenceListParams = {}) => request<Page<CrmSequenceOut>>("/sequences", { params: p }),
    get: (id: number) => request<CrmSequenceOut>(`/sequences/${id}`),
    create: (body: CrmSequenceCreate) => request<CrmSequenceOut>("/sequences", { method: "POST", body }),
    patch: (id: number, body: CrmSequencePatch) =>
      request<CrmSequenceOut>(`/sequences/${id}`, { method: "PATCH", body }),
    delete: (id: number) => request<null>(`/sequences/${id}`, { method: "DELETE" }),
    addStep: (id: number, body: CrmSequenceStepIn) =>
      request<CrmSequenceStepOut>(`/sequences/${id}/steps`, { method: "POST", body }),
    patchStep: (id: number, stepId: number, body: CrmSequenceStepPatch) =>
      request<CrmSequenceStepOut>(`/sequences/${id}/steps/${stepId}`, { method: "PATCH", body }),
    deleteStep: (id: number, stepId: number) =>
      request<null>(`/sequences/${id}/steps/${stepId}`, { method: "DELETE" }),
  },

  enrollments: {
    list: (p: EnrollmentListParams = {}) => request<Page<CrmEnrollmentOut>>("/enrollments", { params: p }),
    pause: (id: number) => request<CrmEnrollmentOut>(`/enrollments/${id}/pause`, { method: "POST" }),
    resume: (id: number) => request<CrmEnrollmentOut>(`/enrollments/${id}/resume`, { method: "POST" }),
    cancel: (id: number) => request<CrmEnrollmentOut>(`/enrollments/${id}/cancel`, { method: "POST" }),
    advance: (id: number) => request<CrmEnrollmentOut>(`/enrollments/${id}/advance`, { method: "POST" }),
    skipStep: (id: number, stepId: number) =>
      request<CrmEnrollmentOut>(`/enrollments/${id}/steps/${stepId}/skip`, { method: "POST" }),
  },

  // --- Enterprise CRM Phase 2: pipelines / deals ---
  pipelines: {
    list: (p: PipelineListParams = {}) => request<Page<PipelineOut>>("/pipelines", { params: p }),
    get: (id: number) => request<PipelineOut>(`/pipelines/${id}`),
    create: (body: PipelineCreate) => request<PipelineOut>("/pipelines", { method: "POST", body }),
    patch: (id: number, body: PipelinePatch) => request<PipelineOut>(`/pipelines/${id}`, { method: "PATCH", body }),
    delete: (id: number) => request<null>(`/pipelines/${id}`, { method: "DELETE" }),
    dashboard: (pipelineId?: number) => request<DealDashboardOut>("/pipelines/dashboard", { params: { pipeline_id: pipelineId } }),
    kanban: (id: number, p: { stage_id?: number; owner_id?: number; search?: string } = {}) =>
      request<KanbanOut>(`/pipelines/${id}/kanban`, { params: p }),
    forecast: (id: number) => request<ForecastOut>(`/pipelines/${id}/forecast`),
    analytics: (id: number) => request<DealAnalyticsOut>(`/pipelines/${id}/analytics`),

    addStage: (id: number, body: PipelineStageCreate) =>
      request<PipelineStageOut>(`/pipelines/${id}/stages`, { method: "POST", body }),
    patchStage: (id: number, stageId: number, body: PipelineStagePatch) =>
      request<PipelineStageOut>(`/pipelines/${id}/stages/${stageId}`, { method: "PATCH", body }),
    deleteStage: (id: number, stageId: number) =>
      request<null>(`/pipelines/${id}/stages/${stageId}`, { method: "DELETE" }),
  },

  deals: {
    list: (p: DealListParams = {}) => request<Page<DealOut>>("/deals", { params: p }),
    get: (id: number) => request<DealOut>(`/deals/${id}`),
    create: (body: DealCreate) => request<DealOut>("/deals", { method: "POST", body }),
    patch: (id: number, body: DealPatch) => request<DealOut>(`/deals/${id}`, { method: "PATCH", body }),
    delete: (id: number) => request<null>(`/deals/${id}`, { method: "DELETE" }),
    move: (id: number, stageId: number) =>
      request<DealOut>(`/deals/${id}/move`, { method: "POST", body: { stage_id: stageId } }),
    history: (id: number) => request<DealStageHistoryOut[]>(`/deals/${id}/history`),
    timeline: (id: number, p: { limit?: number; offset?: number } = {}) =>
      request<UnifiedTimelineEvent[]>(`/deals/${id}/timeline`, { params: p }),
    intelligence: (id: number) => request<DealIntelligenceOut>(`/deals/${id}/intelligence`),
  },

  // --- Enterprise CRM Phase 4: customer success ---
  cs: {
    accounts: (p: CsAccountListParams = {}) => request<Page<CsAccountOut>>("/cs/accounts", { params: p }),
    account: (id: number) => request<CsAccountOut>(`/cs/accounts/${id}`),
    createAccount: (body: CsAccountCreate) => request<CsAccountOut>("/cs/accounts", { method: "POST", body }),
    patchAccount: (id: number, body: CsAccountPatch) =>
      request<CsAccountOut>(`/cs/accounts/${id}`, { method: "PATCH", body }),
    deleteAccount: (id: number) => request<null>(`/cs/accounts/${id}`, { method: "DELETE" }),

    contacts: (accountId: number) => request<CsContactOut[]>(`/cs/accounts/${accountId}/contacts`),
    createContact: (body: CsContactCreate) => request<CsContactOut>("/cs/contacts", { method: "POST", body }),
    patchContact: (id: number, body: CsContactPatch) =>
      request<CsContactOut>(`/cs/contacts/${id}`, { method: "PATCH", body }),
    deleteContact: (id: number) => request<null>(`/cs/contacts/${id}`, { method: "DELETE" }),

    scoreAccount: (accountId: number, body: CsHealthScoreCreate) =>
      request<CsHealthScoreOut>(`/cs/accounts/${accountId}/health`, { method: "POST", body }),
    health: (accountId: number) => request<CsHealthScoreOut>(`/cs/accounts/${accountId}/health`),
    healthHistory: (accountId: number) => request<CsHealthScoreOut[]>(`/cs/accounts/${accountId}/health/history`),

    lifecycle: (accountId: number) => request<CsLifecycleEventOut[]>(`/cs/accounts/${accountId}/lifecycle`),

    contracts: (p: CsContractListParams = {}) => request<Page<CsContractOut>>("/cs/contracts", { params: p }),
    createContract: (body: CsContractCreate) => request<CsContractOut>("/cs/contracts", { method: "POST", body }),
    patchContract: (id: number, body: CsContractPatch) =>
      request<CsContractOut>(`/cs/contracts/${id}`, { method: "PATCH", body }),
    deleteContract: (id: number) => request<null>(`/cs/contracts/${id}`, { method: "DELETE" }),

    plans: (accountId: number) => request<CsSuccessPlanOut[]>(`/cs/accounts/${accountId}/plans`),
    createPlan: (body: CsSuccessPlanCreate) => request<CsSuccessPlanOut>("/cs/plans", { method: "POST", body }),
    patchPlan: (id: number, body: CsSuccessPlanPatch) =>
      request<CsSuccessPlanOut>(`/cs/plans/${id}`, { method: "PATCH", body }),
    deletePlan: (id: number) => request<null>(`/cs/plans/${id}`, { method: "DELETE" }),

    milestones: (planId: number) => request<CsMilestoneOut[]>(`/cs/plans/${planId}/milestones`),
    createMilestone: (body: CsMilestoneCreate) => request<CsMilestoneOut>("/cs/milestones", { method: "POST", body }),
    patchMilestone: (id: number, body: CsMilestonePatch) =>
      request<CsMilestoneOut>(`/cs/milestones/${id}`, { method: "PATCH", body }),
    deleteMilestone: (id: number) => request<null>(`/cs/milestones/${id}`, { method: "DELETE" }),

    risks: (accountId: number, status?: string) =>
      request<CsRiskOut[]>(`/cs/accounts/${accountId}/risks`, { params: { status } }),
    createRisk: (body: CsRiskCreate) => request<CsRiskOut>("/cs/risks", { method: "POST", body }),
    patchRisk: (id: number, body: CsRiskPatch) => request<CsRiskOut>(`/cs/risks/${id}`, { method: "PATCH", body }),
    deleteRisk: (id: number) => request<null>(`/cs/risks/${id}`, { method: "DELETE" }),

    timeline: (accountId: number, p: { limit?: number; offset?: number } = {}) =>
      request<CsTimelineEvent[]>(`/cs/accounts/${accountId}/timeline`, { params: p }),

    dashboard: () => request<CsDashboardOut>("/cs/dashboard"),
    analytics: () => request<CsAnalyticsOut>("/cs/analytics"),
  },

  scheduler: {
    status: () => request<SchedulerStatusOut>("/scheduler/status"),
    runs: (p: { page?: number; page_size?: number } = {}) =>
      request<Page<ExecutionOut>>("/scheduler/runs", { params: p }),
    run: (runId: string) => request<ExecutionOut>(`/scheduler/runs/${encodeURIComponent(runId)}`),
    runNow: () => request<RunNowResult>("/scheduler/run-now", { method: "POST" }),
  },
};
