import type { ReactNode } from "react";

import { cx } from "@/lib/cx";

export function PageHeader({
  title,
  subtitle,
  actions,
  children,
  className,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  /** Filter bar or tabs rendered under the title row, still inside the sticky header. */
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cx("flex flex-col gap-3 border-b border-line bg-base px-4 py-3", className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-18 text-fg">{title}</h1>
          {subtitle && <p className="mt-0.5 text-12 text-fg-muted">{subtitle}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      {children}
    </div>
  );
}
