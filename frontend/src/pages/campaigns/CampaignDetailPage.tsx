import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Trash2 } from "lucide-react";

import { CampaignFormModal } from "@/components/campaigns/CampaignFormModal";
import { CampaignStatusBadge, MemberStatusBadge, OutcomeBadge } from "@/components/campaigns/bits";
import { KeyValueGrid } from "@/components/profile/KeyValueGrid";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { StatStrip, type Stat } from "@/components/data/StatStrip";
import { Pager } from "@/components/data/Pager";
import { Tabs } from "@/components/ui/Tabs";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  useCampaign,
  useCampaignAnalytics,
  useCampaignMemberMutations,
  useCampaignMembers,
  useCampaignMutations,
  useCampaignTimeline,
  useCompanies,
  useSequences,
} from "@/lib/api/queries";
import { CAMPAIGN_OUTCOMES, type CampaignMemberOut } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/store";
import { enumLabel, fmtDate, fmtDateTime, fmtInt, fmtPct, fmtRelative } from "@/lib/format";

type Tab = "overview" | "members" | "activity";
const PAGE_SIZE = 25;

export function CampaignDetailPage() {
  const { id } = useParams();
  const campaignId = Number(id);
  const { isManager } = useAuth();
  const [tab, setTab] = useState<Tab>("overview");
  const [editing, setEditing] = useState(false);
  const [archiving, setArchiving] = useState(false);

  const { data: campaign, isLoading, isError, error, refetch } = useCampaign(campaignId);
  const { archive } = useCampaignMutations();

  if (isError) return <div className="p-4"><ErrorState title="Couldn't load campaign" error={error} onRetry={refetch} /></div>;
  if (isLoading || !campaign) return <div className="grid h-full place-items-center"><Spinner size={20} /></div>;

  function confirmArchive() {
    archive.mutate(campaignId, {
      onSuccess: () => { toast("Campaign archived", "positive"); setArchiving(false); },
      onError: (e) => { toast(apiErrorMessage(e), "danger"); setArchiving(false); },
    });
  }

  return (
    <>
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            <Link to="/campaigns" className="text-fg-subtle hover:text-fg" aria-label="Back to campaigns"><ArrowLeft size={16} /></Link>
            {campaign.name}
            <CampaignStatusBadge status={campaign.status} />
          </span>
        }
        subtitle={campaign.owner_email ? `Owned by ${campaign.owner_email}` : undefined}
        actions={
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => setEditing(true)}>Edit</Button>
            {isManager && campaign.status !== "archived" && (
              <Button size="sm" variant="danger" onClick={() => setArchiving(true)}>Archive</Button>
            )}
          </div>
        }
      >
        <Tabs
          tabs={[
            { id: "overview", label: "Overview" },
            { id: "members", label: "Members", count: campaign.member_count },
            { id: "activity", label: "Activity" },
          ]}
          active={tab}
          onChange={setTab}
        />
      </PageHeader>

      <div className="p-4">
        {tab === "overview" && <OverviewTab campaign={campaign} />}
        {tab === "members" && <MembersTab campaignId={campaignId} />}
        {tab === "activity" && <ActivityTab campaignId={campaignId} />}
      </div>

      {editing && <CampaignFormModal campaign={campaign} onClose={() => setEditing(false)} />}
      {archiving && (
        <Modal
          open
          onClose={() => setArchiving(false)}
          title="Archive campaign"
          footer={
            <>
              <Button variant="ghost" onClick={() => setArchiving(false)} disabled={archive.isPending}>Cancel</Button>
              <Button variant="danger" onClick={confirmArchive} disabled={archive.isPending}>Archive</Button>
            </>
          }
        >
          <p className="text-13 text-fg-muted">Archive “{campaign.name}”? Its history is kept, but it moves out of active views.</p>
        </Modal>
      )}
    </>
  );
}

function OverviewTab({ campaign }: { campaign: import("@/lib/api/types").CampaignOut }) {
  const analytics = useCampaignAnalytics(campaign.id);

  const stats: Stat[] = analytics.data
    ? [
        { label: "Companies contacted", value: fmtInt(analytics.data.companies_contacted) },
        { label: "Decision makers", value: fmtInt(analytics.data.decision_makers_contacted) },
        { label: "Emails sent", value: fmtInt(analytics.data.emails_sent) },
        { label: "Reply rate", value: fmtPct(analytics.data.reply_rate) },
        { label: "Meeting rate", value: fmtPct(analytics.data.meeting_rate) },
        { label: "Conversion rate", value: fmtPct(analytics.data.conversion_rate) },
      ]
    : [];

  return (
    <div className="space-y-4">
      {analytics.isLoading ? (
        <div className="grid place-items-center py-8"><Spinner size={18} /></div>
      ) : analytics.isError ? (
        <ErrorState title="Couldn't load analytics" error={analytics.error} onRetry={analytics.refetch} />
      ) : (
        stats.length > 0 && <StatStrip stats={stats} />
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="panel p-3.5">
          <div className="mb-2 text-13 font-medium text-fg">Details</div>
          <KeyValueGrid
            items={[
              { label: "Type", value: enumLabel(campaign.campaign_type) },
              { label: "Goal", value: campaign.goal || "—" },
              { label: "Budget", value: campaign.budget != null ? `$${fmtInt(campaign.budget)}` : "—" },
              { label: "Start date", value: campaign.start_date ? fmtDate(campaign.start_date) : "—" },
              { label: "End date", value: campaign.end_date ? fmtDate(campaign.end_date) : "—" },
              { label: "Created", value: fmtDateTime(campaign.created_at) },
              { label: "Updated", value: fmtDateTime(campaign.updated_at) },
              {
                label: "Tags",
                value: campaign.tags.length > 0
                  ? campaign.tags.map((t) => <span key={t} className="mr-1 rounded bg-control px-1 text-11">{t}</span>)
                  : "—",
              },
            ]}
          />
        </div>
        {campaign.description && (
          <div className="panel p-3.5">
            <div className="mb-2 text-13 font-medium text-fg">Description</div>
            <p className="whitespace-pre-wrap text-12 text-fg-muted">{campaign.description}</p>
          </div>
        )}
      </div>

      {analytics.data && (
        <div className="panel p-3.5">
          <div className="mb-2 text-13 font-medium text-fg">Sequence completion</div>
          <div className="flex items-center gap-3">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-control">
              <div className="h-full rounded-full bg-accent" style={{ width: `${Math.round(analytics.data.sequence_completion_rate * 100)}%` }} />
            </div>
            <span className="tabular text-12 text-fg-muted">{fmtPct(analytics.data.sequence_completion_rate)}</span>
          </div>
        </div>
      )}
    </div>
  );
}

function AddMemberForm({ campaignId, onDone }: { campaignId: number; onDone: () => void }) {
  const [q, setQ] = useState("");
  const [domain, setDomain] = useState("");
  const [companyName, setCompanyName] = useState("");
  const { data: search } = useCompanies({ q, page_size: 6 });
  const { addMember } = useCampaignMemberMutations(campaignId);

  function submit() {
    if (!domain) return;
    addMember.mutate(
      { company_domain: domain },
      {
        onSuccess: () => { toast("Member added", "positive"); onDone(); },
        onError: (e) => toast(apiErrorMessage(e), "danger"),
      },
    );
  }

  return (
    <div className="panel p-3.5">
      <div className="mb-2 text-13 font-medium text-fg">Add a company to this campaign</div>
      <div className="flex items-start gap-2">
        <div className="relative flex-1">
          <DebouncedInput
            value={domain ? companyName : q}
            onChange={(v) => { setQ(v); setDomain(""); }}
            placeholder="Search company…"
            className="w-full"
          />
          {q && !domain && search && search.items.length > 0 && (
            <div className="absolute z-10 mt-1 w-full rounded-md border border-line bg-raised py-1 shadow-lg">
              {search.items.map((c) => (
                <button
                  key={c.company_domain}
                  type="button"
                  onClick={() => { setDomain(c.company_domain); setCompanyName(c.company_name); setQ(""); }}
                  className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left text-12 hover:bg-control"
                >
                  <span className="truncate text-fg">{c.company_name}</span>
                  <span className="ml-auto shrink-0 truncate text-11 text-fg-subtle">{c.company_domain}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <Button size="sm" variant="primary" onClick={submit} disabled={!domain || addMember.isPending}>Add</Button>
        <Button size="sm" variant="ghost" onClick={onDone}>Cancel</Button>
      </div>
    </div>
  );
}

function EnrollPicker({ campaignId, member, onDone }: { campaignId: number; member: CampaignMemberOut; onDone: () => void }) {
  const { data: seqs } = useSequences({ active_only: true, limit: 100 });
  const [seqId, setSeqId] = useState<number | "">("");
  const { enrollMember } = useCampaignMemberMutations(campaignId);

  function submit() {
    if (!seqId) return;
    enrollMember.mutate(
      { memberId: member.id, sequenceId: Number(seqId) },
      {
        onSuccess: () => { toast("Enrolled in sequence", "positive"); onDone(); },
        onError: (e) => toast(apiErrorMessage(e), "danger"),
      },
    );
  }

  return (
    <Modal
      open
      onClose={onDone}
      title={`Enroll ${member.company_name || member.company_domain}`}
      footer={
        <>
          <Button variant="ghost" onClick={onDone} disabled={enrollMember.isPending}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={!seqId || enrollMember.isPending}>Enroll</Button>
        </>
      }
    >
      {!member.outreach_lead_id ? (
        <p className="text-13 text-danger">This member has no linked outreach lead — link one before enrolling in a sequence.</p>
      ) : (
        <label className="block">
          <span className="mb-1 block text-11 text-fg-muted">Sequence</span>
          <select
            value={seqId}
            onChange={(e) => setSeqId(e.target.value ? Number(e.target.value) : "")}
            className="w-full rounded-md border border-line bg-control px-2.5 py-1.5 text-13 text-fg outline-none focus:border-accent"
          >
            <option value="">Choose a sequence…</option>
            {(seqs?.items ?? []).map((s) => (
              <option key={s.id} value={s.id}>{s.name} ({s.step_count} steps)</option>
            ))}
          </select>
        </label>
      )}
    </Modal>
  );
}

function MembersTab({ campaignId }: { campaignId: number }) {
  const [page, setPage] = useState(1);
  const [adding, setAdding] = useState(false);
  const [enrolling, setEnrolling] = useState<CampaignMemberOut | null>(null);
  const { data, isLoading, isError, error, refetch } = useCampaignMembers(campaignId, {
    limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE,
  });
  const { patchMember, removeMember } = useCampaignMemberMutations(campaignId);
  const err = (e: unknown) => toast(apiErrorMessage(e), "danger");

  return (
    <div className="space-y-4">
      {adding ? (
        <AddMemberForm campaignId={campaignId} onDone={() => setAdding(false)} />
      ) : (
        <Button size="sm" onClick={() => setAdding(true)}>Add company</Button>
      )}

      <div className="panel">
        {isError ? (
          <ErrorState title="Couldn't load members" error={error} onRetry={refetch} />
        ) : isLoading ? (
          <div className="grid place-items-center py-12"><Spinner size={18} /></div>
        ) : (data?.items.length ?? 0) === 0 ? (
          <EmptyState title="No members yet" description="Add a company above to start tracking it in this campaign." />
        ) : (
          <div className="divide-y divide-line">
            {data!.items.map((m) => (
              <div key={m.id} className="flex flex-wrap items-center gap-3 px-3.5 py-2.5">
                <div className="min-w-0 flex-1">
                  <Link to={`/companies/${encodeURIComponent(m.company_domain)}`} className="block truncate text-13 text-fg hover:text-accent">
                    {m.company_name || m.company_domain}
                  </Link>
                  {m.decision_maker_name && <span className="block truncate text-11 text-fg-subtle">{m.decision_maker_name}</span>}
                </div>
                <MemberStatusBadge status={m.engagement_status} />
                <input
                  defaultValue={m.current_stage}
                  onBlur={(e) => {
                    if (e.target.value !== m.current_stage) {
                      patchMember.mutate({ memberId: m.id, body: { current_stage: e.target.value } }, { onError: err });
                    }
                  }}
                  title="Current stage (free text)"
                  aria-label={`Current stage for ${m.company_name || m.company_domain}`}
                  className="w-28 rounded-md border border-line bg-control px-2 py-1 text-12 text-fg outline-none focus:border-accent"
                />
                <OutcomeBadge outcome={m.campaign_outcome} />
                <select
                  value={m.campaign_outcome || ""}
                  onChange={(e) => patchMember.mutate({ memberId: m.id, body: { campaign_outcome: e.target.value } }, { onError: err })}
                  className="rounded-md border border-line bg-control px-2 py-1 text-12 text-fg outline-none focus:border-accent"
                >
                  <option value="">No outcome</option>
                  {CAMPAIGN_OUTCOMES.map((o) => <option key={o} value={o}>{enumLabel(o)}</option>)}
                </select>
                <span className="text-11 text-fg-subtle">
                  {m.last_activity_at ? `active ${fmtRelative(m.last_activity_at)}` : "no activity yet"}
                </span>
                <Button size="sm" variant="ghost" onClick={() => setEnrolling(m)}>Enroll</Button>
                <button
                  type="button"
                  title="Remove from campaign"
                  aria-label={`Remove ${m.company_name || m.company_domain} from campaign`}
                  onClick={() => removeMember.mutate(m.id, { onError: err })}
                  className="text-fg-subtle hover:text-danger"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>
        )}
        {data && data.pages > 1 && (
          <div className="border-t border-line px-2">
            <Pager page={page} pages={data.pages} total={data.total} pageSize={data.page_size} onPage={setPage} />
          </div>
        )}
      </div>

      {enrolling && <EnrollPicker campaignId={campaignId} member={enrolling} onDone={() => setEnrolling(null)} />}
    </div>
  );
}

function ActivityTab({ campaignId }: { campaignId: number }) {
  const { data, isLoading, isError, error, refetch } = useCampaignTimeline(campaignId);
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
