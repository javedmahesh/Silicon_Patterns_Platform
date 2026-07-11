import { Link, useNavigate } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ReviewInsights } from "@/components/analytics/ReviewInsights";
import { DistributionBar } from "@/components/data/DistributionBar";
import { GradeBadge } from "@/components/data/GradeBadge";
import { PageHeader } from "@/components/shell/PageHeader";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { SectionPanel } from "@/components/ui/SectionPanel";
import { SkeletonLines } from "@/components/ui/Skeleton";
import { CHART, tooltipLabelStyle, tooltipStyle } from "@/lib/chartTheme";
import { useAnalyticsCoverage, useAnalyticsSummary } from "@/lib/api/queries";
import { enumLabel, fmtScore } from "@/lib/format";
import { gradeHex } from "@/lib/grades";

export function AnalyticsPage() {
  const summary = useAnalyticsSummary();
  const coverage = useAnalyticsCoverage();
  const cov = coverage.data;
  const navigate = useNavigate();

  if (summary.isError) {
    return (
      <>
        <PageHeader title="Analytics" subtitle="Platform-wide rollups" />
        <div className="p-4">
          <ErrorState title="Couldn't load analytics" error={summary.error} onRetry={summary.refetch} />
        </div>
      </>
    );
  }

  const s = summary.data;
  const gd = s?.grade_distribution ?? {};
  const gradeData = ["A+", "A", "B", "C"].map((g) => ({ grade: g, count: gd[g] ?? 0 }));
  const qualified = (gd["A+"] ?? 0) + (gd["A"] ?? 0) + (gd["B"] ?? 0);

  const funnelData = [
    { name: "Companies", value: s?.total_companies ?? 0 },
    { name: "Scored", value: s?.total_leads ?? 0 },
    { name: "Qualified A–B", value: qualified },
  ];
  const coverageData = [
    { name: "Opportunities", value: s?.total_opportunities ?? 0 },
    { name: "Eng. jobs", value: s?.total_jobs ?? 0 },
    { name: "Demand", value: s?.total_demand_signals ?? 0 },
    { name: "Decision makers", value: s?.total_decision_makers ?? 0 },
  ];

  return (
    <>
      <PageHeader title="Analytics" subtitle="Platform-wide rollups" />

      <div className="space-y-4 p-4">
        <div className="grid gap-4">
          <SectionPanel title="Grade distribution">
            {summary.isLoading ? (
              <SkeletonLines rows={5} />
            ) : (
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={gradeData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <CartesianGrid stroke={CHART.grid} vertical={false} />
                    <XAxis dataKey="grade" tick={{ fill: CHART.tick, fontSize: 11 }} axisLine={{ stroke: CHART.axis }} tickLine={false} />
                    <YAxis tick={{ fill: CHART.tickFaint, fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} width={30} />
                    <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} />
                    <Bar
                      dataKey="count"
                      radius={[3, 3, 0, 0]}
                      maxBarSize={64}
                      className="cursor-pointer"
                      onClick={(e: any) => {
                        const g = e?.grade ?? e?.payload?.grade;
                        if (g) navigate(`/leads?grade=${encodeURIComponent(g)}`);
                      }}
                    >
                      {gradeData.map((d) => (
                        <Cell key={d.grade} fill={gradeHex(d.grade)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            <p className="mt-2 text-11 text-fg-subtle">Click a bar to view those leads.</p>
          </SectionPanel>

          <SectionPanel title="Pipeline funnel">
            {summary.isLoading ? (
              <SkeletonLines rows={5} />
            ) : (
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart layout="vertical" data={funnelData} margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
                    <CartesianGrid stroke={CHART.grid} horizontal={false} />
                    <XAxis type="number" tick={{ fill: CHART.tickFaint, fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <YAxis type="category" dataKey="name" tick={{ fill: CHART.tick, fontSize: 11 }} axisLine={false} tickLine={false} width={104} />
                    <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} />
                    <Bar dataKey="value" fill={CHART.accent} radius={[0, 3, 3, 0]} maxBarSize={28} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </SectionPanel>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <SectionPanel title="Signal volume">
            {summary.isLoading ? (
              <SkeletonLines rows={5} />
            ) : (
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart layout="vertical" data={coverageData} margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
                    <CartesianGrid stroke={CHART.grid} horizontal={false} />
                    <XAxis type="number" tick={{ fill: CHART.tickFaint, fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <YAxis type="category" dataKey="name" tick={{ fill: CHART.tick, fontSize: 11 }} axisLine={false} tickLine={false} width={104} />
                    <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} />
                    <Bar dataKey="value" fill={CHART.accent} radius={[0, 3, 3, 0]} maxBarSize={24} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </SectionPanel>

        </div>

        <SectionPanel title="Company coverage">
          {coverage.isLoading ? (
            <SkeletonLines rows={4} />
          ) : !cov ? (
            <EmptyState title="No coverage data" />
          ) : (
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="space-y-2">
                <div className="text-11 uppercase tracking-wide text-fg-subtle">
                  Companies carrying each signal
                </div>
                {[
                  { label: "Opportunities", n: cov.with_opportunities },
                  { label: "Hiring demand", n: cov.with_demand },
                  { label: "Decision makers", n: cov.with_decision_makers },
                  { label: "Lead score", n: cov.with_lead_score },
                ].map((b) => (
                  <div key={b.label} className="grid grid-cols-[120px_1fr_auto] items-center gap-3">
                    <span className="truncate text-12 text-fg-muted">{b.label}</span>
                    <div className="h-1.5 overflow-hidden rounded-sm bg-control">
                      <div
                        className="h-full rounded-sm bg-accent"
                        style={{ width: `${(b.n / (cov.total_companies || 1)) * 100}%` }}
                      />
                    </div>
                    <span className="tabular w-14 text-right text-12 text-fg-muted">
                      {b.n}/{cov.total_companies}
                    </span>
                  </div>
                ))}
              </div>
              <div className="space-y-2">
                <div className="text-11 uppercase tracking-wide text-fg-subtle">Signals per company</div>
                <DistributionBar
                  showLegend
                  segments={[
                    { label: "0", value: cov.signal_distribution["0"] ?? 0, color: "var(--color-fg-subtle)" },
                    { label: "1", value: cov.signal_distribution["1"] ?? 0, color: "var(--color-warning)" },
                    { label: "2", value: cov.signal_distribution["2"] ?? 0, color: "var(--color-accent)" },
                    { label: "3", value: cov.signal_distribution["3"] ?? 0, color: "var(--color-positive)" },
                  ]}
                />
                <p className="text-12 leading-5 text-fg-muted">
                  <span className="tabular text-fg">{cov.with_all_three}</span> of{" "}
                  <span className="tabular text-fg">{cov.total_companies}</span> companies have all three
                  enrichment signals (opportunity + demand + decision-makers). Converging the engines on one
                  universe raises this — the lever for stronger A/B leads.
                </p>
              </div>
            </div>
          )}
        </SectionPanel>

        <ReviewInsights />

        <SectionPanel title="Top leads">
          {summary.isLoading ? (
            <SkeletonLines rows={5} />
          ) : !s || s.top_companies.length === 0 ? (
            <EmptyState title="No scored leads yet" />
          ) : (
            <div className="divide-y divide-line/60">
              {s.top_companies.map((l, i) => (
                <Link
                  key={l.company_domain}
                  to={`/companies/${encodeURIComponent(l.company_domain)}`}
                  className="-mx-3.5 flex items-center gap-3 px-3.5 py-1.5 hover:bg-raised"
                >
                  <span className="tabular w-5 text-right text-11 text-fg-subtle">{i + 1}</span>
                  <GradeBadge grade={l.grade} size="sm" />
                  <span className="min-w-0 flex-1 truncate text-13 text-fg">{l.company_name || l.company_domain}</span>
                  <span className="hidden text-11 text-fg-subtle sm:inline">{enumLabel(l.prospect_type)}</span>
                  <span className="tabular w-10 text-right text-13 text-fg-muted">{fmtScore(l.lead_score)}</span>
                </Link>
              ))}
            </div>
          )}
        </SectionPanel>
      </div>
    </>
  );
}
