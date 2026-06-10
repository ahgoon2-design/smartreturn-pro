import { apiRequest, getStoredAccessToken, resolveApiBaseUrl } from "./client";
import type {
  ImportConfirmResponse,
  ImportMappingProfilesResponse,
  ImportMappingResponse,
  ImportJob,
  ImportJobCreateRequest,
  ImportExcelUploadResponse,
  ImportJobErrorsResponse,
  ImportJobRowsResponse,
  ImportPasteRowsRequest,
  ImportPasteRowsResponse,
  ImportSourceTypeFieldsResponse,
  ImportSourceTypesResponse,
  ImportValidationRunResponse,
} from "../types/import";

export function createImportJob(request: ImportJobCreateRequest) {
  return apiRequest<ImportJob>("/api/import-jobs", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function savePasteRows(jobId: number, request: ImportPasteRowsRequest) {
  return apiRequest<ImportPasteRowsResponse>(`/api/import-jobs/${jobId}/rows/paste`, {
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

export function listImportSourceTypes() {
  return apiRequest<ImportSourceTypesResponse>("/api/import-jobs/source-types");
}

export function getImportSourceTypeFields(importType: string) {
  return apiRequest<ImportSourceTypeFieldsResponse>(`/api/import-jobs/source-types/${encodeURIComponent(importType)}/fields`);
}

export function autoMapImportJob(jobId: number, options: { saveProfile?: boolean; profileName?: string } = {}) {
  return apiRequest<ImportMappingResponse>(`/api/import-jobs/${jobId}/auto-map`, {
    method: "POST",
    body: JSON.stringify({
      save_profile: Boolean(options.saveProfile),
      profile_name: options.profileName || undefined,
    }),
  });
}

export function applyImportJobMapping(
  jobId: number,
  request: { mappingJson: Record<string, string>; saveProfile?: boolean; profileName?: string },
) {
  return apiRequest<ImportMappingResponse>(`/api/import-jobs/${jobId}/mapping`, {
    method: "PUT",
    body: JSON.stringify({
      mapping_json: request.mappingJson,
      save_profile: Boolean(request.saveProfile),
      profile_name: request.profileName || undefined,
    }),
  });
}

export function listImportMappingProfiles(filters: { clientId?: number; importType?: string; sourceType?: string } = {}) {
  const params = new URLSearchParams();
  if (filters.clientId) {
    params.set("client_id", String(filters.clientId));
  }
  if (filters.importType) {
    params.set("import_type", filters.importType);
  }
  if (filters.sourceType) {
    params.set("source_type", filters.sourceType);
  }
  const query = params.toString();
  return apiRequest<ImportMappingProfilesResponse>(`/api/import-jobs/mapping-profiles${query ? `?${query}` : ""}`);
}

export async function downloadImportTemplate(importType: string) {
  const token = getStoredAccessToken();
  const response = await fetch(`${resolveApiBaseUrl()}/api/import-jobs/templates/${encodeURIComponent(importType)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error("양식 다운로드에 실패했습니다.");
  }
  return response.blob();
}

export function listImportJobRows(jobId: number) {
  return apiRequest<ImportJobRowsResponse>(`/api/import-jobs/${jobId}/rows?page=1&page_size=200`);
}

export function listImportJobErrors(jobId: number) {
  return apiRequest<ImportJobErrorsResponse>(`/api/import-jobs/${jobId}/errors?page=1&page_size=200`);
}
