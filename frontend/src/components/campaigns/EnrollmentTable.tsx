import { useState } from "react";
import { Link } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import { CheckSquare, Pause, Play, X } from "lucide-react";

import { EnrollmentStatusBadge } from "@/components/campaigns/bits";
import { DataTable } from "@/components/data/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import { useEnrollmentMutations } from "@/lib/api/queries";
import type { CrmEnrollmentOut } from "@/lib/api/types";
import { fmtDateTime } from "@/lib/format";

export function EnrollmentTable({
  enrollments, isLoading, emptyTitle = "No enrollments yet", emptyDescription,
}: {
  enrollments: CrmEnrollmentOut[];
  isLoading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
}) {
  const { pause, resume, cancel, advance } = useEnrollmentMutations();
  const [cancelling, setCancelling] = useState<CrmEnrollmentOut | null>(null);
  const err = (e: unknown) => toast(apiErrorMessage(e), "danger");

  function confirmCancel() {
    if (!cancelling) return;
    cancel.mutate(cancelling.id, {
      onSuccess: () => { toast("Enrollment cancelled", "positive"); setCancelling(null); },
      onError: (e) => { err(e); setCancelling(null); },
    });
  }

  const columns: ColumnDef<CrmEnrollmentOut, any>[] = [
    {
      id: "company",
      header: "Company",
      cell: ({ row }) => (
        <Link to={`/companies/${encodeURIComponent(row.original.company_domain)}`} className="text-fg hover:text-accent">
          {row.original.company_name || row.original.company_domain || "—"}
        </Link>
      ),
    },
    {
      id: "sequence",
      header: "Sequence",
      cell: ({ row }) => (
        <Link to={`/campaigns/sequences/${row.original.sequence_id}`} className="text-fg-muted hover:text-accent">
          {row.original.sequence_name || `#${row.original.sequence_id}`}
        </Link>
      ),
    },
    {
      id: "campaign",
      header: "Campaign",
      cell: ({ row }) =>
        row.original.campaign_id ? (
          <Link to={`/campaigns/${row.original.campaign_id}`} className="text-fg-muted hover:text-accent">
            {row.original.campaign_name || `#${row.original.campaign_id}`}
          </Link>
        ) : (
          <span className="text-fg-subtle">—</span>
        ),
    },
    { id: "status", header: "Status", cell: ({ row }) => <EnrollmentStatusBadge status={row.original.status} /> },
    {
      id: "step",
      header: "Step",
      meta: { align: "right" },
      cell: ({ row }) => <span className="tabular text-fg-muted">{row.original.current_step} / {row.original.step_count}</span>,
    },
    {
      id: "next",
      header: "Next step",
      cell: ({ row }) => (
        <span className="text-11 text-fg-subtle">
          {row.original.status === "completed" || row.original.status === "cancelled"
            ? "—"
            : row.original.next_step_at ? fmtDateTime(row.original.next_step_at) : "Due now"}
        </span>
      ),
    },
    {
      id: "completed",
      header: "Completed",
      cell: ({ row }) => <span className="text-11 text-fg-subtle">{row.original.completed_at ? fmtDateTime(row.original.completed_at) : "—"}</span>,
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => {
        const e = row.original;
        const active = e.status === "active";
        const paused = e.status === "paused";
        const finished = e.status === "completed" || e.status === "cancelled" || e.status === "failed";
        if (finished) return null;
        return (
          <div className="flex items-center justify-end gap-1">
            {active && (
              <>
                <Button size="sm" variant="ghost" title="Advance to next step" aria-label="Advance to next step"
                  onClick={() => advance.mutate(e.id, { onError: err })}>
                  <CheckSquare size={13} />
                </Button>
                <Button size="sm" variant="ghost" title="Pause" aria-label="Pause enrollment"
                  onClick={() => pause.mutate(e.id, { onError: err })}>
                  <Pause size={13} />
                </Button>
              </>
            )}
            {paused && (
              <Button size="sm" variant="ghost" title="Resume" aria-label="Resume enrollment"
                onClick={() => resume.mutate(e.id, { onError: err })}>
                <Play size={13} />
              </Button>
            )}
            <Button size="sm" variant="ghost" title="Cancel" aria-label="Cancel enrollment" onClick={() => setCancelling(e)}>
              <X size={13} />
            </Button>
          </div>
        );
      },
    },
  ];

  return (
    <>
      <DataTable
        columns={columns}
        data={enrollments}
        isLoading={isLoading}
        getRowId={(r) => String(r.id)}
        empty={<EmptyState title={emptyTitle} description={emptyDescription} />}
      />
      {cancelling && (
        <Modal
          open
          onClose={() => setCancelling(null)}
          title="Cancel enrollment"
          footer={
            <>
              <Button variant="ghost" onClick={() => setCancelling(null)} disabled={cancel.isPending}>Keep it</Button>
              <Button variant="danger" onClick={confirmCancel} disabled={cancel.isPending}>Cancel enrollment</Button>
            </>
          }
        >
          <p className="text-13 text-fg-muted">
            Cancel {cancelling.company_name || cancelling.company_domain || "this lead"}'s enrollment in{" "}
            {cancelling.sequence_name || "this sequence"}? This stops all further scheduled steps.
          </p>
        </Modal>
      )}
    </>
  );
}
