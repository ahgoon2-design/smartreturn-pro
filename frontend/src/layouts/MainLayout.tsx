import {
  ApiOutlined,
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
  const canSeePlatformMenus = Boolean(
    authContext?.is_platform_admin || authContext?.is_internal_user || authContext?.is_agency_user,
  );
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
      : location.pathname.startsWith(ROUTE_PATHS.channelAccounts)
        ? ROUTE_PATHS.channelAccounts
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
      key: ROUTE_PATHS.dashboard,
      icon: <AppstoreOutlined />,
      label: "오늘 작업",
    },
    {
      key: "return-data-group",
      label: "반품 자료",
      type: "group",
      children: [
        {
          key: ROUTE_PATHS.returnIntake,
          icon: <RollbackOutlined />,
          label: "업체/CJ 반품 자료",
          disabled: !hasPermission("RETURN_VIEW"),
        },
        {
          key: ROUTE_PATHS.importPreview,
          icon: <CloudUploadOutlined />,
          label: "엑셀/복붙 자동매핑",
          disabled: !hasPermission("IMPORT_MANAGE"),
        },
        {
          key: ROUTE_PATHS.channelAccounts,
          icon: <ApiOutlined />,
          label: "자동수집 후보",
          disabled: !canSeePlatformMenus || !hasPermission("RETURN_VIEW"),
        },
      ],
    },
    {
      key: "return-processing-group",
      label: "반품 처리",
      type: "group",
      children: [
        {
          key: ROUTE_PATHS.returnUnitAssignment,
          icon: <TeamOutlined />,
          label: "팀배정/예외",
          disabled: !hasPermission("RETURN_VIEW"),
        },
        {
          key: ROUTE_PATHS.returnProcessing,
          icon: <ScanOutlined />,
          label: "반품 처리 센터",
          disabled: !hasPermission("RETURN_VIEW"),
        },
      ],
    },
    {
      key: "return-closing-group",
      label: "반품 마감",
      type: "group",
      children: [
        {
          key: ROUTE_PATHS.returnClosing,
          icon: <CheckCircleOutlined />,
          label: "일마감/재고반영",
          disabled: !hasPermission("RETURN_VIEW"),
        },
        {
          key: ROUTE_PATHS.returnHistory,
          icon: <HistoryOutlined />,
          label: "반품 이력조회",
          disabled: !hasPermission("RETURN_VIEW"),
        },
      ],
    },
    {
      key: "return-outbound-group",
      label: "반출/폐기",
      type: "group",
      children: [
        {
          key: ROUTE_PATHS.returnExternalOutbound,
          icon: <ExportOutlined />,
          label: "제조사반출",
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
          key: ROUTE_PATHS.returnExternalOutboundBatches,
          icon: <HistoryOutlined />,
          label: "반출 이력",
          disabled: !hasPermission("RETURN_VIEW"),
        },
      ],
    },
    {
      key: "inventory-group",
      label: "재고",
      type: "group",
      children: [
        {
          key: ROUTE_PATHS.inventoryCurrent,
          icon: <DatabaseOutlined />,
          label: "현재고",
          disabled: !hasPermission("INVENTORY_VIEW"),
        },
        {
          key: ROUTE_PATHS.inventoryEvents,
          icon: <HistoryOutlined />,
          label: "재고 이벤트",
          disabled: !hasPermission("INVENTORY_VIEW"),
        },
      ],
    },
    {
      key: "master-group",
      label: "기준정보",
      type: "group",
      children: [
        ...(canSeePlatformMenus
          ? [
              {
                key: ROUTE_PATHS.masterClients,
                icon: <DatabaseOutlined />,
                label: "고객사/대리점",
                disabled: !hasPermission("MASTER_VIEW"),
              },
            ]
          : []),
        {
          key: ROUTE_PATHS.masterProducts,
          icon: <InboxOutlined />,
          label: "상품/바코드",
          disabled: !hasPermission("MASTER_VIEW"),
        },
        {
          key: ROUTE_PATHS.masterCommonCodes,
          icon: <TeamOutlined />,
          label: "공통코드",
          disabled: !hasPermission("MASTER_VIEW"),
        },
        { key: "master-warehouse-ready", icon: <InboxOutlined />, label: "창고/처리장소 준비중", disabled: true },
        { key: "label-policy-ready", icon: <ScanOutlined />, label: "라벨 정책 준비중", disabled: true },
      ],
    },
    {
      key: "system-group",
      label: "시스템",
      type: "group",
      children: [
        { key: "system-users-ready", icon: <UserOutlined />, label: "사용자 관리 준비중", disabled: true },
        { key: "system-permissions-ready", icon: <TeamOutlined />, label: "권한 관리 준비중", disabled: true },
        { key: "system-logs-ready", icon: <HistoryOutlined />, label: "로그 관리 준비중", disabled: true },
        { key: "system-settings-ready", icon: <AppstoreOutlined />, label: "시스템 설정 준비중", disabled: true },
      ],
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
          <Typography.Title level={4}>OMS + WMS + Returns 통합 운영 플랫폼</Typography.Title>
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
            onClick={({ key }) => {
              if (String(key).startsWith("/")) {
                navigate(key);
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
