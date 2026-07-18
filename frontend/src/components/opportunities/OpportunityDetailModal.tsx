import { useState } from "react";
import { ExternalLink, GitMerge, Archive, Pencil, RotateCcw, Ban, Tag, StickyNote } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EditRecordModal, type EditField } from "@/components/ui/EditRecordModal";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  useDeleteOpportunity,
  useOpportunity,
  useOpportunityReview,
  useUpdateOpportunity,
} from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/store";
import type { OpportunityDetailOut } from "@/lib/api/types";
import { enumLabel, fmtDate, fmtRelative } from "@/lib/format";

const OPP_FIELDS: EditField[] = [
  { name: "article_title", label: "Title", full: true },
  { name: "opportunity_type", label: "Type" },
  { name: "published_date", label: "Published date" },
  { name: "company_name", label: "Company" },
  { name: "product_mentioned", label: "Product" },
  { name: "technology_focus", label: "Technology focus" },
  { name: "funding_stage", label: "Funding stage" },
  { name: "funding_amount", label: "Funding amount" },
  { name: "article_url", label: "Article URL", full: true },
  { name: "summary", label: "Summary", kind: "textarea" },
];

type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";
const LIFECYCLE_TONE: Record<string, Tone> = {
  NEW: "accent", ACTIVE: "positive", MONITORING: "warning", RESOLVED: "neutral", ARCHIVED: "neutral",
};
const LIFECYCLES = ["NEW", "ACTIVE", "MONITORING", "RESOLVED", "ARCHIVED"];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-line pt-3">
      <div className="mb-1.5 text-11 font-semibold uppercase tracking-wide text-fg-subtle">{title}</div>
      {children}
    </div>
  );
}

function Chips({ items, tone = "neutral" }: { items: string[]; tone?: Tone }) {
  if (!items?.length) return <span className="text-12 text-fg-subtle">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((it) => (
        <Badge key={it} tone={tone}>{it}</Badge>
      ))}
    </div>
  );
}

function ConfidenceBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-28 shrink-0 text-11 text-fg-muted">{enumLabel(label)}</div>
      <div className="h-1.5 flex-1 overflow-hidden rounded bg-raised">
        <div className="h-full rounded bg-accent" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      </div>
      <div className="w-8 shrink-0 text-right text-11 tabular-nums text-fg-muted">{value}</div>
    </div>
  );
}

export function OpportunityDetailModal({
  opportunityId,
  onClose,
  onOpenOther,
}: {
  opportunityId: string | undefined;
  onClose: () => void;
  onOpenOther?: (id: string) => void;
}) {
  const { data, isLoading, isError, error, refetch } = useOpportunity(opportunityId);
  const { review, setLifecycle } = useOpportunityReview();
  const { isAdmin } = useAuth();
  const del = useDeleteOpportunity();
  const upd = useUpdateOpportunity();
  const [note, setNote] = useState("");
  const [editing, setEditing] = useState(false);
  const busy = review.isPending || setLifecycle.isPending || del.isPending;

  function deleteOpp() {
    if (!opportunityId) return;
    del.mutate(opportunityId, {
      onSuccess: () => { toast("Opportunity deleted", "positive"); onClose(); },
      onError: (e) => toast(apiErrorMessage(e), "danger"),
    });
  }

  function saveEdit(patch: Record<string, string>) {
    if (!opportunityId) return;
    if (Object.keys(patch).length === 0) return setEditing(false);
    upd.mutate(
      { id: opportunityId, body: patch },
      {
        onSuccess: () => { setEditing(false); toast("Opportunity updated", "positive"); },
        onError: (e) => toast(apiErrorMessage(e), "danger"),
      },
    );
  }

  function act(action: string, extra: Record<string, unknown> = {}) {
    if (!opportunityId) return;
    review.mutate(
      { id: opportunityId, body: { action, detail: note, ...extra } as any },
      {
        onSuccess: () => { toast(`Applied: ${enumLabel(action)}`, "positive"); setNote(""); },
        onError: (e) => toast(apiErrorMessage(e), "danger"),
      },
    );
  }

  function changeLifecycle(next: string) {
    if (!opportunityId || !data || next === data.lifecycle_status) return;
    setLifecycle.mutate(
      { id: opportunityId, lifecycle_status: next },
      {
        onSuccess: () => toast(`Lifecycle → ${enumLabel(next)}`, "positive"),
        onError: (e) => toast(apiErrorMessage(e), "danger"),
      },
    );
  }

  return (
    <>
    <Modal
      open={Boolean(opportunityId)}
      onClose={onClose}
      width="max-w-3xl"
      title={data ? (data.article_title || enumLabel(data.opportunity_type) || "Opportunity") : "Opportunity"}
    >
      {isLoading ? (
        <div className="flex h-40 items-center justify-center"><Spinner /></div>
      ) : isError ? (
        <ErrorState title="Couldn't load opportunity" error={error} onRetry={refetch} />
      ) : !data ? (
        <EmptyState title="Not found" description="This opportunity no longer exists." />
      ) : (
        <Detail
          data={data}
          note={note}
          setNote={setNote}
          busy={busy}
          act={act}
          changeLifecycle={changeLifecycle}
          onOpenOther={onOpenOther}
          isAdmin={isAdmin}
          onDelete={deleteOpp}
          onEdit={() => setEditing(true)}
        />
      )}
    </Modal>
    {editing && data && (
      <EditRecordModal
        open
        onClose={() => setEditing(false)}
        title="Edit opportunity"
        icon={<Pencil size={15} />}
        fields={OPP_FIELDS}
        initial={data as unknown as Record<string, unknown>}
        pending={upd.isPending}
        error={upd.isError ? upd.error : undefined}
        onSubmit={saveEdit}
      />
    )}
    </>
  );
}

function Detail({
  data, note, setNote, busy, act, changeLifecycle, onOpenOther, isAdmin, onDelete, onEdit,
}: {
  data: OpportunityDetailOut;
  note: string;
  setNote: (v: string) => void;
  busy: boolean;
  act: (action: string, extra?: Record<string, unknown>) => void;
  changeLifecycle: (next: string) => void;
  onOpenOther?: (id: string) => void;
  isAdmin: boolean;
  onDelete: () => void;
  onEdit: () => void;
}) {
  return (
    <div className="space-y-3.5">
      {/* header meta */}
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="accent">{enumLabel(data.opportunity_type)}</Badge>
        {data.opportunity_subtype && <Badge tone="neutral">{enumLabel(data.opportunity_subtype)}</Badge>}
        <Badge tone={LIFECYCLE_TONE[data.lifecycle_status] ?? "neutral"}>{enumLabel(data.lifecycle_status)}</Badge>
        {!data.is_relevant && <Badge tone="danger">Not relevant</Badge>}
        <span className="text-12 text-fg-muted">{data.company_name || data.company_domain}</span>
        <span className="text-11 text-fg-subtle">· {data.company_domain}</span>
        <span className="ml-auto text-11 text-fg-subtle" title={fmtDate(data.published_date)}>
          {fmtRelative(data.published_date)}
        </span>
      </div>

      {/* scores */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          ["Opportunity", data.effective_opportunity_score || data.opportunity_score],
          ["Confidence", data.confidence_score],
          ["Source cred.", data.source_credibility],
          ["Readiness", data.lead_readiness_score],
        ].map(([label, val]) => (
          <div key={label as string} className="rounded-md border border-line bg-raised px-2.5 py-1.5">
            <div className="text-11 text-fg-subtle">{label}</div>
            <div className="text-15 font-semibold tabular-nums text-fg">{val as number}</div>
          </div>
        ))}
      </div>

      {data.executive_summary && (
        <Section title="Executive Summary"><p className="text-13 text-fg">{data.executive_summary}</p></Section>
      )}
      {data.ai_summary && (
        <Section title="AI Summary"><p className="text-13 text-fg-muted">{data.ai_summary}</p></Section>
      )}
      {data.why_this_matters && (
        <Section title="Why This Matters"><p className="text-13 text-fg-muted">{data.why_this_matters}</p></Section>
      )}
      {data.business_impact && (
        <Section title="Business Impact"><p className="text-13 text-fg-muted">{data.business_impact}</p></Section>
      )}

      {/* entities */}
      <Section title="Entities">
        <div className="grid gap-2 sm:grid-cols-2">
          <Field label="Technologies"><Chips items={data.technologies} tone="accent" /></Field>
          <Field label="Products"><Chips items={data.products} /></Field>
          <Field label="People"><Chips items={data.people} /></Field>
          <Field label="Organizations"><Chips items={data.organizations} /></Field>
          <Field label="Countries"><Chips items={data.countries} /></Field>
          <Field label="Keywords"><Chips items={data.keywords} /></Field>
        </div>
      </Section>

      {/* confidence breakdown */}
      {data.confidence_breakdown && Object.keys(data.confidence_breakdown).length > 0 && (
        <Section title="Confidence Breakdown">
          <div className="space-y-1.5">
            {Object.entries(data.confidence_breakdown).map(([k, v]) => (
              <ConfidenceBar key={k} label={k} value={Number(v)} />
            ))}
          </div>
        </Section>
      )}

      {data.ai_reasoning && (
        <Section title="AI Reasoning"><p className="text-12 italic text-fg-muted">{data.ai_reasoning}</p></Section>
      )}

      {/* sources */}
      <Section title={`Reporting Sources (${data.sources.length})`}>
        {data.sources.length === 0 ? (
          <span className="text-12 text-fg-subtle">—</span>
        ) : (
          <ul className="space-y-1">
            {data.sources.map((s) => (
              <li key={s.id} className="flex items-center gap-2 text-12">
                {s.url ? (
                  <a href={s.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-fg hover:text-accent">
                    <span className="line-clamp-1 max-w-[380px]">{s.title || s.url}</span>
                    <ExternalLink size={11} className="shrink-0 text-fg-subtle" />
                  </a>
                ) : (
                  <span className="line-clamp-1 max-w-[380px] text-fg-muted">{s.title || "—"}</span>
                )}
                {s.publisher && <span className="text-fg-subtle">· {s.publisher}</span>}
                {s.credibility > 0 && <Badge tone="neutral">cred {s.credibility}</Badge>}
              </li>
            ))}
          </ul>
        )}
      </Section>

      {/* related */}
      {data.related.length > 0 && (
        <Section title={`Related Opportunities (${data.related.length})`}>
          <ul className="space-y-1">
            {data.related.map((r) => (
              <li key={r.opportunity_id}>
                <button
                  className="inline-flex items-center gap-2 text-12 text-fg hover:text-accent"
                  onClick={() => onOpenOther?.(r.opportunity_id)}
                >
                  <Badge tone="accent">{enumLabel(r.opportunity_type)}</Badge>
                  <span className="line-clamp-1 max-w-[420px]">{r.article_title || r.opportunity_id}</span>
                </button>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* timeline */}
      {data.timeline.length > 0 && (
        <Section title={`Company Timeline (${data.timeline.length})`}>
          <ol className="space-y-1">
            {data.timeline.map((t) => (
              <li
                key={t.opportunity_id}
                className={"flex items-center gap-2 text-12 " + (t.is_current ? "font-medium text-fg" : "text-fg-muted")}
              >
                <span className="w-20 shrink-0 tabular-nums text-fg-subtle">{fmtDate(t.published_date) || "—"}</span>
                <Badge tone={t.is_current ? "accent" : "neutral"}>{enumLabel(t.opportunity_type)}</Badge>
                <span className="line-clamp-1">{t.article_title || t.opportunity_id}</span>
              </li>
            ))}
          </ol>
        </Section>
      )}

      {/* review history */}
      {data.reviews.length > 0 && (
        <Section title={`Review History (${data.reviews.length})`}>
          <ul className="space-y-1">
            {data.reviews.map((r) => (
              <li key={r.id} className="text-12 text-fg-muted">
                <span className="font-medium text-fg">{enumLabel(r.action)}</span>
                {r.actor_email && <span className="text-fg-subtle"> · {r.actor_email}</span>}
                {r.detail && <span> — {r.detail}</span>}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* manual review actions */}
      <Section title="Manual Review">
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-11 text-fg-subtle">Lifecycle</label>
          <select
            className="h-7 rounded-md border border-line-strong bg-control px-2 text-12 text-fg"
            value={data.lifecycle_status}
            disabled={busy}
            onChange={(e) => changeLifecycle(e.target.value)}
          >
            {LIFECYCLES.map((l) => <option key={l} value={l}>{enumLabel(l)}</option>)}
          </select>
        </div>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Internal note / reason (stored in review history, never overwrites AI output)…"
          className="mt-2 w-full resize-none rounded-md border border-line-strong bg-control px-2.5 py-1.5 text-12 text-fg placeholder:text-fg-subtle"
          rows={2}
        />
        <div className="mt-2 flex flex-wrap gap-2">
          <Button size="sm" variant="default" disabled={busy} onClick={() => act("note")}>
            <StickyNote size={13} /> Add note
          </Button>
          {data.is_relevant ? (
            <Button size="sm" variant="danger" disabled={busy} onClick={() => act("not_relevant")}>
              <Ban size={13} /> Not relevant
            </Button>
          ) : (
            <Button size="sm" variant="default" disabled={busy} onClick={() => act("restore")}>
              <RotateCcw size={13} /> Restore
            </Button>
          )}
          <Button size="sm" variant="default" disabled={busy} onClick={() => act("archive")}>
            <Archive size={13} /> Archive
          </Button>
          <Button size="sm" variant="default" disabled={busy} onClick={() => act("split")}>
            <GitMerge size={13} className="rotate-180" /> Split
          </Button>
          <ChangeType busy={busy} onApply={(t) => act("change_type", { new_type: t })} />
          <MergeInto busy={busy} onApply={(id) => act("merge", { target_opportunity_id: id })} />
        </div>
        {/* Admin-only: permanently remove this Blog Crawler / news entry. */}
        {isAdmin && (
          <div className="mt-3 flex items-center gap-2 border-t border-line pt-3">
            <Button size="sm" variant="default" disabled={busy} onClick={onEdit}>
              <Pencil size={13} /> Edit
            </Button>
            <DeleteConfirm busy={busy} onDelete={onDelete} noun="opportunity" />
          </div>
        )}
      </Section>
    </div>
  );
}

/** Two-click confirm for a destructive delete (admin only). */
function DeleteConfirm({ busy, onDelete, noun }: { busy: boolean; onDelete: () => void; noun: string }) {
  const [confirming, setConfirming] = useState(false);
  if (!confirming) {
    return (
      <Button size="sm" variant="danger" disabled={busy} onClick={() => setConfirming(true)}>
        Delete {noun}
      </Button>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-12 text-danger">Permanently delete this {noun}? This can’t be undone.</span>
      <Button size="sm" variant="danger" disabled={busy} onClick={onDelete}>
        {busy ? <Spinner size={13} /> : null} Confirm delete
      </Button>
      <Button size="sm" variant="ghost" disabled={busy} onClick={() => setConfirming(false)}>Cancel</Button>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-11 text-fg-subtle">{label}</div>
      <div className="mt-0.5">{children}</div>
    </div>
  );
}

const TYPES = ["FUNDING", "ACQUISITION", "PRODUCT_LAUNCH", "EXPANSION", "HIRING",
  "PARTNERSHIP", "EXECUTIVE_HIRE", "LEADERSHIP_CHANGE", "IPO", "CONTRACT_WIN", "COMPANY_NEWS"];

function ChangeType({ busy, onApply }: { busy: boolean; onApply: (t: string) => void }) {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState(TYPES[0]);
  if (!open) {
    return (
      <Button size="sm" variant="default" disabled={busy} onClick={() => setOpen(true)}>
        <Tag size={13} /> Change type
      </Button>
    );
  }
  return (
    <span className="inline-flex items-center gap-1">
      <select
        className="h-7 rounded-md border border-line-strong bg-control px-2 text-12 text-fg"
        value={type}
        onChange={(e) => setType(e.target.value)}
      >
        {TYPES.map((t) => <option key={t} value={t}>{enumLabel(t)}</option>)}
      </select>
      <Button size="sm" variant="primary" disabled={busy} onClick={() => { onApply(type); setOpen(false); }}>
        Apply
      </Button>
    </span>
  );
}

function MergeInto({ busy, onApply }: { busy: boolean; onApply: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const [id, setId] = useState("");
  if (!open) {
    return (
      <Button size="sm" variant="default" disabled={busy} onClick={() => setOpen(true)}>
        <GitMerge size={13} /> Merge
      </Button>
    );
  }
  return (
    <span className="inline-flex items-center gap-1">
      <input
        value={id}
        onChange={(e) => setId(e.target.value)}
        placeholder="target opportunity_id"
        className="h-7 w-56 rounded-md border border-line-strong bg-control px-2 text-12 text-fg placeholder:text-fg-subtle"
      />
      <Button size="sm" variant="primary" disabled={busy || !id} onClick={() => { onApply(id.trim()); setOpen(false); setId(""); }}>
        Apply
      </Button>
    </span>
  );
}
