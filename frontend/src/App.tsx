import { lazy, Suspense, useEffect } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { AppShell } from "@/components/shell/AppShell";
import { Spinner } from "@/components/ui/Spinner";
import { api } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/store";
import { LoginPage } from "@/pages/LoginPage";

// Route-level code-splitting: each page (and its heavy deps, e.g. Recharts) loads
// only when visited, keeping the initial bundle small. Pages use named exports, so
// each import is mapped to a default for React.lazy.
const DashboardPage = lazy(() => import("@/pages/DashboardPage").then((m) => ({ default: m.DashboardPage })));
const LeadsPage = lazy(() => import("@/pages/LeadsPage").then((m) => ({ default: m.LeadsPage })));
const CompaniesPage = lazy(() => import("@/pages/CompaniesPage").then((m) => ({ default: m.CompaniesPage })));
const CompanyProfilePage = lazy(() => import("@/pages/CompanyProfilePage").then((m) => ({ default: m.CompanyProfilePage })));
const WorkspacePage = lazy(() => import("@/pages/WorkspacePage").then((m) => ({ default: m.WorkspacePage })));
const OpportunitiesPage = lazy(() => import("@/pages/OpportunitiesPage").then((m) => ({ default: m.OpportunitiesPage })));
const LeadershipPage = lazy(() => import("@/pages/LeadershipPage").then((m) => ({ default: m.LeadershipPage })));
const DecisionMakersPage = lazy(() => import("@/pages/DecisionMakersPage").then((m) => ({ default: m.DecisionMakersPage })));
const AnalyticsPage = lazy(() => import("@/pages/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage })));
const ReviewQueuePage = lazy(() => import("@/pages/ReviewQueuePage").then((m) => ({ default: m.ReviewQueuePage })));
const ComparePage = lazy(() => import("@/pages/ComparePage").then((m) => ({ default: m.ComparePage })));
const MyLeadsPage = lazy(() => import("@/pages/MyLeadsPage").then((m) => ({ default: m.MyLeadsPage })));
const TeamPage = lazy(() => import("@/pages/TeamPage").then((m) => ({ default: m.TeamPage })));
const AdministrationPage = lazy(() =>
  import("@/pages/AdministrationPage").then((m) => ({ default: m.AdministrationPage })),
);
// Historical Import (Phase 6) — upload / preview / review / commit / history.
const HistoricalImportPage = lazy(() =>
  import("@/pages/import/HistoricalImportPage").then((m) => ({ default: m.HistoricalImportPage })),
);
const ImportDetailPage = lazy(() =>
  import("@/pages/import/ImportDetailPage").then((m) => ({ default: m.ImportDetailPage })),
);
// Enterprise CRM Phase 1 — campaigns / sequences / enrollments
const CampaignListPage = lazy(() => import("@/pages/campaigns/CampaignListPage").then((m) => ({ default: m.CampaignListPage })));
const CampaignDetailPage = lazy(() => import("@/pages/campaigns/CampaignDetailPage").then((m) => ({ default: m.CampaignDetailPage })));
const SequenceListPage = lazy(() => import("@/pages/campaigns/SequenceListPage").then((m) => ({ default: m.SequenceListPage })));
const SequenceDetailPage = lazy(() => import("@/pages/campaigns/SequenceDetailPage").then((m) => ({ default: m.SequenceDetailPage })));
const EnrollmentListPage = lazy(() => import("@/pages/campaigns/EnrollmentListPage").then((m) => ({ default: m.EnrollmentListPage })));
// Standard Scheduled Runs — scheduler status + run history
const RunHistoryPage = lazy(() => import("@/pages/scheduler/RunHistoryPage").then((m) => ({ default: m.RunHistoryPage })));
// Outreach is a native module (no iframe): each page is a first-class route.
const OutreachOverviewPage = lazy(() => import("@/pages/outreach/OutreachOverviewPage").then((m) => ({ default: m.OutreachOverviewPage })));
const OutreachLeadsPage = lazy(() => import("@/pages/outreach/OutreachLeadsPage").then((m) => ({ default: m.OutreachLeadsPage })));
const OutreachLeadDetailPage = lazy(() => import("@/pages/outreach/OutreachLeadDetailPage").then((m) => ({ default: m.OutreachLeadDetailPage })));
const OutreachPipelinePage = lazy(() => import("@/pages/outreach/OutreachPipelinePage").then((m) => ({ default: m.OutreachPipelinePage })));
const OutreachTemplatesPage = lazy(() => import("@/pages/outreach/OutreachTemplatesPage").then((m) => ({ default: m.OutreachTemplatesPage })));
const OutreachApprovalsPage = lazy(() => import("@/pages/outreach/OutreachApprovalsPage").then((m) => ({ default: m.OutreachApprovalsPage })));
const OutreachInboxPage = lazy(() => import("@/pages/outreach/OutreachInboxPage").then((m) => ({ default: m.OutreachInboxPage })));
const OutreachTasksPage = lazy(() => import("@/pages/outreach/OutreachTasksPage").then((m) => ({ default: m.OutreachTasksPage })));

function PageFallback() {
  return (
    <div className="grid h-full place-items-center">
      <Spinner size={20} />
    </div>
  );
}

/** Gate every app route behind a signed-in session; the chrome lives here too. */
function ProtectedLayout() {
  const { isAuthed, user, setUser } = useAuth();
  // Populate the current user (also resolves the synthetic dev-bypass admin).
  const me = useQuery({ queryKey: ["auth", "me"], queryFn: api.auth.me, enabled: isAuthed && !user, retry: 0 });
  useEffect(() => {
    if (me.data) setUser(me.data);
  }, [me.data, setUser]);
  if (!isAuthed) return <Navigate to="/login" replace />;
  return (
    <AppShell>
      <Suspense fallback={<PageFallback />}>
        <Outlet />
      </Suspense>
    </AppShell>
  );
}

/** Manager+ route guard (members are bounced to the dashboard). */
function RequireManager() {
  const { isManager } = useAuth();
  if (!isManager) return <Navigate to="/" replace />;
  return <Outlet />;
}

/** Admin+ route guard — gates Administration (employees/managers are bounced
 *  to the dashboard; the backend independently enforces the same tier). */
function RequireAdmin() {
  const { isAdmin } = useAuth();
  if (!isAdmin) return <Navigate to="/" replace />;
  return <Outlet />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/leads" element={<LeadsPage />} />
        <Route path="/workspace" element={<WorkspacePage />} />
        <Route path="/companies" element={<CompaniesPage />} />
        <Route path="/companies/:domain" element={<CompanyProfilePage />} />
        <Route path="/opportunities" element={<OpportunitiesPage />} />
        {/* Leadership hub — person-level leadership signals + leadership market events. */}
        <Route path="/leadership" element={<LeadershipPage />} />
        <Route path="/decision-makers" element={<DecisionMakersPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/review-queue" element={<ReviewQueuePage />} />
        <Route path="/scheduler" element={<RunHistoryPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/my-leads" element={<MyLeadsPage />} />
        <Route path="/campaigns" element={<CampaignListPage />} />
        <Route path="/campaigns/sequences" element={<SequenceListPage />} />
        <Route path="/campaigns/sequences/:id" element={<SequenceDetailPage />} />
        <Route path="/campaigns/enrollments" element={<EnrollmentListPage />} />
        <Route path="/campaigns/:id" element={<CampaignDetailPage />} />
        <Route path="/outreach" element={<OutreachOverviewPage />} />
        <Route path="/outreach/leads" element={<OutreachLeadsPage />} />
        <Route path="/outreach/leads/:id" element={<OutreachLeadDetailPage />} />
        <Route path="/outreach/pipeline" element={<OutreachPipelinePage />} />
        <Route path="/outreach/templates" element={<OutreachTemplatesPage />} />
        <Route path="/outreach/approvals" element={<OutreachApprovalsPage />} />
        <Route path="/outreach/inbox" element={<OutreachInboxPage />} />
        <Route path="/outreach/tasks" element={<OutreachTasksPage />} />
        <Route element={<RequireManager />}>
          <Route path="/team" element={<TeamPage />} />
          {/* Managers review; upload & commit are admin-gated inside the page + backend. */}
          <Route path="/historical-import" element={<HistoricalImportPage />} />
          <Route path="/historical-import/:importId" element={<ImportDetailPage />} />
        </Route>
        <Route element={<RequireAdmin />}>
          <Route path="/administration" element={<AdministrationPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
