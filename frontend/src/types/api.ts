export interface ApiResult<TData> {
  success: boolean;
  result_code?: string;
  message?: string;
  data?: TData;
  errors?: unknown[];
  next_action?: string | null;
}

export interface PageResponse<TItem> {
  items: TItem[];
  total_count: number;
  page: number;
  page_size: number;
}
