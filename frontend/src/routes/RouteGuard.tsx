import type { ReactNode } from "react";
import { Alert, Spin } from "antd";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ROUTE_PATHS } from "./routePaths";

interface ProtectedRouteProps {
  children: ReactNode;
  requiredPermissions?: string[];
  allowWhenMustChangePassword?: boolean;
}

export function ProtectedRoute({ children, requiredPermissions, allowWhenMustChangePassword = false }: ProtectedRouteProps) {
  const { loading, isAuthenticated, mustChangePassword, canAccess } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="smart-route-loading">
        <Spin />
        <span>인증 상태를 확인하는 중입니다.</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to={ROUTE_PATHS.login} replace state={{ from: location }} />;
  }

  if (mustChangePassword && !allowWhenMustChangePassword) {
    return <Navigate to={ROUTE_PATHS.passwordChange} replace state={{ from: location }} />;
  }

  if (!canAccess(requiredPermissions)) {
    return <Navigate to={ROUTE_PATHS.forbidden} replace />;
  }

  return <>{children}</>;
}

export function PublicRoute({ children }: { children: ReactNode }) {
  const { loading, isAuthenticated, mustChangePassword } = useAuth();

  if (loading) {
    return (
      <div className="smart-route-loading">
        <Spin />
        <span>인증 상태를 확인하는 중입니다.</span>
      </div>
    );
  }

  if (isAuthenticated && mustChangePassword) {
    return <Navigate to={ROUTE_PATHS.passwordChange} replace />;
  }

  if (isAuthenticated) {
    return <Navigate to={ROUTE_PATHS.importPreview} replace />;
  }

  return <>{children}</>;
}

export function ForbiddenNotice() {
  return <Alert type="warning" message="접근 권한이 없습니다." description="필요한 권한이 없거나 현재 계정으로 접근할 수 없는 화면입니다." showIcon />;
}
