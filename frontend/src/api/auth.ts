import { apiRequest } from "./client";
import type { AuthContextResponse, ChangePasswordRequest, ChangePasswordResponse, LoginRequest, LoginResponse } from "../types/auth";

export function login(request: LoginRequest) {
  return apiRequest<LoginResponse>(
    "/api/auth/login",
    {
      method: "POST",
      body: JSON.stringify(request),
    },
    { auth: false, unwrapApiResult: false },
  );
}

export function fetchAuthContext() {
  return apiRequest<AuthContextResponse>("/api/auth/context", {}, { unwrapApiResult: false });
}

export function changePassword(request: ChangePasswordRequest) {
  return apiRequest<ChangePasswordResponse>(
    "/api/auth/password/change",
    {
      method: "POST",
      body: JSON.stringify(request),
    },
    { unwrapApiResult: false },
  );
}
