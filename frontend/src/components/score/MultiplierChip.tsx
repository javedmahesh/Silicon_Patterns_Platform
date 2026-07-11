import { cx } from "@/lib/cx";

/** A fit multiplier (region / prospect / tier). Color signals lift vs. penalty. */
export function MultiplierChip({
  label,
  value,
  emphasis = false,
}: {
  label: string;
  value: number;
  emphasis?: boolean;
}) {
  const tone = value < 1 ? "text-warning" : value > 1 ? "text-positive" : "text-fg-muted";
  return (
    <span
      className={cx(
        "inline-flex h-6 items-center gap-1 rounded-sm border px-1.5 text-12",
        emphasis ? "border-line-strong bg-raised" : "border-line bg-control",
      )}
    >
      <span className="text-fg-subtle">{label}</span>
      <span className={cx("tabular", tone)}>×{value.toFixed(2)}</span>
    </span>
  );
}
