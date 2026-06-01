import { apiRequest } from "./client";
import type {
  ReturnIntakeBatchCreatePayload,
  ReturnIntakeBatchListResponse,
  ReturnIntakeBatchSummary,
  ReturnIntakePasteRowsPayload,
  ReturnIntakePasteRowsResponse,
  ReturnIntakeRowsResponse,
  ReturnIntakeValidateResponse,
} from "../types/returns";

export interface ReturnIntakeListOptions {
  clientId?: number;
  page?: number;
  pageSize?: number;
}

export async function createReturnIntakeBatch(payload: ReturnIntakeBatchCreatePayload) {
  return apiRequest<ReturnIntakeBatchSummary>("/api/returns/intake/batches", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listReturnIntakeBatches(options: ReturnIntakeListOptions = {}) {
  const params = new URLSearchParams();
  if (options.clientId) {
    params.set("client_id", String(options.clientId));
  }
  params.set("page", String(options.page || 1));
  params.set("page_size", String(options.pageSize || 50));
  return apiRequest<ReturnIntakeBatchListResponse>(`/api/returns/intake/batches?${params.toString()}`);
}

export async function getReturnIntakeBatch(batchId: number) {
  return apiRequest<ReturnIntakeBatchSummary>(`/api/returns/intake/batches/${batchId}`);
}

export async function pasteReturnIntakeRows(batchId: number, payload: ReturnIntakePasteRowsPayload) {
  return apiRequest<ReturnIntakePasteRowsResponse>(`/api/returns/intake/batches/${batchId}/rows/paste`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listReturnIntakeRows(batchId: number, options: { page?: number; pageSize?: number } = {}) {
  const params = new URLSearchParams();
  params.set("page", String(options.page || 1));
  params.set("page_size", String(options.pageSize || 200));
  return apiRequest<ReturnIntakeRowsResponse>(`/api/returns/intake/batches/${batchId}/rows?${params.toString()}`);
}

export async function validateReturnIntakeBatch(batchId: number) {
  return apiRequest<ReturnIntakeValidateResponse>(`/api/returns/intake/batches/${batchId}/validate`, {
    method: "POST",
  });
}
