import { apiRequest } from "./client";
import type { AuthContextResponse } from "../types/auth";

export function fetchAuthContext() {
  return apiRequest<AuthContextResponse>("/api/auth/context");
}
