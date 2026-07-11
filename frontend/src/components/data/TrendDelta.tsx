import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";

import { enumLabel } from "@/lib/format";

/** Renders a hiring-trend string with a directional glyph + semantic color. */
export function TrendDelta({ trend }: { trend?: string | null }) {
  const t = (trend ?? "").toLowerCase();
  const label = enumLabel(trend);

  if (/(up|grow|increas|accel|surg|expand)/.test(t)) {
    return (
      <span className="inline-flex items-center gap-0.5 text-12 text-positive">
        <ArrowUpRight size={13} />
        {label}
      </span>
    );
  }
  if (/(down|declin|decreas|slow|contract|freeze)/.test(t)) {
    return (
      <span className="inline-flex items-center gap-0.5 text-12 text-danger">
        <ArrowDownRight size={13} />
        {label}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-0.5 text-12 text-fg-muted">
      <ArrowRight size={13} className="text-fg-subtle" />
      {label}
    </span>
  );
}
