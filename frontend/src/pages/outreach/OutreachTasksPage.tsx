import { useState } from "react";
import { CheckSquare, Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/shell/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import {
  useOutreachTasks,
  useCreateOutreachTask,
  usePatchOutreachTask,
  useDeleteOutreachTask,
} from "@/lib/api/queries";
import { fmtRelative } from "@/lib/format";
import type { OutreachTaskOut } from "@/lib/api/types";

type Priority = "low" | "medium" | "high" | "urgent";
type TaskStatus = "pending" | "in_progress" | "completed" | "cancelled";

const PRIORITY_TONE: Record<Priority, "neutral" | "accent" | "warning" | "danger"> = {
  low: "neutral",
  medium: "accent",
  high: "warning",
  urgent: "danger",
};

const STATUS_TONE: Record<TaskStatus, "neutral" | "accent" | "positive" | "danger"> = {
  pending: "neutral",
  in_progress: "accent",
  completed: "positive",
  cancelled: "danger",
};

function TaskRow({ task }: { task: OutreachTaskOut }) {
  const patch = usePatchOutreachTask();
  const del = useDeleteOutreachTask();

  function complete() {
    patch.mutate(
      { id: task.id, body: { status: "completed" } },
      { onSuccess: () => toast("Task completed", "positive") },
    );
  }

  function remove() {
    del.mutate(task.id, {
      onSuccess: () => toast("Task deleted", "positive"),
      onError: () => toast("Cannot delete — permission denied", "danger"),
    });
  }

  return (
    <tr className="border-b border-line/60 hover:bg-raised">
      <td className="px-3.5 py-2.5">
        <span className={`block font-medium ${task.is_overdue ? "text-danger" : "text-fg"}`}>
          {task.title}
          {task.is_overdue && (
            <Badge tone="danger" className="ml-2">Overdue</Badge>
          )}
        </span>
        {task.description && (
          <span className="block truncate text-11 text-fg-subtle">{task.description}</span>
        )}
      </td>
      <td className="px-2 py-2.5">
        <Badge tone={PRIORITY_TONE[task.priority as Priority] ?? "neutral"}>
          {task.priority}
        </Badge>
      </td>
      <td className="px-2 py-2.5">
        <Badge tone={STATUS_TONE[task.status as TaskStatus] ?? "neutral"}>
          {task.status.replace("_", " ")}
        </Badge>
      </td>
      <td className="px-2 py-2.5 text-12 text-fg-muted">
        {task.company_name || task.company_domain || "—"}
      </td>
      <td className="px-2 py-2.5 text-12 text-fg-muted">
        {task.assigned_to_email ? task.assigned_to_email.split("@")[0] : "Unassigned"}
      </td>
      <td className="px-2 py-2.5 text-11 text-fg-subtle">
        {task.due_at ? new Date(task.due_at).toLocaleDateString() : "—"}
      </td>
      <td className="px-2 py-2.5 text-11 text-fg-subtle">
        {fmtRelative(task.updated_at)}
      </td>
      <td className="px-2 py-2.5">
        <div className="flex items-center gap-1.5 justify-end">
          {task.status !== "completed" && task.status !== "cancelled" && (
            <button
              onClick={complete}
              className="text-positive hover:text-positive/80"
              title="Mark complete"
              aria-label={`Mark "${task.title}" complete`}
            >
              <CheckSquare size={14} />
            </button>
          )}
          <button
            onClick={remove}
            className="text-fg-subtle hover:text-danger"
            title="Delete"
            aria-label={`Delete "${task.title}"`}
          >
            <Trash2 size={13} />
          </button>
        </div>
      </td>
    </tr>
  );
}

function CreateTaskForm({ onDone }: { onDone: () => void }) {
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("medium");
  const [dueAt, setDueAt] = useState("");
  const create = useCreateOutreachTask();

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    create.mutate(
      { title: title.trim(), priority, due_at: dueAt || null },
      {
        onSuccess: () => {
          toast("Task created", "positive");
          onDone();
        },
        onError: () => toast("Failed to create task", "danger"),
      },
    );
  }

  return (
    <form onSubmit={submit} className="flex items-end gap-2 rounded-lg border border-line bg-surface p-3">
      <div className="flex-1">
        <label className="mb-1 block text-11 text-fg-subtle">Title</label>
        <input
          autoFocus
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Task title…"
          className="h-8 w-full rounded-md border border-line bg-control px-2 text-13 text-fg outline-none focus:border-accent"
        />
      </div>
      <div>
        <label className="mb-1 block text-11 text-fg-subtle">Priority</label>
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
          className="h-8 rounded-md border border-line bg-control px-2 text-13 text-fg outline-none focus:border-accent"
        >
          {["low", "medium", "high", "urgent"].map((p) => (
            <option key={p} value={p}>{p[0].toUpperCase() + p.slice(1)}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="mb-1 block text-11 text-fg-subtle">Due date</label>
        <input
          type="date"
          value={dueAt}
          onChange={(e) => setDueAt(e.target.value ? `${e.target.value}T09:00:00Z` : "")}
          className="h-8 rounded-md border border-line bg-control px-2 text-13 text-fg outline-none focus:border-accent"
        />
      </div>
      <Button type="submit" variant="primary" size="sm" disabled={create.isPending || !title.trim()}>
        {create.isPending ? "Creating…" : "Create"}
      </Button>
      <Button type="button" variant="ghost" size="sm" onClick={onDone}>
        Cancel
      </Button>
    </form>
  );
}

export function OutreachTasksPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [mine, setMine] = useState(false);
  const [overdueOnly, setOverdueOnly] = useState(false);

  const { data, isLoading, isError, error, refetch } = useOutreachTasks({
    status: statusFilter || undefined,
    mine: mine || undefined,
    overdue_only: overdueOnly || undefined,
    page_size: 100,
  });
  const tasks = data?.items ?? [];

  return (
    <>
      <PageHeader
        title="Tasks"
        subtitle={data ? `${data.total} task${data.total !== 1 ? "s" : ""}` : "Outreach follow-up tasks"}
      >
        <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
          <Plus size={13} /> New task
        </Button>
      </PageHeader>

      <div className="space-y-4 p-4">
        {showCreate && <CreateTaskForm onDone={() => setShowCreate(false)} />}

        <div className="flex items-center gap-3 flex-wrap">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-8 rounded-md border border-line bg-control px-2 text-12 text-fg outline-none focus:border-accent"
          >
            <option value="">All statuses</option>
            {["pending", "in_progress", "completed", "cancelled"].map((s) => (
              <option key={s} value={s}>{s.replace("_", " ")}</option>
            ))}
          </select>
          <label className="flex items-center gap-1.5 text-12 text-fg-muted">
            <input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} /> My tasks
          </label>
          <label className="flex items-center gap-1.5 text-12 text-fg-muted">
            <input type="checkbox" checked={overdueOnly} onChange={(e) => setOverdueOnly(e.target.checked)} />
            Overdue only
          </label>
        </div>

        <div className="panel">
          {isError ? (
            <ErrorState title="Couldn't load tasks" error={error} onRetry={refetch} />
          ) : isLoading ? (
            <div className="grid place-items-center py-12"><Spinner size={18} /></div>
          ) : tasks.length === 0 ? (
            <EmptyState
              icon={<CheckSquare size={20} />}
              title="No tasks"
              description="Create a task to track follow-ups, calls, and next steps."
            />
          ) : (
            <table className="w-full text-13">
              <thead>
                <tr className="border-b border-line text-left text-11 uppercase tracking-wide text-fg-subtle">
                  <th className="px-3.5 py-2 font-medium">Task</th>
                  <th className="px-2 py-2 font-medium">Priority</th>
                  <th className="px-2 py-2 font-medium">Status</th>
                  <th className="px-2 py-2 font-medium">Company</th>
                  <th className="px-2 py-2 font-medium">Assigned to</th>
                  <th className="px-2 py-2 font-medium">Due</th>
                  <th className="px-2 py-2 font-medium">Updated</th>
                  <th className="px-2 py-2 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => <TaskRow key={t.id} task={t} />)}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}
