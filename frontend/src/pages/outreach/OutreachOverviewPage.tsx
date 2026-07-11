import { Link } from "react-router-dom";
import { AlertTriangle, Calendar, CheckSquare, Inbox, KanbanSquare, RefreshCw, Send, TrendingUp } from "lucide-react";

import { stageLabel } from "@/components/outreach/bits";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { SectionPanel } from "@/components/ui/SectionPanel";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import { useOutreachAnalytics, useOutreachDashboard, useSyncOutreach } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/store";
import { fmtInt, fmtPct, fmtRelative } from "@/lib/format";
import type { OutreachDashboardOut } from "@/lib/api/types";

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="panel p-3.5">
      <div className="text-11 uppercase tracking-wide text-fg-subtle">{label}</div>
      <div className="mt-1 text-22 font-semibold text-fg">{value}</div>
      {hint && <div className="text-11 text-fg-subtle">{hint}</div>}
    </div>
  );
}

function TasksDueWidget({ dashboard }: { dashboard: OutreachDashboardOut }) {
  const items = [...dashboard.tasks_due_today, ...dashboard.overdue_tasks.slice(0, 3)];
  const uniq = items.filter((t, i, a) => a.findIndex((x) => x.id === t.id) === i).slice(0, 5);
  return (
    <SectionPanel title={`Tasks · ${dashboard.open_tasks} open`}>
      {uniq.length === 0 ? (
        <p className="text-12 text-fg-subtle">No tasks due today.</p>
      ) : (
        <div className="space-y-1">
          {uniq.map((t) => (
            <div key={t.id} className="flex items-start gap-2 py-1">
              <CheckSquare size={13} className={t.is_overdue ? "mt-0.5 text-danger" : "mt-0.5 text-fg-subtle"} />
              <div className="min-w-0">
                <span className={`block truncate text-12 ${t.is_overdue ? "text-danger" : "text-fg"}`}>
                  {t.title}
                </span>
                {t.due_at && (
                  <span className="text-11 text-fg-subtle">
                    Due {new Date(t.due_at).toLocaleDateString()}
                    {t.company_name ? ` · ${t.company_name}` : ""}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      <Link to="/outreach/tasks" className="mt-2 block text-11 text-accent hover:underline">
        View all tasks →
      </Link>
    </SectionPanel>
  );
}

function FollowUpsWidget({ dashboard }: { dashboard: OutreachDashboardOut }) {
  const items = dashboard.upcoming_follow_ups.slice(0, 5);
  return (
    <SectionPanel title={`Follow-ups · ${dashboard.overdue_follow_ups > 0 ? `${dashboard.overdue_follow_ups} overdue` : "upcoming"}`}>
      {items.length === 0 ? (
        <p className="text-12 text-fg-subtle">No follow-ups scheduled.</p>
      ) : (
        <div className="space-y-1">
          {items.map((f) => (
            <div key={f.lead_id} className="flex items-start gap-2 py-1">
              <AlertTriangle
                size={13}
                className={`mt-0.5 ${f.is_overdue ? "text-danger" : "text-fg-subtle"}`}
              />
              <div className="min-w-0">
                <Link
                  to={`/outreach/leads/${f.lead_id}`}
                  className="block truncate text-12 text-fg hover:text-accent"
                >
                  {f.company_name}
                </Link>
                <span className="text-11 text-fg-subtle">
                  {f.is_overdue
                    ? `Overdue by ${Math.abs(f.days_until)} day${Math.abs(f.days_until) !== 1 ? "s" : ""}`
                    : f.days_until === 0
                    ? "Due today"
                    : `In ${f.days_until} day${f.days_until !== 1 ? "s" : ""}`}
                  {" · "}
                  {stageLabel(f.stage)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
      <Link to="/outreach/leads" className="mt-2 block text-11 text-accent hover:underline">
        View all leads →
      </Link>
    </SectionPanel>
  );
}

function UpcomingMeetingsWidget({ dashboard }: { dashboard: OutreachDashboardOut }) {
  const items = dashboard.upcoming_meetings.slice(0, 4);
  return (
    <SectionPanel title={`Meetings this week · ${dashboard.total_meetings_this_week}`}>
      {items.length === 0 ? (
        <p className="text-12 text-fg-subtle">No upcoming meetings.</p>
      ) : (
        <div className="space-y-1">
          {items.map((m) => (
            <div key={m.id} className="flex items-start gap-2 py-1">
              <Calendar size={13} className="mt-0.5 text-fg-subtle" />
              <div className="min-w-0">
                <span className="block truncate text-12 text-fg">
                  {m.title || m.meeting_type.replace("_", " ")}
                  {m.company_name ? ` · ${m.company_name}` : ""}
                </span>
                <span className="text-11 text-fg-subtle">
                  {new Date(m.scheduled_at).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}
                  {m.duration_minutes ? ` · ${m.duration_minutes}m` : ""}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </SectionPanel>
  );
}

function RecentActivityWidget({ dashboard }: { dashboard: OutreachDashboardOut }) {
  const items = dashboard.recent_activity.slice(0, 5);
  const TYPE_LABEL: Record<string, string> = {
    lead_created: "Lead created",
    stage_changed: "Stage changed",
    sent: "Email sent",
    reply_received: "Reply received",
    note_added: "Note added",
    task_completed: "Task completed",
    meeting_scheduled: "Meeting logged",
    meeting_completed: "Meeting completed",
  };
  return (
    <SectionPanel title="Recent activity">
      {items.length === 0 ? (
        <p className="text-12 text-fg-subtle">No recent activity.</p>
      ) : (
        <div className="space-y-1">
          {items.map((a) => (
            <div key={a.id} className="flex items-start gap-2 py-1">
              <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
              <div className="min-w-0">
                <span className="block truncate text-12 text-fg">
                  {TYPE_LABEL[a.type] ?? a.type.replace(/_/g, " ")}
                  {a.detail ? ` — ${a.detail}` : ""}
                </span>
                <span className="text-11 text-fg-subtle">{fmtRelative(a.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </SectionPanel>
  );
}

export function OutreachOverviewPage() {
  const { isManager } = useAuth();
  const { data, isLoading } = useOutreachAnalytics();
  const { data: dash } = useOutreachDashboard();
  const sync = useSyncOutreach();
  const max = Math.max(1, ...(data?.funnel ?? []).map((f) => f.count));

  return (
    <>
      <PageHeader title="Outreach" subtitle="Turn qualified Discovery leads into booked conversations">
        {isManager && (
          <Button variant="primary" size="sm" disabled={sync.isPending}
            onClick={() => sync.mutate(60, {
              onSuccess: (r) => toast(`Synced ${r.created} new lead(s) from Discovery`, "positive"),
              onError: () => toast("Sync failed", "danger"),
            })}>
            <RefreshCw size={13} className={sync.isPending ? "animate-spin" : ""} /> Sync from Discovery
          </Button>
        )}
      </PageHeader>

      {isLoading || !data ? (
        <div className="grid place-items-center py-12"><Spinner size={18} /></div>
      ) : (
        <div className="space-y-4 p-4">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi label="Open leads" value={fmtInt(data.open_leads)} hint={`${fmtInt(data.total_leads)} total`} />
            <Kpi label="Sent" value={fmtInt(data.sent)} hint={`${fmtInt(data.pending_approval)} awaiting approval`} />
            <Kpi label="Reply rate" value={fmtPct(data.reply_rate)} hint={`${fmtInt(data.replied)} replies`} />
            <Kpi label="Win rate" value={fmtPct(data.win_rate)} hint={`${fmtInt(data.won)} won · ${fmtInt(data.lost)} lost`} />
          </div>

          {/* Dashboard widgets */}
          {dash && (
            <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
              <TasksDueWidget dashboard={dash} />
              <FollowUpsWidget dashboard={dash} />
              <UpcomingMeetingsWidget dashboard={dash} />
              <RecentActivityWidget dashboard={dash} />
            </div>
          )}

          <div className="grid gap-4 lg:grid-cols-3">
            <div className="panel p-3.5 lg:col-span-2">
              <div className="mb-2 flex items-center gap-1.5 text-13 font-medium text-fg">
                <TrendingUp size={14} /> Pipeline funnel
              </div>
              <div className="space-y-1.5">
                {data.funnel.map((f) => (
                  <div key={f.stage} className="flex items-center gap-2">
                    <span className="w-32 shrink-0 text-12 text-fg-muted">{stageLabel(f.stage)}</span>
                    <div className="h-4 flex-1 rounded bg-control">
                      <div className="h-4 rounded bg-accent/70" style={{ width: `${(f.count / max) * 100}%` }} />
                    </div>
                    <span className="w-8 text-right text-12 text-fg">{f.count}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="panel p-3.5">
              <div className="mb-2 text-13 font-medium text-fg">Jump to</div>
              <div className="space-y-1.5">
                {[
                  { to: "/outreach/leads", icon: Send, label: "Leads" },
                  { to: "/outreach/pipeline", icon: KanbanSquare, label: "Pipeline board" },
                  { to: "/outreach/tasks", icon: CheckSquare, label: "Tasks" },
                  { to: "/outreach/approvals", icon: CheckSquare, label: `Approvals (${data.pending_approval})` },
                  { to: "/outreach/inbox", icon: Inbox, label: "Inbox" },
                ].map((x) => (
                  <Link key={x.to} to={x.to}
                    className="flex items-center gap-2 rounded-md border border-line bg-base px-2.5 py-2 text-12 text-fg hover:bg-raised">
                    <x.icon size={14} className="text-fg-subtle" /> {x.label}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
