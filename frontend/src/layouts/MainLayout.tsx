import {
  ApartmentOutlined,
  ApiOutlined,
  AppstoreOutlined,
  CheckCircleOutlined,
  CloseOutlined,
  CloudUploadOutlined,
  CreditCardOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  ExportOutlined,
  EyeOutlined,
  HistoryOutlined,
  HomeOutlined,
  LogoutOutlined,
  PauseCircleOutlined,
  RollbackOutlined,
  ScanOutlined,
  SettingOutlined,
  ShoppingOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Button, Layout, Menu, Space, Tag, Typography } from "antd";
import type { MenuProps } from "antd";
import { useEffect, useRef } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useRecentWorkTabs } from "../hooks/useRecentWorkTabs";
import { ROUTE_PATHS } from "../routes/routePaths";

const { Header, Sider, Content } = Layout;

const MENU_GROUP_KEYS = [
  "home-group",
  "returns-group",
  "customer-product-group",
  "inventory-group",
  "portal-billing-group",
  "settings-group",
];

export function MainLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const contentRef = useRef<HTMLElement | null>(null);
  const navigationSourceRef = useRef<"menu" | "work-tab" | null>(null);
  const { authContext, role, hasPermission, logout } = useAuth();
  const { tabs: workTabs, closeRecentTab } = useRecentWorkTabs(location);
  const canSeePlatformMenus = Boolean(
    authContext?.is_platform_admin || authContext?.is_internal_user || authContext?.is_agency_user,
  );
  // 고객 포털 미리보기는 내부 운영자/플랫폼 관리자만(대리점/고객 제외) 진입할 수 있다.
  const canPreviewPortal = Boolean(authContext?.is_platform_admin || authContext?.is_internal_user);

  const selectedMenuKey = location.pathname.startsWith(ROUTE_PATHS.settingsPlans)
    ? ROUTE_PATHS.settingsPlans
    : location.pathname.startsWith(ROUTE_PATHS.masterClients)
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
      : location.pathname.startsWith(ROUTE_PATHS.importPreview)
        ? ROUTE_PATHS.importPreview
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
      key: "home-group",
      icon: <HomeOutlined />,
      label: "홈",
      children: [{ key: ROUTE_PATHS.dashboard, icon: <AppstoreOutlined />, label: "대시보드" }],
    },
    {
      key: "returns-group",
      icon: <RollbackOutlined />,
      label: "반품 운영",
      children: [
        { key: ROUTE_PATHS.returnIntake, icon: <RollbackOutlined />, label: "반품입고예정", disabled: !hasPermission("RETURN_VIEW") },
        { key: ROUTE_PATHS.returnUnitAssignment, icon: <TeamOutlined />, label: "팀배정/예외", disabled: !hasPermission("RETURN_VIEW") },
        { key: ROUTE_PATHS.returnProcessing, icon: <ScanOutlined />, label: "반품처리", disabled: !hasPermission("RETURN_VIEW") },
        { key: ROUTE_PATHS.returnClosing, icon: <CheckCircleOutlined />, label: "일마감", disabled: !hasPermission("RETURN_VIEW") },
        { key: ROUTE_PATHS.returnHold, icon: <PauseCircleOutlined />, label: "보류관리", disabled: !hasPermission("RETURN_VIEW") },
        { key: ROUTE_PATHS.returnDisposal, icon: <DeleteOutlined />, label: "폐기관리", disabled: !hasPermission("RETURN_VIEW") },
        { key: ROUTE_PATHS.returnExternalOutbound, icon: <ExportOutlined />, label: "외부반출/제조사반품", disabled: !hasPermission("RETURN_VIEW") },
        { key: ROUTE_PATHS.returnExternalOutboundBatches, icon: <HistoryOutlined />, label: "외부반출 이력", disabled: !hasPermission("RETURN_VIEW") },
        { key: ROUTE_PATHS.returnHistory, icon: <HistoryOutlined />, label: "반품 이력조회", disabled: !hasPermission("RETURN_VIEW") },
      ],
    },
    {
      key: "customer-product-group",
      icon: <TeamOutlined />,
      label: "고객/상품",
      children: [
        { key: ROUTE_PATHS.masterClients, icon: <TeamOutlined />, label: "고객사 관리", disabled: !hasPermission("MASTER_VIEW") },
        { key: ROUTE_PATHS.masterProducts, icon: <ShoppingOutlined />, label: "상품마스터", disabled: !hasPermission("MASTER_VIEW") },
        { key: "set-product-ready", icon: <ApartmentOutlined />, label: "세트/구성품 준비중", disabled: true },
      ],
    },
    {
      key: "inventory-group",
      icon: <DatabaseOutlined />,
      label: "재고/정산",
      children: [
        { key: ROUTE_PATHS.inventoryCurrent, icon: <DatabaseOutlined />, label: "재고현황", disabled: !hasPermission("INVENTORY_VIEW") },
        { key: ROUTE_PATHS.inventoryEvents, icon: <HistoryOutlined />, label: "재고 이벤트", disabled: !hasPermission("INVENTORY_VIEW") },
        { key: "month-close-ready", icon: <CheckCircleOutlined />, label: "월마감/정산 준비중", disabled: true },
        { key: "cycle-count-ready", icon: <AppstoreOutlined />, label: "순환실사 준비중", disabled: true },
      ],
    },
    {
      key: "portal-billing-group",
      icon: <CreditCardOutlined />,
      label: "포털/요금제",
      children: [
        ...(canPreviewPortal
          ? [{ key: ROUTE_PATHS.portalDashboard, icon: <EyeOutlined />, label: "고객 포털 미리보기" }]
          : []),
        { key: ROUTE_PATHS.settingsPlans, icon: <CreditCardOutlined />, label: "플랜/요금제" },
      ],
    },
    {
      key: "settings-group",
      icon: <SettingOutlined />,
      label: "설정",
      children: [
        { key: "system-users-ready", icon: <UserOutlined />, label: "사용자/권한 준비중", disabled: true },
        { key: ROUTE_PATHS.masterCommonCodes, icon: <DatabaseOutlined />, label: "기준정보(공통코드)", disabled: !hasPermission("MASTER_VIEW") },
        {
          key: ROUTE_PATHS.channelAccounts,
          icon: <ApiOutlined />,
          label: "연동 설정(채널)",
          disabled: !canSeePlatformMenus || !hasPermission("RETURN_VIEW"),
        },
        { key: ROUTE_PATHS.importPreview, icon: <CloudUploadOutlined />, label: "Smart Import", disabled: !hasPermission("IMPORT_MANAGE") },
      ],
    },
  ];

  function handleLogout() {
    logout();
    navigate(ROUTE_PATHS.login, { replace: true });
  }

  useEffect(() => {
    if (navigationSourceRef.current !== "menu") {
      navigationSourceRef.current = null;
      return;
    }
    requestAnimationFrame(() => {
      scrollContentToTop(contentRef.current);
      navigationSourceRef.current = null;
    });
  }, [location.pathname, location.search]);

  function handleMenuNavigate(path: string) {
    navigationSourceRef.current = "menu";
    navigate(path);
    requestAnimationFrame(() => scrollContentToTop(contentRef.current));
  }

  function handleWorkTabNavigate(path: string) {
    navigationSourceRef.current = "work-tab";
    navigate(path);
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
            defaultOpenKeys={MENU_GROUP_KEYS}
            items={menuItems}
            onClick={({ key }) => {
              if (String(key).startsWith("/")) {
                handleMenuNavigate(String(key));
              }
            }}
          />
        </Sider>
        <Content ref={contentRef} className="smart-app-content">
          <nav className="smart-work-tabs" aria-label="최근 작업 탭">
            {workTabs.map((tab) => {
              const active = location.pathname === tab.key || location.pathname.startsWith(`${tab.key}/`);
              return (
                <Button
                  key={tab.key}
                  size="small"
                  type={active ? "primary" : "default"}
                  className={["smart-work-tab", active ? "smart-work-tab--active" : "", tab.fixed ? "smart-work-tab--fixed" : ""]
                    .filter(Boolean)
                    .join(" ")}
                  onClick={() => handleWorkTabNavigate(tab.path)}
                >
                  <span className="smart-work-tab__label">{tab.label}</span>
                  {tab.fixed ? <Tag color="blue">고정</Tag> : null}
                  {!tab.fixed ? (
                    <CloseOutlined
                      aria-label={`${tab.label} 탭 닫기`}
                      className="smart-work-tab__close"
                      onClick={(event) => {
                        event.stopPropagation();
                        closeRecentTab(tab.key);
                      }}
                    />
                  ) : null}
                </Button>
              );
            })}
          </nav>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

function scrollContentToTop(contentElement: HTMLElement | null) {
  window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  contentElement?.scrollTo?.({ top: 0, left: 0, behavior: "auto" });
}
