import { SkeletonLines } from "@/components/ui/Skeleton";
import { usePipelineHealth } from "@/lib/api/queries";
import { fmtRelative } from "@/lib/format";

const STATUS_COLOR: Record<string, string> = {
  success: "var(--color-positive)",
  partial: "var(--color-warning)",
  skipped: "var(--color-fg-subtle)",
  failed: "var(--color-danger)",
  running: "var(--color-accent)",
  never: "var(--color-fg-subtle)",
};

/** Per-component freshness of the orchestrator pipeline (from /pipeline/health). */
export function PipelineHealthStrip() {
  const { data, isLoading, isError } = usePipelineHealth();

  if (isLoading) return <SkeletonLines rows={5} />;
  if (isError || !data) return <div className="text-12 text-fg-subtle">Pipeline status unavailable.</div>;

  return (
    <div className="space-y-1.5">
      {data.map((h) => (
        <div key={h.component} className="flex items-center gap-2.5">
          <span
            className="h-1.5 w-1.5 shrink-0 rounded-full"
            style={{ background: STATUS_COLOR[h.last_status] ?? "var(--color-fg-subtle)" }}
          />
          <span className="flex-1 text-13 capitalize text-fg">{h.component}</span>
          <span className="text-11 text-fg-subtle">{h.last_status}</span>
          <span className="tabular w-16 text-right text-11 text-fg-subtle">
            {h.last_success ? fmtRelative(h.last_success) : h.last_run ? fmtRelative(h.last_run) : "—"}
          </span>
        </div>
      ))}
    </div>
  );
}
