import { Fragment, type ReactNode } from "react";

import { cx } from "@/lib/cx";

export interface KVItem {
  label: string;
  value: ReactNode;
}

export function KeyValueGrid({ items, className }: { items: KVItem[]; className?: string }) {
  return (
    <dl
      className={cx(
        "grid grid-cols-[minmax(84px,auto)_1fr] gap-x-3 gap-y-2 text-12",
        className,
      )}
    >
      {items.map((it, i) => (
        <Fragment key={i}>
          <dt className="text-fg-subtle">{it.label}</dt>
          <dd className="min-w-0 break-words text-fg">{it.value}</dd>
        </Fragment>
      ))}
    </dl>
  );
}
