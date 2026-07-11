import { useState } from "react";
import { Link } from "react-router-dom";
import { Calendar, RefreshCw, Send } from "lucide-react";

import { GradeBadge, PriorityBadge, StageBadge, serviceLabel, STAGE_ORDER, stageLabel } from "@/components/outreach/bits";
import { FilterBar } from "@/components/shell/FilterBar";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import { useOutreachLeads, useSyncOutreach } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/store";
import { fmtInt, fmtRelative } from "@/lib/format";

export function OutreachLeadsPage() {
  const { isManager } = useAuth();
  const [stage, setStage] = useState("");
  const [mine, setMine] = useState(false);
  const [search, setSearch] = useState("");
  const { data, isLoading, isError, error, refetch } = useOutreachLeads({
    stage: stage || undefined,
    mine: mine || undefined,
    search: search || undefined,
    page_size: 100,
  });
  const sync = useSyncOutreach();
  const leads = data?.items ?? [];
  const activeCount = (stage ? 1 : 0) + (mine ? 1 : 0) + (search ? 1 : 0);

  function runSync() {
    sync.mutate(60, {
      onSuccess: (r) => toast(`Synced ${r.created} new + ${r.updated} existing from Discovery`, "positive"),
      onError: () => toast("Sync failed — admin/manager only", "danger"),
    });
  }

  return (
    <>
      <PageHeader
        title="Outreach leads"
        subtitle={data ? `${fmtInt(data.total)} qualified ${data.total === 1 ? "lead" : "leads"} in the pipeline` : "Qualified companies ready for outreach, ranked by Discovery score"}
      >
        {isManager && (
          <Button variant="primary" size="sm" onClick={runSync} disabled={sync.isPending}>
            <RefreshCw size={13} className={sync.isPending ? "animate-spin" : ""} /> Sync from Discovery
          </Button>
        )}
      </PageHeader>

      <div className="space-y-4 p-4">
        <FilterBar activeCount={activeCount} onClear={() => { setStage(""); setMine(false); setSearch(""); }}>
          <select
            value={stage}
            onChange={(e) => setStage(e.target.value)}
            className="h-8 rounded-md border border-line bg-control px-2 text-12 text-fg outline-none focus:border-accent"
          >
            <option value="">All stages</option>
            {STAGE_ORDER.map((s) => (
              <option key={s} value={s}>{stageLabel(s)}</option>
            ))}
          </select>
          <DebouncedInput value={search} onChange={setSearch} placeholder="Filter companies…" className="w-56" />
          <label className="flex items-center gap-1.5 text-12 text-fg-muted">
            <input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} /> My leads
          </label>
        </FilterBar>

        <div className="panel">
          {isError ? (
            <ErrorState title="Couldn't load outreach leads" error={error} onRetry={refetch} />
          ) : isLoading ? (
            <div className="grid place-items-center py-12"><Spinner size={18} /></div>
          ) : leads.length === 0 ? (
            <EmptyState
              icon={<Send size={20} />}
              title={activeCount ? "No leads match" : "No outreach leads yet"}
              description={
                isManager
                  ? "Click “Sync from Discovery” to pull the top-scored companies into the outreach pipeline."
                  : "Ask an admin or manager to sync qualified companies from Discovery into the pipeline."
              }
            />
          ) : (
            <table className="w-full text-13">
              <thead>
                <tr className="border-b border-line text-left text-11 uppercase tracking-wide text-fg-subtle">
                  <th className="px-3.5 py-2 font-medium">Company</th>
                  <th className="px-2 py-2 font-medium">Grade</th>
                  <th className="px-2 py-2 font-medium">Priority</th>
                  <th className="px-2 py-2 font-medium">Stage</th>
                  <th className="px-2 py-2 font-medium">Service</th>
                  <th className="px-2 py-2 font-medium">Primary contact</th>
                  <th className="px-2 py-2 font-medium">Owner</th>
                  <th className="px-2 py-2 text-right font-medium">Follow-up / Activity</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((l) => (
                  <tr key={l.id} className="border-b border-line/60 hover:bg-raised">
                    <td className="px-3.5 py-2.5">
                      <Link to={`/outreach/leads/${l.id}`} className="block">
                        <span className="block truncate font-medium text-fg hover:text-accent">{l.company_name}</span>
                        <span className="block truncate text-11 text-fg-subtle">{l.signal_summary || l.company_domain}</span>
                      </Link>
                    </td>
                    <td className="px-2 py-2.5"><GradeBadge grade={l.grade} /></td>
                    <td className="px-2 py-2.5"><PriorityBadge priority={l.priority} /></td>
                    <td className="px-2 py-2.5"><StageBadge stage={l.stage} /></td>
                    <td className="px-2 py-2.5 text-12 text-fg-muted">{serviceLabel(l.service_interest)}</td>
                    <td className="px-2 py-2.5">
                      {l.primary_contact ? (
                        <span className="block truncate text-12 text-fg" title={l.primary_contact.email}>
                          {l.primary_contact.full_name}
                          <span className="block truncate text-11 text-fg-subtle">{l.primary_contact.title}</span>
                        </span>
                      ) : (
                        <span className="text-11 text-fg-subtle">—</span>
                      )}
                    </td>
                    <td className="px-2 py-2.5 text-11 text-fg-subtle">{l.owner_email ? l.owner_email.split("@")[0] : "Unassigned"}</td>
                    <td className="px-2 py-2.5 text-right text-11 text-fg-subtle">
                      {l.next_action_at && new Date(l.next_action_at) < new Date() ? (
                        <span className="flex items-center justify-end gap-1 text-danger" title={`Follow-up overdue · ${new Date(l.next_action_at).toLocaleDateString()}`}>
                          <Calendar size={11} /> Overdue
                        </span>
                      ) : l.next_action_at ? (
                        <span className="flex items-center justify-end gap-1 text-fg-muted" title={`Follow-up · ${new Date(l.next_action_at).toLocaleDateString()}`}>
                          <Calendar size={11} /> {new Date(l.next_action_at).toLocaleDateString()}
                        </span>
                      ) : (
                        fmtRelative(l.last_activity_at)
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}
