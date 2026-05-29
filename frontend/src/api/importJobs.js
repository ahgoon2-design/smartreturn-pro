import { apiRequest } from "../lib/apiClient.js";

export async function createImportJob(request) {
  const result = await apiRequest("/api/import-jobs", {
    method: "POST",
    body: JSON.stringify(request),
  });
  return result.data;
}

export async function savePasteRows(jobId, request) {
  const result = await apiRequest(`/api/import-jobs/${jobId}/rows/paste`, {
    method: "POST",
    body: JSON.stringify(request),
  });
  return result.data;
}

export async function validateImportJob(jobId) {
  const result = await apiRequest(`/api/import-jobs/${jobId}/validate`, {
    method: "POST",
    body: JSON.stringify({ force: false }),
  });
  return result.data;
}

export async function listImportJobRows(jobId) {
  const result = await apiRequest(`/api/import-jobs/${jobId}/rows?page=1&page_size=200`);
  return result.data || { items: [], total_count: 0 };
}

export async function listImportJobErrors(jobId) {
  const result = await apiRequest(`/api/import-jobs/${jobId}/errors?page=1&page_size=200`);
  return result.data || { items: [], total_count: 0 };
}
