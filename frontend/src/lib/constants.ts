import { enumLabel } from "./format";

// Enum vocabularies mirror config/lead_scoring.json + the engine classifications.
export const TIERS = ["STARTUP", "SCALEUP", "ESTABLISHED", "INCUMBENT"] as const;
export const PROSPECT_TYPES = [
  "PRODUCT_COMPANY",
  "SERVICE_PROVIDER",
  "EDA_VENDOR",
  "FOUNDRY",
  "INVESTOR",
  "PUBLISHER",
  "ACADEMIC",
] as const;

export interface Option {
  value: string;
  label: string;
}

const toOptions = (values: readonly string[]): Option[] =>
  values.map((v) => ({ value: v, label: enumLabel(v) }));

export const TIER_OPTIONS = toOptions(TIERS);
export const PROSPECT_OPTIONS = toOptions(PROSPECT_TYPES);
export const GRADE_OPTIONS: Option[] = ["A+", "A", "B", "C"].map((g) => ({ value: g, label: g }));
