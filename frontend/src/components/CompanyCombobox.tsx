import { useState } from "react";

import { Input } from "@/components/ui/Input";
import { useDebounce } from "@/hooks/useDebounce";
import { useCompanies } from "@/lib/api/queries";

/** Type-ahead for picking a canonical company_domain (merge target / alias target). */
export function CompanyCombobox({
  value,
  onChange,
  placeholder = "Search companies…",
}: {
  value: string;
  onChange: (domain: string) => void;
  placeholder?: string;
}) {
  const [term, setTerm] = useState(value);
  const [open, setOpen] = useState(false);
  const dq = useDebounce(term, 250);
  const enabled = dq.trim().length >= 2;
  const { data } = useCompanies({ q: enabled ? dq.trim() : undefined, page_size: 6 });
  const items = enabled ? (data?.items ?? []) : [];

  const select = (domain: string) => {
    onChange(domain);
    setTerm(domain);
    setOpen(false);
  };

  return (
    <div className="relative">
      <Input
        value={term}
        placeholder={placeholder}
        onChange={(e) => {
          setTerm(e.target.value);
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
      />
      {open && items.length > 0 && (
        <div className="panel absolute z-20 mt-1 max-h-56 w-full overflow-y-auto p-1">
          {items.map((c) => (
            <button
              key={c.company_domain}
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                select(c.company_domain);
              }}
              className="flex w-full items-center justify-between gap-2 rounded-sm px-2 py-1 text-left hover:bg-raised"
            >
              <span className="truncate text-12 text-fg">{c.company_name || c.company_domain}</span>
              <span className="shrink-0 text-11 text-fg-subtle">{c.company_domain}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
