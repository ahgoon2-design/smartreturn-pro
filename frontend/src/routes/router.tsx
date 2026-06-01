import { createBrowserRouter, Navigate } from "react-router-dom";
import { MainLayout } from "../layouts/MainLayout";
import { LoginPage } from "../pages/auth/LoginPage";
import { PasswordChangeRequiredPage } from "../pages/auth/PasswordChangeRequiredPage";
import { DashboardPage } from "../pages/dashboard/DashboardPage";
import { ImportPreviewPage } from "../features/import/ImportPreviewPage";
import { ClientDetailPage } from "../features/master/ClientDetailPage";
import { ClientListPage } from "../features/master/ClientListPage";
import { ProductDetailPlaceholderPage, ProductListPage } from "../features/master/ProductListPage";
import { ForbiddenPage } from "../pages/forbidden/ForbiddenPage";
import { NotFoundPage } from "../pages/not-found/NotFoundPage";
import { ProtectedRoute, PublicRoute } from "./RouteGuard";
import { ROUTE_PATHS } from "./routePaths";

export const router = createBrowserRouter([
  {
    path: ROUTE_PATHS.home,
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to={ROUTE_PATHS.importPreview} replace /> },
      {
        path: "imports/preview",
        element: (
          <ProtectedRoute requiredPermissions={["IMPORT_MANAGE"]}>
            <ImportPreviewPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "master/clients",
        element: (
          <ProtectedRoute requiredPermissions={["MASTER_VIEW"]}>
            <ClientListPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "master/clients/:clientId",
        element: (
          <ProtectedRoute requiredPermissions={["MASTER_VIEW"]}>
            <ClientDetailPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "master/products",
        element: (
          <ProtectedRoute requiredPermissions={["MASTER_VIEW"]}>
            <ProductListPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "master/products/:productId",
        element: (
          <ProtectedRoute requiredPermissions={["MASTER_VIEW"]}>
            <ProductDetailPlaceholderPage />
          </ProtectedRoute>
        ),
      },
      { path: "dashboard", element: <DashboardPage /> },
    ],
  },
  {
    path: ROUTE_PATHS.login,
    element: (
      <PublicRoute>
        <LoginPage />
      </PublicRoute>
    ),
  },
  {
    path: ROUTE_PATHS.passwordChange,
    element: (
      <ProtectedRoute allowWhenMustChangePassword>
        <PasswordChangeRequiredPage />
      </ProtectedRoute>
    ),
  },
  { path: ROUTE_PATHS.forbidden, element: <ForbiddenPage /> },
  { path: ROUTE_PATHS.notFound, element: <NotFoundPage /> },
  { path: "*", element: <NotFoundPage /> },
]);
