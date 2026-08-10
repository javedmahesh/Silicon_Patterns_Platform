import type { AlertOut } from "@/lib/api/types";

/**
 * Where a Smart Alert takes you.
 *
 * Smart Alerts are an attention layer, not a destination: every one of them leads
 * back into Opportunities, carrying enough context that the thing which caught the
 * user's eye is the thing they land on.
 *
 * Identity is used in descending order of strength — the opportunity that raised the
 * alert, then the company it concerns — because a headline is a label, not a key, and
 * two companies can publish the same one.
 *
 * The signal category is set deliberately rather than left to the page default. That
 * default is NEWS, so a leadership alert routed without it would land on a table that
 * filters its own subject out and reads as "nothing here".
 */
const LEADERSHIP_TYPES = new Set([
  "executive_joined",
  "executive_departed",
  "promotion",
  "leadership_change",
]);

export function alertHref(alert: AlertOut): string {
  const params = new URLSearchParams();

  // 1. The opportunity itself — open that exact record.
  if (alert.opportunity_id) {
    params.set("opportunity", alert.opportunity_id);
    // The record may be any category; ALL guarantees the surrounding list contains it.
    params.set("signal_category", "ALL");
    if (alert.company_domain) params.set("company_domain", alert.company_domain);
    return `/opportunities?${params.toString()}`;
  }

  // 2. The company — show what it has, in the category the alert is about.
  if (alert.company_domain) {
    params.set("company_domain", alert.company_domain);
    params.set("signal_category", LEADERSHIP_TYPES.has(alert.type) ? "LEADERSHIP" : "ALL");
    return `/opportunities?${params.toString()}`;
  }

  // 3. Nothing to anchor on: the unfiltered page, exactly as the nav opens it.
  return "/opportunities";
}
