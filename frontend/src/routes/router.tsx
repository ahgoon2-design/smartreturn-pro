import { createBrowserRouter, Navigate } from "react-router-dom";
import { MainLayout } from "../layouts/MainLayout";
import { PortalLayout } from "../layouts/PortalLayout";
import { LoginPage } from "../pages/auth/LoginPage";
import { PortalDashboardPage } from "../pages/portal/PortalDashboardPage";
import { PortalReturnIntakePage } from "../pages/portal/PortalReturnIntakePage";
import { PortalReturnStatusPage } from "../pages/portal/PortalReturnStatusPage";
import { PasswordChangeRequiredPage } from "../pages/auth/PasswordChangeRequiredPage";
import { DashboardPage } from "../pages/dashboard/DashboardPage";
import { ChannelAccountManagementScreen } from "../features/channels/ChannelAccountManagementScreen";
import { ImportMappingLearningPage } from "../features/import/ImportMappingLearningPage";
import { ImportPreviewPage } from "../features/import/ImportPreviewPage";
import { CurrentInventoryPage } from "../features/inventory/CurrentInventoryPage";
import { InventoryEventsPage } from "../features/inventory/InventoryEventsPage";
import { ClientDetailPage } from "../features/master/ClientDetailPage";
import { ClientListPage } from "../features/master/ClientListPage";
import { CommonCodeManagementPage } from "../features/master/CommonCodeManagementPage";
import { ProductDetailPage } from "../features/master/ProductDetailPage";
import { ProductListPage } from "../features/master/ProductListPage";
import { ReturnIntakeHubPage } from "../features/returns/ReturnIntakeHubPage";
import { ReturnUnitAssignmentPage } from "../features/returns/ReturnUnitAssignmentPage";
import { ReturnClosingPage } from "../features/returns/ReturnClosingPage";
import { ReturnDisposalManagementPage } from "../features/returns/ReturnDisposalManagementPage";
import { ReturnExternalOutboundBatchesPage } from "../features/returns/ReturnExternalOutboundBatchesPage";
import { ReturnExternalOutboundPage } from "../features/returns/ReturnExternalOutboundPage";
import { ReturnHistoryPage } from "../features/returns/ReturnHistoryPage";
import { ReturnHoldManagementPage } from "../features/returns/ReturnHoldManagementPage";
import { ReturnProcessingWorkspacePage } from "../features/returns/ReturnProcessingWorkspacePage";
import { PricingPlansPage } from "../features/billing/PricingPlansPage";
import { ForbiddenPage } from "../pages/forbidden/ForbiddenPage";
import { NotFoundPage } from "../pages/not-found/NotFoundPage";
import { ProtectedRoute, PublicRoute } from "./RouteGuard";
import { ROUTE_PATHS } from "./routePaths";

export const router = createBrowserRouter([
  {
    path: ROUTE_PATHS.home,
    element: (
      <ProtectedRoute area="internal">
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to={ROUTE_PATHS.dashboard} replace /> },
      {
        path: "channels/accounts",
        element: (
          <ProtectedRoute requiredPermissions={["RETURN_VIEW"]}>
            <ChannelAccountManagementScreen />
          </ProtectedRoute>
        ),
      },
      {
        path: "imports/preview",
        element: (
          <ProtectedRoute requiredPermissions={["IMPORT_MANAGE"]}>
            <ImportPreviewPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "imports/mapping-learning",
        element: (
          <ProtectedRoute requiredPermissions={["IMPORT_MANAGE"]}>
            <ImportMappingLearningPage />
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
            <ProductDetailPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "master/common-codes",
        element: (
          <ProtectedRoute requiredPermissions={["MASTER_VIEW"]}>
            <CommonCodeManagementPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "returns/intake",
        element: (
          <ProtectedRoute requiredPermissions={["RETURN_VIEW"]}>
            <ReturnIntakeHubPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "returns/unit-assignment",
        element: (
          <ProtectedRoute requiredPermissions={["RETURN_VIEW"]}>
            <ReturnUnitAssignmentPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "returns/processing",
        element: (
          <ProtectedRoute requiredPermissions={["RETURN_VIEW"]}>
            <ReturnProcessingWorkspacePage />
          </ProtectedRoute>
        ),
      },
      {
        path: "returns/closing",
        element: (
          <ProtectedRoute requiredPermissions={["RETURN_VIEW"]}>
            <ReturnClosingPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "returns/external-outbound/batches",
        element: (
          <ProtectedRoute requiredPermissions={["RETURN_VIEW"]}>
            <ReturnExternalOutboundBatchesPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "returns/external-outbound",
        element: (
          <ProtectedRoute requiredPermissions={["RETURN_VIEW"]}>
            <ReturnExternalOutboundPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "returns/hold",
        element: (
          <ProtectedRoute requiredPermissions={["RETURN_VIEW"]}>
            <ReturnHoldManagementPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "returns/disposal",
        element: (
          <ProtectedRoute requiredPermissions={["RETURN_VIEW"]}>
            <ReturnDisposalManagementPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "returns/history",
        element: (
          <ProtectedRoute requiredPermissions={["RETURN_VIEW"]}>
            <ReturnHistoryPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "inventory/current",
        element: (
          <ProtectedRoute requiredPermissions={["INVENTORY_VIEW"]}>
            <CurrentInventoryPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "inventory/events",
        element: (
          <ProtectedRoute requiredPermissions={["INVENTORY_VIEW"]}>
            <InventoryEventsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "settings/plans",
        element: (
          <ProtectedRoute area="internal">
            <PricingPlansPage />
          </ProtectedRoute>
        ),
      },
      { path: "dashboard", element: <DashboardPage /> },
    ],
  },
  {
    path: ROUTE_PATHS.portalHome,
    element: (
      <ProtectedRoute area="portal">
        <PortalLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to={ROUTE_PATHS.portalDashboard} replace /> },
      { path: "dashboard", element: <PortalDashboardPage /> },
      { path: "returns", element: <PortalReturnStatusPage /> },
      { path: "returns/intake", element: <PortalReturnIntakePage /> },
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
