import { ExternalLink } from "lucide-react";

import { ConfidenceBadge } from "@/components/data/ConfidenceBadge";
import { Badge } from "@/components/ui/Badge";
import { enumLabel } from "@/lib/format";
import type { LeadershipSignalOut } from "@/lib/api/types";

type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";

/** Movement type → semantic colour (a hire/promotion is good news; a departure isn't). */
const TONE: Record<string, Tone> = {
  new_executive_hire: "positive",
  promotion: "positive",
  role_change: "accent",
  board_appointment: "accent",
  founder_change: "accent",
  executive_departure: "danger",
  executive_reshuffle: "warning",
};

/** Public: movement type → Badge tone (reused by the dashboard widget). */
export function movementTone(type: string): Tone {
  return TONE[type] ?? "neutral";
}

export function ageLabel(days: number): string {
  if (days < 0) return "";
  const mo = Math.round(days / 30);
  if (mo <= 0) return "this month";
  if (mo < 12) return `${mo}mo ago`;
  const years = mo / 12;
  return `${years % 1 === 0 ? years : years.toFixed(1)}y ago`;
}

/** One person-level director+ leadership-movement signal. */
export function LeadershipSignalRow({
  sig,
  showCompany = false,
}: {
  sig: LeadershipSignalOut;
  showCompany?: boolean;
}) {
  const age = ageLabel(sig.event_age_days);
  const meta = [
    sig.from_title ? `was ${sig.from_title}` : "",
    showCompany && sig.company_name ? sig.company_name : "",
    sig.source === "blog_event" ? "via Blog Crawler" : "via LinkedIn",
  ].filter(Boolean);

  return (
    <div className="flex items-start gap-3 py-2.5">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={TONE[sig.movement_type] ?? "neutral"}>{enumLabel(sig.movement_type)}</Badge>
          {sig.seniority_band && (
            <span className="text-11 text-fg-subtle">{enumLabel(sig.seniority_band)}</span>
          )}
          <ConfidenceBadge confidence={sig.confidence} showLabel={false} />
          {age && <span className="text-11 text-fg-subtle">· {age}</span>}
        </div>
        <div className="mt-1 truncate text-13 text-fg">
          <span className="font-medium">{sig.person_name}</span>
          {sig.to_title ? <span className="text-fg-muted"> — {sig.to_title}</span> : null}
        </div>
        {meta.length > 0 && (
          <div className="mt-0.5 truncate text-11 text-fg-subtle">{meta.join(" · ")}</div>
        )}
      </div>
      {sig.linkedin_url && (
        <a
          href={sig.linkedin_url}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 text-fg-subtle hover:text-accent"
          title="Open LinkedIn profile"
        >
          <ExternalLink size={14} />
        </a>
      )}
    </div>
  );
}
