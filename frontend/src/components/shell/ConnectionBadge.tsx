import { AlertTriangle } from "lucide-react";

import { Tooltip } from "@/components/ui/Tooltip";
import { useHealth, usePipelineStatus } from "@/lib/api/queries";
import { cx } from "@/lib/cx";
import { fmtDateTime, fmtRelative } from "@/lib/format";

/** API connectivity (from /health) + data freshness anchored to the last *successful*
 *  refresh (/pipeline/status), with a warning when the latest run failed or is running. */
export function ConnectionBadge() {
  const { data, isError, isLoading } = useHealth();
  const status = usePipelineStatus();
  const s = status.data;

  const ok = !isError && data?.status === "ok" && data?.database === "ok";
  const dbError = !isError && !!data && data.database !== "ok";
  const color = isLoading
    ? "var(--color-fg-subtle)"
    : ok
      ? "var(--color-positive)"
      : dbError
        ? "var(--color-warning)"
        : "var(--color-danger)";
  const label = isLoading ? "Connecting" : ok ? "Online" : dbError ? "DB error" : "Offline";

  const fresh = s?.last_successful_refresh ?? null;
  const failing = !!s && !s.in_progress && (s.latest_run_status === "failed" || s.latest_run_status === "partial");
  const freshText = s?.in_progress ? "refreshing…" : fresh ? fmtRelative(fresh) : null;

  const tip = (
    <div className="space-y-0.5">
      <div>
        {data ? `${data.app} v${data.version} · database ${data.database}` : "API unreachable — start the backend"}
      </div>
      <div className="text-fg-subtle">
        {fresh ? `Data as of ${fmtDateTime(fresh)}` : "No successful refresh recorded yet"}
      </div>
      {failing && (
        <div className="text-warning">
          ⚠ Latest refresh ({s?.latest_run_component ?? "?"}) {s?.latest_run_status} — showing last good data
        </div>
      )}
    </div>
  );

  return (
    <Tooltip side="bottom" label={tip}>
      <span className="inline-flex h-8 items-center gap-2 rounded-md border border-line bg-control px-2 text-12 text-fg-muted">
        <span className="inline-flex items-center gap-1.5">
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: color, boxShadow: `0 0 6px ${color}` }}
          />
          {label}
        </span>
        {freshText && (
          <>
            <span className="text-fg-subtle">·</span>
            <span className={cx("tabular", failing ? "text-warning" : "text-fg-subtle")}>{freshText}</span>
            {failing && <AlertTriangle size={12} className="text-warning" />}
          </>
        )}
      </span>
    </Tooltip>
  );
}
