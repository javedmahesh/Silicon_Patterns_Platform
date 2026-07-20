// Editable enum vocabularies mirrored from config/enums.py — used to constrain
// admin edit dropdowns to values the backend CHECK constraints accept.
export const COMPANY_TIERS = ["STARTUP", "SCALEUP", "ESTABLISHED", "INCUMBENT", "UNKNOWN"] as const;
export const PROSPECT_TYPES = [
  "PRODUCT_COMPANY", "SERVICE_PROVIDER", "EDA_VENDOR", "FOUNDRY",
  "INVESTOR", "PUBLISHER", "ACADEMIC", "UNKNOWN",
] as const;
export const COMPLIANCE_FLAGS = ["APPROVED", "EXCLUDED_REGION", "REVIEW_REQUIRED", "UNKNOWN"] as const;
export const LEADERSHIP_MOVEMENT_TYPES = [
  "promotion", "role_change", "new_executive_hire", "executive_departure",
  "board_appointment", "founder_change", "executive_reshuffle",
] as const;
export const LEADERSHIP_SENIORITY_BANDS = [
  "c_level", "president", "founder", "managing_director", "evp", "svp", "vp",
  "senior_director", "director", "head_of",
] as const;
export const CONFIDENCE_LEVELS = ["low", "medium", "high"] as const;
export const LEADERSHIP_PRIORITY_TIERS = ["high", "medium", "low"] as const;
