import { Button, Space } from "antd";
import { DownloadOutlined, SortAscendingOutlined } from "@ant-design/icons";
import type { ReactNode } from "react";

export function SmartGridToolbar({
  enableOriginalOrderReset,
  onOriginalOrderReset,
  onExcelDownload,
  footerActions,
}: {
  enableOriginalOrderReset?: boolean;
  onOriginalOrderReset?: () => void;
  onExcelDownload?: () => void;
  footerActions?: ReactNode;
}) {
  if (!enableOriginalOrderReset && !onExcelDownload && !footerActions) {
    return null;
  }

  return (
    <div className="smart-grid-toolbar">
      <Space size={8}>
        {enableOriginalOrderReset ? (
          <Button size="small" icon={<SortAscendingOutlined />} onClick={onOriginalOrderReset}>
            원본 순서
          </Button>
        ) : null}
        {onExcelDownload ? (
          <Button size="small" icon={<DownloadOutlined />} onClick={onExcelDownload}>
            엑셀 다운로드
          </Button>
        ) : null}
        {footerActions}
      </Space>
    </div>
  );
}
