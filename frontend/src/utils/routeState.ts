export type SearchParamValue = string | number | boolean | null | undefined;

export function getSearchString(params: URLSearchParams, key: string, fallback = "") {
  return params.get(key) ?? fallback;
}

export function getSearchNumber(params: URLSearchParams, key: string) {
  const value = params.get(key);
  if (!value) {
    return undefined;
  }
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : undefined;
}

export function getSearchBoolean(params: URLSearchParams, key: string, fallback = false) {
  const value = params.get(key);
  if (value === null) {
    return fallback;
  }
  return value === "1" || value.toLowerCase() === "true";
}

export function mergeSearchParams(current: URLSearchParams, updates: Record<string, SearchParamValue>) {
  const next = new URLSearchParams(current);
  Object.entries(updates).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "" || value === false) {
      next.delete(key);
      return;
    }
    next.set(key, value === true ? "1" : String(value));
  });
  return next;
}
