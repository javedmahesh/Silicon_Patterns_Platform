import type { ComponentType } from "react";
import { Building2, Gauge, Megaphone } from "lucide-react";

import { EmptyState } from "@/components/ui/EmptyState";
import { enumLabel, fmtDate, fmtRelative, fmtScore } from "@/lib/format";
import type { CompanyProfile } from "@/lib/api/types";

type IconType = ComponentType<{ size?: number | string; className?: string }>;

interface Event {
  date: string | null;
  icon: IconType;
  title: string;
  meta?: string;
}

/** A dated feed synthesized across engines (no dedicated events endpoint). */
export function SignalTimeline({ profile }: { profile: CompanyProfile }) {
  const events: Event[] = [];

  for (const o of profile.opportunities) {
    events.push({
      date: o.published_date,
      icon: Megaphone,
      title: o.article_title || enumLabel(o.opportunity_type) || "Opportunity",
      meta: enumLabel(o.opportunity_type),
    });
  }
  if (profile.lead_score?.scored_at) {
    events.push({
      date: profile.lead_score.scored_at,
      icon: Gauge,
      title: `Lead scored — grade ${profile.lead_score.grade}`,
      meta: `Score ${fmtScore(profile.lead_score.lead_score)}`,
    });
  }
  if (profile.company.created_at) {
    events.push({
      date: profile.company.created_at,
      icon: Building2,
      title: "Added to the platform",
      meta: profile.company.source ? enumLabel(profile.company.source) : undefined,
    });
  }

  const rows = events
    .map((e) => ({ ...e, t: e.date ? new Date(e.date).getTime() : NaN }))
    .sort((a, b) => (Number.isNaN(b.t) ? -Infinity : b.t) - (Number.isNaN(a.t) ? -Infinity : a.t));

  if (rows.length === 0) {
    return (
      <EmptyState
        title="No timeline events"
        description="No dated signals have been recorded for this company yet."
      />
    );
  }

  return (
    <ol className="relative">
      {rows.map((e, i) => {
        const Icon = e.icon;
        return (
          <li key={i} className="relative flex gap-3 pb-4 last:pb-0">
            {i < rows.length - 1 && (
              <span className="absolute bottom-0 left-[11px] top-7 w-px bg-line" />
            )}
            <span className="z-10 mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full border border-line bg-raised text-fg-subtle">
              <Icon size={13} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-13 text-fg">{e.title}</span>
                <span className="shrink-0 text-11 text-fg-subtle" title={fmtDate(e.date)}>
                  {fmtRelative(e.date)}
                </span>
              </div>
              {e.meta && <div className="text-12 text-fg-subtle">{e.meta}</div>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
