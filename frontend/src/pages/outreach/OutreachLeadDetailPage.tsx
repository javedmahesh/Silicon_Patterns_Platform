import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Calendar, CheckCircle2, CheckSquare, Clock, Mail, MailCheck, Pencil, Plus, Send, Sparkles, Trash2, X } from "lucide-react";

import { GradeBadge, MessageStatusBadge, PriorityBadge, StageBadge, serviceLabel, STAGE_ORDER, stageLabel } from "@/components/outreach/bits";
import { PageHeader } from "@/components/shell/PageHeader";
import { apiErrorMessage } from "@/lib/api/client";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import {
  useAddOutreachNote,
  useCreateOutreachMessage,
  useCreateOutreachMeeting,
  useCreateOutreachTask,
  useDeleteOutreachMeeting,
  useDeleteOutreachTask,
  useOutreachLead,
  useOutreachMessageAction,
  useOutreachMeetings,
  useOutreachMessages,
  useOutreachTasks,
  useOutreachTemplates,
  useOutreachTimeline,
  usePatchOutreachLead,
  usePatchOutreachMessage,
  usePatchOutreachTask,
} from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/store";
import { fmtRelative, fmtScore } from "@/lib/format";
import type { OutreachContactOut, OutreachMeetingOut, OutreachMessageOut, OutreachTaskOut } from "@/lib/api/types";

function Panel({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="panel p-3.5">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-13 font-medium text-fg">{title}</div>
        {action}
      </div>
      {children}
    </div>
  );
}

function MessageCard({ msg }: { msg: OutreachMessageOut }) {
  const { isManager } = useAuth();
  const submit = useOutreachMessageAction("submit");
  const approve = useOutreachMessageAction("approve");
  const send = useOutreachMessageAction("send");
  const reply = useOutreachMessageAction("reply");
  const patch = usePatchOutreachMessage();
  const inbound = msg.direction === "inbound";

  const [editing, setEditing] = useState(false);
  const [editSubject, setEditSubject] = useState(msg.subject);
  const [editBody, setEditBody] = useState(msg.body);

  const act = (m: ReturnType<typeof useOutreachMessageAction>, id: number, ok: string) =>
    m.mutate(id, { onSuccess: () => toast(ok, "positive"), onError: (e: unknown) => toast(apiErrorMessage(e), "danger") });

  function saveEdit() {
    patch.mutate(
      { id: msg.id, body: { subject: editSubject, body: editBody } },
      {
        onSuccess: () => { toast("Draft saved", "positive"); setEditing(false); },
        onError: () => toast("Couldn't save draft", "danger"),
      },
    );
  }

  return (
    <div className={`rounded-md border p-2.5 ${inbound ? "border-accent/40 bg-accent/5" : "border-line bg-base"}`}>
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-12 text-fg">
          {inbound ? <MailCheck size={13} className="text-accent" /> : <Mail size={13} className="text-fg-subtle" />}
          {inbound ? `Reply from ${msg.from_email}` : `To ${msg.to_email || "—"}`}
        </span>
        <MessageStatusBadge status={msg.status} />
      </div>

      {editing ? (
        <div className="space-y-2">
          <input
            value={editSubject}
            onChange={(e) => setEditSubject(e.target.value)}
            placeholder="Subject"
            className="w-full rounded border border-line bg-control px-2 py-1 text-12 text-fg outline-none focus:border-accent"
          />
          <textarea
            value={editBody}
            onChange={(e) => setEditBody(e.target.value)}
            rows={6}
            className="w-full resize-y rounded border border-line bg-control px-2 py-1 text-12 text-fg outline-none focus:border-accent"
          />
          <div className="flex gap-1.5">
            <Button size="sm" variant="primary" onClick={saveEdit} disabled={patch.isPending}>Save</Button>
            <Button size="sm" onClick={() => { setEditing(false); setEditSubject(msg.subject); setEditBody(msg.body); }}>
              <X size={12} /> Cancel
            </Button>
          </div>
        </div>
      ) : (
        <>
          <div className="text-12 font-medium text-fg">{msg.subject || "(no subject)"}</div>
          <p className="mt-0.5 whitespace-pre-wrap text-12 text-fg-muted">{msg.body}</p>
          <div className="mt-1.5 flex items-center justify-between">
            <span className="text-11 text-fg-subtle">
              {msg.created_by_email ? msg.created_by_email.split("@")[0] : ""} · {fmtRelative(msg.sent_at || msg.created_at)}
            </span>
            {!inbound && (
              <div className="flex gap-1.5">
                {msg.status === "draft" && (
                  <>
                    <Button size="sm" variant="ghost" onClick={() => setEditing(true)} title="Edit draft" aria-label="Edit draft">
                      <Pencil size={12} />
                    </Button>
                    <Button size="sm" onClick={() => act(submit, msg.id, "Submitted for approval")} disabled={submit.isPending}>
                      Submit
                    </Button>
                  </>
                )}
                {msg.status === "pending_approval" && isManager && (
                  <Button size="sm" variant="primary" onClick={() => act(approve, msg.id, "Approved")} disabled={approve.isPending}>
                    <CheckCircle2 size={12} /> Approve
                  </Button>
                )}
                {msg.status === "approved" && isManager && (
                  <Button size="sm" variant="primary" onClick={() => act(send, msg.id, "Sent (mock)")} disabled={send.isPending}>
                    <Send size={12} /> Send
                  </Button>
                )}
                {msg.status === "sent" && (
                  <Button size="sm" onClick={() => act(reply, msg.id, "Reply simulated")} disabled={reply.isPending} title="Simulate an inbound reply (mock-mail)">
                    Simulate reply
                  </Button>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function Composer({ leadId, contacts }: { leadId: number; contacts: OutreachContactOut[] }) {
  const templates = useOutreachTemplates(true);
  const create = useCreateOutreachMessage(leadId);
  const [open, setOpen] = useState(false);
  const [templateId, setTemplateId] = useState<number | "">("");
  const [dmId, setDmId] = useState<number | "">(contacts[0]?.decision_maker_id ?? "");

  function submit() {
    create.mutate(
      {
        template_id: templateId ? Number(templateId) : undefined,
        decision_maker_id: dmId ? Number(dmId) : undefined,
        subject: "",
        body: "",
      },
      {
        onSuccess: () => { toast("Draft created", "positive"); setOpen(false); setTemplateId(""); },
        onError: () => toast("Couldn't create draft (pick a template)", "danger"),
      },
    );
  }

  if (!open) {
    return (
      <Button size="sm" onClick={() => setOpen(true)}>
        <Plus size={13} /> New draft
      </Button>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <select value={templateId} onChange={(e) => setTemplateId(e.target.value ? Number(e.target.value) : "")}
        className="h-8 rounded-md border border-line bg-control px-2 text-12 text-fg outline-none focus:border-accent">
        <option value="">Choose template…</option>
        {(templates.data ?? []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
      </select>
      <select value={dmId} onChange={(e) => setDmId(e.target.value ? Number(e.target.value) : "")}
        className="h-8 max-w-44 rounded-md border border-line bg-control px-2 text-12 text-fg outline-none focus:border-accent">
        {contacts.length === 0 && <option value="">No contacts</option>}
        {contacts.map((c) => (
          <option key={c.decision_maker_id} value={c.decision_maker_id}>
            {c.recommendation_rank === "primary" ? "★ " : ""}{c.full_name}
            {c.department ? ` — ${c.department}` : ""}
            {c.influence_score != null ? ` (Infl ${c.influence_score})` : ""}
          </option>
        ))}
      </select>
      <Button size="sm" variant="primary" onClick={submit} disabled={create.isPending || !templateId}>Create</Button>
      <Button size="sm" onClick={() => setOpen(false)}>Cancel</Button>
    </div>
  );
}

function NoteComposer({ leadId }: { leadId: number }) {
  const addNote = useAddOutreachNote(leadId);
  const [text, setText] = useState("");

  function submit() {
    if (!text.trim()) return;
    addNote.mutate(text.trim(), {
      onSuccess: () => { toast("Note added", "positive"); setText(""); },
      onError: () => toast("Couldn't add note", "danger"),
    });
  }

  return (
    <div className="mt-3 space-y-1.5 border-t border-line pt-3">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Add a note…"
        rows={2}
        className="w-full resize-none rounded-md border border-line bg-control px-2.5 py-1.5 text-12 text-fg placeholder:text-fg-subtle outline-none focus:border-accent"
      />
      <Button size="sm" disabled={!text.trim() || addNote.isPending} onClick={submit}>
        Add note
      </Button>
    </div>
  );
}

function FollowUpPicker({ leadId, value }: { leadId: number; value: string | null | undefined }) {
  const patch = usePatchOutreachLead(leadId);
  const [editing, setEditing] = useState(false);
  const [dt, setDt] = useState(value ? value.slice(0, 16) : "");

  const isOverdue = value && new Date(value) < new Date();

  function save() {
    patch.mutate(
      { next_action_at: dt ? new Date(dt).toISOString() : null },
      {
        onSuccess: () => { toast("Follow-up scheduled", "positive"); setEditing(false); },
        onError: () => toast("Couldn't update follow-up", "danger"),
      },
    );
  }

  function clear() {
    patch.mutate(
      { next_action_at: null },
      { onSuccess: () => toast("Follow-up cleared", "positive"), onError: (e) => toast(apiErrorMessage(e), "danger") },
    );
  }

  if (!editing) {
    return (
      <div className="flex items-center gap-2">
        <Calendar size={13} className={isOverdue ? "text-danger" : "text-fg-subtle"} />
        {value ? (
          <span className={`text-12 ${isOverdue ? "text-danger font-medium" : "text-fg-muted"}`}>
            {isOverdue ? "Overdue · " : ""}{new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}
          </span>
        ) : (
          <span className="text-12 text-fg-subtle">No follow-up scheduled</span>
        )}
        <Button size="sm" variant="ghost" onClick={() => setEditing(true)} title="Edit follow-up" aria-label="Edit follow-up">
          <Pencil size={12} />
        </Button>
        {value && (
          <Button size="sm" variant="ghost" onClick={clear} title="Clear follow-up" aria-label="Clear follow-up">
            <X size={12} />
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <input
        type="datetime-local"
        value={dt}
        onChange={(e) => setDt(e.target.value)}
        className="h-8 rounded-md border border-line bg-control px-2 text-12 text-fg outline-none focus:border-accent"
      />
      <Button size="sm" variant="primary" onClick={save} disabled={patch.isPending}>Save</Button>
      <Button size="sm" onClick={() => setEditing(false)}>Cancel</Button>
    </div>
  );
}

function MeetingLogPanel({ leadId }: { leadId: number }) {
  const [showForm, setShowForm] = useState(false);
  const [meetingType, setMeetingType] = useState("call");
  const [title, setTitle] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [duration, setDuration] = useState("");
  const [notes, setNotes] = useState("");
  const { data } = useOutreachMeetings({ outreach_lead_id: leadId, page_size: 20 });
  const create = useCreateOutreachMeeting();
  const del = useDeleteOutreachMeeting();

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!scheduledAt) return;
    create.mutate(
      {
        outreach_lead_id: leadId,
        meeting_type: meetingType,
        title: title || undefined,
        scheduled_at: scheduledAt,
        duration_minutes: duration ? Number(duration) : undefined,
        notes: notes || undefined,
      },
      {
        onSuccess: () => {
          toast("Meeting logged", "positive");
          setShowForm(false);
          setTitle(""); setScheduledAt(""); setDuration(""); setNotes("");
        },
        onError: () => toast("Failed to log meeting", "danger"),
      },
    );
  }

  const meetings = data?.items ?? [];
  return (
    <Panel
      title={`Meetings (${data?.total ?? meetings.length})`}
      action={
        <button onClick={() => setShowForm((p) => !p)} className="text-11 text-accent hover:underline">
          {showForm ? "Cancel" : "+ Log meeting"}
        </button>
      }
    >
      {showForm && (
        <form onSubmit={submit} className="mb-3 space-y-2 rounded-md border border-line bg-surface p-2.5">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="mb-1 block text-11 text-fg-subtle">Type</label>
              <select
                value={meetingType}
                onChange={(e) => setMeetingType(e.target.value)}
                className="h-8 w-full rounded-md border border-line bg-control px-2 text-12 text-fg outline-none focus:border-accent"
              >
                {["call", "video", "in_person", "demo", "follow_up"].map((t) => (
                  <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-11 text-fg-subtle">Duration (min)</label>
              <input
                type="number" min="5" max="480" value={duration}
                onChange={(e) => setDuration(e.target.value)}
                placeholder="30"
                className="h-8 w-full rounded-md border border-line bg-control px-2 text-12 text-fg outline-none focus:border-accent"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-11 text-fg-subtle">Title (optional)</label>
            <input
              value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Intro call"
              className="h-8 w-full rounded-md border border-line bg-control px-2 text-12 text-fg outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="mb-1 block text-11 text-fg-subtle">When *</label>
            <input
              type="datetime-local" required
              value={scheduledAt.slice(0, 16)}
              onChange={(e) => setScheduledAt(e.target.value ? `${e.target.value}:00Z` : "")}
              className="h-8 w-full rounded-md border border-line bg-control px-2 text-12 text-fg outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="mb-1 block text-11 text-fg-subtle">Notes</label>
            <textarea
              value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} placeholder="Key takeaways…"
              className="w-full resize-none rounded-md border border-line bg-control px-2 py-1.5 text-12 text-fg outline-none focus:border-accent"
            />
          </div>
          <Button type="submit" variant="primary" size="sm" disabled={!scheduledAt || create.isPending}>
            {create.isPending ? "Saving…" : "Log meeting"}
          </Button>
        </form>
      )}
      {meetings.length === 0 ? (
        <p className="text-12 text-fg-subtle">No meetings logged yet.</p>
      ) : (
        <div className="space-y-2">
          {meetings.map((m: OutreachMeetingOut) => (
            <div key={m.id} className="flex items-start gap-2 rounded-md border border-line bg-base p-2">
              <Calendar size={13} className="mt-0.5 shrink-0 text-fg-subtle" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-12 font-medium text-fg">
                    {m.title || m.meeting_type.replace(/_/g, " ")}
                  </span>
                  <button
                    onClick={() =>
                      del.mutate(m.id, {
                        onSuccess: () => toast("Meeting deleted", "positive"),
                        onError: (e) => toast(apiErrorMessage(e), "danger"),
                      })
                    }
                    className="shrink-0 text-fg-subtle hover:text-danger"
                    title="Delete"
                    aria-label={`Delete meeting${m.title ? `: ${m.title}` : ""}`}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
                <div className="text-11 text-fg-subtle">
                  {new Date(m.scheduled_at).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}
                  {m.duration_minutes ? ` · ${m.duration_minutes}m` : ""}
                  {m.outcome ? ` · ${m.outcome}` : ""}
                </div>
                {m.notes && <p className="mt-0.5 line-clamp-2 text-11 text-fg-muted">{m.notes}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function LeadTasksPanel({ leadId }: { leadId: number }) {
  const [showForm, setShowForm] = useState(false);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskPriority, setTaskPriority] = useState("medium");
  const [taskDue, setTaskDue] = useState("");
  const { data } = useOutreachTasks({ outreach_lead_id: leadId, page_size: 20 });
  const create = useCreateOutreachTask();
  const patch = usePatchOutreachTask();
  const del = useDeleteOutreachTask();

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!taskTitle.trim()) return;
    create.mutate(
      { title: taskTitle.trim(), priority: taskPriority, due_at: taskDue || null, outreach_lead_id: leadId },
      {
        onSuccess: () => {
          toast("Task created", "positive");
          setShowForm(false); setTaskTitle(""); setTaskDue("");
        },
        onError: () => toast("Failed to create task", "danger"),
      },
    );
  }

  const tasks = data?.items ?? [];
  return (
    <Panel
      title={`Tasks (${data?.total ?? tasks.length})`}
      action={
        <button onClick={() => setShowForm((p) => !p)} className="text-11 text-accent hover:underline">
          {showForm ? "Cancel" : "+ New task"}
        </button>
      }
    >
      {showForm && (
        <form onSubmit={submit} className="mb-3 flex flex-wrap items-end gap-2 rounded-md border border-line bg-surface p-2.5">
          <div className="min-w-0 flex-1">
            <label className="mb-1 block text-11 text-fg-subtle">Title</label>
            <input
              autoFocus value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} placeholder="Task title…"
              className="h-8 w-full rounded-md border border-line bg-control px-2 text-12 text-fg outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="mb-1 block text-11 text-fg-subtle">Priority</label>
            <select
              value={taskPriority} onChange={(e) => setTaskPriority(e.target.value)}
              className="h-8 rounded-md border border-line bg-control px-2 text-12 text-fg outline-none focus:border-accent"
            >
              {["low", "medium", "high", "urgent"].map((p) => (
                <option key={p} value={p}>{p[0].toUpperCase() + p.slice(1)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-11 text-fg-subtle">Due date</label>
            <input
              type="date" value={taskDue}
              onChange={(e) => setTaskDue(e.target.value ? `${e.target.value}T09:00:00Z` : "")}
              className="h-8 rounded-md border border-line bg-control px-2 text-12 text-fg outline-none focus:border-accent"
            />
          </div>
          <Button type="submit" variant="primary" size="sm" disabled={!taskTitle.trim() || create.isPending}>
            {create.isPending ? "Saving…" : "Add"}
          </Button>
        </form>
      )}
      {tasks.length === 0 ? (
        <p className="text-12 text-fg-subtle">No tasks yet.</p>
      ) : (
        <div className="space-y-1">
          {tasks.map((t: OutreachTaskOut) => (
            <div key={t.id} className="flex items-center gap-2 py-1">
              <button
                onClick={() =>
                  t.status !== "completed" && t.status !== "cancelled" &&
                  patch.mutate(
                    { id: t.id, body: { status: "completed" } },
                    { onSuccess: () => toast("Done!", "positive"), onError: (e) => toast(apiErrorMessage(e), "danger") },
                  )
                }
                className={t.status === "completed" ? "text-positive" : "text-fg-subtle hover:text-positive"}
                title="Mark complete"
                aria-label={`Mark "${t.title}" complete`}
              >
                <CheckSquare size={14} />
              </button>
              <div className="min-w-0 flex-1">
                <span className={`block truncate text-12 ${t.status === "completed" ? "line-through text-fg-subtle" : t.is_overdue ? "text-danger" : "text-fg"}`}>
                  {t.title}
                </span>
                {t.due_at && (
                  <span className="text-11 text-fg-subtle">
                    Due {new Date(t.due_at).toLocaleDateString()}
                    {t.is_overdue && <span className="ml-1 text-danger">· overdue</span>}
                  </span>
                )}
              </div>
              <button
                onClick={() =>
                  del.mutate(t.id, {
                    onSuccess: () => toast("Deleted", "positive"),
                    onError: (e) => toast(apiErrorMessage(e), "danger"),
                  })
                }
                className="text-fg-subtle hover:text-danger"
                title="Delete"
                aria-label={`Delete "${t.title}"`}
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

export function OutreachLeadDetailPage() {
  const { id } = useParams();
  const leadId = Number(id);
  const { data: lead, isLoading, isError, error, refetch } = useOutreachLead(leadId);
  const messages = useOutreachMessages(leadId);
  const timeline = useOutreachTimeline(leadId);
  const patch = usePatchOutreachLead(leadId);

  if (isError) return <div className="p-4"><ErrorState title="Couldn't load lead" error={error} onRetry={refetch} /></div>;
  if (isLoading || !lead) return <div className="grid h-full place-items-center"><Spinner size={20} /></div>;

  return (
    <>
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            <Link to="/outreach/leads" className="text-fg-subtle hover:text-fg" aria-label="Back to Outreach leads"><ArrowLeft size={16} /></Link>
            {lead.company_name}
            <GradeBadge grade={lead.grade} />
            <PriorityBadge priority={lead.priority} />
          </span>
        }
        subtitle={lead.company_domain}
      >
        <div className="flex items-center gap-2">
          <span className="text-11 text-fg-subtle">Stage</span>
          <select
            value={lead.stage}
            onChange={(e) =>
              patch.mutate(
                { stage: e.target.value as never },
                { onSuccess: () => toast("Stage updated", "positive"), onError: (err) => toast(apiErrorMessage(err), "danger") },
              )
            }
            className="h-8 rounded-md border border-line bg-control px-2 text-12 text-fg outline-none focus:border-accent"
          >
            {STAGE_ORDER.map((s) => <option key={s} value={s}>{stageLabel(s)}</option>)}
          </select>
        </div>
      </PageHeader>

      <div className="grid gap-4 p-4 lg:grid-cols-3">
        {/* left: intelligence + contacts + follow-up */}
        <div className="space-y-4">
          <Panel title="Intelligence">
            <dl className="space-y-1.5 text-12">
              <div className="flex justify-between"><dt className="text-fg-subtle">Lead score</dt><dd className="text-fg">{fmtScore(lead.lead_score)} <span className="text-fg-subtle">({lead.grade || "—"})</span></dd></div>
              <div className="flex justify-between"><dt className="text-fg-subtle">Service</dt><dd className="text-fg">{serviceLabel(lead.service_interest)}</dd></div>
              <div className="flex justify-between"><dt className="text-fg-subtle">Stage</dt><dd><StageBadge stage={lead.stage} /></dd></div>
            </dl>
            {lead.recommended_pitch && (
              <div className="mt-3 rounded-md border border-accent/40 bg-accent/10 p-2.5">
                <div className="mb-0.5 flex items-center gap-1.5 text-11 font-semibold text-accent">
                  <Sparkles size={12} /> Recommended pitch{lead.recommended_offering ? ` · ${lead.recommended_offering}` : ""}
                </div>
                <p className="text-12 text-fg-muted">{lead.recommended_pitch}</p>
              </div>
            )}
            {lead.qualification_reason && <p className="mt-2 text-12 text-fg-subtle">{lead.qualification_reason}</p>}
          </Panel>

          <Panel title="Follow-up">
            <FollowUpPicker leadId={leadId} value={lead.next_action_at} />
          </Panel>

          <Panel title={`Contacts (${lead.contacts.length})`}>
            {lead.contacts.length === 0 ? (
              <p className="text-12 text-fg-subtle">No decision makers resolved for this company.</p>
            ) : (
              <div className="space-y-1.5">
                {lead.contacts.map((c) => (
                  <div key={c.decision_maker_id} className="rounded-md border border-line bg-base p-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-12 font-medium text-fg">{c.full_name}</span>
                      {c.recommendation_rank ? (
                        <Badge tone={c.recommendation_rank === "primary" ? "positive" : c.recommendation_rank === "secondary" ? "accent" : "neutral"}>
                          {c.recommendation_rank[0].toUpperCase() + c.recommendation_rank.slice(1)}
                        </Badge>
                      ) : c.is_primary ? (
                        <Badge tone="accent">Primary</Badge>
                      ) : null}
                    </div>
                    <div className="text-11 text-fg-subtle">
                      {c.title || "—"}
                      {c.department ? ` · ${c.department}` : ""}
                    </div>
                    <div className="text-11 text-accent">{c.email || "No email"}</div>
                    {(c.influence_score != null || c.confidence_level || c.relationship_status) && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {c.influence_score != null && <Badge tone="accent">Influence {c.influence_score}</Badge>}
                        {c.confidence_level && (
                          <Badge tone={c.confidence_level === "High" ? "positive" : c.confidence_level === "Medium" ? "accent" : "neutral"}>
                            {c.confidence_level}
                          </Badge>
                        )}
                        {c.relationship_status && <Badge tone="neutral">{c.relationship_status}</Badge>}
                      </div>
                    )}
                    {c.next_action && (
                      <div className="mt-0.5 text-11 text-fg-subtle" title={c.next_action_reason}>
                        Next: {c.next_action}
                      </div>
                    )}
                    {c.is_primary && c.recommendation_reason.length > 0 && (
                      <ul className="mt-1 space-y-0.5">
                        {c.recommendation_reason.slice(0, 3).map((r, i) => (
                          <li key={i} className="text-11 text-fg-muted">› {r}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Panel>

          {lead.signals.length > 0 && (
            <Panel title="Signals">
              <ul className="space-y-1.5">
                {lead.signals.map((s, i) => (
                  <li key={i} className="text-12">
                    <span className="text-fg">{s.label}</span>
                    {s.detail && <span className="block text-11 text-fg-subtle">{s.detail}</span>}
                  </li>
                ))}
              </ul>
            </Panel>
          )}
        </div>

        {/* middle: messages */}
        <div className="lg:col-span-1">
          <Panel title="Messages" action={<Composer leadId={leadId} contacts={lead.contacts as OutreachContactOut[]} />}>
            {messages.isLoading ? (
              <div className="py-3"><Spinner size={14} /></div>
            ) : (messages.data ?? []).length === 0 ? (
              <EmptyState icon={<Mail size={18} />} title="No messages yet" description="Create a draft from a template to start the conversation." />
            ) : (
              <div className="space-y-2">
                {messages.data!.map((m) => <MessageCard key={m.id} msg={m} />)}
              </div>
            )}
          </Panel>
        </div>

        {/* right: unified timeline */}
        <div className="lg:col-span-1">
          <Panel title="Activity">
            {timeline.isLoading ? (
              <div className="py-3"><Spinner size={14} /></div>
            ) : (timeline.data ?? []).length === 0 ? (
              <p className="text-12 text-fg-subtle">No activity yet.</p>
            ) : (
              <ol className="space-y-2">
                {timeline.data!.map((e) => {
                  const isMeeting = e.event_type === "meeting";
                  const isTask = e.event_type === "task";
                  const isNote = e.type === "note_added";
                  const Icon = isMeeting ? Calendar : isTask ? CheckSquare : Clock;
                  return (
                    <li key={e.event_id} className="flex gap-2 text-12">
                      <Icon
                        size={13}
                        className={`mt-0.5 shrink-0 ${isNote ? "text-accent" : isMeeting ? "text-fg" : "text-fg-subtle"}`}
                      />
                      <div className="min-w-0">
                        <div className={isNote ? "text-fg" : "text-fg text-opacity-90"}>
                          {e.label}{e.detail ? ` — ${e.detail}` : ""}
                        </div>
                        <div className="text-11 text-fg-subtle">
                          {isNote && <span className="mr-1 text-accent">note ·</span>}
                          {e.actor ? e.actor.split("@")[0] : "system"} · {fmtRelative(e.timestamp)}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ol>
            )}
            <NoteComposer leadId={leadId} />
          </Panel>
        </div>
      </div>

      {/* meetings + tasks */}
      <div className="grid gap-4 p-4 pt-0 lg:grid-cols-2">
        <MeetingLogPanel leadId={leadId} />
        <LeadTasksPanel leadId={leadId} />
      </div>
    </>
  );
}
