import { useMemo } from "react";

import type { RelationshipGraphOut } from "@/lib/api/types";

/** Per-kind fill (themed via the platform CSS variables) + node radius. */
const FILL: Record<string, string> = {
  company: "var(--color-accent)",
  department: "var(--color-accent-weak, var(--color-accent))",
  contact: "var(--color-control)",
  outreach: "var(--color-positive)",
  leadership: "var(--color-warning)",
  opportunity: "var(--color-fg-subtle)",
};
const RADIUS: Record<string, number> = {
  company: 26, department: 13, contact: 9, outreach: 13, leadership: 8, opportunity: 8,
};
// concentric ring (distance from centre) per kind
const RING: Record<string, number> = {
  company: 0, department: 110, outreach: 110, contact: 195, leadership: 255, opportunity: 255,
};
const W = 760;
const H = 560;
const CX = W / 2;
const CY = H / 2;

/**
 * Deterministic node-link relationship graph (no graph lib). Nodes are laid out on
 * concentric rings by kind (company centre → departments/outreach → contacts →
 * leadership/opportunities); clicking a contact node opens its profile.
 */
export function RelationshipGraph({
  graph,
  onSelectDm,
}: {
  graph: RelationshipGraphOut;
  onSelectDm: (dmId: number) => void;
}) {
  const pos = useMemo(() => {
    const byRing: Record<number, string[]> = {};
    for (const n of graph.nodes) {
      const r = RING[n.kind] ?? 255;
      (byRing[r] ??= []).push(n.id);
    }
    const p: Record<string, { x: number; y: number }> = {};
    for (const [r, ids] of Object.entries(byRing)) {
      const radius = Number(r);
      if (radius === 0) {
        ids.forEach((id) => (p[id] = { x: CX, y: CY }));
        continue;
      }
      const n = ids.length;
      ids.forEach((id, i) => {
        const a = (-90 + (i / n) * 360) * (Math.PI / 180);
        p[id] = { x: CX + radius * Math.cos(a), y: CY + radius * Math.sin(a) };
      });
    }
    return p;
  }, [graph]);

  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-[480px] w-full min-w-[680px]">
        {/* edges */}
        {graph.edges.map((e, i) => {
          const a = pos[e.source];
          const b = pos[e.target];
          if (!a || !b) return null;
          return (
            <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
              stroke="var(--color-line)" strokeWidth={e.kind === "hierarchy" ? 1.5 : 1}
              strokeOpacity={0.6} strokeDasharray={e.kind === "alignment" ? "3 3" : undefined} />
          );
        })}
        {/* nodes */}
        {graph.nodes.map((n) => {
          const pt = pos[n.id];
          if (!pt) return null;
          const r = RADIUS[n.kind] ?? 8;
          const clickable = n.kind === "contact" && n.dm_id != null;
          const initials = (n.label || "?").split(/\s+/).filter(Boolean).slice(0, 2)
            .map((w) => w[0]?.toUpperCase()).join("");
          return (
            <g key={n.id}
              transform={`translate(${pt.x},${pt.y})`}
              style={{ cursor: clickable ? "pointer" : "default" }}
              onClick={clickable ? () => onSelectDm(n.dm_id as number) : undefined}>
              <title>{`${n.label}${n.detail ? " — " + n.detail : ""}`}</title>
              <circle r={r} fill={FILL[n.kind] ?? "var(--color-control)"}
                stroke="var(--color-line-strong, var(--color-line))" strokeWidth={1} />
              {n.kind === "company" || n.kind === "department" || n.kind === "outreach" ? (
                <text textAnchor="middle" dy={n.kind === "company" ? 4 : r + 12}
                  style={{ fill: "var(--color-fg)", fontSize: n.kind === "company" ? 12 : 10, fontWeight: 600 }}>
                  {n.label.length > 18 ? n.label.slice(0, 17) + "…" : n.label}
                </text>
              ) : n.kind === "contact" ? (
                <text textAnchor="middle" dy={3} style={{ fill: "var(--color-fg)", fontSize: 8 }}>
                  {initials}
                </text>
              ) : null}
            </g>
          );
        })}
      </svg>
      <div className="flex flex-wrap gap-3 px-1 text-11 text-fg-subtle">
        {Object.entries({ Company: "company", Department: "department", Contact: "contact",
          Outreach: "outreach", Leadership: "leadership", Opportunity: "opportunity" }).map(([label, kind]) => (
          <span key={kind} className="inline-flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: FILL[kind] }} /> {label}
          </span>
        ))}
        <span className="text-fg-subtle">· click a contact to open its profile</span>
      </div>
    </div>
  );
}
