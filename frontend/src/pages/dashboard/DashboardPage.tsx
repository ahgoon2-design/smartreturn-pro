import { Card, Col, Row, Space, Tag, Typography } from "antd";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartSummaryCard } from "../../components/common/SmartSummaryCard";

export function DashboardPage() {
  const modules = [
    {
      title: "OMS 관리",
      tag: "준비중",
      description: "주문관리, 출고지시, 피킹리스트, 출고검수를 연결할 운영 영역입니다.",
    },
    {
      title: "WMS 관리",
      tag: "일부 연결",
      description: "재고현황과 재고 이벤트를 기준으로 입고, 이동, 조정 흐름을 확장합니다.",
    },
    {
      title: "반품 관리",
      tag: "1차 흐름",
      description: "반품접수, 팀배정, 처리, 일마감, 외부반출, 보류, 폐기, 이력조회까지 확인합니다.",
    },
    {
      title: "기준 정보",
      tag: "운영 기준",
      description: "고객사, 상품/바코드, 창고, 운영단위/팀, 판정별 창고 라우팅을 관리합니다.",
    },
  ];

  return (
    <SmartPage>
      <SmartPageHeader
        title="SmartReturn Pro 대시보드"
        description="반품 전문성을 중심에 두되 OMS, WMS, 기준정보를 함께 운영하는 통합 플랫폼 홈입니다."
      />

      <div className="smart-summary-grid">
        <SmartSummaryCard label="반품 처리" value="접수 → 판정 → 후속" />
        <SmartSummaryCard label="재고 기준" value="current_inventory" />
        <SmartSummaryCard label="운영 단위" value="고객사 + 팀" />
        <SmartSummaryCard label="화면 성격" value="운영 허브" />
      </div>

      <Row gutter={[12, 12]}>
        {modules.map((module) => (
          <Col xs={24} md={12} xl={6} key={module.title}>
            <Card size="small" title={module.title} extra={<Tag color="blue">{module.tag}</Tag>}>
              <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
                {module.description}
              </Typography.Paragraph>
            </Card>
          </Col>
        ))}
      </Row>

      <Card size="small" title="브라우저 테스트 권장 순서">
        <Space size={[8, 8]} wrap>
          <Tag>기준정보 확인</Tag>
          <Tag>반품 접수</Tag>
          <Tag>팀배정</Tag>
          <Tag>반품처리</Tag>
          <Tag>일마감</Tag>
          <Tag>재고현황</Tag>
          <Tag>반품 이력조회</Tag>
        </Space>
      </Card>
    </SmartPage>
  );
}
