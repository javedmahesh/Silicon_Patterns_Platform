import { Badge } from "@/components/ui/Badge";
import { REVIEW_STATUS_META, reviewStatusLabel, reviewStatusTone } from "@/lib/reviewStatus";

/** A human review-status pill. Renders a muted "—" when a lead is unreviewed so
 *  the lead table always shows the model grade AND the (possibly empty) human status. */
export function HumanStatusBadge({ status, className }: { status?: string | null; className?: string }) {
  if (!status) {
    return <span className={className ?? "text-12 text-fg-subtle"}>—</span>;
  }
  return (
    <Badge tone={reviewStatusTone(status)} title={REVIEW_STATUS_META[status]?.hint} className={className}>
      {reviewStatusLabel(status)}
    </Badge>
  );
}
