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
  /** 엑셀 다운로드 포함 여부. 기본은 dataIndex 또는 exportValue가 있으면 포함. 액션/사진/버튼 컬럼은 false로 둔다. */
  exportable?: boolean;
  /** 엑셀 다운로드 헤더 라벨. 생략 시 문자열 title을 사용한다. */
  exportHeader?: string;
  /** 엑셀 다운로드 셀 값. 생략 시 dataIndex 값을 사용한다(상태/판정 등은 한글 라벨 권장). */
  exportValue?: (record: TRecord) => string | number | null | undefined;
  /** 운송장번호/상품코드/바코드처럼 숫자로 깨지면 안 되는 값은 true로 두어 문자열로 내보낸다. */
  exportAsText?: boolean;
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
  /** 값이 있으면 조회형 그리드에 "엑셀 다운로드" 버튼을 표시하고, 이 값을 파일명으로 사용한다. */
  exportFileName?: string;
  enableMultiSelect?: boolean;
  className?: string;
}
