import { apiRequest } from "./client";
import type {
  ClientDetail,
  ClientSummary,
  ClientWarehouseOption,
  ClientWarehouseSetting,
  ClientWarehouseSettingCreatePayload,
  ClientWarehouseSettingUpdatePayload,
} from "../types/master";

export async function listClients() {
  const data = await apiRequest<ClientSummary[] | { items?: ClientSummary[] }>("/api/master/clients");
  return Array.isArray(data) ? data : data.items || [];
}

export async function getClient(clientId: number) {
  return apiRequest<ClientDetail | null>(`/api/master/clients/${clientId}`);
}

export async function listClientWarehouseSettings(clientId: number, options: { includeInactive?: boolean } = {}) {
  const query = options.includeInactive ? "?include_inactive=true" : "";
  return apiRequest<ClientWarehouseSetting[]>(`/api/master/clients/${clientId}/warehouse-settings${query}`);
}

export async function listClientWarehouseOptions(clientId: number, options: { includeInactive?: boolean } = {}) {
  const query = options.includeInactive ? "?include_inactive=true" : "";
  return apiRequest<ClientWarehouseOption[]>(`/api/master/clients/${clientId}/warehouse-options${query}`);
}

export async function createClientWarehouseSetting(clientId: number, payload: ClientWarehouseSettingCreatePayload) {
  return apiRequest<ClientWarehouseSetting>(`/api/master/clients/${clientId}/warehouse-settings`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateClientWarehouseSetting(clientId: number, settingId: number, payload: ClientWarehouseSettingUpdatePayload) {
  return apiRequest<ClientWarehouseSetting>(`/api/master/clients/${clientId}/warehouse-settings/${settingId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function disableClientWarehouseSetting(clientId: number, settingId: number) {
  return apiRequest<ClientWarehouseSetting>(`/api/master/clients/${clientId}/warehouse-settings/${settingId}/disable`, {
    method: "POST",
  });
}

export async function enableClientWarehouseSetting(clientId: number, settingId: number) {
  return apiRequest<ClientWarehouseSetting>(`/api/master/clients/${clientId}/warehouse-settings/${settingId}/enable`, {
    method: "POST",
  });
}

export async function setDefaultClientWarehouseSetting(clientId: number, settingId: number) {
  return apiRequest<ClientWarehouseSetting>(`/api/master/clients/${clientId}/warehouse-settings/${settingId}/set-default`, {
    method: "POST",
  });
}
