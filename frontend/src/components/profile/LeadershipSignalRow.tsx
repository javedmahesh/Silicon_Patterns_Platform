import { useState } from "react";
import { ExternalLink, Newspaper } from "lucide-react";

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

const PRIORITY_TONE: Record<string, Tone> = { high: "danger", medium: "warning", low: "neutral" };

/** ``source`` is a feeder id, not an engine name — "blog_event" covers the Blog
 * Crawler, company-news, AND any RSS/Google-Alerts article via the News Collection
 * Engine. Provenance for which one is the linked article/opportunity, not this label. */
function sourceLabel(source: string): string {
  return source === "linkedin_history" ? "via LinkedIn" : source === "blog_event" ? "via news/article" : "";
}

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

/** One person-level director+ leadership-movement signal.
 *  ``onDelete`` (admin-provided) renders an inline delete control with a confirm. */
export function LeadershipSignalRow({
  sig,
  showCompany = false,
  onDelete,
  onEdit,
  onViewSource,
}: {
  sig: LeadershipSignalOut;
  showCompany?: boolean;
  onDelete?: (signalId: string) => void;
  /** Admin-provided: opens the edit form for this signal. */
  onEdit?: (sig: LeadershipSignalOut) => void;
  /** Opens the source article/opportunity for a news/blog-derived signal
   *  (``sig.source_ref`` is an opportunity id for ``source === "blog_event"``). */
  onViewSource?: (opportunityId: string) => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const age = ageLabel(sig.event_age_days);
  const meta = [
    sig.from_title ? `was ${sig.from_title}` : "",
    showCompany && sig.company_name ? sig.company_name : "",
    sig.geography,
    sourceLabel(sig.source),
  ].filter(Boolean);
  const canViewSource = Boolean(onViewSource && sig.source === "blog_event" && sig.source_ref);

  return (
    <div className="flex items-start gap-3 py-2.5">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={TONE[sig.movement_type] ?? "neutral"}>{enumLabel(sig.movement_type)}</Badge>
          {sig.seniority_band && (
            <span className="text-11 text-fg-subtle">{enumLabel(sig.seniority_band)}</span>
          )}
          <ConfidenceBadge confidence={sig.confidence} showLabel={false} />
          {sig.priority_tier === "high" && (
            <Badge tone={PRIORITY_TONE[sig.priority_tier]}>High priority</Badge>
          )}
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
      <div className="flex shrink-0 items-center gap-2">
        {canViewSource && (
          <button
            type="button"
            onClick={() => onViewSource!(sig.source_ref)}
            className="text-fg-subtle hover:text-accent"
            title="View source article"
          >
            <Newspaper size={14} />
          </button>
        )}
        {sig.linkedin_url && (
          <a
            href={sig.linkedin_url}
            target="_blank"
            rel="noreferrer"
            className="text-fg-subtle hover:text-accent"
            title="Open LinkedIn profile"
          >
            <ExternalLink size={14} />
          </a>
        )}
        {onEdit && !confirming && (
          <button
            type="button"
            onClick={() => onEdit(sig)}
            className="text-11 text-fg-subtle hover:text-accent"
            title="Edit this signal (admin)"
          >
            Edit
          </button>
        )}
        {onDelete &&
          (confirming ? (
            <span className="inline-flex items-center gap-1.5 text-11">
              <button type="button" onClick={() => onDelete(sig.signal_id)} className="text-danger hover:underline">
                Confirm
              </button>
              <button type="button" onClick={() => setConfirming(false)} className="text-fg-subtle hover:underline">
                Cancel
              </button>
            </span>
          ) : (
            <button
              type="button"
              onClick={() => setConfirming(true)}
              className="text-11 text-fg-subtle hover:text-danger"
              title="Delete this signal (admin)"
            >
              Delete
            </button>
          ))}
      </div>
    </div>
  );
}
