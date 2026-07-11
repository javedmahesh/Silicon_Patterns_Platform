import { useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { ShieldCheck } from "lucide-react";

import { DataTable } from "@/components/data/DataTable";
import { NumericCell } from "@/components/data/NumericCell";
import { Pager } from "@/components/data/Pager";
import { ReviewDetail } from "@/components/review/ReviewDetail";
import { FilterBar, FilterSelect } from "@/components/shell/FilterBar";
import { PageHeader } from "@/components/shell/PageHeader";
import { PeekDrawer } from "@/components/shell/PeekDrawer";
import { Badge } from "@/components/ui/Badge";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { useUrlFilters } from "@/hooks/useUrlFilters";
import type { Option } from "@/lib/constants";
import { useReviewQueue } from "@/lib/api/queries";
import type { ReviewItemOut } from "@/lib/api/types";
import { enumLabel, fmtInt, fmtRelative, fmtScore } from "@/lib/format";

const KEYS = ["page", "status", "source_engine", "match_type"] as const;

const STATUS_OPTIONS: Option[] = [
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "merged", label: "Merged" },
  { value: "rejected", label: "Rejected" },
];

type Tone = "positive" | "warning" | "danger" | "accent" | "neutral";
function statusTone(status: string): Tone {
  const s = status.toLowerCase();
  if (s === "approved") return "positive";
  if (s === "merged") return "accent";
  if (s === "rejected") return "danger";
  return "warning";
}

const columns: ColumnDef<ReviewItemOut, any>[] = [
  {
    id: "name",
    header: "Raw name",
    cell: ({ row }) => (
      <div className="min-w-0">
        <div className="truncate text-fg">{row.original.raw_name || "—"}</div>
        <div className="truncate text-11 text-fg-subtle">{row.original.raw_domain || "no domain"}</div>
      </div>
    ),
  },
  { id: "engine", header: "Source", cell: ({ row }) => <Badge>{enumLabel(row.original.source_engine)}</Badge> },
  {
    id: "match",
    header: "Match",
    meta: { headerClass: "hidden md:table-cell", cellClass: "hidden md:table-cell" },
    cell: ({ row }) => <span className="text-fg-muted">{enumLabel(row.original.match_type)}</span>,
  },
  {
    id: "suggested",
    header: "Suggested",
    meta: { headerClass: "hidden lg:table-cell", cellClass: "hidden lg:table-cell" },
    cell: ({ row }) => <span className="text-fg-muted">{row.original.suggested_domain || "—"}</span>,
  },
  {
    id: "confidence",
    header: "Conf",
    meta: { align: "right", headerClass: "hidden sm:table-cell", cellClass: "hidden sm:table-cell" },
    cell: ({ row }) => <NumericCell className="text-fg-muted">{fmtScore(row.original.confidence, 2)}</NumericCell>,
  },
  {
    id: "status",
    header: "Status",
    cell: ({ row }) => <Badge tone={statusTone(row.original.status)}>{enumLabel(row.original.status)}</Badge>,
  },
  {
    id: "age",
    header: "Age",
    meta: { align: "right", headerClass: "hidden sm:table-cell", cellClass: "hidden sm:table-cell" },
    cell: ({ row }) => <span className="text-11 text-fg-subtle">{fmtRelative(row.original.created_at)}</span>,
  },
];

export function ReviewQueuePage() {
  const { values, setValue, clear, activeCount } = useUrlFilters(KEYS);
  const page = Math.max(1, Number(values.page) || 1);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const { data, isLoading, isError, error, refetch } = useReviewQueue({
    page,
    status: values.status,
    source_engine: values.source_engine,
    match_type: values.match_type,
  });
  const items = data?.items ?? [];

  return (
    <>
      <PageHeader
        title="Review queue"
        subtitle={data ? `${fmtInt(data.total)} items` : "Resolve, merge & approve companies"}
      >
        <FilterBar activeCount={activeCount} onClear={clear}>
          <FilterSelect label="All statuses" value={values.status} onChange={(v) => setValue("status", v)} options={STATUS_OPTIONS} />
          <DebouncedInput
            value={values.source_engine}
            onChange={(v) => setValue("source_engine", v)}
            placeholder="Source engine…"
            className="w-44"
          />
          <DebouncedInput
            value={values.match_type}
            onChange={(v) => setValue("match_type", v)}
            placeholder="Match type…"
            className="w-40"
          />
        </FilterBar>
      </PageHeader>

      <div className="p-4">
        <div className="panel">
          {isError ? (
            <ErrorState title="Couldn't load the review queue" error={error} onRetry={refetch} />
          ) : (
            <DataTable
              columns={columns}
              data={items}
              isLoading={isLoading}
              getRowId={(r) => String(r.id)}
              onRowClick={(r) => setSelectedId(r.id)}
              isActive={(r) => r.id === selectedId}
              empty={
                <EmptyState
                  icon={<ShieldCheck size={20} />}
                  title="Queue is clear"
                  description="No companies are awaiting resolution for these filters."
                />
              }
            />
          )}
          {data && data.total > 0 && (
            <div className="border-t border-line px-2">
              <Pager
                page={page}
                pages={data.pages}
                total={data.total}
                pageSize={data.page_size}
                onPage={(p) => setValue("page", String(p))}
              />
            </div>
          )}
        </div>
      </div>

      <PeekDrawer open={selectedId != null} onClose={() => setSelectedId(null)} title="Review item" width={460}>
        {selectedId != null && <ReviewDetail id={selectedId} />}
      </PeekDrawer>
    </>
  );
}
