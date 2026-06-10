import type { Key, ReactNode } from "react";
import type { ColumnType } from "antd/es/table/interface";
import { Button, Space, Tooltip, message } from "antd";
import { CopyOutlined } from "@ant-design/icons";
import { SmartGridStatusCell } from "./SmartGridStatusCell";
import type { SmartDataGridColumn, SmartGridOriginalOrderKey, SmartGridRowKey } from "./SmartDataGrid.types";

export function getSmartRowKey<TRecord extends object>(rowKey: SmartGridRowKey<TRecord>, record: TRecord): Key {
  if (typeof rowKey === "function") {
    return rowKey(record);
  }
  return getRecordValue(record, rowKey as string) as Key;
}

export function sortByOriginalOrder<TRecord extends object>(
  rows: TRecord[],
  originalOrderKey?: SmartGridOriginalOrderKey<TRecord>,
) {
  if (!originalOrderKey) {
    return [...rows];
  }
  return [...rows].sort((left, right) => compareOriginalOrder(getOriginalOrderValue(left, originalOrderKey), getOriginalOrderValue(right, originalOrderKey)));
}

export function toAntTableColumns<TRecord extends object>(
  columns: SmartDataGridColumn<TRecord>[],
  enableCopy?: boolean,
): ColumnType<TRecord>[] {
  return columns.map((column) => {
    const antColumn: ColumnType<TRecord> = {
      key: column.key,
      title: column.tooltip ? <Tooltip title={column.tooltip}>{column.title}</Tooltip> : column.title,
      dataIndex: column.dataIndex as ColumnType<TRecord>["dataIndex"],
      width: column.width,
      minWidth: column.minWidth,
      align: column.align as ColumnType<TRecord>["align"],
      fixed: column.fixed,
      className: column.className,
      sorter: typeof column.sortable === "function" ? column.sortable : column.sortable ? defaultColumnSorter(column.dataIndex) : undefined,
      render: (value: unknown, record: TRecord, index: number) => {
        const renderedValue = renderSmartCell(column, value, record, index);
        if (enableCopy && column.copyable) {
          return <CopyableCell value={getCopyText(value, renderedValue)}>{renderedValue}</CopyableCell>;
        }
        return renderedValue;
      },
      onCell: (record) => ({
        className: getCellHighlightClassName(column, record),
      }),
    };
    return antColumn;
  });
}

export function getRecordValue(record: object, dataIndex?: string | Array<string | number>) {
  if (!dataIndex) {
    return undefined;
  }
  if (Array.isArray(dataIndex)) {
    return dataIndex.reduce<unknown>((current, key) => {
      if (current && typeof current === "object") {
        return (current as Record<string, unknown>)[String(key)];
      }
      return undefined;
    }, record);
  }
  return dataIndex.split(".").reduce<unknown>((current, key) => {
    if (current && typeof current === "object") {
      return (current as Record<string, unknown>)[key];
    }
    return undefined;
  }, record);
}

function renderSmartCell<TRecord extends object>(column: SmartDataGridColumn<TRecord>, value: unknown, record: TRecord, index: number) {
  if (column.render) {
    return column.render(value, record, index);
  }
  if (column.renderType === "status") {
    const statusValue = value === null || value === undefined ? "" : String(value);
    const mapped = column.statusMap?.[statusValue];
    return <SmartGridStatusCell status={mapped?.status || statusValue} label={mapped?.label} />;
  }
  if (value === null || value === undefined || value === "") {
    return "";
  }
  return String(value);
}

function CopyableCell({ value, children }: { value: string; children: ReactNode }) {
  async function handleCopy() {
    if (!value) {
      return;
    }
    // 민감값은 column.copyable을 켜지 않는 것을 기본 원칙으로 둔다.
    await navigator.clipboard.writeText(value);
    message.success("셀 값을 복사했습니다.");
  }

  return (
    <Space size={4} className="smart-grid-copy-cell">
      <span>{children}</span>
      <Button aria-label="셀 값 복사" size="small" type="text" icon={<CopyOutlined />} onClick={handleCopy} />
    </Space>
  );
}

function getCopyText(value: unknown, renderedValue: ReactNode) {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (typeof renderedValue === "string" || typeof renderedValue === "number") {
    return String(renderedValue);
  }
  return "";
}

function getOriginalOrderValue<TRecord extends object>(record: TRecord, originalOrderKey: SmartGridOriginalOrderKey<TRecord>) {
  if (typeof originalOrderKey === "function") {
    return originalOrderKey(record);
  }
  return getRecordValue(record, String(originalOrderKey));
}

function compareOriginalOrder(left: unknown, right: unknown) {
  const leftNumber = Number(left);
  const rightNumber = Number(right);
  if (Number.isFinite(leftNumber) && Number.isFinite(rightNumber)) {
    return leftNumber - rightNumber;
  }
  return String(left ?? "").localeCompare(String(right ?? ""));
}

function defaultColumnSorter<TRecord extends object>(dataIndex?: SmartDataGridColumn<TRecord>["dataIndex"]) {
  return (left: TRecord, right: TRecord) => {
    const leftValue = getRecordValue(left, dataIndex as string | Array<string | number>);
    const rightValue = getRecordValue(right, dataIndex as string | Array<string | number>);
    if (typeof leftValue === "number" && typeof rightValue === "number") {
      return leftValue - rightValue;
    }
    return String(leftValue ?? "").localeCompare(String(rightValue ?? ""));
  };
}

function getCellHighlightClassName<TRecord extends object>(column: SmartDataGridColumn<TRecord>, record: TRecord) {
  const classes: string[] = [];
  if (typeof column.errorHighlight === "function" ? column.errorHighlight(record) : column.errorHighlight) {
    classes.push("smart-grid-cell-error");
  }
  if (typeof column.warningHighlight === "function" ? column.warningHighlight(record) : column.warningHighlight) {
    classes.push("smart-grid-cell-warning");
  }
  return classes.join(" ");
}
