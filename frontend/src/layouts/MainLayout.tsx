import {
  AppstoreOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  ExportOutlined,
  HistoryOutlined,
  InboxOutlined,
  LogoutOutlined,
  PauseCircleOutlined,
  RollbackOutlined,
  ScanOutlined,
  ShoppingOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Button, Layout, Menu, Space, Tag, Typography } from "antd";
import type { MenuProps } from "antd";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ROUTE_PATHS } from "../routes/routePaths";

const { Header, Sider, Content } = Layout;

export function MainLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { authContext, role, hasPermission, logout } = useAuth();
  const selectedMenuKey = location.pathname.startsWith(ROUTE_PATHS.masterClients)
    ? ROUTE_PATHS.masterClients
    : location.pathname.startsWith(ROUTE_PATHS.masterProducts)
      ? ROUTE_PATHS.masterProducts
      : location.pathname.startsWith(ROUTE_PATHS.masterCommonCodes)
      ? ROUTE_PATHS.masterCommonCodes
      : location.pathname.startsWith(ROUTE_PATHS.returnExternalOutboundBatches)
        ? ROUTE_PATHS.returnExternalOutboundBatches
      : location.pathname.startsWith(ROUTE_PATHS.returnExternalOutbound)
        ? ROUTE_PATHS.returnExternalOutbound
      : location.pathname.startsWith(ROUTE_PATHS.returnHold)
        ? ROUTE_PATHS.returnHold
      : location.pathname.startsWith(ROUTE_PATHS.returnDisposal)
        ? ROUTE_PATHS.returnDisposal
      : location.pathname.startsWith(ROUTE_PATHS.returnHistory)
        ? ROUTE_PATHS.returnHistory
      : location.pathname.startsWith(ROUTE_PATHS.inventoryEvents)
        ? ROUTE_PATHS.inventoryEvents
      : location.pathname.startsWith(ROUTE_PATHS.inventoryCurrent)
        ? ROUTE_PATHS.inventoryCurrent
      : location.pathname.startsWith(ROUTE_PATHS.returnClosing)
        ? ROUTE_PATHS.returnClosing
      : location.pathname.startsWith(ROUTE_PATHS.returnProcessing)
        ? ROUTE_PATHS.returnProcessing
      : location.pathname.startsWith(ROUTE_PATHS.returnUnitAssignment)
        ? ROUTE_PATHS.returnUnitAssignment
        : location.pathname.startsWith(ROUTE_PATHS.returnIntake)
          ? ROUTE_PATHS.returnIntake
      : location.pathname;

  const menuItems: MenuProps["items"] = [
    {
      key: ROUTE_PATHS.importPreview,
      icon: <CloudUploadOutlined />,
      label: "Import Preview",
      disabled: !hasPermission("IMPORT_MANAGE"),
    },
    {
      key: ROUTE_PATHS.masterClients,
      icon: <DatabaseOutlined />,
      label: "고객사/셀러",
      disabled: !hasPermission("MASTER_VIEW"),
    },
    {
      key: ROUTE_PATHS.masterProducts,
      icon: <ShoppingOutlined />,
      label: "상품/바코드",
      disabled: !hasPermission("MASTER_VIEW"),
    },
    {
      key: ROUTE_PATHS.masterCommonCodes,
      icon: <TeamOutlined />,
      label: "공통코드",
      disabled: !hasPermission("MASTER_VIEW"),
    },
    {
      key: ROUTE_PATHS.returnIntake,
      icon: <RollbackOutlined />,
      label: "반품 접수 허브",
      disabled: !hasPermission("RETURN_VIEW"),
    },
    {
      key: ROUTE_PATHS.returnUnitAssignment,
      icon: <TeamOutlined />,
      label: "반품 팀배정",
      disabled: !hasPermission("RETURN_VIEW"),
    },
    {
      key: ROUTE_PATHS.returnProcessing,
      icon: <ScanOutlined />,
      label: "반품처리 작업",
      disabled: !hasPermission("RETURN_VIEW"),
    },
    {
      key: ROUTE_PATHS.returnClosing,
      icon: <CheckCircleOutlined />,
      label: "반품 일마감",
      disabled: !hasPermission("RETURN_VIEW"),
    },
    {
      key: ROUTE_PATHS.returnExternalOutbound,
      icon: <ExportOutlined />,
      label: "반품 외부반출",
      disabled: !hasPermission("RETURN_VIEW"),
    },
    {
      key: ROUTE_PATHS.returnExternalOutboundBatches,
      icon: <HistoryOutlined />,
      label: "외부반출 이력",
      disabled: !hasPermission("RETURN_VIEW"),
    },
    {
      key: ROUTE_PATHS.returnHold,
      icon: <PauseCircleOutlined />,
      label: "반품 보류관리",
      disabled: !hasPermission("RETURN_VIEW"),
    },
    {
      key: ROUTE_PATHS.returnDisposal,
      icon: <DeleteOutlined />,
      label: "반품 폐기관리",
      disabled: !hasPermission("RETURN_VIEW"),
    },
    {
      key: ROUTE_PATHS.returnHistory,
      icon: <HistoryOutlined />,
      label: "반품 이력조회",
      disabled: !hasPermission("RETURN_VIEW"),
    },
    {
      key: ROUTE_PATHS.inventoryCurrent,
      icon: <DatabaseOutlined />,
      label: "재고현황",
      disabled: !hasPermission("INVENTORY_VIEW"),
    },
    {
      key: ROUTE_PATHS.inventoryEvents,
      icon: <HistoryOutlined />,
      label: "재고 이벤트",
      disabled: !hasPermission("INVENTORY_VIEW"),
    },
    {
      key: "master-other-ready",
      icon: <DatabaseOutlined />,
      label: "기준정보 후속 준비중",
      disabled: true,
    },
    {
      key: "inbound-ready",
      icon: <InboxOutlined />,
      label: "입고 준비중",
      disabled: true,
    },
    {
      key: "operations-ready",
      icon: <AppstoreOutlined />,
      label: "출고/반품/재고/정산 준비중",
      disabled: true,
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
          <Typography.Title level={4}>프론트 앱</Typography.Title>
        </div>
        <Space>
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
            selectedKeys={[selectedMenuKey]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
          />
        </Sider>
        <Content className="smart-app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
