export interface AgencySummary {
  agency_id: number;
  code: string;
  name: string;
  status: string;
  memo?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ClientSummary {
  client_id?: number;
  id?: number;
  agency_id?: number | null;
  agency_name?: string | null;
  client_code: string;
  client_name: string;
  active_yn: boolean;
  contract_type?: string | null;
  owner_type?: string | null;
  default_warehouse?: string | null;
  default_processing_site?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ClientDetail extends ClientSummary {
  business_no?: string | null;
  contact_name?: string | null;
  contact_phone?: string | null;
  contact_email?: string | null;
  use_oms?: boolean;
  use_wms?: boolean;
  use_returns?: boolean;
  use_settlement?: boolean;
  remarks?: string | null;
}

export interface ClientWarehouseAllowedActions {
  can_update?: boolean;
  can_disable?: boolean;
  can_enable?: boolean;
  can_set_default?: boolean;
}

export interface ClientWarehouseSetting {
  setting_id: number;
  agency_id?: number | null;
  client_id: number;
  client_code?: string | null;
  client_name?: string | null;
  warehouse_id: number;
  warehouse_code: string;
  warehouse_name: string;
  warehouse_type?: string | null;
  warehouse_active_yn?: boolean | null;
  usage_type: string;
  usage_type_label?: string | null;
  is_default: boolean;
  active_yn: boolean;
  allowed_actions?: ClientWarehouseAllowedActions;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ClientWarehouseOption {
  warehouse_id: number;
  warehouse_code: string;
  warehouse_name: string;
  warehouse_type?: string | null;
  active_yn: boolean;
  already_linked?: boolean;
  linked_usage_types?: string[];
  default_usage_types?: string[];
}

export interface ClientUnit {
  unit_id: number;
  agency_id?: number | null;
  client_id: number;
  client_code?: string | null;
  client_name?: string | null;
  unit_code: string;
  unit_name: string;
  unit_type?: string | null;
  default_warehouse_id?: number | null;
  default_warehouse_name?: string | null;
  return_warehouse_id?: number | null;
  return_warehouse_name?: string | null;
  active_yn: boolean;
  sort_order: number;
  memo?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ClientUnitCreatePayload {
  unit_code: string;
  unit_name: string;
  unit_type?: string | null;
  default_warehouse_id?: number | null;
  return_warehouse_id?: number | null;
  sort_order?: number;
  memo?: string | null;
}

export interface ClientUnitUpdatePayload {
  unit_code?: string;
  unit_name?: string;
  unit_type?: string | null;
  default_warehouse_id?: number | null;
  return_warehouse_id?: number | null;
  sort_order?: number;
  memo?: string | null;
}

export interface ReturnWarehouseRoute {
  route_id: number;
  agency_id?: number | null;
  client_id: number;
  client_code?: string | null;
  client_name?: string | null;
  client_unit_id?: number | null;
  client_unit_name?: string | null;
  judgment_code: string;
  warehouse_id: number;
  warehouse_code?: string | null;
  warehouse_name?: string | null;
  active_yn: boolean;
  sort_order: number;
  memo?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ReturnWarehouseRouteCreatePayload {
  client_unit_id?: number | null;
  judgment_code: string;
  warehouse_id: number;
  sort_order?: number;
  memo?: string | null;
}

export interface ReturnWarehouseRouteUpdatePayload {
  client_unit_id?: number | null;
  judgment_code?: string;
  warehouse_id?: number;
  sort_order?: number;
  memo?: string | null;
}

export interface WarehouseSummary {
  warehouse_id: number;
  warehouse_code: string;
  warehouse_name: string;
  warehouse_type?: string | null;
  active_yn: boolean;
}

export interface ClientWarehouseSettingCreatePayload {
  warehouse_id: number;
  usage_type: string;
  is_default?: boolean;
}

export interface ClientWarehouseSettingUpdatePayload {
  usage_type?: string;
}

export interface ProductSummary {
  product_id: number;
  agency_id?: number | null;
  client_id: number;
  client_name: string;
  product_code: string;
  product_name: string;
  barcode?: string | null;
  active_yn: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ProductBarcodeSummary {
  barcode_id: number;
  agency_id?: number | null;
  barcode: string;
  barcode_type: string;
  unit_qty: number;
  active_yn: boolean;
  remarks?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ProductDetail extends ProductSummary {
  specification?: string | null;
  unit_name?: string | null;
  remarks?: string | null;
  barcodes?: ProductBarcodeSummary[];
}

export interface ProductBarcodeCreatePayload {
  product_id: number;
  barcode: string;
  barcode_type: string;
  unit_qty: number;
  remarks?: string | null;
}

export interface ProductBarcodeUpdatePayload {
  barcode?: string;
  barcode_type?: string;
  unit_qty?: number;
  remarks?: string | null;
}

export interface CommonCodeGroupSummary {
  group_id: number;
  group_code: string;
  group_name: string;
  active_yn: boolean;
  description?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CommonCodeSummary {
  code_id: number;
  group_code: string;
  code_value: string;
  code_name: string;
  sort_order: number;
  active_yn: boolean;
  description?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CommonCodeGroupCreatePayload {
  group_code: string;
  group_name: string;
  description?: string | null;
}

export interface CommonCodeGroupUpdatePayload {
  group_name?: string;
  description?: string | null;
}

export interface CommonCodeCreatePayload {
  group_id: number;
  code_value: string;
  code_name: string;
  sort_order?: number;
  description?: string | null;
}

export interface CommonCodeUpdatePayload {
  code_name?: string;
  sort_order?: number;
  description?: string | null;
}
