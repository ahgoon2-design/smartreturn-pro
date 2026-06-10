import {
  ApiOutlined,
  AppstoreOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  ExportOutlined,
  InboxOutlined,
  RollbackOutlined,
  ShoppingOutlined,
  TeamOutlined,
} from "@ant-design/icons";
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
      title: "주문/채널",
      tag: "OMS",
      description: "채널 계정, 자동수집 후보, 향후 주문/반품/교환/취소 수집 흐름을 관리합니다.",
      path: ROUTE_PATHS.channelAccounts,
      icon: <ApiOutlined />,
    },
    {
      title: "입고/출고",
      tag: "WMS 준비",
      description: "일반 입고, 출고 예정, 피킹, 출고검수는 WMS 확장 모듈로 연결될 자리입니다.",
      icon: <InboxOutlined />,
    },
    {
      title: "재고",
      tag: "WMS",
      description: "현재고와 재고 이벤트를 고객사, 창고, 상품 기준으로 확인합니다.",
      path: ROUTE_PATHS.inventoryCurrent,
      icon: <DatabaseOutlined />,
    },
    {
      title: "반품",
      tag: "Returns",
      description: "반품 자료, 현장 처리, 일마감, 반출/폐기까지 MVP 핵심 업무를 실행합니다.",
      path: ROUTE_PATHS.returnProcessing,
      icon: <RollbackOutlined />,
    },
    {
      title: "정산",
      tag: "Platform 준비",
      description: "사용량 집계, 대리점 요금, 고객사 청구는 후속 정산 모듈로 확장합니다.",
      icon: <CheckCircleOutlined />,
    },
    {
      title: "고객사/대리점",
      tag: "Platform",
      description: "agency_id, client_id, client_unit_id 계층으로 운영 범위와 고객사를 관리합니다.",
      path: ROUTE_PATHS.masterClients,
      icon: <TeamOutlined />,
    },
  ];

  return (
    <SmartPage>
      <SmartPageHeader
        title="통합 운영 대시보드"
        description="SmartReturn Pro는 반품 MVP를 시작점으로 OMS, WMS, Returns, 정산, 대리점 운영을 하나의 SaaS 계층에서 확장합니다."
      />

      <div className="smart-summary-grid">
        <SmartSummaryCard label="OMS" value="주문/채널" tone="info" />
        <SmartSummaryCard label="WMS" value="입고/출고/재고" tone="success" />
        <SmartSummaryCard label="Returns" value="반품 MVP" tone="warning" />
        <SmartSummaryCard label="Platform" value="대리점/정산" tone="system" />
      </div>

      <Row gutter={[12, 12]}>
        {workCards.map((module) => (
          <Col xs={24} md={12} xl={8} key={module.title}>
            <Card
              size="small"
              title={module.title}
              extra={<Tag color={module.path ? "blue" : "default"}>{module.tag}</Tag>}
            >
              <Space align="start" size={10}>
                <Typography.Text type="secondary">{module.icon}</Typography.Text>
                <Typography.Paragraph type="secondary" className="smart-paragraph-compact">
                  {module.description}
                </Typography.Paragraph>
              </Space>
              <div className="smart-inline-actions">
                <Button type="link" disabled={!module.path} onClick={() => module.path && navigate(module.path)}>
                  {module.path ? "바로가기" : "준비중"}
                </Button>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Card size="small" title="반품 MVP 테스트 흐름">
        <Row gutter={[8, 8]}>
          {[
            { label: "반품 자료", icon: <RollbackOutlined />, path: ROUTE_PATHS.returnIntake },
            { label: "팀배정/예외", icon: <TeamOutlined />, path: ROUTE_PATHS.returnUnitAssignment },
            { label: "반품 처리", icon: <ShoppingOutlined />, path: ROUTE_PATHS.returnProcessing },
            { label: "일마감", icon: <CheckCircleOutlined />, path: ROUTE_PATHS.returnClosing },
            { label: "반출/폐기", icon: <ExportOutlined />, path: ROUTE_PATHS.returnExternalOutbound },
            { label: "현재고", icon: <DatabaseOutlined />, path: ROUTE_PATHS.inventoryCurrent },
          ].map((step, index) => (
            <Col xs={12} md={8} xl={4} key={step.label}>
              <Button block onClick={() => navigate(step.path)}>
                <Space>
                  {step.icon}
                  <span>{index + 1}. {step.label}</span>
                </Space>
              </Button>
            </Col>
          ))}
        </Row>
      </Card>

      <Card size="small" title="플랫폼 설계 기준">
        <Space size={[8, 8]} wrap>
          <Tag icon={<AppstoreOutlined />}>platform_owner</Tag>
          <Tag icon={<TeamOutlined />} color="purple">agency_id</Tag>
          <Tag icon={<TeamOutlined />} color="blue">client_id</Tag>
          <Tag icon={<TeamOutlined />} color="green">client_unit_id</Tag>
          <Tag color="orange">핵심 운영 테이블 agency_id 직접 저장</Tag>
          <Tag color="green">반품 재고반영은 마감 후</Tag>
        </Space>
        <Typography.Paragraph type="secondary" className="smart-paragraph-note">
          미구현 OMS/WMS/정산 기능은 준비중으로 두되, 메뉴와 데이터 계층은 처음부터 통합 SaaS 기준을 따릅니다.
        </Typography.Paragraph>
      </Card>
    </SmartPage>
  );
}
