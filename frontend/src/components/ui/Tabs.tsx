import type { ReactNode } from "react";

import { cx } from "@/lib/cx";

export interface TabDef<T extends string> {
  id: T;
  label: ReactNode;
  count?: number;
}

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
  className,
}: {
  tabs: TabDef<T>[];
  active: T;
  onChange: (id: T) => void;
  className?: string;
}) {
  return (
    <div className={cx("flex items-center gap-1 overflow-x-auto border-b border-line", className)} role="tablist">
      {tabs.map((t) => {
        const selected = active === t.id;
        return (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(t.id)}
            className={cx(
              "relative -mb-px flex h-9 items-center gap-1.5 whitespace-nowrap px-3 text-13 transition-colors",
              selected ? "text-fg" : "text-fg-muted hover:text-fg",
            )}
          >
            {t.label}
            {typeof t.count === "number" && (
              <span className="tabular text-11 text-fg-subtle">{t.count}</span>
            )}
            {selected && <span className="absolute inset-x-0 -bottom-px h-0.5 bg-accent" />}
          </button>
        );
      })}
    </div>
  );
}
