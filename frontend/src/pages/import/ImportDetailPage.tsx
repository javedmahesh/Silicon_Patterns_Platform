import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ChevronDown, ChevronRight, Download } from "lucide-react";

import {
  CATEGORY_LABEL,
  IMPORT_STATUS_TONE,
  REVIEW_CATEGORY_ORDER,
  REVIEW_STATE_TONE,
  fmtDuration,
} from "@/components/import/importTones";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { Tabs } from "@/components/ui/Tabs";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import { useImportActions, useImportAudit, useImportJob, useImportReview } from "@/lib/api/queries";
import type { BulkAction, ImportReportDTO, ReviewFieldDTO, ReviewItemDTO } from "@/lib/api/import-types";
import { useAuth } from "@/lib/auth/store";
import { enumLabel, fmtDateTime, fmtInt } from "@/lib/format";

type TabId = "review" | "report" | "audit";

export function ImportDetailPage() {
  const { importId = "" } = useParams();
  const [tab, setTab] = useState<TabId>("review");
  const job = useImportJob(importId);
  const j = job.data;

  return (
    <>
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            <Link to="/historical-import" className="text-fg-subtle hover:text-fg"><ArrowLeft size={16} /></Link>
            <span className="truncate">{j?.filename || "Import"}</span>
            {j && <Badge tone={IMPORT_STATUS_TONE[j.status] ?? "neutral"}>{enumLabel(j.status)}</Badge>}
          </span>
        }
        subtitle={j ? j.summary : "Loading import…"}
      />
      <div className="p-4">
        <Tabs
          tabs={[{ id: "review", label: "Review" }, { id: "report", label: "Report" }, { id: "audit", label: "Audit trail" }]}
          active={tab}
          onChange={(t) => setTab(t as TabId)}
          className="mb-4"
        />
        {job.isError ? (
          <ErrorState title="Couldn't load import" error={job.error} onRetry={job.refetch} />
        ) : job.isLoading ? (
          <div className="grid place-items-center py-10"><Spinner size={20} /></div>
        ) : tab === "review" ? (
          <ReviewTab importId={importId} status={j?.status ?? ""} />
        ) : tab === "report" ? (
          <ReportTab importId={importId} />
        ) : (
          <AuditTab importId={importId} />
        )}
      </div>
    </>
  );
}

// ------------------------------------------------------------------ Review
function ReviewTab({ importId, status }: { importId: string; status: string }) {
  const { isManager, isAdmin } = useAuth();
  const [category, setCategory] = useState("");
  const review = useImportReview(importId, category ? { category } : {});
  const actions = useImportActions(importId);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [report, setReport] = useState<ImportReportDTO | null>(null);

  const stats = review.data?.stats;
  const items = review.data?.items ?? [];
  const byState = stats?.by_state ?? {};
  const byCat = stats?.by_category ?? {};

  const grouped = useMemo(() => {
    const map = new Map<string, ReviewItemDTO[]>();
    for (const it of items) {
      const arr = map.get(it.category);
      if (arr) arr.push(it);
      else map.set(it.category, [it]);
    }
    return map;
  }, [items]);

  function bulk(action: BulkAction, cat?: string) {
    actions.bulk.mutate(
      { action, category: cat },
      { onSuccess: (r) => toast(`${r.changed} record(s) updated`, "positive"), onError: (e) => toast(apiErrorMessage(e), "danger") },
    );
  }

  function commit(dry: boolean) {
    actions.commit.mutate(dry, {
      onSuccess: (r) => {
        setReport(r);
        toast(dry ? `Dry run: ${r.decision_makers_created + r.companies_created} would import`
                  : `Import ${r.status}`, r.status === "failed" ? "danger" : "positive");
        setConfirmOpen(false);
      },
      onError: (e) => { toast(apiErrorMessage(e), "danger"); setConfirmOpen(false); },
    });
  }

  if (review.isError) return <ErrorState title="Couldn't load review" error={review.error} onRetry={review.refetch} />;

  const pending = stats?.pending ?? 0;
  const importable = stats?.importable ?? 0;
  const committed = status !== "previewed";

  return (
    <div className="space-y-4">
      {/* live statistics — refreshes after every action via query invalidation */}
      <div className="panel grid grid-cols-3 divide-x divide-line sm:grid-cols-5 lg:grid-cols-9">
        {[
          ["Pending", byState.pending ?? 0, "warning"], ["Approved", byState.approved ?? 0, "positive"],
          ["Rejected", byState.rejected ?? 0, "danger"], ["Skipped", byState.skipped ?? 0, "neutral"],
          ["Resolved", byState.resolved ?? 0, "accent"], ["Conflicts", byCat.conflict ?? 0, "warning"],
          ["Invalid", byCat.invalid ?? 0, "neutral"], ["Duplicates", byCat.duplicate ?? 0, "neutral"],
          ["Importable", importable, "positive"],
        ].map(([label, val]) => (
          <div key={label as string} className="px-3 py-2.5">
            <div className="text-11 uppercase tracking-wide text-fg-subtle">{label}</div>
            <div className="tabular mt-1 text-16 text-fg">{fmtInt(val as number)}</div>
          </div>
        ))}
      </div>

      {/* bulk + commit bar */}
      <div className="flex flex-wrap items-center gap-2">
        {isManager && !committed && (
          <>
            <Button size="sm" variant="default" disabled={actions.bulk.isPending} onClick={() => bulk("approve_all")}>
              Approve all
            </Button>
            <Button size="sm" variant="default" disabled={actions.bulk.isPending} onClick={() => bulk("reject_all")}>
              Reject all
            </Button>
            <select
              className="h-7 rounded-md border border-line-strong bg-control px-2 text-12 text-fg"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="">All categories</option>
              {REVIEW_CATEGORY_ORDER.map((c) => <option key={c} value={c}>{CATEGORY_LABEL[c]}</option>)}
            </select>
            {category && (
              <>
                <Button size="sm" variant="ghost" onClick={() => bulk("approve_category", category)}>Approve category</Button>
                <Button size="sm" variant="ghost" onClick={() => bulk("reject_category", category)}>Reject category</Button>
              </>
            )}
          </>
        )}
        <div className="ml-auto flex items-center gap-2">
          {!committed && isAdmin && (
            <>
              <Button size="sm" variant="ghost" disabled={actions.commit.isPending} onClick={() => commit(true)}>
                Dry run
              </Button>
              <Button
                size="sm" variant="primary"
                disabled={actions.commit.isPending || importable === 0 || pending > 0}
                onClick={() => setConfirmOpen(true)}
              >
                {actions.commit.isPending ? "Committing…" : `Commit import (${importable})`}
              </Button>
            </>
          )}
        </div>
      </div>
      {!committed && pending > 0 && (
        <p className="text-11 text-warning">{fmtInt(pending)} record(s) still pending review — resolve them to enable commit.</p>
      )}
      {actions.commit.isPending && <ProgressBar />}
      {report && <InlineReport report={report} />}

      {/* grouped, expandable review sections */}
      {review.isLoading ? (
        <div className="grid place-items-center py-8"><Spinner size={18} /></div>
      ) : items.length === 0 ? (
        <EmptyState title="No records in this view" description="Adjust the category filter to see more." />
      ) : (
        <div className="space-y-2">
          {REVIEW_CATEGORY_ORDER.filter((c) => grouped.has(c)).map((cat) => (
            <CategoryGroup
              key={cat}
              category={cat}
              records={grouped.get(cat)!}
              actions={actions}
              editable={isManager && !committed}
            />
          ))}
        </div>
      )}

      {confirmOpen && (
        <Modal
          open onClose={() => setConfirmOpen(false)} title="Commit import"
          footer={
            <>
              <Button variant="ghost" onClick={() => setConfirmOpen(false)}>Cancel</Button>
              <Button variant="primary" disabled={actions.commit.isPending} onClick={() => commit(false)}>
                {actions.commit.isPending ? "Committing…" : "Commit now"}
              </Button>
            </>
          }
        >
          <p className="text-13 text-fg">
            Apply <span className="font-medium">{fmtInt(importable)}</span> approved record(s) to the platform in a single
            transaction? Rejected, skipped and pending records are not imported. This cannot be undone.
          </p>
        </Modal>
      )}
    </div>
  );
}

function CategoryGroup({ category, records, actions, editable }:
  { category: string; records: ReviewItemDTO[]; actions: ReturnType<typeof useImportActions>; editable: boolean }) {
  const [open, setOpen] = useState(category === "conflict");
  return (
    <section className="panel overflow-hidden">
      <button
        type="button" onClick={() => setOpen((o) => !o)}
        className="flex h-10 w-full items-center gap-2 px-3.5 text-13 font-medium text-fg hover:bg-raised"
      >
        <span className="text-fg-subtle">{open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}</span>
        <span>{CATEGORY_LABEL[category] ?? category}</span>
        <span className="font-normal text-fg-subtle">({records.length})</span>
      </button>
      {open && (
        <div className="divide-y divide-line border-t border-line">
          {records.map((r) => <RecordRow key={`${r.record_kind}:${r.source_ref}`} item={r} actions={actions} editable={editable} />)}
        </div>
      )}
    </section>
  );
}

function RecordRow({ item, actions, editable }:
  { item: ReviewItemDTO; actions: ReturnType<typeof useImportActions>; editable: boolean }) {
  const [open, setOpen] = useState(false);
  const hasFields = item.fields.length > 0;

  function decide(decision: "approve" | "reject" | "skip") {
    actions.decide.mutate(
      { kind: item.record_kind, source_ref: item.source_ref, decision },
      { onError: (e) => toast(apiErrorMessage(e), "danger") },
    );
  }

  return (
    <div className="px-3.5 py-2.5">
      <div className="flex items-center gap-3">
        <button type="button" onClick={() => hasFields && setOpen((o) => !o)}
                className={hasFields ? "text-fg-subtle" : "invisible"}>
          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        <div className="min-w-0 flex-1">
          <div className="truncate text-13 text-fg">{item.label || item.source_ref}</div>
          <div className="truncate text-11 text-fg-subtle">
            {item.resolved_domain || "—"}{item.match_type ? ` · ${enumLabel(item.match_type)}` : ""}
            {item.reviewer ? ` · by ${item.reviewer}` : ""}
          </div>
        </div>
        <Badge tone={REVIEW_STATE_TONE[item.state] ?? "neutral"}>{enumLabel(item.state)}</Badge>
        {editable && (
          <div className="flex shrink-0 items-center gap-1">
            <Button size="sm" variant="ghost" className="text-positive" onClick={() => decide("approve")}>Approve</Button>
            <Button size="sm" variant="ghost" className="text-danger" onClick={() => decide("reject")}>Reject</Button>
            <Button size="sm" variant="ghost" onClick={() => decide("skip")}>Skip</Button>
          </div>
        )}
      </div>
      {open && hasFields && (
        <div className="mt-2 space-y-1.5 pl-7">
          {item.fields.map((f) => (
            <FieldRow key={f.field} item={item} field={f} actions={actions} editable={editable} />
          ))}
        </div>
      )}
    </div>
  );
}

function FieldRow({ item, field, actions, editable }:
  { item: ReviewItemDTO; field: ReviewFieldDTO; actions: ReturnType<typeof useImportActions>; editable: boolean }) {
  const resulting = field.decision === "accept_historical" ? field.historical_value : field.platform_value;
  function choose(choice: "keep_platform" | "accept_historical") {
    actions.resolve.mutate(
      { kind: item.record_kind, source_ref: item.source_ref, field: field.field, choice },
      { onError: (e) => toast(apiErrorMessage(e), "danger") },
    );
  }
  return (
    <div className="rounded-md border border-line/70 bg-raised/40 px-3 py-2 text-12">
      <div className="flex items-center gap-2">
        <span className="font-medium text-fg">{field.field}</span>
        {field.is_conflict && <Badge tone="warning">conflict</Badge>}
      </div>
      <div className="mt-1 grid gap-x-4 gap-y-0.5 sm:grid-cols-2">
        <div><span className="text-fg-subtle">Platform: </span><span className="text-fg">{field.platform_value || "—"}</span></div>
        <div><span className="text-fg-subtle">Historical: </span><span className="text-fg">{field.historical_value || "—"}</span></div>
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        {editable && (
          <>
            <Button size="sm" variant={field.decision === "keep_platform" ? "primary" : "default"}
                    onClick={() => choose("keep_platform")}>Keep platform</Button>
            <Button size="sm" variant={field.decision === "accept_historical" ? "primary" : "default"}
                    onClick={() => choose("accept_historical")}>Accept historical</Button>
          </>
        )}
        <span className="text-11 text-fg-subtle">Result: <span className="text-fg">{resulting || "—"}</span></span>
      </div>
    </div>
  );
}

function ProgressBar() {
  return (
    <div className="panel p-3">
      <div className="flex items-center gap-2 text-12 text-fg-muted"><Spinner size={14} /> Applying transaction…</div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-line">
        <div className="h-full w-1/2 animate-pulse rounded-full bg-accent" />
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ Report
function InlineReport({ report }: { report: ImportReportDTO }) {
  return (
    <div className="panel p-3">
      <div className="mb-1 text-12 font-medium text-fg">Last run: {enumLabel(report.status)}</div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-12 sm:grid-cols-4">
        <Kv label="Companies created" value={report.companies_created} />
        <Kv label="Companies updated" value={report.companies_updated} />
        <Kv label="DMs created" value={report.decision_makers_created} />
        <Kv label="DMs updated" value={report.decision_makers_updated} />
      </div>
      {report.errors.length > 0 && <p className="mt-1 text-11 text-danger">{report.errors.join("; ")}</p>}
    </div>
  );
}

function Kv({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex justify-between gap-2"><span className="text-fg-subtle">{label}</span><span className="tabular text-fg">{fmtInt(value)}</span></div>
  );
}

function ReportTab({ importId }: { importId: string }) {
  const job = useImportJob(importId);
  const j = job.data;
  const stats = (j?.stats ?? {}) as Record<string, unknown>;
  const isReport = "companies_created" in stats;

  function download() {
    const blob = new Blob([JSON.stringify({ import: j, report: stats }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `import-${importId}.json`; a.click();
    URL.revokeObjectURL(url);
  }

  if (job.isLoading) return <div className="grid place-items-center py-8"><Spinner size={18} /></div>;
  if (!j) return <ErrorState title="Not found" error={new Error("import not found")} />;
  if (!isReport)
    return <EmptyState title="Not committed yet" description="The import report appears here after you commit." />;

  const rows: [string, number][] = [
    ["Companies created", Number(stats.companies_created) || 0],
    ["Companies updated", Number(stats.companies_updated) || 0],
    ["Decision makers created", Number(stats.decision_makers_created) || 0],
    ["Decision makers updated", Number(stats.decision_makers_updated) || 0],
    ["Unchanged", Number(stats.unchanged) || 0],
    ["Duplicates skipped", Number(stats.duplicates_skipped) || 0],
    ["Conflicts skipped", Number(stats.conflicts_skipped) || 0],
    ["Invalid skipped", Number(stats.invalid_skipped) || 0],
  ];
  const warnings = (stats.warnings as string[]) ?? [];
  const errors = (stats.errors as string[]) ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Badge tone={IMPORT_STATUS_TONE[j.status] ?? "neutral"}>{enumLabel(j.status)}</Badge>
        <span className="text-12 text-fg-subtle">{fmtDuration(j.duration_ms)} · finished {j.finished_at ? fmtDateTime(j.finished_at) : "—"}</span>
        <Button size="sm" variant="default" className="ml-auto" onClick={download}>
          <Download size={13} /> Download report
        </Button>
      </div>
      <div className="panel grid grid-cols-2 divide-x divide-y divide-line sm:grid-cols-4 sm:divide-y-0">
        {rows.map(([label, val]) => (
          <div key={label} className="px-3.5 py-2.5">
            <div className="text-11 uppercase tracking-wide text-fg-subtle">{label}</div>
            <div className="tabular mt-1 text-18 text-fg">{fmtInt(val)}</div>
          </div>
        ))}
      </div>
      {warnings.length > 0 && (
        <div className="panel p-3">
          <div className="mb-1 text-12 font-medium text-warning">Warnings ({warnings.length})</div>
          <ul className="space-y-0.5 text-11 text-fg-muted">{warnings.slice(0, 50).map((w, i) => <li key={i}>• {w}</li>)}</ul>
        </div>
      )}
      {errors.length > 0 && (
        <div className="panel p-3">
          <div className="mb-1 text-12 font-medium text-danger">Errors ({errors.length})</div>
          <ul className="space-y-0.5 text-11 text-danger">{errors.map((e, i) => <li key={i}>• {e}</li>)}</ul>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ Audit
function AuditTab({ importId }: { importId: string }) {
  const audit = useImportAudit(importId);
  if (audit.isError) return <ErrorState title="Couldn't load audit trail" error={audit.error} onRetry={audit.refetch} />;
  if (audit.isLoading) return <div className="grid place-items-center py-8"><Spinner size={18} /></div>;
  const events = audit.data ?? [];
  if (events.length === 0) return <EmptyState title="No review activity yet" description="Approvals, rejections and field resolutions are recorded here." />;
  return (
    <div className="panel divide-y divide-line">
      {events.map((e, i) => (
        <div key={i} className="flex items-start gap-3 px-3.5 py-2 text-12">
          <Badge tone="neutral">{enumLabel(e.action)}</Badge>
          <div className="min-w-0 flex-1">
            <div className="truncate text-fg">
              {e.record_kind ? `${enumLabel(e.record_kind)} · ${e.source_ref}` : "bulk"}
              {e.field ? ` · ${e.field}` : ""}
            </div>
            {(e.previous_value || e.approved_value) && (
              <div className="truncate text-11 text-fg-subtle">{e.previous_value || "—"} → {e.approved_value || "—"}</div>
            )}
          </div>
          <div className="shrink-0 text-right text-11 text-fg-subtle">
            <div>{e.reviewer || "—"}</div>
            <div>{e.at ? fmtDateTime(e.at) : ""}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
