import { Badge } from "@/components/ui/Badge";
import { enumLabel } from "@/lib/format";

type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";

const ACCOUNT_STATUS_TONE: Record<string, Tone> = {
  prospect: "neutral",
  active: "positive",
  at_risk: "warning",
  churned: "danger",
  inactive: "neutral",
};

const CONTRACT_STATUS_TONE: Record<string, Tone> = {
  draft: "neutral",
  active: "positive",
  expired: "danger",
  renewed: "positive",
  terminated: "danger",
  pending_renewal: "warning",
};

const MILESTONE_STATUS_TONE: Record<string, Tone> = {
  pending: "neutral",
  in_progress: "accent",
  completed: "positive",
  at_risk: "warning",
  missed: "danger",
};

const RISK_SEVERITY_TONE: Record<string, Tone> = {
  low: "neutral",
  medium: "accent",
  high: "warning",
  critical: "danger",
};

const RISK_STATUS_TONE: Record<string, Tone> = {
  open: "warning",
  mitigated: "accent",
  accepted: "neutral",
  closed: "positive",
};

const GRADE_TONE: Record<string, Tone> = { A: "positive", B: "positive", C: "accent", D: "warning", F: "danger" };

export function AccountStatusBadge({ status }: { status: string }) {
  return <Badge tone={ACCOUNT_STATUS_TONE[status] ?? "neutral"}>{enumLabel(status)}</Badge>;
}

export function ContractStatusBadge({ status }: { status: string }) {
  return <Badge tone={CONTRACT_STATUS_TONE[status] ?? "neutral"}>{enumLabel(status)}</Badge>;
}

export function MilestoneStatusBadge({ status }: { status: string }) {
  return <Badge tone={MILESTONE_STATUS_TONE[status] ?? "neutral"}>{enumLabel(status)}</Badge>;
}

export function RiskSeverityBadge({ severity }: { severity: string }) {
  return <Badge tone={RISK_SEVERITY_TONE[severity] ?? "neutral"}>{enumLabel(severity)}</Badge>;
}

export function RiskStatusBadge({ status }: { status: string }) {
  return <Badge tone={RISK_STATUS_TONE[status] ?? "neutral"}>{enumLabel(status)}</Badge>;
}

export function HealthGradeBadge({ grade }: { grade: string | null | undefined }) {
  if (!grade) return <span className="text-fg-subtle">—</span>;
  return <Badge tone={GRADE_TONE[grade] ?? "neutral"}>{grade}</Badge>;
}

const TREND_ARROW: Record<string, string> = { up: "↑", down: "↓", stable: "→" };
const TREND_TONE: Record<string, Tone> = { up: "positive", down: "danger", stable: "neutral" };

export function HealthTrendBadge({ trend }: { trend: string | null | undefined }) {
  if (!trend) return null;
  return <Badge tone={TREND_TONE[trend] ?? "neutral"}>{TREND_ARROW[trend] ?? ""} {enumLabel(trend)}</Badge>;
}

export function fmtMoney(value: number | null | undefined, currency = "USD"): string {
  if (value == null) return "—";
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
  } catch {
    return `${currency} ${Math.round(value).toLocaleString("en-US")}`;
  }
}
