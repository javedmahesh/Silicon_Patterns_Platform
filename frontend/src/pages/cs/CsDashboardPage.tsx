import { fmtMoney } from "@/components/cs/bits";
import { StatStrip, type Stat } from "@/components/data/StatStrip";
import { PageHeader } from "@/components/shell/PageHeader";
import { ErrorState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { useCsAnalytics, useCsDashboard } from "@/lib/api/queries";
import { enumLabel, fmtInt, fmtPct } from "@/lib/format";

export function CsDashboardPage() {
  const dashboard = useCsDashboard();
  const analytics = useCsAnalytics();

  const stats: Stat[] = dashboard.data
    ? [
        { label: "Total accounts", value: fmtInt(dashboard.data.total_accounts) },
        { label: "Active", value: fmtInt(dashboard.data.active_accounts) },
        { label: "At risk", value: fmtInt(dashboard.data.at_risk_accounts) },
        { label: "Churned", value: fmtInt(dashboard.data.churned_accounts) },
        { label: "Total ARR", value: fmtMoney(dashboard.data.total_arr) },
        { label: "Total MRR", value: fmtMoney(dashboard.data.total_mrr) },
      ]
    : [];

  const stats2: Stat[] = dashboard.data
    ? [
        { label: "Avg health score", value: dashboard.data.avg_health_score != null ? dashboard.data.avg_health_score.toFixed(1) : "—" },
        { label: "Renewals due (90d)", value: fmtInt(dashboard.data.renewals_due_90d) },
        { label: "Open risks", value: fmtInt(dashboard.data.open_risks) },
        { label: "Expansion accounts", value: fmtInt(dashboard.data.expansion_accounts) },
        { label: "Open tasks", value: fmtInt(dashboard.data.open_tasks) },
        { label: "Upcoming meetings", value: fmtInt(dashboard.data.upcoming_meetings) },
      ]
    : [];

  return (
    <>
      <PageHeader title="Customer Success" subtitle="Health, renewals, and account overview" />

      <div className="space-y-4 p-4">
        {dashboard.isError ? (
          <ErrorState title="Couldn't load the dashboard" error={dashboard.error} onRetry={dashboard.refetch} />
        ) : dashboard.isLoading ? (
          <div className="grid place-items-center py-8"><Spinner size={18} /></div>
        ) : (
          <>
            <StatStrip stats={stats} />
            <StatStrip stats={stats2} />
          </>
        )}

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="panel p-3.5">
            <div className="mb-2 text-13 font-medium text-fg">Retention</div>
            {analytics.isLoading ? (
              <div className="grid place-items-center py-6"><Spinner size={16} /></div>
            ) : analytics.isError ? (
              <ErrorState title="Couldn't load analytics" error={analytics.error} onRetry={analytics.refetch} />
            ) : analytics.data ? (
              <div className="space-y-1.5 text-12">
                <div className="flex justify-between"><span className="text-fg-subtle">Renewal rate</span><span className="tabular text-fg">{fmtPct(analytics.data.renewal_rate)}</span></div>
                <div className="flex justify-between"><span className="text-fg-subtle">Churn rate</span><span className="tabular text-fg">{fmtPct(analytics.data.churn_rate)}</span></div>
                <div className="flex justify-between"><span className="text-fg-subtle">Churned accounts</span><span className="tabular text-fg">{fmtInt(analytics.data.churn_count)}</span></div>
                <div className="flex justify-between"><span className="text-fg-subtle">Expansion accounts</span><span className="tabular text-fg">{fmtInt(analytics.data.expansion_account_count)}</span></div>
              </div>
            ) : null}
          </div>

          <div className="panel p-3.5">
            <div className="mb-2 text-13 font-medium text-fg">Health distribution</div>
            {analytics.data && Object.keys(analytics.data.health_distribution).length > 0 ? (
              <div className="space-y-1.5 text-12">
                {Object.entries(analytics.data.health_distribution).map(([grade, count]) => (
                  <div key={grade} className="flex items-center gap-2">
                    <span className="w-4 text-fg">{grade}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-control">
                      <div
                        className="h-full rounded-full bg-accent"
                        style={{ width: `${Math.min(100, (count / Math.max(1, analytics.data.active_count)) * 100)}%` }}
                      />
                    </div>
                    <span className="tabular w-6 text-right text-fg-muted">{count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-12 text-fg-subtle">No health scores recorded yet.</p>
            )}
          </div>
        </div>

        {analytics.data && Object.keys(analytics.data.by_status).length > 0 && (
          <div className="panel p-3.5">
            <div className="mb-2 text-13 font-medium text-fg">Accounts by status</div>
            <div className="flex flex-wrap gap-3 text-12">
              {Object.entries(analytics.data.by_status).map(([status, count]) => (
                <span key={status} className="rounded-md border border-line bg-control px-2.5 py-1">
                  {enumLabel(status)} <span className="tabular text-fg-subtle">{count}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
