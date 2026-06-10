import { DatabaseOutlined, RollbackOutlined, ScanOutlined, ShoppingOutlined } from "@ant-design/icons";
import { Card, Col, Descriptions, Row, Space, Tag, Typography } from "antd";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartSummaryCard } from "../../components/common/SmartSummaryCard";
import { useAuth } from "../../context/AuthContext";

/**
 * 고객(셀러) 포털 기본 진입 화면.
 * 1차에서는 로그인한 고객사/팀 정보 확인과 향후 제공 기능 안내(준비중)까지만 담당한다.
 */
export function PortalDashboardPage() {
  const { authContext } = useAuth();

  const upcomingModules = [
    {
      title: "반품 접수",
      description: "반품 요청 등록과 접수 현황을 확인하는 화면이 제공될 예정입니다.",
      icon: <RollbackOutlined />,
    },
    {
      title: "처리 현황",
      description: "센터 도착, 판정, 마감, 반출까지 반품 처리 진행 상태를 확인합니다.",
      icon: <ScanOutlined />,
    },
    {
      title: "상품마스터",
      description: "고객사 상품/바코드 정보를 확인하고 제공하는 화면이 연결됩니다.",
      icon: <ShoppingOutlined />,
    },
    {
      title: "재고/정산",
      description: "고객사 재고 현황과 정산 리포트를 확인하는 화면이 연결됩니다.",
      icon: <DatabaseOutlined />,
    },
  ];

  return (
    <SmartPage>
      <SmartPageHeader
        title="스마트리턴프로 고객 포털"
        description="로그인한 고객사 기준으로 반품 진행 상황과 운영 결과를 확인하는 공간입니다. 세부 기능은 순차적으로 제공됩니다."
      />

      <div className="smart-summary-grid">
        <SmartSummaryCard label="고객사" value={authContext?.client_name || "미지정"} tone="info" />
        <SmartSummaryCard label="대리점" value={authContext?.agency_name || "미지정"} tone="system" />
        <SmartSummaryCard label="권한" value={authContext?.roles?.[0] || "ROLE 없음"} tone="success" />
      </div>

      <Card size="small" title="내 계정/범위">
        <Descriptions column={{ xs: 1, md: 2 }} size="small" colon>
          <Descriptions.Item label="사용자">{authContext?.user_name || "-"}</Descriptions.Item>
          <Descriptions.Item label="로그인 ID">{authContext?.login_id || "-"}</Descriptions.Item>
          <Descriptions.Item label="고객사">{authContext?.client_name || "-"}</Descriptions.Item>
          <Descriptions.Item label="대리점">{authContext?.agency_name || "-"}</Descriptions.Item>
          <Descriptions.Item label="client_id">{authContext?.client_id ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="운영단위">
            {authContext?.client_unit_id ?? "고객사 전체"}
          </Descriptions.Item>
        </Descriptions>
        <Typography.Paragraph type="secondary" className="smart-paragraph-note">
          현재 계정은 고객사(client) 단위로 접근 범위가 제한됩니다. 운영단위(팀) 단위 세부 권한은 추후 제공됩니다.
        </Typography.Paragraph>
      </Card>

      <Row gutter={[12, 12]}>
        {upcomingModules.map((module) => (
          <Col xs={24} md={12} key={module.title}>
            <Card size="small" title={module.title} extra={<Tag color="default">준비중</Tag>}>
              <Space align="start" size={10}>
                <Typography.Text type="secondary">{module.icon}</Typography.Text>
                <Typography.Paragraph type="secondary" className="smart-paragraph-compact">
                  {module.description}
                </Typography.Paragraph>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    </SmartPage>
  );
}
