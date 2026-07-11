import { Link } from "react-router-dom";
import { Inbox, Mail, MailCheck } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/shell/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { useOutreachInbox } from "@/lib/api/queries";
import { fmtRelative } from "@/lib/format";

export function OutreachInboxPage() {
  const { data, isLoading } = useOutreachInbox();
  const threads = data ?? [];

  return (
    <>
      <PageHeader title="Inbox" subtitle="Outbound threads and their replies (mock-mail in this environment)" />
      <div className="p-4">
        <div className="panel">
          {isLoading ? (
            <div className="grid place-items-center py-12"><Spinner size={18} /></div>
          ) : threads.length === 0 ? (
            <EmptyState icon={<Inbox size={20} />} title="No conversations yet" description="Sent messages and their replies will be threaded here." />
          ) : (
            <div className="divide-y divide-line">
              {threads.map((t) => (
                <div key={t.thread_id} className="px-3.5 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <Link to={`/outreach/leads/${t.outreach_lead_id}`} className="min-w-0">
                      <span className="block truncate text-13 font-medium text-fg hover:text-accent">{t.subject || "(no subject)"}</span>
                      <span className="block truncate text-11 text-fg-subtle">{t.company_name}</span>
                    </Link>
                    <div className="flex shrink-0 items-center gap-1.5">
                      {t.has_reply
                        ? <Badge tone="positive"><MailCheck size={11} /> Replied</Badge>
                        : <Badge tone="neutral"><Mail size={11} /> Awaiting reply</Badge>}
                      <span className="text-11 text-fg-subtle">{fmtRelative(t.last_at)}</span>
                    </div>
                  </div>
                  <div className="mt-2 space-y-1.5 border-l border-line pl-3">
                    {t.messages.map((m) => (
                      <div key={m.id} className="text-12">
                        <span className={m.direction === "inbound" ? "text-accent" : "text-fg-subtle"}>
                          {m.direction === "inbound" ? "▸ Reply" : "▸ Sent"}
                        </span>{" "}
                        <span className="text-fg-muted">{m.body.slice(0, 120)}{m.body.length > 120 ? "…" : ""}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
