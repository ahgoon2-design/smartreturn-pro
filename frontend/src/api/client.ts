import type { ApiResult } from "../types/api";

const TOKEN_STORAGE_KEYS = ["smartreturn.accessToken", "smartreturn_access_token", "access_token"];

export class ApiClientError extends Error {
  resultCode: string;
  status: number;
  errors: unknown[];

  constructor(params: { resultCode?: string; message?: string; status?: number; errors?: unknown[] }) {
    super(params.message || params.resultCode || "요청 처리 중 오류가 발생했습니다.");
    this.name = "ApiClientError";
    this.resultCode = params.resultCode || "SERVER_ERROR";
    this.status = params.status || 0;
    this.errors = params.errors || [];
  }
}

export function resolveApiBaseUrl() {
  const fromEnv = import.meta.env.VITE_API_BASE_URL?.trim().replace(/\/+$/, "");
  if (fromEnv) {
    return fromEnv;
  }
  // Vite 개발 서버는 5173, FastAPI 로컬 서버는 8000을 기본으로 쓴다. 배포 환경에서는 VITE_API_BASE_URL로 덮어쓴다.
  return "http://127.0.0.1:8000";
}

export function getStoredAccessToken() {
  for (const key of TOKEN_STORAGE_KEYS) {
    const value = localStorage.getItem(key);
    if (value) {
      return value;
    }
  }
  return "";
}

export function hasStoredAccessToken() {
  return Boolean(getStoredAccessToken());
}

export function clearStoredAccessToken() {
  TOKEN_STORAGE_KEYS.forEach((key) => localStorage.removeItem(key));
}

export async function apiRequest<TData>(path: string, options: RequestInit = {}) {
  const token = getStoredAccessToken();
  if (!token) {
    throw new ApiClientError({
      resultCode: "NOT_AUTHENTICATED",
      message: "로그인이 필요합니다. 기존 인증 화면에서 로그인한 뒤 다시 시도해 주세요.",
      status: 401,
    });
  }

  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${resolveApiBaseUrl()}${path}`, {
    ...options,
    headers,
  });
  const payload = (await response.json().catch(() => null)) as ApiResult<TData> | null;

  if (!response.ok || payload?.success === false) {
    throw new ApiClientError({
      resultCode: payload?.result_code || `HTTP_${response.status}`,
      message: payload?.message || "요청 처리 중 오류가 발생했습니다.",
      status: response.status,
      errors: payload?.errors || [],
    });
  }

  return payload?.data as TData;
}
