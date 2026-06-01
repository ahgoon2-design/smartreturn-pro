import type { PageResponse } from "./api";

export type ReturnIntakeBatchStatus = "DRAFT" | "RECEIVED" | "VALIDATED" | "HAS_ERRORS" | "READY_FOR_PROCESSING";
export type ReturnIntakeRowValidationStatus = "NOT_VALIDATED" | "VALID" | "WARNING" | "INVALID";

export interface ReturnIntakeBatchSummary {
  batch_id: number;
  client_id: number;
  client_code?: string | null;
  client_name?: string | null;
  source_type: string;
  source_name?: string | null;
  status: ReturnIntakeBatchStatus | string;
  total_rows: number;
  valid_rows: number;
  warning_rows: number;
  error_rows: number;
  memo?: string | null;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export type ReturnIntakeBatchListResponse = PageResponse<ReturnIntakeBatchSummary>;

export interface ReturnIntakeBatchCreatePayload {
  client_id: number;
  source_type: string;
  source_name?: string | null;
  memo?: string | null;
}

export interface ReturnIntakePasteRow {
  row_no?: number;
  order_no?: string | null;
  return_tracking_no?: string | null;
  original_tracking_no?: string | null;
  product_code?: string | null;
  barcode?: string | null;
  product_name?: string | null;
  option_name?: string | null;
  qty?: number | string | null;
  return_reason?: string | null;
}

export interface ReturnIntakePasteRowsPayload {
  rows: ReturnIntakePasteRow[];
  replace_existing?: boolean;
}

export interface ReturnIntakePasteRowsResponse {
  batch_id: number;
  saved_row_count: number;
  status: string;
  total_rows: number;
  valid_rows: number;
  warning_rows: number;
  error_rows: number;
}

export interface ReturnIntakeRow {
  row_id: number;
  batch_id: number;
  client_id: number;
  row_no: number;
  order_no?: string | null;
  return_tracking_no?: string | null;
  original_tracking_no?: string | null;
  product_code?: string | null;
  barcode?: string | null;
  product_name?: string | null;
  option_name?: string | null;
  qty?: number | null;
  return_reason?: string | null;
  customer_name?: string | null;
  customer_phone_masked?: string | null;
  raw_data: Record<string, unknown>;
  validation_status: ReturnIntakeRowValidationStatus | string;
  validation_message?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export type ReturnIntakeRowsResponse = PageResponse<ReturnIntakeRow>;

export interface ReturnIntakeValidateResponse {
  batch_id: number;
  status: string;
  total_rows: number;
  valid_rows: number;
  warning_rows: number;
  error_rows: number;
}

export interface ReturnIntakePrepareProcessingResponse {
  batch_id: number;
  total_rows: number;
  prepared_rows: number;
  skipped_rows: number;
  invalid_rows: number;
  warning_rows: number;
  status: string;
  message: string;
}

export interface ReturnProcessingTask {
  task_id: number;
  row_id: number;
  batch_id: number;
  client_id: number;
  client_code?: string | null;
  client_name?: string | null;
  row_no: number;
  order_no?: string | null;
  return_tracking_no?: string | null;
  original_tracking_no?: string | null;
  product_code?: string | null;
  barcode?: string | null;
  product_name?: string | null;
  option_name?: string | null;
  qty?: number | null;
  return_reason?: string | null;
  validation_status: ReturnIntakeRowValidationStatus | string;
  status: string;
  created_at: string;
  updated_at: string;
}

export type ReturnProcessingTaskListResponse = PageResponse<ReturnProcessingTask>;
