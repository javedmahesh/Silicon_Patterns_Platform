import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { useAddCompanyNote, useCompanyActivity, useCompanyNotes } from "@/lib/api/queries";
import { fmtRelative } from "@/lib/format";

/** Notes + merged activity timeline for one company (Company Profile). */
export function CompanyCrmPanel({ domain }: { domain: string }) {
  const notes = useCompanyNotes(domain);
  const activity = useCompanyActivity(domain);
  const addNote = useAddCompanyNote(domain);
  const [draft, setDraft] = useState("");

  function post() {
    const body = draft.trim();
    if (!body) return;
    addNote.mutate(body, { onSuccess: () => setDraft("") });
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="panel p-3.5">
        <div className="mb-2 text-13 font-medium text-fg">Notes</div>
        <div className="flex gap-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={2}
            placeholder="Add a note…"
            className="flex-1 resize-none rounded-md border border-line bg-control px-2.5 py-1.5 text-12 text-fg outline-none focus:border-accent"
          />
          <Button size="sm" onClick={post} disabled={!draft.trim() || addNote.isPending}>
            Post
          </Button>
        </div>
        <div className="mt-3 space-y-2">
          {(notes.data ?? []).length === 0 ? (
            <p className="text-12 text-fg-subtle">No notes yet.</p>
          ) : (
            notes.data!.map((n) => (
              <div key={n.id} className="rounded-md border border-line bg-base p-2.5">
                <div className="mb-0.5 flex items-center justify-between text-11 text-fg-subtle">
                  <span className="truncate">{n.author_email}</span>
                  <span>{fmtRelative(n.created_at)}</span>
                </div>
                <p className="whitespace-pre-wrap text-12 text-fg-muted">{n.body}</p>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="panel p-3.5">
        <div className="mb-2 text-13 font-medium text-fg">Activity</div>
        {activity.isLoading ? (
          <div className="py-4">
            <Spinner size={14} />
          </div>
        ) : (activity.data ?? []).length === 0 ? (
          <p className="text-12 text-fg-subtle">No activity yet.</p>
        ) : (
          <ol className="space-y-2">
            {activity.data!.map((a, i) => (
              <li key={i} className="flex gap-2 text-12">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                <div className="min-w-0">
                  <div className="text-fg">
                    <span className="capitalize">{a.title}</span>
                    {a.detail ? <span className="text-fg-muted"> — {a.detail}</span> : null}
                  </div>
                  <div className="text-11 text-fg-subtle">
                    {a.actor} · {fmtRelative(a.at)}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
