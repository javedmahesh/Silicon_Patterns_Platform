import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";

import { AccountFormModal } from "@/components/cs/AccountFormModal";
import {
  AccountStatusBadge, ContractStatusBadge, HealthGradeBadge, HealthTrendBadge,
  MilestoneStatusBadge, RiskSeverityBadge, RiskStatusBadge, fmtMoney,
} from "@/components/cs/bits";
import { KeyValueGrid } from "@/components/profile/KeyValueGrid";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Input, Select } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { Tabs } from "@/components/ui/Tabs";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import { api } from "@/lib/api/endpoints";
import {
  useCsAccount, useCsAccountMutations, useCsContactMutations, useCsContacts,
  useCsContractMutations, useCsContracts, useCsHealth, useCsHealthHistory,
  useCsMilestoneMutations, useCsMilestones, useCsPlanMutations, useCsPlans,
  useCsRiskMutations, useCsRisks, useCsTimeline,
} from "@/lib/api/queries";
import {
  CS_CONTRACT_STATUSES, CS_MILESTONE_STATUSES, CS_RISK_SEVERITIES, CS_RISK_STATUSES,
  type CsSuccessPlanOut,
} from "@/lib/api/types";
import { enumLabel, fmtDate, fmtDateTime, fmtRelative } from "@/lib/format";

type Tab = "overview" | "health" | "contracts" | "plan" | "risks" | "activity";

export function AccountDetailPage() {
  const { id } = useParams();
  const accountId = Number(id);
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("overview");
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const { data: account, isLoading, isError, error, refetch } = useCsAccount(accountId);
  const qc = useQueryClient();
  const [deletePending, setDeletePending] = useState(false);

  if (isError) return <div className="p-4"><ErrorState title="Couldn't load account" error={error} onRetry={refetch} /></div>;
  if (isLoading || !account) return <div className="grid h-full place-items-center"><Spinner size={20} /></div>;

  // Deletes directly (not via the shared cs-mutation hook) and navigates away before
  // invalidating: this page's own useCsAccount(accountId) query is still mounted at the
  // moment of deletion, so an invalidate-then-navigate ordering leaves the navigation
  // waiting on a refetch of a query for a row that no longer exists. Leaving is safe
  // first; the list/dashboard queries still get refreshed for whenever they're next seen.
  async function confirmDelete() {
    setDeletePending(true);
    try {
      await api.cs.deleteAccount(accountId);
      toast("Account deleted", "positive");
      navigate("/customer-success/accounts");
      qc.invalidateQueries({ queryKey: ["cs"] });
    } catch (e) {
      toast(apiErrorMessage(e), "danger");
      setDeletePending(false);
    }
  }

  return (
    <>
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            <Link to="/customer-success/accounts" className="text-fg-subtle hover:text-fg" aria-label="Back to accounts"><ArrowLeft size={16} /></Link>
            {account.name}
            <AccountStatusBadge status={account.status} />
            <HealthGradeBadge grade={account.health_grade} />
          </span>
        }
        subtitle={account.company_domain ? (
          <Link to={`/companies/${encodeURIComponent(account.company_domain)}`} className="hover:text-accent">{account.company_domain}</Link>
        ) : undefined}
        actions={
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => setEditing(true)}>Edit</Button>
            <Button size="sm" variant="danger" onClick={() => setDeleting(true)}>Delete</Button>
          </div>
        }
      >
        <Tabs
          tabs={[
            { id: "overview", label: "Overview" },
            { id: "health", label: "Health" },
            { id: "contracts", label: "Contracts" },
            { id: "plan", label: "Success plan" },
            { id: "risks", label: "Risks" },
            { id: "activity", label: "Activity" },
          ]}
          active={tab}
          onChange={setTab}
        />
      </PageHeader>

      <div className="p-4">
        {tab === "overview" && <OverviewTab account={account} />}
        {tab === "health" && <HealthTab accountId={accountId} />}
        {tab === "contracts" && <ContractsTab accountId={accountId} />}
        {tab === "plan" && <PlansTab accountId={accountId} />}
        {tab === "risks" && <RisksTab accountId={accountId} />}
        {tab === "activity" && <ActivityTab accountId={accountId} />}
      </div>

      {editing && <AccountFormModal account={account} onClose={() => setEditing(false)} />}
      {deleting && (
        <Modal
          open
          onClose={() => setDeleting(false)}
          title="Delete account"
          footer={
            <>
              <Button variant="ghost" onClick={() => setDeleting(false)} disabled={deletePending}>Cancel</Button>
              <Button variant="danger" onClick={confirmDelete} disabled={deletePending}>Delete</Button>
            </>
          }
        >
          <p className="text-13 text-fg-muted">Delete “{account.name}”? This permanently removes the account and all of its contracts, plans, and history.</p>
        </Modal>
      )}
    </>
  );
}

function OverviewTab({ account }: { account: import("@/lib/api/types").CsAccountOut }) {
  const contacts = useCsContacts(account.id);
  const { create, remove } = useCsContactMutations();
  const [adding, setAdding] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const err = (e: unknown) => toast(apiErrorMessage(e), "danger");

  function submitContact() {
    if (!firstName.trim() && !lastName.trim()) return;
    create.mutate(
      {
        account_id: account.id, first_name: firstName.trim(), last_name: lastName.trim(), email: email.trim(),
        is_primary: false, notes: "", phone: "", role: "primary", title: "",
      },
      {
        onSuccess: () => { toast("Contact added", "positive"); setAdding(false); setFirstName(""); setLastName(""); setEmail(""); },
        onError: err,
      },
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="panel p-3.5">
        <div className="mb-2 text-13 font-medium text-fg">Details</div>
        <KeyValueGrid
          items={[
            { label: "Status", value: <AccountStatusBadge status={account.status} /> },
            { label: "Tier", value: enumLabel(account.tier) },
            { label: "Lifecycle stage", value: enumLabel(account.lifecycle_stage) },
            { label: "Owner", value: account.owner_email || "—" },
            { label: "Industry", value: account.industry || "—" },
            { label: "ARR", value: fmtMoney(account.arr, account.currency) },
            { label: "MRR", value: fmtMoney(account.mrr, account.currency) },
            { label: "Contract value", value: fmtMoney(account.contract_value, account.currency) },
            { label: "Renewal date", value: account.renewal_date ? fmtDate(account.renewal_date) : "—" },
            {
              label: "Health",
              value: (
                <span className="flex items-center gap-1.5">
                  <HealthGradeBadge grade={account.health_grade} />
                  {account.health_score != null && <span className="tabular text-fg-muted">{account.health_score}</span>}
                  <HealthTrendBadge trend={account.health_trend} />
                </span>
              ),
            },
            { label: "Created", value: fmtDateTime(account.created_at) },
            {
              label: "Tags",
              value: account.tags.length > 0 ? account.tags.map((t) => <span key={t} className="mr-1 rounded bg-control px-1 text-11">{t}</span>) : "—",
            },
          ]}
        />
        {account.notes && (
          <>
            <div className="mb-1 mt-3 text-13 font-medium text-fg">Notes</div>
            <p className="whitespace-pre-wrap text-12 text-fg-muted">{account.notes}</p>
          </>
        )}
      </div>

      <div className="panel p-3.5">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-13 font-medium text-fg">Contacts ({contacts.data?.length ?? 0})</span>
          <Button size="sm" variant="ghost" onClick={() => setAdding((a) => !a)}><Plus size={13} /> Add</Button>
        </div>
        {adding && (
          <div className="mb-2 space-y-1.5 rounded-md border border-line bg-surface p-2">
            <div className="grid grid-cols-2 gap-1.5">
              <Input value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="First name" />
              <Input value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder="Last name" />
            </div>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
            <div className="flex gap-1.5">
              <Button size="sm" variant="primary" onClick={submitContact} disabled={create.isPending}>Save</Button>
              <Button size="sm" variant="ghost" onClick={() => setAdding(false)}>Cancel</Button>
            </div>
          </div>
        )}
        {contacts.isLoading ? (
          <div className="grid place-items-center py-4"><Spinner size={16} /></div>
        ) : (contacts.data ?? []).length === 0 ? (
          <p className="text-12 text-fg-subtle">No contacts yet.</p>
        ) : (
          <div className="divide-y divide-line">
            {contacts.data!.map((c) => (
              <div key={c.id} className="flex items-center gap-2 py-1.5">
                <div className="min-w-0 flex-1">
                  <div className="truncate text-12 text-fg">{c.first_name} {c.last_name}{c.is_primary && <Badge tone="accent" className="ml-1.5">Primary</Badge>}</div>
                  <div className="truncate text-11 text-fg-subtle">{c.title || enumLabel(c.role)} {c.email && `· ${c.email}`}</div>
                </div>
                <button
                  type="button"
                  aria-label={`Remove ${c.first_name} ${c.last_name}`}
                  title="Remove contact"
                  onClick={() => remove.mutate(c.id, { onError: err })}
                  className="text-fg-subtle hover:text-danger"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function HealthTab({ accountId }: { accountId: number }) {
  const current = useCsHealth(accountId);
  const history = useCsHealthHistory(accountId);
  const { scoreHealth } = useCsAccountMutations();
  const [recording, setRecording] = useState(false);
  const [signals, setSignals] = useState({
    product_adoption: "50", meeting_activity: "50", email_activity: "50",
    opportunity_activity: "50", open_issues: "100", renewal_status: "100", executive_engagement: "50",
  });

  function submitScore() {
    scoreHealth.mutate(
      { accountId, body: Object.fromEntries(Object.entries(signals).map(([k, v]) => [k, Number(v)])) as any },
      {
        onSuccess: () => { toast("Health score recorded", "positive"); setRecording(false); },
        onError: (e) => toast(apiErrorMessage(e), "danger"),
      },
    );
  }

  const labels: Record<string, string> = {
    product_adoption: "Product adoption", meeting_activity: "Meeting activity", email_activity: "Email activity",
    opportunity_activity: "Opportunity activity", open_issues: "Open issues (100 = none)",
    renewal_status: "Renewal status", executive_engagement: "Executive engagement",
  };

  return (
    <div className="space-y-4">
      <div className="panel p-3.5">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-13 font-medium text-fg">Current health</span>
          <Button size="sm" onClick={() => setRecording((r) => !r)}>Record new score</Button>
        </div>
        {recording && (
          <div className="mb-3 space-y-2 rounded-md border border-line bg-surface p-2.5">
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(labels).map(([key, label]) => (
                <label key={key} className="block">
                  <span className="mb-0.5 block text-11 text-fg-subtle">{label}</span>
                  <Input
                    type="number" min="0" max="100"
                    value={signals[key as keyof typeof signals]}
                    onChange={(e) => setSignals((s) => ({ ...s, [key]: e.target.value }))}
                  />
                </label>
              ))}
            </div>
            <Button size="sm" variant="primary" onClick={submitScore} disabled={scoreHealth.isPending}>
              {scoreHealth.isPending ? "Saving…" : "Save score"}
            </Button>
          </div>
        )}
        {current.isLoading ? (
          <div className="grid place-items-center py-4"><Spinner size={16} /></div>
        ) : current.isError || !current.data ? (
          <p className="text-12 text-fg-subtle">No health score recorded yet.</p>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <HealthGradeBadge grade={current.data.grade} />
              <span className="tabular text-18 text-fg">{current.data.score}</span>
              <HealthTrendBadge trend={current.data.trend} />
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-12 sm:grid-cols-3">
              {(["product_adoption", "meeting_activity", "email_activity", "opportunity_activity", "open_issues", "renewal_status", "executive_engagement"] as const).map((k) => (
                <div key={k} className="flex justify-between gap-2">
                  <span className="text-fg-subtle">{labels[k]}</span>
                  <span className="tabular text-fg">{current.data![k]}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="border-b border-line px-3.5 py-2 text-13 font-medium text-fg">History</div>
        {history.isLoading ? (
          <div className="grid place-items-center py-8"><Spinner size={16} /></div>
        ) : (history.data ?? []).length === 0 ? (
          <EmptyState title="No history yet" />
        ) : (
          <div className="divide-y divide-line">
            {history.data!.map((h) => (
              <div key={h.id} className="flex items-center justify-between gap-2 px-3.5 py-2 text-12">
                <span className="flex items-center gap-1.5"><HealthGradeBadge grade={h.grade} /><span className="tabular text-fg">{h.score}</span><HealthTrendBadge trend={h.trend} /></span>
                <span className="text-11 text-fg-subtle">{fmtRelative(h.created_at)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ContractsTab({ accountId }: { accountId: number }) {
  const { data, isLoading, isError, error, refetch } = useCsContracts({ account_id: accountId, limit: 100 });
  const { create, patch, remove } = useCsContractMutations();
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const [endDate, setEndDate] = useState("");
  const err = (e: unknown) => toast(apiErrorMessage(e), "danger");

  function submit() {
    if (!name.trim()) return;
    create.mutate(
      {
        account_id: accountId, name: name.trim(), value: value.trim() ? Number(value) : 0, end_date: endDate ? new Date(endDate).toISOString() : null,
        auto_renew: false, currency: "USD", notes: "", renewal_probability: 0.5, status: "active",
      },
      { onSuccess: () => { toast("Contract added", "positive"); setAdding(false); setName(""); setValue(""); setEndDate(""); }, onError: err },
    );
  }

  return (
    <div className="space-y-3">
      <Button size="sm" onClick={() => setAdding((a) => !a)}><Plus size={13} /> New contract</Button>
      {adding && (
        <div className="panel space-y-2 p-3">
          <div className="grid grid-cols-3 gap-2">
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Contract name" />
            <Input type="number" value={value} onChange={(e) => setValue(e.target.value)} placeholder="Value" />
            <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>
          <div className="flex gap-1.5">
            <Button size="sm" variant="primary" onClick={submit} disabled={create.isPending}>Save</Button>
            <Button size="sm" variant="ghost" onClick={() => setAdding(false)}>Cancel</Button>
          </div>
        </div>
      )}
      <div className="panel">
        {isError ? (
          <ErrorState title="Couldn't load contracts" error={error} onRetry={refetch} />
        ) : isLoading ? (
          <div className="grid place-items-center py-8"><Spinner size={16} /></div>
        ) : (data?.items.length ?? 0) === 0 ? (
          <EmptyState title="No contracts yet" />
        ) : (
          <div className="divide-y divide-line">
            {data!.items.map((c) => (
              <div key={c.id} className="flex flex-wrap items-center gap-3 px-3.5 py-2.5">
                <div className="min-w-0 flex-1">
                  <div className="truncate text-13 text-fg">{c.name}</div>
                  <div className="text-11 text-fg-subtle">{fmtMoney(c.value, c.currency)} · {c.end_date ? `ends ${fmtDate(c.end_date)}` : "no end date"}</div>
                </div>
                <ContractStatusBadge status={c.status} />
                <select
                  value={c.status}
                  onChange={(e) => patch.mutate({ id: c.id, body: { status: e.target.value } }, { onError: err })}
                  className="rounded-md border border-line bg-control px-2 py-1 text-12 text-fg outline-none focus:border-accent"
                >
                  {CS_CONTRACT_STATUSES.map((s) => <option key={s} value={s}>{enumLabel(s)}</option>)}
                </select>
                <button
                  type="button"
                  aria-label={`Delete contract ${c.name}`}
                  title="Delete contract"
                  onClick={() => remove.mutate(c.id, { onError: err })}
                  className="text-fg-subtle hover:text-danger"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MilestonesList({ plan }: { plan: CsSuccessPlanOut }) {
  const milestones = useCsMilestones(plan.id);
  const { create, patch, remove } = useCsMilestoneMutations();
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const err = (e: unknown) => toast(apiErrorMessage(e), "danger");

  function submit() {
    if (!name.trim()) return;
    create.mutate(
      { plan_id: plan.id, account_id: plan.account_id, name: name.trim(), notes: "", status: "pending" },
      { onSuccess: () => { toast("Milestone added", "positive"); setAdding(false); setName(""); }, onError: err },
    );
  }

  return (
    <div className="mt-2 space-y-1.5 border-t border-line pt-2">
      {milestones.isLoading ? (
        <Spinner size={14} />
      ) : (milestones.data ?? []).length === 0 ? (
        <p className="text-11 text-fg-subtle">No milestones yet.</p>
      ) : (
        milestones.data!.map((m) => (
          <div key={m.id} className="flex items-center gap-2 text-12">
            <div className="min-w-0 flex-1 truncate text-fg">{m.name}</div>
            <MilestoneStatusBadge status={m.status} />
            <select
              value={m.status}
              onChange={(e) => patch.mutate({ id: m.id, body: { status: e.target.value } }, { onError: err })}
              className="rounded-md border border-line bg-control px-1.5 py-0.5 text-11 text-fg outline-none focus:border-accent"
            >
              {CS_MILESTONE_STATUSES.map((s) => <option key={s} value={s}>{enumLabel(s)}</option>)}
            </select>
            <button type="button" aria-label={`Delete milestone ${m.name}`} onClick={() => remove.mutate(m.id, { onError: err })} className="text-fg-subtle hover:text-danger">
              <Trash2 size={12} />
            </button>
          </div>
        ))
      )}
      {adding ? (
        <div className="flex gap-1.5">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Milestone name" className="flex-1" />
          <Button size="sm" variant="primary" onClick={submit} disabled={create.isPending}>Add</Button>
          <Button size="sm" variant="ghost" onClick={() => setAdding(false)}>Cancel</Button>
        </div>
      ) : (
        <Button size="sm" variant="ghost" onClick={() => setAdding(true)}><Plus size={12} /> Add milestone</Button>
      )}
    </div>
  );
}

function PlansTab({ accountId }: { accountId: number }) {
  const plans = useCsPlans(accountId);
  const { create, remove } = useCsPlanMutations();
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const err = (e: unknown) => toast(apiErrorMessage(e), "danger");

  function submit() {
    if (!name.trim()) return;
    create.mutate(
      { account_id: accountId, name: name.trim(), goals: [], notes: "", status: "active" },
      { onSuccess: () => { toast("Success plan created", "positive"); setAdding(false); setName(""); }, onError: err },
    );
  }

  return (
    <div className="space-y-3">
      <Button size="sm" onClick={() => setAdding((a) => !a)}><Plus size={13} /> New success plan</Button>
      {adding && (
        <div className="panel flex gap-2 p-3">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Plan name" className="flex-1" />
          <Button size="sm" variant="primary" onClick={submit} disabled={create.isPending}>Save</Button>
          <Button size="sm" variant="ghost" onClick={() => setAdding(false)}>Cancel</Button>
        </div>
      )}
      {plans.isLoading ? (
        <div className="grid place-items-center py-8"><Spinner size={16} /></div>
      ) : (plans.data ?? []).length === 0 ? (
        <div className="panel"><EmptyState title="No success plans yet" description="Create a plan to track goals and milestones for this account." /></div>
      ) : (
        <div className="space-y-3">
          {plans.data!.map((p) => (
            <div key={p.id} className="panel p-3.5">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-13 font-medium text-fg">{p.name}</span>
                <div className="flex items-center gap-2">
                  <Badge tone={p.status === "active" ? "positive" : p.status === "completed" ? "accent" : "neutral"}>{enumLabel(p.status)}</Badge>
                  <button type="button" aria-label={`Delete plan ${p.name}`} onClick={() => remove.mutate(p.id, { onError: err })} className="text-fg-subtle hover:text-danger">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
              {p.due_date && <div className="text-11 text-fg-subtle">Due {fmtDate(p.due_date)}</div>}
              <MilestonesList plan={p} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RisksTab({ accountId }: { accountId: number }) {
  const [statusFilter, setStatusFilter] = useState("");
  const { data, isLoading, isError, error, refetch } = useCsRisks(accountId, statusFilter || undefined);
  const { create, patch, remove } = useCsRiskMutations();
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState("medium");
  const err = (e: unknown) => toast(apiErrorMessage(e), "danger");

  function submit() {
    if (!title.trim()) return;
    create.mutate(
      { account_id: accountId, title: title.trim(), severity, description: "", status: "open" },
      { onSuccess: () => { toast("Risk logged", "positive"); setAdding(false); setTitle(""); }, onError: err },
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Button size="sm" onClick={() => setAdding((a) => !a)}><Plus size={13} /> Log risk</Button>
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          {CS_RISK_STATUSES.map((s) => <option key={s} value={s}>{enumLabel(s)}</option>)}
        </Select>
      </div>
      {adding && (
        <div className="panel space-y-2 p-3">
          <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Risk title" />
          <Select value={severity} onChange={(e) => setSeverity(e.target.value)} className="w-full">
            {CS_RISK_SEVERITIES.map((s) => <option key={s} value={s}>{enumLabel(s)}</option>)}
          </Select>
          <div className="flex gap-1.5">
            <Button size="sm" variant="primary" onClick={submit} disabled={create.isPending}>Save</Button>
            <Button size="sm" variant="ghost" onClick={() => setAdding(false)}>Cancel</Button>
          </div>
        </div>
      )}
      <div className="panel">
        {isError ? (
          <ErrorState title="Couldn't load risks" error={error} onRetry={refetch} />
        ) : isLoading ? (
          <div className="grid place-items-center py-8"><Spinner size={16} /></div>
        ) : (data ?? []).length === 0 ? (
          <EmptyState title="No risks logged" description="Great — nothing tracked against this account." />
        ) : (
          <div className="divide-y divide-line">
            {data!.map((r) => (
              <div key={r.id} className="flex flex-wrap items-center gap-3 px-3.5 py-2.5">
                <div className="min-w-0 flex-1">
                  <div className="truncate text-13 text-fg">{r.title}</div>
                  {r.description && <div className="truncate text-11 text-fg-subtle">{r.description}</div>}
                </div>
                <RiskSeverityBadge severity={r.severity} />
                <RiskStatusBadge status={r.status} />
                <select
                  value={r.status}
                  onChange={(e) => patch.mutate({ id: r.id, body: { status: e.target.value } }, { onError: err })}
                  className="rounded-md border border-line bg-control px-2 py-1 text-12 text-fg outline-none focus:border-accent"
                >
                  {CS_RISK_STATUSES.map((s) => <option key={s} value={s}>{enumLabel(s)}</option>)}
                </select>
                <button type="button" aria-label={`Delete risk ${r.title}`} onClick={() => remove.mutate(r.id, { onError: err })} className="text-fg-subtle hover:text-danger">
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ActivityTab({ accountId }: { accountId: number }) {
  const { data, isLoading, isError, error, refetch } = useCsTimeline(accountId);
  if (isLoading) return <div className="grid place-items-center py-12"><Spinner size={18} /></div>;
  if (isError) return <ErrorState title="Couldn't load activity" error={error} onRetry={refetch} />;
  if (!data || data.length === 0) return <div className="panel"><EmptyState title="No activity yet" /></div>;
  return (
    <div className="panel divide-y divide-line">
      {data.map((e) => (
        <div key={e.event_id} className="flex items-center justify-between gap-2 px-3.5 py-2 text-12">
          <span className="text-fg-muted"><span className="font-medium text-fg">{e.label}</span>{e.detail ? ` — ${e.detail}` : ""}</span>
          <span className="shrink-0 text-11 text-fg-subtle">{fmtRelative(e.timestamp)}</span>
        </div>
      ))}
    </div>
  );
}
