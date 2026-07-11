import { useState } from "react";
import { Plus, StickyNote, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";

import { StatusSelect } from "@/components/crm/status";
import { GradeBadge } from "@/components/data/GradeBadge";
import { PageHeader } from "@/components/shell/PageHeader";
import { apiErrorMessage } from "@/lib/api/client";
import { Button } from "@/components/ui/Button";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import { useAssignableUsers, useAssignments, useCompanies, useCrmMutations, useWorkload } from "@/lib/api/queries";
import type { AssignmentOut } from "@/lib/api/types";
import { cx } from "@/lib/cx";
import { fmtInt, monogram } from "@/lib/format";

const onMutateError = (e: unknown) => toast(apiErrorMessage(e), "danger");

type Tab = "assignments" | "workload";

export function TeamPage() {
  const [tab, setTab] = useState<Tab>("assignments");
  const tabs: { id: Tab; label: string }[] = [
    { id: "assignments", label: "Assignments" },
    { id: "workload", label: "Workload" },
  ];

  return (
    <>
      <PageHeader title="Team" subtitle="Lead assignment and workload">
        <div className="flex gap-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={cx(
                "rounded-md px-3 py-1.5 text-13",
                tab === t.id ? "bg-accent-weak text-fg" : "text-fg-muted hover:bg-raised",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </PageHeader>

      <div className="p-4">
        {tab === "assignments" && <AssignmentsTab />}
        {tab === "workload" && <WorkloadTab />}
      </div>
    </>
  );
}

function AssignmentsTab() {
  const { data: assignments, isLoading } = useAssignments();
  const { data: users } = useAssignableUsers();
  const { createAssignment } = useCrmMutations();

  const [q, setQ] = useState("");
  const [domain, setDomain] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [userId, setUserId] = useState<number | "">("");
  const [status, setStatus] = useState("assigned");
  const [note, setNote] = useState("");
  const { data: search } = useCompanies({ q, page_size: 6 });

  const assignable = (users ?? []).filter((u) => u.is_active);

  function submit() {
    if (!domain || userId === "") return;
    createAssignment.mutate(
      { company_domain: domain, user_id: Number(userId), status, note: note.trim() },
      {
        onSuccess: () => {
          toast("Lead assigned", "positive");
          setDomain(""); setCompanyName(""); setQ(""); setUserId(""); setStatus("assigned"); setNote("");
        },
        onError: onMutateError,
      },
    );
  }

  return (
    <div className="space-y-4">
      <div className="panel p-3.5">
        <div className="mb-2 text-13 font-medium text-fg">Assign a lead</div>
        <div className="grid gap-2 md:grid-cols-[1fr_1fr_auto] md:items-start">
          <div className="relative">
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
          <select
            value={userId}
            onChange={(e) => setUserId(e.target.value ? Number(e.target.value) : "")}
            className="rounded-md border border-line bg-control px-2 py-1.5 text-13 text-fg outline-none focus:border-accent"
          >
            <option value="">Assign to…</option>
            {assignable.map((u) => (
              <option key={u.id} value={u.id} className="bg-surface">
                {(u.full_name || u.email)} ({u.role})
              </option>
            ))}
          </select>
          <StatusSelect value={status} onChange={setStatus} />
        </div>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          placeholder="Add a note for the assignee (optional) — context, priority, or what to keep in mind…"
          className="mt-2 w-full resize-y rounded-md border border-line bg-control px-2.5 py-1.5 text-13 text-fg outline-none placeholder:text-fg-subtle focus:border-accent"
        />
        <div className="mt-2 flex items-center justify-between gap-3">
          <span className="truncate text-11 text-fg-subtle">
            {domain ? `Selected: ${companyName} (${domain})` : "Pick a company and a teammate, then assign."}
          </span>
          <Button size="sm" onClick={submit} disabled={!domain || userId === "" || createAssignment.isPending}>
            Assign
          </Button>
        </div>
      </div>

      <div className="panel">
        {isLoading ? (
          <div className="grid place-items-center py-12"><Spinner size={18} /></div>
        ) : (assignments ?? []).length === 0 ? (
          <EmptyState title="No assignments yet" description="Assign a lead above to get started." />
        ) : (
          <div className="divide-y divide-line">
            {assignments!.map((a) => <AssignmentRow key={a.id} a={a} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function AssignmentRow({ a }: { a: AssignmentOut }) {
  const { updateAssignment, unassign } = useCrmMutations();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(a.note ?? "");

  function openEditor() {
    setDraft(a.note ?? "");
    setEditing(true);
  }

  function saveNote() {
    updateAssignment.mutate(
      { id: a.id, patch: { note: draft.trim() } },
      { onSuccess: () => setEditing(false), onError: onMutateError },
    );
  }

  return (
    <div className="px-3.5 py-2.5">
      <div className="flex items-center gap-3">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-line bg-control text-12 text-fg-muted">
          {monogram(a.company_name, a.company_domain)}
        </span>
        <Link to={`/companies/${encodeURIComponent(a.company_domain)}`} className="min-w-0 flex-1">
          <span className="block truncate text-13 text-fg hover:text-accent">{a.company_name}</span>
          <span className="block truncate text-11 text-fg-subtle">{a.user_name || a.user_email}</span>
        </Link>
        {a.grade ? <GradeBadge grade={a.grade} /> : null}
        <StatusSelect
          value={a.status}
          onChange={(s) => updateAssignment.mutate({ id: a.id, patch: { status: s } }, { onError: onMutateError })}
        />
        <button
          type="button"
          onClick={() => unassign.mutate(a.id, { onError: onMutateError })}
          title="Unassign"
          aria-label="Unassign"
          className="text-fg-subtle hover:text-danger"
        >
          <Trash2 size={15} />
        </button>
      </div>

      <div className="mt-2 pl-11">
        {editing ? (
          <div className="space-y-1.5">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={2}
              autoFocus
              placeholder="Note for the assignee — context, priority, what to keep in mind…"
              className="w-full resize-y rounded-md border border-line bg-control px-2.5 py-1.5 text-12 text-fg outline-none placeholder:text-fg-subtle focus:border-accent"
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={saveNote} disabled={updateAssignment.isPending}>Save note</Button>
              <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
            </div>
          </div>
        ) : a.note ? (
          <button
            type="button"
            onClick={openEditor}
            title="Edit note"
            className="group flex w-full items-start gap-1.5 text-left"
          >
            <StickyNote size={13} className="mt-0.5 shrink-0 text-fg-subtle" />
            <span className="whitespace-pre-wrap text-12 text-fg-muted group-hover:text-fg">{a.note}</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={openEditor}
            className="flex items-center gap-1 text-12 text-fg-subtle hover:text-accent"
          >
            <Plus size={12} /> Add a note
          </button>
        )}
      </div>
    </div>
  );
}

function WorkloadTab() {
  const { data, isLoading } = useWorkload();
  if (isLoading) return <div className="grid place-items-center py-12"><Spinner size={18} /></div>;
  if (!data) return null;
  return (
    <div className="space-y-4">
      <div className="panel flex items-center justify-between p-3.5">
        <span className="text-13 text-fg-muted">Unassigned A / B-grade leads</span>
        <span className="tabular text-18 text-fg">{fmtInt(data.unassigned_high_grade)}</span>
      </div>
      {data.users.length === 0 ? (
        <div className="panel"><EmptyState title="No assignments yet" description="Workload appears once leads are assigned." /></div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.users.map((u) => (
            <div key={u.user_id} className="panel p-3.5">
              <div className="flex items-center justify-between">
                <span className="truncate text-13 text-fg">{u.full_name || u.email}</span>
                <span className="text-11 capitalize text-fg-subtle">{u.role}</span>
              </div>
              <div className="mt-1 text-18 tabular text-fg">
                {fmtInt(u.total)} <span className="text-11 text-fg-subtle">leads</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {Object.entries(u.by_status).map(([s, n]) => (
                  <span key={s} className="rounded-full border border-line bg-control px-2 py-0.5 text-11 capitalize text-fg-muted">
                    {s.replace("_", " ")} {n}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
