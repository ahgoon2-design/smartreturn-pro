import { apiRequest } from "./client";
import type {
  JudgeReturnProcessingTaskPayload,
  JudgeReturnProcessingTaskResponse,
  ReturnClosingCandidateListResponse,
  ReturnClosingConfirmPayload,
  ReturnClosingConfirmResponse,
  ReturnExternalOutboundCandidateListResponse,
  ReturnExternalOutboundConfirmPayload,
  ReturnExternalOutboundConfirmResponse,
  ReturnIntakeBatchCreatePayload,
  ReturnIntakeBatchListResponse,
  ReturnIntakeBatchSummary,
  ReturnIntakePasteRowsPayload,
  ReturnIntakePasteRowsResponse,
  ReturnIntakePrepareProcessingResponse,
  ReturnIntakeRowsResponse,
  ReturnIntakeValidateResponse,
  ReturnProcessingAttachmentListResponse,
  ReturnProcessingTaskListResponse,
  UploadReturnProcessingAttachmentPayload,
  UploadReturnProcessingAttachmentResponse,
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

export async function prepareReturnIntakeBatchForProcessing(batchId: number) {
  return apiRequest<ReturnIntakePrepareProcessingResponse>(
    `/api/returns/intake/batches/${batchId}/prepare-processing`,
    {
      method: "POST",
    },
  );
}

export interface ReturnProcessingTaskListOptions {
  clientId?: number;
  batchId?: number;
  trackingNo?: string;
  status?: string;
  page?: number;
  pageSize?: number;
}

export async function listReturnProcessingTasks(options: ReturnProcessingTaskListOptions = {}) {
  const params = new URLSearchParams();
  if (options.clientId) {
    params.set("client_id", String(options.clientId));
  }
  if (options.batchId) {
    params.set("batch_id", String(options.batchId));
  }
  if (options.trackingNo) {
    params.set("tracking_no", options.trackingNo);
  }
  if (options.status) {
    params.set("status", options.status);
  }
  params.set("page", String(options.page || 1));
  params.set("page_size", String(options.pageSize || 100));
  return apiRequest<ReturnProcessingTaskListResponse>(`/api/returns/processing/tasks?${params.toString()}`);
}

export async function judgeReturnProcessingTask(taskId: number, payload: JudgeReturnProcessingTaskPayload) {
  return apiRequest<JudgeReturnProcessingTaskResponse>(`/api/returns/processing/tasks/${taskId}/judge`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function uploadReturnProcessingAttachment(
  taskId: number,
  file: File,
  payload: UploadReturnProcessingAttachmentPayload = {},
) {
  const formData = new FormData();
  formData.append("file", file);
  if (payload.attachment_type) {
    formData.append("attachment_type", payload.attachment_type);
  }
  if (payload.note) {
    formData.append("note", payload.note);
  }
  return apiRequest<UploadReturnProcessingAttachmentResponse>(`/api/returns/processing/tasks/${taskId}/attachments`, {
    method: "POST",
    body: formData,
  });
}

export async function listReturnProcessingAttachments(taskId: number, options: { includeInactive?: boolean } = {}) {
  const params = new URLSearchParams();
  if (options.includeInactive) {
    params.set("include_inactive", "true");
  }
  const query = params.toString();
  return apiRequest<ReturnProcessingAttachmentListResponse>(
    `/api/returns/processing/tasks/${taskId}/attachments${query ? `?${query}` : ""}`,
  );
}

export async function disableReturnProcessingAttachment(taskId: number, attachmentId: number) {
  return apiRequest<UploadReturnProcessingAttachmentResponse>(
    `/api/returns/processing/tasks/${taskId}/attachments/${attachmentId}/disable`,
    {
      method: "POST",
    },
  );
}

export interface ReturnClosingCandidateListOptions {
  clientId?: number;
  judgementStatus?: string;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  pageSize?: number;
}

export async function listReturnClosingCandidates(options: ReturnClosingCandidateListOptions = {}) {
  const params = new URLSearchParams();
  if (options.clientId) {
    params.set("client_id", String(options.clientId));
  }
  if (options.judgementStatus) {
    params.set("judgement_status", options.judgementStatus);
  }
  if (options.dateFrom) {
    params.set("date_from", options.dateFrom);
  }
  if (options.dateTo) {
    params.set("date_to", options.dateTo);
  }
  params.set("page", String(options.page || 1));
  params.set("page_size", String(options.pageSize || 100));
  return apiRequest<ReturnClosingCandidateListResponse>(`/api/returns/closing/candidates?${params.toString()}`);
}

export async function confirmReturnClosing(payload: ReturnClosingConfirmPayload) {
  return apiRequest<ReturnClosingConfirmResponse>("/api/returns/closing/confirm", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface ReturnExternalOutboundCandidateListOptions {
  clientId?: number;
  judgementStatus?: string;
  dateFrom?: string;
  dateTo?: string;
  returnManagementNo?: string;
  page?: number;
  pageSize?: number;
}

export async function listReturnExternalOutboundCandidates(
  options: ReturnExternalOutboundCandidateListOptions = {},
) {
  const params = new URLSearchParams();
  if (options.clientId) {
    params.set("client_id", String(options.clientId));
  }
  if (options.judgementStatus) {
    params.set("judgement_status", options.judgementStatus);
  }
  if (options.dateFrom) {
    params.set("date_from", options.dateFrom);
  }
  if (options.dateTo) {
    params.set("date_to", options.dateTo);
  }
  if (options.returnManagementNo) {
    params.set("return_management_no", options.returnManagementNo);
  }
  params.set("page", String(options.page || 1));
  params.set("page_size", String(options.pageSize || 100));
  return apiRequest<ReturnExternalOutboundCandidateListResponse>(
    `/api/returns/external-outbound/candidates?${params.toString()}`,
  );
}

export async function confirmReturnExternalOutbound(payload: ReturnExternalOutboundConfirmPayload) {
  return apiRequest<ReturnExternalOutboundConfirmResponse>("/api/returns/external-outbound/confirm", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
