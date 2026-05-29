import type { SmartDataGridColumn } from "../../components/grid";
import type { ImportJobRow, ImportValidationError } from "../../types/import";

export type ImportPreviewRowFilter = "ALL" | "ERROR" | "WARNING";

export function createImportPreviewColumns(errors: ImportValidationError[]): SmartDataGridColumn<ImportJobRow>[] {
  return [
    { key: "row_no", title: "행번호", dataIndex: "row_no", width: 72, fixed: "left", sortable: true },
    {
      key: "validation_status",
      title: "상태",
      dataIndex: "validation_status",
      width: 110,
      renderType: "status",
    },
    {
      key: "error_warning_count",
      title: "오류/경고",
      width: 92,
      render: (_value, row) => getRowErrors(errors, row).length,
      errorHighlight: (row) => getImportPreviewRowSeverity(errors, row) === "ERROR",
      warningHighlight: (row) => getImportPreviewRowSeverity(errors, row) === "WARNING",
    },
    {
      key: "product_code",
      title: "product_code",
      render: (_value, row) => readImportRowValue(row, "product_code"),
      copyable: true,
    },
    {
      key: "product_name",
      title: "product_name",
      render: (_value, row) => readImportRowValue(row, "product_name"),
      copyable: true,
    },
    {
      key: "barcode",
      title: "barcode",
      render: (_value, row) => readImportRowValue(row, "barcode"),
      copyable: true,
    },
    {
      key: "barcode_type",
      title: "barcode_type",
      render: (_value, row) => readImportRowValue(row, "barcode_type"),
      copyable: true,
    },
    {
      key: "unit_qty",
      title: "unit_qty",
      render: (_value, row) => readImportRowValue(row, "unit_qty"),
      copyable: true,
    },
    {
      key: "validation_message",
      title: "처리 메시지",
      render: (_value, row) => getImportPreviewRowMessage(errors, row),
      errorHighlight: (row) => getImportPreviewRowSeverity(errors, row) === "ERROR",
      warningHighlight: (row) => getImportPreviewRowSeverity(errors, row) === "WARNING",
    },
  ];
}

export function filterImportPreviewRows(rows: ImportJobRow[], errors: ImportValidationError[], rowFilter: ImportPreviewRowFilter) {
  const orderedRows = [...rows].sort((left, right) => left.row_no - right.row_no);
  if (rowFilter === "ERROR") {
    return orderedRows.filter((row) => getImportPreviewRowSeverity(errors, row) === "ERROR");
  }
  if (rowFilter === "WARNING") {
    return orderedRows.filter((row) => getImportPreviewRowSeverity(errors, row) === "WARNING");
  }
  return orderedRows;
}

export function getImportPreviewRowClassName(errors: ImportValidationError[], row: ImportJobRow) {
  const severity = getImportPreviewRowSeverity(errors, row);
  if (severity === "ERROR") {
    return "smart-grid-row-error";
  }
  if (severity === "WARNING") {
    return "smart-grid-row-warning";
  }
  return "";
}

export function getRowErrors(errors: ImportValidationError[], row: ImportJobRow) {
  return errors.filter((item) => item.row_id === row.row_id || item.row_id === row.id || item.row_no === row.row_no);
}

export function countRowsBySeverity(errors: ImportValidationError[], severity: string) {
  return new Set(errors.filter((item) => item.severity === severity).map((item) => item.row_id || item.row_no)).size;
}

function getImportPreviewRowSeverity(errors: ImportValidationError[], row: ImportJobRow) {
  const rowErrors = getRowErrors(errors, row);
  if (row.validation_status === "INVALID" || rowErrors.some((item) => item.severity === "ERROR")) {
    return "ERROR";
  }
  if (row.validation_status === "WARNING" || rowErrors.some((item) => item.severity === "WARNING")) {
    return "WARNING";
  }
  return "";
}

function getImportPreviewRowMessage(errors: ImportValidationError[], row: ImportJobRow) {
  if (row.validation_message) {
    return row.validation_message;
  }
  return getRowErrors(errors, row)
    .map((item) => item.error_code)
    .join(", ");
}

function readImportRowValue(row: ImportJobRow, key: string) {
  const data = row.normalized_json || row.raw_json || {};
  const value = data[key];
  return value === null || value === undefined ? "" : String(value);
}
