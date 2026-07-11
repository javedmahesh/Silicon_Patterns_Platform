import type { ReactNode } from "react";

import { cx } from "@/lib/cx";

/** Lightweight CSS-only tooltip (hover/focus). For dense UI hints, not menus. */
export function Tooltip({
  label,
  children,
  side = "top",
  className,
}: {
  label: ReactNode;
  children: ReactNode;
  side?: "top" | "bottom";
  className?: string;
}) {
  return (
    <span className={cx("group/tt relative inline-flex", className)}>
      {children}
      <span
        role="tooltip"
        className={cx(
          "pointer-events-none absolute left-1/2 z-50 hidden -translate-x-1/2 whitespace-nowrap",
          "rounded-sm border border-line bg-raised px-1.5 py-1 text-11 text-fg",
          "group-hover/tt:block",
          side === "top" ? "bottom-full mb-1" : "top-full mt-1",
        )}
      >
        {label}
      </span>
    </span>
  );
}
