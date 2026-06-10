import type { ApiResult } from "../types/api";

const PRIMARY_TOKEN_STORAGE_KEY = "smartreturn.pro.accessToken";
const TOKEN_STORAGE_KEYS = [PRIMARY_TOKEN_STORAGE_KEY, "smartreturn.accessToken", "smartreturn_access_token", "access_token"];

type UnauthorizedHandler = () => void;

let unauthorizedHandler: UnauthorizedHandler | null = null;

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

interface ApiRequestConfig {
  auth?: boolean;
  unwrapApiResult?: boolean;
}

export function resolveApiBaseUrl() {
  const fromEnv = import.meta.env.VITE_API_BASE_URL?.trim().replace(/\/+$/, "");
  if (fromEnv) {
    return fromEnv;
  }
  // 로컬 개발 기본값이다. 실제 환경 값은 Vite 환경변수로 주입하며, 비밀값은 코드에 쓰지 않는다.
  return "http://127.0.0.1:8000";
}

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  unauthorizedHandler = handler;
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

export function setStoredAccessToken(token: string) {
  clearStoredAccessToken();
  localStorage.setItem(PRIMARY_TOKEN_STORAGE_KEY, token);
}

export function clearStoredAccessToken() {
  TOKEN_STORAGE_KEYS.forEach((key) => localStorage.removeItem(key));
}

export async function apiRequest<TData>(path: string, options: RequestInit = {}, config: ApiRequestConfig = {}) {
  const auth = config.auth ?? true;
  const unwrapApiResult = config.unwrapApiResult ?? true;
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (auth) {
    const token = getStoredAccessToken();
    if (!token) {
      throw new ApiClientError({
        resultCode: "NOT_AUTHENTICATED",
        message: "로그인이 필요합니다.",
        status: 401,
      });
    }
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${resolveApiBaseUrl()}${path}`, {
    ...options,
    headers,
  });
  const payload = (await response.json().catch(() => null)) as ApiResult<TData> | TData | null;
  const apiResult = isApiResult<TData>(payload) ? payload : null;

  if (!response.ok || apiResult?.success === false) {
    const resultCode = apiResult?.result_code || `HTTP_${response.status}`;
    const error = new ApiClientError({
      resultCode,
      message: apiResult?.message || toDefaultErrorMessage(response.status),
      status: response.status,
      errors: apiResult?.errors || [],
    });
    if (isUnauthorizedError(error)) {
      clearStoredAccessToken();
      unauthorizedHandler?.();
    }
    throw error;
  }

  if (unwrapApiResult && apiResult) {
    return apiResult.data as TData;
  }

  return payload as TData;
}

function isApiResult<TData>(payload: ApiResult<TData> | TData | null): payload is ApiResult<TData> {
  return Boolean(
    payload &&
      typeof payload === "object" &&
      "success" in payload &&
      ("data" in payload || "errors" in payload || "warnings" in payload || "next_action" in payload),
  );
}

function isUnauthorizedError(error: ApiClientError) {
  return error.status === 401 || error.resultCode === "INVALID_TOKEN" || error.resultCode === "NOT_AUTHENTICATED";
}

function toDefaultErrorMessage(status: number) {
  if (status === 401) {
    return "로그인이 필요하거나 인증이 만료되었습니다.";
  }
  if (status === 403) {
    return "접근 권한이 없습니다.";
  }
  if (status === 422) {
    return "입력값을 다시 확인해 주세요.";
  }
  if (status >= 500) {
    return "서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
  }
  return "요청 처리 중 오류가 발생했습니다.";
}
