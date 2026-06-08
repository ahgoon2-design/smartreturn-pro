export type ChannelType = "NAVER_SMARTSTORE" | "COUPANG" | "CAFE24" | "EASYADMIN" | "COURIER";
export type ChannelAccountStatus = "ACTIVE" | "INACTIVE" | "AUTH_REQUIRED" | "ERROR";
export type ChannelAuthStatus = "NOT_CONNECTED" | "CONNECTED" | "EXPIRED" | "ERROR";
export type ChannelSyncJobStatus = "PENDING" | "RUNNING" | "SUCCESS" | "FAILED" | "PARTIAL_SUCCESS";
export type ChannelSyncJobType = "COLLECT_CHANGED_ORDERS" | "COLLECT_RETURN_CLAIMS" | "DRY_RUN";
export type ChannelRawEventStatus = "RECEIVED" | "NORMALIZED" | "DUPLICATE_SKIPPED" | "NEEDS_REVIEW" | "FAILED";

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
