import type { PageResponse } from "./api";

export type ImportType = "PRODUCT_MASTER" | "PRODUCT_BARCODE";
export type SourceType = "PASTE" | "EXCEL_FILE" | "MANUAL";
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
  headers: string[];
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

export type ImportConfirmResult = ImportConfirmResponse;

export type ImportJobRowsResponse = PageResponse<ImportJobRow>;
export type ImportJobErrorsResponse = PageResponse<ImportValidationError>;
