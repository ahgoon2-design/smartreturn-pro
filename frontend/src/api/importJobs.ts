import { apiRequest } from "./client";
import type {
  ImportJob,
  ImportJobCreateRequest,
  ImportJobErrorsResponse,
  ImportJobRowsResponse,
  ImportPasteRowsRequest,
  ImportValidationRunResponse,
} from "../types/import";

export function createImportJob(request: ImportJobCreateRequest) {
  return apiRequest<ImportJob>("/api/import-jobs", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function savePasteRows(jobId: number, request: ImportPasteRowsRequest) {
  return apiRequest<ImportValidationRunResponse | ImportJob>(`/api/import-jobs/${jobId}/rows/paste`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function validateImportJob(jobId: number) {
  return apiRequest<ImportValidationRunResponse>(`/api/import-jobs/${jobId}/validate`, {
    method: "POST",
    body: JSON.stringify({ force: false }),
  });
}

export function listImportJobRows(jobId: number) {
  return apiRequest<ImportJobRowsResponse>(`/api/import-jobs/${jobId}/rows?page=1&page_size=200`);
}

export function listImportJobErrors(jobId: number) {
  return apiRequest<ImportJobErrorsResponse>(`/api/import-jobs/${jobId}/errors?page=1&page_size=200`);
}
