import { Alert } from "antd";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";

export function DashboardPage() {
  return (
    <SmartPage>
      <SmartPageHeader title="Dashboard" description="업무 홈 화면은 후속 작업에서 연결합니다." />
      <Alert type="info" message="대시보드 준비중" showIcon />
    </SmartPage>
  );
}
