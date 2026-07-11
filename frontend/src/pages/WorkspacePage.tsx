import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Eye, Flag, GitCompare, Pin, X } from "lucide-react";

import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { IconButton } from "@/components/ui/IconButton";
import { SectionPanel } from "@/components/ui/SectionPanel";
import { useWorkspace } from "@/hooks/useWorkspace";
import { fmtDate, fmtInt, monogram } from "@/lib/format";

function Row({
  domain,
  onRemove,
  children,
}: {
  domain: string;
  onRemove: () => void;
  children?: ReactNode;
}) {
  return (
    <div className="-mx-3.5 flex items-center gap-3 px-3.5 py-2 hover:bg-raised">
      <div className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-line bg-control text-11 text-fg-muted">
        {monogram(null, domain)}
      </div>
      <div className="min-w-0 flex-1">
        <Link
          to={`/companies/${encodeURIComponent(domain)}`}
          className="block truncate text-13 text-fg hover:text-accent"
        >
          {domain}
        </Link>
        {children}
      </div>
      <IconButton size="sm" onClick={onRemove} aria-label="Remove">
        <X size={14} />
      </IconButton>
    </div>
  );
}

export function WorkspacePage() {
  const { watch, pinned, followUp, toggleWatch, togglePin, removeFollowUp, clearAll } = useWorkspace();
  const total = watch.length + pinned.length + followUp.length;

  return (
    <>
      <PageHeader
        title="Workspace"
        subtitle="Your watchlist, pinned companies & follow-up queue — saved locally in this browser"
        actions={
          total > 0 ? (
            <Button variant="ghost" size="sm" onClick={clearAll}>
              Clear all
            </Button>
          ) : undefined
        }
      />

      <div className="grid gap-4 p-4 lg:grid-cols-3">
        <SectionPanel
          title="Watchlist"
          icon={<Eye size={15} />}
          actions={<span className="tabular text-11 text-fg-subtle">{fmtInt(watch.length)}</span>}
        >
          {watch.length === 0 ? (
            <EmptyState title="Nothing watched" description="Use Watch on a company to track it here." />
          ) : (
            <div className="divide-y divide-line/60">
              {watch.map((d) => (
                <Row key={d} domain={d} onRemove={() => toggleWatch(d)} />
              ))}
            </div>
          )}
        </SectionPanel>

        <SectionPanel
          title="Pinned"
          icon={<Pin size={15} />}
          actions={
            pinned.length >= 2 ? (
              <Link
                to={`/compare?domains=${pinned.map(encodeURIComponent).join(",")}`}
                className="inline-flex items-center gap-1.5 rounded-md border border-line bg-control px-2.5 py-1 text-12 text-fg hover:border-accent hover:text-accent"
              >
                <GitCompare size={13} />
                Compare {pinned.length}
              </Link>
            ) : (
              <span className="tabular text-11 text-fg-subtle">{fmtInt(pinned.length)}</span>
            )
          }
        >
          {pinned.length === 0 ? (
            <EmptyState title="Nothing pinned" description="Pin companies to line them up for comparison." />
          ) : (
            <div className="divide-y divide-line/60">
              {pinned.map((d) => (
                <Row key={d} domain={d} onRemove={() => togglePin(d)} />
              ))}
            </div>
          )}
        </SectionPanel>

        <SectionPanel
          title="Follow-up queue"
          icon={<Flag size={15} />}
          actions={<span className="tabular text-11 text-fg-subtle">{fmtInt(followUp.length)}</span>}
        >
          {followUp.length === 0 ? (
            <EmptyState title="No follow-ups" description="Flag companies for follow-up to queue them here." />
          ) : (
            <div className="divide-y divide-line/60">
              {followUp.map((f) => (
                <Row key={f.domain} domain={f.domain} onRemove={() => removeFollowUp(f.domain)}>
                  <div className="flex items-center gap-2">
                    {f.due && <Badge tone="warning">Due {fmtDate(f.due)}</Badge>}
                    {f.note && <span className="truncate text-11 text-fg-subtle">{f.note}</span>}
                    {!f.due && !f.note && (
                      <span className="text-11 text-fg-subtle">Added {fmtDate(f.addedAt)}</span>
                    )}
                  </div>
                </Row>
              ))}
            </div>
          )}
        </SectionPanel>
      </div>
    </>
  );
}
