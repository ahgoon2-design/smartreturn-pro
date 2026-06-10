import {
  AppstoreOutlined,
  DatabaseOutlined,
  LogoutOutlined,
  MessageOutlined,
  RollbackOutlined,
  ScanOutlined,
  ShoppingOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Button, Layout, Menu, Space, Tag, Typography } from "antd";
import type { MenuProps } from "antd";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ROUTE_PATHS } from "../routes/routePaths";

const { Header, Sider, Content } = Layout;

/**
 * 고객(셀러) 포털 전용 최소 레이아웃.
 * 내부 운영자용 MainLayout과 메뉴/구조를 분리하며, 1차에서는 대시보드 외 메뉴를 준비중으로 노출한다.
 */
export function PortalLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { authContext, role, logout } = useAuth();

  const clientLabel = authContext?.client_name || "고객사 미지정";
  const agencyLabel = authContext?.agency_name;

  const menuItems: MenuProps["items"] = [
    { key: ROUTE_PATHS.portalDashboard, icon: <AppstoreOutlined />, label: "대시보드" },
    {
      key: "portal-returns-group",
      icon: <RollbackOutlined />,
      label: "반품",
      children: [
        { key: "portal-return-status-ready", icon: <ScanOutlined />, label: "반품 처리현황 준비중", disabled: true },
        { key: "portal-return-intake-ready", icon: <RollbackOutlined />, label: "반품 접수 등록 준비중", disabled: true },
      ],
    },
    {
      key: "portal-catalog-group",
      icon: <ShoppingOutlined />,
      label: "상품/재고",
      children: [
        { key: "portal-product-ready", icon: <ShoppingOutlined />, label: "상품마스터 준비중", disabled: true },
        { key: "portal-inventory-ready", icon: <DatabaseOutlined />, label: "재고/정산 준비중", disabled: true },
      ],
    },
    {
      key: "portal-support-group",
      icon: <MessageOutlined />,
      label: "지원",
      children: [{ key: "portal-inquiry-ready", icon: <MessageOutlined />, label: "문의/보류 준비중", disabled: true }],
    },
  ];

  function handleLogout() {
    logout();
    navigate(ROUTE_PATHS.login, { replace: true });
  }

  return (
    <Layout className="smart-app-shell">
      <Header className="smart-app-header">
        <div>
          <Typography.Text className="smart-app-eyebrow">SmartReturn Pro</Typography.Text>
          <Typography.Title level={4}>스마트리턴프로 고객 포털</Typography.Title>
        </div>
        <Space>
          {agencyLabel ? <Tag color="blue">{agencyLabel}</Tag> : null}
          <Tag color="geekblue">{clientLabel}</Tag>
          <Tag icon={<UserOutlined />} color={authContext ? "green" : "gold"}>
            {authContext ? `${authContext.user_name} · ${role || "ROLE 없음"}` : "인증 정보 없음"}
          </Tag>
          {authContext?.must_change_password ? <Tag color="red">비밀번호 변경 필요</Tag> : null}
          <Button icon={<LogoutOutlined />} onClick={handleLogout}>
            로그아웃
          </Button>
        </Space>
      </Header>
      <Layout>
        <Sider width={240} theme="light" className="smart-app-sider">
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            defaultOpenKeys={["portal-returns-group", "portal-catalog-group", "portal-support-group"]}
            items={menuItems}
            onClick={({ key }) => {
              if (String(key).startsWith("/")) {
                navigate(String(key));
              }
            }}
          />
        </Sider>
        <Content className="smart-app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
