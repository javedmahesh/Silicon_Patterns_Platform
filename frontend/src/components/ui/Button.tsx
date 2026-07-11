import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cx } from "@/lib/cx";

type Variant = "primary" | "default" | "ghost" | "danger";
type Size = "sm" | "md";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const base =
  "inline-flex items-center justify-center gap-1.5 rounded-md border font-medium whitespace-nowrap " +
  "transition-colors duration-[var(--dur)] disabled:opacity-50 disabled:pointer-events-none";

const variants: Record<Variant, string> = {
  primary: "bg-accent border-accent text-[#06101d] hover:bg-accent-strong",
  default: "bg-control border-line-strong text-fg hover:border-fg-subtle hover:bg-raised",
  ghost: "bg-transparent border-transparent text-fg-muted hover:text-fg hover:bg-raised",
  danger: "bg-transparent border-line-strong text-danger hover:border-danger hover:bg-danger/10",
};

const sizes: Record<Size, string> = {
  sm: "h-7 px-2.5 text-12",
  md: "h-8 px-3 text-13",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "default", size = "md", className, type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cx(base, variants[variant], sizes[size], className)}
      {...props}
    />
  );
});
