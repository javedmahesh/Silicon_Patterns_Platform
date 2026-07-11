import { cx } from "@/lib/cx";

/** The lead pipeline (mirrors backend ASSIGNMENT_STATUSES). */
export const ASSIGNMENT_STATUSES = [
  "new", "assigned", "contacted", "qualified", "proposal", "won", "lost", "on_hold",
] as const;

const COLORS: Record<string, string> = {
  new: "text-fg-muted",
  assigned: "text-accent",
  contacted: "text-accent",
  qualified: "text-accent-strong",
  proposal: "text-accent-strong",
  won: "text-emerald-400",
  lost: "text-danger",
  on_hold: "text-amber-400",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full border border-line bg-control px-2 py-0.5 text-11 capitalize",
        COLORS[status] ?? "text-fg-muted",
      )}
    >
      {status.replace("_", " ")}
    </span>
  );
}

export function StatusSelect({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (s: string) => void;
  disabled?: boolean;
}) {
  return (
    <select
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-md border border-line bg-control px-2 py-1 text-12 capitalize text-fg outline-none focus:border-accent disabled:opacity-50"
      aria-label="Lead status"
    >
      {ASSIGNMENT_STATUSES.map((s) => (
        <option key={s} value={s} className="bg-surface capitalize">
          {s.replace("_", " ")}
        </option>
      ))}
    </select>
  );
}
