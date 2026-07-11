import { Fragment } from "react";

import { ConfidenceBadge } from "@/components/data/ConfidenceBadge";
import { GradeBadge } from "@/components/data/GradeBadge";
import { ScoreBar } from "@/components/data/ScoreBar";
import { cx } from "@/lib/cx";
import { enumLabel, fmtInt, fmtScore } from "@/lib/format";
import { gradeVar } from "@/lib/grades";
import type { LeadScoreOut } from "@/lib/api/types";
import { MissingInputsCallout } from "./MissingInputsCallout";
import { MultiplierChip } from "./MultiplierChip";

// Falls back to config/lead_scoring.json defaults if rationale omits weights.
const DEFAULT_WEIGHTS = { opportunity: 0.3, demand: 0.3, readiness: 0.2, decision_maker: 0.2 };

export function ScoreExplanation({ score }: { score: LeadScoreOut }) {
  const r = score.rationale ?? {};
  const weights = { ...DEFAULT_WEIGHTS, ...(r.weights ?? {}) };

  const subs = [
    { label: "Opportunity", value: score.opportunity_subscore, w: weights.opportunity },
    { label: "Demand", value: score.demand_subscore, w: weights.demand },
    { label: "Readiness", value: score.readiness_subscore, w: weights.readiness },
    { label: "Decision makers", value: score.dm_subscore, w: weights.decision_maker },
  ];

  const base = r.weighted_base ?? subs.reduce((a, s) => a + s.value * s.w, 0);
  const combined =
    r.multipliers?.combined ?? score.region_mult * score.prospect_mult * score.tier_mult;

  const inputs = r.inputs ?? {};
  const inputItems: { label: string; value: string }[] = [
    { label: "Opportunities", value: fmtInt(inputs.opportunities) },
    { label: "Engineering jobs", value: fmtInt(inputs.engineering_jobs) },
    { label: "Decision makers", value: fmtInt(inputs.decision_makers) },
    { label: "Senior DMs", value: fmtInt(inputs.senior_decision_makers) },
  ];

  return (
    <div className="space-y-4">
      {/* Weighted subscores */}
      <div className="space-y-2.5">
        {subs.map((s) => (
          <div key={s.label} className="grid grid-cols-[130px_1fr] items-center gap-3">
            <div className="text-12 text-fg-muted">
              {s.label}
              <span className="ml-1 text-fg-subtle">· {Math.round(s.w * 100)}%</span>
            </div>
            <ScoreBar value={s.value} />
          </div>
        ))}
      </div>

      {/* Weighted base */}
      <div className="flex items-center justify-between border-t border-line pt-3 text-12">
        <span className="text-fg-muted">Weighted base</span>
        <span className="tabular text-fg">{fmtScore(base)}</span>
      </div>

      {/* Fit multipliers */}
      <div className="space-y-2">
        <div className="text-11 uppercase tracking-wide text-fg-subtle">Fit multipliers</div>
        <div className="flex flex-wrap items-center gap-1.5">
          <MultiplierChip label="Region" value={score.region_mult} />
          <MultiplierChip label="Prospect" value={score.prospect_mult} />
          <MultiplierChip label="Tier" value={score.tier_mult} />
          <span className="text-fg-subtle">=</span>
          <MultiplierChip label="Combined" value={combined} emphasis />
        </div>
      </div>

      {/* Final */}
      <div
        className="flex items-center justify-between rounded-md border px-3 py-2.5"
        style={{
          borderColor: `color-mix(in srgb, ${gradeVar(score.grade)} 35%, transparent)`,
          background: `color-mix(in srgb, ${gradeVar(score.grade)} 8%, transparent)`,
        }}
      >
        <div>
          <div className="text-11 uppercase tracking-wide text-fg-subtle">Final lead score</div>
          <div className="tabular mt-0.5 text-12 text-fg-subtle">
            {fmtScore(base)} × {combined.toFixed(2)} = {fmtScore(score.lead_score)}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="tabular text-22 leading-none text-fg">{fmtScore(score.lead_score)}</span>
          <GradeBadge grade={score.grade} size="lg" />
        </div>
      </div>

      {/* Confidence — how many of the 3 engine signals backed this score */}
      <div className="flex items-center justify-between text-12">
        <span className="text-fg-muted">
          Confidence
          <span className="ml-1 text-fg-subtle">· {score.coverage} of 3 signals</span>
        </span>
        <ConfidenceBadge confidence={score.confidence} coverage={score.coverage} />
      </div>

      <MissingInputsCallout missing={r.missing_inputs} />

      {/* Signals considered */}
      <div>
        <div className="mb-1.5 text-11 uppercase tracking-wide text-fg-subtle">Signals considered</div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-4">
          {inputItems.map((it) => (
            <Fragment key={it.label}>
              <div className="flex items-baseline justify-between gap-2">
                <dt className="text-12 text-fg-subtle">{it.label}</dt>
                <dd className={cx("tabular text-12 text-fg")}>{it.value}</dd>
              </div>
            </Fragment>
          ))}
        </dl>
        <div className="mt-2 text-11 text-fg-subtle">
          Model {score.model_version}
          {inputs.company_tier ? ` · ${enumLabel(inputs.company_tier)}` : ""}
          {inputs.prospect_type ? ` · ${enumLabel(inputs.prospect_type)}` : ""}
        </div>
      </div>
    </div>
  );
}
