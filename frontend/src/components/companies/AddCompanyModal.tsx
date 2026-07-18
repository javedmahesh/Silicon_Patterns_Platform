import { useState, type ReactNode } from "react";
import { Building2 } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { apiErrorMessage } from "@/lib/api/client";
import { useCreateCompany } from "@/lib/api/queries";
import type { CompanySummary } from "@/lib/api/types";

const EMPTY = { company_name: "", company_domain: "", country: "", website: "", industry_category: "" };

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="text-12 text-fg-muted">{label}</span>
      {children}
      {hint && <span className="block text-11 text-fg-subtle">{hint}</span>}
    </label>
  );
}

/** Manually add a company to the Universe (manager+). The backend normalizes the
 *  domain + derives the join key, so a hand-added company dedupes like an ingested one. */
export function AddCompanyModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated?: (company: CompanySummary) => void;
}) {
  const [form, setForm] = useState(EMPTY);
  const create = useCreateCompany();
  const set = (k: keyof typeof EMPTY, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const valid = form.company_name.trim() !== "" && form.company_domain.trim() !== "";

  const close = () => {
    setForm(EMPTY);
    create.reset();
    onClose();
  };

  const submit = () =>
    create.mutate(form, {
      onSuccess: (company) => {
        onCreated?.(company);
        setForm(EMPTY);
        create.reset();
        onClose();
      },
    });

  return (
    <Modal
      open={open}
      onClose={close}
      title={
        <span className="flex items-center gap-2">
          <Building2 size={15} /> Add company
        </span>
      }
      footer={
        <>
          <Button variant="ghost" onClick={close}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={!valid || create.isPending}>
            {create.isPending ? <Spinner size={13} /> : null}
            Add company
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <Field label="Company name *">
          <Input value={form.company_name} onChange={(e) => set("company_name", e.target.value)} placeholder="Acme Semiconductor" />
        </Field>
        <Field label="Domain *" hint="Any URL or bare domain — it’s normalized to the join key (e.g. acme.com).">
          <Input value={form.company_domain} onChange={(e) => set("company_domain", e.target.value)} placeholder="acme.com" />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Country">
            <Input value={form.country} onChange={(e) => set("country", e.target.value)} placeholder="USA" />
          </Field>
          <Field label="Industry">
            <Input value={form.industry_category} onChange={(e) => set("industry_category", e.target.value)} placeholder="Semiconductors" />
          </Field>
        </div>
        <Field label="Website">
          <Input value={form.website} onChange={(e) => set("website", e.target.value)} placeholder="https://acme.com" />
        </Field>

        {create.isError && <p className="text-12 text-danger">{apiErrorMessage(create.error)}</p>}
      </div>
    </Modal>
  );
}
