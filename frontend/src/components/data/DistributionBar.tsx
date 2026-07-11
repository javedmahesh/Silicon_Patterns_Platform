export interface Segment {
  label: string;
  value: number;
  color: string; // css var / hex
}

/** A single stacked bar showing the proportions of labeled segments. */
export function DistributionBar({
  segments,
  showLegend = false,
  className,
}: {
  segments: Segment[];
  showLegend?: boolean;
  className?: string;
}) {
  const total = segments.reduce((a, s) => a + s.value, 0) || 1;
  return (
    <div className={className}>
      <div className="flex h-2 overflow-hidden rounded-sm bg-control">
        {segments.map(
          (s, i) =>
            s.value > 0 && (
              <div
                key={i}
                style={{ width: `${(s.value / total) * 100}%`, background: s.color }}
                title={`${s.label}: ${s.value}`}
              />
            ),
        )}
      </div>
      {showLegend && (
        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
          {segments.map((s, i) => (
            <span key={i} className="inline-flex items-center gap-1.5 text-11 text-fg-muted">
              <span className="h-2 w-2 rounded-[2px]" style={{ background: s.color }} />
              {s.label}
              <span className="tabular text-fg-subtle">{s.value}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
