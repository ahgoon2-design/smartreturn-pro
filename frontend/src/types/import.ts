import type { PageResponse } from "./api";

export type ImportType =
  | "PRODUCT_MASTER"
  | "PRODUCT_BARCODE"
  | "CLIENT_MASTER"
  | "COMMON_CODE"
  | "CLIENT_WAREHOUSE"
  | "CLIENT_UNIT"
  | "RETURN_WAREHOUSE_ROUTE"
  | "RETURN_INTAKE"
  | "RETURN_WAYBILL_EXPECTED"
  | "VENDOR_RETURN_DETAIL"
  | "RETURN_EXPECTED"
  | "RETURN_RECEPTION"
  | "INBOUND_EXPECTED"
  | "OUTBOUND_ORDER";
export type SourceType = "PASTE" | "EXCEL_FILE" | "CSV_FILE" | "MANUAL" | "GOOGLE_SHEET" | "API";
export type JobStatus = "DRAFT" | "READY_TO_VALIDATE" | "VALIDATING" | "VALIDATED" | "HAS_ERRORS" | "FAILED" | "APPLIED";
export type ValidationStatus = "NOT_VALIDATED" | "VALID" | "WARNING" | "INVALID";
export type ValidationSeverity = "ERROR" | "WARNING";

export interface ImportJob {
  id?: number;
  job_id?: number;
  import_type: string;
  source_type: string;
  requested_client_id: number;
  status: string;
  total_rows?: number;
  parsed_rows?: number;
  valid_rows?: number;
  invalid_rows?: number;
  error_rows?: number;
  warning_rows?: number;
  inserted_rows?: number;
  updated_rows?: number;
  skipped_rows?: number;
  skipped_empty_rows?: number;
  skipped_noise_rows?: number;
  skipped_rows_total?: number;
  total_read_rows?: number;
  header_row_no?: number | null;
  applied_rows?: number;
  failed_rows?: number;
  progress_percent?: number;
  file_name?: string | null;
  worksheet_name?: string | null;
  message?: string | null;
}

export interface ImportJobCreateRequest {
  import_type: ImportType;
  source_type: SourceType;
  requested_client_id: number;
  source_name?: string;
  file_name?: string;
  worksheet_name?: string;
}

export interface ImportExcelUploadResponse {
  job_id: number;
  saved_row_count: number;
  status: string;
  total_rows: number;
  parsed_rows: number;
  valid_rows: number;
  invalid_rows: number;
  error_rows: number;
  progress_percent: number;
  file_name: string;
  worksheet_name: string;
  header_row_no?: number;
  total_read_rows?: number;
  headers: string[];
  mapped_headers?: Record<string, string>;
  unmapped_headers?: string[];
  skipped_empty_rows?: number;
  skipped_noise_rows?: number;
  skipped_rows_total?: number;
}

export interface ImportPasteRowsResponse {
  job_id: number;
  saved_row_count: number;
  status: string;
  total_rows: number;
  parsed_rows: number;
  valid_rows: number;
  invalid_rows: number;
  error_rows: number;
  progress_percent: number;
  skipped_empty_rows?: number;
  skipped_noise_rows?: number;
  skipped_rows_total?: number;
  total_read_rows?: number;
}

export interface ImportPasteRowItem {
  row_no?: number;
  raw_json: Record<string, unknown>;
  normalized_json?: Record<string, unknown> | null;
  source_row_key?: string | null;
}

export interface ImportPasteRowsRequest {
  rows: ImportPasteRowItem[];
  replace_existing: false;
  source_name?: string;
  worksheet_name?: string;
}

export interface ImportJobRow {
  id?: number;
  row_id?: number;
  job_id: number;
  row_no: number;
  raw_json: Record<string, unknown>;
  normalized_json?: Record<string, unknown> | null;
  validation_status: ValidationStatus | string;
  validation_message?: string | null;
}

export interface ImportValidationError {
  id?: number;
  error_id?: number;
  job_id: number;
  row_id?: number | null;
  row_no: number;
  field_name?: string | null;
  raw_value?: unknown;
  error_code: string;
  error_message: string;
  severity: ValidationSeverity | string;
}

export interface ImportValidationRunResponse {
  job_id: number;
  status: string;
  total_rows?: number;
  validated_row_count?: number;
  valid_rows?: number;
  invalid_rows?: number;
  warning_rows?: number;
  error_rows?: number;
  validation_error_count?: number;
  progress_percent?: number;
}

export interface ImportConfirmResponse {
  job_id: number;
  import_type: string;
  source_type: string;
  status: string;
  total_rows: number;
  applied_rows: number;
  skipped_rows: number;
  failed_rows: number;
  warning_rows: number;
  invalid_rows: number;
  result_code: string;
  message: string;
}

export interface ImportCanonicalField {
  field_name: string;
  label: string;
  required: boolean;
  aliases: string[];
}

export interface ImportSourceTypesResponse {
  import_types: string[];
  source_types: string[];
}

export interface ImportSourceTypeFieldsResponse {
  import_type: string;
  fields: ImportCanonicalField[];
}

export interface ImportMappingSuggestionItem {
  source_header: string;
  target_field?: string | null;
  canonical_field?: string | null;
  confidence: number;
  status: string;
  decision_level?: "AUTO_APPLY" | "NEEDS_REVIEW" | "LOW_CONFIDENCE" | "BLOCKED" | string | null;
  reason?: string | null;
  provider?: string | null;
  providers?: string[];
  is_required?: boolean;
  is_risky_field?: boolean;
  previous_profile_matched?: boolean;
  decision_history_count?: number;
  conflict_reason?: string | null;
  alternative_candidates?: Array<Record<string, unknown>>;
  risk_flags?: string[];
  blocked_reason?: string | null;
  user_action_required?: boolean;
  needs_user_confirmation?: boolean;
  is_auto_applied?: boolean;
}

export interface ImportMappingResponse {
  job_id: number;
  import_type: string;
  source_type: string;
  header_signature: string;
  applied_mapping: Record<string, string>;
  suggestions: ImportMappingSuggestionItem[];
  mapped_rows: number;
  confirmation_required: boolean;
  low_confidence_headers: string[];
  ambiguous_headers: string[];
  unmapped_headers: string[];
  required_missing_fields: string[];
  decision_summary?: Record<string, number>;
  blocked_reasons?: string[];
  confirm_block_reasons?: string[];
  can_confirm?: boolean;
  required_fields_status?: Record<string, { mapped: boolean; decision_level: string }>;
  auto_apply_count?: number;
  needs_review_count?: number;
  low_confidence_count?: number;
  blocked_count?: number;
  profile_match_status?: string | null;
  learning_status?: string | null;
}

export interface ImportMappingProfile {
  profile_id: number;
  client_id?: number | null;
  import_type: string;
  source_type: string;
  profile_name: string;
  header_signature: string;
  mapping_json: Record<string, string>;
  active_yn: boolean;
  last_used_at?: string | null;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export type ImportConfirmResult = ImportConfirmResponse;

export type ImportJobRowsResponse = PageResponse<ImportJobRow>;
export type ImportJobErrorsResponse = PageResponse<ImportValidationError>;
export type ImportMappingProfilesResponse = { items: ImportMappingProfile[] };
