import { AppstoreOutlined, CloudUploadOutlined, DatabaseOutlined, InboxOutlined } from "@ant-design/icons";
import { Layout, Menu, Tag, Typography } from "antd";
import type { MenuProps } from "antd";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { ROUTE_PATHS } from "../routes/routePaths";
import { useAuth } from "../context/AuthContext";

const { Header, Sider, Content } = Layout;

const menuItems: MenuProps["items"] = [
  {
    key: ROUTE_PATHS.importPreview,
    icon: <CloudUploadOutlined />,
    label: "Import Preview",
  },
  {
    key: "master-ready",
    icon: <DatabaseOutlined />,
    label: "기준정보 준비중",
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

export function MainLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { authContext } = useAuth();

  return (
    <Layout className="smart-app-shell">
      <Header className="smart-app-header">
        <div>
          <Typography.Text className="smart-app-eyebrow">SmartReturn Pro</Typography.Text>
          <Typography.Title level={4}>프론트 앱 스캐폴드</Typography.Title>
        </div>
        <Tag color={authContext ? "green" : "gold"}>
          {authContext ? `${authContext.role} context 연결` : "인증 연동 준비중"}
        </Tag>
      </Header>
      <Layout>
        <Sider width={240} theme="light" className="smart-app-sider">
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
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
