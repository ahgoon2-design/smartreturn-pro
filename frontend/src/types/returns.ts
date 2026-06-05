import type { PageResponse } from "./api";

export type ReturnIntakeBatchStatus = "DRAFT" | "RECEIVED" | "VALIDATED" | "HAS_ERRORS" | "READY_FOR_PROCESSING";
export type ReturnIntakeRowValidationStatus = "NOT_VALIDATED" | "VALID" | "WARNING" | "INVALID";
export type ReturnJudgementStatus = "GOOD" | "REFURB" | "SAMPLE" | "MANUFACTURER_RETURN" | "DISPOSAL" | "HOLD";
export type ReturnLabelPrintStatus =
  | "NOT_REQUIRED"
  | "PRINT_PENDING"
  | "PRINTED"
  | "PRINT_FAILED"
  | "LOCAL_AGENT_NOT_CONNECTED";
export type ReturnExternalOutboundStatus = "NOT_REQUIRED" | "READY" | "SCANNED" | "CONFIRMED";
export type ReturnHoldStatus = "HOLD_PENDING" | "CUSTOMER_CHECKING" | "READY_TO_REJUDGE" | "RESOLVED";
export type ReturnDisposalStatus = "DISPOSAL_PENDING" | "DISPOSAL_CONFIRMED";

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
  judgement_status?: ReturnJudgementStatus | string | null;
  judgement_memo?: string | null;
  judged_at?: string | null;
  judged_by?: number | null;
  return_management_no?: string | null;
  return_label_no?: string | null;
  label_print_required?: boolean;
  label_print_status?: ReturnLabelPrintStatus | string | null;
  label_printed_at?: string | null;
  inventory_reflected_yn?: boolean;
  inventory_reflected_at?: string | null;
  inventory_event_id?: number | null;
  external_outbound_required?: boolean;
  external_outbound_status?: ReturnExternalOutboundStatus | string;
  external_outbound_at?: string | null;
  external_outbound_confirmed_by?: number | null;
  hold_status?: ReturnHoldStatus | string;
  hold_reason?: string | null;
  hold_response_memo?: string | null;
  hold_resolved_at?: string | null;
  hold_resolved_by?: number | null;
  disposal_status?: ReturnDisposalStatus | string;
  disposal_reason?: string | null;
  disposal_memo?: string | null;
  disposal_confirmed_at?: string | null;
  disposal_confirmed_by?: number | null;
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
  judgement_status?: ReturnJudgementStatus | string | null;
  judgement_memo?: string | null;
  judged_at?: string | null;
  judged_by?: number | null;
  return_management_no?: string | null;
  return_label_no?: string | null;
  label_print_required?: boolean;
  label_print_status?: ReturnLabelPrintStatus | string | null;
  label_printed_at?: string | null;
  inventory_reflected_yn?: boolean;
  inventory_reflected_at?: string | null;
  inventory_event_id?: number | null;
  external_outbound_required?: boolean;
  external_outbound_status?: ReturnExternalOutboundStatus | string;
  external_outbound_at?: string | null;
  external_outbound_confirmed_by?: number | null;
  hold_status?: ReturnHoldStatus | string;
  hold_reason?: string | null;
  hold_response_memo?: string | null;
  hold_resolved_at?: string | null;
  hold_resolved_by?: number | null;
  disposal_status?: ReturnDisposalStatus | string;
  disposal_reason?: string | null;
  disposal_memo?: string | null;
  disposal_confirmed_at?: string | null;
  disposal_confirmed_by?: number | null;
  created_at: string;
  updated_at: string;
}

export type ReturnProcessingTaskListResponse = PageResponse<ReturnProcessingTask>;

export interface JudgeReturnProcessingTaskPayload {
  judgement_status: ReturnJudgementStatus;
  judgement_memo?: string | null;
  print_label?: boolean;
}

export interface JudgeReturnProcessingTaskResponse extends ReturnProcessingTask {
  message: string;
}

export interface ReturnProcessingAttachment {
  attachment_id: number;
  task_id: number;
  row_id: number;
  batch_id: number;
  client_id: number;
  attachment_type: string;
  original_filename: string;
  content_type: string;
  file_size: number;
  note?: string | null;
  uploaded_by: number;
  uploaded_at: string;
  active_yn: boolean;
  preview_url?: string | null;
  download_url?: string | null;
}

export interface ReturnProcessingAttachmentListResponse {
  items: ReturnProcessingAttachment[];
}

export interface UploadReturnProcessingAttachmentPayload {
  attachment_type?: string;
  note?: string | null;
}

export type UploadReturnProcessingAttachmentResponse = ReturnProcessingAttachment;

export type ReturnClosingAction = "INVENTORY_REFLECT_TARGET" | "FOLLOWUP_TARGET" | string;

export interface ReturnClosingCandidate {
  row_id: number;
  task_id: number;
  batch_id: number;
  client_id: number;
  client_code?: string | null;
  client_name?: string | null;
  row_no: number;
  order_no?: string | null;
  return_tracking_no?: string | null;
  product_code?: string | null;
  barcode?: string | null;
  product_name?: string | null;
  qty?: number | null;
  judgement_status: ReturnJudgementStatus | string;
  return_management_no?: string | null;
  return_label_no?: string | null;
  status: string;
  inventory_reflected_yn: boolean;
  inventory_reflected_at?: string | null;
  inventory_event_id?: number | null;
  judged_at?: string | null;
  created_at: string;
  updated_at: string;
  closing_action: ReturnClosingAction;
  message?: string | null;
}

export type ReturnClosingCandidateListResponse = PageResponse<ReturnClosingCandidate>;

export interface ReturnClosingConfirmPayload {
  row_ids: number[];
  client_id?: number;
  confirm_good_only?: boolean;
}

export interface ReturnClosingRowResult {
  row_id: number;
  judgement_status?: ReturnJudgementStatus | string | null;
  result: string;
  message: string;
  inventory_event_id?: number | null;
}

export interface ReturnClosingConfirmResponse {
  total_rows: number;
  reflected_rows: number;
  skipped_rows: number;
  failed_rows: number;
  followup_rows: number;
  event_count: number;
  message: string;
  row_results: ReturnClosingRowResult[];
}

export interface ReturnExternalOutboundCandidate {
  row_id: number;
  task_id: number;
  batch_id: number;
  client_id: number;
  client_code?: string | null;
  client_name?: string | null;
  row_no: number;
  order_no?: string | null;
  return_tracking_no?: string | null;
  product_code?: string | null;
  barcode?: string | null;
  product_name?: string | null;
  option_name?: string | null;
  qty?: number | null;
  judgement_status: ReturnJudgementStatus | string;
  return_management_no?: string | null;
  return_label_no?: string | null;
  external_outbound_required: boolean;
  external_outbound_status: ReturnExternalOutboundStatus | string;
  external_outbound_at?: string | null;
  external_outbound_confirmed_by?: number | null;
  judged_at?: string | null;
  created_at: string;
  updated_at: string;
}

export type ReturnExternalOutboundCandidateListResponse = PageResponse<ReturnExternalOutboundCandidate>;

export interface ReturnExternalOutboundConfirmPayload {
  row_ids: number[];
  scanned_numbers?: string[];
  client_id?: number;
}

export interface ReturnExternalOutboundRowResult {
  row_id: number;
  judgement_status?: ReturnJudgementStatus | string | null;
  result: string;
  message: string;
  external_outbound_status?: ReturnExternalOutboundStatus | string | null;
}

export interface ReturnExternalOutboundConfirmResponse {
  total_rows: number;
  confirmed_rows: number;
  skipped_rows: number;
  failed_rows: number;
  message: string;
  row_results: ReturnExternalOutboundRowResult[];
}

export interface ReturnHoldCandidate {
  row_id: number;
  task_id: number;
  batch_id: number;
  client_id: number;
  client_code?: string | null;
  client_name?: string | null;
  row_no: number;
  order_no?: string | null;
  return_tracking_no?: string | null;
  product_code?: string | null;
  barcode?: string | null;
  product_name?: string | null;
  option_name?: string | null;
  qty?: number | null;
  return_reason?: string | null;
  judgement_status: ReturnJudgementStatus | string;
  judgement_memo?: string | null;
  hold_status: ReturnHoldStatus | string;
  hold_reason?: string | null;
  hold_response_memo?: string | null;
  hold_resolved_at?: string | null;
  hold_resolved_by?: number | null;
  return_management_no?: string | null;
  return_label_no?: string | null;
  judged_at?: string | null;
  created_at: string;
  updated_at: string;
}

export type ReturnHoldCandidateListResponse = PageResponse<ReturnHoldCandidate>;

export interface UpdateReturnHoldTaskPayload {
  hold_status: ReturnHoldStatus;
  hold_reason?: string | null;
  hold_response_memo?: string | null;
}

export interface UpdateReturnHoldTaskResponse extends ReturnHoldCandidate {
  message: string;
}

export interface ReturnDisposalCandidate {
  row_id: number;
  task_id: number;
  batch_id: number;
  client_id: number;
  client_code?: string | null;
  client_name?: string | null;
  row_no: number;
  order_no?: string | null;
  return_tracking_no?: string | null;
  product_code?: string | null;
  barcode?: string | null;
  product_name?: string | null;
  option_name?: string | null;
  qty?: number | null;
  return_reason?: string | null;
  judgement_status: ReturnJudgementStatus | string;
  judgement_memo?: string | null;
  disposal_status: ReturnDisposalStatus | string;
  disposal_reason?: string | null;
  disposal_memo?: string | null;
  disposal_confirmed_at?: string | null;
  disposal_confirmed_by?: number | null;
  return_management_no?: string | null;
  return_label_no?: string | null;
  judged_at?: string | null;
  created_at: string;
  updated_at: string;
}

export type ReturnDisposalCandidateListResponse = PageResponse<ReturnDisposalCandidate>;

export interface ConfirmReturnDisposalTaskPayload {
  disposal_reason?: string | null;
  disposal_memo?: string | null;
}

export interface ConfirmReturnDisposalTaskResponse extends ReturnDisposalCandidate {
  message: string;
}
