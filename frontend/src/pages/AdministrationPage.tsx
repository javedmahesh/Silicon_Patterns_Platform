import { useMemo, useState } from "react";
import { Trash2 } from "lucide-react";

import { Pager } from "@/components/data/Pager";
import { PageHeader } from "@/components/shell/PageHeader";
import { apiErrorMessage } from "@/lib/api/client";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import { useAdminUsers, useCrmMutations, useUserAudit } from "@/lib/api/queries";
import type { UserOut } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/store";
import { cx } from "@/lib/cx";
import { fmtDate, fmtInt, fmtRelative } from "@/lib/format";

const ROLES = ["super_admin", "admin", "manager", "member"] as const;
/** Internal role id → UI label ("member" is surfaced as "Employee"). */
const ROLE_LABEL: Record<string, string> = {
  super_admin: "Super Admin", admin: "Admin", manager: "Manager", member: "Employee",
};
const STATUS_FILTERS = ["", "pending", "active", "disabled", "rejected", "deleted"] as const;
const STATUS_TONE: Record<string, "neutral" | "accent" | "positive" | "warning" | "danger"> = {
  active: "positive", pending: "warning", disabled: "neutral", rejected: "danger", deleted: "danger",
};
const PAGE_SIZE = 25;

type ConfirmAction = { type: "reject" | "disable" | "delete"; user: UserOut };

export function AdministrationPage() {
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [page, setPage] = useState(1);
  const [showAudit, setShowAudit] = useState(false);
  const [confirmAction, setConfirmAction] = useState<ConfirmAction | null>(null);

  const { data, isLoading, isError, error, refetch } = useAdminUsers({
    status: statusFilter || undefined,
    q: q || undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });
  // Widened past the 100-default so the approval-date lookup below (derived,
  // not backend-stored) has the best chance of covering older accounts too.
  const audit = useUserAudit(500);
  const { updateUser, rejectUser, deleteUser } = useCrmMutations();

  const approvedAt = useMemo(() => {
    const map = new Map<string, string>();
    for (const e of audit.data ?? []) {
      if (e.action === "approved" && e.target_email && e.created_at) {
        const prev = map.get(e.target_email);
        if (!prev || e.created_at > prev) map.set(e.target_email, e.created_at);
      }
    }
    return map;
  }, [audit.data]);

  function setQuery(next: string) {
    setQ(next);
    setPage(1);
  }
  function setStatus(next: string) {
    setStatusFilter(next);
    setPage(1);
  }

  function runConfirmed() {
    if (!confirmAction) return;
    const { type, user: target } = confirmAction;
    const opts = {
      onError: (e: unknown) => toast(apiErrorMessage(e), "danger"),
      onSettled: () => setConfirmAction(null),
    };
    if (type === "reject") rejectUser.mutate(target.id, opts);
    else if (type === "disable") updateUser.mutate({ id: target.id, patch: { is_active: false } }, opts);
    else deleteUser.mutate(target.id, opts);
  }
  const confirmPending = rejectUser.isPending || updateUser.isPending || deleteUser.isPending;

  if (isLoading) {
    return (
      <>
        <PageHeader title="Administration" subtitle="Account approvals, roles, and audit history" />
        <div className="grid place-items-center py-24">
          <Spinner size={18} />
        </div>
      </>
    );
  }

  if (isError) {
    return (
      <>
        <PageHeader title="Administration" subtitle="Account approvals, roles, and audit history" />
        <div className="p-4">
          <div className="panel grid place-items-center gap-2 py-12 text-center">
            <p className="text-13 text-danger">Couldn't load accounts — {apiErrorMessage(error)}</p>
            <Button size="sm" variant="ghost" onClick={() => refetch()}>Retry</Button>
          </div>
        </div>
      </>
    );
  }

  const users = data?.items ?? [];
  const pending = users.filter((u) => u.status === "pending");
  const rest = users.filter((u) => u.status !== "pending");

  return (
    <>
      <PageHeader title="Administration" subtitle="Account approvals, roles, and audit history" />
      <div className="space-y-4 p-4">
        <div className="flex flex-wrap gap-2">
          <DebouncedInput value={q} onChange={setQuery} placeholder="Search by name or email…" className="max-w-xs" />
          <select
            value={statusFilter}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-md border border-line bg-control px-2 py-1.5 text-13 text-fg outline-none focus:border-accent"
          >
            {STATUS_FILTERS.map((s) => (
              <option key={s} value={s} className="bg-surface">{s ? s : "All statuses"}</option>
            ))}
          </select>
        </div>

        {pending.length > 0 && (
          <div className="panel">
            <div className="border-b border-line px-3.5 py-2 text-12 font-semibold text-warning">
              Pending approval ({pending.length})
            </div>
            <div className="divide-y divide-line">
              {pending.map((u) => (
                <UserRow
                  key={u.id}
                  u={u}
                  selfId={user?.id}
                  actorRole={user?.role}
                  approvedAt={approvedAt.get(u.email)}
                  onReject={(target) => setConfirmAction({ type: "reject", user: target })}
                  onDisable={(target) => setConfirmAction({ type: "disable", user: target })}
                  onDelete={(target) => setConfirmAction({ type: "delete", user: target })}
                />
              ))}
            </div>
          </div>
        )}

        <div className="panel">
          <div className="border-b border-line px-3.5 py-2 text-12 font-medium text-fg">
            All accounts ({rest.length}{data && data.total > data.items.length ? ` of ${data.total}` : ""})
          </div>
          <div className="divide-y divide-line">
            {rest.length === 0 ? (
              <p className="px-3.5 py-3 text-12 text-fg-subtle">No accounts match this filter.</p>
            ) : (
              rest.map((u) => (
                <UserRow
                  key={u.id}
                  u={u}
                  selfId={user?.id}
                  actorRole={user?.role}
                  approvedAt={approvedAt.get(u.email)}
                  onReject={(target) => setConfirmAction({ type: "reject", user: target })}
                  onDisable={(target) => setConfirmAction({ type: "disable", user: target })}
                  onDelete={(target) => setConfirmAction({ type: "delete", user: target })}
                />
              ))
            )}
          </div>
          {data && data.pages > 1 && (
            <div className="border-t border-line px-2">
              <Pager page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onPage={setPage} />
            </div>
          )}
        </div>

        <div className="panel">
          <button
            type="button"
            onClick={() => setShowAudit((s) => !s)}
            className="flex w-full items-center justify-between px-3.5 py-2 text-12 font-medium text-fg hover:bg-raised"
          >
            <span>Audit log</span>
            <span className="text-11 text-fg-subtle">{showAudit ? "Hide" : "Show"}</span>
          </button>
          {showAudit && (
            <div className="max-h-80 divide-y divide-line/60 overflow-y-auto border-t border-line">
              {(audit.data ?? []).length === 0 ? (
                <p className="px-3.5 py-3 text-12 text-fg-subtle">No audit entries yet.</p>
              ) : (
                audit.data!.map((e) => (
                  <div key={e.id} className="flex items-center justify-between gap-2 px-3.5 py-1.5 text-12">
                    <span className="text-fg-muted">
                      <span className="font-medium text-fg">{e.action.replace(/_/g, " ")}</span>
                      {" "}{e.target_email}{e.detail ? ` · ${e.detail}` : ""}
                    </span>
                    <span className="shrink-0 text-11 text-fg-subtle">
                      {e.actor_email ? e.actor_email.split("@")[0] : "system"} · {fmtRelative(e.created_at)}
                    </span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      <ConfirmDialog
        action={confirmAction}
        pending={confirmPending}
        onCancel={() => setConfirmAction(null)}
        onConfirm={runConfirmed}
      />
    </>
  );
}

function UserRow({
  u, selfId, actorRole, approvedAt, onReject, onDisable, onDelete,
}: {
  u: UserOut;
  selfId: number | undefined;
  actorRole: string | undefined;
  approvedAt?: string;
  onReject: (u: UserOut) => void;
  onDisable: (u: UserOut) => void;
  onDelete: (u: UserOut) => void;
}) {
  const { updateUser, approveUser } = useCrmMutations();
  const isSelf = u.id === selfId;
  const deleted = u.status === "deleted";
  // Mirrors backend/services.py::_guard_super_admin_tier — only a super_admin may
  // touch another super_admin's role/active-state, or grant super_admin at all.
  const canManageTier = u.role !== "super_admin" || actorRole === "super_admin";
  const assignableRoles = actorRole === "super_admin" ? ROLES : ROLES.filter((r) => r !== "super_admin");
  const err = (e: unknown) => toast(apiErrorMessage(e), "danger");

  return (
    <div className={cx("flex flex-wrap items-center gap-3 px-3.5 py-2.5", !u.is_active && "opacity-70")}>
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-control text-12 text-fg-muted">
        {(u.full_name || u.email).slice(0, 1).toUpperCase()}
      </span>
      <div className="min-w-0 flex-1">
        <span className="block truncate text-13 text-fg">
          {u.full_name || u.email}{isSelf && <span className="ml-1 text-11 text-fg-subtle">(you)</span>}
        </span>
        <span className="block truncate text-11 text-fg-subtle">{u.email}</span>
      </div>
      <Badge tone={STATUS_TONE[u.status] ?? "neutral"}>{u.status}</Badge>
      <div className="hidden text-right text-11 text-fg-subtle sm:block">
        <div>{u.last_login_at ? `seen ${fmtRelative(u.last_login_at)}` : "never logged in"}</div>
        <div>{fmtInt(u.login_count)} logins</div>
      </div>
      <div className="hidden text-right text-11 text-fg-subtle md:block">
        <div>joined {fmtDate(u.created_at)}</div>
        {approvedAt && <div>approved {fmtDate(approvedAt)}</div>}
      </div>

      {u.status === "pending" ? (
        <div className="flex gap-1.5">
          <Button size="sm" variant="primary" onClick={() => approveUser.mutate(u.id, { onError: err })}>Approve</Button>
          <Button size="sm" variant="ghost" onClick={() => onReject(u)}>Reject</Button>
        </div>
      ) : deleted ? (
        <span className="text-11 text-fg-subtle">removed</span>
      ) : (
        <>
          <select
            value={u.role}
            disabled={isSelf || !canManageTier}
            title={isSelf ? "You can't change your own role" : !canManageTier ? "Only a super admin can do this" : undefined}
            onChange={(e) => updateUser.mutate({ id: u.id, patch: { role: e.target.value } }, { onError: err })}
            className="rounded-md border border-line bg-control px-2 py-1 text-12 text-fg outline-none focus:border-accent disabled:opacity-40"
          >
            {assignableRoles.map((r) => (
              <option key={r} value={r} className="bg-surface">{ROLE_LABEL[r]}</option>
            ))}
          </select>
          <Button
            size="sm"
            variant="ghost"
            disabled={(isSelf && u.is_active) || !canManageTier}
            title={isSelf && u.is_active ? "You can't disable your own account" : !canManageTier ? "Only a super admin can do this" : undefined}
            onClick={() =>
              u.is_active ? onDisable(u) : updateUser.mutate({ id: u.id, patch: { is_active: true } }, { onError: err })
            }
          >
            {u.is_active ? "Disable" : "Enable"}
          </Button>
          <button
            type="button"
            title={isSelf ? "You can't delete your own account" : !canManageTier ? "Only a super admin can do this" : "Delete account"}
            disabled={isSelf || !canManageTier}
            onClick={() => onDelete(u)}
            className="text-fg-subtle enabled:hover:text-danger disabled:opacity-40"
          >
            <Trash2 size={15} />
          </button>
        </>
      )}
    </div>
  );
}

const CONFIRM_COPY: Record<ConfirmAction["type"], (email: string) => { title: string; body: string; confirmLabel: string }> = {
  reject: (email) => ({
    title: "Reject registration",
    body: `Reject ${email}'s registration request? They won't be able to sign in.`,
    confirmLabel: "Reject",
  }),
  disable: (email) => ({
    title: "Disable account",
    body: `Disable ${email}? They'll be signed out immediately and unable to sign back in until re-enabled.`,
    confirmLabel: "Disable",
  }),
  delete: (email) => ({
    title: "Delete account",
    body: `Delete ${email}? This anonymizes the account. It's kept for audit but can't be restored.`,
    confirmLabel: "Delete",
  }),
};

function ConfirmDialog({
  action, pending, onCancel, onConfirm,
}: {
  action: ConfirmAction | null;
  pending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  if (!action) return null;
  const c = CONFIRM_COPY[action.type](action.user.email);
  return (
    <Modal
      open
      onClose={onCancel}
      title={c.title}
      footer={
        <>
          <Button size="sm" variant="ghost" onClick={onCancel} disabled={pending}>Cancel</Button>
          <Button size="sm" variant="danger" onClick={onConfirm} disabled={pending}>{c.confirmLabel}</Button>
        </>
      }
    >
      <p className="text-13 text-fg-muted">{c.body}</p>
    </Modal>
  );
}
