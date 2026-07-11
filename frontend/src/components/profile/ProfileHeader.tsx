import { Download, ExternalLink } from "lucide-react";

import { GradeBadge } from "@/components/data/GradeBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { toast } from "@/components/ui/Toast";
import { FollowUpButton, PinButton, WatchButton } from "@/components/workspace/WorkspaceButtons";
import { domainHref, enumLabel, fmtInt, fmtScore, monogram } from "@/lib/format";
import type { CompanyProfile } from "@/lib/api/types";

type Tone = "positive" | "warning" | "danger" | "neutral";

function complianceTone(flag: string): Tone {
  const f = flag.toUpperCase();
  if (f.includes("APPROVED")) return "positive";
  if (f.includes("EXCLUD")) return "danger";
  if (f.includes("REVIEW")) return "warning";
  return "neutral";
}

export function ProfileHeader({ profile }: { profile: CompanyProfile }) {
  const { company, lead_score } = profile;
  const domain = company.company_domain;
  const href = domainHref(company.website || domain);

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(profile, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${domain}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast("Exported profile JSON", "positive");
  };

  return (
    <div className="bg-base px-4 py-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <div className="grid h-12 w-12 shrink-0 place-items-center rounded-md border border-line bg-surface text-18 text-fg-muted">
            {monogram(company.company_name, domain)}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="truncate text-22 text-fg">{company.company_name || domain}</h1>
              {company.is_stub && <Badge tone="warning">Stub</Badge>}
            </div>
            <div className="mt-0.5 text-12 text-fg-muted">
              {href ? (
                <a
                  href={href}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 hover:text-accent"
                >
                  {domain}
                  <ExternalLink size={12} />
                </a>
              ) : (
                <span>{domain}</span>
              )}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              {company.company_tier && <Badge>{enumLabel(company.company_tier)}</Badge>}
              {company.prospect_type && <Badge>{enumLabel(company.prospect_type)}</Badge>}
              {company.compliance_flag && (
                <Badge tone={complianceTone(company.compliance_flag)}>
                  {enumLabel(company.compliance_flag)}
                  {company.country ? ` · ${company.country}` : ""}
                </Badge>
              )}
              {company.validation_status && (
                <Badge tone={company.validation_status === "VALID" ? "neutral" : "warning"}>
                  {enumLabel(company.validation_status)}
                </Badge>
              )}
            </div>
          </div>
        </div>

        {lead_score ? (
          <div className="flex items-center gap-3 rounded-md border border-line bg-surface px-3 py-2">
            <GradeBadge grade={lead_score.grade} size="lg" />
            <div>
              <div className="tabular text-22 leading-none text-fg">
                {fmtScore(lead_score.lead_score)}
              </div>
              <div className="mt-1 text-11 text-fg-subtle">
                Priority rank #{fmtInt(lead_score.priority_rank)}
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-md border border-line bg-surface px-3 py-2 text-12 text-fg-subtle">
            Not scored yet
          </div>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <WatchButton domain={domain} />
        <PinButton domain={domain} />
        <FollowUpButton domain={domain} />
        <Button variant="ghost" onClick={exportJson}>
          <Download size={14} />
          Export
        </Button>
      </div>
    </div>
  );
}
