import type { ReactNode } from "react";

import { cx } from "@/lib/cx";

/** A titled, hairline-bordered panel — the primary content container. */
export function SectionPanel({
  id,
  title,
  icon,
  actions,
  children,
  bodyClassName,
  className,
}: {
  id?: string;
  title?: ReactNode;
  icon?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  bodyClassName?: string;
  className?: string;
}) {
  return (
    <section id={id} className={cx("panel overflow-hidden", className)}>
      {(title || actions) && (
        <header className="flex h-10 items-center justify-between gap-3 border-b border-line px-3.5">
          <div className="flex items-center gap-2 text-13 font-medium text-fg">
            {icon && <span className="text-fg-subtle">{icon}</span>}
            {title}
          </div>
          {actions && <div className="flex items-center gap-1.5">{actions}</div>}
        </header>
      )}
      <div className={cx("p-3.5", bodyClassName)}>{children}</div>
    </section>
  );
}
