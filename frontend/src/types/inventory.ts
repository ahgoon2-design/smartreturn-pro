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

export interface InventoryEventItem {
  event_id: number;
  event_no: string;
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
  event_type: string;
  source_type: string;
  source_id: number;
  source_line_id?: number | null;
  stock_status: string;
  qty: number;
  idempotency_key: string;
  event_reason?: string | null;
  memo?: string | null;
  created_at: string;
  created_by?: number | null;
}

export interface InventoryEventFilters {
  clientId?: number;
  warehouseId?: number;
  productCode?: string;
  barcode?: string;
  keyword?: string;
  eventType?: string;
  sourceType?: string;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  pageSize?: number;
}

export type InventoryEventListResponse = PageResponse<InventoryEventItem>;
