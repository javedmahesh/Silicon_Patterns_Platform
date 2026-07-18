import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { apiErrorMessage } from "@/lib/api/client";
import { cx } from "@/lib/cx";
import { enumLabel } from "@/lib/format";

export type EditField = {
  name: string;
  label: string;
  kind?: "text" | "textarea" | "select";
  options?: readonly string[];
  full?: boolean; // span both columns
};

const asStr = (v: unknown): string => (v == null ? "" : String(v));

const CONTROL =
  "h-8 w-full rounded-md border border-line bg-control px-2.5 text-13 text-fg focus:border-accent focus:outline-none";

/** Reusable admin edit form. Renders one control per field and submits only the
 *  fields that actually changed (a partial PATCH). Mount it conditionally (or with a
 *  `key`) so each record opens with fresh values. */
export function EditRecordModal({
  open,
  onClose,
  title,
  icon,
  fields,
  initial,
  pending,
  error,
  onSubmit,
  submitLabel = "Save changes",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  icon?: ReactNode;
  fields: readonly EditField[];
  initial: Record<string, unknown>;
  pending?: boolean;
  error?: unknown;
  onSubmit: (patch: Record<string, string>) => void;
  submitLabel?: string;
}) {
  const base: Record<string, string> = {};
  for (const f of fields) base[f.name] = asStr(initial[f.name]);
  const [form, setForm] = useState<Record<string, string>>(base);
  const set = (k: string, v: string) => setForm((s) => ({ ...s, [k]: v }));

  const submit = () => {
    const patch: Record<string, string> = {};
    for (const f of fields) if (form[f.name] !== base[f.name]) patch[f.name] = form[f.name];
    onSubmit(patch);
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={<span className="flex items-center gap-2">{icon}{title}</span>}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={pending}>
            {pending ? <Spinner size={13} /> : null}
            {submitLabel}
          </Button>
        </>
      }
    >
      <div className="grid grid-cols-2 gap-3">
        {fields.map((f) => (
          <label
            key={f.name}
            className={cx("block space-y-1", (f.full || f.kind === "textarea") && "col-span-2")}
          >
            <span className="text-12 text-fg-muted">{f.label}</span>
            {f.kind === "textarea" ? (
              <textarea
                value={form[f.name]}
                onChange={(e) => set(f.name, e.target.value)}
                rows={3}
                className={cx(CONTROL, "h-auto py-1.5")}
              />
            ) : f.kind === "select" ? (
              <select
                value={form[f.name]}
                onChange={(e) => set(f.name, e.target.value)}
                className={CONTROL}
              >
                <option value="">—</option>
                {(f.options ?? []).map((o) => (
                  <option key={o} value={o}>{enumLabel(o)}</option>
                ))}
              </select>
            ) : (
              <Input value={form[f.name]} onChange={(e) => set(f.name, e.target.value)} />
            )}
          </label>
        ))}
      </div>
      {error ? <p className="mt-3 text-12 text-danger">{apiErrorMessage(error)}</p> : null}
    </Modal>
  );
}
