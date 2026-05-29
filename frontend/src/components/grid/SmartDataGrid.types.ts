import type { Key, ReactNode } from "react";
import type { TablePaginationConfig } from "antd";

export type SmartGridDensity = "compact" | "standard" | "comfortable";

export type SmartGridAlign = "left" | "center" | "right";

export type SmartGridRenderType = "text" | "number" | "date" | "status" | "action" | "tag" | "money";

export type SmartGridRowKey<TRecord extends object> = keyof TRecord | ((record: TRecord) => Key);

export type SmartGridOriginalOrderKey<TRecord extends object> =
  | keyof TRecord
  | string
  | ((record: TRecord) => number | string | null | undefined);

export interface SmartGridStatusMapItem {
  label: string;
  status?: string;
}

export interface SmartDataGridColumn<TRecord extends object> {
  key: string;
  title: ReactNode;
  dataIndex?: keyof TRecord | string | Array<string | number>;
  width?: number | string;
  minWidth?: number;
  align?: SmartGridAlign;
  render?: (value: unknown, record: TRecord, index: number) => ReactNode;
  renderType?: SmartGridRenderType;
  statusMap?: Record<string, SmartGridStatusMapItem>;
  sortable?: boolean | ((left: TRecord, right: TRecord) => number);
  copyable?: boolean;
  tooltip?: ReactNode;
  fixed?: "left" | "right";
  errorHighlight?: boolean | ((record: TRecord) => boolean);
  warningHighlight?: boolean | ((record: TRecord) => boolean);
  className?: string;
}

export interface SmartGridRowAction<TRecord extends object> {
  key: string;
  label: ReactNode;
  icon?: ReactNode;
  danger?: boolean;
  disabled?: boolean | ((record: TRecord) => boolean);
  onClick: (record: TRecord) => void;
}

export interface SmartDataGridProps<TRecord extends object> {
  rows?: TRecord[];
  dataSource?: TRecord[];
  columns: SmartDataGridColumn<TRecord>[];
  rowKey: SmartGridRowKey<TRecord>;
  loading?: boolean;
  error?: string | Error | null;
  emptyText?: ReactNode;
  selectedRowKeys?: Key[];
  onSelectionChange?: (selectedRowKeys: Key[], selectedRows: TRecord[]) => void;
  onRowClick?: (record: TRecord) => void;
  rowActions?: SmartGridRowAction<TRecord>[];
  pagination?: false | TablePaginationConfig;
  preserveOriginalOrder?: boolean;
  originalOrderKey?: SmartGridOriginalOrderKey<TRecord>;
  enableOriginalOrderReset?: boolean;
  density?: SmartGridDensity;
  stickyHeader?: boolean;
  maxHeight?: number;
  getRowClassName?: (record: TRecord, index: number) => string;
  footerActions?: ReactNode;
  enableCopy?: boolean;
  enableMultiSelect?: boolean;
  className?: string;
}
