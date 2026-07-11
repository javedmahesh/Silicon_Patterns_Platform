import { useState } from "react";
import { ChevronDown, ChevronRight, Crown, Layers, Network, Target } from "lucide-react";

import { ContactDrawer } from "@/components/profile/ContactDrawer";
import { Badge } from "@/components/ui/Badge";
import { SectionPanel } from "@/components/ui/SectionPanel";
import { Spinner } from "@/components/ui/Spinner";
import { useCompanyContacts } from "@/lib/api/queries";
import type { DecisionMakerOut, RankedContactOut } from "@/lib/api/types";

type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";
const RANK_TONE: Record<string, Tone> = { primary: "positive", secondary: "accent", alternate: "neutral" };
const CONF_TONE: Record<string, Tone> = { High: "positive", Medium: "accent", Low: "neutral" };
const GROUPS_OPEN_BY_DEFAULT = new Set(["Executive", "Engineering Leaders"]);

/** Influence + confidence chips for a ranked contact. */
function IntelChips({ c }: { c: DecisionMakerOut }) {
  return (
    <span className="flex shrink-0 items-center gap-1.5">
      {c.influence_score != null && <Badge tone="accent">Influence {c.influence_score}</Badge>}
      {c.confidence_level && <Badge tone={CONF_TONE[c.confidence_level] ?? "neutral"}>{c.confidence_level}</Badge>}
    </span>
  );
}

function ContactLine({ rc, onOpen }: { rc: RankedContactOut; onOpen: (d: DecisionMakerOut) => void }) {
  const c = rc.contact as DecisionMakerOut;
  return (
    <button
      onClick={() => onOpen(c)}
      className="flex w-full items-center justify-between gap-3 rounded-md border border-line bg-base px-2.5 py-2 text-left hover:bg-raised"
    >
      <span className="min-w-0">
        <span className="block truncate text-12 font-medium text-fg">
          {c.full_name || [c.first_name, c.last_name].filter(Boolean).join(" ") || "Decision maker"}
        </span>
        <span className="block truncate text-11 text-fg-subtle">
          {c.current_title || c.headline || "—"}
          {c.department_class ? ` · ${c.department_class}` : ""}
        </span>
      </span>
      <IntelChips c={c} />
    </button>
  );
}

/** A recommended-contact card: role + name + reasons. */
function RecCard({ rc, onOpen }: { rc: RankedContactOut; onOpen: (d: DecisionMakerOut) => void }) {
  const c = rc.contact as DecisionMakerOut;
  return (
    <div className="rounded-lg border border-line bg-surface p-3">
      <div className="mb-1 flex items-center justify-between gap-2">
        <Badge tone={RANK_TONE[rc.rank] ?? "neutral"}>
          {rc.rank ? rc.rank[0].toUpperCase() + rc.rank.slice(1) : "Contact"}
        </Badge>
        <IntelChips c={c} />
      </div>
      <button onClick={() => onOpen(c)} className="block w-full text-left">
        <span className="block truncate text-13 font-semibold text-fg hover:text-accent">
          {c.full_name || [c.first_name, c.last_name].filter(Boolean).join(" ") || "Decision maker"}
        </span>
        <span className="block truncate text-11 text-fg-subtle">
          {c.current_title || c.headline || "—"}
          {c.exec_level ? ` · ${c.exec_level}` : ""}
        </span>
      </button>
      {rc.reasons.length > 0 && (
        <ul className="mt-1.5 space-y-0.5">
          {rc.reasons.slice(0, 4).map((r, i) => (
            <li key={i} className="flex items-start gap-1 text-11 text-fg-muted">
              <span className="mt-0.5 text-accent">›</span> {r}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function MapGroup({
  group,
  contacts,
  onOpen,
}: {
  group: string;
  contacts: RankedContactOut[];
  onOpen: (d: DecisionMakerOut) => void;
}) {
  const [open, setOpen] = useState(GROUPS_OPEN_BY_DEFAULT.has(group));
  return (
    <div className="rounded-lg border border-line">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-3 py-2 text-12 font-medium text-fg"
      >
        <span className="flex items-center gap-1.5">
          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          {group}
        </span>
        <span className="text-11 text-fg-subtle">{contacts.length}</span>
      </button>
      {open && (
        <div className="space-y-1.5 border-t border-line p-2">
          {contacts.map((rc) => (
            <ContactLine key={rc.contact.id} rc={rc} onOpen={onOpen} />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Phase 2 company contact intelligence: ranked recommendations (primary/secondary/
 * alternate with reasons), the auto-grouped Company Contact Map (collapsible), and
 * the inferred organisation hierarchy. Lazy-loaded when the People tab renders.
 */
export function CompanyContactsSection({ domain }: { domain: string }) {
  const { data, isLoading } = useCompanyContacts(domain);
  const [contactFor, setContactFor] = useState<DecisionMakerOut | null>(null);

  if (isLoading) {
    return (
      <div className="grid place-items-center py-6">
        <Spinner size={16} />
      </div>
    );
  }
  if (!data || data.total === 0) return null;

  return (
    <>
      {data.recommended.length > 0 && (
        <SectionPanel title="Recommended contacts" icon={<Target size={15} />}>
          <div className="grid gap-3 sm:grid-cols-3">
            {data.recommended.map((rc) => (
              <RecCard key={rc.contact.id} rc={rc} onOpen={setContactFor} />
            ))}
          </div>
        </SectionPanel>
      )}

      <SectionPanel title="Contact map" icon={<Layers size={15} />}>
        <div className="space-y-2">
          {data.groups.map((g) => (
            <MapGroup key={g.group} group={g.group} contacts={g.contacts} onOpen={setContactFor} />
          ))}
        </div>
      </SectionPanel>

      <SectionPanel title="Organization hierarchy" icon={<Network size={15} />}>
        <div className="space-y-2.5">
          {data.hierarchy.map((level) => (
            <div key={level.rank}>
              <div className="mb-1 flex items-center gap-1.5 text-11 font-semibold uppercase tracking-wide text-fg-subtle">
                <Crown size={12} /> {level.level}
                <span className="text-fg-subtle">· {level.contacts.length}</span>
              </div>
              <div className="space-y-1.5">
                {level.contacts.map((rc) => (
                  <ContactLine key={rc.contact.id} rc={rc} onOpen={setContactFor} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </SectionPanel>

      {contactFor && <ContactDrawer dm={contactFor} open onClose={() => setContactFor(null)} />}
    </>
  );
}
