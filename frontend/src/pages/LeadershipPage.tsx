import { useState } from "react";
import { Megaphone, UserCog } from "lucide-react";

import { LeadershipSignalsSection } from "@/components/profile/LeadershipSignalsSection";
import { OpportunityDetailModal } from "@/components/opportunities/OpportunityDetailModal";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { EditRecordModal, type EditField } from "@/components/ui/EditRecordModal";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { SectionPanel } from "@/components/ui/SectionPanel";
import { SkeletonLines } from "@/components/ui/Skeleton";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  useDeleteLeadershipSignal,
  useLeadershipSignals,
  useOpportunities,
  useUpdateLeadershipSignal,
} from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/store";
import {
  CONFIDENCE_LEVELS,
  LEADERSHIP_MOVEMENT_TYPES,
  LEADERSHIP_PRIORITY_TIERS,
  LEADERSHIP_SENIORITY_BANDS,
} from "@/lib/enums";
import { enumLabel, fmtInt, fmtRelative } from "@/lib/format";
import type { LeadershipSignalOut } from "@/lib/api/types";

const LDR_FIELDS: EditField[] = [
  { name: "person_name", label: "Person name" },
  { name: "to_title", label: "New title" },
  { name: "from_title", label: "Previous title" },
  { name: "movement_type", label: "Movement", kind: "select", options: LEADERSHIP_MOVEMENT_TYPES },
  { name: "seniority_band", label: "Seniority", kind: "select", options: LEADERSHIP_SENIORITY_BANDS },
  { name: "confidence", label: "Confidence", kind: "select", options: CONFIDENCE_LEVELS },
  { name: "priority_tier", label: "Priority", kind: "select", options: LEADERSHIP_PRIORITY_TIERS },
  { name: "role_function", label: "Function" },
  { name: "geography", label: "Geography" },
  { name: "effective_date", label: "Effective (YYYY-MM)" },
  { name: "company_name", label: "Company" },
  { name: "linkedin_url", label: "LinkedIn URL", full: true },
  { name: "summary", label: "Summary", kind: "textarea" },
];

/** The Leadership hub: person-level leadership movement (who moved) as its own
 *  first-class section, plus the leadership-category market events. */
export function LeadershipPage() {
  const ldr = useLeadershipSignals({ page: 1, page_size: 100 });
  const opps = useOpportunities({ page: 1, page_size: 15, signal_category: "LEADERSHIP", sort: "newest" });
  const [activeId, setActiveId] = useState<string | undefined>(undefined);
  const { isAdmin } = useAuth();
  const delSig = useDeleteLeadershipSignal();
  const updSig = useUpdateLeadershipSignal();
  const [editSig, setEditSig] = useState<LeadershipSignalOut | null>(null);

  const onDeleteSignal = isAdmin
    ? (id: string) =>
        delSig.mutate(id, {
          onSuccess: () => toast("Leadership signal deleted", "positive"),
          onError: (e) => toast(apiErrorMessage(e), "danger"),
        })
    : undefined;
  const onEditSignal = isAdmin ? (sig: LeadershipSignalOut) => setEditSig(sig) : undefined;
  const saveSig = (patch: Record<string, string>) => {
    if (!editSig) return;
    if (Object.keys(patch).length === 0) return setEditSig(null);
    updSig.mutate(
      { id: editSig.signal_id, body: patch },
      {
        onSuccess: () => { setEditSig(null); toast("Leadership signal updated", "positive"); },
        onError: (e) => toast(apiErrorMessage(e), "danger"),
      },
    );
  };

  const signals = ldr.data?.items ?? [];

  return (
    <>
      <PageHeader
        title="Leadership"
        subtitle={
          ldr.data
            ? `${fmtInt(ldr.data.total)} leadership signals`
            : "Person-level leadership movement and leadership market events"
        }
      />

      <div className="space-y-4 p-4">
        <SectionPanel title="Leadership signals" icon={<UserCog size={15} />}>
          {ldr.isLoading ? (
            <div className="grid place-items-center py-8">
              <Spinner size={18} />
            </div>
          ) : ldr.isError ? (
            <ErrorState title="Couldn't load leadership signals" error={ldr.error} onRetry={ldr.refetch} />
          ) : (
            <LeadershipSignalsSection
              signals={signals}
              groupByCompany
              showCompany
              onDelete={onDeleteSignal}
              onEdit={onEditSignal}
              onViewSource={setActiveId}
              emptyHint="No director-level+ moves — hires, departures, promotions, board or founder changes — detected yet."
            />
          )}
        </SectionPanel>

        <SectionPanel title="Leadership market events" icon={<Megaphone size={15} />}>
          {opps.isLoading ? (
            <SkeletonLines rows={4} />
          ) : opps.isError ? (
            <ErrorState title="Couldn't load leadership events" error={opps.error} onRetry={opps.refetch} />
          ) : !opps.data || opps.data.items.length === 0 ? (
            <EmptyState
              icon={<Megaphone size={20} />}
              title="No leadership events"
              description="Executive hires, leadership and role changes surface here as they’re detected."
            />
          ) : (
            <div className="divide-y divide-line/60">
              {opps.data.items.map((o) => (
                <button
                  key={o.opportunity_id}
                  type="button"
                  onClick={() => setActiveId(o.opportunity_id)}
                  className="-mx-3.5 flex w-full items-start gap-3 px-3.5 py-2 text-left hover:bg-raised"
                >
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2">
                      {o.opportunity_type && <Badge tone="accent">{enumLabel(o.opportunity_type)}</Badge>}
                      <span className="text-11 text-fg-subtle">{fmtRelative(o.published_date)}</span>
                    </span>
                    <span className="mt-0.5 block truncate text-13 text-fg">
                      {o.article_title || o.company_name || o.company_domain}
                    </span>
                    <span className="block truncate text-11 text-fg-subtle">
                      {o.company_name || o.company_domain}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </SectionPanel>
      </div>

      <OpportunityDetailModal
        opportunityId={activeId}
        onClose={() => setActiveId(undefined)}
        onOpenOther={setActiveId}
      />

      {editSig && (
        <EditRecordModal
          open
          onClose={() => setEditSig(null)}
          title={`Edit signal — ${editSig.person_name}`}
          icon={<UserCog size={15} />}
          fields={LDR_FIELDS}
          initial={editSig as unknown as Record<string, unknown>}
          pending={updSig.isPending}
          error={updSig.isError ? updSig.error : undefined}
          onSubmit={saveSig}
        />
      )}
    </>
  );
}
