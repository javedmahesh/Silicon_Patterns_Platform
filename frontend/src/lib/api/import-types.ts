/**
 * Historical Import DTOs (Phase 6).
 *
 * The /sync/imports endpoints return plain JSON (response_model=None on the backend),
 * so these shapes are declared here rather than generated into schema.ts. They mirror
 * backend/import_repo.py, backend/review_repo.py and backend/import_engine.py.
 */

export interface ImportJobDTO {
  import_id: string;
  source: string;
  filename: string;
  initiated_by: string;
  status: string; // previewed | running | completed | partial | failed | rolled_back | cancelled
  companies_processed: number;
  decision_makers_processed: number;
  created: number;
  updated: number;
  unchanged: number;
  duplicates: number;
  conflicts: number;
  invalid: number;
  summary: string;
  current_stage: string;
  records_processed: number;
  total_records: number;
  progress_pct: number;
  error_message: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number;
  created_at: string | null;
}

export interface ReviewFieldDTO {
  field: string;
  platform_value: string;
  historical_value: string;
  is_conflict: boolean;
  decision: string; // keep_platform | accept_historical
}

export interface ReviewItemDTO {
  record_kind: "company" | "decision_maker";
  source_ref: string;
  category: string;
  state: string; // pending | approved | rejected | skipped | resolved
  label: string;
  reviewer: string;
  reason: string;
  match_type: string | null;
  resolved_domain: string | null;
  fields: ReviewFieldDTO[];
}

export interface ReviewStatsDTO {
  total: number;
  by_state: Record<string, number>;
  by_category: Record<string, number>;
  importable: number;
  pending: number;
}

export interface ReviewResponseDTO {
  import_id: string;
  items: ReviewItemDTO[];
  stats: ReviewStatsDTO;
}

export interface ImportReportDTO {
  status: string;
  companies_created: number;
  companies_updated: number;
  decision_makers_created: number;
  decision_makers_updated: number;
  unchanged: number;
  duplicates_skipped: number;
  conflicts_skipped: number;
  invalid_skipped: number;
  companies_with_decision_makers: number;
  total_decision_makers: number;
  duration_ms: number;
  warnings: string[];
  errors: string[];
}

export interface AuditEventDTO {
  action: string;
  record_kind: string;
  source_ref: string;
  field: string;
  previous_value: string;
  approved_value: string;
  reviewer: string;
  reason: string;
  at: string | null;
}

export type ReviewDecision = "approve" | "reject" | "skip";
export type FieldChoice = "keep_platform" | "accept_historical";
export type BulkAction =
  | "approve_all"
  | "reject_all"
  | "approve_selected"
  | "reject_selected"
  | "approve_category"
  | "reject_category";

export const IMPORT_TERMINAL_STATES = ["completed", "partial", "failed", "rolled_back", "cancelled"];
