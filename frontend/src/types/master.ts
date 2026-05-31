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
