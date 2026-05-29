const API_BASE_STORAGE_KEY = "smartreturn.apiBaseUrl";
const TOKEN_STORAGE_KEYS = ["smartreturn.accessToken", "smartreturn_access_token", "access_token"];

export class ApiClientError extends Error {
  constructor({ resultCode, message, status, errors }) {
    super(message || resultCode || "요청 처리 중 오류가 발생했습니다.");
    this.name = "ApiClientError";
    this.resultCode = resultCode || "SERVER_ERROR";
    this.status = status || 0;
    this.errors = errors || [];
  }
}

export function getStoredApiBaseUrl() {
  return localStorage.getItem(API_BASE_STORAGE_KEY) || "";
}

export function setStoredApiBaseUrl(value) {
  const nextValue = value.trim().replace(/\/+$/, "");
  if (nextValue) {
    localStorage.setItem(API_BASE_STORAGE_KEY, nextValue);
  } else {
    localStorage.removeItem(API_BASE_STORAGE_KEY);
  }
  return nextValue;
}

export function resolveApiBaseUrl() {
  const storedBaseUrl = getStoredApiBaseUrl();
  if (storedBaseUrl) {
    return storedBaseUrl;
  }
  if (window.location.protocol === "http:" || window.location.protocol === "https:") {
    return window.location.origin;
  }
  throw new ApiClientError({
    resultCode: "API_BASE_URL_REQUIRED",
    message: "API 서버 주소를 입력해 주세요.",
  });
}

function getAccessToken() {
  for (const key of TOKEN_STORAGE_KEYS) {
    const value = localStorage.getItem(key);
    if (value) {
      return value;
    }
  }
  return "";
}

export function hasAccessToken() {
  return Boolean(getAccessToken());
}

export async function apiRequest(path, options = {}) {
  const token = getAccessToken();
  if (!token) {
    throw new ApiClientError({
      resultCode: "NOT_AUTHENTICATED",
      message: "로그인이 필요합니다. 기존 인증 화면에서 로그인한 뒤 다시 시도해 주세요.",
      status: 401,
    });
  }

  const headers = {
    Accept: "application/json",
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    Authorization: `Bearer ${token}`,
    ...(options.headers || {}),
  };

  const response = await fetch(`${resolveApiBaseUrl()}${path}`, {
    ...options,
    headers,
  });
  const payload = await response.json().catch(() => null);

  if (!response.ok || payload?.success === false) {
    throw new ApiClientError({
      resultCode: payload?.result_code || `HTTP_${response.status}`,
      message: payload?.message || "요청 처리 중 오류가 발생했습니다.",
      status: response.status,
      errors: payload?.errors || [],
    });
  }

  return payload;
}
