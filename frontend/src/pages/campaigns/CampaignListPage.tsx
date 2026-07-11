import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import { Megaphone, Plus } from "lucide-react";

import { CampaignFormModal } from "@/components/campaigns/CampaignFormModal";
import { CampaignStatusBadge } from "@/components/campaigns/bits";
import { DataTable } from "@/components/data/DataTable";
import { NumericCell } from "@/components/data/NumericCell";
import { Pager } from "@/components/data/Pager";
import { StatStrip, type Stat } from "@/components/data/StatStrip";
import { FilterBar, FilterSelect } from "@/components/shell/FilterBar";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import { useCampaignDashboard, useCampaignMutations, useCampaigns } from "@/lib/api/queries";
import { CAMPAIGN_STATUSES, CAMPAIGN_TYPES, type CampaignOut } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/store";
import { useUrlFilters } from "@/hooks/useUrlFilters";
import { enumLabel, fmtDate, fmtInt, fmtPct } from "@/lib/format";

const KEYS = ["page", "status", "campaign_type", "q"] as const;
const STATUS_OPTIONS = CAMPAIGN_STATUSES.map((s) => ({ value: s, label: enumLabel(s) }));
const TYPE_OPTIONS = CAMPAIGN_TYPES.map((t) => ({ value: t, label: enumLabel(t) }));
const PAGE_SIZE = 25;

type SortField = "name" | "status" | "member_count" | "emails_sent" | "replies" | "meetings" | "created_at";

export function CampaignListPage() {
  const { isManager } = useAuth();
  const navigate = useNavigate();
  const { values, setValue, clear, activeCount } = useUrlFilters(KEYS);
  const page = Math.max(1, Number(values.page) || 1);
  const [sort, setSort] = useState<{ field: SortField; dir: "asc" | "desc" }>({ field: "created_at", dir: "desc" });
  const [creating, setCreating] = useState(false);
  const [archiving, setArchiving] = useState<CampaignOut | null>(null);

  const dashboard = useCampaignDashboard();
  const { data, isLoading, isError, error, refetch } = useCampaigns({
    status: values.status || undefined,
    campaign_type: values.campaign_type || undefined,
    search: values.q || undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });
  const { archive } = useCampaignMutations();

  const items = data?.items ?? [];
  const sorted = useMemo(() => {
    const list = [...items];
    const dir = sort.dir === "asc" ? 1 : -1;
    list.sort((a, b) => {
      const av = a[sort.field], bv = b[sort.field];
      if (typeof av === "string" || typeof bv === "string") return String(av).localeCompare(String(bv)) * dir;
      return ((av as number) - (bv as number)) * dir;
    });
    return list;
  }, [items, sort]);

  function onSortChange(field: string) {
    setSort((s) => (s.field === field ? { field: field as SortField, dir: s.dir === "asc" ? "desc" : "asc" } : { field: field as SortField, dir: "asc" }));
  }

  function confirmArchive() {
    if (!archiving) return;
    archive.mutate(archiving.id, {
      onSuccess: () => { toast("Campaign archived", "positive"); setArchiving(null); },
      onError: (e) => { toast(apiErrorMessage(e), "danger"); setArchiving(null); },
    });
  }

  const stats: Stat[] = dashboard.data
    ? [
        { label: "Active campaigns", value: fmtInt(dashboard.data.active_campaigns) },
        { label: "Members", value: fmtInt(dashboard.data.total_members) },
        { label: "Emails sent", value: fmtInt(dashboard.data.emails_sent) },
        { label: "Replies", value: fmtInt(dashboard.data.replies) },
        { label: "Meetings", value: fmtInt(dashboard.data.meetings) },
        { label: "Reply rate", value: fmtPct(dashboard.data.overall_reply_rate) },
      ]
    : [];

  const columns: ColumnDef<CampaignOut, any>[] = [
    {
      id: "name",
      header: "Campaign",
      meta: { sortField: "name" },
      cell: ({ row }) => (
        <div className="min-w-0">
          <div className="truncate text-fg">{row.original.name}</div>
          {row.original.tags.length > 0 && (
            <div className="mt-0.5 flex flex-wrap gap-1">
              {row.original.tags.map((t) => (
                <span key={t} className="rounded bg-control px-1 text-11 text-fg-subtle">{t}</span>
              ))}
            </div>
          )}
        </div>
      ),
    },
    {
      id: "status",
      header: "Status",
      meta: { sortField: "status" },
      cell: ({ row }) => <CampaignStatusBadge status={row.original.status} />,
    },
    {
      id: "type",
      header: "Type",
      cell: ({ row }) => <span className="text-fg-muted">{enumLabel(row.original.campaign_type)}</span>,
    },
    {
      id: "owner",
      header: "Owner",
      cell: ({ row }) => <span className="text-fg-muted">{row.original.owner_email || "—"}</span>,
    },
    {
      id: "members",
      header: "Members",
      meta: { align: "right", sortField: "member_count" },
      cell: ({ row }) => <NumericCell>{fmtInt(row.original.member_count)}</NumericCell>,
    },
    {
      id: "emails",
      header: "Emails",
      meta: { align: "right", sortField: "emails_sent" },
      cell: ({ row }) => <NumericCell className="text-fg-muted">{fmtInt(row.original.emails_sent)}</NumericCell>,
    },
    {
      id: "replies",
      header: "Replies",
      meta: { align: "right", sortField: "replies" },
      cell: ({ row }) => <NumericCell className="text-fg-muted">{fmtInt(row.original.replies)}</NumericCell>,
    },
    {
      id: "meetings",
      header: "Meetings",
      meta: { align: "right", sortField: "meetings" },
      cell: ({ row }) => <NumericCell className="text-fg-muted">{fmtInt(row.original.meetings)}</NumericCell>,
    },
    {
      id: "created",
      header: "Created",
      meta: { sortField: "created_at" },
      cell: ({ row }) => <span className="text-11 text-fg-subtle">{fmtDate(row.original.created_at)}</span>,
    },
    ...(isManager
      ? [{
          id: "actions",
          header: "",
          cell: ({ row }: { row: { original: CampaignOut } }) =>
            row.original.status !== "archived" ? (
              <Button
                size="sm"
                variant="ghost"
                onClick={(e: React.MouseEvent) => { e.stopPropagation(); setArchiving(row.original); }}
              >
                Archive
              </Button>
            ) : null,
        } as ColumnDef<CampaignOut, any>]
      : []),
  ];

  return (
    <>
      <PageHeader
        title="Campaigns"
        subtitle={data ? `${fmtInt(data.total)} campaigns` : "Outreach campaigns grouping companies under a common goal"}
      >
        <Button variant="primary" size="sm" onClick={() => setCreating(true)}>
          <Plus size={13} /> New campaign
        </Button>
      </PageHeader>

      <div className="space-y-4 p-4">
        {stats.length > 0 && <StatStrip stats={stats} />}

        <FilterBar activeCount={activeCount} onClear={clear}>
          <DebouncedInput value={values.q} onChange={(v) => setValue("q", v)} placeholder="Search campaigns…" className="w-56" />
          <FilterSelect label="All statuses" value={values.status} onChange={(v) => setValue("status", v)} options={STATUS_OPTIONS} />
          <FilterSelect label="All types" value={values.campaign_type} onChange={(v) => setValue("campaign_type", v)} options={TYPE_OPTIONS} />
        </FilterBar>

        <div className="panel">
          {isError ? (
            <ErrorState title="Couldn't load campaigns" error={error} onRetry={refetch} />
          ) : (
            <DataTable
              columns={columns}
              data={sorted}
              isLoading={isLoading}
              getRowId={(r) => String(r.id)}
              onRowClick={(r) => navigate(`/campaigns/${r.id}`)}
              sort={sort}
              onSortChange={onSortChange}
              empty={
                <EmptyState
                  icon={<Megaphone size={20} />}
                  title="No campaigns yet"
                  description="Create your first campaign to start organizing outreach around a goal."
                  action={<Button size="sm" onClick={() => setCreating(true)}>New campaign</Button>}
                />
              }
            />
          )}
          {data && data.pages > 1 && (
            <div className="border-t border-line px-2">
              <Pager page={page} pages={data.pages} total={data.total} pageSize={data.page_size} onPage={(p) => setValue("page", String(p))} />
            </div>
          )}
        </div>
      </div>

      {creating && <CampaignFormModal onClose={() => setCreating(false)} />}

      {archiving && (
        <Modal
          open
          onClose={() => setArchiving(null)}
          title="Archive campaign"
          footer={
            <>
              <Button variant="ghost" onClick={() => setArchiving(null)} disabled={archive.isPending}>Cancel</Button>
              <Button variant="danger" onClick={confirmArchive} disabled={archive.isPending}>Archive</Button>
            </>
          }
        >
          <p className="text-13 text-fg-muted">
            Archive “{archiving.name}”? It will be marked archived and hidden from active views, but its history is kept.
          </p>
        </Modal>
      )}
    </>
  );
}
