import { Link } from "react-router-dom";

import { GradeBadge } from "@/components/data/GradeBadge";
import { HumanStatusBadge } from "@/components/data/HumanStatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionPanel } from "@/components/ui/SectionPanel";
import { SkeletonLines } from "@/components/ui/Skeleton";
import { useReviewReports } from "@/lib/api/queries";
import type { ReviewReports } from "@/lib/api/types";
import { fmtScore } from "@/lib/format";

// The element type as it actually arrives (inner fields stay optional — `Concrete`
// only de-optionalises the top-level report arrays, not their row members).
type ReportRow = ReviewReports["disagreements"][number];

/** One row in a report list: company → model grade + human status + an optional note. */
function Row({ r, note }: { r: ReportRow; note?: string }) {
  return (
    <Link
      to={`/companies/${encodeURIComponent(r.company_domain)}`}
      className="-mx-3.5 flex items-center gap-2 px-3.5 py-1.5 hover:bg-raised"
    >
      <GradeBadge grade={r.model_grade} size="sm" />
      <span className="min-w-0 flex-1 truncate text-13 text-fg">{r.company_name}</span>
      <HumanStatusBadge status={r.human_status} />
      {note ? <span className="tabular w-12 text-right text-11 text-fg-subtle">{note}</span> : null}
    </Link>
  );
}

function ReportList({ title, rows, note }: {
  title: string;
  rows: ReportRow[];
  note?: (r: ReportRow) => string;
}) {
  return (
    <div>
      <div className="mb-1 text-11 uppercase tracking-wide text-fg-subtle">
        {title} <span className="tabular text-fg-muted">({rows.length})</span>
      </div>
      {rows.length === 0 ? (
        <p className="py-1.5 text-12 text-fg-subtle">None.</p>
      ) : (
        <div className="divide-y divide-line/60">
          {rows.slice(0, 8).map((r) => (
            <Row key={r.company_domain} r={r} note={note?.(r)} />
          ))}
        </div>
      )}
    </div>
  );
}

/** The human-review reports (P-task viii §7): model-vs-human disagreements,
 *  frequently-overridden companies, strategic accounts, and false neg/pos. */
export function ReviewInsights() {
  const { data, isLoading, isError } = useReviewReports();

  return (
    <SectionPanel title="Review insights — model vs human">
      {isLoading ? (
        <SkeletonLines rows={5} />
      ) : isError || !data ? (
        <EmptyState title="No review insights" description="Reviews appear here once analysts assess leads." />
      ) : data.disagreements.length === 0 &&
        data.strategic_accounts.length === 0 &&
        Object.keys(data.status_distribution).length === 0 ? (
        <EmptyState
          title="No human reviews yet"
          description="When analysts assess leads (approve, disqualify, flag strategic…), the model-vs-human reports build here."
        />
      ) : (
        <div className="space-y-5">
          {/* Review-adjustment analytics (reconciled Change_05) */}
          <div>
            <div className="mb-1.5 flex items-center gap-2 text-11 uppercase tracking-wide text-fg-subtle">
              Score adjustments
              {data.adjustments.enabled ? null : (
                <span className="text-fg-subtle">(review→score off — model unchanged)</span>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {[
                { k: "Active", v: data.adjustments.active_adjustments },
                { k: "Boosted", v: data.adjustments.boosted },
                { k: "Penalised", v: data.adjustments.penalised },
                { k: "Floor applied", v: data.adjustments.floor_applied },
                { k: "Expired", v: data.adjustments.expired },
                { k: "Avg Δ", v: data.adjustments.avg_delta },
              ].map((s) => (
                <div key={s.k} className="rounded-sm border border-line bg-base px-2.5 py-1.5">
                  <div className="text-11 text-fg-subtle">{s.k}</div>
                  <div className="tabular text-15 text-fg">{s.v}</div>
                </div>
              ))}
            </div>
            {data.adjustments.movers.length > 0 ? (
              <div className="mt-2 divide-y divide-line/60">
                {data.adjustments.movers.map((r) => (
                  <Link
                    key={r.company_domain}
                    to={`/companies/${encodeURIComponent(r.company_domain)}`}
                    className="-mx-3.5 flex items-center gap-2 px-3.5 py-1.5 hover:bg-raised"
                  >
                    <GradeBadge grade={r.model_grade} size="sm" />
                    <span className="text-fg-subtle">→</span>
                    <GradeBadge grade={r.adjusted_grade} size="sm" />
                    <span className="min-w-0 flex-1 truncate text-13 text-fg">{r.company_name}</span>
                    <HumanStatusBadge status={r.human_status} />
                  </Link>
                ))}
              </div>
            ) : null}
          </div>

        <div className="grid gap-5 lg:grid-cols-2">
          <ReportList
            title="Model vs human disagreements"
            rows={data.disagreements}
            note={(r) => (r.disagreement === "false_positive" ? "model high" : "model low")}
          />
          <ReportList
            title="Frequently overridden"
            rows={data.frequently_overridden}
            note={(r) => `${r.override_count}×`}
          />
          <ReportList title="Strategic accounts" rows={data.strategic_accounts} />
          <ReportList
            title="False positives — model high, human disqualified"
            rows={data.false_positives}
            note={(r) => fmtScore(r.model_score, 0)}
          />
          <ReportList
            title="False negatives — model low, human strategic/approved"
            rows={data.false_negatives}
            note={(r) => fmtScore(r.model_score, 0)}
          />
          <div>
            <div className="mb-1 text-11 uppercase tracking-wide text-fg-subtle">Status distribution</div>
            {Object.keys(data.status_distribution).length === 0 ? (
              <p className="py-1.5 text-12 text-fg-subtle">None.</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(data.status_distribution).map(([status, n]) => (
                  <div key={status} className="flex items-center gap-1.5 rounded-sm border border-line bg-base px-2 py-1">
                    <HumanStatusBadge status={status} />
                    <span className="tabular text-12 text-fg-muted">{n}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        </div>
      )}
    </SectionPanel>
  );
}
