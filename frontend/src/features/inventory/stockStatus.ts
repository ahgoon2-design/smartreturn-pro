// 재고등급(stock_status) 표시 단일 출처(표시 레이어 전용).
// 주의: 이 매핑은 화면 표시용이다. 재고 계산/반영(backend) 로직에 하드코딩하지 않는다.
// 라벨 기준은 backend CLOSING_REFLECTED_STOCK_LABELS와 의미를 맞춘다.

export type StockStatusGroup = "SELLABLE" | "DISPOSAL_PENDING";

export interface StockStatusMeta {
  code: string;
  label: string;
  group: StockStatusGroup;
  order: number;
}

// 업무 순서: 판매가능(양품 → 리퍼A·B·C → 샘플) 먼저, 처분대기(제조사반품 → 폐기) 뒤.
const STOCK_STATUS_LIST: StockStatusMeta[] = [
  { code: "GOOD", label: "정상재고", group: "SELLABLE", order: 10 },
  { code: "REFURB_A", label: "리퍼A 재고", group: "SELLABLE", order: 20 },
  { code: "REFURB_B", label: "리퍼B 재고", group: "SELLABLE", order: 30 },
  { code: "REFURB_C", label: "리퍼C 재고", group: "SELLABLE", order: 40 },
  // 레거시 등급 미지정 리퍼(표시 호환용, 신규 필터 옵션 아님)
  { code: "REFURB", label: "리퍼 재고", group: "SELLABLE", order: 45 },
  { code: "SAMPLE", label: "샘플 재고", group: "SELLABLE", order: 50 },
  { code: "MANUFACTURER_RETURN", label: "제조사반품 재고", group: "DISPOSAL_PENDING", order: 60 },
  { code: "DISPOSAL", label: "폐기 재고", group: "DISPOSAL_PENDING", order: 70 },
];

const STOCK_STATUS_MAP: Record<string, StockStatusMeta> = STOCK_STATUS_LIST.reduce(
  (acc, meta) => {
    acc[meta.code] = meta;
    return acc;
  },
  {} as Record<string, StockStatusMeta>,
);

export const GROUP_META: Record<StockStatusGroup, { label: string; tone: "success" | "warning" }> = {
  SELLABLE: { label: "판매가능", tone: "success" },
  DISPOSAL_PENDING: { label: "처분대기", tone: "warning" },
};

// 재고상태 필터 옵션: 전체 + 7등급(업무 순서). 레거시 generic REFURB는 신규 필터 옵션으로 노출하지 않는다.
export const STOCK_STATUS_FILTER_OPTIONS = [
  { value: "ALL", label: "전체 재고상태" },
  ...STOCK_STATUS_LIST.filter((meta) => meta.code !== "REFURB").map((meta) => ({
    value: meta.code,
    label: meta.label,
  })),
];

export function stockStatusLabel(code: unknown): string {
  if (code === null || code === undefined || code === "") {
    return "-";
  }
  const key = String(code);
  return STOCK_STATUS_MAP[key]?.label ?? key;
}

export function stockStatusGroup(code: unknown): StockStatusGroup | null {
  if (code === null || code === undefined) {
    return null;
  }
  return STOCK_STATUS_MAP[String(code)]?.group ?? null;
}

export function stockStatusOrder(code: unknown): number {
  if (code === null || code === undefined) {
    return 999;
  }
  return STOCK_STATUS_MAP[String(code)]?.order ?? 990;
}

export function stockStatusGroupTone(code: unknown): "success" | "warning" | "neutral" {
  const group = stockStatusGroup(code);
  return group ? GROUP_META[group].tone : "neutral";
}

export function stockStatusGroupLabel(code: unknown): string {
  const group = stockStatusGroup(code);
  return group ? GROUP_META[group].label : "-";
}
