import { ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";

import { GradeBadge } from "@/components/data/GradeBadge";
import { KeyValueGrid, type KVItem } from "@/components/profile/KeyValueGrid";
import { Button } from "@/components/ui/Button";
import { FollowUpButton, PinButton, WatchButton } from "@/components/workspace/WorkspaceButtons";
import { domainHref, fmtInt, fmtScore, monogram } from "@/lib/format";

/** Drawer body for a company-centric row — identity, score, facts, workspace
 *  actions, and a link into the full profile. Shared by the list pages. */
export function CompanyPeek({
  domain,
  name,
  grade,
  score,
  rank,
  items = [],
}: {
  domain: string;
  name: string;
  grade?: string | null;
  score?: number | null;
  rank?: number | null;
  items?: KVItem[];
}) {
  const href = domainHref(domain);
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-md border border-line bg-control text-15 text-fg-muted">
          {monogram(name, domain)}
        </div>
        <div className="min-w-0">
          <div className="truncate text-15 text-fg">{name || domain}</div>
          {href ? (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-12 text-fg-muted hover:text-accent"
            >
              {domain}
              <ExternalLink size={11} />
            </a>
          ) : (
            <span className="text-12 text-fg-muted">{domain}</span>
          )}
        </div>
      </div>

      {(grade || score != null) && (
        <div className="flex items-center gap-3 rounded-md border border-line bg-raised px-3 py-2">
          <GradeBadge grade={grade} size="lg" />
          <div>
            <div className="tabular text-18 leading-none text-fg">{fmtScore(score)}</div>
            {rank != null && <div className="mt-1 text-11 text-fg-subtle">Priority rank #{fmtInt(rank)}</div>}
          </div>
        </div>
      )}

      {items.length > 0 && <KeyValueGrid items={items} />}

      <div className="flex flex-wrap gap-1.5">
        <WatchButton domain={domain} size="sm" />
        <PinButton domain={domain} size="sm" />
        <FollowUpButton domain={domain} size="sm" />
      </div>

      <Link to={`/companies/${encodeURIComponent(domain)}`} className="block">
        <Button variant="primary" className="w-full">
          Open profile
        </Button>
      </Link>
    </div>
  );
}
