import { useMemo, useState } from "react";
import { Activity, Clock, Network, Sparkles, Target } from "lucide-react";

import { ContactDrawer } from "@/components/profile/ContactDrawer";
import { RelationshipGraph } from "@/components/profile/RelationshipGraph";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionPanel } from "@/components/ui/SectionPanel";
import { Spinner } from "@/components/ui/Spinner";
import { useCompanyRelationships } from "@/lib/api/queries";
import type { DecisionMakerOut, NextBestContactOut } from "@/lib/api/types";

type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";
const PRIORITY_TONE: Record<string, Tone> = {
  "Contact Now": "warning", "Contact This Week": "accent", Monitor: "neutral", "Low Priority": "neutral",
};
const REL_TONE: Record<string, Tone> = {
  Strategic: "positive", Active: "positive", Engaged: "accent", Known: "neutral", Cold: "neutral",
};
const ALERT_TONE: Record<string, Tone> = { high: "danger", medium: "warning", info: "neutral" };
const ACTION_TONE: Record<string, Tone> = { high: "danger", medium: "warning", low: "neutral" };

function ContactRow({ c, onOpen }: { c: NextBestContactOut; onOpen: (id: number) => void }) {
  return (
    <button
      onClick={() => onOpen(c.contact.decision_maker_id)}
      className="w-full rounded-md border border-line bg-base px-2.5 py-2 text-left hover:bg-raised"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="min-w-0">
          <span className="block truncate text-12 font-medium text-fg">{c.contact.full_name}</span>
          <span className="block truncate text-11 text-fg-subtle">
            {c.contact.title || "—"}{c.contact.department ? ` · ${c.contact.department}` : ""}
          </span>
        </span>
        <span className="flex shrink-0 items-center gap-1.5">
          <Badge tone={REL_TONE[c.relationship_status] ?? "neutral"}>{c.relationship_status || "Cold"}</Badge>
          <Badge tone={PRIORITY_TONE[c.priority] ?? "neutral"}>{c.priority}</Badge>
        </span>
      </div>
      {c.next_action && (
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-11">
          <Badge tone={ACTION_TONE[c.next_action.priority] ?? "neutral"}>{c.next_action.action}</Badge>
          <span className="text-fg-subtle">{c.next_action.reason}</span>
          {c.follow_up?.overdue && <span className="text-danger">· Follow-up overdue</span>}
          {c.risk_severity === "high" && <span className="text-danger">· Risk</span>}
        </div>
      )}
    </button>
  );
}

/**
 * Phase 3 relationship-intelligence panel for the Company Profile: smart alerts,
 * next best contacts + actions, overdue follow-ups, opportunity intelligence and an
 * interactive relationship graph. Lazy-loaded when the Relationships tab opens.
 */
export function CompanyRelationshipsPanel({
  domain,
  decisionMakers,
}: {
  domain: string;
  decisionMakers: DecisionMakerOut[];
}) {
  const { data, isLoading, isError } = useCompanyRelationships(domain);
  const [contactFor, setContactFor] = useState<DecisionMakerOut | null>(null);
  const dmById = useMemo(
    () => new Map(decisionMakers.map((d) => [d.id, d])),
    [decisionMakers],
  );
  const open = (id: number) => {
    const dm = dmById.get(id);
    if (dm) setContactFor(dm);
  };

  if (isLoading) return <div className="grid place-items-center py-12"><Spinner size={18} /></div>;
  if (isError || !data) {
    return <EmptyState icon={<Network size={20} />} title="Relationships unavailable" description="Couldn't compute relationship intelligence." />;
  }

  return (
    <div className="space-y-4">
      {data.alerts.length > 0 && (
        <SectionPanel title="Smart alerts" icon={<Activity size={15} />}>
          <div className="space-y-1.5">
            {data.alerts.slice(0, 12).map((a, i) => (
              <div key={i} className="flex items-center justify-between gap-2 rounded-md border border-line bg-base px-2.5 py-1.5">
                <span className="min-w-0">
                  <span className="block truncate text-12 text-fg">{a.title}</span>
                  {a.detail && <span className="block truncate text-11 text-fg-subtle">{a.detail}</span>}
                </span>
                <Badge tone={ALERT_TONE[a.severity] ?? "neutral"}>{a.type.replace(/_/g, " ")}</Badge>
              </div>
            ))}
          </div>
        </SectionPanel>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionPanel title="Next best contacts" icon={<Target size={15} />}>
          {data.next_best_contacts.length === 0 ? (
            <p className="text-12 text-fg-subtle">No contacts.</p>
          ) : (
            <div className="space-y-1.5">
              {(data.next_best_contacts as NextBestContactOut[]).slice(0, 8).map((c) => (
                <ContactRow key={c.contact.decision_maker_id} c={c} onOpen={open} />
              ))}
            </div>
          )}
        </SectionPanel>

        <SectionPanel title="Follow-ups due" icon={<Clock size={15} />}>
          {data.follow_ups.length === 0 ? (
            <p className="text-12 text-fg-subtle">Nothing overdue. 🎉</p>
          ) : (
            <div className="space-y-1.5">
              {(data.follow_ups as NextBestContactOut[]).map((c) => (
                <ContactRow key={c.contact.decision_maker_id} c={c} onOpen={open} />
              ))}
            </div>
          )}
        </SectionPanel>
      </div>

      <SectionPanel title="Opportunity intelligence" icon={<Sparkles size={15} />}>
        {data.opportunity_intelligence.length === 0 ? (
          <p className="text-12 text-fg-subtle">No opportunities to align.</p>
        ) : (
          <div className="space-y-2">
            {data.opportunity_intelligence.map((o) => (
              <div key={o.opportunity_id} className="rounded-md border border-line bg-base p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-12 font-medium text-fg">{o.label}</span>
                  <Badge tone="accent">{o.best_department}</Badge>
                </div>
                {o.best && (
                  <button onClick={() => open(o.best!.decision_maker_id)} className="mt-0.5 block text-left text-11 text-accent hover:underline">
                    Best: {o.best.full_name} ({o.best.title || "—"})
                    {o.relationship_status ? ` · ${o.relationship_status}` : ""}
                  </button>
                )}
                {o.suggested_action && (
                  <div className="mt-0.5 text-11 text-fg-muted">→ {o.suggested_action.action}: {o.suggested_action.reason}</div>
                )}
                {o.backups.length > 0 && (
                  <div className="mt-0.5 text-11 text-fg-subtle">
                    Backups: {o.backups.map((b) => b.full_name).join(", ")}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </SectionPanel>

      <SectionPanel title="Relationship graph" icon={<Network size={15} />}>
        <RelationshipGraph graph={data.graph} onSelectDm={open} />
      </SectionPanel>

      {contactFor && <ContactDrawer dm={contactFor} open onClose={() => setContactFor(null)} />}
    </div>
  );
}
