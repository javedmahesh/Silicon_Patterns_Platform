import { Badge } from "@/components/ui/Badge";
import { enumLabel } from "@/lib/format";

type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";

const STAGE_TYPE_TONE: Record<string, Tone> = {
  open: "accent",
  won: "positive",
  lost: "danger",
};

const FORECAST_TONE: Record<string, Tone> = {
  pipeline: "neutral",
  best_case: "accent",
  commit: "warning",
  won: "positive",
  omitted: "neutral",
};

export function StageTypeBadge({ stageType }: { stageType: string }) {
  return <Badge tone={STAGE_TYPE_TONE[stageType] ?? "neutral"}>{enumLabel(stageType)}</Badge>;
}

export function ForecastCategoryBadge({ category }: { category: string }) {
  return <Badge tone={FORECAST_TONE[category] ?? "neutral"}>{enumLabel(category)}</Badge>;
}

export function fmtMoney(value: number | null | undefined, currency = "USD"): string {
  if (value == null) return "—";
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
  } catch {
    return `${currency} ${Math.round(value).toLocaleString("en-US")}`;
  }
}
