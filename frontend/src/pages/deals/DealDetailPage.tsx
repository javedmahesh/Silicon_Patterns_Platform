import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { DealFormModal } from "@/components/deals/DealFormModal";
import { ForecastCategoryBadge, StageTypeBadge, fmtMoney } from "@/components/deals/bits";
import { KeyValueGrid } from "@/components/profile/KeyValueGrid";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { Tabs } from "@/components/ui/Tabs";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  useDeal,
  useDealHistory,
  useDealIntelligence,
  useDealMutations,
  useDealTimeline,
  usePipeline,
} from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/store";
import { fmtDate, fmtDateTime, fmtRelative } from "@/lib/format";

type Tab = "overview" | "history" | "activity";

function CloseDealModal({
  outcome, dealId, targetStageId, onClose,
}: {
  outcome: "won" | "lost";
  dealId: number;
  targetStageId: number;
  onClose: () => void;
}) {
  const [reason, setReason] = useState("");
  const { patch, move } = useDealMutations();
  const pending = patch.isPending || move.isPending;

  function submit() {
    const patchBody = outcome === "won" ? { won_reason: reason.trim() } : { lost_reason: reason.trim() };
    patch.mutate({ id: dealId, body: patchBody }, {
      onSuccess: () => {
        move.mutate({ id: dealId, stageId: targetStageId }, {
          onSuccess: () => { toast(outcome === "won" ? "Deal marked won" : "Deal marked lost", "positive"); onClose(); },
          onError: (e) => toast(apiErrorMessage(e), "danger"),
        });
      },
      onError: (e) => toast(apiErrorMessage(e), "danger"),
    });
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={outcome === "won" ? "Close as Won" : "Close as Lost"}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={pending}>Cancel</Button>
          <Button variant={outcome === "won" ? "primary" : "danger"} onClick={submit} disabled={pending}>
            {pending ? "Saving…" : outcome === "won" ? "Mark Won" : "Mark Lost"}
          </Button>
        </>
      }
    >
      <label className="block">
        <span className="mb-1 block text-11 text-fg-muted">{outcome === "won" ? "Won reason (optional)" : "Lost reason (optional)"}</span>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={2}
          autoFocus
          placeholder={outcome === "won" ? "Why did we win this deal?" : "Why did we lose this deal?"}
          className="w-full resize-y rounded-md border border-line bg-control px-2.5 py-1.5 text-13 text-fg outline-none focus:border-accent"
        />
      </label>
    </Modal>
  );
}

function IntelligenceTab({ dealId }: { dealId: number }) {
  const { data, isLoading, isError } = useDealIntelligence(dealId);
  if (isLoading) return <div className="grid place-items-center py-6"><Spinner size={16} /></div>;
  if (isError || !data) return <p className="text-12 text-fg-subtle">No intelligence available for this account yet.</p>;

  return (
    <div className="space-y-3">
      {data.best_contact && (
        <div>
          <div className="text-11 text-fg-subtle">Best contact</div>
          <div className="text-13 text-fg">{data.best_contact.full_name} — {data.best_contact.title}</div>
          <div className="text-11 text-fg-subtle">{data.best_contact.email}</div>
        </div>
      )}
      {data.success_probability && (
        <div>
          <div className="text-11 text-fg-subtle">Success probability</div>
          <div className="flex items-center gap-2">
            <span className="tabular text-13 text-fg">{data.success_probability.probability}%</span>
            <Badge tone={data.success_probability.confidence_level === "High" ? "positive" : "neutral"}>
              {data.success_probability.confidence_level} confidence
            </Badge>
          </div>
        </div>
      )}
      {data.next_action && (
        <div>
          <div className="text-11 text-fg-subtle">Next action</div>
          <div className="text-13 text-fg">{data.next_action.action}</div>
          {data.next_action.reason && <div className="text-11 text-fg-subtle">{data.next_action.reason}</div>}
        </div>
      )}
      {data.buying_committee && data.buying_committee.total > 0 && (
        <div>
          <div className="text-11 text-fg-subtle">Buying committee coverage</div>
          <div className="text-13 text-fg">{data.buying_committee.present} / {data.buying_committee.total} roles covered ({data.buying_committee.coverage_pct}%)</div>
        </div>
      )}
      {!data.best_contact && !data.success_probability && !data.next_action && (!data.buying_committee || data.buying_committee.total === 0) && (
        <p className="text-12 text-fg-subtle">Not enough signal yet to surface recommendations for this account.</p>
      )}
    </div>
  );
}

export function DealDetailPage() {
  const { id } = useParams();
  const dealId = Number(id);
  const navigate = useNavigate();
  const { isManager } = useAuth();
  const [tab, setTab] = useState<Tab>("overview");
  const [editing, setEditing] = useState(false);
  const [closing, setClosing] = useState<"won" | "lost" | null>(null);
  const [deleting, setDeleting] = useState(false);

  const { data: deal, isLoading, isError, error, refetch } = useDeal(dealId);
  const { data: pipeline } = usePipeline(deal?.pipeline_id);
  const { remove } = useDealMutations();

  if (isError) return <div className="p-4"><ErrorState title="Couldn't load deal" error={error} onRetry={refetch} /></div>;
  if (isLoading || !deal) return <div className="grid h-full place-items-center"><Spinner size={20} /></div>;

  const wonStage = pipeline?.stages.find((s) => s.stage_type === "won");
  const lostStage = pipeline?.stages.find((s) => s.stage_type === "lost");
  const currentStage = pipeline?.stages.find((s) => s.id === deal.stage_id);
  const isClosed = currentStage?.stage_type === "won" || currentStage?.stage_type === "lost";

  function confirmDelete() {
    remove.mutate(dealId, {
      onSuccess: () => { toast("Deal deleted", "positive"); navigate("/deals/list"); },
      onError: (e) => { toast(apiErrorMessage(e), "danger"); setDeleting(false); },
    });
  }

  return (
    <>
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            <Link to="/deals/list" className="text-fg-subtle hover:text-fg" aria-label="Back to deals"><ArrowLeft size={16} /></Link>
            {deal.title}
            {currentStage && <StageTypeBadge stageType={currentStage.stage_type} />}
          </span>
        }
        subtitle={
          <Link to={`/companies/${encodeURIComponent(deal.company_domain)}`} className="hover:text-accent">
            {deal.company_domain}
          </Link>
        }
        actions={
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => setEditing(true)}>Edit</Button>
            {!isClosed && wonStage && <Button size="sm" variant="primary" onClick={() => setClosing("won")}>Close Won</Button>}
            {!isClosed && lostStage && <Button size="sm" variant="danger" onClick={() => setClosing("lost")}>Close Lost</Button>}
            {isManager && <Button size="sm" variant="danger" onClick={() => setDeleting(true)}>Delete</Button>}
          </div>
        }
      >
        <Tabs
          tabs={[
            { id: "overview", label: "Overview" },
            { id: "history", label: "History" },
            { id: "activity", label: "Activity" },
          ]}
          active={tab}
          onChange={setTab}
        />
      </PageHeader>

      <div className="p-4">
        {tab === "overview" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="panel p-3.5">
              <div className="mb-2 text-13 font-medium text-fg">Details</div>
              <KeyValueGrid
                items={[
                  { label: "Stage", value: currentStage?.name ?? "—" },
                  { label: "Owner", value: deal.owner_email || "—" },
                  { label: "Value", value: fmtMoney(deal.value, deal.currency) },
                  { label: "Probability", value: `${deal.probability}%` },
                  { label: "Forecast", value: <ForecastCategoryBadge category={deal.forecast_category} /> },
                  { label: "Expected close", value: deal.expected_close_date ? fmtDate(deal.expected_close_date) : "—" },
                  { label: "Last activity", value: deal.last_activity_at ? fmtRelative(deal.last_activity_at) : "—" },
                  { label: "Created", value: fmtDateTime(deal.created_at) },
                  { label: "Updated", value: fmtDateTime(deal.updated_at) },
                  ...(deal.won_reason ? [{ label: "Won reason", value: deal.won_reason }] : []),
                  ...(deal.lost_reason ? [{ label: "Lost reason", value: deal.lost_reason }] : []),
                ]}
              />
              {deal.notes && (
                <>
                  <div className="mb-1 mt-3 text-13 font-medium text-fg">Notes</div>
                  <p className="whitespace-pre-wrap text-12 text-fg-muted">{deal.notes}</p>
                </>
              )}
            </div>
            <div className="panel p-3.5">
              <div className="mb-2 text-13 font-medium text-fg">Account intelligence</div>
              <IntelligenceTab dealId={dealId} />
            </div>
          </div>
        )}
        {tab === "history" && <HistoryTab dealId={dealId} pipeline={pipeline} />}
        {tab === "activity" && <ActivityTab dealId={dealId} />}
      </div>

      {editing && <DealFormModal deal={deal} onClose={() => setEditing(false)} />}
      {closing && wonStage && lostStage && (
        <CloseDealModal
          outcome={closing}
          dealId={dealId}
          targetStageId={closing === "won" ? wonStage.id : lostStage.id}
          onClose={() => setClosing(null)}
        />
      )}
      {deleting && (
        <Modal
          open
          onClose={() => setDeleting(false)}
          title="Delete deal"
          footer={
            <>
              <Button variant="ghost" onClick={() => setDeleting(false)} disabled={remove.isPending}>Cancel</Button>
              <Button variant="danger" onClick={confirmDelete} disabled={remove.isPending}>Delete</Button>
            </>
          }
        >
          <p className="text-13 text-fg-muted">Delete “{deal.title}”? This permanently removes the deal and its stage history.</p>
        </Modal>
      )}
    </>
  );
}

function HistoryTab({ dealId, pipeline }: { dealId: number; pipeline: import("@/lib/api/types").PipelineOut | undefined }) {
  const { data, isLoading, isError, error, refetch } = useDealHistory(dealId);
  if (isLoading) return <div className="grid place-items-center py-12"><Spinner size={18} /></div>;
  if (isError) return <ErrorState title="Couldn't load history" error={error} onRetry={refetch} />;
  if (!data || data.length === 0) return <div className="panel"><EmptyState title="No stage history yet" /></div>;
  const stageName = (id: number | null) => pipeline?.stages.find((s) => s.id === id)?.name ?? (id ? `Stage #${id}` : "—");
  return (
    <div className="panel divide-y divide-line">
      {data.map((h) => (
        <div key={h.id} className="flex items-center justify-between gap-2 px-3.5 py-2 text-12">
          <span className="text-fg-muted">{stageName(h.from_stage_id)} → {stageName(h.to_stage_id)}</span>
          <span className="shrink-0 text-11 text-fg-subtle">
            {fmtRelative(h.entered_at)}
            {h.time_in_stage_seconds != null && ` · ${Math.round(h.time_in_stage_seconds / 86400)}d in stage`}
          </span>
        </div>
      ))}
    </div>
  );
}

function ActivityTab({ dealId }: { dealId: number }) {
  const { data, isLoading, isError, error, refetch } = useDealTimeline(dealId);
  if (isLoading) return <div className="grid place-items-center py-12"><Spinner size={18} /></div>;
  if (isError) return <ErrorState title="Couldn't load activity" error={error} onRetry={refetch} />;
  if (!data || data.length === 0) return <div className="panel"><EmptyState title="No activity yet" /></div>;
  return (
    <div className="panel divide-y divide-line">
      {data.map((e) => (
        <div key={e.event_id} className="flex items-center justify-between gap-2 px-3.5 py-2 text-12">
          <span className="text-fg-muted"><span className="font-medium text-fg">{e.label}</span>{e.detail ? ` — ${e.detail}` : ""}</span>
          <span className="shrink-0 text-11 text-fg-subtle">{e.actor ? e.actor.split("@")[0] : "system"} · {fmtRelative(e.timestamp)}</span>
        </div>
      ))}
    </div>
  );
}
