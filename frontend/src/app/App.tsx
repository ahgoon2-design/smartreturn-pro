import { ConfigProvider } from "antd";
import koKR from "antd/locale/ko_KR";
import { RouterProvider } from "react-router-dom";
import { AuthProvider } from "../context/AuthContext";
import { router } from "../routes/router";

export function App() {
  return (
    <ConfigProvider
      locale={koKR}
      theme={{
        token: {
          colorPrimary: "#2F80ED",
          colorSuccess: "#35A853",
          colorWarning: "#F59E0B",
          colorError: "#E5484D",
          colorInfo: "#2F80ED",
          colorBgLayout: "#F6F8FB",
          colorBgContainer: "#FFFFFF",
          colorBorder: "#E5EAF0",
          colorText: "#172033",
          colorTextSecondary: "#64748B",
          borderRadius: 10,
          boxShadowTertiary: "0 8px 24px rgba(15, 23, 42, 0.06)",
        },
        components: {
          Card: {
            borderRadiusLG: 14,
          },
          Table: {
            headerBg: "#F8FBFF",
            headerColor: "#172033",
            rowHoverBg: "#F6FAFF",
          },
          Tag: {
            borderRadiusSM: 999,
          },
          Modal: {
            borderRadiusLG: 16,
          },
        },
      }}
    >
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ConfigProvider>
  );
}
