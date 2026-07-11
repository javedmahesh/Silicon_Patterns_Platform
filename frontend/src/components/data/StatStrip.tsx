import type { ReactNode } from "react";

import { cx } from "@/lib/cx";

export interface Stat {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  accent?: string; // optional value color (css var / hex)
}

/** A thin row of KPIs — deliberately not big colorful cards. */
export function StatStrip({ stats, className }: { stats: Stat[]; className?: string }) {
  return (
    <div
      className={cx(
        "panel grid grid-cols-2 divide-x divide-y divide-line sm:grid-cols-3 sm:divide-y-0 lg:grid-cols-6",
        className,
      )}
    >
      {stats.map((s, i) => (
        <div key={i} className="px-3.5 py-2.5">
          <div className="text-11 uppercase tracking-wide text-fg-subtle">{s.label}</div>
          <div className="tabular mt-1 text-18 leading-none text-fg" style={{ color: s.accent }}>
            {s.value}
          </div>
          {s.hint && <div className="mt-1 text-11 text-fg-subtle">{s.hint}</div>}
        </div>
      ))}
    </div>
  );
}
