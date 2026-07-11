import { Award, ExternalLink } from "lucide-react";

import { EmptyState } from "@/components/ui/EmptyState";
import { fmtRelative } from "@/lib/format";
import type { CompanyProfile, OpportunityOut } from "@/lib/api/types";

/** Annual-list appearances (opportunity_type === "ANNUAL_LIST") for a company (Change_04),
 *  presented as recognition/credentials rather than as raw "opportunities". */
export function RecognitionCard({ profile }: { profile: CompanyProfile }) {
  const lists: OpportunityOut[] = (profile.opportunities ?? []).filter(
    (o) => o.opportunity_type === "ANNUAL_LIST",
  );

  if (lists.length === 0) {
    return (
      <EmptyState
        icon={<Award size={20} />}
        title="No list appearances"
        description="This company hasn't been recorded on a tracked annual list yet."
      />
    );
  }

  return (
    <ul className="divide-y divide-line">
      {lists.map((o) => {
        const rank = (o.company_news_signal || "").replace(/^Rank:\s*/i, "").trim();
        return (
          <li key={o.opportunity_id} className="flex items-center justify-between gap-3 py-2">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-13 text-fg">
                <Award size={13} className="shrink-0 text-accent" />
                <span className="truncate">{o.opportunity_category || o.article_title}</span>
              </div>
              {o.published_date && (
                <div className="mt-0.5 text-11 text-fg-subtle">{fmtRelative(o.published_date)}</div>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {rank && <span className="tabular text-12 text-fg-muted">#{rank}</span>}
              {o.article_url && (
                <a
                  href={o.article_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-fg-subtle hover:text-accent"
                >
                  <ExternalLink size={12} />
                </a>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
