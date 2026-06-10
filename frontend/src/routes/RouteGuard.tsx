import type { ReactNode } from "react";
import { Alert, Spin } from "antd";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ROUTE_PATHS } from "./routePaths";

type RouteArea = "internal" | "portal";

interface AreaUserFlags {
  isClientUser: boolean;
  isInternalUser: boolean;
  isPlatformAdmin: boolean;
}

/**
 * 로그인 사용자 유형에 맞는 기본 진입 경로를 반환한다.
 * 고객 사용자는 고객 포털, 그 외(내부 운영자/대리점/플랫폼 관리자)는 내부 대시보드로 보낸다.
 */
export function resolveHomePathForUser(flags: AreaUserFlags | null | undefined): string {
  if (flags?.isClientUser) {
    return ROUTE_PATHS.portalDashboard;
  }
  return ROUTE_PATHS.dashboard;
}

function isAllowedInArea(area: RouteArea | undefined, flags: AreaUserFlags): boolean {
  if (!area) {
    return true;
  }
  if (area === "internal") {
    // 고객 사용자는 내부 운영자 화면에 접근할 수 없다.
    return !flags.isClientUser;
  }
  // area === "portal": 고객 사용자(기본) + 내부/플랫폼 관리자(미리보기) 허용.
  return flags.isClientUser || flags.isInternalUser || flags.isPlatformAdmin;
}

interface ProtectedRouteProps {
  children: ReactNode;
  requiredPermissions?: string[];
  allowWhenMustChangePassword?: boolean;
  /** 화면이 속한 영역. 내부 운영자/고객 포털 접근 분리에 사용한다. */
  area?: RouteArea;
}

export function ProtectedRoute({
  children,
  requiredPermissions,
  allowWhenMustChangePassword = false,
  area,
}: ProtectedRouteProps) {
  const { loading, isAuthenticated, mustChangePassword, canAccess, isClientUser, isInternalUser, isPlatformAdmin } =
    useAuth();
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

  const flags = { isClientUser, isInternalUser, isPlatformAdmin };
  // 사용자 유형이 영역과 맞지 않으면 차단 대신 본인 기본 화면으로 안전하게 보낸다.
  if (!isAllowedInArea(area, flags)) {
    return <Navigate to={resolveHomePathForUser(flags)} replace />;
  }

  if (!canAccess(requiredPermissions)) {
    return <Navigate to={ROUTE_PATHS.forbidden} replace />;
  }

  return <>{children}</>;
}

export function PublicRoute({ children }: { children: ReactNode }) {
  const { loading, isAuthenticated, mustChangePassword, isClientUser, isInternalUser, isPlatformAdmin } = useAuth();

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
    return <Navigate to={resolveHomePathForUser({ isClientUser, isInternalUser, isPlatformAdmin })} replace />;
  }

  return <>{children}</>;
}

export function ForbiddenNotice() {
  return <Alert type="warning" message="접근 권한이 없습니다." description="필요한 권한이 없거나 현재 계정으로 접근할 수 없는 화면입니다." showIcon />;
}
