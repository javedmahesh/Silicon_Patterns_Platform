import { Activity, Clock, Gauge, Layers, Network, ShieldAlert, Target, Users } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionPanel } from "@/components/ui/SectionPanel";
import { Spinner } from "@/components/ui/Spinner";
import { useCompanyIntelligence } from "@/lib/api/queries";

type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";
const ENGAGE_TONE: Record<string, Tone> = { Healthy: "positive", Warm: "accent", Cold: "warning", Dormant: "neutral" };
const HEAT_TONE: Record<string, Tone> = { Strong: "positive", Moderate: "accent", Weak: "warning", Missing: "danger" };

function Bar({ pct, tone = "accent" }: { pct: number; tone?: "accent" | "positive" }) {
  return (
    <div className="h-1.5 rounded bg-control">
      <div className={`h-1.5 rounded ${tone === "positive" ? "bg-positive" : "bg-accent"}`} style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-md border border-line bg-base p-2.5">
      <div className="text-11 text-fg-subtle">{label}</div>
      <div className="text-18 font-semibold text-fg">{value}</div>
      {hint && <div className="text-11 text-fg-subtle">{hint}</div>}
    </div>
  );
}

/**
 * Company Intelligence panel (Phase 2.5): buying-committee coverage, department
 * coverage, contact completeness, engagement score, relationship heatmap,
 * opportunity alignment, contact risk and a unified timeline — all deterministic
 * and lazy-loaded when the Intelligence tab opens.
 */
export function CompanyIntelligencePanel({ domain }: { domain: string }) {
  const { data, isLoading, isError } = useCompanyIntelligence(domain);

  if (isLoading) {
    return <div className="grid place-items-center py-12"><Spinner size={18} /></div>;
  }
  if (isError || !data) {
    return <EmptyState icon={<Gauge size={20} />} title="Intelligence unavailable" description="Couldn't compute company intelligence." />;
  }

  const bc = data.buying_committee;
  const dc = data.department_coverage;
  const cc = data.contact_completeness;
  const eng = data.engagement;
  const risk = data.contact_risk;

  return (
    <div className="space-y-4">
      {/* Top line: engagement + coverage headline stats */}
      <div className="grid gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-line bg-surface p-3">
          <div className="flex items-center justify-between">
            <span className="text-11 text-fg-subtle">Engagement</span>
            <Badge tone={ENGAGE_TONE[eng.label] ?? "neutral"}>{eng.label}</Badge>
          </div>
          <div className="text-22 font-semibold text-fg">{eng.score}<span className="text-12 text-fg-subtle">/100</span></div>
          <Bar pct={eng.score} />
          <div className="mt-1 text-11 text-fg-subtle">Relationship: {eng.relationship}</div>
        </div>
        <Stat label="Buying committee" value={`${bc.coverage_pct}%`} hint={`${bc.present}/${bc.total} roles`} />
        <Stat label="Department coverage" value={`${dc.coverage_pct}%`} hint={`${dc.present}/${dc.total} depts`} />
        <Stat label="Contacts" value={`${cc.total_contacts}`} hint={`avg influence ${cc.avg_influence}`} />
      </div>

      {/* Buying committee */}
      <SectionPanel title="Buying committee coverage" icon={<Users size={15} />}>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {(bc.roles ?? []).map((r) => (
            <div key={r.role} className={`rounded-md border p-2.5 ${r.present ? "border-line bg-base" : "border-dashed border-line bg-surface"}`}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-12 font-medium text-fg">{r.role}</span>
                <Badge tone={r.present ? "positive" : "neutral"}>{r.present ? "Present" : "Missing"}</Badge>
              </div>
              {r.contact && (
                <div className="mt-0.5 truncate text-11 text-fg-subtle">
                  {r.contact.full_name} · {r.contact.title || "—"}
                  {r.contact.influence_score != null ? ` · Infl ${r.contact.influence_score}` : ""}
                </div>
              )}
            </div>
          ))}
        </div>
      </SectionPanel>

      {/* Department coverage */}
      <SectionPanel title="Department coverage" icon={<Layers size={15} />}>
        <div className="flex flex-wrap gap-1.5">
          {(dc.rows ?? []).map((row) => (
            <span key={row.department}
              className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-11 ${row.present ? "border-line bg-base text-fg" : "border-dashed border-line text-fg-subtle"}`}>
              {row.department}
              <span className={row.present ? "text-accent" : "text-fg-subtle"}>{row.count}</span>
            </span>
          ))}
        </div>
        {dc.missing.length > 0 && (
          <p className="mt-2 text-11 text-fg-subtle">Missing: {dc.missing.join(", ")}</p>
        )}
      </SectionPanel>

      {/* Contact completeness */}
      <SectionPanel title="Contact completeness" icon={<Gauge size={15} />}>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { label: "Verified email", pct: cc.verified_email_pct, miss: `${cc.missing_email} missing` },
            { label: "Phone coverage", pct: cc.phone_pct, miss: `${cc.missing_phone} missing` },
            { label: "LinkedIn coverage", pct: cc.linkedin_pct, miss: `${cc.missing_linkedin} missing` },
            { label: "High confidence", pct: cc.high_confidence_pct, miss: `avg confidence ${cc.avg_confidence}` },
          ].map((m) => (
            <div key={m.label}>
              <div className="mb-0.5 flex items-center justify-between text-11">
                <span className="text-fg-subtle">{m.label}</span>
                <span className="text-fg">{m.pct}%</span>
              </div>
              <Bar pct={m.pct} tone="positive" />
              <div className="mt-0.5 text-11 text-fg-subtle">{m.miss}</div>
            </div>
          ))}
        </div>
      </SectionPanel>

      {/* Relationship heatmap */}
      <SectionPanel title="Relationship heatmap" icon={<Network size={15} />}>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {(data.relationship_heatmap ?? []).map((h) => (
            <div key={h.department} className="rounded-md border border-line bg-base p-2.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-12 text-fg">{h.department}</span>
                <Badge tone={HEAT_TONE[h.status] ?? "neutral"}>{h.status}</Badge>
              </div>
              <div className="mt-0.5 text-11 text-fg-subtle">{h.detail}</div>
            </div>
          ))}
        </div>
      </SectionPanel>

      {/* Opportunity alignment */}
      <SectionPanel title="Opportunity alignment" icon={<Target size={15} />}>
        {(data.opportunity_alignment ?? []).length === 0 ? (
          <p className="text-12 text-fg-subtle">No opportunities to align yet.</p>
        ) : (
          <div className="space-y-2">
            {data.opportunity_alignment.map((o) => (
              <div key={o.opportunity_id} className="rounded-md border border-line bg-base p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-12 font-medium text-fg">{o.label}</span>
                  <Badge tone="accent">{o.best_department}</Badge>
                </div>
                {o.contact && (
                  <div className="text-11 text-fg-subtle">
                    Best contact: {o.contact.full_name} ({o.contact.title || "—"})
                    {o.contact.influence_score != null ? ` · Infl ${o.contact.influence_score}` : ""}
                  </div>
                )}
                <div className="mt-0.5 text-11 text-fg-muted">{o.reason}</div>
              </div>
            ))}
          </div>
        )}
      </SectionPanel>

      {/* Contact risk */}
      <SectionPanel title="Contact risk" icon={<ShieldAlert size={15} />}>
        <div className="mb-2 flex flex-wrap gap-1.5">
          {[
            ["Missing email", risk.missing_email],
            ["Missing phone", risk.missing_phone],
            ["Missing LinkedIn", risk.missing_linkedin],
            ["Low confidence", risk.low_confidence],
            ["Stale", risk.stale],
            ["Duplicates", risk.duplicates],
            ["Leadership departures", risk.leadership_departures],
          ].map(([label, n]) => (
            <Badge key={label as string} tone={(n as number) > 0 ? "warning" : "neutral"}>
              {label}: {n as number}
            </Badge>
          ))}
        </div>
        {(risk.items ?? []).length > 0 && (
          <div className="space-y-1">
            {risk.items.map((it) => (
              <div key={it.decision_maker_id} className="flex items-center justify-between gap-2 text-11">
                <span className="truncate text-fg">{it.name}</span>
                <span className="shrink-0 text-fg-subtle">{it.risks.join(" · ")}</span>
              </div>
            ))}
          </div>
        )}
      </SectionPanel>

      {/* Timeline */}
      <SectionPanel title="Company timeline" icon={<Clock size={15} />}>
        {(data.timeline ?? []).length === 0 ? (
          <p className="text-12 text-fg-subtle">No events yet.</p>
        ) : (
          <ol className="space-y-2">
            {data.timeline.map((e, i) => (
              <li key={i} className="flex gap-2 text-12">
                <Activity size={13} className="mt-0.5 shrink-0 text-fg-subtle" />
                <div className="min-w-0">
                  <div className="text-fg">{e.title}</div>
                  <div className="text-11 text-fg-subtle">
                    {e.at || "—"}{e.detail ? ` · ${e.detail}` : ""}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </SectionPanel>
    </div>
  );
}
