import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import { Handshake, Plus } from "lucide-react";

import { DealFormModal } from "@/components/deals/DealFormModal";
import { ForecastCategoryBadge, fmtMoney } from "@/components/deals/bits";
import { DataTable } from "@/components/data/DataTable";
import { NumericCell } from "@/components/data/NumericCell";
import { Pager } from "@/components/data/Pager";
import { FilterBar, FilterSelect } from "@/components/shell/FilterBar";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { useDeals, usePipelines } from "@/lib/api/queries";
import { DEAL_FORECAST_CATEGORIES, type DealOut } from "@/lib/api/types";
import { useUrlFilters } from "@/hooks/useUrlFilters";
import { enumLabel, fmtDate, fmtInt } from "@/lib/format";

const KEYS = ["page", "pipeline_id", "stage_id", "forecast_category", "q"] as const;
const FORECAST_OPTIONS = DEAL_FORECAST_CATEGORIES.map((c) => ({ value: c, label: enumLabel(c) }));
const PAGE_SIZE = 25;

type SortField = "title" | "value" | "probability" | "expected_close_date" | "last_activity_at";

export function DealListPage() {
  const navigate = useNavigate();
  const { values, setValue, clear, activeCount } = useUrlFilters(KEYS);
  const page = Math.max(1, Number(values.page) || 1);
  const [sort, setSort] = useState<{ field: SortField; dir: "asc" | "desc" }>({ field: "last_activity_at", dir: "desc" });
  const [creating, setCreating] = useState(false);

  const pipelines = usePipelines({ active_only: true, limit: 50 });
  const pipelineOptions = (pipelines.data?.items ?? []).map((p) => ({ value: String(p.id), label: p.name }));
  const currentPipeline = pipelines.data?.items.find((p) => String(p.id) === values.pipeline_id) ?? pipelines.data?.items[0];
  const stageOptions = (currentPipeline?.stages ?? []).map((s) => ({ value: String(s.id), label: s.name }));

  const { data, isLoading, isError, error, refetch } = useDeals({
    pipeline_id: values.pipeline_id ? Number(values.pipeline_id) : undefined,
    stage_id: values.stage_id ? Number(values.stage_id) : undefined,
    forecast_category: values.forecast_category || undefined,
    search: values.q || undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });

  const items = data?.items ?? [];
  const sorted = useMemo(() => {
    const list = [...items];
    const dir = sort.dir === "asc" ? 1 : -1;
    list.sort((a, b) => {
      const av = a[sort.field], bv = b[sort.field];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "string" || typeof bv === "string") return String(av).localeCompare(String(bv)) * dir;
      return ((av as number) - (bv as number)) * dir;
    });
    return list;
  }, [items, sort]);

  function onSortChange(field: string) {
    setSort((s) => (s.field === field ? { field: field as SortField, dir: s.dir === "asc" ? "desc" : "asc" } : { field: field as SortField, dir: "desc" }));
  }

  const columns: ColumnDef<DealOut, any>[] = [
    {
      id: "title",
      header: "Deal",
      meta: { sortField: "title" },
      cell: ({ row }) => (
        <div className="min-w-0">
          <div className="truncate text-fg">{row.original.title}</div>
          <div className="truncate text-11 text-fg-subtle">{row.original.company_domain}</div>
        </div>
      ),
    },
    { id: "stage", header: "Stage", cell: ({ row }) => <span className="text-fg-muted">{row.original.stage_name}</span> },
    {
      id: "forecast",
      header: "Forecast",
      cell: ({ row }) => <ForecastCategoryBadge category={row.original.forecast_category} />,
    },
    { id: "owner", header: "Owner", cell: ({ row }) => <span className="text-fg-muted">{row.original.owner_email || "—"}</span> },
    {
      id: "value",
      header: "Value",
      meta: { align: "right", sortField: "value" },
      cell: ({ row }) => <NumericCell>{fmtMoney(row.original.value, row.original.currency)}</NumericCell>,
    },
    {
      id: "probability",
      header: "Probability",
      meta: { align: "right", sortField: "probability" },
      cell: ({ row }) => <NumericCell className="text-fg-muted">{row.original.probability}%</NumericCell>,
    },
    {
      id: "close",
      header: "Expected close",
      meta: { sortField: "expected_close_date" },
      cell: ({ row }) => <span className="text-11 text-fg-subtle">{row.original.expected_close_date ? fmtDate(row.original.expected_close_date) : "—"}</span>,
    },
  ];

  return (
    <>
      <PageHeader title="Deals" subtitle={data ? `${fmtInt(data.total)} deals` : "All deals across your pipelines"}>
        <Button variant="primary" size="sm" onClick={() => setCreating(true)} disabled={!currentPipeline}>
          <Plus size={13} /> New deal
        </Button>
      </PageHeader>

      <div className="space-y-4 p-4">
        <FilterBar activeCount={activeCount} onClear={clear}>
          <DebouncedInput value={values.q} onChange={(v) => setValue("q", v)} placeholder="Search deals…" className="w-56" />
          <FilterSelect label="All pipelines" value={values.pipeline_id} onChange={(v) => setValue("pipeline_id", v)} options={pipelineOptions} />
          <FilterSelect label="All stages" value={values.stage_id} onChange={(v) => setValue("stage_id", v)} options={stageOptions} />
          <FilterSelect label="All forecast categories" value={values.forecast_category} onChange={(v) => setValue("forecast_category", v)} options={FORECAST_OPTIONS} />
        </FilterBar>

        <div className="panel">
          {isError ? (
            <ErrorState title="Couldn't load deals" error={error} onRetry={refetch} />
          ) : (
            <DataTable
              columns={columns}
              data={sorted}
              isLoading={isLoading}
              getRowId={(r) => String(r.id)}
              onRowClick={(r) => navigate(`/deals/${r.id}`)}
              sort={sort}
              onSortChange={onSortChange}
              empty={
                <EmptyState
                  icon={<Handshake size={20} />}
                  title="No deals match"
                  description="Create a deal to start tracking it through your pipeline."
                  action={<Button size="sm" onClick={() => setCreating(true)} disabled={!currentPipeline}>New deal</Button>}
                />
              }
            />
          )}
          {data && data.pages > 1 && (
            <div className="border-t border-line px-2">
              <Pager page={page} pages={data.pages} total={data.total} pageSize={data.page_size} onPage={(p) => setValue("page", String(p))} />
            </div>
          )}
        </div>
      </div>

      {creating && currentPipeline && <DealFormModal pipeline={currentPipeline} onClose={() => setCreating(false)} />}
    </>
  );
}
