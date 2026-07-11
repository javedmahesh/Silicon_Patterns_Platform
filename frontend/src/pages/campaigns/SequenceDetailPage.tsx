import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Pencil, Plus, Trash2 } from "lucide-react";

import { SequenceActiveBadge, stepActionLabel } from "@/components/campaigns/bits";
import { SequenceFormModal } from "@/components/campaigns/SequenceFormModal";
import { EnrollmentTable } from "@/components/campaigns/EnrollmentTable";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { Tabs } from "@/components/ui/Tabs";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  useEnrollments,
  useOutreachTemplates,
  useSequence,
  useSequenceMutations,
} from "@/lib/api/queries";
import { SEQUENCE_STEP_ACTIONS, type CrmSequenceOut } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/store";

type Tab = "steps" | "enrollments";
type StepOut = CrmSequenceOut["steps"][number];

function StepFormModal({
  sequenceId, step, nextOrder, onClose,
}: {
  sequenceId: number;
  step?: StepOut;
  nextOrder: number;
  onClose: () => void;
}) {
  const isEdit = Boolean(step);
  const [action, setAction] = useState(step?.action ?? "email");
  const [name, setName] = useState(step?.name ?? "");
  const [description, setDescription] = useState(step?.description ?? "");
  const [delayDays, setDelayDays] = useState(String(step?.delay_days ?? 0));
  const [templateId, setTemplateId] = useState<number | "">(step?.template_id ?? "");
  const { addStep, patchStep } = useSequenceMutations();
  const templates = useOutreachTemplates(true);
  const pending = addStep.isPending || patchStep.isPending;

  function save() {
    const body = {
      action, name: name.trim(), description: description.trim(),
      delay_days: Number(delayDays) || 0,
      template_id: templateId ? Number(templateId) : null,
      config: {},
    };
    const onSuccess = () => { toast(isEdit ? "Step updated" : "Step added", "positive"); onClose(); };
    const onError = (e: unknown) => toast(apiErrorMessage(e), "danger");
    if (isEdit) patchStep.mutate({ id: sequenceId, stepId: step!.id, body }, { onSuccess, onError });
    else addStep.mutate({ id: sequenceId, body: { ...body, step_order: nextOrder } }, { onSuccess, onError });
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={isEdit ? "Edit step" : "Add step"}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={pending}>Cancel</Button>
          <Button variant="primary" onClick={save} disabled={pending}>{pending ? "Saving…" : "Save"}</Button>
        </>
      }
    >
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="mb-1 block text-11 text-fg-muted">Action</span>
            <select value={action} onChange={(e) => setAction(e.target.value)}
              className="w-full rounded-md border border-line bg-control px-2.5 py-1.5 text-13 text-fg outline-none focus:border-accent">
              {SEQUENCE_STEP_ACTIONS.map((a) => <option key={a} value={a}>{stepActionLabel(a)}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-11 text-fg-muted">Delay (days after previous step)</span>
            <input type="number" min="0" value={delayDays} onChange={(e) => setDelayDays(e.target.value)}
              className="w-full rounded-md border border-line bg-control px-2.5 py-1.5 text-13 text-fg outline-none focus:border-accent" />
          </label>
        </div>
        <label className="block">
          <span className="mb-1 block text-11 text-fg-muted">Name</span>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Initial email"
            className="w-full rounded-md border border-line bg-control px-2.5 py-1.5 text-13 text-fg outline-none focus:border-accent" />
        </label>
        <label className="block">
          <span className="mb-1 block text-11 text-fg-muted">Description</span>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2}
            className="w-full resize-y rounded-md border border-line bg-control px-2.5 py-1.5 text-13 text-fg outline-none focus:border-accent" />
        </label>
        {(action === "email" || action === "follow_up") && (
          <label className="block">
            <span className="mb-1 block text-11 text-fg-muted">Email template (optional)</span>
            <select value={templateId} onChange={(e) => setTemplateId(e.target.value ? Number(e.target.value) : "")}
              className="w-full rounded-md border border-line bg-control px-2.5 py-1.5 text-13 text-fg outline-none focus:border-accent">
              <option value="">No template</option>
              {(templates.data ?? []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </label>
        )}
      </div>
    </Modal>
  );
}

export function SequenceDetailPage() {
  const { id } = useParams();
  const sequenceId = Number(id);
  const { isManager } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("steps");
  const [editing, setEditing] = useState(false);
  const [addingStep, setAddingStep] = useState(false);
  const [editingStep, setEditingStep] = useState<StepOut | null>(null);
  const [deletingStep, setDeletingStep] = useState<StepOut | null>(null);
  const [deletingSequence, setDeletingSequence] = useState(false);

  const { data: sequence, isLoading, isError, error, refetch } = useSequence(sequenceId);
  const { patch, remove, deleteStep } = useSequenceMutations();
  const enrollments = useEnrollments({ sequence_id: sequenceId, limit: 100 });
  const err = (e: unknown) => toast(apiErrorMessage(e), "danger");

  if (isError) return <div className="p-4"><ErrorState title="Couldn't load sequence" error={error} onRetry={refetch} /></div>;
  if (isLoading || !sequence) return <div className="grid h-full place-items-center"><Spinner size={20} /></div>;

  function toggleActive() {
    patch.mutate({ id: sequenceId, body: { is_active: !sequence!.is_active } }, {
      onSuccess: () => toast(sequence!.is_active ? "Sequence paused" : "Sequence resumed", "positive"),
      onError: err,
    });
  }

  function confirmDeleteStep() {
    if (!deletingStep) return;
    deleteStep.mutate({ id: sequenceId, stepId: deletingStep.id }, {
      onSuccess: () => { toast("Step deleted", "positive"); setDeletingStep(null); },
      onError: (e) => { err(e); setDeletingStep(null); },
    });
  }

  function confirmDeleteSequence() {
    remove.mutate(sequenceId, {
      onSuccess: () => { toast("Sequence deleted", "positive"); navigate("/campaigns/sequences"); },
      onError: (e) => { err(e); setDeletingSequence(false); },
    });
  }

  return (
    <>
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            <Link to="/campaigns/sequences" className="text-fg-subtle hover:text-fg" aria-label="Back to sequences"><ArrowLeft size={16} /></Link>
            {sequence.name}
            <SequenceActiveBadge isActive={sequence.is_active} />
          </span>
        }
        subtitle={sequence.description || undefined}
        actions={
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => setEditing(true)}>Edit</Button>
            <Button size="sm" variant="ghost" onClick={toggleActive} disabled={patch.isPending}>
              {sequence.is_active ? "Pause" : "Resume"}
            </Button>
            {isManager && <Button size="sm" variant="danger" onClick={() => setDeletingSequence(true)}>Delete</Button>}
          </div>
        }
      >
        <Tabs
          tabs={[
            { id: "steps", label: "Steps", count: sequence.step_count },
            { id: "enrollments", label: "Enrollments", count: enrollments.data?.total },
          ]}
          active={tab}
          onChange={setTab}
        />
      </PageHeader>

      <div className="p-4">
        {tab === "steps" && (
          <div className="space-y-3">
            <Button size="sm" onClick={() => setAddingStep(true)}><Plus size={13} /> Add step</Button>
            {sequence.steps.length === 0 ? (
              <div className="panel"><EmptyState title="No steps yet" description="Add the first touch in this sequence." /></div>
            ) : (
              <ol className="panel divide-y divide-line">
                {sequence.steps.map((s) => (
                  <li key={s.id} className="flex items-center gap-3 px-3.5 py-2.5">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-control text-11 text-fg-muted">{s.step_order}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-13 text-fg">{s.name || stepActionLabel(s.action)}</span>
                        <span className="rounded bg-control px-1.5 py-0.5 text-11 text-fg-subtle">{stepActionLabel(s.action)}</span>
                      </div>
                      {s.description && <div className="truncate text-11 text-fg-subtle">{s.description}</div>}
                    </div>
                    <span className="shrink-0 text-11 text-fg-subtle">{s.delay_days === 0 ? "Immediately" : `+${s.delay_days}d`}</span>
                    <Button size="sm" variant="ghost" aria-label={`Edit step ${s.step_order}`} onClick={() => setEditingStep(s)}>
                      <Pencil size={13} />
                    </Button>
                    <button
                      type="button"
                      aria-label={`Delete step ${s.step_order}`}
                      title="Delete step"
                      onClick={() => setDeletingStep(s)}
                      className="text-fg-subtle hover:text-danger"
                    >
                      <Trash2 size={14} />
                    </button>
                  </li>
                ))}
              </ol>
            )}
          </div>
        )}

        {tab === "enrollments" && (
          <div className="panel">
            <EnrollmentTable
              enrollments={enrollments.data?.items ?? []}
              isLoading={enrollments.isLoading}
              emptyTitle="No enrollments yet"
              emptyDescription="Enroll a campaign member into this sequence from the campaign's Members tab."
            />
          </div>
        )}
      </div>

      {editing && <SequenceFormModal sequence={sequence} onClose={() => setEditing(false)} />}
      {addingStep && (
        <StepFormModal sequenceId={sequenceId} nextOrder={sequence.steps.length + 1} onClose={() => setAddingStep(false)} />
      )}
      {editingStep && (
        <StepFormModal sequenceId={sequenceId} step={editingStep} nextOrder={0} onClose={() => setEditingStep(null)} />
      )}
      {deletingStep && (
        <Modal
          open
          onClose={() => setDeletingStep(null)}
          title="Delete step"
          footer={
            <>
              <Button variant="ghost" onClick={() => setDeletingStep(null)} disabled={deleteStep.isPending}>Cancel</Button>
              <Button variant="danger" onClick={confirmDeleteStep} disabled={deleteStep.isPending}>Delete</Button>
            </>
          }
        >
          <p className="text-13 text-fg-muted">Delete step {deletingStep.step_order} ({stepActionLabel(deletingStep.action)})? This can't be undone.</p>
        </Modal>
      )}
      {deletingSequence && (
        <Modal
          open
          onClose={() => setDeletingSequence(false)}
          title="Delete sequence"
          footer={
            <>
              <Button variant="ghost" onClick={() => setDeletingSequence(false)} disabled={remove.isPending}>Cancel</Button>
              <Button variant="danger" onClick={confirmDeleteSequence} disabled={remove.isPending}>Delete</Button>
            </>
          }
        >
          <p className="text-13 text-fg-muted">Delete “{sequence.name}”? It will be deactivated and no longer usable for new enrollments.</p>
        </Modal>
      )}
    </>
  );
}
