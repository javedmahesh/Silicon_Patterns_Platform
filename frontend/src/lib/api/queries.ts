import { keepPreviousData, useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  api,
  type CampaignListParams,
  type CompanyListParams,
  type DecisionMakerListParams,
  type DemandListParams,
  type EnrollmentListParams,
  type LeadListParams,
  type LeadershipSignalListParams,
  type OpportunityListParams,
  type ReviewListParams,
  type SequenceListParams,
} from "./endpoints";
import { qk } from "./queryKeys";
import type {
  AssignmentPatch,
  ContactIn,
  DecisionMakerNoteIn,
  LeadReviewIn,
  OpportunityReviewIn,
  UserPatch,
} from "./types";

export function useHealth() {
  return useQuery({
    queryKey: qk.health,
    queryFn: api.health,
    staleTime: 15_000,
    refetchInterval: 30_000,
    retry: 0,
  });
}

export function useCompanies(p: CompanyListParams) {
  return useQuery({
    queryKey: qk.companies(p),
    queryFn: () => api.companies(p),
    placeholderData: keepPreviousData,
  });
}

/** Manually add a company to the universe (manager+); refreshes the companies list. */
export function useCreateCompany() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: import("./types").CompanyCreate) => api.createCompany(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["companies"] }),
  });
}

export function useUpdateCompany() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { domain: string; body: import("./types").CompanyUpdate }) =>
      api.updateCompany(v.domain, v.body),
    onSuccess: (_r, v) => {
      qc.invalidateQueries({ queryKey: ["companies"] });
      qc.invalidateQueries({ queryKey: ["company", v.domain] });
    },
  });
}

export function useDeleteCompany() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (domain: string) => api.deleteCompany(domain),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["companies"] });
      qc.invalidateQueries({ queryKey: ["decision-makers"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
    },
  });
}

export function useUpdateDecisionMaker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: number; body: import("./types").DecisionMakerUpdate }) =>
      api.updateDecisionMaker(v.id, v.body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["decision-makers"] }),
  });
}

export function useDeleteDecisionMaker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteDecisionMaker(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["decision-makers"] }),
  });
}

export function useCompanyProfile(domain: string | undefined) {
  return useQuery({
    queryKey: qk.companyProfile(domain ?? ""),
    queryFn: () => api.companyProfile(domain as string),
    enabled: Boolean(domain),
  });
}

/** Parallel per-domain profile fetches for the Compare view (each cached on the
 *  same key as the single-company profile, so it's warm after visiting a profile). */
export function useCompanyProfiles(domains: string[]) {
  return useQueries({
    queries: domains.map((d) => ({
      queryKey: qk.companyProfile(d),
      queryFn: () => api.companyProfile(d),
      enabled: Boolean(d),
    })),
  });
}

export function useLeads(p: LeadListParams) {
  return useQuery({
    queryKey: qk.leads(p),
    queryFn: () => api.leads(p),
    placeholderData: keepPreviousData,
  });
}

export function useOpportunities(p: OpportunityListParams) {
  return useQuery({
    queryKey: qk.opportunities(p),
    queryFn: () => api.opportunities(p),
    placeholderData: keepPreviousData,
  });
}

/** Full opportunity intelligence (detail panel). */
export function useOpportunity(id: string | undefined) {
  return useQuery({
    queryKey: qk.opportunity(id ?? ""),
    queryFn: () => api.opportunity(id as string),
    enabled: Boolean(id),
  });
}

/** Configured news sources (RSS / Google Alerts) + create/toggle/seed actions. */
export function useNewsSources() {
  return useQuery({ queryKey: qk.newsSources, queryFn: api.newsSources });
}

export function useNewsSourceMutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: qk.newsSources });
  const create = useMutation({ mutationFn: api.createNewsSource, onSuccess: invalidate });
  const update = useMutation({
    mutationFn: (v: { id: number; patch: import("./types").NewsSourcePatch }) =>
      api.updateNewsSource(v.id, v.patch),
    onSuccess: invalidate,
  });
  const seed = useMutation({ mutationFn: api.seedNewsSources, onSuccess: invalidate });
  return { create, update, seed };
}

/** Manual-review + lifecycle write actions for an opportunity. All invalidate the
 *  opportunity list, its detail, and company/analytics caches. */
export function useOpportunityReview() {
  const qc = useQueryClient();
  const invalidate = (id?: string) => {
    qc.invalidateQueries({ queryKey: ["opportunities"] });
    if (id) qc.invalidateQueries({ queryKey: qk.opportunity(id) });
    qc.invalidateQueries({ queryKey: ["analytics"] });
  };
  const review = useMutation({
    mutationFn: (v: { id: string; body: OpportunityReviewIn }) =>
      api.reviewOpportunity(v.id, v.body),
    onSuccess: (_d, v) => invalidate(v.id),
  });
  const setLifecycle = useMutation({
    mutationFn: (v: { id: string; lifecycle_status: string }) =>
      api.setOpportunityLifecycle(v.id, v.lifecycle_status),
    onSuccess: (_d, v) => invalidate(v.id),
  });
  return { review, setLifecycle };
}

/** Admin-only hard delete of an opportunity (Blog Crawler / news entry). */
export function useDeleteOpportunity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteOpportunity(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["opportunities"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
    },
  });
}

export function useUpdateOpportunity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; body: import("./types").OpportunityUpdate }) =>
      api.updateOpportunity(v.id, v.body),
    onSuccess: (_r, v) => {
      qc.invalidateQueries({ queryKey: ["opportunities"] });
      qc.invalidateQueries({ queryKey: ["opportunity", v.id] });
    },
  });
}

/** Admin-only hard delete of a person-level leadership signal. */
export function useDeleteLeadershipSignal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteLeadershipSignal(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["leadership-signals"] }),
  });
}

export function useUpdateLeadershipSignal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; body: import("./types").LeadershipSignalUpdate }) =>
      api.updateLeadershipSignal(v.id, v.body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["leadership-signals"] }),
  });
}

export function useDemandSignals(p: DemandListParams) {
  return useQuery({
    queryKey: qk.demandSignals(p),
    queryFn: () => api.demandSignals(p),
    placeholderData: keepPreviousData,
  });
}

export function useDecisionMakers(p: DecisionMakerListParams, opts?: { enabled?: boolean }) {
  return useQuery({
    queryKey: qk.decisionMakers(p),
    queryFn: () => api.decisionMakers(p),
    placeholderData: keepPreviousData,
    enabled: opts?.enabled ?? true,
  });
}

export function useLeadershipSignals(p: LeadershipSignalListParams, opts?: { enabled?: boolean }) {
  return useQuery({
    queryKey: qk.leadershipSignals(p),
    queryFn: () => api.leadershipSignals(p),
    placeholderData: keepPreviousData,
    enabled: opts?.enabled ?? true,
  });
}

export function useDecisionMakerCompanies() {
  return useQuery({
    queryKey: qk.decisionMakerCompanies,
    queryFn: api.decisionMakerCompanies,
    placeholderData: keepPreviousData,
  });
}

/** Statuses at which a DM intelligence job is finished (polling can stop). */
const DM_JOB_TERMINAL = ["completed", "partial", "failed"];

/** Kick off a manual Decision Maker Intelligence run (manager+). */
export function useRunDmIntelligence() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: import("./types").DmIntelligenceRunIn) => api.runDmIntelligence(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.dmIntelligenceRuns }),
  });
}

/** Poll one DM intelligence job for live per-company progress; stops once terminal. */
export function useDmIntelligenceRun(id: number | undefined) {
  return useQuery({
    queryKey: qk.dmIntelligenceRun(id ?? -1),
    queryFn: () => api.dmIntelligenceRun(id as number),
    enabled: Boolean(id),
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status && DM_JOB_TERMINAL.includes(status) ? false : 2000;
    },
  });
}

export function useAnalyticsSummary() {
  return useQuery({ queryKey: qk.analyticsSummary, queryFn: api.analyticsSummary });
}

export function useAnalyticsCoverage() {
  return useQuery({ queryKey: qk.analyticsCoverage, queryFn: api.analyticsCoverage });
}

export function usePipelineHealth() {
  return useQuery({
    queryKey: qk.pipelineHealth,
    queryFn: api.pipelineHealth,
    staleTime: 15_000,
    refetchInterval: 60_000,
    retry: 0,
  });
}

export function usePipelineRuns(limit = 20) {
  return useQuery({ queryKey: qk.pipelineRuns(limit), queryFn: () => api.pipelineRuns(limit) });
}

export function usePipelineStatus() {
  return useQuery({
    queryKey: qk.pipelineStatus,
    queryFn: api.pipelineStatus,
    staleTime: 15_000,
    refetchInterval: 60_000,
    retry: 0,
  });
}

export function useReviewQueue(p: ReviewListParams) {
  return useQuery({
    queryKey: qk.reviewQueue(p),
    queryFn: () => api.reviewQueue(p),
    placeholderData: keepPreviousData,
  });
}

export function useReviewItem(id: number | undefined) {
  return useQuery({
    queryKey: qk.reviewItem(id ?? -1),
    queryFn: () => api.reviewItem(id as number),
    enabled: Boolean(id),
  });
}

export function useReviewActions(id: number | undefined) {
  return useQuery({
    queryKey: qk.reviewActions(id ?? -1),
    queryFn: () => api.reviewActions(id as number),
    enabled: Boolean(id),
  });
}

/** Review-queue write actions. All invalidate the queue + the affected item +
 *  company/analytics caches (a merge/approve changes company resolution). */
export function useReviewMutations() {
  const qc = useQueryClient();
  const invalidate = (id?: number) => {
    qc.invalidateQueries({ queryKey: ["review-queue"] });
    if (id !== undefined) qc.invalidateQueries({ queryKey: qk.reviewItem(id) });
    qc.invalidateQueries({ queryKey: ["companies"] });
    qc.invalidateQueries({ queryKey: ["analytics"] });
  };

  const approve = useMutation({
    mutationFn: (v: { id: number; actor?: string }) => api.approve(v.id, v.actor),
    onSuccess: (_d, v) => invalidate(v.id),
  });
  const merge = useMutation({
    mutationFn: (v: { id: number; target: string; actor?: string }) =>
      api.merge(v.id, v.target, v.actor),
    onSuccess: (_d, v) => invalidate(v.id),
  });
  const reject = useMutation({
    mutationFn: (v: { id: number; reason?: string; actor?: string }) =>
      api.reject(v.id, v.reason, v.actor),
    onSuccess: (_d, v) => invalidate(v.id),
  });
  const alias = useMutation({
    mutationFn: (v: { id: number; name: string; domain: string; actor?: string }) =>
      api.createAlias(v.id, v.name, v.domain, v.actor),
    onSuccess: (_d, v) => invalidate(v.id),
  });

  return { approve, merge, reject, alias };
}


// ----------------------------------------------------------------- Phase 2: CRM
export function useAdminUsers(
  p: { status?: string; q?: string; limit?: number; offset?: number } = {}, enabled = true,
) {
  return useQuery({
    queryKey: [...qk.adminUsers, p],
    queryFn: () => api.adminUsers(p),
    enabled,
    retry: 0,
    placeholderData: keepPreviousData,
  });
}

export function useAssignments(p: { user_id?: number; status?: string } = {}, enabled = true) {
  return useQuery({
    queryKey: qk.assignments(p),
    queryFn: () => api.assignments(p),
    enabled,
    placeholderData: keepPreviousData,
  });
}

export function useMyAssignments() {
  return useQuery({ queryKey: qk.myAssignments, queryFn: api.myAssignments });
}

export function useAssignableUsers(enabled = true) {
  return useQuery({ queryKey: qk.assignableUsers, queryFn: api.assignableUsers, enabled, retry: 0 });
}

export function useWorkload(enabled = true) {
  return useQuery({ queryKey: qk.workload, queryFn: api.workload, enabled });
}

export function useCompanyNotes(domain: string | undefined) {
  return useQuery({
    queryKey: qk.companyNotes(domain ?? ""),
    queryFn: () => api.companyNotes(domain as string),
    enabled: Boolean(domain),
  });
}

export function useCompanyActivity(domain: string | undefined) {
  return useQuery({
    queryKey: qk.companyActivity(domain ?? ""),
    queryFn: () => api.companyActivity(domain as string),
    enabled: Boolean(domain),
  });
}

/** CRM write actions (assign / update status / unassign / user role) + cache invalidation. */
export function useCrmMutations() {
  const qc = useQueryClient();
  const invalidateAssignments = () => qc.invalidateQueries({ queryKey: ["assignments"] });

  const createAssignment = useMutation({ mutationFn: api.createAssignment, onSuccess: invalidateAssignments });
  const updateAssignment = useMutation({
    mutationFn: (v: { id: number; patch: AssignmentPatch }) => api.updateAssignment(v.id, v.patch),
    onSuccess: invalidateAssignments,
  });
  const unassign = useMutation({ mutationFn: (id: number) => api.unassign(id), onSuccess: invalidateAssignments });
  const invalidateUsers = () => {
    qc.invalidateQueries({ queryKey: qk.adminUsers });
    qc.invalidateQueries({ queryKey: qk.userAudit });
  };
  const updateUser = useMutation({
    mutationFn: (v: { id: number; patch: UserPatch }) => api.updateUser(v.id, v.patch),
    onSuccess: invalidateUsers,
  });
  const approveUser = useMutation({ mutationFn: (id: number) => api.approveUser(id), onSuccess: invalidateUsers });
  const rejectUser = useMutation({ mutationFn: (id: number) => api.rejectUser(id), onSuccess: invalidateUsers });
  const deleteUser = useMutation({ mutationFn: (id: number) => api.deleteUser(id), onSuccess: invalidateUsers });
  return { createAssignment, updateAssignment, unassign, updateUser, approveUser, rejectUser, deleteUser };
}

export function useUserAudit(limit = 100, enabled = true) {
  return useQuery({ queryKey: [...qk.userAudit, limit], queryFn: () => api.userAudit(limit), enabled, retry: 0 });
}

export function useAddCompanyNote(domain: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => api.addCompanyNote(domain, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.companyNotes(domain) });
      qc.invalidateQueries({ queryKey: qk.companyActivity(domain) });
    },
  });
}

/** Full enrichment for one decision maker — lazy-loaded only when the panel opens. */
export function useDmDetail(id: number | undefined, enabled = true) {
  return useQuery({
    queryKey: qk.dmDetail(id ?? -1),
    queryFn: () => api.dmDetail(id as number),
    enabled: enabled && Boolean(id),
  });
}

/** Decision-intelligence contacts for a company (ranked + map + hierarchy), lazy. */
export function useCompanyContacts(domain: string | undefined, enabled = true) {
  return useQuery({
    queryKey: qk.companyContacts(domain ?? ""),
    queryFn: () => api.companyContacts(domain as string),
    enabled: enabled && Boolean(domain),
  });
}

/** Company intelligence bundle (committee/coverage/engagement/heatmap/…), lazy. */
export function useCompanyIntelligence(domain: string | undefined, enabled = true) {
  return useQuery({
    queryKey: qk.companyIntelligence(domain ?? ""),
    queryFn: () => api.companyIntelligence(domain as string),
    enabled: enabled && Boolean(domain),
  });
}

/** Relationship intelligence bundle (next-best-contacts/actions, alerts, graph), lazy. */
export function useCompanyRelationships(domain: string | undefined, enabled = true) {
  return useQuery({
    queryKey: qk.companyRelationships(domain ?? ""),
    queryFn: () => api.companyRelationships(domain as string),
    enabled: enabled && Boolean(domain),
  });
}

/** Cross-company smart alerts for the Dashboard. */
export function useAlerts(limit = 25) {
  return useQuery({ queryKey: qk.alerts(limit), queryFn: () => api.alerts(limit) });
}

export function useDmContact(id: number | undefined, enabled = true) {
  return useQuery({
    queryKey: qk.dmContact(id ?? -1),
    queryFn: () => api.dmContact(id as number),
    enabled: enabled && Boolean(id),
  });
}

export function usePutDmContact(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ContactIn) => api.putDmContact(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.dmContact(id) }),
  });
}

// ---------------------------------------- decision-maker notes (team / personal)
export function useDmNotes(id: number | undefined, enabled = true) {
  return useQuery({
    queryKey: qk.dmNotes(id ?? -1),
    queryFn: () => api.dmNotes(id as number),
    enabled: enabled && Boolean(id),
  });
}

export function useCreateDmNote(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DecisionMakerNoteIn) => api.createDmNote(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.dmNotes(id) }),
  });
}

export function useUpdateDmNote(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ noteId, content }: { noteId: number; content: string }) =>
      api.updateDmNote(id, noteId, { content }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.dmNotes(id) }),
  });
}

export function useDeleteDmNote(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (noteId: number) => api.deleteDmNote(id, noteId),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.dmNotes(id) }),
  });
}

// ----------------------------------------------------------- outreach module
type OutreachLeadParams = {
  stage?: string;
  mine?: boolean;
  open_only?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
};

export function useOutreachLeads(p: OutreachLeadParams = {}) {
  return useQuery({
    queryKey: qk.outreachLeads(p),
    queryFn: () => api.outreach.leads(p),
    placeholderData: keepPreviousData,
  });
}

export function useOutreachLead(id: number | undefined) {
  return useQuery({
    queryKey: qk.outreachLead(id ?? -1),
    queryFn: () => api.outreach.lead(id as number),
    enabled: Boolean(id),
  });
}

export function useOutreachActivities(id: number | undefined) {
  return useQuery({
    queryKey: qk.outreachActivities(id ?? -1),
    queryFn: () => api.outreach.activities(id as number),
    enabled: Boolean(id),
  });
}

export function useOutreachMessages(id: number | undefined) {
  return useQuery({
    queryKey: qk.outreachMessages(id ?? -1),
    queryFn: () => api.outreach.messages(id as number),
    enabled: Boolean(id),
  });
}

export function useOutreachTemplates(activeOnly = false) {
  return useQuery({
    queryKey: [...qk.outreachTemplates, activeOnly] as const,
    queryFn: () => api.outreach.templates(activeOnly),
  });
}

export function useOutreachApprovals() {
  return useQuery({ queryKey: qk.outreachApprovals, queryFn: api.outreach.approvals });
}

export function useOutreachInbox() {
  return useQuery({ queryKey: qk.outreachInbox, queryFn: api.outreach.inbox });
}

export function useOutreachAnalytics() {
  return useQuery({ queryKey: qk.outreachAnalytics, queryFn: api.outreach.analytics });
}

/** Invalidate everything outreach — the cheapest correct option after a mutation
 *  that can affect lead state, counts, the funnel and the inbox at once. */
function useInvalidateOutreach() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["outreach"] });
}

export function useSyncOutreach() {
  const invalidate = useInvalidateOutreach();
  return useMutation({ mutationFn: (limit?: number) => api.outreach.sync(limit), onSuccess: invalidate });
}

export function useCreateOutreachLead() {
  const invalidate = useInvalidateOutreach();
  return useMutation({
    mutationFn: (body: import("./types").OutreachLeadCreate) => api.outreach.createLead(body),
    onSuccess: invalidate,
  });
}

export function usePatchOutreachLead(id: number) {
  const invalidate = useInvalidateOutreach();
  return useMutation({
    mutationFn: (body: import("./types").OutreachLeadPatch) => api.outreach.patchLead(id, body),
    onSuccess: invalidate,
  });
}

export function useCreateOutreachMessage(leadId: number) {
  const invalidate = useInvalidateOutreach();
  return useMutation({
    mutationFn: (body: import("./types").OutreachMessageCreate) =>
      api.outreach.createMessage(leadId, body),
    onSuccess: invalidate,
  });
}

export function usePatchOutreachMessage() {
  const invalidate = useInvalidateOutreach();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: import("./types").OutreachMessagePatch }) =>
      api.outreach.patchMessage(id, body),
    onSuccess: invalidate,
  });
}

export function useAddOutreachNote(leadId: number) {
  const invalidate = useInvalidateOutreach();
  return useMutation({
    mutationFn: (text: string) => api.outreach.addNote(leadId, text),
    onSuccess: invalidate,
  });
}

/** Lifecycle actions on a message (submit / approve / send / reply). */
export function useOutreachMessageAction(action: "submit" | "approve" | "send" | "reply") {
  const invalidate = useInvalidateOutreach();
  const fn = {
    submit: api.outreach.submitMessage,
    approve: api.outreach.approveMessage,
    send: api.outreach.sendMessage,
    reply: api.outreach.replyMessage,
  }[action];
  return useMutation({ mutationFn: (id: number) => fn(id), onSuccess: invalidate });
}

export function useCreateOutreachTemplate() {
  const invalidate = useInvalidateOutreach();
  return useMutation({
    mutationFn: (body: import("./types").OutreachTemplateIn) => api.outreach.createTemplate(body),
    onSuccess: invalidate,
  });
}

export function useUpdateOutreachTemplate() {
  const invalidate = useInvalidateOutreach();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: import("./types").OutreachTemplateIn }) =>
      api.outreach.updateTemplate(id, body),
    onSuccess: invalidate,
  });
}

export function useDeleteOutreachTemplate() {
  const invalidate = useInvalidateOutreach();
  return useMutation({ mutationFn: (id: number) => api.outreach.deleteTemplate(id), onSuccess: invalidate });
}

// ----------------------------------------------------------- outreach CRM Foundation
export function useOutreachDashboard() {
  return useQuery({ queryKey: qk.outreachDashboard, queryFn: api.outreach.dashboard });
}

export function useOutreachFollowUps(limit = 30) {
  return useQuery({
    queryKey: qk.outreachFollowUps(limit),
    queryFn: () => api.outreach.followUps(limit),
  });
}

export function useOutreachTimeline(leadId: number | undefined, limit = 50) {
  return useQuery({
    queryKey: qk.outreachTimeline(leadId ?? -1),
    queryFn: () => api.outreach.timeline(leadId as number, limit),
    enabled: Boolean(leadId),
  });
}

export function useOutreachTasks(p: Parameters<typeof api.outreach.tasks>[0] = {}) {
  return useQuery({
    queryKey: qk.outreachTasks(p),
    queryFn: () => api.outreach.tasks(p),
    placeholderData: keepPreviousData,
  });
}

export function useCreateOutreachTask() {
  const invalidate = useInvalidateOutreach();
  return useMutation({
    mutationFn: (body: import("./types").OutreachTaskIn) => api.outreach.createTask(body),
    onSuccess: invalidate,
  });
}

export function usePatchOutreachTask() {
  const invalidate = useInvalidateOutreach();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: import("./types").OutreachTaskPatch }) =>
      api.outreach.patchTask(id, body),
    onSuccess: invalidate,
  });
}

export function useDeleteOutreachTask() {
  const invalidate = useInvalidateOutreach();
  return useMutation({ mutationFn: (id: number) => api.outreach.deleteTask(id), onSuccess: invalidate });
}

export function useOutreachMeetings(p: Parameters<typeof api.outreach.meetings>[0] = {}) {
  return useQuery({
    queryKey: qk.outreachMeetings(p),
    queryFn: () => api.outreach.meetings(p),
    placeholderData: keepPreviousData,
  });
}

export function useCreateOutreachMeeting() {
  const invalidate = useInvalidateOutreach();
  return useMutation({
    mutationFn: (body: import("./types").OutreachMeetingIn) => api.outreach.createMeeting(body),
    onSuccess: invalidate,
  });
}

export function usePatchOutreachMeeting() {
  const invalidate = useInvalidateOutreach();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: import("./types").OutreachMeetingPatch }) =>
      api.outreach.patchMeeting(id, body),
    onSuccess: invalidate,
  });
}

export function useDeleteOutreachMeeting() {
  const invalidate = useInvalidateOutreach();
  return useMutation({ mutationFn: (id: number) => api.outreach.deleteMeeting(id), onSuccess: invalidate });
}

export function useContactHistory(dmId: number | undefined) {
  return useQuery({
    queryKey: qk.outreachContactHistory(dmId ?? -1),
    queryFn: () => api.outreach.contactHistory(dmId as number),
    enabled: Boolean(dmId),
  });
}

// --------------------------------------------------- human lead review (P-task viii)
export function useReviewReports(enabled = true) {
  return useQuery({ queryKey: qk.reviewReports, queryFn: api.reviewReports, enabled });
}

/** Submit/update a human assessment. Invalidates the company profile (the panel +
 *  history live there), the leads table (the human-status column + combined sort),
 *  the reports, and analytics — the model score itself is never touched. */
export function useSetLeadReview(domain: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: LeadReviewIn) => api.putLeadReview(domain, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.companyProfile(domain) });
      qc.invalidateQueries({ queryKey: qk.companyActivity(domain) });
      qc.invalidateQueries({ queryKey: ["leads"] });
      qc.invalidateQueries({ queryKey: qk.reviewReports });
      qc.invalidateQueries({ queryKey: ["analytics"] });
    },
  });
}

// --------------------------------------- Enterprise CRM Phase 1: campaigns
export function useCampaigns(p: CampaignListParams = {}) {
  return useQuery({
    queryKey: qk.campaigns(p),
    queryFn: () => api.campaigns.list(p),
    placeholderData: keepPreviousData,
  });
}

export function useCampaign(id: number | undefined) {
  return useQuery({
    queryKey: qk.campaign(id ?? -1),
    queryFn: () => api.campaigns.get(id as number),
    enabled: Boolean(id),
  });
}

export function useCampaignDashboard() {
  return useQuery({ queryKey: qk.campaignDashboard, queryFn: api.campaigns.dashboard });
}

export function useCampaignAnalytics(id: number | undefined) {
  return useQuery({
    queryKey: qk.campaignAnalytics(id ?? -1),
    queryFn: () => api.campaigns.analytics(id as number),
    enabled: Boolean(id),
  });
}

export function useCampaignTimeline(id: number | undefined, limit = 50) {
  return useQuery({
    queryKey: qk.campaignTimeline(id ?? -1),
    queryFn: () => api.campaigns.timeline(id as number, { limit }),
    enabled: Boolean(id),
  });
}

export function useCampaignMembers(id: number | undefined, p: { limit?: number; offset?: number } = {}) {
  return useQuery({
    queryKey: qk.campaignMembers(id ?? -1, p),
    queryFn: () => api.campaigns.members(id as number, p),
    enabled: Boolean(id),
    placeholderData: keepPreviousData,
  });
}

/** Every campaign/sequence/enrollment view is cross-linked (a step edit changes an
 *  enrollment's step_count, an enrollment changes its campaign's member stats) —
 *  invalidate all three families together rather than tracking each edge. */
function useInvalidateCampaignData() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["campaigns"] });
    qc.invalidateQueries({ queryKey: ["sequences"] });
    qc.invalidateQueries({ queryKey: ["enrollments"] });
  };
}

export function useCampaignMutations() {
  const invalidate = useInvalidateCampaignData();
  const create = useMutation({
    mutationFn: (body: import("./types").CampaignCreate) => api.campaigns.create(body),
    onSuccess: invalidate,
  });
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: number; body: import("./types").CampaignPatch }) =>
      api.campaigns.patch(id, body),
    onSuccess: invalidate,
  });
  const archive = useMutation({
    mutationFn: (id: number) => api.campaigns.archive(id),
    onSuccess: invalidate,
  });
  return { create, patch, archive };
}

export function useCampaignMemberMutations(campaignId: number) {
  const invalidate = useInvalidateCampaignData();
  const addMember = useMutation({
    mutationFn: (body: import("./types").CampaignMemberIn) => api.campaigns.addMember(campaignId, body),
    onSuccess: invalidate,
  });
  const patchMember = useMutation({
    mutationFn: ({ memberId, body }: { memberId: number; body: import("./types").CampaignMemberPatch }) =>
      api.campaigns.patchMember(campaignId, memberId, body),
    onSuccess: invalidate,
  });
  const removeMember = useMutation({
    mutationFn: (memberId: number) => api.campaigns.removeMember(campaignId, memberId),
    onSuccess: invalidate,
  });
  const enrollMember = useMutation({
    mutationFn: ({ memberId, sequenceId }: { memberId: number; sequenceId: number }) =>
      api.campaigns.enrollMember(campaignId, memberId, sequenceId),
    onSuccess: invalidate,
  });
  return { addMember, patchMember, removeMember, enrollMember };
}

// --------------------------------------- Enterprise CRM Phase 1: sequences
export function useSequences(p: SequenceListParams = {}) {
  return useQuery({
    queryKey: qk.sequences(p),
    queryFn: () => api.sequences.list(p),
    placeholderData: keepPreviousData,
  });
}

export function useSequence(id: number | undefined) {
  return useQuery({
    queryKey: qk.sequence(id ?? -1),
    queryFn: () => api.sequences.get(id as number),
    enabled: Boolean(id),
  });
}

export function useSequenceMutations() {
  const invalidate = useInvalidateCampaignData();
  const create = useMutation({
    mutationFn: (body: import("./types").CrmSequenceCreate) => api.sequences.create(body),
    onSuccess: invalidate,
  });
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: number; body: import("./types").CrmSequencePatch }) =>
      api.sequences.patch(id, body),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.sequences.delete(id),
    onSuccess: invalidate,
  });
  const addStep = useMutation({
    mutationFn: ({ id, body }: { id: number; body: import("./types").CrmSequenceStepIn }) =>
      api.sequences.addStep(id, body),
    onSuccess: invalidate,
  });
  const patchStep = useMutation({
    mutationFn: ({ id, stepId, body }: { id: number; stepId: number; body: import("./types").CrmSequenceStepPatch }) =>
      api.sequences.patchStep(id, stepId, body),
    onSuccess: invalidate,
  });
  const deleteStep = useMutation({
    mutationFn: ({ id, stepId }: { id: number; stepId: number }) => api.sequences.deleteStep(id, stepId),
    onSuccess: invalidate,
  });
  return { create, patch, remove, addStep, patchStep, deleteStep };
}

// --------------------------------------- Enterprise CRM Phase 1: enrollments
export function useEnrollments(p: EnrollmentListParams = {}) {
  return useQuery({
    queryKey: qk.enrollments(p),
    queryFn: () => api.enrollments.list(p),
    placeholderData: keepPreviousData,
  });
}

export function useEnrollmentMutations() {
  const invalidate = useInvalidateCampaignData();
  const pause = useMutation({ mutationFn: (id: number) => api.enrollments.pause(id), onSuccess: invalidate });
  const resume = useMutation({ mutationFn: (id: number) => api.enrollments.resume(id), onSuccess: invalidate });
  const cancel = useMutation({ mutationFn: (id: number) => api.enrollments.cancel(id), onSuccess: invalidate });
  const advance = useMutation({ mutationFn: (id: number) => api.enrollments.advance(id), onSuccess: invalidate });
  const skipStep = useMutation({
    mutationFn: ({ id, stepId }: { id: number; stepId: number }) => api.enrollments.skipStep(id, stepId),
    onSuccess: invalidate,
  });
  return { pause, resume, cancel, advance, skipStep };
}

// ------------------------------------------------------- scheduler / run history
export function useSchedulerStatus() {
  return useQuery({
    queryKey: qk.schedulerStatus,
    queryFn: api.scheduler.status,
    // A run in progress flips fields (running/last_run) — poll modestly while mounted.
    refetchInterval: 15_000,
  });
}

export function useRunHistory(p: { page?: number; page_size?: number } = {}) {
  return useQuery({
    queryKey: qk.schedulerRuns(p),
    queryFn: () => api.scheduler.runs(p),
    placeholderData: keepPreviousData,
    refetchInterval: 15_000,
  });
}

export function useRunNow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.scheduler.runNow(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scheduler"] }),
  });
}

/** Drill-down: the records one engine touched during one run. Loaded on demand
 * (only when a stage row is expanded), paginated, strictly scoped to that run. */
export function useRunEngineRecords(
  runId: string, engine: string, page: number, enabled: boolean,
) {
  return useQuery({
    queryKey: qk.schedulerRunRecords(runId, engine, page),
    queryFn: () => api.scheduler.runEngineRecords(runId, engine, { page, page_size: 25 }),
    enabled,
    placeholderData: keepPreviousData,
  });
}

/** Update the Standard Run schedule (times / enabled / grace) — manager+. */
export function useUpdateSchedulerConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: import("./types").SchedulerConfigIn) => api.scheduler.updateConfig(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scheduler"] }),
  });
}

// ---------------------------------------------------------------- Historical Import (Phase 6)
import type {
  AuditEventDTO,
  BulkAction,
  FieldChoice,
  ImportJobDTO,
  ReviewDecision,
  ReviewResponseDTO,
  ReviewStatsDTO,
} from "./import-types";
import { IMPORT_TERMINAL_STATES } from "./import-types";

export function useImportJobs() {
  return useQuery({
    queryKey: qk.imports,
    queryFn: () => api.imports.list(),
    select: (d) => d.items,
    refetchInterval: 15_000,
  });
}

/** One import job; polls while running so live progress refreshes. */
export function useImportJob(id: string | undefined) {
  return useQuery({
    queryKey: qk.import(id ?? ""),
    queryFn: () => api.imports.get(id as string),
    enabled: Boolean(id),
    refetchInterval: (q) => {
      const s = (q.state.data as ImportJobDTO | undefined)?.status;
      return s && IMPORT_TERMINAL_STATES.includes(s) ? false : 2000;
    },
  });
}

export function useImportReview(id: string | undefined, filters: { category?: string; state?: string } = {}) {
  return useQuery({
    queryKey: qk.importReview(id ?? "", filters),
    queryFn: () => api.imports.review(id as string, filters),
    enabled: Boolean(id),
    placeholderData: keepPreviousData,
  });
}

export function useImportAudit(id: string | undefined) {
  return useQuery({
    queryKey: qk.importAudit(id ?? ""),
    queryFn: () => api.imports.audit(id as string),
    enabled: Boolean(id),
    select: (d) => d.events,
  });
}

/** Upload an Excel export (base64) → previewed ImportJob (admin). */
export function useUploadImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { filename: string; content_base64: string }) => api.imports.upload(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.imports }),
  });
}

/** All review + commit mutations for one import, refreshing only the affected queries. */
export function useImportActions(id: string) {
  const qc = useQueryClient();
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["imports", id] });
    qc.invalidateQueries({ queryKey: qk.imports });
  };
  const decide = useMutation({
    mutationFn: (b: { kind: string; source_ref: string; decision: ReviewDecision; reason?: string }) =>
      api.imports.decide(id, b),
    onSuccess: refresh,
  });
  const resolve = useMutation({
    mutationFn: (b: { kind: string; source_ref: string; field: string; choice: FieldChoice; reason?: string }) =>
      api.imports.resolve(id, b),
    onSuccess: refresh,
  });
  const bulk = useMutation({
    mutationFn: (b: { action: BulkAction; refs?: { kind: string; source_ref: string }[]; category?: string }) =>
      api.imports.bulk(id, b),
    onSuccess: refresh,
  });
  const commit = useMutation({
    mutationFn: (dryRun: boolean) => api.imports.commit(id, dryRun),
    onSuccess: refresh,
  });
  return { decide, resolve, bulk, commit };
}

export type { AuditEventDTO, ImportJobDTO, ReviewResponseDTO, ReviewStatsDTO };
