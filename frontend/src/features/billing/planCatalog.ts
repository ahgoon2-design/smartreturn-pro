/**
 * 스마트리턴프로 플랜/요금제 카탈로그 (1차: 프론트 상수).
 *
 * NOTE: 지금은 프론트 상수지만, 추후 DB 기반 `plan_limits` / `subscriptions` API로
 * 옮길 수 있도록 화면 파일과 분리해 구조화한다. 실제 backend plan enforcement와
 * 결제/청구 로직은 이번 작업 범위가 아니며 다음 작업에서 plan_limits 기반으로 구현한다.
 */

export type PlanTierId = "basic" | "pro" | "ultra" | "enterprise";

/** 기능 제공 수준. 표/배지 색상 매핑의 기준이 된다. */
export type FeatureLevel = "included" | "advanced" | "limited" | "locked" | "consult";

export interface PlanTier {
  id: PlanTierId;
  name: string;
  tagline: string;
  /** 월 기본료(원). null이면 별도 협의(Enterprise). */
  monthlyPrice: number | null;
  priceNote?: string;
  badge?: { text: string; tone: "recommend" | "agency" };
  cta: { label: string; kind: "upgrade" | "consult" };
  highlights: string[];
}

export interface PlanMetricRow {
  label: string;
  values: Record<PlanTierId, string>;
}

export interface PlanFeatureRow {
  label: string;
  values: Record<PlanTierId, { level: FeatureLevel; text: string }>;
}

export interface AddonRow {
  item: string;
  basis: string;
  price: string;
}

export const PLAN_TIER_ORDER: PlanTierId[] = ["basic", "pro", "ultra", "enterprise"];

export const PLAN_TIERS: PlanTier[] = [
  {
    id: "basic",
    name: "Basic",
    tagline: "단일 창고·단일 고객사로 시작하는 소규모 셀러용",
    monthlyPrice: 99_000,
    cta: { label: "업그레이드 문의", kind: "upgrade" },
    highlights: ["활성 SKU 500개", "월 반품 1,000건", "사용자 3명", "사진 보관 30일"],
  },
  {
    id: "pro",
    name: "Pro",
    tagline: "여러 고객사·팀을 운영하는 성장 단계 셀러용",
    monthlyPrice: 299_000,
    badge: { text: "추천", tone: "recommend" },
    cta: { label: "업그레이드 문의", kind: "upgrade" },
    highlights: ["활성 SKU 5,000개", "월 반품 10,000건", "API 연동 3개", "사진 보관 180일"],
  },
  {
    id: "ultra",
    name: "Ultra",
    tagline: "대량 반품을 대행 처리하는 대리점·3PL 운영용",
    monthlyPrice: 990_000,
    badge: { text: "대리점/3PL 추천", tone: "agency" },
    cta: { label: "업그레이드 문의", kind: "upgrade" },
    highlights: ["활성 SKU 50,000개", "월 반품 100,000건", "API 연동 10개", "우선 지원"],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    tagline: "전용 SLA·정산·보고서가 필요한 대형 운영용",
    monthlyPrice: null,
    priceNote: "별도 협의",
    cta: { label: "상담 문의", kind: "consult" },
    highlights: ["한도 전체 협의", "전용 지원/SLA", "전용 정산/보고서", "데이터 마이그레이션"],
  },
];

/** 플랜별 한도(수치) 비교. */
export const PLAN_METRIC_ROWS: PlanMetricRow[] = [
  { label: "활성 SKU", values: { basic: "500개", pro: "5,000개", ultra: "50,000개", enterprise: "협의" } },
  { label: "월 반품 처리", values: { basic: "1,000건", pro: "10,000건", ultra: "100,000건", enterprise: "협의" } },
  { label: "사용자", values: { basic: "3명", pro: "10명", ultra: "50명", enterprise: "협의" } },
  { label: "고객사(client)", values: { basic: "1개", pro: "3개", ultra: "20개", enterprise: "협의" } },
  { label: "팀(client_unit)", values: { basic: "1개", pro: "5개", ultra: "50개", enterprise: "협의" } },
  { label: "창고", values: { basic: "1개", pro: "3개", ultra: "10개", enterprise: "협의" } },
  { label: "로케이션/bin", values: { basic: "100개", pro: "2,000개", ultra: "20,000개", enterprise: "협의" } },
  { label: "API 연동", values: { basic: "미지원", pro: "3개", ultra: "10개", enterprise: "협의" } },
  { label: "사진 보관", values: { basic: "30일", pro: "180일", ultra: "365일", enterprise: "협의" } },
];

/** 플랜별 기능 제공 수준 비교. */
export const PLAN_FEATURE_ROWS: PlanFeatureRow[] = [
  {
    label: "엑셀 업로드",
    values: {
      basic: { level: "included", text: "지원" },
      pro: { level: "included", text: "지원" },
      ultra: { level: "included", text: "지원" },
      enterprise: { level: "consult", text: "협의" },
    },
  },
  {
    label: "구글시트",
    values: {
      basic: { level: "limited", text: "제한" },
      pro: { level: "included", text: "지원" },
      ultra: { level: "advanced", text: "대량 지원" },
      enterprise: { level: "consult", text: "협의" },
    },
  },
  {
    label: "세트/구성품",
    values: {
      basic: { level: "locked", text: "잠금" },
      pro: { level: "included", text: "기본" },
      ultra: { level: "advanced", text: "고급" },
      enterprise: { level: "consult", text: "협의" },
    },
  },
  {
    label: "부품적출",
    values: {
      basic: { level: "locked", text: "잠금" },
      pro: { level: "included", text: "지원" },
      ultra: { level: "advanced", text: "고급" },
      enterprise: { level: "consult", text: "협의" },
    },
  },
  {
    label: "월마감/정산",
    values: {
      basic: { level: "limited", text: "제한" },
      pro: { level: "included", text: "기본" },
      ultra: { level: "advanced", text: "고급" },
      enterprise: { level: "consult", text: "협의" },
    },
  },
  {
    label: "순환실사",
    values: {
      basic: { level: "locked", text: "잠금" },
      pro: { level: "limited", text: "제한" },
      ultra: { level: "included", text: "지원" },
      enterprise: { level: "consult", text: "협의" },
    },
  },
  {
    label: "AI 보조",
    values: {
      basic: { level: "locked", text: "잠금" },
      pro: { level: "limited", text: "제한" },
      ultra: { level: "included", text: "지원" },
      enterprise: { level: "consult", text: "협의" },
    },
  },
  {
    label: "지원",
    values: {
      basic: { level: "included", text: "이메일" },
      pro: { level: "included", text: "이메일/채팅" },
      ultra: { level: "advanced", text: "우선 지원" },
      enterprise: { level: "advanced", text: "전용 지원/SLA" },
    },
  },
];

/** 추가 과금표(표시 전용, 실제 청구 로직 미연결). */
export const ADDON_ROWS: AddonRow[] = [
  { item: "활성 SKU 추가", basis: "1,000 SKU당", price: "월 20,000원" },
  { item: "월 반품 처리량 추가", basis: "1,000건당", price: "월 30,000원" },
  { item: "사용자 추가", basis: "1명당", price: "월 10,000원" },
  { item: "고객사(client) 추가", basis: "1개당", price: "월 50,000원" },
  { item: "팀(client_unit) 추가", basis: "5개당", price: "월 20,000원" },
  { item: "창고 추가", basis: "1개당", price: "월 50,000원" },
  { item: "로케이션 추가", basis: "1,000개당", price: "월 20,000원" },
  { item: "API 연동 추가", basis: "1개당", price: "월 50,000원" },
  { item: "API 호출량 추가", basis: "10,000 calls당", price: "월 20,000원" },
  { item: "사진 보관 추가", basis: "100GB당", price: "월 20,000원" },
  { item: "동영상 보관", basis: "100GB당", price: "월 30,000원" },
  { item: "커스텀 보고서", basis: "1개당", price: "100,000원부터" },
  { item: "초기 세팅 지원", basis: "1회", price: "300,000원부터" },
  { item: "API 연동 구축", basis: "프로젝트", price: "별도 견적" },
  { item: "데이터 마이그레이션", basis: "프로젝트", price: "별도 견적" },
];

const PRICE_FORMATTER = new Intl.NumberFormat("ko-KR");

/** 월/연 결제 주기에 따른 표시용 가격 정보를 만든다(UI 전용, 결제 미연결). */
export function formatPlanPrice(plan: PlanTier, cycle: "monthly" | "yearly"): { primary: string; note?: string } {
  if (plan.monthlyPrice === null) {
    return { primary: plan.priceNote ?? "별도 협의" };
  }
  if (cycle === "yearly") {
    // 연간 결제 시 2개월분 할인(월 기본료 x 10)으로 가정한 표시값이다.
    const yearly = plan.monthlyPrice * 10;
    const monthlyEquivalent = Math.round(yearly / 12);
    return {
      primary: `₩${PRICE_FORMATTER.format(yearly)} / 년`,
      note: `월 환산 약 ₩${PRICE_FORMATTER.format(monthlyEquivalent)} · 2개월 할인`,
    };
  }
  return { primary: `₩${PRICE_FORMATTER.format(plan.monthlyPrice)} / 월` };
}
