import { useState, type ReactNode } from "react";
import { ExternalLink, Pencil } from "lucide-react";

import { NumericCell } from "@/components/data/NumericCell";
import { Badge } from "@/components/ui/Badge";
import { EditRecordModal, type EditField } from "@/components/ui/EditRecordModal";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import { useDeleteDecisionMaker, useUpdateDecisionMaker } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/store";
import { cleanLocation, enumLabel, fmtScore, fullName } from "@/lib/format";
import type { DecisionMakerOut } from "@/lib/api/types";

const DM_FIELDS: EditField[] = [
  { name: "first_name", label: "First name" },
  { name: "last_name", label: "Last name" },
  { name: "full_name", label: "Full name" },
  { name: "current_title", label: "Title" },
  { name: "seniority", label: "Seniority" },
  { name: "functional_area", label: "Function" },
  { name: "work_email", label: "Work email" },
  { name: "work_phone", label: "Work phone" },
  { name: "city", label: "City" },
  { name: "state_region", label: "State / Region" },
  { name: "country", label: "Country" },
  { name: "location", label: "Location" },
  { name: "headline", label: "Headline", full: true },
  { name: "organization_website", label: "Org website" },
  { name: "organization_linkedin", label: "Org LinkedIn" },
];

/** Admin-only inline edit + delete for one decision maker (self-contained so it works
 *  on every surface that renders a DM row). Renders nothing for non-admins. */
function DmAdminActions({ dm }: { dm: DecisionMakerOut }) {
  const { isAdmin } = useAuth();
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const upd = useUpdateDecisionMaker();
  const del = useDeleteDecisionMaker();
  if (!isAdmin) return null;

  const save = (patch: Record<string, string>) => {
    if (Object.keys(patch).length === 0) return setEditing(false);
    upd.mutate(
      { id: dm.id, body: patch },
      {
        onSuccess: () => { setEditing(false); toast("Decision maker updated", "positive"); },
        onError: (e) => toast(apiErrorMessage(e), "danger"),
      },
    );
  };
  const remove = () =>
    del.mutate(dm.id, {
      onSuccess: () => toast("Decision maker deleted", "positive"),
      onError: (e) => { setConfirming(false); toast(apiErrorMessage(e), "danger"); },
    });

  return (
    <>
      {confirming ? (
        <span className="inline-flex shrink-0 items-center gap-1.5 text-11">
          <button type="button" onClick={remove} className="text-danger hover:underline">Confirm</button>
          <button type="button" onClick={() => setConfirming(false)} className="text-fg-subtle hover:underline">
            Cancel
          </button>
        </span>
      ) : (
        <span className="inline-flex shrink-0 items-center gap-2">
          <button type="button" onClick={() => setEditing(true)}
                  className="text-fg-subtle hover:text-accent" title="Edit decision maker (admin)">
            <Pencil size={13} />
          </button>
          <button type="button" onClick={() => setConfirming(true)}
                  className="text-11 text-fg-subtle hover:text-danger" title="Delete decision maker (admin)">
            Delete
          </button>
        </span>
      )}
      {editing && (
        <EditRecordModal
          open
          onClose={() => setEditing(false)}
          title={`Edit ${fullName(dm.first_name, dm.last_name)}`}
          icon={<Pencil size={15} />}
          fields={DM_FIELDS}
          initial={dm as unknown as Record<string, unknown>}
          pending={upd.isPending}
          error={upd.isError ? upd.error : undefined}
          onSubmit={save}
        />
      )}
    </>
  );
}

export function DecisionMakerRow({
  dm,
  showScore = true,
  action,
}: {
  dm: DecisionMakerOut;
  showScore?: boolean;
  /** Optional trailing slot (e.g. a Contact button) rendered after the LinkedIn link. */
  action?: ReactNode;
}) {
  const initials =
    `${dm.first_name?.[0] ?? ""}${dm.last_name?.[0] ?? ""}`.toUpperCase() || "?";
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-control text-12 text-fg-muted">
        {initials}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="truncate text-13 text-fg">{fullName(dm.first_name, dm.last_name)}</span>
          {dm.seniority && <Badge>{enumLabel(dm.seniority)}</Badge>}
          {dm.influence_score != null && <Badge tone="accent">Infl {dm.influence_score}</Badge>}
          {dm.confidence_level && (
            <Badge tone={dm.confidence_level === "High" ? "positive" : dm.confidence_level === "Medium" ? "accent" : "neutral"}>
              {dm.confidence_level}
            </Badge>
          )}
        </div>
        <div className="truncate text-12 text-fg-subtle">
          {dm.current_title || dm.headline || "—"}
          {dm.department_class ? ` · ${dm.department_class}` : ""}
          {cleanLocation(dm.location) ? ` · ${cleanLocation(dm.location)}` : ""}
        </div>
      </div>
      {showScore && dm.match_score > 0 && (
        <div className="shrink-0 text-right">
          <div className="text-11 text-fg-subtle">Match</div>
          <NumericCell className="text-12 text-fg">{fmtScore(dm.match_score, 0)}</NumericCell>
        </div>
      )}
      {dm.linkedin_url && (
        <a
          href={dm.linkedin_url}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 text-fg-subtle hover:text-accent"
          title="Open LinkedIn profile"
        >
          <ExternalLink size={15} />
        </a>
      )}
      {action}
      <DmAdminActions dm={dm} />
    </div>
  );
}
