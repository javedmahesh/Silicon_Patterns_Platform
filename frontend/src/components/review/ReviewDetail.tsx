import { useState } from "react";

import { CompanyCombobox } from "@/components/CompanyCombobox";
import { KeyValueGrid } from "@/components/profile/KeyValueGrid";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { SkeletonLines } from "@/components/ui/Skeleton";
import { toast } from "@/components/ui/Toast";
import { useReviewActions, useReviewItem, useReviewMutations } from "@/lib/api/queries";
import { enumLabel, fmtDateTime, fmtRelative, fmtScore } from "@/lib/format";

type Tone = "positive" | "warning" | "danger" | "accent" | "neutral";
function statusTone(status: string): Tone {
  const s = status.toLowerCase();
  if (s === "approved") return "positive";
  if (s === "merged") return "accent";
  if (s === "rejected") return "danger";
  return "warning";
}

type Mode = "merge" | "reject" | "alias" | null;

export function ReviewDetail({ id }: { id: number }) {
  const item = useReviewItem(id);
  const actions = useReviewActions(id);
  const { approve, merge, reject, alias } = useReviewMutations();

  const [mode, setMode] = useState<Mode>(null);
  const [target, setTarget] = useState("");
  const [reason, setReason] = useState("");
  const [aliasName, setAliasName] = useState("");
  const [aliasDomain, setAliasDomain] = useState("");

  if (item.isLoading) return <SkeletonLines rows={6} />;
  if (item.isError || !item.data)
    return <ErrorState title="Couldn't load this item" error={item.error} onRetry={item.refetch} />;

  const it = item.data;
  const pending = it.status.toLowerCase() === "pending";
  const busy = approve.isPending || merge.isPending || reject.isPending || alias.isPending;

  const facts = [
    { label: "Raw name", value: it.raw_name || "—" },
    { label: "Raw domain", value: it.raw_domain || "—" },
    { label: "Website", value: it.raw_website || "—" },
    { label: "Source", value: enumLabel(it.source_engine) },
    { label: "Record", value: <span className="tabular text-11">{it.source_record_ref || "—"}</span> },
    { label: "Suggested", value: it.suggested_domain || "—" },
    { label: "Match", value: enumLabel(it.match_type) },
    { label: "Confidence", value: fmtScore(it.confidence, 2) },
    { label: "Resolved", value: it.resolved_domain || "—" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <Badge tone={statusTone(it.status)}>{enumLabel(it.status)}</Badge>
        <span className="text-11 text-fg-subtle">{fmtRelative(it.created_at)}</span>
      </div>

      <KeyValueGrid items={facts} />
      {it.notes && <p className="rounded-md border border-line bg-control px-2.5 py-2 text-12 text-fg-muted">{it.notes}</p>}

      {pending ? (
        <div className="space-y-3 border-t border-line pt-3">
          {mode === null && (
            <div className="flex flex-wrap gap-2">
              <Button
                variant="primary"
                size="sm"
                disabled={busy}
                onClick={() =>
                  approve.mutate({ id }, { onSuccess: () => toast("Stub approved", "positive") })
                }
              >
                Approve
              </Button>
              <Button size="sm" disabled={busy} onClick={() => { setMode("merge"); setTarget(it.suggested_domain || ""); }}>
                Merge…
              </Button>
              <Button size="sm" disabled={busy} onClick={() => { setMode("alias"); setAliasName(it.raw_name); setAliasDomain(it.suggested_domain || ""); }}>
                Alias…
              </Button>
              <Button variant="danger" size="sm" disabled={busy} onClick={() => { setMode("reject"); setReason(""); }}>
                Reject…
              </Button>
            </div>
          )}

          {mode === "merge" && (
            <div className="space-y-2">
              <div className="text-12 text-fg-muted">Merge this stub into a canonical company:</div>
              <CompanyCombobox value={target} onChange={setTarget} placeholder="Target company domain…" />
              <div className="flex gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  disabled={!target.trim() || busy}
                  onClick={() =>
                    merge.mutate(
                      { id, target: target.trim() },
                      { onSuccess: () => { toast("Merged", "positive"); setMode(null); } },
                    )
                  }
                >
                  Confirm merge
                </Button>
                <Button size="sm" onClick={() => setMode(null)}>Cancel</Button>
              </div>
            </div>
          )}

          {mode === "alias" && (
            <div className="space-y-2">
              <div className="text-12 text-fg-muted">Create a name → domain alias:</div>
              <Input value={aliasName} onChange={(e) => setAliasName(e.target.value)} placeholder="Name" />
              <CompanyCombobox value={aliasDomain} onChange={setAliasDomain} placeholder="Maps to company domain…" />
              <div className="flex gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  disabled={!aliasName.trim() || !aliasDomain.trim() || busy}
                  onClick={() =>
                    alias.mutate(
                      { id, name: aliasName.trim(), domain: aliasDomain.trim() },
                      { onSuccess: () => { toast("Alias created", "positive"); setMode(null); } },
                    )
                  }
                >
                  Create alias
                </Button>
                <Button size="sm" onClick={() => setMode(null)}>Cancel</Button>
              </div>
            </div>
          )}

          {mode === "reject" && (
            <div className="space-y-2">
              <div className="text-12 text-fg-muted">Reject (not a prospect):</div>
              <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason (optional)" />
              <div className="flex gap-2">
                <Button
                  variant="danger"
                  size="sm"
                  disabled={busy}
                  onClick={() =>
                    reject.mutate(
                      { id, reason: reason.trim() || undefined },
                      { onSuccess: () => { toast("Rejected"); setMode(null); } },
                    )
                  }
                >
                  Confirm reject
                </Button>
                <Button size="sm" onClick={() => setMode(null)}>Cancel</Button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="border-t border-line pt-3 text-12 text-fg-subtle">
          This item is resolved ({enumLabel(it.status)}).
        </div>
      )}

      <div>
        <div className="mb-1.5 text-11 uppercase tracking-wide text-fg-subtle">Audit trail</div>
        {actions.isLoading ? (
          <SkeletonLines rows={2} />
        ) : (actions.data?.length ?? 0) === 0 ? (
          <div className="text-12 text-fg-subtle">No actions yet.</div>
        ) : (
          <ol className="space-y-2">
            {actions.data!.map((a) => (
              <li key={a.id} className="flex items-start gap-2 text-12">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-line-strong" />
                <div className="min-w-0">
                  <span className="text-fg">{enumLabel(a.action)}</span>
                  <span className="text-fg-subtle">
                    {" "}
                    by {a.actor || "—"} · {fmtDateTime(a.created_at)}
                  </span>
                  {(a.from_domain || a.to_domain) && (
                    <div className="text-11 text-fg-subtle">
                      {a.from_domain || "—"} → {a.to_domain || "—"}
                    </div>
                  )}
                  {a.detail && <div className="text-11 text-fg-subtle">{a.detail}</div>}
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
