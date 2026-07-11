import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import { Calendar } from "lucide-react";

import { ContractStatusBadge, fmtMoney } from "@/components/cs/bits";
import { DataTable } from "@/components/data/DataTable";
import { NumericCell } from "@/components/data/NumericCell";
import { FilterBar, FilterSelect } from "@/components/shell/FilterBar";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import { useCsAccounts, useCsContractMutations, useCsContracts } from "@/lib/api/queries";
import { CS_CONTRACT_STATUSES, type CsContractOut } from "@/lib/api/types";
import { enumLabel, fmtDate, fmtInt, fmtPct } from "@/lib/format";

const STATUS_OPTIONS = CS_CONTRACT_STATUSES.map((s) => ({ value: s, label: enumLabel(s) }));

export function RenewalsPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [renewing, setRenewing] = useState<CsContractOut | null>(null);

  const { data, isLoading, isError, error, refetch } = useCsContracts({ status: status || undefined, limit: 200 });
  const accounts = useCsAccounts({ limit: 200 });
  const accountName = useMemo(() => {
    const map = new Map<number, string>();
    for (const a of accounts.data?.items ?? []) map.set(a.id, a.name);
    return map;
  }, [accounts.data]);

  const items = (data?.items ?? [])
    .filter((c) => !q || c.name.toLowerCase().includes(q.toLowerCase()) || (accountName.get(c.account_id) ?? "").toLowerCase().includes(q.toLowerCase()))
    .sort((a, b) => {
      if (!a.end_date) return 1;
      if (!b.end_date) return -1;
      return new Date(a.end_date).getTime() - new Date(b.end_date).getTime();
    });

  const columns: ColumnDef<CsContractOut, any>[] = [
    {
      id: "name",
      header: "Contract",
      cell: ({ row }) => (
        <div className="min-w-0">
          <div className="truncate text-fg">{row.original.name}</div>
          <div className="truncate text-11 text-fg-subtle">{accountName.get(row.original.account_id) ?? `Account #${row.original.account_id}`}</div>
        </div>
      ),
    },
    { id: "status", header: "Status", cell: ({ row }) => <ContractStatusBadge status={row.original.status} /> },
    { id: "owner", header: "Owner", cell: ({ row }) => <span className="text-fg-muted">{row.original.owner_email || "—"}</span> },
    {
      id: "value",
      header: "Value",
      meta: { align: "right" },
      cell: ({ row }) => <NumericCell>{fmtMoney(row.original.value, row.original.currency)}</NumericCell>,
    },
    {
      id: "probability",
      header: "Renewal odds",
      meta: { align: "right" },
      cell: ({ row }) => <NumericCell className="text-fg-muted">{fmtPct(row.original.renewal_probability)}</NumericCell>,
    },
    {
      id: "end",
      header: "Ends",
      cell: ({ row }) => <span className="text-11 text-fg-subtle">{row.original.end_date ? fmtDate(row.original.end_date) : "—"}</span>,
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) =>
        row.original.status !== "renewed" && row.original.status !== "terminated" ? (
          <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); setRenewing(row.original); }}>
            Renew
          </Button>
        ) : null,
    },
  ];

  return (
    <>
      <PageHeader title="Renewals" subtitle={data ? `${fmtInt(data.total)} contracts` : "Contracts across all customer accounts"} />

      <div className="space-y-4 p-4">
        <FilterBar>
          <DebouncedInput value={q} onChange={setQ} placeholder="Search contract or account…" className="w-56" />
          <FilterSelect label="All statuses" value={status} onChange={setStatus} options={STATUS_OPTIONS} />
        </FilterBar>

        <div className="panel">
          {isError ? (
            <ErrorState title="Couldn't load contracts" error={error} onRetry={refetch} />
          ) : (
            <DataTable
              columns={columns}
              data={items}
              isLoading={isLoading}
              getRowId={(r) => String(r.id)}
              onRowClick={(r) => navigate(`/customer-success/accounts/${r.account_id}`)}
              empty={<EmptyState icon={<Calendar size={20} />} title="No contracts match" />}
            />
          )}
        </div>
      </div>

      {renewing && <RenewModal contract={renewing} onClose={() => setRenewing(null)} />}
    </>
  );
}

function RenewModal({ contract, onClose }: { contract: CsContractOut; onClose: () => void }) {
  const { patch } = useCsContractMutations();

  function markRenewed() {
    patch.mutate(
      { id: contract.id, body: { status: "renewed" } },
      {
        onSuccess: () => { toast("Contract marked renewed", "positive"); onClose(); },
        onError: (e) => toast(apiErrorMessage(e), "danger"),
      },
    );
  }
  function markPending() {
    patch.mutate(
      { id: contract.id, body: { status: "pending_renewal" } },
      {
        onSuccess: () => { toast("Marked pending renewal", "positive"); onClose(); },
        onError: (e) => toast(apiErrorMessage(e), "danger"),
      },
    );
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Renew “${contract.name}”`}
      footer={<Button variant="ghost" onClick={onClose} disabled={patch.isPending}>Close</Button>}
    >
      <div className="space-y-2">
        <p className="text-13 text-fg-muted">Current status: <ContractStatusBadge status={contract.status} /></p>
        <div className="flex gap-2">
          <Button size="sm" variant="primary" onClick={markRenewed} disabled={patch.isPending}>Mark renewed</Button>
          <Button size="sm" onClick={markPending} disabled={patch.isPending}>Mark pending renewal</Button>
        </div>
      </div>
    </Modal>
  );
}
