import { useState } from "react";
import { History } from "lucide-react";

import { GradeBadge } from "@/components/data/GradeBadge";
import { HumanStatusBadge } from "@/components/data/HumanStatusBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useSetLeadReview } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/store";
import type { CompanyProfile } from "@/lib/api/types";
import { fmtRelative, fmtScore } from "@/lib/format";
import {
  REVIEW_STATUSES, REVIEW_STATUS_META, SCORE_AFFECTING_STATUSES, reviewStatusLabel,
} from "@/lib/reviewStatus";

/**
 * The Human Review & Assessment panel (P-task viii + reconciled Change_05). Shows
 * the MODEL verdict and (when enabled) the SEPARATE ADJUSTED verdict + the HUMAN
 * assessment — the model score is never overwritten. Score-affecting statuses
 * require a reason + manager/admin (the backend enforces this); reviews can carry
 * an optional expiry, after which the score effect lapses.
 */
export function LeadReviewPanel({ profile }: { profile: CompanyProfile }) {
  const domain = profile.company.company_domain;
  const review = profile.lead_review;
  const history = profile.lead_review_history;
  const ls = profile.lead_score;
  const enabled = profile.review_feedback_enabled;
  const { isManager } = useAuth();
  const set = useSetLeadReview(domain);

  const [status, setStatus] = useState<string>(review?.review_status ?? "needs_review");
  const [notes, setNotes] = useState<string>(review?.human_notes ?? "");
  const [expiry, setExpiry] = useState<string>(review?.expires_at ? review.expires_at.slice(0, 10) : "");
  const [editing, setEditing] = useState<boolean>(!review);

  const modelScore = ls?.lead_score ?? null;
  const modelGrade = ls?.grade ?? null;
  const adjGrade = ls?.adjusted_grade || ls?.grade || null;
  const adjScore = ls?.adjusted_score ?? ls?.lead_score ?? null;
  const adjustment = ls?.rationale?.adjustment;
  const adjustedDiffers = Boolean(ls && (adjGrade !== modelGrade || adjScore !== modelScore));
  const expired = Boolean(review?.expires_at && new Date(review.expires_at).getTime() < Date.now());

  const scoreAffecting = enabled && SCORE_AFFECTING_STATUSES.has(status);
  const reasonMissing = scoreAffecting && !notes.trim();
  const blockedByRole = scoreAffecting && !isManager;
  const dirty =
    status !== (review?.review_status ?? "needs_review") ||
    notes !== (review?.human_notes ?? "") ||
    expiry !== (review?.expires_at ? review.expires_at.slice(0, 10) : "");

  function save() {
    set.mutate(
      {
        review_status: status,
        human_notes: notes.trim(),
        expires_at: expiry ? new Date(expiry + "T00:00:00Z").toISOString() : null,
      },
      { onSuccess: () => setEditing(false) },
    );
  }

  return (
    <div className="space-y-4">
      {/* Model vs Adjusted vs Human — model is never overwritten */}
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-md border border-line bg-base p-3">
          <div className="text-11 uppercase tracking-wide text-fg-subtle">Model</div>
          <div className="mt-1.5 flex items-center gap-2">
            <GradeBadge grade={modelGrade} size="md" />
            <span className="tabular text-15 text-fg">{ls ? fmtScore(modelScore) : "—"}</span>
          </div>
          <div className="mt-1 text-11 text-fg-subtle">The intelligence model — never changed by a review.</div>
        </div>
        <div className="rounded-md border border-line bg-base p-3">
          <div className="text-11 uppercase tracking-wide text-fg-subtle">Adjusted</div>
          <div className="mt-1.5 flex items-center gap-2">
            <GradeBadge grade={adjGrade} size="md" />
            <span className="tabular text-15 text-fg">{ls ? fmtScore(adjScore) : "—"}</span>
          </div>
          <div className="mt-1 text-11 text-fg-subtle">
            {!enabled
              ? "Review→score off — equals the model."
              : expired
                ? "Review expired — effect lapsed."
                : adjustedDiffers && adjustment
                  ? `Human override: ${adjustment.boost ? `×${adjustment.boost} boost` : ""}${adjustment.penalty ? `×${adjustment.penalty} penalty` : ""}${adjustment.floor_grade ? ` · floor ${adjustment.floor_grade}` : ""}`.trim()
                  : "No override — equals the model."}
          </div>
        </div>
        <div className="rounded-md border border-line bg-base p-3">
          <div className="flex items-center gap-1.5 text-11 uppercase tracking-wide text-fg-subtle">
            Human Assessment
            {expired ? <Badge tone="warning">expired</Badge> : null}
          </div>
          <div className="mt-1.5">
            <HumanStatusBadge status={review?.review_status} />
          </div>
          {review?.human_notes ? (
            <p className="mt-1.5 whitespace-pre-wrap text-12 text-fg-muted">{review.human_notes}</p>
          ) : (
            <div className="mt-1 text-11 text-fg-subtle">No human assessment yet.</div>
          )}
          {review ? (
            <div className="mt-1.5 text-11 text-fg-subtle">
              by {review.reviewed_by_email || "—"} · {fmtRelative(review.reviewed_at || review.updated_at)}
              {review.expires_at ? ` · expires ${review.expires_at.slice(0, 10)}` : ""}
            </div>
          ) : null}
        </div>
      </div>

      {/* Editor */}
      {editing ? (
        <div className="rounded-md border border-line bg-base p-3">
          <div className="mb-2 text-12 font-medium text-fg">Set human assessment</div>
          <div className="flex flex-wrap gap-1.5">
            {REVIEW_STATUSES.map((s) => {
              const affects = enabled && SCORE_AFFECTING_STATUSES.has(s);
              const locked = affects && !isManager;
              return (
                <button
                  key={s}
                  type="button"
                  disabled={locked}
                  onClick={() => setStatus(s)}
                  title={locked ? "Manager/admin only (affects the score)" : REVIEW_STATUS_META[s].hint}
                  className={
                    "rounded-sm border px-2 py-1 text-12 transition-colors disabled:opacity-40 disabled:cursor-not-allowed " +
                    (status === s
                      ? "border-accent bg-accent-weak text-accent"
                      : "border-line bg-control text-fg-muted hover:text-fg")
                  }
                >
                  {reviewStatusLabel(s)}
                  {affects ? <span className="ml-1 text-fg-subtle">▲</span> : null}
                </button>
              );
            })}
          </div>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder={
              scoreAffecting
                ? "Reason (required for a score-affecting status)…"
                : "Reason (optional)…"
            }
            className="mt-2 w-full resize-none rounded-md border border-line bg-control px-2.5 py-1.5 text-12 text-fg outline-none focus:border-accent"
          />
          {enabled ? (
            <label className="mt-2 flex items-center gap-2 text-11 text-fg-subtle">
              Expires
              <input
                type="date"
                value={expiry}
                onChange={(e) => setExpiry(e.target.value)}
                className="rounded-sm border border-line bg-control px-1.5 py-1 text-12 text-fg outline-none focus:border-accent"
              />
              <span>(optional — the score effect lapses after this date)</span>
            </label>
          ) : null}
          <div className="mt-2 flex items-center gap-2">
            <Button
              size="sm"
              variant="primary"
              onClick={save}
              disabled={!dirty || reasonMissing || blockedByRole || set.isPending}
            >
              {set.isPending ? "Saving…" : "Save assessment"}
            </Button>
            {review ? (
              <Button size="sm" variant="ghost" onClick={() => setEditing(false)} disabled={set.isPending}>
                Cancel
              </Button>
            ) : null}
            {blockedByRole ? <span className="text-11 text-warning">Manager/admin only.</span> : null}
            {reasonMissing && !blockedByRole ? (
              <span className="text-11 text-fg-subtle">A reason is required.</span>
            ) : null}
            {set.isError ? <span className="text-11 text-danger">Couldn't save — check the reason / your role.</span> : null}
          </div>
          <p className="mt-2 text-11 text-fg-subtle">
            {enabled
              ? "Recorded as auditable feedback. Score-affecting statuses adjust a SEPARATE score — the model score is never changed."
              : "Recorded as feedback — it complements the model and never modifies the score."}
          </p>
        </div>
      ) : (
        <Button size="sm" onClick={() => setEditing(true)}>
          Update assessment
        </Button>
      )}

      {/* Audit trail */}
      {history.length > 0 ? (
        <div>
          <div className="mb-1.5 flex items-center gap-1.5 text-12 font-medium text-fg">
            <History size={13} className="text-fg-subtle" />
            Review history
          </div>
          <ol className="space-y-1.5">
            {history.map((e) => (
              <li key={e.id} className="flex items-start gap-2 text-12">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-1.5">
                    {e.from_status ? <HumanStatusBadge status={e.from_status} /> : null}
                    {e.from_status ? <span className="text-fg-subtle">→</span> : null}
                    <HumanStatusBadge status={e.to_status} />
                    <span className="text-11 text-fg-subtle">
                      · model {e.model_grade || "—"} ({fmtScore(e.model_score)})
                      {e.adjusted_grade && e.adjusted_grade !== e.model_grade
                        ? ` → adjusted ${e.adjusted_grade} (${fmtScore(e.adjusted_score)})`
                        : ""}
                    </span>
                  </div>
                  {e.notes ? <p className="mt-0.5 whitespace-pre-wrap text-fg-muted">{e.notes}</p> : null}
                  <div className="text-11 text-fg-subtle">
                    {e.actor_email || "system"} · {fmtRelative(e.created_at)}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </div>
  );
}
