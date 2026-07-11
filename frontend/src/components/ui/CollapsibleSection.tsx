import { useId, type ReactNode } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { useSessionToggle } from "@/hooks/useSessionToggle";
import { cx } from "@/lib/cx";

/**
 * A `SectionPanel`-styled panel whose body collapses behind a clickable header
 * (chevron + title + optional count). Open/closed state is remembered for the
 * browser-tab session via `sessionKey`. Reduces page clutter for secondary
 * intelligence modules that should stay available but not always-visible.
 */
export function CollapsibleSection({
  sessionKey,
  title,
  icon,
  count,
  defaultOpen = false,
  actions,
  children,
  className,
  bodyClassName,
}: {
  /** Stable key used to remember open/closed state for the tab session. */
  sessionKey: string;
  title: ReactNode;
  icon?: ReactNode;
  /** Rendered as "(count)" next to the title (e.g. Leadership Signals (8)). */
  count?: number;
  defaultOpen?: boolean;
  /** Optional trailing controls in the header (kept clickable, outside the toggle). */
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  const [open, toggle] = useSessionToggle(sessionKey, defaultOpen);
  const bodyId = useId();
  return (
    <section className={cx("panel overflow-hidden", className)}>
      <header className={cx("flex h-10 items-center justify-between gap-3", open && "border-b border-line")}>
        <button
          type="button"
          onClick={toggle}
          aria-expanded={open}
          aria-controls={bodyId}
          className="flex h-full flex-1 items-center gap-2 px-3.5 text-13 font-medium text-fg hover:bg-raised"
        >
          <span className="text-fg-subtle">
            {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
          </span>
          {icon && <span className="text-fg-subtle">{icon}</span>}
          <span>{title}</span>
          {typeof count === "number" && <span className="font-normal text-fg-subtle">({count})</span>}
        </button>
        {actions && <div className="flex items-center gap-1.5 pr-3.5">{actions}</div>}
      </header>
      {open && (
        <div id={bodyId} className={cx("p-3.5", bodyClassName)}>
          {children}
        </div>
      )}
    </section>
  );
}
