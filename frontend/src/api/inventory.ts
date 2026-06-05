import { apiRequest } from "./client";
import type { CurrentInventoryFilters, CurrentInventoryListResponse } from "../types/inventory";

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
