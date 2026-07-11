import { Link } from "react-router-dom";

import { GradeBadge, PriorityBadge, STAGE_ORDER, stageLabel } from "@/components/outreach/bits";
import { PageHeader } from "@/components/shell/PageHeader";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import { useOutreachLeads, usePatchOutreachLead } from "@/lib/api/queries";
import type { OutreachLeadOut } from "@/lib/api/types";
import { KanbanSquare } from "lucide-react";

function Card({ lead }: { lead: OutreachLeadOut }) {
  const patch = usePatchOutreachLead(lead.id);
  return (
    <div className="rounded-md border border-line bg-base p-2.5">
      <Link to={`/outreach/leads/${lead.id}`} className="block">
        <span className="block truncate text-12 font-medium text-fg hover:text-accent">{lead.company_name}</span>
      </Link>
      <div className="mt-1 flex items-center gap-1.5">
        <GradeBadge grade={lead.grade} />
        <PriorityBadge priority={lead.priority} />
      </div>
      {lead.primary_contact && (
        <div className="mt-1 truncate text-11 text-fg-subtle">{lead.primary_contact.full_name}</div>
      )}
      <select
        value={lead.stage}
        onChange={(e) => patch.mutate({ stage: e.target.value as never }, { onSuccess: () => toast("Moved", "positive") })}
        className="mt-1.5 h-7 w-full rounded border border-line bg-control px-1.5 text-11 text-fg-muted outline-none focus:border-accent"
      >
        {STAGE_ORDER.map((s) => <option key={s} value={s}>{stageLabel(s)}</option>)}
      </select>
    </div>
  );
}

export function OutreachPipelinePage() {
  const { data, isLoading, isError, error, refetch } = useOutreachLeads({ page_size: 200 });
  const leads = data?.items ?? [];
  const byStage = (stage: string) => leads.filter((l) => l.stage === stage);

  return (
    <>
      <PageHeader title="Pipeline" subtitle="Drag-free Kanban — move a lead with the stage selector on its card" />
      <div className="p-4">
        {isError ? (
          <ErrorState title="Couldn't load the pipeline" error={error} onRetry={refetch} />
        ) : isLoading ? (
          <div className="grid place-items-center py-12"><Spinner size={18} /></div>
        ) : leads.length === 0 ? (
          <div className="panel"><EmptyState icon={<KanbanSquare size={20} />} title="Pipeline is empty" description="Sync qualified leads from Discovery to populate the board." /></div>
        ) : (
          <div className="flex gap-3 overflow-x-auto pb-2">
            {STAGE_ORDER.map((stage) => {
              const items = byStage(stage);
              return (
                <div key={stage} className="w-60 shrink-0">
                  <div className="mb-2 flex items-center justify-between px-1">
                    <span className="text-12 font-medium text-fg">{stageLabel(stage)}</span>
                    <span className="text-11 text-fg-subtle">{items.length}</span>
                  </div>
                  <div className="space-y-2">
                    {items.map((l) => <Card key={l.id} lead={l} />)}
                    {items.length === 0 && <div className="rounded-md border border-dashed border-line py-4 text-center text-11 text-fg-subtle">—</div>}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
