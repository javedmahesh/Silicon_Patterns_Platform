import { AlertTriangle } from "lucide-react";

import { enumLabel } from "@/lib/format";

/** Honest callout: which engines have NO data for this company, so the analyst
 *  reads the score in context rather than mistaking gaps for low signal. */
export function MissingInputsCallout({ missing }: { missing?: string[] }) {
  if (!missing || missing.length === 0) return null;
  return (
    <div className="flex items-start gap-2 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-12 text-fg-muted">
      <AlertTriangle size={14} className="mt-px shrink-0 text-warning" />
      <div>
        <span className="text-fg">No data from:</span> {missing.map(enumLabel).join(", ")}. The
        score reflects only the engines that have data for this company.
      </div>
    </div>
  );
}
