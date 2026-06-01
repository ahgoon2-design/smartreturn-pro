import { apiRequest } from "./client";
import type {
  ImportConfirmResponse,
  ImportJob,
  ImportJobCreateRequest,
  ImportExcelUploadResponse,
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

export function uploadImportExcelFile(jobId: number, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest<ImportExcelUploadResponse>(`/api/import-jobs/${jobId}/files/excel`, {
    method: "POST",
    body: formData,
  });
}

export function validateImportJob(jobId: number) {
  return apiRequest<ImportValidationRunResponse>(`/api/import-jobs/${jobId}/validate`, {
    method: "POST",
    body: JSON.stringify({ force: false }),
  });
}

export function confirmImportJob(jobId: number) {
  return apiRequest<ImportConfirmResponse>(`/api/import-jobs/${jobId}/confirm`, {
    method: "POST",
  });
}

export function listImportJobRows(jobId: number) {
  return apiRequest<ImportJobRowsResponse>(`/api/import-jobs/${jobId}/rows?page=1&page_size=200`);
}

export function listImportJobErrors(jobId: number) {
  return apiRequest<ImportJobErrorsResponse>(`/api/import-jobs/${jobId}/errors?page=1&page_size=200`);
}
