import { useState, type ReactNode } from "react";
import { Check, Copy, PencilLine, ShieldCheck, Sparkles, X } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { toast } from "@/components/ui/Toast";

/** Where a field's value came from — drives the per-field provenance chip. */
export type FieldSource = "apify" | "overridden" | "manual" | "none";

/** Round avatar — the actor photo when present, else initials on an accent tint. */
export function Avatar({ name, src, size = 44 }: { name: string; src?: string | null; size?: number }) {
  const initials =
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0]?.toUpperCase())
      .join("") || "?";
  return (
    <div
      className="grid shrink-0 place-items-center overflow-hidden rounded-full bg-accent/15 font-semibold text-accent"
      style={{ width: size, height: size, fontSize: Math.round(size * 0.36) }}
      aria-hidden={!src}
    >
      {src ? <img src={src} alt={name} className="h-full w-full object-cover" /> : initials}
    </div>
  );
}

/** One-click copy-to-clipboard for a contact value. */
export function CopyButton({ value }: { value?: string | null }) {
  const [done, setDone] = useState(false);
  if (!value) return null;
  return (
    <button
      type="button"
      title="Copy"
      onClick={async (e) => {
        e.preventDefault();
        try {
          await navigator.clipboard.writeText(value);
          setDone(true);
          toast("Copied", "positive");
          setTimeout(() => setDone(false), 1200);
        } catch {
          toast("Couldn't copy", "danger");
        }
      }}
      className="shrink-0 text-fg-subtle hover:text-accent"
    >
      {done ? <Check size={12} /> : <Copy size={12} />}
    </button>
  );
}

/** Verified / Unknown contact-quality chip (presence handled separately by NotAvailable). */
export function VerifiedBadge({ verified }: { verified: boolean }) {
  return verified ? (
    <Badge tone="positive" title="Verified by the data provider">
      <ShieldCheck size={10} /> Verified
    </Badge>
  ) : (
    <Badge tone="neutral" title="Verification status unknown">
      Unknown
    </Badge>
  );
}

/** A titled enterprise-CRM section card (header + body). */
export function SectionCard({
  title,
  icon,
  action,
  children,
  className = "",
}: {
  title: string;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-lg border border-line bg-surface p-3 ${className}`}>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-11 font-semibold uppercase tracking-wide text-fg-subtle">
          {icon}
          {title}
        </span>
        {action}
      </div>
      {children}
    </section>
  );
}

/** Small per-field provenance chip ("Auto-filled from Apify" / "Manually overridden"). */
export function SourceBadge({ source, original }: { source: FieldSource; original?: string }) {
  if (source === "apify")
    return (
      <Badge tone="accent" title="Auto-filled from Apify">
        <Sparkles size={10} /> Auto-filled
      </Badge>
    );
  if (source === "overridden")
    return (
      <Badge
        tone="warning"
        title={original ? `Manually overridden — Apify had: ${original}` : "Manually overridden"}
      >
        <PencilLine size={10} /> Overridden
      </Badge>
    );
  if (source === "manual")
    return (
      <Badge tone="neutral" title="Manually added by an analyst">
        <PencilLine size={10} /> Manual
      </Badge>
    );
  return null;
}

/** Greyed "Not Available" for missing data — never a placeholder value. */
export function NotAvailable() {
  return <span className="italic text-fg-subtle">Not Available</span>;
}

/** A labelled read-only field row: label · value (or Not Available) · provenance chip. */
export function FieldRow({
  label,
  value,
  source = "none",
  original,
  href,
  trailing,
}: {
  label: string;
  value?: string | null;
  source?: FieldSource;
  original?: string;
  href?: string | null;
  trailing?: ReactNode;
}) {
  const has = Boolean(value && String(value).trim());
  return (
    <div className="flex items-start justify-between gap-3 py-1">
      <span className="mt-0.5 shrink-0 text-11 text-fg-subtle">{label}</span>
      <span className="flex min-w-0 flex-wrap items-center justify-end gap-1.5">
        <span className="truncate text-right text-12 text-fg">
          {has ? (
            href ? (
              <a href={href} target="_blank" rel="noreferrer" className="text-accent hover:underline">
                {value}
              </a>
            ) : (
              value
            )
          ) : (
            <NotAvailable />
          )}
        </span>
        {trailing}
        {has && <SourceBadge source={source} original={original} />}
      </span>
    </div>
  );
}

/** A titled group of field rows. */
export function FieldGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-0.5 text-11 font-semibold uppercase tracking-wide text-fg-subtle">{title}</div>
      <div className="divide-y divide-line/60">{children}</div>
    </div>
  );
}

/** Contact-completeness checklist (✓/✗ per key field). */
export function Completeness({ items }: { items: { label: string; ok: boolean }[] }) {
  const done = items.filter((i) => i.ok).length;
  return (
    <div className="rounded-lg border border-line bg-surface p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-12 font-semibold text-fg">Contact Completeness</span>
        <span className="text-11 text-fg-subtle">
          {done}/{items.length} complete
        </span>
      </div>
      <div className="flex flex-wrap gap-x-3.5 gap-y-1">
        {items.map((i) => (
          <span
            key={i.label}
            className={`inline-flex items-center gap-1 text-12 ${
              i.ok ? "text-positive" : "text-fg-subtle"
            }`}
          >
            {i.ok ? <Check size={13} /> : <X size={13} />} {i.label}
          </span>
        ))}
      </div>
    </div>
  );
}
