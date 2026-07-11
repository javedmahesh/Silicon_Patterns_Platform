import { ClipboardList, StickyNote } from "lucide-react";
import { Link } from "react-router-dom";

import { StatusSelect } from "@/components/crm/status";
import { GradeBadge } from "@/components/data/GradeBadge";
import { PageHeader } from "@/components/shell/PageHeader";
import { apiErrorMessage } from "@/lib/api/client";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import { useCrmMutations, useMyAssignments } from "@/lib/api/queries";
import { fmtInt, fmtRelative, monogram } from "@/lib/format";

export function MyLeadsPage() {
  const { data, isLoading, isError, error, refetch } = useMyAssignments();
  const { updateAssignment } = useCrmMutations();
  const items = data ?? [];

  return (
    <>
      <PageHeader
        title="My leads"
        subtitle={data ? `${fmtInt(items.length)} assigned to you` : "Companies assigned to you"}
      />
      <div className="p-4">
        <div className="panel">
          {isError ? (
            <ErrorState title="Couldn't load your leads" error={error} onRetry={refetch} />
          ) : isLoading ? (
            <div className="grid place-items-center py-12">
              <Spinner size={18} />
            </div>
          ) : items.length === 0 ? (
            <EmptyState
              icon={<ClipboardList size={20} />}
              title="No leads assigned to you yet"
              description="When a manager assigns you a company, it appears here. You can update its status as you work it."
            />
          ) : (
            <div className="divide-y divide-line">
              {items.map((a) => (
                <div key={a.id} className="px-3.5 py-2.5">
                  <div className="flex items-center gap-3">
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-line bg-control text-12 text-fg-muted">
                      {monogram(a.company_name, a.company_domain)}
                    </span>
                    <Link to={`/companies/${encodeURIComponent(a.company_domain)}`} className="min-w-0 flex-1">
                      <span className="block truncate text-13 text-fg hover:text-accent">{a.company_name}</span>
                      <span className="block truncate text-11 text-fg-subtle">{a.company_domain}</span>
                    </Link>
                    {a.grade ? <GradeBadge grade={a.grade} /> : null}
                    <StatusSelect
                      value={a.status}
                      onChange={(s) =>
                        updateAssignment.mutate(
                          { id: a.id, patch: { status: s } },
                          { onError: (e) => toast(apiErrorMessage(e), "danger") },
                        )
                      }
                    />
                  </div>
                  {a.note && (
                    <div className="mt-2 ml-11 rounded-md border border-line bg-raised px-2.5 py-1.5">
                      <div className="flex items-start gap-2">
                        <StickyNote size={13} className="mt-0.5 shrink-0 text-accent" />
                        <span className="whitespace-pre-wrap text-12 text-fg-muted">{a.note}</span>
                      </div>
                      {(a.assigned_by_name || a.assigned_by_email || a.created_at) && (
                        <div className="mt-1 pl-[21px] text-11 text-fg-subtle">
                          From {a.assigned_by_name || a.assigned_by_email || "your manager"}
                          {a.created_at ? ` · ${fmtRelative(a.created_at)}` : ""}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
