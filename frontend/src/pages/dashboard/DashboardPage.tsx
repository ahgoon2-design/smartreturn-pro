import { CheckCircleOutlined, ExclamationCircleOutlined, ExportOutlined, RollbackOutlined, ScanOutlined } from "@ant-design/icons";
import { Button, Card, Col, Row, Space, Tag, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartSummaryCard } from "../../components/common/SmartSummaryCard";
import { ROUTE_PATHS } from "../../routes/routePaths";

export function DashboardPage() {
  const navigate = useNavigate();
  const workCards = [
    {
      title: "반품 자료",
      tag: "등록/검증",
      description: "업체 세부정보, CJ 반품 운송장, 자동수집 후보를 처리대상으로 준비합니다.",
      path: ROUTE_PATHS.returnIntake,
    },
    {
      title: "반품 처리",
      tag: "현장 작업",
      description: "운송장 스캔 또는 그리드 선택으로 상품 확인, 판정, 증빙 기록을 진행합니다.",
      path: ROUTE_PATHS.returnProcessing,
    },
    {
      title: "반품 마감",
      tag: "재고반영",
      description: "처리완료 자료를 고객사/상품/창고/판정 기준으로 확인한 뒤 일마감합니다.",
      path: ROUTE_PATHS.returnClosing,
    },
    {
      title: "반출/폐기",
      tag: "후속 처리",
      description: "제조사반출, 보류, 폐기 대상은 일마감과 분리된 후속 흐름으로 관리합니다.",
      path: ROUTE_PATHS.returnExternalOutbound,
    },
  ];

  return (
    <SmartPage>
      <SmartPageHeader
        title="오늘 작업"
        description="실무 테스트는 반품 자료 준비, 현장 처리, 일마감, 반출/폐기 순서로 진행합니다. 처리완료는 재고반영이 아니며 일마감 또는 반출/폐기 확정 후 재고에 반영됩니다."
      />

      <div className="smart-summary-grid">
        <SmartSummaryCard label="오늘 입고 예정" value="자료 확인" tone="info" />
        <SmartSummaryCard label="처리 대기" value="스캔/선택" tone="warning" />
        <SmartSummaryCard label="일마감 대기" value="수량 체크" tone="success" />
        <SmartSummaryCard label="확인 필요" value="보류/오류" tone="danger" />
      </div>

      <Row gutter={[12, 12]}>
        {workCards.map((module) => (
          <Col xs={24} md={12} xl={6} key={module.title}>
            <Card
              size="small"
              title={module.title}
              extra={<Tag color={module.tag === "후속 처리" ? "orange" : "blue"}>{module.tag}</Tag>}
            >
              <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
                {module.description}
              </Typography.Paragraph>
              <Button type="link" onClick={() => navigate(module.path)}>
                바로가기
              </Button>
            </Card>
          </Col>
        ))}
      </Row>

      <Card size="small" title="오늘 작업 상태 기준">
        <Space size={[8, 8]} wrap>
          <Tag icon={<RollbackOutlined />}>CJ 배송완료 반품</Tag>
          <Tag icon={<ScanOutlined />} color="blue">처리중</Tag>
          <Tag icon={<ExclamationCircleOutlined />} color="orange">보류/확인필요</Tag>
          <Tag icon={<CheckCircleOutlined />} color="green">일마감 대기</Tag>
          <Tag icon={<ExportOutlined />} color="purple">반출 대기</Tag>
        </Space>
      </Card>
    </SmartPage>
  );
}
