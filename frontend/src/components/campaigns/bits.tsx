import { Badge } from "@/components/ui/Badge";
import { enumLabel } from "@/lib/format";

type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";

const CAMPAIGN_STATUS_TONE: Record<string, Tone> = {
  draft: "neutral",
  active: "positive",
  paused: "warning",
  completed: "accent",
  archived: "neutral",
};

const MEMBER_STATUS_TONE: Record<string, Tone> = {
  active: "positive",
  paused: "warning",
  completed: "accent",
  removed: "neutral",
};

const OUTCOME_TONE: Record<string, Tone> = {
  converted: "positive",
  lost: "danger",
  no_response: "neutral",
  disqualified: "danger",
};

const ENROLLMENT_STATUS_TONE: Record<string, Tone> = {
  active: "positive",
  paused: "warning",
  completed: "accent",
  cancelled: "neutral",
  failed: "danger",
};

export function CampaignStatusBadge({ status }: { status: string }) {
  return <Badge tone={CAMPAIGN_STATUS_TONE[status] ?? "neutral"}>{enumLabel(status)}</Badge>;
}

export function MemberStatusBadge({ status }: { status: string }) {
  return <Badge tone={MEMBER_STATUS_TONE[status] ?? "neutral"}>{enumLabel(status)}</Badge>;
}

export function OutcomeBadge({ outcome }: { outcome: string }) {
  if (!outcome) return <span className="text-fg-subtle">—</span>;
  return <Badge tone={OUTCOME_TONE[outcome] ?? "neutral"}>{enumLabel(outcome)}</Badge>;
}

export function EnrollmentStatusBadge({ status }: { status: string }) {
  return <Badge tone={ENROLLMENT_STATUS_TONE[status] ?? "neutral"}>{enumLabel(status)}</Badge>;
}

export function SequenceActiveBadge({ isActive }: { isActive: boolean }) {
  return <Badge tone={isActive ? "positive" : "neutral"}>{isActive ? "Active" : "Paused"}</Badge>;
}

const STEP_ACTION_LABEL: Record<string, string> = {
  email: "Email",
  follow_up: "Follow-up",
  meeting_request: "Meeting request",
  call: "Call",
  task: "Task",
  wait: "Wait",
  manual_review: "Manual review",
};

export function stepActionLabel(action: string): string {
  return STEP_ACTION_LABEL[action] ?? enumLabel(action);
}
