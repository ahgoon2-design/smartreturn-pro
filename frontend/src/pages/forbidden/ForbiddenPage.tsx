import { Button, Result } from "antd";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "../../routes/routePaths";

export function ForbiddenPage() {
  return (
    <Result
      status="403"
      title="접근 권한이 없습니다."
      subTitle="현재 계정으로 접근할 수 없는 화면입니다. 필요한 권한이 있으면 관리자에게 요청해 주세요."
      extra={
        <Link to={ROUTE_PATHS.importPreview}>
          <Button type="primary">기본 화면으로 이동</Button>
        </Link>
      }
    />
  );
}
