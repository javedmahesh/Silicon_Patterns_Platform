import type { ReactNode } from "react";
import { X } from "lucide-react";

import { Select } from "@/components/ui/Input";
import { cx } from "@/lib/cx";
import type { Option } from "@/lib/constants";

export function FilterBar({
  children,
  activeCount = 0,
  onClear,
  className,
}: {
  children: ReactNode;
  activeCount?: number;
  onClear?: () => void;
  className?: string;
}) {
  return (
    <div className={cx("flex flex-wrap items-center gap-2", className)}>
      {children}
      {activeCount > 0 && onClear && (
        <button
          type="button"
          onClick={onClear}
          className="inline-flex items-center gap-1 text-12 text-fg-subtle hover:text-fg"
        >
          <X size={12} />
          Clear{activeCount > 1 ? ` (${activeCount})` : ""}
        </button>
      )}
    </div>
  );
}

/** A labeled dropdown whose empty value clears the filter. */
export function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Option[];
}) {
  return (
    <Select value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}>
      <option value="">{label}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </Select>
  );
}
