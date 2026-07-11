import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import { Building2, Plus } from "lucide-react";

import { AccountFormModal } from "@/components/cs/AccountFormModal";
import { AccountStatusBadge, HealthGradeBadge, HealthTrendBadge, fmtMoney } from "@/components/cs/bits";
import { DataTable } from "@/components/data/DataTable";
import { NumericCell } from "@/components/data/NumericCell";
import { Pager } from "@/components/data/Pager";
import { FilterBar, FilterSelect } from "@/components/shell/FilterBar";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { useCsAccounts } from "@/lib/api/queries";
import { CS_ACCOUNT_STATUSES, CS_ACCOUNT_TIERS, type CsAccountOut } from "@/lib/api/types";
import { useUrlFilters } from "@/hooks/useUrlFilters";
import { enumLabel, fmtDate, fmtInt } from "@/lib/format";

const KEYS = ["page", "status", "tier", "q"] as const;
const STATUS_OPTIONS = CS_ACCOUNT_STATUSES.map((s) => ({ value: s, label: enumLabel(s) }));
const TIER_OPTIONS = CS_ACCOUNT_TIERS.map((t) => ({ value: t, label: enumLabel(t) }));
const PAGE_SIZE = 25;

export function AccountListPage() {
  const navigate = useNavigate();
  const { values, setValue, clear, activeCount } = useUrlFilters(KEYS);
  const page = Math.max(1, Number(values.page) || 1);
  const [creating, setCreating] = useState(false);

  const { data, isLoading, isError, error, refetch } = useCsAccounts({
    status: values.status || undefined,
    tier: values.tier || undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });

  // No server-side text search on this endpoint — filter the loaded page client-side
  // (search is a convenience narrowing of what's already fetched, not a full-dataset query).
  const q = values.q.trim().toLowerCase();
  const items = (data?.items ?? []).filter(
    (a) => !q || a.name.toLowerCase().includes(q) || (a.company_domain ?? "").toLowerCase().includes(q),
  );

  const columns: ColumnDef<CsAccountOut, any>[] = [
    {
      id: "name",
      header: "Account",
      cell: ({ row }) => (
        <div className="min-w-0">
          <div className="truncate text-fg">{row.original.name}</div>
          {row.original.company_domain && <div className="truncate text-11 text-fg-subtle">{row.original.company_domain}</div>}
        </div>
      ),
    },
    { id: "status", header: "Status", cell: ({ row }) => <AccountStatusBadge status={row.original.status} /> },
    { id: "tier", header: "Tier", cell: ({ row }) => <span className="text-fg-muted">{enumLabel(row.original.tier)}</span> },
    { id: "owner", header: "Owner", cell: ({ row }) => <span className="text-fg-muted">{row.original.owner_email || "—"}</span> },
    {
      id: "health",
      header: "Health",
      cell: ({ row }) => (
        <div className="flex items-center gap-1.5">
          <HealthGradeBadge grade={row.original.health_grade} />
          <HealthTrendBadge trend={row.original.health_trend} />
        </div>
      ),
    },
    {
      id: "arr",
      header: "ARR",
      meta: { align: "right" },
      cell: ({ row }) => <NumericCell>{fmtMoney(row.original.arr, row.original.currency)}</NumericCell>,
    },
    {
      id: "renewal",
      header: "Renewal",
      cell: ({ row }) => <span className="text-11 text-fg-subtle">{row.original.renewal_date ? fmtDate(row.original.renewal_date) : "—"}</span>,
    },
  ];

  return (
    <>
      <PageHeader title="Customer accounts" subtitle={data ? `${fmtInt(data.total)} accounts` : "All customer success accounts"}>
        <Button variant="primary" size="sm" onClick={() => setCreating(true)}>
          <Plus size={13} /> New account
        </Button>
      </PageHeader>

      <div className="space-y-4 p-4">
        <FilterBar activeCount={activeCount} onClear={clear}>
          <DebouncedInput value={values.q} onChange={(v) => setValue("q", v)} placeholder="Search accounts…" className="w-56" />
          <FilterSelect label="All statuses" value={values.status} onChange={(v) => setValue("status", v)} options={STATUS_OPTIONS} />
          <FilterSelect label="All tiers" value={values.tier} onChange={(v) => setValue("tier", v)} options={TIER_OPTIONS} />
        </FilterBar>

        <div className="panel">
          {isError ? (
            <ErrorState title="Couldn't load accounts" error={error} onRetry={refetch} />
          ) : (
            <DataTable
              columns={columns}
              data={items}
              isLoading={isLoading}
              getRowId={(r) => String(r.id)}
              onRowClick={(r) => navigate(`/customer-success/accounts/${r.id}`)}
              empty={
                <EmptyState
                  icon={<Building2 size={20} />}
                  title="No accounts match"
                  description="Create a customer account to start tracking health, contracts, and renewals."
                  action={<Button size="sm" onClick={() => setCreating(true)}>New account</Button>}
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

      {creating && <AccountFormModal onClose={() => setCreating(false)} />}
    </>
  );
}
