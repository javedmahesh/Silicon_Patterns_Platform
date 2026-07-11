/**
 * Human lead-review status metadata (P-task viii) — the single source for labels,
 * badge tones, and the picker order, reused by the lead table, the Company-Profile
 * panel, and the review reports.
 */
type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";

export const REVIEW_STATUS_META: Record<string, { label: string; tone: Tone; hint: string }> = {
  approved: { label: "Approved", tone: "positive", hint: "A human confirmed this is a real, qualified prospect." },
  needs_review: { label: "Needs Review", tone: "neutral", hint: "Flagged for a second look." },
  strategic_account: {
    label: "Strategic Account", tone: "accent",
    hint: "High-value relationship — always prioritised above the model order.",
  },
  disqualified: { label: "Disqualified", tone: "danger", hint: "A human ruled this out — sinks below the model order." },
  watchlist: { label: "Watchlist", tone: "warning", hint: "Worth tracking; not yet actioned." },
};

/** Picker / display order (matches the task spec). */
export const REVIEW_STATUSES = [
  "approved", "needs_review", "strategic_account", "disqualified", "watchlist",
] as const;

/** Statuses that can influence the adjusted score when the feature is enabled —
 *  these require a reason + manager/admin. Mirrors the default `review_feedback`
 *  config; the backend is the source of truth and enforces the gates. */
export const SCORE_AFFECTING_STATUSES = new Set(["strategic_account", "approved", "disqualified"]);

export function reviewStatusLabel(status?: string | null): string {
  if (!status) return "—";
  return REVIEW_STATUS_META[status]?.label ?? status;
}

export function reviewStatusTone(status?: string | null): Tone {
  return (status && REVIEW_STATUS_META[status]?.tone) || "neutral";
}
