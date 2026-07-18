export type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";

export const IMPORT_STATUS_TONE: Record<string, Tone> = {
  previewed: "neutral",
  running: "accent",
  completed: "positive",
  partial: "warning",
  failed: "danger",
  rolled_back: "warning",
  cancelled: "neutral",
};

export const REVIEW_STATE_TONE: Record<string, Tone> = {
  pending: "warning",
  approved: "positive",
  rejected: "danger",
  skipped: "neutral",
  resolved: "accent",
};

export const CATEGORY_LABEL: Record<string, string> = {
  new_company: "New companies",
  updated_company: "Updated companies",
  new_decision_maker: "New decision makers",
  updated_decision_maker: "Updated decision makers",
  conflict: "Conflicts",
  duplicate: "Duplicates",
  invalid: "Invalid records",
  unchanged: "Unchanged",
};

/** Categories shown in the review workflow, in display order. */
export const REVIEW_CATEGORY_ORDER = [
  "new_company",
  "updated_company",
  "new_decision_maker",
  "updated_decision_maker",
  "conflict",
  "duplicate",
  "invalid",
] as const;

export function humanBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function fmtDuration(ms: number): string {
  const s = (ms || 0) / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}
