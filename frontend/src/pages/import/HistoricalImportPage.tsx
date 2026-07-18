import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import { Database } from "lucide-react";

import { UploadCard } from "@/components/import/UploadCard";
import { IMPORT_STATUS_TONE, fmtDuration } from "@/components/import/importTones";
import { DataTable } from "@/components/data/DataTable";
import { NumericCell } from "@/components/data/NumericCell";
import { StatStrip, type Stat } from "@/components/data/StatStrip";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { useImportJobs } from "@/lib/api/queries";
import type { ImportJobDTO } from "@/lib/api/import-types";
import { useAuth } from "@/lib/auth/store";
import { enumLabel, fmtDateTime, fmtInt } from "@/lib/format";

const STATUS_FILTERS = ["", "previewed", "running", "completed", "failed", "rolled_back"];

export function HistoricalImportPage() {
  const { isAdmin } = useAuth();
  const nav = useNavigate();
  const jobs = useImportJobs();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");

  const all = jobs.data ?? [];
  const stats: Stat[] = [
    { label: "Total imports", value: fmtInt(all.length) },
    { label: "Running", value: fmtInt(all.filter((j) => j.status === "running").length),
      accent: all.some((j) => j.status === "running") ? "var(--accent)" : undefined },
    { label: "Completed", value: fmtInt(all.filter((j) => j.status === "completed").length),
      accent: "var(--positive)" },
    { label: "Failed", value: fmtInt(all.filter((j) => ["failed", "rolled_back"].includes(j.status)).length),
      accent: all.some((j) => ["failed", "rolled_back"].includes(j.status)) ? "var(--danger)" : undefined },
  ];

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return all.filter(
      (j) =>
        (!status || j.status === status) &&
        (!needle || j.filename.toLowerCase().includes(needle) || j.initiated_by.toLowerCase().includes(needle)),
    );
  }, [all, q, status]);

  const columns: ColumnDef<ImportJobDTO, unknown>[] = [
    {
      id: "filename", header: "File",
      cell: ({ row }) => (
        <div className="min-w-0">
          <div className="truncate text-12 text-fg">{row.original.filename || "—"}</div>
          <div className="truncate text-11 text-fg-subtle">
            {row.original.initiated_by || "—"} · {row.original.created_at ? fmtDateTime(row.original.created_at) : "—"}
          </div>
        </div>
      ),
    },
    { id: "status", header: "Status",
      cell: ({ row }) => <Badge tone={IMPORT_STATUS_TONE[row.original.status] ?? "neutral"}>{enumLabel(row.original.status)}</Badge> },
    { id: "created", header: "Created", meta: { align: "right" },
      cell: ({ row }) => <NumericCell className="text-positive">{fmtInt(row.original.created)}</NumericCell> },
    { id: "updated", header: "Updated", meta: { align: "right" },
      cell: ({ row }) => <NumericCell>{fmtInt(row.original.updated)}</NumericCell> },
    { id: "conflicts", header: "Conflicts", meta: { align: "right" },
      cell: ({ row }) => (
        <NumericCell className={row.original.conflicts ? "text-warning" : "text-fg-subtle"}>
          {fmtInt(row.original.conflicts)}
        </NumericCell>
      ) },
    { id: "records", header: "Records", meta: { align: "right" },
      cell: ({ row }) => <NumericCell>{fmtInt(row.original.decision_makers_processed)}</NumericCell> },
    { id: "duration", header: "Duration", meta: { align: "right" },
      cell: ({ row }) => <NumericCell className="text-fg-muted">{fmtDuration(row.original.duration_ms)}</NumericCell> },
  ];

  return (
    <>
      <PageHeader title="Historical Import" subtitle="Upload, review, approve and import historical company & contact data" />

      <div className="space-y-4 p-4">
        {isAdmin && <UploadCard />}

        <StatStrip stats={stats} />

        <div className="flex flex-wrap items-center gap-2">
          <DebouncedInput value={q} onChange={setQ} placeholder="Search by file or reviewer…" className="w-64" />
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="h-8 rounded-md border border-line-strong bg-control px-2 text-12 text-fg"
          >
            {STATUS_FILTERS.map((s) => (
              <option key={s} value={s}>{s ? enumLabel(s) : "All statuses"}</option>
            ))}
          </select>
        </div>

        <div className="panel">
          {jobs.isError ? (
            <ErrorState title="Couldn't load imports" error={jobs.error} onRetry={jobs.refetch} />
          ) : (
            <DataTable
              columns={columns}
              data={rows}
              isLoading={jobs.isLoading}
              getRowId={(r) => r.import_id}
              onRowClick={(r) => nav(`/historical-import/${r.import_id}`)}
              empty={<EmptyState icon={<Database size={20} />} title="No imports yet"
                                 description={isAdmin ? "Upload an Excel export above to generate a preview." : "An administrator can upload a historical export."} />}
            />
          )}
        </div>
      </div>
    </>
  );
}
