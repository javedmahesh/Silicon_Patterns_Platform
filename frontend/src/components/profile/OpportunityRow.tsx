import { ExternalLink } from "lucide-react";

import { NumericCell } from "@/components/data/NumericCell";
import { Badge } from "@/components/ui/Badge";
import { enumLabel, fmtRelative, fmtScore } from "@/lib/format";
import type { OpportunityOut } from "@/lib/api/types";

export function OpportunityRow({ opp }: { opp: OpportunityOut }) {
  const title = opp.article_title || enumLabel(opp.opportunity_type) || "Opportunity";
  const score = opp.effective_opportunity_score || opp.opportunity_score;
  return (
    <div className="flex items-start gap-3 py-2.5">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          {opp.opportunity_type && <Badge tone="accent">{enumLabel(opp.opportunity_type)}</Badge>}
          {opp.opportunity_category && (
            <span className="text-11 text-fg-subtle">{enumLabel(opp.opportunity_category)}</span>
          )}
          <span className="text-11 text-fg-subtle">· {fmtRelative(opp.published_date)}</span>
        </div>
        <div className="mt-1 text-13 text-fg">
          {opp.article_url ? (
            <a
              href={opp.article_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-start gap-1 hover:text-accent"
            >
              {title}
              <ExternalLink size={12} className="mt-0.5 shrink-0 text-fg-subtle" />
            </a>
          ) : (
            title
          )}
        </div>
        {opp.summary && <p className="mt-0.5 line-clamp-2 text-12 text-fg-subtle">{opp.summary}</p>}
        {opp.technology_focus && (
          <div className="mt-1 text-11 text-fg-subtle">{opp.technology_focus}</div>
        )}
      </div>
      <div className="shrink-0 text-right">
        <div className="text-11 text-fg-subtle">Score</div>
        <NumericCell className="text-13 text-fg">{fmtScore(score, 0)}</NumericCell>
      </div>
    </div>
  );
}
