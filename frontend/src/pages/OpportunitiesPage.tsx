import { useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { ExternalLink, Megaphone } from "lucide-react";

import { DataTable } from "@/components/data/DataTable";
import { NumericCell } from "@/components/data/NumericCell";
import { Pager } from "@/components/data/Pager";
import { OpportunityDetailModal } from "@/components/opportunities/OpportunityDetailModal";
import { FilterBar } from "@/components/shell/FilterBar";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { useUrlFilters } from "@/hooks/useUrlFilters";
import { useOpportunities } from "@/lib/api/queries";
import type { OpportunityOut } from "@/lib/api/types";
import { enumLabel, fmtDate, fmtInt, fmtRelative, fmtScore } from "@/lib/format";

const KEYS = ["page", "opportunity_type", "lifecycle_status", "sort", "date_from", "date_to", "signal_category"] as const;

const SORT_OPTIONS = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
  { value: "score", label: "Top score" },
] as const;

// First-class signal categories. Default is NEWS, so leadership people-movement
// events no longer appear under the general Opportunities/News feed.
const CATEGORY_OPTIONS = [
  { value: "NEWS", label: "News" },
  { value: "LEADERSHIP", label: "Leadership" },
  { value: "ALL", label: "All signals" },
] as const;

type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";
const LIFECYCLE_TONE: Record<string, Tone> = {
  NEW: "accent", ACTIVE: "positive", MONITORING: "warning", RESOLVED: "neutral", ARCHIVED: "neutral",
};

const columns: ColumnDef<OpportunityOut, any>[] = [
  {
    id: "type",
    header: "Type",
    cell: ({ row }) =>
      row.original.opportunity_type ? (
        <div className="flex flex-col items-start gap-0.5">
          <Badge tone="accent">{enumLabel(row.original.opportunity_type)}</Badge>
          {row.original.opportunity_subtype && (
            <span className="text-10 text-fg-subtle">{enumLabel(row.original.opportunity_subtype)}</span>
          )}
        </div>
      ) : (
        <span className="text-fg-subtle">—</span>
      ),
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
  {
    id: "title",
    header: "Headline",
    meta: { headerClass: "hidden md:table-cell", cellClass: "hidden md:table-cell" },
    cell: ({ row }) =>
      row.original.article_url ? (
        <a
          href={row.original.article_url}
          target="_blank"
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="inline-flex items-center gap-1 text-fg hover:text-accent"
        >
          <span className="line-clamp-1 max-w-[320px]">{row.original.article_title || "—"}</span>
          <ExternalLink size={11} className="shrink-0 text-fg-subtle" />
        </a>
      ) : (
        <span className="line-clamp-1 max-w-[320px] text-fg-muted">{row.original.article_title || "—"}</span>
      ),
  },
  {
    id: "lifecycle",
    header: "Stage",
    meta: { headerClass: "hidden sm:table-cell", cellClass: "hidden sm:table-cell" },
    cell: ({ row }) => (
      <Badge tone={LIFECYCLE_TONE[row.original.lifecycle_status] ?? "neutral"}>
        {enumLabel(row.original.lifecycle_status || "NEW")}
      </Badge>
    ),
  },
  {
    id: "date",
    header: "Published",
    cell: ({ row }) => (
      <span className="text-fg-muted" title={fmtDate(row.original.published_date)}>
        {fmtRelative(row.original.published_date)}
      </span>
    ),
  },
  {
    id: "score",
    header: "Score",
    meta: { align: "right" },
    cell: ({ row }) => (
      <NumericCell className="text-fg-muted">
        {fmtScore(row.original.effective_opportunity_score || row.original.opportunity_score, 0)}
      </NumericCell>
    ),
  },
];

/** ``fixedCategory`` locks the page to one signal category (used by the dedicated
 *  Leadership route); left undefined, the page defaults to NEWS with a category
 *  selector — so leadership events never appear under the general News feed. */
export function OpportunitiesPage({ fixedCategory }: { fixedCategory?: "LEADERSHIP" | "NEWS" } = {}) {
  const { values, setValue, clear, activeCount } = useUrlFilters(KEYS);
  const page = Math.max(1, Number(values.page) || 1);
  const [activeId, setActiveId] = useState<string | undefined>(undefined);

  const category = fixedCategory ?? (values.signal_category || "NEWS");
  const isLeadership = category === "LEADERSHIP";

  const { data, isLoading, isError, error, refetch } = useOpportunities({
    page,
    opportunity_type: values.opportunity_type,
    lifecycle_status: values.lifecycle_status,
    sort: (values.sort || "newest") as "newest" | "oldest" | "score",
    date_from: values.date_from,
    date_to: values.date_to,
    // "ALL" clears the filter; otherwise scope to the chosen first-class category.
    signal_category: category === "ALL" ? undefined : category,
  });
  const items = data?.items ?? [];

  const noun = isLeadership ? "leadership signals" : category === "ALL" ? "signals" : "market events";

  return (
    <>
      <PageHeader
        title={isLeadership ? "Leadership signals" : "Opportunities"}
        subtitle={
          data
            ? `${fmtInt(data.total)} ${noun}`
            : isLeadership
              ? "Executive hires, leadership & role changes — a first-class signal category"
              : "Market events from the News Collection Engine"
        }
      >
        <FilterBar activeCount={activeCount} onClear={clear}>
          {!fixedCategory && (
            <select
              aria-label="Signal category"
              value={category}
              onChange={(e) => setValue("signal_category", e.target.value)}
              className="h-8 rounded-md border border-line-strong bg-control px-2 text-13 text-fg"
            >
              {CATEGORY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          )}
          <DebouncedInput
            value={values.opportunity_type}
            onChange={(v) => setValue("opportunity_type", v)}
            placeholder="Filter by type…"
            className="w-48"
          />
          <select
            aria-label="Sort by"
            value={values.sort || "newest"}
            onChange={(e) => setValue("sort", e.target.value)}
            className="h-8 rounded-md border border-line-strong bg-control px-2 text-13 text-fg"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <select
            aria-label="Lifecycle stage"
            value={values.lifecycle_status}
            onChange={(e) => setValue("lifecycle_status", e.target.value)}
            className="h-8 rounded-md border border-line-strong bg-control px-2 text-13 text-fg"
          >
            <option value="">All stages</option>
            {["NEW", "ACTIVE", "MONITORING", "RESOLVED", "ARCHIVED"].map((l) => (
              <option key={l} value={l}>{enumLabel(l)}</option>
            ))}
          </select>
          <Input
            type="date"
            aria-label="From date"
            value={values.date_from}
            onChange={(e) => setValue("date_from", e.target.value)}
            className="w-[150px]"
          />
          <Input
            type="date"
            aria-label="To date"
            value={values.date_to}
            onChange={(e) => setValue("date_to", e.target.value)}
            className="w-[150px]"
          />
        </FilterBar>
      </PageHeader>

      <div className="p-4">
        <div className="panel">
          {isError ? (
            <ErrorState title="Couldn't load opportunities" error={error} onRetry={refetch} />
          ) : (
            <DataTable
              columns={columns}
              data={items}
              isLoading={isLoading}
              getRowId={(r) => r.opportunity_id}
              onRowClick={(r) => setActiveId(r.opportunity_id)}
              empty={
                <EmptyState
                  icon={<Megaphone size={20} />}
                  title="No opportunities match"
                  description="The Blog Crawler surfaces funding, product, and expansion events."
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

      <OpportunityDetailModal
        opportunityId={activeId}
        onClose={() => setActiveId(undefined)}
        onOpenOther={(id) => setActiveId(id)}
      />
    </>
  );
}
