import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import { useSequenceMutations } from "@/lib/api/queries";
import type { CrmSequenceOut } from "@/lib/api/types";

export function SequenceFormModal({ sequence, onClose }: { sequence?: CrmSequenceOut; onClose: () => void }) {
  const isEdit = Boolean(sequence);
  const [name, setName] = useState(sequence?.name ?? "");
  const [description, setDescription] = useState(sequence?.description ?? "");
  const { create, patch } = useSequenceMutations();
  const pending = create.isPending || patch.isPending;

  function save() {
    if (!name.trim()) return;
    const onSuccess = () => { toast(isEdit ? "Sequence updated" : "Sequence created", "positive"); onClose(); };
    const onError = (e: unknown) => toast(apiErrorMessage(e), "danger");
    if (isEdit) patch.mutate({ id: sequence!.id, body: { name: name.trim(), description: description.trim() } }, { onSuccess, onError });
    else create.mutate({ name: name.trim(), description: description.trim() }, { onSuccess, onError });
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={isEdit ? "Edit sequence" : "New sequence"}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={pending}>Cancel</Button>
          <Button variant="primary" onClick={save} disabled={!name.trim() || pending}>{pending ? "Saving…" : "Save"}</Button>
        </>
      }
    >
      <div className="space-y-3">
        <label className="block">
          <span className="mb-1 flex items-center gap-1 text-11 text-fg-muted">Name <span className="text-danger">*</span></span>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="5-touch cold outreach" autoFocus />
        </label>
        <label className="block">
          <span className="mb-1 block text-11 text-fg-muted">Description</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full resize-y rounded-md border border-line bg-control px-2.5 py-1.5 text-13 text-fg outline-none focus:border-accent"
          />
        </label>
      </div>
    </Modal>
  );
}
