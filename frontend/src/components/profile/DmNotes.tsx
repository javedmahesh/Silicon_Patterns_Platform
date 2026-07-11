import { useState } from "react";
import { Briefcase, Check, Lock, Pencil, ShieldCheck, Trash2, Users, X } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import {
  useCreateDmNote,
  useDeleteDmNote,
  useDmNotes,
  useUpdateDmNote,
} from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/store";
import { fmtRelative } from "@/lib/format";
import type { DecisionMakerNoteOut } from "@/lib/api/types";

type NoteType = "admin" | "manager" | "team" | "personal";

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  manager: "Manager",
  member: "Employee",
};

/** Ordered tier config — also the display order: admin → manager → team → personal. */
const TIERS: {
  type: NoteType;
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  cardClass: string;
  pinned?: boolean;
}[] = [
  {
    type: "admin",
    title: "Admin Notes",
    subtitle: "visible to everyone",
    icon: <ShieldCheck size={13} />,
    cardClass: "border-accent/50 bg-accent/10",
    pinned: true,
  },
  {
    type: "manager",
    title: "Manager Notes",
    subtitle: "visible to everyone",
    icon: <Briefcase size={13} />,
    cardClass: "border-accent/30 bg-accent/5",
  },
  {
    type: "team",
    title: "Team Notes",
    subtitle: "shared with everyone",
    icon: <Users size={13} />,
    cardClass: "border-line bg-surface",
  },
  {
    type: "personal",
    title: "My Notes",
    subtitle: "private to you",
    icon: <Lock size={13} />,
    cardClass: "border-line bg-surface",
  },
];

function RoleChip({ role }: { role?: string | null }) {
  const label = role ? ROLE_LABEL[role] ?? role : "";
  if (!label) return null;
  return (
    <Badge tone={role === "admin" ? "accent" : "neutral"}>{label}</Badge>
  );
}

/** One note: author + role + timestamp, with inline edit + two-click delete (when `can_edit`). */
function NoteItem({ dmId, note }: { dmId: number; note: DecisionMakerNoteOut }) {
  const update = useUpdateDmNote(dmId);
  const del = useDeleteDmNote(dmId);
  const [editing, setEditing] = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);
  const [draft, setDraft] = useState(note.content);

  function save() {
    const content = draft.trim();
    if (!content) return;
    update.mutate(
      { noteId: note.id, content },
      { onSuccess: () => setEditing(false), onError: () => toast("Couldn't update note", "danger") },
    );
  }

  return (
    <div className="rounded-md border border-line bg-base p-2.5">
      <div className="mb-0.5 flex items-center justify-between gap-2 text-11 text-fg-subtle">
        <span className="flex min-w-0 items-center gap-1.5">
          <span className="truncate">{note.author_email ? note.author_email.split("@")[0] : "—"}</span>
          <RoleChip role={note.author_role} />
        </span>
        <span className="flex shrink-0 items-center gap-2">
          <span>{fmtRelative(note.updated_at || note.created_at)}</span>
          {note.can_edit && !editing && (
            <>
              <button
                onClick={() => {
                  setDraft(note.content);
                  setEditing(true);
                  setConfirmDel(false);
                }}
                className="text-fg-subtle hover:text-fg"
                title="Edit note"
              >
                <Pencil size={12} />
              </button>
              {confirmDel ? (
                <button
                  onClick={() =>
                    del.mutate(note.id, { onError: () => toast("Couldn't delete note", "danger") })
                  }
                  className="text-11 font-medium text-danger hover:underline"
                  disabled={del.isPending}
                >
                  Delete?
                </button>
              ) : (
                <button
                  onClick={() => setConfirmDel(true)}
                  className="text-fg-subtle hover:text-danger"
                  title="Delete note"
                >
                  <Trash2 size={12} />
                </button>
              )}
            </>
          )}
        </span>
      </div>
      {editing ? (
        <div className="mt-1 space-y-1.5">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={2}
            className="w-full resize-none rounded-md border border-line bg-control px-2 py-1 text-12 text-fg outline-none focus:border-accent"
          />
          <div className="flex justify-end gap-1.5">
            <Button size="sm" onClick={() => setEditing(false)}>
              <X size={12} /> Cancel
            </Button>
            <Button size="sm" variant="primary" onClick={save} disabled={update.isPending || !draft.trim()}>
              <Check size={12} /> Save
            </Button>
          </div>
        </div>
      ) : (
        <p className="whitespace-pre-wrap text-12 text-fg-muted">{note.content}</p>
      )}
    </div>
  );
}

function NoteGroup({
  dmId,
  tier,
  notes,
  canAdd,
  loading,
}: {
  dmId: number;
  tier: (typeof TIERS)[number];
  notes: DecisionMakerNoteOut[];
  canAdd: boolean;
  loading: boolean;
}) {
  const create = useCreateDmNote(dmId);
  const [draft, setDraft] = useState("");

  // Keep the panel uncluttered: hide a tier the viewer can neither add to nor see notes in.
  if (!canAdd && notes.length === 0) return null;

  function add() {
    const content = draft.trim();
    if (!content) return;
    create.mutate(
      { note_type: tier.type, content },
      { onSuccess: () => setDraft(""), onError: () => toast("Couldn't add note", "danger") },
    );
  }

  return (
    <div className={`rounded-lg border p-3 ${tier.cardClass}`}>
      <div className="mb-2 flex items-center gap-1.5">
        <span className="text-fg-muted">{tier.icon}</span>
        <span className="text-12 font-semibold text-fg">{tier.title}</span>
        <span className="text-11 text-fg-subtle">· {tier.subtitle}</span>
        {tier.pinned && notes.length > 0 && (
          <span className="ml-auto">
            <Badge tone="accent">Pinned</Badge>
          </span>
        )}
      </div>

      {canAdd && (
        <div className="mb-2 flex gap-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={2}
            placeholder={
              tier.type === "personal"
                ? "Private reminder — e.g. “Follow up after DAC.”"
                : `Add a ${tier.title.replace(/ Notes$/, "").toLowerCase()} note visible to the team…`
            }
            className="flex-1 resize-none rounded-md border border-line bg-control px-2 py-1 text-12 text-fg outline-none placeholder:text-fg-subtle focus:border-accent"
          />
          <Button size="sm" onClick={add} disabled={!draft.trim() || create.isPending}>
            Add
          </Button>
        </div>
      )}

      {loading ? (
        <div className="py-2">
          <Spinner size={13} />
        </div>
      ) : notes.length === 0 ? (
        <p className="text-11 text-fg-subtle">No notes yet.</p>
      ) : (
        <div className="space-y-1.5">
          {notes.map((n) => (
            <NoteItem key={n.id} dmId={dmId} note={n} />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Four-tier collaboration notes for a decision maker, shown admin → manager →
 * team → personal. admin/manager/team are visible to everyone; personal is
 * private to the author. Create rights: admin→admins, manager→admin/manager,
 * team & personal→any user (all backend-enforced).
 */
export function DmNotes({ dmId, open }: { dmId: number; open: boolean }) {
  const { isAdmin, isManager } = useAuth();
  const { data, isLoading } = useDmNotes(dmId, open);
  const notes = data ?? [];

  const canAdd: Record<NoteType, boolean> = {
    admin: isAdmin,
    manager: isManager,
    team: true,
    personal: true,
  };

  return (
    <div className="space-y-2.5">
      {TIERS.map((tier) => (
        <NoteGroup
          key={tier.type}
          dmId={dmId}
          tier={tier}
          notes={notes.filter((n) => n.note_type === tier.type)}
          canAdd={canAdd[tier.type]}
          loading={isLoading}
        />
      ))}
    </div>
  );
}
