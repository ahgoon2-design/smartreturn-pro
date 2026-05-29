import { Tag } from "antd";

const STATUS_COLORS: Record<string, string> = {
  VALID: "green",
  WARNING: "gold",
  INVALID: "red",
  NOT_VALIDATED: "default",
  VALIDATED: "green",
  HAS_ERRORS: "red",
  READY_TO_VALIDATE: "blue",
  DRAFT: "default",
};

const STATUS_LABELS: Record<string, string> = {
  VALID: "정상",
  WARNING: "경고",
  INVALID: "오류",
  NOT_VALIDATED: "검증 전",
  VALIDATED: "검증 완료",
  HAS_ERRORS: "오류 있음",
  READY_TO_VALIDATE: "검증 대기",
  DRAFT: "작성 중",
  VALIDATING: "검증 중",
  FAILED: "실패",
};

export function SmartStatusBadge({ status }: { status?: string | null }) {
  const value = status || "DRAFT";
  return <Tag color={STATUS_COLORS[value] || "default"}>{STATUS_LABELS[value] || value}</Tag>;
}
