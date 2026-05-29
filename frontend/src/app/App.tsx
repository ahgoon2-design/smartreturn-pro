import { ConfigProvider } from "antd";
import koKR from "antd/locale/ko_KR";
import { RouterProvider } from "react-router-dom";
import { AuthProvider } from "../context/AuthContext";
import { router } from "../routes/router";

export function App() {
  return (
    <ConfigProvider locale={koKR}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ConfigProvider>
  );
}
