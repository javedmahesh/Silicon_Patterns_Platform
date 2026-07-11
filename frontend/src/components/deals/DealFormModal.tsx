import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { Input, Select } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import { useCompanies, useDealMutations, usePipeline } from "@/lib/api/queries";
import { DEAL_CURRENCIES, DEAL_FORECAST_CATEGORIES, type DealOut, type PipelineOut } from "@/lib/api/types";
import { enumLabel } from "@/lib/format";

export function DealFormModal({
  deal, pipeline, onClose,
}: {
  deal?: DealOut;
  /** Required for create (which pipeline/stage to file the new deal under); ignored for edit. */
  pipeline?: PipelineOut;
  onClose: () => void;
}) {
  const isEdit = Boolean(deal);
  const [title, setTitle] = useState(deal?.title ?? "");
  const [q, setQ] = useState("");
  const [domain, setDomain] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [stageId, setStageId] = useState<number | "">(pipeline?.stages[0]?.id ?? "");
  const [value, setValue] = useState(deal?.value != null ? String(deal.value) : "");
  const [currency, setCurrency] = useState(deal?.currency ?? "USD");
  const [probability, setProbability] = useState(deal?.probability != null ? String(deal.probability) : "");
  const [forecastCategory, setForecastCategory] = useState(deal?.forecast_category ?? "pipeline");
  const [expectedClose, setExpectedClose] = useState(deal?.expected_close_date?.slice(0, 10) ?? "");
  const [notes, setNotes] = useState(deal?.notes ?? "");

  const { data: search } = useCompanies({ q, page_size: 6 });
  const { data: fullPipeline } = usePipeline(isEdit ? deal!.pipeline_id : undefined);
  const { create, patch } = useDealMutations();
  const pending = create.isPending || patch.isPending;

  function save() {
    if (!title.trim()) return;
    const shared = {
      value: value.trim() ? Number(value) : null,
      currency,
      probability: probability.trim() ? Number(probability) : null,
      forecast_category: forecastCategory,
      expected_close_date: expectedClose ? new Date(expectedClose).toISOString() : null,
      notes: notes.trim(),
    };
    const onSuccess = () => { toast(isEdit ? "Deal updated" : "Deal created", "positive"); onClose(); };
    const onError = (e: unknown) => toast(apiErrorMessage(e), "danger");

    if (isEdit) {
      patch.mutate({ id: deal!.id, body: { title: title.trim(), ...shared } }, { onSuccess, onError });
    } else {
      if (!domain || !stageId || !pipeline) return;
      create.mutate(
        {
          title: title.trim(), company_domain: domain, pipeline_id: pipeline.id, stage_id: Number(stageId),
          ...shared, tags: [], lost_reason: "", won_reason: "",
        },
        { onSuccess, onError },
      );
    }
  }

  const stages = isEdit ? fullPipeline?.stages ?? [] : pipeline?.stages ?? [];

  return (
    <Modal
      open
      onClose={onClose}
      title={isEdit ? "Edit deal" : "New deal"}
      width="32rem"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={pending}>Cancel</Button>
          <Button
            variant="primary"
            onClick={save}
            disabled={pending || !title.trim() || (!isEdit && (!domain || !stageId))}
          >
            {pending ? "Saving…" : "Save"}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <label className="block">
          <span className="mb-1 flex items-center gap-1 text-11 text-fg-muted">Title <span className="text-danger">*</span></span>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Acme Corp — enterprise license" autoFocus />
        </label>

        {!isEdit && (
          <>
            <label className="block">
              <span className="mb-1 flex items-center gap-1 text-11 text-fg-muted">Company <span className="text-danger">*</span></span>
              <div className="relative">
                <DebouncedInput
                  value={domain ? companyName : q}
                  onChange={(v) => { setQ(v); setDomain(""); }}
                  placeholder="Search company…"
                  className="w-full"
                />
                {q && !domain && search && search.items.length > 0 && (
                  <div className="absolute z-10 mt-1 w-full rounded-md border border-line bg-raised py-1 shadow-lg">
                    {search.items.map((c) => (
                      <button
                        key={c.company_domain}
                        type="button"
                        onClick={() => { setDomain(c.company_domain); setCompanyName(c.company_name); setQ(""); }}
                        className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left text-12 hover:bg-control"
                      >
                        <span className="truncate text-fg">{c.company_name}</span>
                        <span className="ml-auto shrink-0 truncate text-11 text-fg-subtle">{c.company_domain}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </label>
            <label className="block">
              <span className="mb-1 block text-11 text-fg-muted">Stage</span>
              <Select value={stageId} onChange={(e) => setStageId(e.target.value ? Number(e.target.value) : "")} className="w-full">
                {stages.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </Select>
            </label>
          </>
        )}

        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="mb-1 block text-11 text-fg-muted">Value</span>
            <Input type="number" min="0" value={value} onChange={(e) => setValue(e.target.value)} placeholder="50000" />
          </label>
          <label className="block">
            <span className="mb-1 block text-11 text-fg-muted">Currency</span>
            <Select value={currency} onChange={(e) => setCurrency(e.target.value)} className="w-full">
              {DEAL_CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </Select>
          </label>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="mb-1 block text-11 text-fg-muted">Probability (%)</span>
            <Input type="number" min="0" max="100" value={probability} onChange={(e) => setProbability(e.target.value)} placeholder="Uses stage default" />
          </label>
          <label className="block">
            <span className="mb-1 block text-11 text-fg-muted">Expected close</span>
            <Input type="date" value={expectedClose} onChange={(e) => setExpectedClose(e.target.value)} />
          </label>
        </div>

        <label className="block">
          <span className="mb-1 block text-11 text-fg-muted">Forecast category</span>
          <Select value={forecastCategory} onChange={(e) => setForecastCategory(e.target.value)} className="w-full">
            {DEAL_FORECAST_CATEGORIES.map((c) => <option key={c} value={c}>{enumLabel(c)}</option>)}
          </Select>
        </label>

        <label className="block">
          <span className="mb-1 block text-11 text-fg-muted">Notes</span>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="w-full resize-y rounded-md border border-line bg-control px-2.5 py-1.5 text-13 text-fg outline-none focus:border-accent"
          />
        </label>
      </div>
    </Modal>
  );
}
