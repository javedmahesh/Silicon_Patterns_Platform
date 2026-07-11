import { Badge } from "@/components/ui/Badge";
import type { OutreachStage } from "@/lib/api/types";

/** Human labels for the pipeline stages (snake_case → Title Case). */
export const STAGE_LABEL: Record<string, string> = {
  research_complete: "Research complete",
  outreach_ready: "Outreach ready",
  contacted: "Contacted",
  replied: "Replied",
  interested: "Interested",
  meeting_scheduled: "Meeting scheduled",
  proposal_sent: "Proposal sent",
  won: "Won",
  lost: "Lost",
};

type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";

const STAGE_TONE: Record<string, Tone> = {
  research_complete: "neutral",
  outreach_ready: "neutral",
  contacted: "accent",
  replied: "accent",
  interested: "accent",
  meeting_scheduled: "warning",
  proposal_sent: "warning",
  won: "positive",
  lost: "danger",
};

const PRIORITY_TONE: Record<string, Tone> = { high: "warning", medium: "accent", low: "neutral" };

const MSG_TONE: Record<string, Tone> = {
  draft: "neutral",
  pending_approval: "warning",
  approved: "accent",
  sent: "positive",
  replied: "positive",
  failed: "danger",
};

export function stageLabel(stage: string): string {
  return STAGE_LABEL[stage] ?? stage;
}

export function StageBadge({ stage }: { stage: string }) {
  return <Badge tone={STAGE_TONE[stage] ?? "neutral"}>{stageLabel(stage)}</Badge>;
}

export function PriorityBadge({ priority }: { priority: string }) {
  if (!priority) return null;
  return (
    <Badge tone={PRIORITY_TONE[priority] ?? "neutral"}>
      {priority[0].toUpperCase() + priority.slice(1)}
    </Badge>
  );
}

export function GradeBadge({ grade }: { grade: string }) {
  if (!grade) return null;
  const tone: Tone = grade.startsWith("A") ? "positive" : grade === "B" ? "accent" : "neutral";
  return <Badge tone={tone}>{grade}</Badge>;
}

export function MessageStatusBadge({ status }: { status: string }) {
  return (
    <Badge tone={MSG_TONE[status] ?? "neutral"}>{(STAGE_LABEL[status] ?? status).replace(/_/g, " ")}</Badge>
  );
}

export function serviceLabel(s?: string | null): string {
  if (!s) return "—";
  return s[0].toUpperCase() + s.slice(1);
}

/** Ordered open→closed list, handy for selects/kanban. */
export const STAGE_ORDER: OutreachStage[] = [
  "research_complete",
  "outreach_ready",
  "contacted",
  "replied",
  "interested",
  "meeting_scheduled",
  "proposal_sent",
  "won",
  "lost",
];
