import type { ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, ExternalLink, GitCompare, X } from "lucide-react";

import { GradeBadge } from "@/components/data/GradeBadge";
import { ScoreBar } from "@/components/data/ScoreBar";
import { PageHeader } from "@/components/shell/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Spinner } from "@/components/ui/Spinner";
import { useCompanyProfiles } from "@/lib/api/queries";
import type { CompanyProfile } from "@/lib/api/types";
import { cx } from "@/lib/cx";
import { enumLabel, fmtInt, fmtScore, monogram } from "@/lib/format";

type Metric = {
  label: string;
  /** Numeric value used to highlight the leader (omit for text-only rows). */
  num?: (p: CompanyProfile) => number | null;
  betterLow?: boolean;
  render: (p: CompanyProfile, best: boolean) => ReactNode;
};
type Section = { title: string; rows: Metric[] };

const text = (v: ReactNode) => <span className="text-fg-muted">{v}</span>;
const best = (v: ReactNode) => <span className="font-medium text-accent">{v}</span>;

const SECTIONS: Section[] = [
  {
    title: "Lead score",
    rows: [
      { label: "Grade", render: (p) => <GradeBadge grade={p.lead_score?.grade} /> },
      {
        label: "Lead score",
        num: (p) => p.lead_score?.lead_score ?? null,
        render: (p, b) =>
          p.lead_score ? (b ? best(fmtScore(p.lead_score.lead_score)) : text(fmtScore(p.lead_score.lead_score))) : text("—"),
      },
      {
        label: "Priority rank",
        num: (p) => p.lead_score?.priority_rank ?? null,
        betterLow: true,
        render: (p, b) =>
          p.lead_score?.priority_rank ? (b ? best(`#${p.lead_score.priority_rank}`) : text(`#${p.lead_score.priority_rank}`)) : text("—"),
      },
    ],
  },
  {
    title: "Score components",
    rows: [
      { label: "Opportunity", render: (p) => <ScoreBar value={p.lead_score?.opportunity_subscore} /> },
      { label: "Hiring demand", render: (p) => <ScoreBar value={p.lead_score?.demand_subscore} /> },
      { label: "Readiness", render: (p) => <ScoreBar value={p.lead_score?.readiness_subscore} /> },
      { label: "Decision-makers", render: (p) => <ScoreBar value={p.lead_score?.dm_subscore} /> },
    ],
  },
  {
    title: "Coverage",
    rows: [
      { label: "Opportunities", num: (p) => p.counts.opportunities, render: (p, b) => (b ? best(fmtInt(p.counts.opportunities)) : text(fmtInt(p.counts.opportunities))) },
      { label: "Jobs", num: (p) => p.counts.jobs, render: (p, b) => (b ? best(fmtInt(p.counts.jobs)) : text(fmtInt(p.counts.jobs))) },
      { label: "Demand signal", num: (p) => p.counts.demand_signal, render: (p, b) => (b ? best(p.counts.demand_signal ? "Yes" : "No") : text(p.counts.demand_signal ? "Yes" : "No")) },
      { label: "Decision-makers", num: (p) => p.counts.decision_makers, render: (p, b) => (b ? best(fmtInt(p.counts.decision_makers)) : text(fmtInt(p.counts.decision_makers))) },
    ],
  },
  {
    title: "Profile",
    rows: [
      { label: "Tier", render: (p) => text(enumLabel(p.company.company_tier)) },
      { label: "Prospect type", render: (p) => text(enumLabel(p.company.prospect_type)) },
      { label: "Country", render: (p) => text(p.company.country || "—") },
      { label: "Compliance", render: (p) => text(enumLabel(p.company.compliance_flag)) },
      { label: "Validation", render: (p) => text(enumLabel(p.company.validation_status)) },
    ],
  },
];

/** The leading value(s) for a row, or null when there's nothing to highlight. */
function bestValue(profiles: (CompanyProfile | undefined)[], m: Metric): number | null {
  if (!m.num) return null;
  const vals = profiles.map((p) => (p ? m.num!(p) : null)).filter((v): v is number => v != null);
  if (vals.length < 2 || new Set(vals).size < 2) return null;
  return m.betterLow ? Math.min(...vals) : Math.max(...vals);
}

export function ComparePage() {
  const [params, setParams] = useSearchParams();
  const domains = [...new Set((params.get("domains") ?? "").split(",").map((d) => d.trim()).filter(Boolean))];
  const results = useCompanyProfiles(domains);
  const profiles = results.map((r) => r.data as CompanyProfile | undefined);

  const remove = (domain: string) => {
    const next = domains.filter((d) => d !== domain);
    setParams(next.length ? { domains: next.join(",") } : {}, { replace: true });
  };

  return (
    <>
      <PageHeader
        title="Compare companies"
        subtitle={domains.length ? `${domains.length} pinned ${domains.length === 1 ? "company" : "companies"}` : undefined}
        actions={
          <Link to="/workspace" className="inline-flex items-center gap-1.5 text-12 text-fg-muted hover:text-accent">
            <ArrowLeft size={14} /> Workspace
          </Link>
        }
      />

      <div className="p-4">
        {domains.length === 0 ? (
          <div className="panel">
            <EmptyState
              icon={<GitCompare size={20} />}
              title="Nothing to compare"
              description="Pin companies from a profile or list, then open Compare from your Workspace."
            />
          </div>
        ) : (
          <div className="panel overflow-x-auto">
            <table className="w-full border-collapse text-13">
              <thead>
                <tr>
                  <th className="sticky left-0 z-10 w-40 border-b border-line bg-surface px-3 py-3" />
                  {domains.map((domain, i) => {
                    const p = profiles[i];
                    const loading = results[i]?.isLoading;
                    return (
                      <th key={domain} className="min-w-[180px] border-b border-l border-line bg-surface px-3 py-3 text-left align-top font-normal">
                        <div className="flex items-start gap-2">
                          <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-line bg-control text-11 text-fg-muted">
                            {monogram(p?.company.company_name, domain)}
                          </span>
                          <div className="min-w-0 flex-1">
                            <Link to={`/companies/${encodeURIComponent(domain)}`} className="block truncate text-13 text-fg hover:text-accent">
                              {p?.company.company_name || domain}
                            </Link>
                            <div className="truncate text-11 text-fg-subtle">{domain}</div>
                          </div>
                          <div className="flex shrink-0 items-center gap-1.5">
                            <Link to={`/companies/${encodeURIComponent(domain)}`} className="text-fg-subtle hover:text-accent" title="Open profile">
                              <ExternalLink size={13} />
                            </Link>
                            <button type="button" onClick={() => remove(domain)} className="text-fg-subtle hover:text-danger" title="Remove from compare">
                              <X size={14} />
                            </button>
                          </div>
                        </div>
                        {loading && <div className="mt-1.5"><Spinner size={12} /></div>}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {SECTIONS.map((section) => (
                  <SectionRows
                    key={section.title}
                    section={section}
                    domains={domains}
                    profiles={profiles}
                    loading={results.map((r) => r.isLoading)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {domains.length === 1 && (
          <p className="mt-3 px-1 text-11 text-fg-subtle">Pin another company to compare side by side.</p>
        )}
      </div>
    </>
  );
}

function SectionRows({
  section,
  domains,
  profiles,
  loading,
}: {
  section: Section;
  domains: string[];
  profiles: (CompanyProfile | undefined)[];
  loading: boolean[];
}) {
  return (
    <>
      <tr>
        <td
          colSpan={domains.length + 1}
          className="sticky left-0 bg-base px-3 pb-1.5 pt-4 text-11 font-medium uppercase tracking-wide text-fg-subtle"
        >
          {section.title}
        </td>
      </tr>
      {section.rows.map((m) => {
        const b = bestValue(profiles, m);
        return (
          <tr key={m.label} className="hover:bg-raised">
            <td className="sticky left-0 z-10 w-40 border-t border-line bg-surface px-3 py-2.5 text-12 text-fg-subtle">
              {m.label}
            </td>
            {domains.map((domain, i) => {
              const p = profiles[i];
              const isBest = b != null && m.num != null && p != null && m.num(p) === b;
              return (
                <td key={domain} className={cx("border-l border-t border-line px-3 py-2.5 align-middle")}>
                  {p ? (
                    m.render(p, isBest)
                  ) : loading[i] ? (
                    <Skeleton className="h-3.5 w-16" />
                  ) : (
                    <span className="text-fg-subtle">—</span>
                  )}
                </td>
              );
            })}
          </tr>
        );
      })}
    </>
  );
}
