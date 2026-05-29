import { createBrowserRouter, Navigate } from "react-router-dom";
import { MainLayout } from "../layouts/MainLayout";
import { LoginPlaceholderPage } from "../pages/auth/LoginPlaceholderPage";
import { DashboardPage } from "../pages/dashboard/DashboardPage";
import { ImportPreviewPage } from "../features/import/ImportPreviewPage";
import { NotFoundPage } from "../pages/not-found/NotFoundPage";
import { RouteGuard } from "./RouteGuard";
import { ROUTE_PATHS } from "./routePaths";

export const router = createBrowserRouter([
  {
    path: ROUTE_PATHS.home,
    element: <MainLayout />,
    children: [
      { index: true, element: <Navigate to={ROUTE_PATHS.importPreview} replace /> },
      {
        path: "imports/preview",
        element: (
          <RouteGuard>
            <ImportPreviewPage />
          </RouteGuard>
        ),
      },
      { path: "dashboard", element: <DashboardPage /> },
    ],
  },
  { path: ROUTE_PATHS.login, element: <LoginPlaceholderPage /> },
  { path: "*", element: <NotFoundPage /> },
]);
