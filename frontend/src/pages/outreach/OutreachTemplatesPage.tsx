import { useState } from "react";
import { FileText, Pencil, Plus, Trash2 } from "lucide-react";

import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import {
  useCreateOutreachTemplate,
  useDeleteOutreachTemplate,
  useOutreachTemplates,
  useUpdateOutreachTemplate,
} from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/store";
import type { OutreachTemplateOut } from "@/lib/api/types";

const BLANK = { name: "", category: "", subject: "", body: "", is_active: true };

function Editor({ tpl, onClose }: { tpl: OutreachTemplateOut | "new"; onClose: () => void }) {
  const create = useCreateOutreachTemplate();
  const update = useUpdateOutreachTemplate();
  const isNew = tpl === "new";
  const [form, setForm] = useState(
    isNew ? BLANK : { name: tpl.name, category: tpl.category, subject: tpl.subject, body: tpl.body, is_active: tpl.is_active },
  );
  const set = (k: keyof typeof BLANK) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  function save() {
    const onSuccess = () => { toast("Template saved", "positive"); onClose(); };
    const onError = () => toast("Couldn't save (admin/manager only)", "danger");
    if (isNew) create.mutate(form, { onSuccess, onError });
    else update.mutate({ id: tpl.id, body: form }, { onSuccess, onError });
  }

  return (
    <Modal open onClose={onClose} title={isNew ? "New template" : "Edit template"} width="40rem"
      footer={<><Button onClick={onClose}>Cancel</Button><Button variant="primary" onClick={save} disabled={!form.name.trim() || create.isPending || update.isPending}>Save</Button></>}>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <label className="block"><span className="mb-1 block text-11 text-fg-muted">Name</span><Input value={form.name} onChange={set("name")} placeholder="Intro — staffing" /></label>
          <label className="block"><span className="mb-1 block text-11 text-fg-muted">Category</span><Input value={form.category} onChange={set("category")} placeholder="staffing / engineering / follow_up" /></label>
        </div>
        <label className="block"><span className="mb-1 block text-11 text-fg-muted">Subject</span><Input value={form.subject} onChange={set("subject")} placeholder="Hi {{first_name}} — {{company}}" /></label>
        <label className="block">
          <span className="mb-1 block text-11 text-fg-muted">Body</span>
          <textarea value={form.body} onChange={set("body")} rows={8}
            placeholder={"Hi {{first_name}},\n\n{{pitch}}\n\n— {{sender_name}}"}
            className="w-full resize-y rounded-md border border-line bg-control px-2.5 py-1.5 text-12 text-fg outline-none focus:border-accent" />
        </label>
        <p className="text-11 text-fg-subtle">
          Variables: <code className="text-accent">{"{{first_name}} {{full_name}} {{company}} {{title}} {{pitch}} {{signal}} {{service}} {{sender_name}}"}</code> — filled from platform data when a draft is created.
        </p>
      </div>
    </Modal>
  );
}

export function OutreachTemplatesPage() {
  const { isManager } = useAuth();
  const { data, isLoading } = useOutreachTemplates();
  const del = useDeleteOutreachTemplate();
  const [editing, setEditing] = useState<OutreachTemplateOut | "new" | null>(null);
  const [deleting, setDeleting] = useState<OutreachTemplateOut | null>(null);
  const templates = data ?? [];

  function confirmDelete() {
    if (!deleting) return;
    del.mutate(deleting.id, {
      onSuccess: () => toast("Template deleted", "positive"),
      onError: () => toast("Delete failed", "danger"),
      onSettled: () => setDeleting(null),
    });
  }

  return (
    <>
      <PageHeader title="Email templates" subtitle="Deterministic {{variable}} templates — no AI, fully reviewable">
        {isManager && <Button variant="primary" size="sm" onClick={() => setEditing("new")}><Plus size={13} /> New template</Button>}
      </PageHeader>

      <div className="p-4">
        <div className="panel">
          {isLoading ? (
            <div className="grid place-items-center py-12"><Spinner size={18} /></div>
          ) : templates.length === 0 ? (
            <EmptyState icon={<FileText size={20} />} title="No templates yet"
              description={isManager ? "Create your first reusable email template." : "Ask an admin or manager to add templates."} />
          ) : (
            <div className="divide-y divide-line">
              {templates.map((t) => (
                <div key={t.id} className="flex items-start justify-between gap-3 px-3.5 py-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-13 font-medium text-fg">{t.name}</span>
                      {t.category && <Badge>{t.category}</Badge>}
                      {!t.is_active && <Badge tone="neutral">Inactive</Badge>}
                    </div>
                    <div className="truncate text-12 text-fg-muted">{t.subject}</div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {t.variables.map((v) => <span key={v} className="rounded bg-control px-1 text-11 text-fg-subtle">{`{{${v}}}`}</span>)}
                    </div>
                  </div>
                  {isManager && (
                    <div className="flex shrink-0 gap-1.5">
                      <Button size="sm" variant="ghost" aria-label={`Edit ${t.name}`} onClick={() => setEditing(t)}><Pencil size={13} /></Button>
                      <Button size="sm" variant="ghost" aria-label={`Delete ${t.name}`} onClick={() => setDeleting(t)}><Trash2 size={13} /></Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {editing && <Editor tpl={editing} onClose={() => setEditing(null)} />}
      {deleting && (
        <Modal
          open
          onClose={() => setDeleting(null)}
          title="Delete template"
          footer={
            <>
              <Button variant="ghost" onClick={() => setDeleting(null)} disabled={del.isPending}>Cancel</Button>
              <Button variant="danger" onClick={confirmDelete} disabled={del.isPending}>Delete</Button>
            </>
          }
        >
          <p className="text-13 text-fg-muted">Delete template “{deleting.name}”? This can't be undone.</p>
        </Modal>
      )}
    </>
  );
}
