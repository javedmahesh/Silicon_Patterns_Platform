import { Link } from "react-router-dom";
import { CheckCircle2, CheckSquare, Send } from "lucide-react";

import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import { useOutreachApprovals, useOutreachMessageAction } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/store";
import { fmtRelative } from "@/lib/format";

export function OutreachApprovalsPage() {
  const { isManager } = useAuth();
  const { data, isLoading } = useOutreachApprovals();
  const approve = useOutreachMessageAction("approve");
  const send = useOutreachMessageAction("send");
  const items = data ?? [];

  const act = (m: ReturnType<typeof useOutreachMessageAction>, id: number, ok: string) =>
    m.mutate(id, { onSuccess: () => toast(ok, "positive"), onError: () => toast("Action failed (admin/manager only)", "danger") });

  return (
    <>
      <PageHeader title="Approvals" subtitle="Outbound drafts awaiting an admin/manager sign-off before sending" />
      <div className="p-4">
        <div className="panel">
          {isLoading ? (
            <div className="grid place-items-center py-12"><Spinner size={18} /></div>
          ) : items.length === 0 ? (
            <EmptyState icon={<CheckSquare size={20} />} title="Nothing to approve" description="Drafts submitted for approval will appear here." />
          ) : (
            <div className="divide-y divide-line">
              {items.map((m) => (
                <div key={m.id} className="flex items-start justify-between gap-3 px-3.5 py-3">
                  <Link to={`/outreach/leads/${m.outreach_lead_id}`} className="min-w-0">
                    <div className="text-13 font-medium text-fg hover:text-accent">{m.subject || "(no subject)"}</div>
                    <div className="truncate text-12 text-fg-muted">To {m.recipient_name || m.to_email}</div>
                    <div className="mt-0.5 line-clamp-2 text-11 text-fg-subtle">{m.body}</div>
                    <div className="mt-0.5 text-11 text-fg-subtle">
                      by {m.created_by_email ? m.created_by_email.split("@")[0] : "—"} · {fmtRelative(m.created_at)}
                    </div>
                  </Link>
                  {isManager && (
                    <div className="flex shrink-0 flex-col gap-1.5">
                      <Button size="sm" variant="primary" onClick={() => act(approve, m.id, "Approved")} disabled={approve.isPending}>
                        <CheckCircle2 size={12} /> Approve
                      </Button>
                      <Button size="sm" onClick={() => act(send, m.id, "Approved & sent")} disabled={send.isPending}
                        title="Approve is required before send; use after approving">
                        <Send size={12} /> Send
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
