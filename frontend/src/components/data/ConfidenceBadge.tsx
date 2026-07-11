import { cx } from "@/lib/cx";

type Meta = { label: string; full: string; color: string };

// Confidence in a lead score = how many of the 3 engine signals (opportunity /
// demand / decision-makers) actually backed it. Lets a thin-evidence A+ be told
// apart from a fully-backed one.
const META: Record<string, Meta> = {
  high: { label: "High", full: "High", color: "var(--ok, #3fb950)" },
  medium: { label: "Med", full: "Medium", color: "var(--warn, #d2a106)" },
  low: { label: "Low", full: "Low", color: "var(--fg-subtle, #8b949e)" },
};

/** Confidence pill, colored by signal coverage (high / medium / low). */
export function ConfidenceBadge({
  confidence,
  coverage,
  showLabel = true,
  className,
}: {
  confidence?: string | null;
  coverage?: number | null;
  showLabel?: boolean;
  className?: string;
}) {
  const m = META[(confidence ?? "low").toLowerCase()] ?? META.low;
  const title =
    coverage != null ? `${m.full} confidence · ${coverage} of 3 signals` : `${m.full} confidence`;
  return (
    <span
      title={title}
      className={cx(
        "inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-11 leading-none",
        className,
      )}
      style={{
        color: m.color,
        borderColor: `color-mix(in srgb, ${m.color} 40%, transparent)`,
        background: `color-mix(in srgb, ${m.color} 12%, transparent)`,
      }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: m.color }} />
      {showLabel ? m.label : null}
    </span>
  );
}
