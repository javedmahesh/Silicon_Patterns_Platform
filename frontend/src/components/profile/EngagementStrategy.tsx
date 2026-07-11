import { Lightbulb } from "lucide-react";

import { ConfidenceBadge } from "@/components/data/ConfidenceBadge";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import type { EngagementOut } from "@/lib/api/types";

/** The "Recommended Engagement Strategy" — a likely business need, the matching
 *  Silicon Patterns offering, a one-line pitch, confidence, and the evidence. */
export function EngagementStrategy({ engagement }: { engagement: EngagementOut | null }) {
  if (!engagement) {
    return (
      <EmptyState
        icon={<Lightbulb size={20} />}
        title="No recommendation yet"
        description="Not enough intelligence signals for this company to generate an engagement strategy."
      />
    );
  }
  const e = engagement;
  return (
    <div className="space-y-3">
      <div>
        <div className="flex items-center justify-between gap-2">
          <span className="text-11 uppercase tracking-wide text-fg-subtle">Likely business need</span>
          <span className="flex items-center gap-1.5">
            <ConfidenceBadge confidence={e.confidence_label} />
            <span className="text-11 text-fg-subtle">{e.confidence}/100</span>
          </span>
        </div>
        <p className="mt-1 text-13 text-fg">{e.business_need}</p>
      </div>

      <div>
        <span className="text-11 uppercase tracking-wide text-fg-subtle">Recommended offering</span>
        <div className="mt-1">
          <Badge tone="accent">{e.offering}</Badge>
        </div>
      </div>

      <div>
        <span className="text-11 uppercase tracking-wide text-fg-subtle">One-line sales pitch</span>
        <blockquote className="mt-1 border-l-2 border-accent pl-3 text-13 italic text-fg">
          “{e.pitch}”
        </blockquote>
      </div>

      {e.rationale.length > 0 && (
        <details className="text-fg-subtle">
          <summary className="cursor-pointer text-11 hover:text-fg">
            Why this pitch · {e.signals_used} signal{e.signals_used === 1 ? "" : "s"}
          </summary>
          <ul className="mt-1.5 space-y-1">
            {e.rationale.map((r, i) => (
              <li key={i} className="flex gap-1.5 text-11">
                <span aria-hidden>•</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
