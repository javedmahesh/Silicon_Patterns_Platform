import type { ReactNode } from "react";

import { cx } from "@/lib/cx";

/** Wraps a numeric value in the tabular monospaced treatment for column alignment. */
export function NumericCell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <span className={cx("tabular", className)}>{children}</span>;
}
