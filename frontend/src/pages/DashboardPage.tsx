import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, Megaphone, UserCog } from "lucide-react";

import { GradeBadge } from "@/components/data/GradeBadge";
import { StatStrip, type Stat } from "@/components/data/StatStrip";
import { ageLabel, movementTone } from "@/components/profile/LeadershipSignalRow";
import { PipelineHealthStrip } from "@/components/system/PipelineHealthStrip";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { SectionPanel } from "@/components/ui/SectionPanel";
import { SkeletonLines } from "@/components/ui/Skeleton";
import { CHART, tooltipLabelStyle, tooltipStyle } from "@/lib/chartTheme";
import { useAlerts, useAnalyticsSummary, useLeadershipSignals, useOpportunities } from "@/lib/api/queries";
import { enumLabel, fmtInt, fmtRelative, fmtScore } from "@/lib/format";
import { gradeHex } from "@/lib/grades";

const ROW = "-mx-3.5 flex items-center gap-3 px-3.5 py-1.5 hover:bg-raised";

export function DashboardPage() {
  const summary = useAnalyticsSummary();
  // News feed only — leadership events are a first-class category shown separately
  // (the "Recent leadership signals" panel below + the Leadership page).
  const opps = useOpportunities({ page: 1, page_size: 6, signal_category: "NEWS" });
  const ldr = useLeadershipSignals({ page: 1, page_size: 6 });
  const alerts = useAlerts(10);

  const s = summary.data;
  const gd = s?.grade_distribution ?? {};
  const gradeData = ["A+", "A", "B", "C"].map((g) => ({ grade: g, count: gd[g] ?? 0 }));

  const stats: Stat[] = [
    { label: "Companies", value: fmtInt(s?.total_companies) },
    { label: "Leads", value: fmtInt(s?.total_leads) },
    {
      label: "A / B grades",
      value: `${fmtInt((gd["A+"] ?? 0) + (gd["A"] ?? 0))} / ${fmtInt(gd["B"] ?? 0)}`,
    },
    { label: "Opportunities", value: fmtInt(s?.total_opportunities) },
    { label: "Decision makers", value: fmtInt(s?.total_decision_makers) },
    { label: "Leadership moves", value: fmtInt(ldr.data?.total) },
  ];

  if (summary.isError) {
    return (
      <>
        <PageHeader title="Dashboard" subtitle="Platform-wide triage" />
        <div className="p-4">
          <ErrorState title="Couldn't load the dashboard" error={summary.error} onRetry={summary.refetch} />
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Platform-wide triage" />

      <div className="space-y-4 p-4">
        <StatStrip stats={stats} />

        <SectionPanel title="Smart alerts" icon={<Activity size={15} />}>
          {alerts.isLoading ? (
            <SkeletonLines rows={3} />
          ) : alerts.isError ? (
            <ErrorState title="Couldn't load alerts" error={alerts.error} onRetry={alerts.refetch} />
          ) : !alerts.data || alerts.data.length === 0 ? (
            <EmptyState title="No alerts right now" />
          ) : (
            <div className="divide-y divide-line/60">
              {alerts.data.slice(0, 8).map((a, i) => (
                <Link
                  key={i}
                  to={a.company_domain ? `/companies/${encodeURIComponent(a.company_domain)}` : "/decision-makers"}
                  className="-mx-3.5 flex items-center justify-between gap-3 px-3.5 py-2 hover:bg-raised"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-13 text-fg">{a.title}</span>
                    <span className="block truncate text-11 text-fg-subtle">
                      {a.company_name || a.company_domain}{a.detail ? ` · ${a.detail}` : ""}
                    </span>
                  </span>
                  <Badge tone={a.severity === "high" ? "danger" : a.severity === "medium" ? "warning" : "neutral"}>
                    {a.type.replace(/_/g, " ")}
                  </Badge>
                </Link>
              ))}
            </div>
          )}
        </SectionPanel>

        <div className="grid gap-4 lg:grid-cols-3">
          <SectionPanel title="Priority leads" className="lg:col-span-2">
            {summary.isLoading ? (
              <SkeletonLines rows={6} />
            ) : !s || s.top_companies.length === 0 ? (
              <EmptyState title="No scored leads yet" />
            ) : (
              <div className="divide-y divide-line/60">
                {s.top_companies.slice(0, 8).map((l, i) => (
                  <Link
                    key={l.company_domain}
                    to={`/companies/${encodeURIComponent(l.company_domain)}`}
                    className={ROW}
                  >
                    <span className="tabular w-5 text-right text-11 text-fg-subtle">{i + 1}</span>
                    <GradeBadge grade={l.grade} size="sm" />
                    <span className="min-w-0 flex-1 truncate text-13 text-fg">
                      {l.company_name || l.company_domain}
                    </span>
                    <span className="hidden text-11 text-fg-subtle sm:inline">
                      {enumLabel(l.company_tier)}
                    </span>
                    <span className="tabular w-10 text-right text-13 text-fg-muted">
                      {fmtScore(l.lead_score)}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </SectionPanel>

          <div className="space-y-4">
            <SectionPanel title="Grade distribution">
            {summary.isLoading ? (
              <SkeletonLines rows={5} />
            ) : (
              <div className="h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={gradeData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <CartesianGrid stroke={CHART.grid} vertical={false} />
                    <XAxis
                      dataKey="grade"
                      tick={{ fill: CHART.tick, fontSize: 11 }}
                      axisLine={{ stroke: CHART.axis }}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: CHART.tickFaint, fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                      allowDecimals={false}
                      width={30}
                    />
                    <Tooltip
                      cursor={{ fill: "rgba(255,255,255,0.04)" }}
                      contentStyle={tooltipStyle}
                      labelStyle={tooltipLabelStyle}
                    />
                    <Bar dataKey="count" radius={[3, 3, 0, 0]} maxBarSize={56}>
                      {gradeData.map((d) => (
                        <Cell key={d.grade} fill={gradeHex(d.grade)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </SectionPanel>
            <SectionPanel title="Pipeline health" icon={<Activity size={15} />}>
              <PipelineHealthStrip />
            </SectionPanel>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <SectionPanel title="Latest opportunities" icon={<Megaphone size={15} />}>
            {opps.isLoading ? (
              <SkeletonLines rows={4} />
            ) : opps.isError ? (
              <ErrorState title="Couldn't load opportunities" error={opps.error} onRetry={opps.refetch} />
            ) : !opps.data || opps.data.items.length === 0 ? (
              <EmptyState title="No opportunities yet" />
            ) : (
              <div className="divide-y divide-line/60">
                {opps.data.items.map((o) => (
                  <Link
                    key={o.opportunity_id}
                    to={`/companies/${encodeURIComponent(o.company_domain)}`}
                    className="-mx-3.5 block px-3.5 py-2 hover:bg-raised"
                  >
                    <div className="flex items-center gap-2">
                      {o.opportunity_type && <Badge tone="accent">{enumLabel(o.opportunity_type)}</Badge>}
                      <span className="text-11 text-fg-subtle">{fmtRelative(o.published_date)}</span>
                    </div>
                    <div className="mt-0.5 truncate text-13 text-fg">
                      {o.article_title || o.company_name || o.company_domain}
                    </div>
                    <div className="truncate text-11 text-fg-subtle">
                      {o.company_name || o.company_domain}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </SectionPanel>

          <SectionPanel title="Recent leadership signals" icon={<UserCog size={15} />}>
            {ldr.isLoading ? (
              <SkeletonLines rows={4} />
            ) : ldr.isError ? (
              <ErrorState title="Couldn't load leadership signals" error={ldr.error} onRetry={ldr.refetch} />
            ) : !ldr.data || ldr.data.items.length === 0 ? (
              <EmptyState title="No leadership signals yet" />
            ) : (
              <div className="divide-y divide-line/60">
                {ldr.data.items.map((x) => (
                  <Link
                    key={x.signal_id}
                    to={x.company_domain ? `/companies/${encodeURIComponent(x.company_domain)}` : "/decision-makers"}
                    className="-mx-3.5 block px-3.5 py-2 hover:bg-raised"
                  >
                    <div className="flex items-center gap-2">
                      <Badge tone={movementTone(x.movement_type)}>{enumLabel(x.movement_type)}</Badge>
                      <span className="text-11 text-fg-subtle">{ageLabel(x.event_age_days)}</span>
                    </div>
                    <div className="mt-0.5 truncate text-13 text-fg">
                      {x.person_name}
                      {x.to_title && <span className="text-fg-muted"> — {x.to_title}</span>}
                    </div>
                    <div className="truncate text-11 text-fg-subtle">{x.company_name || x.company_domain}</div>
                  </Link>
                ))}
              </div>
            )}
          </SectionPanel>
        </div>
      </div>
    </>
  );
}
