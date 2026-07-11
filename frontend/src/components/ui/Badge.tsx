import type { ReactNode } from "react";
import { X } from "lucide-react";

import { cx } from "@/lib/cx";

type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";

const tones: Record<Tone, string> = {
  neutral: "bg-control text-fg-muted border-line",
  accent: "bg-accent-weak text-accent border-line",
  positive: "bg-positive/10 text-positive border-positive/30",
  warning: "bg-warning/10 text-warning border-warning/30",
  danger: "bg-danger/10 text-danger border-danger/30",
};

export function Badge({
  children,
  tone = "neutral",
  title,
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  title?: string;
  className?: string;
}) {
  return (
    <span
      title={title}
      className={cx(
        "inline-flex h-[18px] items-center gap-1 rounded-sm border px-1.5 text-11 font-medium leading-none",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** A filter token with an optional remove affordance. */
export function Chip({
  children,
  onRemove,
  className,
}: {
  children: ReactNode;
  onRemove?: () => void;
  className?: string;
}) {
  return (
    <span
      className={cx(
        "inline-flex h-6 items-center gap-1 rounded-sm border border-line bg-control px-1.5 text-12 text-fg-muted",
        className,
      )}
    >
      {children}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="-mr-0.5 grid h-4 w-4 place-items-center rounded-sm text-fg-subtle hover:bg-raised hover:text-fg"
          aria-label="Remove filter"
        >
          <X size={11} />
        </button>
      )}
    </span>
  );
}
