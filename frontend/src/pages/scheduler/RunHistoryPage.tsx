import { useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Clock } from "lucide-react";

import { DataTable } from "@/components/data/DataTable";
import { NumericCell } from "@/components/data/NumericCell";
import { Pager } from "@/components/data/Pager";
import { StatStrip, type Stat } from "@/components/data/StatStrip";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import { useRunHistory, useRunNow, useSchedulerStatus } from "@/lib/api/queries";
import type { ExecutionOut } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/store";
import { enumLabel, fmtDateTime, fmtInt } from "@/lib/format";

type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";
const STATUS_TONE: Record<string, Tone> = {
  success: "positive", partial: "warning", failed: "danger", running: "accent", skipped: "neutral",
};
const NOTIFY_TONE: Record<string, Tone> = {
  sent: "positive", logged: "accent", failed: "danger", skipped: "neutral", pending: "neutral",
};

function fmtDuration(ms: number): string {
  const s = (ms || 0) / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

export function RunHistoryPage() {
  const { isManager } = useAuth();
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState<ExecutionOut | null>(null);

  const status = useSchedulerStatus();
  const history = useRunHistory({ page, page_size: 20 });
  const runNow = useRunNow();

  const s = status.data;
  const stats: Stat[] = s
    ? [
        { label: "Scheduler", value: s.enabled ? (s.running ? "Running" : "Enabled") : "Disabled",
          accent: s.enabled && s.running ? "var(--positive)" : undefined },
        { label: "Schedule", value: s.schedule_times.join(" · ") || "—" },
        { label: "Next run", value: s.next_run ? fmtDateTime(s.next_run) : "—" },
        { label: "Active recipients", value: fmtInt(s.active_recipient_count) },
        { label: "Notifications", value: s.notify_configured ? `Graph (${s.notify_mode})` : `Log-only (${s.notify_mode})` },
        { label: "In progress", value: s.is_run_in_progress ? "Yes" : "No" },
      ]
    : [];

  function triggerRunNow() {
    runNow.mutate(undefined, {
      onSuccess: (r) => toast(r.detail || "Standard Run started", "positive"),
      onError: (e) => toast(apiErrorMessage(e), "danger"),
    });
  }

  const columns: ColumnDef<ExecutionOut, unknown>[] = [
    {
      id: "run_id", header: "Run ID",
      cell: ({ row }) => (
        <div className="min-w-0">
          <div className="truncate font-mono text-12 text-fg">{row.original.run_id}</div>
          <div className="text-11 text-fg-subtle">
            {enumLabel(row.original.trigger)}{row.original.scheduled_slot ? ` · ${row.original.scheduled_slot}` : ""}
          </div>
        </div>
      ),
    },
    { id: "status", header: "Status",
      cell: ({ row }) => <Badge tone={STATUS_TONE[row.original.status] ?? "neutral"}>{enumLabel(row.original.status)}</Badge> },
    { id: "started", header: "Started",
      cell: ({ row }) => <span className="text-12 text-fg-muted">{row.original.started_at ? fmtDateTime(row.original.started_at) : "—"}</span> },
    { id: "duration", header: "Duration", meta: { align: "right" },
      cell: ({ row }) => <NumericCell className="text-fg-muted">{fmtDuration(row.original.duration_ms)}</NumericCell> },
    { id: "processed", header: "Records", meta: { align: "right" },
      cell: ({ row }) => <NumericCell>{fmtInt(row.original.records_processed)}</NumericCell> },
    { id: "failures", header: "Failures", meta: { align: "right" },
      cell: ({ row }) => (
        <NumericCell className={row.original.failure_count ? "text-danger" : "text-fg-subtle"}>
          {fmtInt(row.original.failure_count)}
        </NumericCell>
      ) },
    { id: "notify", header: "Notification",
      cell: ({ row }) => <Badge tone={NOTIFY_TONE[row.original.notification_status] ?? "neutral"}>{enumLabel(row.original.notification_status)}</Badge> },
  ];

  return (
    <>
      <PageHeader
        title="Scheduler & Run History"
        subtitle="Automated Standard Runs, schedule, and per-run execution history"
        actions={
          isManager ? (
            <Button variant="primary" size="sm" onClick={triggerRunNow}
                    disabled={runNow.isPending || s?.is_run_in_progress}>
              {s?.is_run_in_progress ? "Run in progress…" : runNow.isPending ? "Starting…" : "Run now"}
            </Button>
          ) : undefined
        }
      />

      <div className="space-y-4 p-4">
        {status.isError ? (
          <ErrorState title="Couldn't load scheduler status" error={status.error} onRetry={status.refetch} />
        ) : status.isLoading ? (
          <div className="grid place-items-center py-6"><Spinner size={18} /></div>
        ) : (
          <StatStrip stats={stats} />
        )}

        <div className="panel">
          {history.isError ? (
            <ErrorState title="Couldn't load run history" error={history.error} onRetry={history.refetch} />
          ) : (
            <DataTable
              columns={columns}
              data={history.data?.items ?? []}
              isLoading={history.isLoading}
              getRowId={(r) => r.run_id}
              onRowClick={(r) => setDetail(r)}
              empty={<EmptyState icon={<Clock size={20} />} title="No runs yet"
                                 description="The scheduler records a row here for every Standard Run." />}
            />
          )}
          {history.data && history.data.pages > 1 && (
            <Pager page={history.data.page} pages={history.data.pages} total={history.data.total}
                   pageSize={history.data.page_size} onPage={setPage} />
          )}
        </div>
      </div>

      {detail && <RunDetailModal run={detail} onClose={() => setDetail(null)} />}
    </>
  );
}

function RunDetailModal({ run, onClose }: { run: ExecutionOut; onClose: () => void }) {
  const totals = run.totals || {};
  const totalRows: [string, string][] = [
    ["Companies", "companies"], ["Opportunities", "opportunities"],
    ["Decision makers", "decision_makers"], ["Jobs", "jobs"], ["Leads scored", "leads_scored"],
  ];

  return (
    <Modal open onClose={onClose} title={`Run ${run.run_id}`} width="max-w-2xl"
           footer={<Button variant="ghost" onClick={onClose}>Close</Button>}>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2 text-12">
          <Badge tone={STATUS_TONE[run.status] ?? "neutral"}>{enumLabel(run.status)}</Badge>
          <span className="text-fg-subtle">{enumLabel(run.trigger)}{run.scheduled_slot ? ` · ${run.scheduled_slot}` : ""}</span>
          <span className="text-fg-subtle">· {fmtDuration(run.duration_ms)}</span>
          <span className="text-fg-subtle">· {fmtInt(run.records_processed)} processed</span>
          <Badge tone={NOTIFY_TONE[run.notification_status] ?? "neutral"}>notify: {enumLabel(run.notification_status)}</Badge>
        </div>
        {run.notification_detail && <p className="text-11 text-fg-subtle">{run.notification_detail}</p>}

        <div>
          <div className="mb-1.5 text-13 font-medium text-fg">Engines</div>
          <div className="divide-y divide-line rounded-md border border-line">
            {run.stages.length === 0 ? (
              <p className="p-3 text-12 text-fg-subtle">No engine stages recorded.</p>
            ) : run.stages.map((st) => (
              <div key={st.component} className="flex items-center gap-3 px-3 py-2 text-12">
                <span className="min-w-0 flex-1 truncate text-fg">{enumLabel(st.component)}</span>
                <Badge tone={STATUS_TONE[st.status] ?? "neutral"}>{enumLabel(st.status)}</Badge>
                <span className="tabular w-24 text-right text-fg-muted">{fmtInt(st.processed)} recs</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-1.5 text-13 font-medium text-fg">Platform totals</div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-12 sm:grid-cols-3">
            {totalRows.map(([label, key]) => (
              <div key={key} className="flex justify-between gap-2">
                <span className="text-fg-subtle">{label}</span>
                <span className="tabular text-fg">{fmtInt(totals[key] ?? 0)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Modal>
  );
}
