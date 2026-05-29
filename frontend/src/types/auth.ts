export interface AuthContextResponse {
  user_id?: number;
  username?: string;
  role: string;
  permissions?: string[];
  permissions_count?: number;
  is_internal_user?: boolean;
  must_change_password?: boolean;
  client_id?: number | null;
}
