import { cx } from "@/lib/cx";
import { fmtScore } from "@/lib/format";
import { scoreVar } from "@/lib/grades";

/** Horizontal 0–max bar with an optional trailing tabular value. */
export function ScoreBar({
  value,
  max = 100,
  color,
  showValue = true,
  className,
}: {
  value?: number | null;
  max?: number;
  color?: string;
  showValue?: boolean;
  className?: string;
}) {
  const v = value ?? 0;
  const pct = Math.max(0, Math.min(100, (v / max) * 100));
  const fill = color ?? scoreVar(value);
  return (
    <div className={cx("flex items-center gap-2", className)}>
      <div className="relative h-1.5 flex-1 overflow-hidden rounded-sm bg-control">
        <div
          className="absolute inset-y-0 left-0 rounded-sm transition-[width] duration-300"
          style={{ width: `${pct}%`, background: fill }}
        />
      </div>
      {showValue && (
        <span className="tabular w-9 shrink-0 text-right text-12 text-fg-muted">
          {fmtScore(value)}
        </span>
      )}
    </div>
  );
}
