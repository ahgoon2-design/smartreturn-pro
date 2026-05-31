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
