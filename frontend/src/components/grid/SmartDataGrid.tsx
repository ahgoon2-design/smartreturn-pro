import { Table } from "antd";
import type { ColumnsType } from "antd/es/table";

interface SmartDataGridProps<TRecord extends object> {
  rowKey: keyof TRecord | ((record: TRecord) => string | number);
  columns: ColumnsType<TRecord>;
  dataSource: TRecord[];
  loading?: boolean;
}

export function SmartDataGrid<TRecord extends object>({ rowKey, columns, dataSource, loading }: SmartDataGridProps<TRecord>) {
  return (
    <Table<TRecord>
      className="smart-data-grid"
      rowKey={rowKey}
      columns={columns}
      dataSource={dataSource}
      loading={loading}
      pagination={false}
      size="small"
      scroll={{ x: 960, y: 320 }}
    />
  );
}
