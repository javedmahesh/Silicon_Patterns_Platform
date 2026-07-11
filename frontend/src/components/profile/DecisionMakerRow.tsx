import type { ReactNode } from "react";
import { ExternalLink } from "lucide-react";

import { NumericCell } from "@/components/data/NumericCell";
import { Badge } from "@/components/ui/Badge";
import { cleanLocation, enumLabel, fmtScore, fullName } from "@/lib/format";
import type { DecisionMakerOut } from "@/lib/api/types";

export function DecisionMakerRow({
  dm,
  showScore = true,
  action,
}: {
  dm: DecisionMakerOut;
  showScore?: boolean;
  /** Optional trailing slot (e.g. a Contact button) rendered after the LinkedIn link. */
  action?: ReactNode;
}) {
  const initials =
    `${dm.first_name?.[0] ?? ""}${dm.last_name?.[0] ?? ""}`.toUpperCase() || "?";
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-control text-12 text-fg-muted">
        {initials}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="truncate text-13 text-fg">{fullName(dm.first_name, dm.last_name)}</span>
          {dm.seniority && <Badge>{enumLabel(dm.seniority)}</Badge>}
          {dm.influence_score != null && <Badge tone="accent">Infl {dm.influence_score}</Badge>}
          {dm.confidence_level && (
            <Badge tone={dm.confidence_level === "High" ? "positive" : dm.confidence_level === "Medium" ? "accent" : "neutral"}>
              {dm.confidence_level}
            </Badge>
          )}
        </div>
        <div className="truncate text-12 text-fg-subtle">
          {dm.current_title || dm.headline || "—"}
          {dm.department_class ? ` · ${dm.department_class}` : ""}
          {cleanLocation(dm.location) ? ` · ${cleanLocation(dm.location)}` : ""}
        </div>
      </div>
      {showScore && dm.match_score > 0 && (
        <div className="shrink-0 text-right">
          <div className="text-11 text-fg-subtle">Match</div>
          <NumericCell className="text-12 text-fg">{fmtScore(dm.match_score, 0)}</NumericCell>
        </div>
      )}
      {dm.linkedin_url && (
        <a
          href={dm.linkedin_url}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 text-fg-subtle hover:text-accent"
          title="Open LinkedIn profile"
        >
          <ExternalLink size={15} />
        </a>
      )}
      {action}
    </div>
  );
}
