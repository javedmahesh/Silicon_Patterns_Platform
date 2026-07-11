import { useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { ListOrdered } from "lucide-react";

import { CompanyPeek } from "@/components/CompanyPeek";
import { ConfidenceBadge } from "@/components/data/ConfidenceBadge";
import { DataTable } from "@/components/data/DataTable";
import { GradeBadge } from "@/components/data/GradeBadge";
import { HumanStatusBadge } from "@/components/data/HumanStatusBadge";
import { NumericCell } from "@/components/data/NumericCell";
import { Pager } from "@/components/data/Pager";
import { ScoreBar } from "@/components/data/ScoreBar";
import { FilterBar, FilterSelect } from "@/components/shell/FilterBar";
import { PageHeader } from "@/components/shell/PageHeader";
import { PeekDrawer } from "@/components/shell/PeekDrawer";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { useUrlFilters } from "@/hooks/useUrlFilters";
import { GRADE_OPTIONS, PROSPECT_OPTIONS, TIER_OPTIONS } from "@/lib/constants";
import { useLeads } from "@/lib/api/queries";
import type { LeadOut } from "@/lib/api/types";
import { enumLabel, fmtInt, fmtScore } from "@/lib/format";
import { reviewStatusLabel } from "@/lib/reviewStatus";

const KEYS = ["page", "grade", "tier", "prospect_type", "sort"] as const;

const SORT_OPTIONS = [
  { value: "human", label: "Sort: Human assessment" },
  { value: "combined", label: "Sort: Combined priority" },
];

const subCol = (id: string, header: string, pick: (l: LeadOut) => number): ColumnDef<LeadOut, any> => ({
  id,
  header,
  meta: { align: "right", headerClass: "hidden xl:table-cell", cellClass: "hidden xl:table-cell" },
  cell: ({ row }) => <NumericCell className="text-fg-muted">{fmtScore(pick(row.original), 0)}</NumericCell>,
});

const columns: ColumnDef<LeadOut, any>[] = [
  {
    id: "rank",
    header: "#",
    meta: { align: "right" },
    cell: ({ row }) => <NumericCell className="text-fg-subtle">{fmtInt(row.original.priority_rank)}</NumericCell>,
  },
  {
    id: "company",
    header: "Company",
    cell: ({ row }) => (
      <div className="min-w-0">
        <div className="truncate text-fg">{row.original.company_name || row.original.company_domain}</div>
        <div className="truncate text-11 text-fg-subtle">{row.original.company_domain}</div>
      </div>
    ),
  },
  { id: "grade", header: "Grade", cell: ({ row }) => <GradeBadge grade={row.original.grade} size="sm" /> },
  {
    id: "human",
    header: "Human",
    cell: ({ row }) => <HumanStatusBadge status={row.original.human_status} />,
  },
  {
    id: "adjusted",
    header: "Adj.",
    meta: { cellClass: "hidden md:table-cell", headerClass: "hidden md:table-cell" },
    cell: ({ row }) => {
      const adj = row.original.adjusted_grade;
      // Only call it out when a human review actually moved the grade.
      return adj && adj !== row.original.grade ? (
        <GradeBadge grade={adj} size="sm" />
      ) : (
        <span className="text-12 text-fg-subtle">—</span>
      );
    },
  },
  {
    id: "confidence",
    header: "Conf.",
    meta: { cellClass: "hidden md:table-cell", headerClass: "hidden md:table-cell" },
    cell: ({ row }) => (
      <ConfidenceBadge confidence={row.original.confidence} coverage={row.original.coverage} />
    ),
  },
  {
    id: "score",
    header: "Score",
    meta: { headerClass: "w-[170px]" },
    cell: ({ row }) => <ScoreBar value={row.original.lead_score} className="w-[150px]" />,
  },
  subCol("opp", "Opp", (l) => l.opportunity_subscore),
  subCol("dem", "Dem", (l) => l.demand_subscore),
  subCol("rdy", "Rdy", (l) => l.readiness_subscore),
  subCol("dm", "DM", (l) => l.dm_subscore),
  {
    id: "tier",
    header: "Tier",
    meta: { cellClass: "hidden lg:table-cell", headerClass: "hidden lg:table-cell" },
    cell: ({ row }) => <span className="text-fg-muted">{enumLabel(row.original.company_tier)}</span>,
  },
  {
    id: "prospect",
    header: "Prospect",
    meta: { cellClass: "hidden lg:table-cell", headerClass: "hidden lg:table-cell" },
    cell: ({ row }) => <span className="text-fg-muted">{enumLabel(row.original.prospect_type)}</span>,
  },
];

export function LeadsPage() {
  const { values, setValue, clear, activeCount } = useUrlFilters(KEYS);
  const page = Math.max(1, Number(values.page) || 1);
  const [selected, setSelected] = useState<LeadOut | null>(null);

  const sort = (values.sort as "model" | "human" | "combined") || "model";
  const { data, isLoading, isError, error, refetch } = useLeads({
    page,
    grade: values.grade,
    tier: values.tier,
    prospect_type: values.prospect_type,
    sort,
  });
  const items = data?.items ?? [];

  return (
    <>
      <PageHeader
        title="Lead rankings"
        subtitle={data ? `${fmtInt(data.total)} scored prospects` : "Scored, ranked prospects"}
      >
        <FilterBar activeCount={activeCount} onClear={clear}>
          <FilterSelect label="All grades" value={values.grade} onChange={(v) => setValue("grade", v)} options={GRADE_OPTIONS} />
          <FilterSelect label="All tiers" value={values.tier} onChange={(v) => setValue("tier", v)} options={TIER_OPTIONS} />
          <FilterSelect
            label="All prospect types"
            value={values.prospect_type}
            onChange={(v) => setValue("prospect_type", v)}
            options={PROSPECT_OPTIONS}
          />
          <FilterSelect
            label="Sort: Model score"
            value={values.sort}
            onChange={(v) => setValue("sort", v)}
            options={SORT_OPTIONS}
          />
        </FilterBar>
      </PageHeader>

      <div className="p-4">
        <div className="panel">
          {isError ? (
            <ErrorState title="Couldn't load leads" error={error} onRetry={refetch} />
          ) : (
            <DataTable
              columns={columns}
              data={items}
              isLoading={isLoading}
              getRowId={(r) => r.company_domain}
              onRowClick={setSelected}
              isActive={(r) => r.company_domain === selected?.company_domain}
              empty={
                <EmptyState
                  icon={<ListOrdered size={20} />}
                  title="No leads match"
                  description="Adjust the filters, or run the scoring stage to populate leads."
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
        title={selected?.company_name || "Lead"}
      >
        {selected && (
          <CompanyPeek
            domain={selected.company_domain}
            name={selected.company_name}
            grade={selected.grade}
            score={selected.lead_score}
            rank={selected.priority_rank}
            items={[
              { label: "Human status", value: reviewStatusLabel(selected.human_status) },
              {
                label: "Adjusted grade",
                value:
                  selected.adjusted_grade && selected.adjusted_grade !== selected.grade
                    ? `${selected.adjusted_grade} (${fmtScore(selected.adjusted_score ?? selected.lead_score, 0)})`
                    : "= model",
              },
              { label: "Tier", value: enumLabel(selected.company_tier) },
              { label: "Prospect", value: enumLabel(selected.prospect_type) },
              { label: "Compliance", value: enumLabel(selected.compliance_flag) },
              { label: "Confidence", value: `${enumLabel(selected.confidence)} (${selected.coverage}/3 signals)` },
              { label: "Opportunity", value: fmtScore(selected.opportunity_subscore, 0) },
              { label: "Demand", value: fmtScore(selected.demand_subscore, 0) },
              { label: "Readiness", value: fmtScore(selected.readiness_subscore, 0) },
              { label: "Decision makers", value: fmtScore(selected.dm_subscore, 0) },
            ]}
          />
        )}
      </PeekDrawer>
    </>
  );
}
