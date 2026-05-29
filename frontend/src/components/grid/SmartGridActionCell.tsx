import { Button, Space } from "antd";
import type { SmartGridRowAction } from "./SmartDataGrid.types";

export function SmartGridActionCell<TRecord extends object>({ actions, record }: { actions: SmartGridRowAction<TRecord>[]; record: TRecord }) {
  return (
    <Space size={4} className="smart-grid-action-cell">
      {actions.map((action) => {
        const disabled = typeof action.disabled === "function" ? action.disabled(record) : action.disabled;
        return (
          <Button
            key={action.key}
            size="small"
            type="text"
            danger={action.danger}
            disabled={disabled}
            icon={action.icon}
            onClick={(event) => {
              event.stopPropagation();
              action.onClick(record);
            }}
          >
            {action.label}
          </Button>
        );
      })}
    </Space>
  );
}
