import { apiRequest } from "./client";
import type {
  ChannelAccount,
  ChannelAccountCreatePayload,
  ChannelAccountUpdatePayload,
  ChannelConnectionTestResponse,
  ChannelRawEventListItem,
  ChannelSyncDryRunPayload,
  ChannelSyncDryRunResponse,
  ChannelSyncJob,
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
