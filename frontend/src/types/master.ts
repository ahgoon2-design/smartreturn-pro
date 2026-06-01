export interface ClientSummary {
  client_id?: number;
  id?: number;
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
  barcode: string;
  barcode_type: string;
  unit_qty: number;
  active_yn: boolean;
  remarks?: string | null;
}

export interface ProductDetail extends ProductSummary {
  specification?: string | null;
  unit_name?: string | null;
  remarks?: string | null;
  barcodes?: ProductBarcodeSummary[];
}
