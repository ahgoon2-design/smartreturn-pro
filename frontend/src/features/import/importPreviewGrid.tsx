import type { SmartDataGridColumn } from "../../components/grid";
import type { ImportJobRow, ImportValidationError } from "../../types/import";

export type ImportPreviewRowFilter = "ALL" | "ERROR" | "WARNING";
export type ImportPreviewMessageFormatter = (message: string, row: ImportJobRow, rowErrors: ImportValidationError[]) => string;

const VALIDATION_STATUS_MAP = {
  VALID: { label: "정상", status: "VALID" },
  WARNING: { label: "경고", status: "WARNING" },
  INVALID: { label: "오류", status: "INVALID" },
  NOT_VALIDATED: { label: "검증 전", status: "NOT_VALIDATED" },
};

// 기존 상품/바코드 import 화면이 쓰는 기본 데이터 컬럼. fieldColumns 미지정 시 그대로 유지한다.
const DEFAULT_PREVIEW_FIELD_COLUMNS: Array<{ key: string; title?: string }> = [
  { key: "product_code" },
  { key: "product_name" },
  { key: "barcode" },
  { key: "primary_barcode" },
  { key: "additional_barcode" },
  { key: "carton_barcode" },
  { key: "barcode_type" },
  { key: "unit_qty" },
];

export function createImportPreviewColumns(
  errors: ImportValidationError[],
  fieldColumns?: Array<{ key: string; title?: string }>,
  formatMessage?: ImportPreviewMessageFormatter,
): SmartDataGridColumn<ImportJobRow>[] {
  const dataColumns = (fieldColumns?.length ? fieldColumns : DEFAULT_PREVIEW_FIELD_COLUMNS).map<SmartDataGridColumn<ImportJobRow>>(
    (field) => ({
      key: field.key,
      title: field.title || field.key,
      render: (_value, row) => readImportRowValue(row, field.key),
      copyable: true,
    }),
  );
  return [
    { key: "row_no", title: "행번호", dataIndex: "row_no", width: 72, fixed: "left", sortable: true },
    {
      key: "validation_status",
      title: "상태",
      dataIndex: "validation_status",
      width: 110,
      renderType: "status",
      statusMap: VALIDATION_STATUS_MAP,
    },
    {
      key: "error_warning_count",
      title: "오류/경고",
      width: 92,
      render: (_value, row) => summarizeImportPreviewRowIssues(errors, row),
      errorHighlight: (row) => getImportPreviewRowSeverity(errors, row) === "ERROR",
      warningHighlight: (row) => getImportPreviewRowSeverity(errors, row) === "WARNING",
    },
    ...dataColumns,
    {
      key: "validation_message",
      title: "처리 메시지",
      render: (_value, row) => getImportPreviewRowMessage(errors, row, formatMessage),
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

export function getImportPreviewRowSeverity(errors: ImportValidationError[], row: ImportJobRow) {
  const rowErrors = getRowErrors(errors, row);
  if (row.validation_status === "INVALID" || rowErrors.some((item) => item.severity === "ERROR")) {
    return "ERROR";
  }
  if (row.validation_status === "WARNING" || rowErrors.some((item) => item.severity === "WARNING")) {
    return "WARNING";
  }
  return "";
}

export function getRowErrors(errors: ImportValidationError[], row: ImportJobRow) {
  return errors.filter((item) => item.row_id === row.row_id || item.row_id === row.id || item.row_no === row.row_no);
}

export function countRowsBySeverity(errors: ImportValidationError[], severity: string) {
  return new Set(errors.filter((item) => item.severity === severity).map((item) => item.row_id || item.row_no)).size;
}

function summarizeImportPreviewRowIssues(errors: ImportValidationError[], row: ImportJobRow) {
  const rowErrors = getRowErrors(errors, row);
  const errorCount = rowErrors.filter((item) => item.severity === "ERROR").length;
  const warningCount = rowErrors.filter((item) => item.severity === "WARNING").length;
  if (errorCount === 0 && warningCount === 0) {
    return "";
  }
  return `오류 ${errorCount} / 경고 ${warningCount}`;
}

function getImportPreviewRowMessage(errors: ImportValidationError[], row: ImportJobRow, formatMessage?: ImportPreviewMessageFormatter) {
  const rowErrors = getRowErrors(errors, row);
  if (row.validation_message) {
    return formatMessage ? formatMessage(row.validation_message, row, rowErrors) : row.validation_message;
  }
  return rowErrors
    .map((item) => {
      const message = item.error_message || item.error_code;
      return formatMessage ? formatMessage(message, row, rowErrors) : message;
    })
    .join(", ");
}

function readImportRowValue(row: ImportJobRow, key: string) {
  const data = row.normalized_json || row.raw_json || {};
  const value = data[key];
  return value === null || value === undefined ? "" : String(value);
}
