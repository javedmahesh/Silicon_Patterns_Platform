import { Check, Minus } from "lucide-react";

import { cx } from "@/lib/cx";
import { enumLabel, fmtInt, fmtRelative } from "@/lib/format";
import type { CompanyProfile } from "@/lib/api/types";

/** Which of the five engines contributed data for this company, + last scored. */
export function DataCoverage({ profile }: { profile: CompanyProfile }) {
  const c = profile.counts;
  const engines = [
    {
      name: "Industry Discovery",
      on: true,
      detail: profile.company.source ? enumLabel(profile.company.source) : "Classified",
    },
    { name: "Blog Crawler", on: c.opportunities > 0, detail: `${fmtInt(c.opportunities)} opportunities` },
    {
      name: "Career Scraper",
      on: c.demand_signal > 0 || c.jobs > 0,
      detail: `${fmtInt(c.jobs)} jobs`,
    },
    { name: "LinkedIn Scraper", on: c.decision_makers > 0, detail: `${fmtInt(c.decision_makers)} contacts` },
  ];

  return (
    <div className="space-y-2">
      {engines.map((e) => (
        <div key={e.name} className="flex items-center gap-2.5">
          <span
            className={cx(
              "grid h-4 w-4 shrink-0 place-items-center rounded-full",
              e.on ? "bg-positive/15 text-positive" : "bg-control text-fg-subtle",
            )}
          >
            {e.on ? <Check size={11} /> : <Minus size={11} />}
          </span>
          <span className={cx("flex-1 text-12", e.on ? "text-fg" : "text-fg-subtle")}>{e.name}</span>
          <span className="text-11 text-fg-subtle">{e.on ? e.detail : "No data"}</span>
        </div>
      ))}
      <div className="border-t border-line pt-2 text-11 text-fg-subtle">
        Last scored:{" "}
        {profile.lead_score?.scored_at ? fmtRelative(profile.lead_score.scored_at) : "never"}
      </div>
    </div>
  );
}
