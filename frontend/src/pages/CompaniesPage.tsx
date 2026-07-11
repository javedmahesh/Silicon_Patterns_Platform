import { useEffect, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Building2 } from "lucide-react";

import { CompanyPeek } from "@/components/CompanyPeek";
import { DataTable } from "@/components/data/DataTable";
import { GradeBadge } from "@/components/data/GradeBadge";
import { Pager } from "@/components/data/Pager";
import { ScoreBar } from "@/components/data/ScoreBar";
import { FilterBar, FilterSelect } from "@/components/shell/FilterBar";
import { PageHeader } from "@/components/shell/PageHeader";
import { PeekDrawer } from "@/components/shell/PeekDrawer";
import { Badge } from "@/components/ui/Badge";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { SearchInput } from "@/components/ui/Input";
import { useDebounce } from "@/hooks/useDebounce";
import { useUrlFilters } from "@/hooks/useUrlFilters";
import { GRADE_OPTIONS, PROSPECT_OPTIONS, TIER_OPTIONS } from "@/lib/constants";
import { useCompanies } from "@/lib/api/queries";
import type { CompanySummary } from "@/lib/api/types";
import { enumLabel, fmtInt } from "@/lib/format";

const KEYS = ["page", "q", "tier", "prospect_type", "grade", "sort", "order"] as const;

function complianceTone(flag: string): "positive" | "warning" | "danger" | "neutral" {
  const f = flag.toUpperCase();
  if (f.includes("APPROVED")) return "positive";
  if (f.includes("EXCLUD")) return "danger";
  if (f.includes("REVIEW")) return "warning";
  return "neutral";
}

const columns: ColumnDef<CompanySummary, any>[] = [
  {
    id: "company",
    header: "Company",
    meta: { sortField: "company_name" },
    cell: ({ row }) => (
      <div className="flex min-w-0 items-center gap-2">
        <div className="min-w-0">
          <div className="truncate text-fg">{row.original.company_name || row.original.company_domain}</div>
          <div className="truncate text-11 text-fg-subtle">{row.original.company_domain}</div>
        </div>
        {row.original.is_stub && <Badge tone="warning">Stub</Badge>}
      </div>
    ),
  },
  { id: "grade", header: "Grade", cell: ({ row }) => <GradeBadge grade={row.original.grade} size="sm" /> },
  {
    id: "score",
    header: "Score",
    meta: { sortField: "lead_score", headerClass: "w-[170px]" },
    cell: ({ row }) =>
      row.original.lead_score != null ? (
        <ScoreBar value={row.original.lead_score} className="w-[150px]" />
      ) : (
        <span className="text-12 text-fg-subtle">—</span>
      ),
  },
  {
    id: "tier",
    header: "Tier",
    meta: { sortField: "company_tier" },
    cell: ({ row }) => <span className="text-fg-muted">{enumLabel(row.original.company_tier)}</span>,
  },
  {
    id: "prospect",
    header: "Prospect",
    meta: { headerClass: "hidden lg:table-cell", cellClass: "hidden lg:table-cell" },
    cell: ({ row }) => <span className="text-fg-muted">{enumLabel(row.original.prospect_type)}</span>,
  },
  {
    id: "compliance",
    header: "Compliance",
    meta: { headerClass: "hidden xl:table-cell", cellClass: "hidden xl:table-cell" },
    cell: ({ row }) =>
      row.original.compliance_flag ? (
        <Badge tone={complianceTone(row.original.compliance_flag)}>
          {enumLabel(row.original.compliance_flag)}
          {row.original.country ? ` · ${row.original.country}` : ""}
        </Badge>
      ) : (
        <span className="text-fg-subtle">—</span>
      ),
  },
];

export function CompaniesPage() {
  const { values, setValue, setMany, clear, activeCount } = useUrlFilters(KEYS);
  const page = Math.max(1, Number(values.page) || 1);
  const sort = values.sort || "lead_score";
  const order = values.order === "asc" ? "asc" : "desc";

  const [q, setQ] = useState(values.q);
  const dq = useDebounce(q, 300);
  useEffect(() => {
    setValue("q", dq);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dq]);

  const [selected, setSelected] = useState<CompanySummary | null>(null);

  const { data, isLoading, isError, error, refetch } = useCompanies({
    page,
    q: values.q,
    tier: values.tier,
    prospect_type: values.prospect_type,
    grade: values.grade,
    sort,
    order,
  });
  const items = data?.items ?? [];

  const onSortChange = (field: string) => {
    if (field === sort) {
      setMany({ sort: field, order: order === "asc" ? "desc" : "asc" });
    } else {
      setMany({ sort: field, order: field === "company_name" ? "asc" : "desc" });
    }
  };

  const clearAll = () => {
    setQ("");
    clear();
  };

  return (
    <>
      <PageHeader
        title="Companies"
        subtitle={data ? `${fmtInt(data.total)} companies` : "The company universe"}
      >
        <FilterBar activeCount={activeCount} onClear={clearAll}>
          <SearchInput
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search by name…"
            className="w-56"
          />
          <FilterSelect label="All grades" value={values.grade} onChange={(v) => setValue("grade", v)} options={GRADE_OPTIONS} />
          <FilterSelect label="All tiers" value={values.tier} onChange={(v) => setValue("tier", v)} options={TIER_OPTIONS} />
          <FilterSelect
            label="All prospect types"
            value={values.prospect_type}
            onChange={(v) => setValue("prospect_type", v)}
            options={PROSPECT_OPTIONS}
          />
        </FilterBar>
      </PageHeader>

      <div className="p-4">
        <div className="panel">
          {isError ? (
            <ErrorState title="Couldn't load companies" error={error} onRetry={refetch} />
          ) : (
            <DataTable
              columns={columns}
              data={items}
              isLoading={isLoading}
              getRowId={(r) => r.company_domain}
              onRowClick={setSelected}
              isActive={(r) => r.company_domain === selected?.company_domain}
              sort={{ field: sort, dir: order }}
              onSortChange={onSortChange}
              empty={
                <EmptyState
                  icon={<Building2 size={20} />}
                  title="No companies match"
                  description="Try a different search or clear the filters."
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

      <PeekDrawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.company_name || "Company"}
      >
        {selected && (
          <CompanyPeek
            domain={selected.company_domain}
            name={selected.company_name}
            grade={selected.grade}
            score={selected.lead_score}
            items={[
              { label: "Tier", value: enumLabel(selected.company_tier) },
              { label: "Prospect", value: enumLabel(selected.prospect_type) },
              { label: "Compliance", value: enumLabel(selected.compliance_flag) },
              { label: "Country", value: selected.country || "—" },
              { label: "Validation", value: enumLabel(selected.validation_status) },
            ]}
          />
        )}
      </PeekDrawer>
    </>
  );
}
