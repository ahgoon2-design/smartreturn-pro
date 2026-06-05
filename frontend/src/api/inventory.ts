import { apiRequest } from "./client";
import type {
  CurrentInventoryFilters,
  CurrentInventoryListResponse,
  InventoryEventFilters,
  InventoryEventListResponse,
} from "../types/inventory";

export async function listCurrentInventory(options: CurrentInventoryFilters = {}) {
  const params = new URLSearchParams();
  if (options.clientId) {
    params.set("client_id", String(options.clientId));
  }
  if (options.warehouseId) {
    params.set("warehouse_id", String(options.warehouseId));
  }
  if (options.productCode?.trim()) {
    params.set("product_code", options.productCode.trim());
  }
  if (options.barcode?.trim()) {
    params.set("barcode", options.barcode.trim());
  }
  if (options.keyword?.trim()) {
    params.set("keyword", options.keyword.trim());
  }
  if (options.stockStatus?.trim()) {
    params.set("stock_status", options.stockStatus.trim());
  }
  params.set("page", String(options.page || 1));
  params.set("page_size", String(options.pageSize || 100));
  return apiRequest<CurrentInventoryListResponse>(`/api/inventory/current?${params.toString()}`);
}

export async function listInventoryEvents(options: InventoryEventFilters = {}) {
  const params = new URLSearchParams();
  if (options.clientId) {
    params.set("client_id", String(options.clientId));
  }
  if (options.warehouseId) {
    params.set("warehouse_id", String(options.warehouseId));
  }
  if (options.productCode?.trim()) {
    params.set("product_code", options.productCode.trim());
  }
  if (options.barcode?.trim()) {
    params.set("barcode", options.barcode.trim());
  }
  if (options.keyword?.trim()) {
    params.set("keyword", options.keyword.trim());
  }
  if (options.eventType?.trim()) {
    params.set("event_type", options.eventType.trim());
  }
  if (options.sourceType?.trim()) {
    params.set("source_type", options.sourceType.trim());
  }
  if (options.dateFrom) {
    params.set("date_from", options.dateFrom);
  }
  if (options.dateTo) {
    params.set("date_to", options.dateTo);
  }
  params.set("page", String(options.page || 1));
  params.set("page_size", String(options.pageSize || 100));
  return apiRequest<InventoryEventListResponse>(`/api/inventory/events?${params.toString()}`);
}
