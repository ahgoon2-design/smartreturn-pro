import { Button, Result } from "antd";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "../../routes/routePaths";

export function NotFoundPage() {
  return (
    <Result
      status="404"
      title="화면을 찾을 수 없습니다"
      subTitle="요청한 경로가 아직 등록되지 않았습니다."
      extra={
        <Link to={ROUTE_PATHS.importPreview}>
          <Button type="primary">Import Preview로 이동</Button>
        </Link>
      }
    />
  );
}
