export type ChannelType = "NAVER_SMARTSTORE" | "COUPANG" | "CAFE24" | "EASYADMIN" | "COURIER";
export type ChannelAccountStatus = "ACTIVE" | "INACTIVE" | "AUTH_REQUIRED" | "ERROR";
export type ChannelAuthStatus = "NOT_CONNECTED" | "CONNECTED" | "EXPIRED" | "ERROR";
export type ChannelSyncJobStatus = "PENDING" | "RUNNING" | "SUCCESS" | "FAILED" | "PARTIAL_SUCCESS";
export type ChannelSyncJobType = "COLLECT_CHANGED_ORDERS" | "COLLECT_RETURN_CLAIMS" | "DRY_RUN";
export type ChannelRawEventStatus = "RECEIVED" | "NORMALIZED" | "DUPLICATE_SKIPPED" | "NEEDS_REVIEW" | "FAILED";
export type ChannelReturnCandidateStatus =
  | "READY_FOR_INTAKE"
  | "TEAM_ASSIGN_PENDING"
  | "PRODUCT_MATCH_PENDING"
  | "RETURN_TRACKING_PENDING"
  | "NEEDS_REVIEW"
  | "BLOCKED";
export type ChannelReturnExpectedCreateStatus = "NOT_CREATED" | "CREATED" | "SKIPPED_DUPLICATE" | "FAILED";
export type ChannelReturnCorrectionStatus = "NONE" | "CORRECTED" | "REVIEWED" | "REPROCESS_REQUIRED";

export interface ChannelAccount {
  id: number;
  client_id: number;
  client_unit_id?: number | null;
  channel_type: ChannelType;
  account_name: string;
  store_name: string;
  external_account_id?: string | null;
  status: ChannelAccountStatus;
  auth_status: ChannelAuthStatus;
  credential_ref_masked?: string | null;
  last_sync_at?: string | null;
  last_success_sync_at?: string | null;
  last_error_at?: string | null;
  last_error_code?: string | null;
  last_error_message?: string | null;
  sync_enabled: boolean;
  created_by?: number | null;
  updated_by?: number | null;
  created_at: string;
  updated_at: string;
}

export interface ChannelAccountCreatePayload {
  client_id: number;
  client_unit_id?: number | null;
  channel_type: ChannelType;
  account_name: string;
  store_name: string;
  external_account_id?: string | null;
  credential_ref?: string | null;
  sync_enabled?: boolean;
}

export interface ChannelAccountUpdatePayload {
  client_unit_id?: number | null;
  account_name?: string | null;
  store_name?: string | null;
  external_account_id?: string | null;
  status?: ChannelAccountStatus | null;
  auth_status?: ChannelAuthStatus | null;
  credential_ref?: string | null;
  sync_enabled?: boolean | null;
}

export interface ChannelConnectionTestResponse {
  channel_account_id: number;
  channel_type: ChannelType;
  dry_run: boolean;
  success: boolean;
  status: ChannelAccountStatus;
  auth_status: ChannelAuthStatus;
  message: string;
  provider_name: string;
}

export interface ChannelSyncDryRunPayload {
  job_type?: ChannelSyncJobType;
  save_mock_event?: boolean;
}

export interface ChannelSyncJob {
  id: number;
  channel_account_id: number;
  job_type: ChannelSyncJobType;
  status: ChannelSyncJobStatus;
  cursor_from?: string | null;
  cursor_to?: string | null;
  cursor_more_from?: string | null;
  cursor_more_sequence?: string | null;
  total_collected: number;
  total_inserted: number;
  total_updated: number;
  total_skipped: number;
  total_failed: number;
  started_at?: string | null;
  finished_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface ChannelSyncDryRunResponse {
  job: ChannelSyncJob;
  dry_run: boolean;
  provider_name: string;
  collected_event_count: number;
  inserted_event_count: number;
  updated_event_count: number;
  skipped_event_count: number;
  message: string;
}

export interface ChannelRawEventListItem {
  id: number;
  channel_account_id: number;
  channel_type: ChannelType;
  event_type: string;
  external_order_id?: string | null;
  external_product_order_id?: string | null;
  external_claim_id?: string | null;
  external_tracking_no_hash?: string | null;
  last_changed_at?: string | null;
  raw_hash: string;
  process_status: ChannelRawEventStatus;
  process_error_code?: string | null;
  process_error_message?: string | null;
  collected_at: string;
  created_at: string;
}

export interface ChannelReturnCandidate {
  id: number;
  channel_raw_event_id: number;
  channel_account_id: number;
  client_id: number;
  client_unit_id?: number | null;
  source_type: string;
  source_origin: string;
  external_order_id?: string | null;
  external_product_order_id?: string | null;
  external_claim_id?: string | null;
  return_tracking_no?: string | null;
  original_tracking_no?: string | null;
  tracking_no_for_scan?: string | null;
  product_code?: string | null;
  barcode?: string | null;
  product_id?: number | null;
  product_name?: string | null;
  option_name?: string | null;
  qty?: number | null;
  claim_reason?: string | null;
  claim_status?: string | null;
  match_status: ChannelReturnCandidateStatus;
  match_reason: string;
  risk_flags: string[];
  reviewed_at?: string | null;
  reviewed_by?: number | null;
  manual_client_unit_id?: number | null;
  manual_product_id?: number | null;
  manual_product_code?: string | null;
  manual_return_tracking_no?: string | null;
  manual_original_tracking_no?: string | null;
  manual_qty?: number | null;
  manual_review_note?: string | null;
  manual_reviewed_by?: number | null;
  manual_reviewed_at?: string | null;
  correction_status: ChannelReturnCorrectionStatus;
  correction_summary: Record<string, unknown>;
  return_expected_id?: number | null;
  return_expected_created_at?: string | null;
  return_expected_create_status: ChannelReturnExpectedCreateStatus;
  return_expected_create_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChannelReturnCandidateListResponse {
  items: ChannelReturnCandidate[];
  summary: Record<string, number>;
}

export interface ChannelRawEventTransformResponse {
  candidate: ChannelReturnCandidate;
  created: boolean;
  message: string;
}

export interface ChannelRawEventsBulkTransformResponse {
  transformed_count: number;
  created_count: number;
  updated_count: number;
  failed_count: number;
  candidates: ChannelReturnCandidate[];
  summary: Record<string, number>;
}

export interface ChannelReturnCandidateActionResponse {
  candidate: ChannelReturnCandidate;
  message: string;
}

export interface ChannelReturnCandidateCorrectionPayload {
  client_unit_id?: number | null;
  product_id?: number | null;
  product_code?: string | null;
  return_tracking_no?: string | null;
  original_tracking_no?: string | null;
  qty?: number | null;
  review_note?: string | null;
}

export interface ChannelReturnExpectedCreateResponse {
  candidate: ChannelReturnCandidate;
  return_expected_id?: number | null;
  created: boolean;
  skipped_duplicate: boolean;
  message: string;
}

export interface ChannelReturnExpectedBulkCreateResponse {
  total_requested: number;
  created_count: number;
  skipped_duplicate_count: number;
  blocked_count: number;
  failed_count: number;
  created_candidate_ids: number[];
  blocked_reasons: string[];
  error_summary: string[];
  candidates: ChannelReturnCandidate[];
}
