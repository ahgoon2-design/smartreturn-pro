import { Button, Result } from "antd";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "../../routes/routePaths";

export function LoginPlaceholderPage() {
  return (
    <Result
      status="info"
      title="로그인 화면 준비중"
      subTitle="이번 스캐폴드에서는 실제 로그인 구현을 포함하지 않습니다. 기존 로그인 흐름에서 저장된 인증 토큰이 있으면 API 호출을 사용할 수 있습니다."
      extra={
        <Link to={ROUTE_PATHS.importPreview}>
          <Button type="primary">Import Preview로 이동</Button>
        </Link>
      }
    />
  );
}
