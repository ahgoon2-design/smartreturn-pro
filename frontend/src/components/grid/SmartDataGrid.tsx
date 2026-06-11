import { Alert, Empty, Table } from "antd";
import type { Key } from "react";
import { useMemo, useState } from "react";
import { SmartGridActionCell } from "./SmartGridActionCell";
import { getSmartRowKey, sortByOriginalOrder, toAntTableColumns } from "./SmartDataGrid.helpers";
import { buildGridCsv, downloadGridCsv } from "./SmartDataGrid.export";
import { SmartGridToolbar } from "./SmartGridToolbar";
import type { SmartDataGridColumn, SmartDataGridProps } from "./SmartDataGrid.types";
import "./SmartDataGrid.css";

export function SmartDataGrid<TRecord extends object>({
  rows,
  dataSource,
  columns,
  rowKey,
  loading,
  error,
  emptyText = "표시할 데이터가 없습니다.",
  selectedRowKeys,
  onSelectionChange,
  onRowClick,
  rowActions,
  pagination = false,
  preserveOriginalOrder,
  originalOrderKey,
  enableOriginalOrderReset,
  density = "compact",
  stickyHeader,
  maxHeight = 320,
  getRowClassName,
  footerActions,
  enableCopy,
  exportFileName,
  enableMultiSelect = true,
  className,
}: SmartDataGridProps<TRecord>) {
  const [tableVersion, setTableVersion] = useState(0);
  const sourceRows = rows ?? dataSource ?? [];
  const orderedRows = useMemo(() => {
    if (preserveOriginalOrder && originalOrderKey) {
      return sortByOriginalOrder(sourceRows, originalOrderKey);
    }
    return [...sourceRows];
  }, [originalOrderKey, preserveOriginalOrder, sourceRows]);

  const antColumns = useMemo(() => {
    const baseColumns = toAntTableColumns(columns, enableCopy);
    if (!rowActions || rowActions.length === 0) {
      return baseColumns;
    }
    return [
      ...baseColumns,
      {
        key: "__smart_grid_actions",
        title: "작업",
        width: 120,
        fixed: "right" as const,
        render: (_: unknown, record: TRecord) => <SmartGridActionCell actions={rowActions} record={record} />,
      },
    ];
  }, [columns, enableCopy, rowActions]);

  const rowSelection =
    selectedRowKeys || onSelectionChange
      ? {
          selectedRowKeys,
          type: enableMultiSelect ? ("checkbox" as const) : ("radio" as const),
          onChange: (nextSelectedRowKeys: Key[], selectedRows: TRecord[]) => onSelectionChange?.(nextSelectedRowKeys, selectedRows),
        }
      : undefined;

  const gridClassName = ["smart-data-grid", `smart-data-grid--${density}`, stickyHeader ? "smart-data-grid--sticky-header" : "", className || ""]
    .filter(Boolean)
    .join(" ");

  function handleOriginalOrderReset() {
    setTableVersion((value) => value + 1);
  }

  function handleExcelDownload() {
    // 현재 표시 중인 행(원본 정렬 포함)과 컬럼 정의 기준으로 다운로드한다.
    downloadGridCsv(exportFileName as string, buildGridCsv(columns, orderedRows));
  }

  return (
    <div className={gridClassName}>
      <SmartGridToolbar
        enableOriginalOrderReset={enableOriginalOrderReset}
        onOriginalOrderReset={handleOriginalOrderReset}
        onExcelDownload={exportFileName && orderedRows.length > 0 ? handleExcelDownload : undefined}
        footerActions={footerActions}
      />
      {error ? <Alert className="smart-grid-error" type="error" showIcon message={toSafeErrorMessage(error)} /> : null}
      <Table<TRecord>
        key={tableVersion}
        rowKey={(record) => getSmartRowKey(rowKey, record)}
        columns={antColumns}
        dataSource={orderedRows}
        loading={loading}
        pagination={pagination}
        size={density === "comfortable" ? "middle" : "small"}
        rowSelection={rowSelection}
        locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyText} /> }}
        scroll={{ x: "max-content", y: maxHeight }}
        onRow={(record) => ({
          onClick: () => onRowClick?.(record),
        })}
        rowClassName={(record, index) => ["smart-grid-row", getRowClassName?.(record, index) || ""].filter(Boolean).join(" ")}
      />
    </div>
  );
}

export type { SmartDataGridColumn, SmartDataGridProps };

function toSafeErrorMessage(error: string | Error) {
  if (typeof error === "string") {
    return error;
  }
  return error.message || "그리드 데이터를 표시하는 중 오류가 발생했습니다.";
}
