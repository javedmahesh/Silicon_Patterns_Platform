import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { UserCog } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { useDebounce } from "@/hooks/useDebounce";
import { useCompanies, useDmIntelligenceRun, useRunDmIntelligence } from "@/lib/api/queries";
import type { DmIntelligenceJobOut } from "@/lib/api/types";
import { fmtDateTime, fmtInt } from "@/lib/format";

type Selected = { company_domain: string; company_name: string; requested_count: number };

const MIN_COUNT = 1;
const MAX_COUNT = 500;

type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";
const STATUS_TONE: Record<string, Tone> = {
  queued: "neutral", running: "accent", completed: "positive", partial: "warning", failed: "danger",
};
const TERMINAL = ["completed", "partial", "failed"];

function fmtMs(ms?: number | null): string {
  if (!ms || ms < 0) return "—";
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${Math.round(s - m * 60)}s`;
}

/** Modal action on the Decision Makers page: pick companies + per-company counts,
 *  run the (paid) Apify Decision Maker engine, and watch live per-company progress. */
export function RunDmIntelligenceModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [jobId, setJobId] = useState<number | null>(null);
  const close = () => {
    setJobId(null);
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={close}
      width="max-w-2xl"
      title={
        <span className="flex items-center gap-2">
          <UserCog size={15} /> Run Decision Maker Intelligence
        </span>
      }
    >
      {jobId == null ? (
        <SetupView onStarted={setJobId} onCancel={close} />
      ) : (
        <ProgressView jobId={jobId} onClose={close} onRunAnother={() => setJobId(null)} />
      )}
    </Modal>
  );
}

function SetupView({ onStarted, onCancel }: { onStarted: (id: number) => void; onCancel: () => void }) {
  const [selected, setSelected] = useState<Selected[]>([]);
  const [term, setTerm] = useState("");
  const dq = useDebounce(term, 250);
  const enabled = dq.trim().length >= 2;
  const { data } = useCompanies({ q: enabled ? dq.trim() : undefined, page_size: 8 });
  const run = useRunDmIntelligence();

  const chosen = new Set(selected.map((s) => s.company_domain));
  const results = enabled ? (data?.items ?? []).filter((c) => !chosen.has(c.company_domain)) : [];

  const add = (company_domain: string, company_name: string) => {
    setSelected((prev) => [...prev, { company_domain, company_name: company_name || company_domain, requested_count: 25 }]);
    setTerm("");
  };
  const remove = (domain: string) => setSelected((prev) => prev.filter((s) => s.company_domain !== domain));
  const setCount = (domain: string, n: number) =>
    setSelected((prev) => prev.map((s) => (s.company_domain === domain ? { ...s, requested_count: n } : s)));

  const totalLeads = selected.reduce((n, s) => n + (s.requested_count || 0), 0);

  const submit = () =>
    run.mutate(
      { items: selected.map((s) => ({ company_domain: s.company_domain, requested_count: s.requested_count })) },
      { onSuccess: (job: DmIntelligenceJobOut) => onStarted(job.id) },
    );

  return (
    <div className="space-y-4">
      <p className="text-12 text-fg-subtle">
        Pick one or more companies and set how many decision makers to fetch for each. This runs the
        paid Apify engine on demand — it isn’t part of the scheduled pipeline.
      </p>

      {/* Searchable, multi-select company picker */}
      <div className="relative">
        <Input
          value={term}
          placeholder="Search companies to add…"
          onChange={(e) => setTerm(e.target.value)}
        />
        {results.length > 0 && (
          <div className="panel absolute z-20 mt-1 max-h-56 w-full overflow-y-auto p-1">
            {results.map((c) => (
              <button
                key={c.company_domain}
                type="button"
                onClick={() => add(c.company_domain, c.company_name)}
                className="flex w-full items-center justify-between gap-2 rounded-sm px-2 py-1 text-left hover:bg-raised"
              >
                <span className="truncate text-12 text-fg">{c.company_name || c.company_domain}</span>
                <span className="shrink-0 text-11 text-fg-subtle">{c.company_domain}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Selected companies with per-company counts */}
      {selected.length === 0 ? (
        <div className="rounded-md border border-dashed border-line px-3 py-6 text-center text-12 text-fg-subtle">
          No companies selected yet. Search above to add companies.
        </div>
      ) : (
        <div className="overflow-hidden rounded-md border border-line">
          <div className="flex items-center justify-between bg-raised px-3 py-1.5 text-11 uppercase tracking-wide text-fg-subtle">
            <span>{fmtInt(selected.length)} companies</span>
            <span>Decision makers each</span>
          </div>
          <div className="max-h-64 divide-y divide-line/60 overflow-y-auto">
            {selected.map((s) => (
              <div key={s.company_domain} className="flex items-center gap-3 px-3 py-2">
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-13 text-fg">{s.company_name || s.company_domain}</span>
                  <span className="block truncate text-11 text-fg-subtle">{s.company_domain}</span>
                </span>
                {/* Fixed-width wrapper: the Input component hardcodes w-full (cx doesn't
                    tailwind-merge), so constrain it here rather than via className. */}
                <div className="w-20 shrink-0">
                  <Input
                    type="number"
                    min={MIN_COUNT}
                    max={MAX_COUNT}
                    value={s.requested_count}
                    onChange={(e) =>
                      setCount(s.company_domain, Math.max(MIN_COUNT, Math.min(MAX_COUNT, Number(e.target.value) || MIN_COUNT)))
                    }
                    className="text-right"
                    aria-label={`Decision makers for ${s.company_name || s.company_domain}`}
                  />
                </div>
                <Button size="sm" variant="ghost" className="shrink-0" onClick={() => remove(s.company_domain)}>
                  Remove
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {run.isError && (
        <p className="text-12 text-danger">
          {(run.error as { message?: string })?.message || "Couldn’t start the run."}
        </p>
      )}

      <div className="flex items-center justify-between gap-2 border-t border-line pt-3">
        <span className="text-11 text-fg-subtle">
          {selected.length > 0 && `≈ ${fmtInt(totalLeads)} leads requested`}
        </span>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={onCancel}>Cancel</Button>
          <Button
            variant="primary"
            onClick={submit}
            disabled={selected.length === 0 || run.isPending}
          >
            {run.isPending ? <Spinner size={13} /> : null}
            Run intelligence
          </Button>
        </div>
      </div>
    </div>
  );
}

function ProgressView({
  jobId,
  onClose,
  onRunAnother,
}: {
  jobId: number;
  onClose: () => void;
  onRunAnother: () => void;
}) {
  const { data: job, isLoading } = useDmIntelligenceRun(jobId);
  const qc = useQueryClient();
  const terminal = Boolean(job && TERMINAL.includes(job.status));

  // When the run finishes, refresh only the Decision Makers directory queries (not
  // the poll query) so the table reflects newly-found people without a page reload.
  useEffect(() => {
    if (!terminal) return;
    qc.invalidateQueries({
      predicate: (q) =>
        Array.isArray(q.queryKey) &&
        q.queryKey[0] === "decision-makers" &&
        q.queryKey[1] !== "intelligence-run" &&
        q.queryKey[1] !== "intelligence-runs",
    });
  }, [terminal, qc]);

  if (isLoading || !job) {
    return (
      <div className="flex items-center gap-2 py-8 text-12 text-fg-subtle">
        <Spinner size={14} /> Starting run…
      </div>
    );
  }

  const items = job.items ?? [];
  const counts = items.reduce<Record<string, number>>((acc, it) => {
    acc[it.status] = (acc[it.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Badge tone={STATUS_TONE[job.status] ?? "neutral"}>{job.status}</Badge>
          {!terminal && <Spinner size={13} />}
          <span className="text-12 text-fg-muted">
            {fmtInt((counts.completed ?? 0) + (counts.failed ?? 0))} / {fmtInt(items.length)} companies
          </span>
        </div>
        <span className="text-12 text-fg-subtle">
          {fmtInt(job.total_found)} found · {fmtInt(job.total_requested)} requested
          {job.duration_ms ? ` · ${fmtMs(job.duration_ms)}` : ""}
        </span>
      </div>

      {/* Queued / Running / Completed / Failed summary */}
      <div className="flex flex-wrap gap-1.5">
        {(["queued", "running", "completed", "failed"] as const).map((st) => (
          <Badge key={st} tone={STATUS_TONE[st]}>
            {st}: {fmtInt(counts[st] ?? 0)}
          </Badge>
        ))}
      </div>

      <div className="overflow-x-auto rounded-md border border-line">
        <table className="w-full text-12">
          <thead>
            <tr className="bg-raised text-11 uppercase tracking-wide text-fg-subtle">
              <th className="px-2.5 py-1.5 text-left font-medium">Company</th>
              <th className="px-2.5 py-1.5 text-right font-medium">Req.</th>
              <th className="px-2.5 py-1.5 text-left font-medium">Status</th>
              <th className="px-2.5 py-1.5 text-right font-medium">Found</th>
              <th className="hidden px-2.5 py-1.5 text-right font-medium sm:table-cell">Duration</th>
              <th className="hidden px-2.5 py-1.5 text-left font-medium md:table-cell">Started</th>
              <th className="hidden px-2.5 py-1.5 text-left font-medium md:table-cell">Finished</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/60">
            {items.map((it) => (
              <tr key={it.id}>
                <td className="max-w-[200px] px-2.5 py-1.5">
                  <span className="block truncate text-fg">{it.company_name || it.company_domain}</span>
                  {it.error && <span className="block truncate text-11 text-danger" title={it.error}>{it.error}</span>}
                </td>
                <td className="px-2.5 py-1.5 text-right tabular text-fg-muted">{fmtInt(it.requested_count)}</td>
                <td className="px-2.5 py-1.5">
                  <Badge tone={STATUS_TONE[it.status] ?? "neutral"}>{it.status}</Badge>
                </td>
                <td className="px-2.5 py-1.5 text-right tabular text-fg-muted">
                  {it.status === "completed" ? fmtInt(it.records_found) : "—"}
                </td>
                <td className="hidden px-2.5 py-1.5 text-right tabular text-fg-subtle sm:table-cell">
                  {fmtMs(it.duration_ms)}
                </td>
                <td className="hidden px-2.5 py-1.5 text-fg-subtle md:table-cell">
                  {it.started_at ? fmtDateTime(it.started_at) : "—"}
                </td>
                <td className="hidden px-2.5 py-1.5 text-fg-subtle md:table-cell">
                  {it.finished_at ? fmtDateTime(it.finished_at) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {job.error && <p className="text-12 text-danger">{job.error}</p>}

      <div className="flex items-center justify-between gap-2 border-t border-line pt-3">
        <span className="text-11 text-fg-subtle">
          {terminal ? "Run complete — the directory has been refreshed." : "Running… you can close this and it keeps going."}
        </span>
        <div className="flex gap-2">
          {terminal && <Button variant="ghost" onClick={onRunAnother}>Run another</Button>}
          <Button variant={terminal ? "primary" : "default"} onClick={onClose}>
            {terminal ? "Done" : "Close"}
          </Button>
        </div>
      </div>
    </div>
  );
}
