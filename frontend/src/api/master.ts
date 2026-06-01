import { apiRequest } from "./client";
import type {
  ClientDetail,
  ClientSummary,
  ClientWarehouseOption,
  ClientWarehouseSetting,
  ClientWarehouseSettingCreatePayload,
  ClientWarehouseSettingUpdatePayload,
  CommonCodeCreatePayload,
  CommonCodeGroupCreatePayload,
  CommonCodeGroupSummary,
  CommonCodeGroupUpdatePayload,
  CommonCodeSummary,
  CommonCodeUpdatePayload,
  ProductBarcodeCreatePayload,
  ProductBarcodeSummary,
  ProductBarcodeUpdatePayload,
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

export async function createProductBarcode(payload: ProductBarcodeCreatePayload) {
  return apiRequest<ProductBarcodeSummary>("/api/master/product-barcodes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateProductBarcode(barcodeId: number, payload: ProductBarcodeUpdatePayload) {
  return apiRequest<ProductBarcodeSummary>(`/api/master/product-barcodes/${barcodeId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function disableProductBarcode(barcodeId: number) {
  return apiRequest<ProductBarcodeSummary>(`/api/master/product-barcodes/${barcodeId}/disable`, {
    method: "POST",
  });
}

export async function enableProductBarcode(barcodeId: number) {
  return apiRequest<ProductBarcodeSummary>(`/api/master/product-barcodes/${barcodeId}/enable`, {
    method: "POST",
  });
}

export async function listCommonCodeGroups() {
  return apiRequest<CommonCodeGroupSummary[]>("/api/master/common-code-groups");
}

export async function createCommonCodeGroup(payload: CommonCodeGroupCreatePayload) {
  return apiRequest<CommonCodeGroupSummary>("/api/master/common-code-groups", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateCommonCodeGroup(groupId: number, payload: CommonCodeGroupUpdatePayload) {
  return apiRequest<CommonCodeGroupSummary>(`/api/master/common-code-groups/${groupId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function disableCommonCodeGroup(groupId: number) {
  return apiRequest<CommonCodeGroupSummary>(`/api/master/common-code-groups/${groupId}/disable`, {
    method: "POST",
  });
}

export async function enableCommonCodeGroup(groupId: number) {
  return apiRequest<CommonCodeGroupSummary>(`/api/master/common-code-groups/${groupId}/enable`, {
    method: "POST",
  });
}

export async function listCommonCodes(groupCode?: string) {
  const params = new URLSearchParams();
  if (groupCode) {
    params.set("group_code", groupCode);
  }
  const query = params.toString();
  return apiRequest<CommonCodeSummary[]>(`/api/master/common-codes${query ? `?${query}` : ""}`);
}

export async function createCommonCode(payload: CommonCodeCreatePayload) {
  return apiRequest<CommonCodeSummary>("/api/master/common-codes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateCommonCode(codeId: number, payload: CommonCodeUpdatePayload) {
  return apiRequest<CommonCodeSummary>(`/api/master/common-codes/${codeId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function disableCommonCode(codeId: number) {
  return apiRequest<CommonCodeSummary>(`/api/master/common-codes/${codeId}/disable`, {
    method: "POST",
  });
}

export async function enableCommonCode(codeId: number) {
  return apiRequest<CommonCodeSummary>(`/api/master/common-codes/${codeId}/enable`, {
    method: "POST",
  });
}
