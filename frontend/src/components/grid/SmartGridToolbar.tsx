import { Button, Space } from "antd";
import { SortAscendingOutlined } from "@ant-design/icons";
import type { ReactNode } from "react";

export function SmartGridToolbar({
  enableOriginalOrderReset,
  onOriginalOrderReset,
  footerActions,
}: {
  enableOriginalOrderReset?: boolean;
  onOriginalOrderReset?: () => void;
  footerActions?: ReactNode;
}) {
  if (!enableOriginalOrderReset && !footerActions) {
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
        {footerActions}
      </Space>
    </div>
  );
}
