import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { Input, Select } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import { useCompanies, useCsAccountMutations } from "@/lib/api/queries";
import { CS_ACCOUNT_STATUSES, CS_ACCOUNT_TIERS, CS_LIFECYCLE_STAGES, type CsAccountOut } from "@/lib/api/types";
import { enumLabel } from "@/lib/format";

export function AccountFormModal({ account, onClose }: { account?: CsAccountOut; onClose: () => void }) {
  const isEdit = Boolean(account);
  const [name, setName] = useState(account?.name ?? "");
  const [q, setQ] = useState("");
  const [domain, setDomain] = useState(account?.company_domain ?? "");
  const [companyName, setCompanyName] = useState("");
  const [status, setStatus] = useState(account?.status ?? "active");
  const [tier, setTier] = useState(account?.tier ?? "mid_market");
  const [lifecycleStage, setLifecycleStage] = useState(account?.lifecycle_stage ?? "customer");
  const [arr, setArr] = useState(account ? String(account.arr) : "");
  const [renewalDate, setRenewalDate] = useState(account?.renewal_date?.slice(0, 10) ?? "");
  const [industry, setIndustry] = useState(account?.industry ?? "");

  const { data: search } = useCompanies({ q, page_size: 6 });
  const { create, patch } = useCsAccountMutations();
  const pending = create.isPending || patch.isPending;

  function save() {
    if (!name.trim()) return;
    const shared = {
      status, tier, lifecycle_stage: lifecycleStage, industry: industry.trim(),
      arr: arr.trim() ? Number(arr) : 0,
      renewal_date: renewalDate ? new Date(renewalDate).toISOString() : null,
    };
    const onSuccess = () => { toast(isEdit ? "Account updated" : "Account created", "positive"); onClose(); };
    const onError = (e: unknown) => toast(apiErrorMessage(e), "danger");
    if (isEdit) {
      patch.mutate({ id: account!.id, body: { name: name.trim(), ...shared } }, { onSuccess, onError });
    } else {
      create.mutate(
        {
          name: name.trim(),
          company_domain: domain || null,
          ...shared,
          contract_value: 0,
          currency: "USD",
          mrr: 0,
          notes: "",
          tags: [],
        },
        { onSuccess, onError },
      );
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={isEdit ? "Edit account" : "New account"}
      width="32rem"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={pending}>Cancel</Button>
          <Button variant="primary" onClick={save} disabled={!name.trim() || pending}>{pending ? "Saving…" : "Save"}</Button>
        </>
      }
    >
      <div className="space-y-3">
        <label className="block">
          <span className="mb-1 flex items-center gap-1 text-11 text-fg-muted">Account name <span className="text-danger">*</span></span>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Corp" autoFocus />
        </label>

        {!isEdit && (
          <label className="block">
            <span className="mb-1 block text-11 text-fg-muted">Linked company (optional)</span>
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
        )}

        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="mb-1 block text-11 text-fg-muted">Status</span>
            <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-full">
              {CS_ACCOUNT_STATUSES.map((s) => <option key={s} value={s}>{enumLabel(s)}</option>)}
            </Select>
          </label>
          <label className="block">
            <span className="mb-1 block text-11 text-fg-muted">Tier</span>
            <Select value={tier} onChange={(e) => setTier(e.target.value)} className="w-full">
              {CS_ACCOUNT_TIERS.map((t) => <option key={t} value={t}>{enumLabel(t)}</option>)}
            </Select>
          </label>
        </div>

        <label className="block">
          <span className="mb-1 block text-11 text-fg-muted">Lifecycle stage</span>
          <Select value={lifecycleStage} onChange={(e) => setLifecycleStage(e.target.value)} className="w-full">
            {CS_LIFECYCLE_STAGES.map((s) => <option key={s} value={s}>{enumLabel(s)}</option>)}
          </Select>
        </label>

        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="mb-1 block text-11 text-fg-muted">ARR</span>
            <Input type="number" min="0" value={arr} onChange={(e) => setArr(e.target.value)} placeholder="120000" />
          </label>
          <label className="block">
            <span className="mb-1 block text-11 text-fg-muted">Renewal date</span>
            <Input type="date" value={renewalDate} onChange={(e) => setRenewalDate(e.target.value)} />
          </label>
        </div>

        <label className="block">
          <span className="mb-1 block text-11 text-fg-muted">Industry</span>
          <Input value={industry} onChange={(e) => setIndustry(e.target.value)} placeholder="Semiconductors" />
        </label>
      </div>
    </Modal>
  );
}
