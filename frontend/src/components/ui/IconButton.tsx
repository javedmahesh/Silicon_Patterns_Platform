import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cx } from "@/lib/cx";

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  size?: "sm" | "md";
  active?: boolean;
  /** Required — this button shows an icon only, so screen readers need a label. */
  "aria-label": string;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { size = "md", active, className, type = "button", ...props },
  ref,
) {
  const dim = size === "sm" ? "h-7 w-7" : "h-8 w-8";
  return (
    <button
      ref={ref}
      type={type}
      className={cx(
        "inline-grid place-items-center rounded-md border transition-colors duration-[var(--dur)]",
        "disabled:opacity-40 disabled:pointer-events-none",
        active
          ? "border-line bg-accent-weak text-accent"
          : "border-transparent text-fg-muted hover:bg-raised hover:text-fg",
        dim,
        className,
      )}
      {...props}
    />
  );
});
