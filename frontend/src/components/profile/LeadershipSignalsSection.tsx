import { UserCog } from "lucide-react";

import { EmptyState } from "@/components/ui/EmptyState";
import { LeadershipSignalRow } from "./LeadershipSignalRow";
import type { LeadershipSignalOut } from "@/lib/api/types";

/** Bucket signals by company, preserving the (recency-ordered) first-seen order. */
function groupByCompanyName(signals: LeadershipSignalOut[]): { company: string; items: LeadershipSignalOut[] }[] {
  const order: string[] = [];
  const buckets = new Map<string, LeadershipSignalOut[]>();
  for (const s of signals) {
    const key = s.company_name || s.company_domain || "Unresolved company";
    if (!buckets.has(key)) {
      buckets.set(key, []);
      order.push(key);
    }
    buckets.get(key)!.push(s);
  }
  return order.map((company) => ({ company, items: buckets.get(company)! }));
}

/** A feed of person-level director+ leadership-movement signals. */
export function LeadershipSignalsSection({
  signals,
  groupByCompany = false,
  showCompany = false,
  emptyHint,
  onDelete,
  onEdit,
  onViewSource,
}: {
  signals: LeadershipSignalOut[];
  /** Group rows under a per-company header (for the cross-company directory feed). */
  groupByCompany?: boolean;
  showCompany?: boolean;
  emptyHint?: string;
  /** Admin-provided: enables a per-row delete control. */
  onDelete?: (signalId: string) => void;
  /** Admin-provided: enables a per-row edit control. */
  onEdit?: (sig: LeadershipSignalOut) => void;
  /** Opens the source article/opportunity for a news/blog-derived signal. */
  onViewSource?: (opportunityId: string) => void;
}) {
  if (signals.length === 0) {
    return (
      <EmptyState
        icon={<UserCog size={20} />}
        title="No leadership signals"
        description={
          emptyHint ??
          "No director-level+ moves — hires, departures, promotions, board or founder changes — detected in the recent window."
        }
      />
    );
  }

  if (!groupByCompany) {
    return (
      <div className="divide-y divide-line">
        {signals.map((s) => (
          <LeadershipSignalRow key={s.signal_id} sig={s} showCompany={showCompany} onDelete={onDelete} onEdit={onEdit} onViewSource={onViewSource} />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {groupByCompanyName(signals).map(({ company, items }) => (
        <div key={company}>
          <div className="flex items-center gap-2 px-0.5 pb-0.5 text-11 font-medium uppercase tracking-wide text-fg-subtle">
            <span className="truncate">{company}</span>
            <span className="shrink-0 normal-case tracking-normal">· {items.length}</span>
          </div>
          <div className="divide-y divide-line">
            {items.map((s) => (
              <LeadershipSignalRow key={s.signal_id} sig={s} showCompany={false} onDelete={onDelete} onEdit={onEdit} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
