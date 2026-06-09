import { apiRequest } from "./client";
import type {
  ChannelAccount,
  ChannelAccountCreatePayload,
  ChannelAccountUpdatePayload,
  ChannelConnectionTestResponse,
  ChannelDashboardSummary,
  ChannelRawEventListItem,
  ChannelRawEventsBulkTransformResponse,
  ChannelRawEventTransformResponse,
  ChannelReturnCandidateActionResponse,
  ChannelReturnCandidateCorrectionPayload,
  ChannelReturnCandidateListResponse,
  ChannelReturnExpectedBulkCreateResponse,
  ChannelReturnExpectedCreateResponse,
  ChannelSyncDryRunPayload,
  ChannelSyncDryRunResponse,
  ChannelSyncJob,
  ProductChannelMappingListResponse,
} from "../types/channels";

export interface ChannelAccountListOptions {
  clientId?: number;
  channelType?: string;
  includeInactive?: boolean;
}

export async function listChannelAccounts(options: ChannelAccountListOptions = {}) {
  const params = new URLSearchParams();
  if (options.clientId) {
    params.set("client_id", String(options.clientId));
  }
  if (options.channelType) {
    params.set("channel_type", options.channelType);
  }
  if (options.includeInactive) {
    params.set("include_inactive", "true");
  }
  const query = params.toString();
  return apiRequest<{ items: ChannelAccount[] }>(`/api/channels/accounts${query ? `?${query}` : ""}`);
}

export async function createChannelAccount(payload: ChannelAccountCreatePayload) {
  return apiRequest<ChannelAccount>("/api/channels/accounts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateChannelAccount(accountId: number, payload: ChannelAccountUpdatePayload) {
  return apiRequest<ChannelAccount>(`/api/channels/accounts/${accountId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function disableChannelAccount(accountId: number) {
  return apiRequest<ChannelAccount>(`/api/channels/accounts/${accountId}/disable`, {
    method: "POST",
  });
}

export async function testChannelConnection(accountId: number) {
  return apiRequest<ChannelConnectionTestResponse>(`/api/channels/accounts/${accountId}/test-connection`, {
    method: "POST",
  });
}

export async function runChannelDryRunSync(accountId: number, payload: ChannelSyncDryRunPayload = {}) {
  return apiRequest<ChannelSyncDryRunResponse>(`/api/channels/accounts/${accountId}/sync-jobs/dry-run`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listChannelSyncJobs(accountId?: number) {
  const path = accountId ? `/api/channels/accounts/${accountId}/sync-jobs` : "/api/channels/sync-jobs";
  return apiRequest<{ items: ChannelSyncJob[] }>(path);
}

export async function listChannelRawEvents(options: { accountId?: number; processStatus?: string } = {}) {
  const params = new URLSearchParams();
  if (options.accountId) {
    params.set("account_id", String(options.accountId));
  }
  if (options.processStatus) {
    params.set("process_status", options.processStatus);
  }
  const query = params.toString();
  return apiRequest<{ items: ChannelRawEventListItem[] }>(`/api/channels/raw-events${query ? `?${query}` : ""}`);
}

export interface ChannelDashboardSummaryOptions {
  clientId?: number;
  clientUnitId?: number;
  channelType?: string;
  accountId?: number;
  dateFrom?: string;
  dateTo?: string;
  status?: string;
}

export async function getChannelDashboardSummary(options: ChannelDashboardSummaryOptions = {}) {
  const params = new URLSearchParams();
  if (options.clientId) {
    params.set("client_id", String(options.clientId));
  }
  if (options.clientUnitId) {
    params.set("client_unit_id", String(options.clientUnitId));
  }
  if (options.channelType) {
    params.set("channel_type", options.channelType);
  }
  if (options.accountId) {
    params.set("account_id", String(options.accountId));
  }
  if (options.dateFrom) {
    params.set("date_from", options.dateFrom);
  }
  if (options.dateTo) {
    params.set("date_to", options.dateTo);
  }
  if (options.status) {
    params.set("status", options.status);
  }
  const query = params.toString();
  return apiRequest<ChannelDashboardSummary>(`/api/channels/dashboard/summary${query ? `?${query}` : ""}`);
}

export async function transformChannelRawEvent(rawEventId: number) {
  return apiRequest<ChannelRawEventTransformResponse>(`/api/channels/raw-events/${rawEventId}/transform`, {
    method: "POST",
  });
}

export async function transformChannelAccountRawEvents(accountId: number) {
  return apiRequest<ChannelRawEventsBulkTransformResponse>(`/api/channels/accounts/${accountId}/raw-events/transform`, {
    method: "POST",
  });
}

export interface ChannelReturnCandidateListOptions {
  accountId?: number;
  matchStatus?: string;
  correctionStatus?: string;
  returnExpectedCreateStatus?: string;
  channelType?: string;
  clientId?: number;
  clientUnitId?: number;
  hasReturnTrackingNo?: boolean;
  hasProduct?: boolean;
  dateFrom?: string;
  dateTo?: string;
  keyword?: string;
  sortBy?: string;
}

export async function listChannelReturnCandidates(options: ChannelReturnCandidateListOptions = {}) {
  const params = new URLSearchParams();
  if (options.accountId) {
    params.set("account_id", String(options.accountId));
  }
  if (options.matchStatus && options.matchStatus !== "ALL") {
    params.set("match_status", options.matchStatus);
  }
  if (options.correctionStatus && options.correctionStatus !== "ALL") {
    params.set("correction_status", options.correctionStatus);
  }
  if (options.returnExpectedCreateStatus && options.returnExpectedCreateStatus !== "ALL") {
    params.set("return_expected_create_status", options.returnExpectedCreateStatus);
  }
  if (options.channelType) {
    params.set("channel_type", options.channelType);
  }
  if (options.clientId) {
    params.set("client_id", String(options.clientId));
  }
  if (options.clientUnitId) {
    params.set("client_unit_id", String(options.clientUnitId));
  }
  if (options.hasReturnTrackingNo !== undefined) {
    params.set("has_return_tracking_no", String(options.hasReturnTrackingNo));
  }
  if (options.hasProduct !== undefined) {
    params.set("has_product", String(options.hasProduct));
  }
  if (options.dateFrom) {
    params.set("date_from", options.dateFrom);
  }
  if (options.dateTo) {
    params.set("date_to", options.dateTo);
  }
  if (options.keyword?.trim()) {
    params.set("keyword", options.keyword.trim());
  }
  if (options.sortBy) {
    params.set("sort_by", options.sortBy);
  }
  const query = params.toString();
  return apiRequest<ChannelReturnCandidateListResponse>(`/api/channels/return-candidates${query ? `?${query}` : ""}`);
}

export interface ProductChannelMappingListOptions {
  clientId?: number;
  channelType?: string;
  accountId?: number;
  decisionType?: string;
  conflictOnly?: boolean;
  keyword?: string;
}

export async function listProductChannelMappings(options: ProductChannelMappingListOptions = {}) {
  const params = new URLSearchParams();
  if (options.clientId) {
    params.set("client_id", String(options.clientId));
  }
  if (options.channelType) {
    params.set("channel_type", options.channelType);
  }
  if (options.accountId) {
    params.set("account_id", String(options.accountId));
  }
  if (options.decisionType) {
    params.set("decision_type", options.decisionType);
  }
  if (options.conflictOnly) {
    params.set("conflict_only", "true");
  }
  if (options.keyword?.trim()) {
    params.set("keyword", options.keyword.trim());
  }
  const query = params.toString();
  return apiRequest<ProductChannelMappingListResponse>(`/api/channels/product-mappings${query ? `?${query}` : ""}`);
}

export async function reprocessChannelReturnCandidate(candidateId: number) {
  return apiRequest<ChannelReturnCandidateActionResponse>(`/api/channels/return-candidates/${candidateId}/reprocess`, {
    method: "POST",
  });
}

export async function markChannelReturnCandidateReviewed(candidateId: number) {
  return apiRequest<ChannelReturnCandidateActionResponse>(`/api/channels/return-candidates/${candidateId}/mark-reviewed`, {
    method: "POST",
  });
}

export async function updateChannelReturnCandidateCorrection(candidateId: number, payload: ChannelReturnCandidateCorrectionPayload) {
  return apiRequest<ChannelReturnCandidateActionResponse>(`/api/channels/return-candidates/${candidateId}/correction`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function clearChannelReturnCandidateCorrection(candidateId: number) {
  return apiRequest<ChannelReturnCandidateActionResponse>(`/api/channels/return-candidates/${candidateId}/clear-correction`, {
    method: "POST",
  });
}

export async function createReturnExpectedFromChannelCandidate(candidateId: number) {
  return apiRequest<ChannelReturnExpectedCreateResponse>(
    `/api/channels/return-candidates/${candidateId}/create-return-expected`,
    {
      method: "POST",
    },
  );
}

export async function createReturnExpectedFromChannelAccount(accountId: number) {
  return apiRequest<ChannelReturnExpectedBulkCreateResponse>(
    `/api/channels/accounts/${accountId}/return-candidates/create-return-expected`,
    {
      method: "POST",
    },
  );
}
