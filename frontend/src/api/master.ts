import { apiRequest } from "./client";
import type {
  ClientDetail,
  ClientSummary,
  ClientWarehouseOption,
  ClientWarehouseSetting,
  ClientWarehouseSettingCreatePayload,
  ClientWarehouseSettingUpdatePayload,
  ProductDetail,
  ProductSummary,
} from "../types/master";
import type { PageResponse } from "../types/api";

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

export interface ProductListOptions {
  clientId?: number;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

export async function listProducts(options: ProductListOptions = {}) {
  const params = new URLSearchParams();
  if (options.clientId) {
    params.set("client_id", String(options.clientId));
  }
  if (options.keyword?.trim()) {
    params.set("keyword", options.keyword.trim());
  }
  params.set("page", String(options.page || 1));
  params.set("page_size", String(options.pageSize || 50));
  const query = params.toString();
  return apiRequest<PageResponse<ProductSummary>>(`/api/master/products${query ? `?${query}` : ""}`);
}

export async function getProduct(productId: number) {
  return apiRequest<ProductDetail | null>(`/api/master/products/${productId}`);
}
