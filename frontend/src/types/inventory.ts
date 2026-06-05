import type { PageResponse } from "./api";

export interface CurrentInventoryItem {
  inventory_id: number;
  client_id: number;
  client_code?: string | null;
  client_name?: string | null;
  warehouse_id: number;
  warehouse_code?: string | null;
  warehouse_name?: string | null;
  product_id: number;
  product_code?: string | null;
  product_name?: string | null;
  barcode?: string | null;
  stock_status: string;
  qty: number;
  updated_at?: string | null;
}

export interface CurrentInventoryFilters {
  clientId?: number;
  warehouseId?: number;
  productCode?: string;
  barcode?: string;
  keyword?: string;
  stockStatus?: string;
  page?: number;
  pageSize?: number;
}

export type CurrentInventoryListResponse = PageResponse<CurrentInventoryItem>;
