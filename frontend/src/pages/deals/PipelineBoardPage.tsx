import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { KanbanSquare, Plus } from "lucide-react";

import { DealFormModal } from "@/components/deals/DealFormModal";
import { fmtMoney } from "@/components/deals/bits";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Input, Select } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import { useDealMutations, useKanban, usePipelineMutations, usePipelines } from "@/lib/api/queries";
import type { KanbanOut } from "@/lib/api/types";
import { fmtInt } from "@/lib/format";

type Deal = KanbanOut["columns"][number]["deals"][number];

function NewPipelineModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("");
  const { create } = usePipelineMutations();

  function submit() {
    if (!name.trim()) return;
    create.mutate(
      {
        name: name.trim(),
        description: "",
        is_default: false,
        stages: [
          { name: "New", stage_type: "open", stage_order: 1, probability: 10 },
          { name: "Qualified", stage_type: "open", stage_order: 2, probability: 40 },
          { name: "Won", stage_type: "won", stage_order: 3, probability: 100 },
          { name: "Lost", stage_type: "lost", stage_order: 4, probability: 0 },
        ],
      },
      {
        onSuccess: () => { toast("Pipeline created", "positive"); onClose(); },
        onError: (e) => toast(apiErrorMessage(e), "danger"),
      },
    );
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="New pipeline"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={create.isPending}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={!name.trim() || create.isPending}>
            {create.isPending ? "Creating…" : "Create"}
          </Button>
        </>
      }
    >
      <label className="block">
        <span className="mb-1 block text-11 text-fg-muted">Name</span>
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Sales pipeline" autoFocus />
      </label>
      <p className="mt-2 text-11 text-fg-subtle">Starts with New → Qualified → Won → Lost stages; add or rename stages any time.</p>
    </Modal>
  );
}

function DealCard({ deal, stages, onMoved }: { deal: Deal; stages: KanbanOut["columns"]; onMoved: () => void }) {
  const navigate = useNavigate();
  const { move } = useDealMutations();

  return (
    <div
      draggable
      onDragStart={(e) => e.dataTransfer.setData("text/deal-id", String(deal.id))}
      onClick={() => navigate(`/deals/${deal.id}`)}
      className="cursor-pointer rounded-md border border-line bg-base p-2.5 hover:border-accent/60"
    >
      <div className="truncate text-13 text-fg">{deal.title}</div>
      <div className="truncate text-11 text-fg-subtle">{deal.company_domain}</div>
      <div className="mt-1.5 flex items-center justify-between gap-2">
        <span className="tabular text-12 text-fg">{fmtMoney(deal.value, deal.currency)}</span>
        <span className="text-11 text-fg-subtle">{deal.probability}%</span>
      </div>
      {deal.owner_email && <div className="mt-1 truncate text-11 text-fg-subtle">{deal.owner_email.split("@")[0]}</div>}
      <select
        value={deal.stage_id}
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => {
          e.stopPropagation();
          move.mutate(
            { id: deal.id, stageId: Number(e.target.value) },
            { onSuccess: onMoved, onError: (err) => toast(apiErrorMessage(err), "danger") },
          );
        }}
        aria-label={`Move "${deal.title}" to a different stage`}
        className="mt-1.5 w-full rounded-md border border-line bg-control px-1.5 py-1 text-11 text-fg outline-none focus:border-accent"
      >
        {stages.map((s) => <option key={s.stage_id} value={s.stage_id}>{s.stage_name}</option>)}
      </select>
    </div>
  );
}

export function PipelineBoardPage() {
  const [pipelineId, setPipelineId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [creatingPipeline, setCreatingPipeline] = useState(false);
  const [creatingDeal, setCreatingDeal] = useState(false);
  const [dragOverStage, setDragOverStage] = useState<number | null>(null);

  const pipelines = usePipelines({ active_only: true, limit: 50 });
  useEffect(() => {
    if (pipelineId === null && pipelines.data && pipelines.data.items.length > 0) {
      setPipelineId(pipelines.data.items.find((p) => p.is_default)?.id ?? pipelines.data.items[0].id);
    }
  }, [pipelines.data, pipelineId]);

  const kanban = useKanban(pipelineId ?? undefined, { search: search || undefined });
  const { move } = useDealMutations();
  const currentPipeline = pipelines.data?.items.find((p) => p.id === pipelineId);

  function onDrop(stageId: number) {
    return (e: React.DragEvent) => {
      e.preventDefault();
      setDragOverStage(null);
      const dealId = Number(e.dataTransfer.getData("text/deal-id"));
      if (!dealId) return;
      move.mutate({ id: dealId, stageId }, { onError: (err) => toast(apiErrorMessage(err), "danger") });
    };
  }

  if (pipelines.isLoading) return <div className="grid h-full place-items-center"><Spinner size={20} /></div>;
  if (pipelines.isError) return <div className="p-4"><ErrorState title="Couldn't load pipelines" error={pipelines.error} onRetry={pipelines.refetch} /></div>;
  if (pipelines.data && pipelines.data.items.length === 0) {
    return (
      <>
        <PageHeader title="Pipeline" subtitle="Sales pipeline board" />
        <div className="p-4">
          <div className="panel">
            <EmptyState
              icon={<KanbanSquare size={20} />}
              title="No pipelines yet"
              description="Create a pipeline to start tracking deals through stages."
              action={<Button size="sm" onClick={() => setCreatingPipeline(true)}>New pipeline</Button>}
            />
          </div>
        </div>
        {creatingPipeline && <NewPipelineModal onClose={() => setCreatingPipeline(false)} />}
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Pipeline"
        subtitle={kanban.data ? `${fmtInt(kanban.data.total_deals)} deals · ${fmtMoney(kanban.data.total_value)}` : "Sales pipeline board"}
      >
        <div className="flex items-center gap-2">
          <Select value={pipelineId ?? ""} onChange={(e) => setPipelineId(Number(e.target.value))}>
            {(pipelines.data?.items ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </Select>
          <DebouncedInput value={search} onChange={setSearch} placeholder="Search deals…" className="w-48" />
          <Button size="sm" variant="ghost" onClick={() => setCreatingPipeline(true)}>New pipeline</Button>
          <Button size="sm" variant="primary" onClick={() => setCreatingDeal(true)} disabled={!currentPipeline}>
            <Plus size={13} /> New deal
          </Button>
        </div>
      </PageHeader>

      <div className="p-4">
        {kanban.isError ? (
          <ErrorState title="Couldn't load the board" error={kanban.error} onRetry={kanban.refetch} />
        ) : kanban.isLoading || !kanban.data ? (
          <div className="grid place-items-center py-16"><Spinner size={20} /></div>
        ) : (
          <div className="flex gap-3 overflow-x-auto pb-2">
            {kanban.data.columns.map((col) => (
              <div
                key={col.stage_id}
                onDragOver={(e) => { e.preventDefault(); setDragOverStage(col.stage_id); }}
                onDragLeave={() => setDragOverStage((s) => (s === col.stage_id ? null : s))}
                onDrop={onDrop(col.stage_id)}
                className={`flex w-72 shrink-0 flex-col rounded-lg border ${dragOverStage === col.stage_id ? "border-accent bg-accent/5" : "border-line bg-surface"}`}
              >
                <div className="flex items-center justify-between border-b border-line px-3 py-2">
                  <span className="text-13 font-medium text-fg">{col.stage_name}</span>
                  <span className="tabular text-11 text-fg-subtle">{fmtInt(col.deal_count)}</span>
                </div>
                <div className="px-3 py-1 text-11 text-fg-subtle">{fmtMoney(col.total_value)}</div>
                <div className="flex-1 space-y-2 p-2">
                  {col.deals.length === 0 ? (
                    <div className="py-6 text-center text-11 text-fg-subtle">No deals</div>
                  ) : (
                    col.deals.map((d) => (
                      <DealCard key={d.id} deal={d} stages={kanban.data!.columns} onMoved={() => {}} />
                    ))
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {creatingPipeline && <NewPipelineModal onClose={() => setCreatingPipeline(false)} />}
      {creatingDeal && currentPipeline && <DealFormModal pipeline={currentPipeline} onClose={() => setCreatingDeal(false)} />}
    </>
  );
}
