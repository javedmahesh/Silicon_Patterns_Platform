import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import { useCampaignMutations } from "@/lib/api/queries";
import { CAMPAIGN_TYPES } from "@/lib/api/types";
import type { CampaignOut } from "@/lib/api/types";
import { enumLabel } from "@/lib/format";

type Draft = {
  name: string;
  description: string;
  campaign_type: string;
  goal: string;
  budget: string;
  tags: string;
};

function draftFrom(c?: CampaignOut): Draft {
  return {
    name: c?.name ?? "",
    description: c?.description ?? "",
    campaign_type: c?.campaign_type ?? "cold_outreach",
    goal: c?.goal ?? "",
    budget: c?.budget != null ? String(c.budget) : "",
    tags: c?.tags?.join(", ") ?? "",
  };
}

export function CampaignFormModal({ campaign, onClose }: { campaign?: CampaignOut; onClose: () => void }) {
  const isEdit = Boolean(campaign);
  const [form, setForm] = useState<Draft>(draftFrom(campaign));
  const { create, patch } = useCampaignMutations();
  const pending = create.isPending || patch.isPending;
  const set = (k: keyof Draft) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));

  function save() {
    if (!form.name.trim()) return;
    const body = {
      name: form.name.trim(),
      description: form.description.trim(),
      campaign_type: form.campaign_type,
      goal: form.goal.trim(),
      budget: form.budget.trim() ? Number(form.budget) : null,
      tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
    };
    const onSuccess = () => { toast(isEdit ? "Campaign updated" : "Campaign created", "positive"); onClose(); };
    const onError = (e: unknown) => toast(apiErrorMessage(e), "danger");
    if (isEdit) patch.mutate({ id: campaign!.id, body }, { onSuccess, onError });
    else create.mutate(body, { onSuccess, onError });
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={isEdit ? "Edit campaign" : "New campaign"}
      width="32rem"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={pending}>Cancel</Button>
          <Button variant="primary" onClick={save} disabled={!form.name.trim() || pending}>
            {pending ? "Saving…" : "Save"}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <label className="block">
          <span className="mb-1 flex items-center gap-1 text-11 text-fg-muted">
            Name <span className="text-danger">*</span>
          </span>
          <Input value={form.name} onChange={set("name")} placeholder="Q1 enterprise outreach" autoFocus />
        </label>
        <label className="block">
          <span className="mb-1 block text-11 text-fg-muted">Description</span>
          <textarea
            value={form.description}
            onChange={set("description")}
            rows={2}
            className="w-full resize-y rounded-md border border-line bg-control px-2.5 py-1.5 text-13 text-fg outline-none focus:border-accent"
          />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="mb-1 block text-11 text-fg-muted">Type</span>
            <Select value={form.campaign_type} onChange={set("campaign_type")} className="w-full">
              {CAMPAIGN_TYPES.map((t) => <option key={t} value={t}>{enumLabel(t)}</option>)}
            </Select>
          </label>
          <label className="block">
            <span className="mb-1 block text-11 text-fg-muted">Budget</span>
            <Input type="number" min="0" value={form.budget} onChange={set("budget")} placeholder="5000" />
          </label>
        </div>
        <label className="block">
          <span className="mb-1 block text-11 text-fg-muted">Goal</span>
          <Input value={form.goal} onChange={set("goal")} placeholder="Book 20 qualified meetings" />
        </label>
        <label className="block">
          <span className="mb-1 block text-11 text-fg-muted">Tags (comma-separated)</span>
          <Input value={form.tags} onChange={set("tags")} placeholder="q1, enterprise" />
        </label>
      </div>
    </Modal>
  );
}
