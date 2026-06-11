import { getRecordValue } from "./SmartDataGrid.helpers";
import type { SmartDataGridColumn } from "./SmartDataGrid.types";

/**
 * SmartDataGrid 공통 엑셀(CSV) 다운로드 유틸.
 *
 * - 화면별 중복 구현 없이 컬럼/행 정의만으로 다운로드를 만든다.
 * - 액션/사진/버튼 전용 컬럼(dataIndex·exportValue 없음 또는 exportable=false)은 제외한다.
 * - 운송장번호/상품코드/바코드 등은 exportAsText로 문자열 보존(Excel 숫자 변환 방지).
 * - 현재 표시 순서(원본 정렬 포함)를 그대로 내보낸다.
 * - 외부 라이브러리 없이 CSV로 구현하되 UI 문구는 "엑셀 다운로드"로 사용한다.
 */

function isExportableColumn<TRecord extends object>(column: SmartDataGridColumn<TRecord>): boolean {
  if (column.exportable === false) {
    return false;
  }
  return Boolean(column.dataIndex) || typeof column.exportValue === "function";
}

function toHeaderLabel<TRecord extends object>(column: SmartDataGridColumn<TRecord>): string {
  if (column.exportHeader) {
    return column.exportHeader;
  }
  if (typeof column.title === "string") {
    return column.title;
  }
  return column.key;
}

function toCellString<TRecord extends object>(column: SmartDataGridColumn<TRecord>, record: TRecord): string {
  const raw = column.exportValue
    ? column.exportValue(record)
    : getRecordValue(record, column.dataIndex as string | Array<string | number>);
  if (raw === null || raw === undefined) {
    return "";
  }
  return String(raw);
}

function escapeCsvField(value: string): string {
  return `"${value.replace(/"/g, '""')}"`;
}

function toCsvField<TRecord extends object>(column: SmartDataGridColumn<TRecord>, record: TRecord): string {
  const value = toCellString(column, record);
  if (value === "") {
    return '""';
  }
  // 문자열 보존이 필요한 컬럼은 Excel에서 ="..." 수식으로 인식되어 숫자 변환을 막는다.
  if (column.exportAsText) {
    return escapeCsvField(`="${value.replace(/"/g, '""')}"`);
  }
  return escapeCsvField(value);
}

export function buildGridCsv<TRecord extends object>(
  columns: SmartDataGridColumn<TRecord>[],
  rows: TRecord[],
): string {
  const exportColumns = columns.filter(isExportableColumn);
  const header = exportColumns.map((column) => escapeCsvField(toHeaderLabel(column))).join(",");
  const body = rows.map((record) => exportColumns.map((column) => toCsvField(column, record)).join(",")).join("\r\n");
  return body ? `${header}\r\n${body}` : header;
}

export function downloadGridCsv(fileName: string, csv: string): void {
  // UTF-8 BOM을 붙여 Excel에서 한글이 깨지지 않게 한다.
  const blob = new Blob(["﻿", csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  const stamp = new Date().toISOString().slice(0, 10);
  anchor.href = url;
  anchor.download = `${fileName}_${stamp}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
