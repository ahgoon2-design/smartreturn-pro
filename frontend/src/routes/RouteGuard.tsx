import type { ReactNode } from "react";
import { Alert } from "antd";
import { useAuth } from "../context/AuthContext";

interface RouteGuardProps {
  children: ReactNode;
}

export function RouteGuard({ children }: RouteGuardProps) {
  const { loading, authContext } = useAuth();

  if (loading) {
    return <Alert type="info" message="인증 상태를 확인하는 중입니다." showIcon />;
  }

  return (
    <>
      {!authContext ? (
        <Alert
          className="smart-auth-banner"
          type="warning"
          message="인증 연동 준비중"
          description="현재 화면은 프론트 스캐폴드 단계입니다. API 호출은 기존 로그인에서 저장된 인증 토큰이 있을 때만 동작합니다."
          showIcon
        />
      ) : null}
      {children}
    </>
  );
}
