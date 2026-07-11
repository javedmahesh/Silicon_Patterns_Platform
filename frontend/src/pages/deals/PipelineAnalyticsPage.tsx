import { useEffect, useState } from "react";

import { fmtMoney } from "@/components/deals/bits";
import { StatStrip, type Stat } from "@/components/data/StatStrip";
import { PageHeader } from "@/components/shell/PageHeader";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Select } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { useForecast, usePipelineAnalytics, usePipelines } from "@/lib/api/queries";
import { fmtInt, fmtPct } from "@/lib/format";

export function PipelineAnalyticsPage() {
  const [pipelineId, setPipelineId] = useState<number | null>(null);
  const pipelines = usePipelines({ active_only: true, limit: 50 });

  useEffect(() => {
    if (pipelineId === null && pipelines.data && pipelines.data.items.length > 0) {
      setPipelineId(pipelines.data.items.find((p) => p.is_default)?.id ?? pipelines.data.items[0].id);
    }
  }, [pipelines.data, pipelineId]);

  const analytics = usePipelineAnalytics(pipelineId ?? undefined);
  const forecast = useForecast(pipelineId ?? undefined);

  if (pipelines.isLoading) return <div className="grid h-full place-items-center"><Spinner size={20} /></div>;
  if (pipelines.data && pipelines.data.items.length === 0) {
    return (
      <>
        <PageHeader title="Pipeline analytics" />
        <div className="p-4"><div className="panel"><EmptyState title="No pipelines yet" description="Create a pipeline on the Pipeline board first." /></div></div>
      </>
    );
  }

  const stats: Stat[] = analytics.data
    ? [
        { label: "Open deals", value: fmtInt(analytics.data.open_deals) },
        { label: "Won", value: fmtInt(analytics.data.won_deals) },
        { label: "Lost", value: fmtInt(analytics.data.lost_deals) },
        { label: "Win rate", value: fmtPct(analytics.data.win_rate) },
        { label: "Pipeline value", value: fmtMoney(analytics.data.pipeline_value) },
        { label: "Weighted pipeline", value: fmtMoney(analytics.data.weighted_pipeline) },
        { label: "Stalled deals", value: fmtInt(analytics.data.stalled_deal_count) },
      ]
    : [];

  return (
    <>
      <PageHeader title="Pipeline analytics" subtitle="Forecast, win rate, and stage velocity">
        <Select value={pipelineId ?? ""} onChange={(e) => setPipelineId(Number(e.target.value))}>
          {(pipelines.data?.items ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
      </PageHeader>

      <div className="space-y-4 p-4">
        {analytics.isError ? (
          <ErrorState title="Couldn't load analytics" error={analytics.error} onRetry={analytics.refetch} />
        ) : analytics.isLoading ? (
          <div className="grid place-items-center py-8"><Spinner size={18} /></div>
        ) : (
          stats.length > 0 && <StatStrip stats={stats} />
        )}

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="panel p-3.5">
            <div className="mb-2 text-13 font-medium text-fg">Forecast</div>
            {forecast.isLoading ? (
              <div className="grid place-items-center py-6"><Spinner size={16} /></div>
            ) : forecast.isError ? (
              <ErrorState title="Couldn't load forecast" error={forecast.error} onRetry={forecast.refetch} />
            ) : forecast.data ? (
              <div className="space-y-2 text-12">
                <div className="flex justify-between"><span className="text-fg-subtle">Expected revenue</span><span className="tabular text-fg">{fmtMoney(forecast.data.expected_revenue)}</span></div>
                <div className="flex justify-between"><span className="text-fg-subtle">Weighted pipeline</span><span className="tabular text-fg">{fmtMoney(forecast.data.weighted_pipeline)}</span></div>
                <div className="flex justify-between"><span className="text-fg-subtle">Avg deal size</span><span className="tabular text-fg">{fmtMoney(forecast.data.avg_deal_size)}</span></div>
                <div className="flex justify-between"><span className="text-fg-subtle">Win probability</span><span className="tabular text-fg">{forecast.data.win_probability}%</span></div>
                {forecast.data.avg_sales_cycle_days != null && (
                  <div className="flex justify-between"><span className="text-fg-subtle">Avg sales cycle</span><span className="tabular text-fg">{forecast.data.avg_sales_cycle_days}d</span></div>
                )}
                {forecast.data.forecast_by_quarter.length > 0 && (
                  <div className="mt-3">
                    <div className="mb-1 text-11 text-fg-subtle">By quarter</div>
                    {forecast.data.forecast_by_quarter.map((q) => (
                      <div key={q.quarter} className="flex justify-between"><span className="text-fg-muted">{q.quarter}</span><span className="tabular text-fg">{fmtMoney(q.weighted_value)}</span></div>
                    ))}
                  </div>
                )}
              </div>
            ) : null}
          </div>

          <div className="panel p-3.5">
            <div className="mb-2 text-13 font-medium text-fg">Forecast by owner</div>
            {forecast.data && forecast.data.forecast_by_owner.length > 0 ? (
              <div className="space-y-1.5 text-12">
                {forecast.data.forecast_by_owner.map((o) => (
                  <div key={o.owner_id} className="flex justify-between"><span className="text-fg-muted">{o.owner_email || `User #${o.owner_id}`}</span><span className="tabular text-fg">{fmtMoney(o.weighted_value)}</span></div>
                ))}
              </div>
            ) : (
              <p className="text-12 text-fg-subtle">No owned open deals yet.</p>
            )}
          </div>
        </div>

        {analytics.data && analytics.data.stage_velocity.length > 0 && (
          <div className="panel">
            <div className="border-b border-line px-3.5 py-2 text-13 font-medium text-fg">Stage velocity</div>
            <div className="divide-y divide-line">
              {analytics.data.stage_velocity.map((s) => (
                <div key={s.stage_id} className="flex items-center justify-between gap-3 px-3.5 py-2 text-12">
                  <span className="text-fg">{s.stage_name}</span>
                  <span className="text-fg-subtle">{s.deals_entered} entered · {s.deals_exited} exited</span>
                  <span className="tabular text-fg-muted">{s.avg_time_days}d avg</span>
                  <span className="tabular text-fg-muted">{fmtPct(s.conversion_rate)} conversion</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
