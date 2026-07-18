import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Download, ExternalLink, Pencil, Trash2 } from "lucide-react";

import { GradeBadge } from "@/components/data/GradeBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EditRecordModal, type EditField } from "@/components/ui/EditRecordModal";
import { toast } from "@/components/ui/Toast";
import { FollowUpButton, PinButton, WatchButton } from "@/components/workspace/WorkspaceButtons";
import { apiErrorMessage } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/store";
import { useDeleteCompany, useUpdateCompany } from "@/lib/api/queries";
import { COMPANY_TIERS, COMPLIANCE_FLAGS, PROSPECT_TYPES } from "@/lib/enums";
import { domainHref, enumLabel, fmtInt, fmtScore, monogram } from "@/lib/format";
import type { CompanyProfile } from "@/lib/api/types";

type Tone = "positive" | "warning" | "danger" | "neutral";

const COMPANY_FIELDS: EditField[] = [
  { name: "company_name", label: "Company name" },
  { name: "website", label: "Website" },
  { name: "country", label: "Country" },
  { name: "city", label: "City" },
  { name: "headquarters", label: "Headquarters" },
  { name: "industry_category", label: "Industry" },
  { name: "sub_category", label: "Sub-category" },
  { name: "technology_focus", label: "Technology focus" },
  { name: "company_type", label: "Company type" },
  { name: "founded_year", label: "Founded year" },
  { name: "company_tier", label: "Tier", kind: "select", options: COMPANY_TIERS },
  { name: "prospect_type", label: "Prospect type", kind: "select", options: PROSPECT_TYPES },
  { name: "compliance_flag", label: "Compliance", kind: "select", options: COMPLIANCE_FLAGS },
  { name: "company_linkedin", label: "Company LinkedIn", full: true },
  { name: "description", label: "Description", kind: "textarea" },
];

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
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);
  const update = useUpdateCompany();
  const del = useDeleteCompany();

  const saveEdit = (patch: Record<string, string>) => {
    if (Object.keys(patch).length === 0) return setEditing(false);
    update.mutate(
      { domain, body: patch },
      {
        onSuccess: () => { setEditing(false); toast("Company updated", "positive"); },
        onError: (e) => toast(apiErrorMessage(e), "danger"),
      },
    );
  };
  const doDelete = () =>
    del.mutate(domain, {
      onSuccess: () => { toast("Company deleted", "positive"); navigate("/companies"); },
      onError: (e) => { setConfirmDel(false); toast(apiErrorMessage(e), "danger"); },
    });

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
        {isAdmin && (
          <>
            <Button variant="ghost" onClick={() => setEditing(true)}>
              <Pencil size={14} /> Edit
            </Button>
            {confirmDel ? (
              <span className="inline-flex items-center gap-1.5 text-12">
                <span className="text-fg-subtle">Delete company + all its data?</span>
                <button type="button" onClick={doDelete} disabled={del.isPending}
                        className="text-danger hover:underline">Confirm</button>
                <button type="button" onClick={() => setConfirmDel(false)}
                        className="text-fg-subtle hover:underline">Cancel</button>
              </span>
            ) : (
              <Button variant="ghost" onClick={() => setConfirmDel(true)}
                      className="text-danger hover:text-danger">
                <Trash2 size={14} /> Delete
              </Button>
            )}
          </>
        )}
      </div>

      {editing && (
        <EditRecordModal
          open
          onClose={() => setEditing(false)}
          title={`Edit ${company.company_name || domain}`}
          icon={<Pencil size={15} />}
          fields={COMPANY_FIELDS}
          initial={company as unknown as Record<string, unknown>}
          pending={update.isPending}
          error={update.isError ? update.error : undefined}
          onSubmit={saveEdit}
        />
      )}
    </div>
  );
}
