export interface LoginRequest {
  login_id: string;
  password: string;
}

export interface LoginUserDto {
  user_id: number;
  login_id: string;
  user_name: string;
  roles: string[];
  client_id: number | null;
  agency_id: number | null;
  client_name: string | null;
  must_change_password: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  must_change_password: boolean;
  user: LoginUserDto;
  result_code: string;
  message: string;
}

export interface AuthContextResponse {
  user_id: number;
  login_id: string;
  user_name: string;
  roles: string[];
  permissions: string[];
  client_id: number | null;
  agency_id: number | null;
  client_name: string | null;
  default_warehouse_id: number | null;
  must_change_password: boolean;
  is_platform_admin: boolean;
  is_internal_user: boolean;
  is_agency_user: boolean;
  is_client_user: boolean;
  effective_client_id: number | null;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
  new_password_confirm: string;
}

export interface ChangePasswordResponse {
  success: boolean;
  result_code: string;
  message: string;
  must_change_password: boolean | null;
}
