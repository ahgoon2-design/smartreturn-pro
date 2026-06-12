import { RightOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Space, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { ApiClientError } from "../../api/client";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { useAuth } from "../../context/AuthContext";
import { SmartImportLauncher } from "../../features/import/SmartImportLauncher";
import { ROUTE_PATHS } from "../../routes/routePaths";

// RETURN_RECEPTION canonical 필드(운송장번호 필수, 상품코드/바코드 중 하나 필수) 기준 샘플.
const RECEPTION_SAMPLE_PASTE_TEXT = "운송장번호\t상품코드\t바코드\n689000000001\tPRD-001\t8800000000001";

/**
 * 고객 포털 - 반품 접수 등록.
 * Smart Import Mapper 공용 파이프라인(RETURN_RECEPTION)을 재사용하며,
 * 접수 확정은 고객 반품 접수 자료만 생성한다. 입고/판정/마감/재고 처리는 내부 단계에서 진행된다.
 * client scope는 backend가 강제하며, 화면에서 고객사 선택 UI를 제공하지 않는다.
 */
export function PortalReturnIntakePage() {
  const navigate = useNavigate();
  const { authContext, isClientUser, hasPermission } = useAuth();

  const canSubmitReturns = hasPermission("RETURN_CLIENT_SUBMIT");
  const clientLabel = authContext?.client_name || "고객사";
  // 고객 사용자는 자기 client_id로 고정한다. 내부 미리보기 사용자는 런처의 고객사 선택을 그대로 쓴다.
  const fixedClientId = isClientUser && authContext?.client_id ? authContext.client_id : undefined;

  if (!canSubmitReturns) {
    return (
      <SmartPage>
        <SmartPageHeader title="반품 접수 등록" description="반품 접수 자료를 업로드하는 화면입니다." />
        <Alert
          type="warning"
          showIcon
          message="반품 접수 등록 권한이 없습니다."
          description="현재 계정 권한으로 반품 접수 등록을 사용할 수 없습니다. 담당 관리자에게 권한을 요청해 주세요."
        />
      </SmartPage>
    );
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="반품 접수 등록"
        description={`${clientLabel}의 반품 접수 자료를 엑셀 업로드 또는 붙여넣기로 등록합니다.`}
        extra={
          <Space>
            <SmartImportLauncher
              importType="RETURN_RECEPTION"
              buttonLabel="반품 접수 업로드"
              title="반품 접수 자료 등록"
              samplePasteText={RECEPTION_SAMPLE_PASTE_TEXT}
              confirmSuccessMessage="반품 접수 자료를 등록했습니다. 센터 입고, 판정, 재고 반영은 내부 처리 단계에서 진행됩니다."
              fixedClientId={fixedClientId}
              showTemplateDownload={false}
              sourceName="portal-return-reception"
              formatErrorMessage={toPortalErrorMessage}
              formatPreviewMessage={toPortalPreviewMessage}
              useCanonicalPreviewColumns
            />
            <Button icon={<RightOutlined />} onClick={() => navigate(ROUTE_PATHS.portalReturnStatus)}>
              처리현황 보기
            </Button>
          </Space>
        }
      />

      <Alert
        type="info"
        showIcon
        message="접수 확정은 고객 반품 접수 자료만 등록합니다."
        description="센터 입고, 판정, 재고 반영은 내부 처리 단계에서 진행됩니다. 등록한 자료의 진행 상태는 반품 처리현황 화면에서 확인하세요."
      />

      <Card title="업로드 안내" size="small">
        <Space direction="vertical" size={6}>
          <Typography.Text>
            필수 컬럼: <Typography.Text strong>운송장번호</Typography.Text>,{" "}
            <Typography.Text strong>상품코드 또는 바코드</Typography.Text> (둘 중 하나)
          </Typography.Text>
          <Typography.Text type="secondary">
            주문번호, 상품명, 수량 같은 추가 컬럼은 함께 붙여넣어도 되며, 자동매핑되지 않은 컬럼은 확인 필요로 표시됩니다.
          </Typography.Text>
          <Typography.Text type="secondary">
            운송장번호 칸에 "재접수요청" 같은 메모가 들어 있으면 검증 오류로 표시될 수 있습니다. 메모는 별도 컬럼에 적어 주세요.
          </Typography.Text>
          <Typography.Text type="secondary">
            업로드한 원본 행 순서는 그대로 보존되며, 자동매핑은 추천일 뿐 확인 필요/낮은 신뢰도 항목은 직접 확인한 뒤 확정할 수 있습니다.
          </Typography.Text>
        </Space>
      </Card>

      <Card size="small">
        <Space direction="vertical" size={4}>
          <Typography.Text strong>진행 순서</Typography.Text>
          <Typography.Text type="secondary">
            1. 반품 접수 업로드 버튼 클릭 → 2. 엑셀 업로드 또는 붙여넣기 → 3. 자동매핑 결과 확인(확인 필요 항목 수정) → 4. 검증
            실행 → 5. 접수 확정 → 6. 반품 처리현황에서 진행 상태 확인
          </Typography.Text>
        </Space>
      </Card>
    </SmartPage>
  );
}

function toPortalErrorMessage(error: unknown): string | null {
  if (!(error instanceof ApiClientError)) {
    return null;
  }
  if (error.status === 401 || error.resultCode === "NOT_AUTHENTICATED" || error.resultCode === "INVALID_TOKEN") {
    return "로그인이 필요하거나 인증이 만료되었습니다. 다시 로그인해 주세요.";
  }
  if (error.resultCode === "CLIENT_SCOPE_DENIED" || error.resultCode?.includes("SCOPE")) {
    return "허용된 고객사/운영단위 범위 밖의 자료입니다. 담당 관리자에게 문의해 주세요.";
  }
  if (error.status === 403) {
    return "현재 계정 권한으로 사용할 수 없는 기능입니다. 담당 관리자에게 요청해 주세요.";
  }
  return null;
}

function toPortalPreviewMessage(message: string): string {
  const normalized = message.toLowerCase();
  if (
    message.includes("INVALID_TRACKING_NO_VALUE") ||
    normalized.includes("one of tracking_no, invoice_no is required") ||
    normalized.includes("tracking_no") ||
    normalized.includes("invoice_no") ||
    normalized.includes("waybill_no")
  ) {
    return "운송장번호가 비어 있거나 올바르지 않습니다. 운송장번호 칸에는 메모가 아니라 숫자 운송장번호를 입력해 주세요. 오류 행을 수정한 뒤 다시 검증해 주세요.";
  }
  if (normalized.includes("required") || normalized.includes("invalid") || normalized.includes("validation error")) {
    return "입력값을 확인할 수 없습니다. 오류 행을 수정한 뒤 다시 검증해 주세요.";
  }
  return message;
}
