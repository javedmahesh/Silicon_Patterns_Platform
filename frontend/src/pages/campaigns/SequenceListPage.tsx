import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import { Plus, Workflow } from "lucide-react";

import { SequenceActiveBadge } from "@/components/campaigns/bits";
import { SequenceFormModal } from "@/components/campaigns/SequenceFormModal";
import { DataTable } from "@/components/data/DataTable";
import { NumericCell } from "@/components/data/NumericCell";
import { Pager } from "@/components/data/Pager";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { useSequences } from "@/lib/api/queries";
import type { CrmSequenceOut } from "@/lib/api/types";
import { fmtDate, fmtInt } from "@/lib/format";

const PAGE_SIZE = 25;

export function SequenceListPage() {
  const navigate = useNavigate();
  const [activeOnly, setActiveOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);

  const { data, isLoading, isError, error, refetch } = useSequences({
    active_only: activeOnly, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE,
  });

  const columns: ColumnDef<CrmSequenceOut, any>[] = [
    {
      id: "name",
      header: "Sequence",
      cell: ({ row }) => (
        <div className="min-w-0">
          <div className="truncate text-fg">{row.original.name}</div>
          {row.original.description && <div className="truncate text-11 text-fg-subtle">{row.original.description}</div>}
        </div>
      ),
    },
    { id: "status", header: "Status", cell: ({ row }) => <SequenceActiveBadge isActive={row.original.is_active} /> },
    {
      id: "steps",
      header: "Steps",
      meta: { align: "right" },
      cell: ({ row }) => <NumericCell>{fmtInt(row.original.step_count)}</NumericCell>,
    },
    {
      id: "created",
      header: "Created",
      cell: ({ row }) => <span className="text-11 text-fg-subtle">{fmtDate(row.original.created_at)}</span>,
    },
  ];

  return (
    <>
      <PageHeader
        title="Sequences"
        subtitle={data ? `${fmtInt(data.total)} sequences` : "Reusable multi-step outreach templates"}
      >
        <Button variant="primary" size="sm" onClick={() => setCreating(true)}>
          <Plus size={13} /> New sequence
        </Button>
      </PageHeader>

      <div className="space-y-4 p-4">
        <label className="flex w-fit items-center gap-1.5 text-12 text-fg-muted">
          <input type="checkbox" checked={activeOnly} onChange={(e) => { setActiveOnly(e.target.checked); setPage(1); }} />
          Active only
        </label>

        <div className="panel">
          {isError ? (
            <ErrorState title="Couldn't load sequences" error={error} onRetry={refetch} />
          ) : (
            <DataTable
              columns={columns}
              data={data?.items ?? []}
              isLoading={isLoading}
              getRowId={(r) => String(r.id)}
              onRowClick={(r) => navigate(`/campaigns/sequences/${r.id}`)}
              empty={
                <EmptyState
                  icon={<Workflow size={20} />}
                  title="No sequences yet"
                  description="Create a reusable sequence of touches (email, call, follow-up) to enroll leads into."
                  action={<Button size="sm" onClick={() => setCreating(true)}>New sequence</Button>}
                />
              }
            />
          )}
          {data && data.pages > 1 && (
            <div className="border-t border-line px-2">
              <Pager page={page} pages={data.pages} total={data.total} pageSize={data.page_size} onPage={setPage} />
            </div>
          )}
        </div>
      </div>

      {creating && <SequenceFormModal onClose={() => setCreating(false)} />}
    </>
  );
}
