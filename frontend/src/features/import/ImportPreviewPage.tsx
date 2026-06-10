import { CheckCircleOutlined, ReloadOutlined, SaveOutlined, SearchOutlined, UploadOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Input, Modal, Select, Space, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import {
  confirmImportJob,
  createImportJob,
  listImportJobErrors,
  listImportJobRows,
  savePasteRows,
  uploadImportExcelFile,
  validateImportJob,
} from "../../api/importJobs";
import { ApiClientError } from "../../api/client";
import { listClients } from "../../api/master";
import { SmartActionBar } from "../../components/common/SmartActionBar";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartSummaryCard } from "../../components/common/SmartSummaryCard";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { ClientSummary } from "../../types/master";
import type {
  ImportJob,
  ImportJobRow,
  ImportPasteRowItem,
  ImportType,
  SourceType,
  ImportConfirmResponse,
  ImportExcelUploadResponse,
  ImportValidationError,
  ImportValidationRunResponse,
} from "../../types/import";
import {
  countRowsBySeverity,
  createImportPreviewColumns,
  filterImportPreviewRows,
  getImportPreviewRowClassName,
  getRowErrors,
  type ImportPreviewRowFilter,
} from "./importPreviewGrid";

const IMPORT_TYPES: ImportType[] = ["PRODUCT_MASTER", "PRODUCT_BARCODE"];
const SOURCE_TYPES: SourceType[] = ["PASTE", "EXCEL_FILE"];

const ERROR_MESSAGES: Record<string, string> = {
  NOT_AUTHENTICATED: "로그인이 필요합니다. 기존 인증 화면에서 로그인한 뒤 다시 시도해 주세요.",
  INVALID_TOKEN: "로그인 정보가 만료되었거나 올바르지 않습니다. 다시 로그인해 주세요.",
  IMPORT_JOB_NOT_FOUND: "Import job을 찾을 수 없습니다.",
  IMPORT_JOB_VALIDATE_ALREADY_DONE: "이미 검증이 완료된 자료입니다.",
  IMPORT_JOB_VALIDATE_FORCE_UNSUPPORTED: "강제 재검증은 아직 지원하지 않습니다.",
  IMPORT_JOB_VALIDATE_SOURCE_TYPE_INVALID: "현재 source_type에서는 검증을 실행할 수 없습니다.",
  IMPORT_JOB_VALIDATE_STATUS_INVALID: "현재 상태에서는 검증을 실행할 수 없습니다.",
  IMPORT_JOB_VALIDATE_NO_ROWS: "검증할 row가 없습니다.",
  IMPORT_JOB_EXCEL_FILE_REQUIRED: "엑셀 파일을 선택해 주세요.",
  IMPORT_JOB_EXCEL_FILE_TYPE_INVALID: ".xlsx 파일만 지원합니다.",
  IMPORT_JOB_EXCEL_FILE_INVALID: "엑셀 파일을 읽을 수 없습니다.",
  IMPORT_JOB_EXCEL_NO_ROWS: "엑셀 파일에 저장할 데이터 row가 없습니다.",
  IMPORT_JOB_EXCEL_HEADERS_REQUIRED: "엑셀 첫 번째 행에 헤더가 필요합니다.",
  IMPORT_JOB_EXCEL_UPLOAD_SOURCE_TYPE_INVALID: "EXCEL_FILE source_type job에서만 엑셀 업로드를 실행할 수 있습니다.",
  IMPORT_JOB_EXCEL_UPLOAD_STATUS_INVALID: "현재 job 상태에서는 엑셀 업로드를 실행할 수 없습니다.",
  IMPORT_JOB_ROWS_ALREADY_EXISTS: "이미 rows가 저장된 job입니다.",
  IMPORT_JOB_CONFIRM_STATUS_INVALID: "검증 완료 후 확정할 수 있습니다.",
  IMPORT_JOB_CONFIRM_ALREADY_DONE: "이미 확정된 자료입니다.",
  IMPORT_JOB_CONFIRM_HAS_ERRORS: "오류 행이 있어 확정할 수 없습니다.",
  IMPORT_JOB_CONFIRM_NO_ROWS: "확정 반영할 row가 없습니다.",
  IMPORT_JOB_CONFIRM_UNSUPPORTED_TYPE: "현재 import_type은 확정 반영을 지원하지 않습니다.",
};

export function ImportPreviewPage() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [clientId, setClientId] = useState<number | null>(null);
  const [importType, setImportType] = useState<ImportType>("PRODUCT_MASTER");
  const [sourceType, setSourceType] = useState<SourceType>("PASTE");
  const [pasteText, setPasteText] = useState(samplePasteText);
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [excelUploadResult, setExcelUploadResult] = useState<ImportExcelUploadResponse | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [job, setJob] = useState<ImportJob | null>(null);
  const [rows, setRows] = useState<ImportJobRow[]>([]);
  const [errors, setErrors] = useState<ImportValidationError[]>([]);
  const [validationSummary, setValidationSummary] = useState<ImportValidationRunResponse | null>(null);
  const [confirmSummary, setConfirmSummary] = useState<ImportConfirmResponse | null>(null);
  const [rowFilter, setRowFilter] = useState<ImportPreviewRowFilter>("ALL");
  const [loadingClients, setLoadingClients] = useState(false);
  const [savingRows, setSavingRows] = useState(false);
  const [validating, setValidating] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [notice, setNotice] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [gridErrorMessage, setGridErrorMessage] = useState("");
  const [selectedRowKey, setSelectedRowKey] = useState<number | null>(null);

  const parsedRows = useMemo(() => parsePasteRows(pasteText), [pasteText]);
  const errorRows = useMemo(() => countRowsBySeverity(errors, "ERROR"), [errors]);
  const warningRows = useMemo(() => countRowsBySeverity(errors, "WARNING"), [errors]);
  const filteredRows = useMemo(() => filterImportPreviewRows(rows, errors, rowFilter), [errors, rowFilter, rows]);
  const columns = useMemo(() => createImportPreviewColumns(errors), [errors]);
  const selectedRow = useMemo(
    () => (selectedRowKey === null ? null : rows.find((row) => getRowId(row) === selectedRowKey) || null),
    [rows, selectedRowKey],
  );
  const selectedRowErrors = useMemo(() => (selectedRow ? getRowErrors(errors, selectedRow) : []), [errors, selectedRow]);
  const detailErrors = selectedRow ? selectedRowErrors : errors;
  const currentJobStatus = jobStatus(job);
  const confirmResult = useMemo(() => getConfirmResultSummary(confirmSummary, job), [confirmSummary, job]);
  const confirmHelpText = getConfirmHelpText(currentJobStatus, rows.length, confirming);

  useEffect(() => {
    setLoadingClients(true);
    listClients()
      .then((items) => {
        const activeClients = items.filter((client) => client.active_yn);
        setClients(activeClients);
        setClientId(getClientId(activeClients[0]) || null);
      })
      .catch((error) => setErrorMessage(toUserMessage(error)))
      .finally(() => setLoadingClients(false));
  }, []);

  const canSaveRows = Boolean(
    clientId &&
      importType &&
      !job &&
      (sourceType === "EXCEL_FILE" ? excelFile : pasteText.trim() && parsedRows.length > 0),
  );
  const canValidate = Boolean(currentJobStatus === "READY_TO_VALIDATE" && rows.length > 0 && !validating);
  const canConfirm = Boolean(currentJobStatus === "VALIDATED" && rows.length > 0 && !confirming);

  async function handleSaveRows() {
    if (!clientId) {
      return;
    }
    setSavingRows(true);
    clearMessages();
    try {
      const createdJob = await createImportJob({
        import_type: importType,
        source_type: sourceType,
        requested_client_id: clientId,
        source_name: sourceType === "EXCEL_FILE" ? excelFile?.name || "frontend-excel-preview" : "frontend-react-preview",
        file_name: sourceType === "EXCEL_FILE" ? excelFile?.name : undefined,
      });
      const nextJobId = getJobId(createdJob);
      if (sourceType === "EXCEL_FILE") {
        if (!excelFile) {
          throw new ApiClientError({
            resultCode: "IMPORT_JOB_EXCEL_FILE_REQUIRED",
            message: "엑셀 파일을 선택해 주세요.",
            status: 400,
          });
        }
        const uploadResult = await uploadImportExcelFile(nextJobId, excelFile);
        setExcelUploadResult(uploadResult);
        setJob({
          ...createdJob,
          ...uploadResult,
          id: createdJob.id,
          job_id: nextJobId,
          status: uploadResult.status,
          source_type: sourceType,
        });
        setNotice("엑셀 행을 저장했습니다. 검증을 실행할 수 있습니다.");
      } else {
        await savePasteRows(nextJobId, {
          rows: parsedRows,
          replace_existing: false,
          source_name: "frontend-react-preview",
        });
        setExcelUploadResult(null);
        setJob({ ...createdJob, status: "READY_TO_VALIDATE", total_rows: parsedRows.length, parsed_rows: parsedRows.length });
        setNotice("rows 저장이 완료되었습니다. 검증을 실행할 수 있습니다.");
      }
      setSelectedRowKey(null);
      setConfirmSummary(null);
      await refreshRowsAndErrors(nextJobId);
    } catch (error) {
      setErrorMessage(toUserMessage(error));
    } finally {
      setSavingRows(false);
    }
  }

  async function handleValidate() {
    if (!job) {
      return;
    }
    setValidating(true);
    clearMessages();
    try {
      const jobId = getJobId(job);
      const summary = await validateImportJob(jobId);
      setValidationSummary(summary);
      setConfirmSummary(null);
      setJob({ ...job, ...summary, id: job.id, job_id: jobId });
      setSelectedRowKey(null);
      await refreshRowsAndErrors(jobId);
      setNotice("검증이 완료되었습니다.");
    } catch (error) {
      setErrorMessage(toUserMessage(error));
    } finally {
      setValidating(false);
    }
  }

  function handleConfirmClick() {
    if (!job || !canConfirm) {
      return;
    }
    Modal.confirm({
      title: "확정 반영",
      content: "검증 완료된 VALID/WARNING row를 상품/바코드 마스터에 반영합니다. 계속할까요?",
      okText: "확정 반영",
      cancelText: "취소",
      onOk: runConfirm,
    });
  }

  async function runConfirm() {
    if (!job) {
      return;
    }
    setConfirming(true);
    clearMessages();
    try {
      const jobId = getJobId(job);
      const summary = await confirmImportJob(jobId);
      setConfirmSummary(summary);
      setJob({ ...job, ...summary, id: job.id, job_id: jobId });
      setSelectedRowKey(null);
      await refreshRowsAndErrors(jobId);
      setNotice("상품/바코드 마스터에 반영했습니다.");
    } catch (error) {
      setErrorMessage(toUserMessage(error));
      throw error;
    } finally {
      setConfirming(false);
    }
  }

  async function refreshRowsAndErrors(jobId: number) {
    try {
      const [rowsResult, errorsResult] = await Promise.all([listImportJobRows(jobId), listImportJobErrors(jobId)]);
      setRows([...(rowsResult.items || [])].sort((left, right) => left.row_no - right.row_no));
      setErrors([...(errorsResult.items || [])].sort((left, right) => left.row_no - right.row_no || getErrorId(left) - getErrorId(right)));
      setGridErrorMessage("");
    } catch (error) {
      const message = toUserMessage(error);
      setGridErrorMessage(message);
      throw error;
    }
  }

  function resetInput() {
    setPasteText("");
    setExcelFile(null);
    setExcelUploadResult(null);
    setFileInputKey((value) => value + 1);
    setJob(null);
    setRows([]);
    setErrors([]);
    setValidationSummary(null);
    setConfirmSummary(null);
    setRowFilter("ALL");
    setGridErrorMessage("");
    setSelectedRowKey(null);
    clearMessages();
  }

  function clearMessages() {
    setErrorMessage("");
    setNotice("");
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="Import Preview"
        description="paste rows 저장, validation 실행, rows/errors 조회 흐름을 확인하는 React skeleton 화면입니다."
        extra={<SmartStatusBadge status={currentJobStatus} />}
      />

      <section className="smart-toolbar">
        <Select
          className="smart-control"
          loading={loadingClients}
          placeholder="고객사 선택"
          value={clientId ?? undefined}
          options={clients.map((client) => ({
            value: getClientId(client),
            label: `${client.client_code} · ${client.client_name}`,
          }))}
          onChange={setClientId}
        />
        <Select className="smart-control" value={importType} options={IMPORT_TYPES.map(toSelectOption)} onChange={setImportType} />
        <Select
          className="smart-control"
          value={sourceType}
          options={SOURCE_TYPES.map(toSelectOption)}
          onChange={(value) => {
            setSourceType(value);
            setJob(null);
            setRows([]);
            setErrors([]);
            setValidationSummary(null);
            setConfirmSummary(null);
            setExcelUploadResult(null);
            setSelectedRowKey(null);
            clearMessages();
          }}
        />
      </section>

      <SmartErrorNotice message={errorMessage} />
      {notice ? <Alert type="success" message={notice} showIcon /> : null}
      {currentJobStatus === "HAS_ERRORS" ? <Alert type="warning" message="오류 행이 있어 확정할 수 없습니다." showIcon /> : null}
      {currentJobStatus === "APPLIED" ? <Alert type="info" message="이미 확정된 자료입니다." showIcon /> : null}
      {confirmResult ? (
        <Alert
          type={confirmResult.failed_rows > 0 ? "warning" : "success"}
          message={getConfirmDisplayMessage(confirmResult)}
          description={`반영 ${confirmResult.applied_rows}건 / 건너뜀 ${confirmResult.skipped_rows}건 / 실패 ${confirmResult.failed_rows}건`}
          showIcon
        />
      ) : null}

      {confirmResult ? (
        <Card className="smart-work-panel" title="확정 결과" extra={<SmartStatusBadge status={confirmResult.status} />}>
          <div className="smart-summary-grid">
            <SmartSummaryCard label="총 행 수" value={confirmResult.total_rows} />
            <SmartSummaryCard label="반영 건수" value={confirmResult.applied_rows} />
            <SmartSummaryCard label="건너뜀" value={confirmResult.skipped_rows} />
            <SmartSummaryCard label="실패" value={confirmResult.failed_rows} />
            <SmartSummaryCard label="경고" value={confirmResult.warning_rows} />
            <SmartSummaryCard label="오류" value={confirmResult.invalid_rows} />
          </div>
          <Typography.Text type="secondary">마지막 확정 메시지: {getConfirmDisplayMessage(confirmResult)}</Typography.Text>
        </Card>
      ) : null}

      <Card className="smart-work-panel" title={sourceType === "EXCEL_FILE" ? "엑셀 파일 업로드" : "Paste 입력"}>
        {sourceType === "EXCEL_FILE" ? (
          <Space direction="vertical" className="smart-import-file-area">
            <Typography.Text type="secondary">
              .xlsx 파일만 지원합니다. 첫 번째 시트를 기준으로 미리보기를 생성하고, 첫 번째 행은 헤더로 사용합니다.
            </Typography.Text>
            <Input
              key={fileInputKey}
              type="file"
              accept=".xlsx"
              onChange={(event) => {
                setExcelFile(event.target.files?.[0] || null);
                setExcelUploadResult(null);
                if (job) {
                  setJob(null);
                  setRows([]);
                  setErrors([]);
                  setValidationSummary(null);
                  setConfirmSummary(null);
                }
                clearMessages();
              }}
            />
            <Typography.Text>{excelFile ? excelFile.name : "선택된 파일이 없습니다."}</Typography.Text>
          </Space>
        ) : (
          <Input.TextArea
            value={pasteText}
            rows={7}
            spellCheck={false}
            placeholder={"product_code\tproduct_name\tbarcode\nLOCAL-001\t테스트 상품\t880000000001"}
            onChange={(event) => {
              setPasteText(event.target.value);
              if (job) {
                setJob(null);
                setRows([]);
                setErrors([]);
                setValidationSummary(null);
                setConfirmSummary(null);
              }
            }}
          />
        )}
        <Space className="smart-inline-actions">
          <Button icon={<ReloadOutlined />} onClick={resetInput} disabled={savingRows || validating || confirming}>
            {sourceType === "EXCEL_FILE" ? "파일 선택 초기화" : "붙여넣기 초기화"}
          </Button>
          <Button
            type="primary"
            icon={sourceType === "EXCEL_FILE" ? <UploadOutlined /> : <SaveOutlined />}
            onClick={handleSaveRows}
            loading={savingRows}
            disabled={!canSaveRows || validating || confirming}
          >
            {sourceType === "EXCEL_FILE" ? "업로드/미리보기" : "미리보기/행 저장"}
          </Button>
          <Button icon={<SearchOutlined />} onClick={handleValidate} loading={validating} disabled={!canValidate || savingRows || confirming}>
            검증 실행
          </Button>
          <Button
            icon={<CheckCircleOutlined />}
            onClick={handleConfirmClick}
            loading={confirming}
            disabled={!canConfirm || savingRows || validating}
            title={confirmHelpText}
          >
            확정 반영
          </Button>
          <Typography.Text type={canConfirm ? "success" : "secondary"}>{confirmHelpText}</Typography.Text>
        </Space>
      </Card>

      {sourceType === "EXCEL_FILE" && excelUploadResult ? (
        <Card className="smart-work-panel" title="엑셀 컬럼 인식 결과">
          <Space direction="vertical" size={8}>
            <Typography.Text>
              시트명: {excelUploadResult.worksheet_name || "-"} / 저장 행 수: {excelUploadResult.saved_row_count ?? "-"}
            </Typography.Text>
            <Typography.Text>
              인식된 컬럼: {formatMappedHeaders(excelUploadResult.mapped_headers).join(", ") || "없음"}
            </Typography.Text>
            <Typography.Text>
              미인식 컬럼: {excelUploadResult.unmapped_headers?.length ? excelUploadResult.unmapped_headers.join(", ") : "없음"}
            </Typography.Text>
            <Typography.Text type="secondary">미인식 컬럼은 검증에는 사용하지 않습니다.</Typography.Text>
          </Space>
        </Card>
      ) : null}

      <div className="smart-summary-grid">
        <SmartSummaryCard label="전체 행" value={job?.total_rows ?? rows.length} />
        <SmartSummaryCard label="정상 행" value={validationSummary?.valid_rows ?? job?.valid_rows ?? 0} />
        <SmartSummaryCard label="경고 행" value={validationSummary?.warning_rows ?? warningRows} />
        <SmartSummaryCard label="오류 행" value={validationSummary?.invalid_rows ?? job?.invalid_rows ?? 0} />
        <SmartSummaryCard label="오류 발생 행" value={validationSummary?.error_rows ?? job?.error_rows ?? 0} />
        <SmartSummaryCard label="진행률" value={`${validationSummary?.progress_percent ?? job?.progress_percent ?? 0}%`} />
      </div>

      <Card
        className="smart-work-panel"
        title="Preview Grid"
        extra={
          <Space>
            <Button type={rowFilter === "ALL" ? "primary" : "default"} onClick={() => setRowFilter("ALL")}>
              전체 보기 {rows.length}
            </Button>
            <Button type={rowFilter === "ERROR" ? "primary" : "default"} onClick={() => setRowFilter("ERROR")}>
              오류 행만 보기 {errorRows}
            </Button>
            <Button type={rowFilter === "WARNING" ? "primary" : "default"} onClick={() => setRowFilter("WARNING")}>
              경고 행만 보기 {warningRows}
            </Button>
            <Button onClick={() => setRowFilter("ALL")}>원본 순서 보기</Button>
          </Space>
        }
      >
        <SmartDataGrid<ImportJobRow>
          rowKey={(row) => getRowId(row)}
          columns={columns}
          rows={filteredRows}
          loading={savingRows || validating}
          error={gridErrorMessage || null}
          emptyText="rows 저장 후 원본 순서대로 표시됩니다."
          preserveOriginalOrder
          originalOrderKey="row_no"
          enableOriginalOrderReset
          enableCopy
          selectedRowKeys={selectedRowKey === null ? [] : [selectedRowKey]}
          enableMultiSelect={false}
          onSelectionChange={(keys) => setSelectedRowKey(keys.length ? Number(keys[0]) : null)}
          onRowClick={(row) => setSelectedRowKey(getRowId(row))}
          getRowClassName={(row) => getImportPreviewRowClassName(errors, row)}
        />
      </Card>

      <Card
        className="smart-work-panel"
        title="오류/경고 상세"
        extra={selectedRow ? <Typography.Text type="secondary">선택 row {selectedRow.row_no}</Typography.Text> : null}
      >
        {detailErrors.length === 0 ? (
          <Typography.Text type="secondary">
            {selectedRow ? "선택한 row에 표시할 오류/경고가 없습니다." : "표시할 오류/경고가 없습니다."}
          </Typography.Text>
        ) : (
          <div className="smart-error-list">
            {detailErrors.map((item) => (
              <article className="smart-error-item" key={getErrorId(item)}>
                <Space>
                  <SmartStatusBadge status={item.severity === "ERROR" ? "INVALID" : "WARNING"} />
                  <strong>row {item.row_no}</strong>
                  <Typography.Text copyable>{item.error_code}</Typography.Text>
                </Space>
                <p>{item.error_message}</p>
              </article>
            ))}
          </div>
        )}
      </Card>

      <SmartActionBar>
        <Typography.Text type="secondary">다음 단계 진행은 이번 skeleton 범위에서 비활성입니다.</Typography.Text>
        <Button disabled>다음 단계 진행 준비중</Button>
      </SmartActionBar>
    </SmartPage>
  );
}

const samplePasteText = "product_code\tproduct_name\tbarcode\nLOCAL-001\t테스트 상품\t880000000001";

function parsePasteRows(text: string): ImportPasteRowItem[] {
  const trimmed = text.trim();
  if (!trimmed) {
    return [];
  }
  try {
    const parsed = JSON.parse(trimmed) as unknown;
    if (Array.isArray(parsed)) {
      return parsed.map((item, index) => ({
        row_no: index + 1,
        raw_json: isRecord(item) ? item : { value: item },
        source_row_key: `row-${index + 1}`,
      }));
    }
  } catch {
    // JSON이 아니면 TSV/CSV로 해석한다.
  }

  const lines = trimmed.split(/\r?\n/).filter((line) => line.trim());
  if (lines.length < 2) {
    return [];
  }
  const delimiter = lines[0].includes("\t") ? "\t" : ",";
  const headers = lines[0].split(delimiter).map((header) => header.trim());
  return lines.slice(1).map((line, index) => {
    const values = line.split(delimiter);
    const rawJson = headers.reduce<Record<string, string>>((acc, header, headerIndex) => {
      acc[header] = (values[headerIndex] || "").trim();
      return acc;
    }, {});
    return { row_no: index + 1, raw_json: rawJson, source_row_key: `row-${index + 1}` };
  });
}

function getJobId(job: ImportJob) {
  return Number(job.job_id || job.id);
}

function getRowId(row: ImportJobRow) {
  return Number(row.row_id || row.id || row.row_no);
}

function getErrorId(error: ImportValidationError) {
  return Number(error.error_id || error.id || error.row_no);
}

function getConfirmResultSummary(confirmSummary: ImportConfirmResponse | null, job: ImportJob | null): ImportConfirmResponse | null {
  if (confirmSummary) {
    return confirmSummary;
  }
  if (!job || !["APPLIED", "FAILED"].includes(job.status)) {
    return null;
  }
  const hasSummary =
    typeof job.applied_rows === "number" || typeof job.inserted_rows === "number" || typeof job.skipped_rows === "number" || typeof job.failed_rows === "number";
  if (!hasSummary) {
    return null;
  }
  return {
    job_id: getJobId(job),
    import_type: job.import_type,
    source_type: job.source_type,
    status: job.status,
    total_rows: job.total_rows ?? 0,
    applied_rows: job.applied_rows ?? job.inserted_rows ?? 0,
    skipped_rows: job.skipped_rows ?? 0,
    failed_rows: job.failed_rows ?? 0,
    warning_rows: job.warning_rows ?? 0,
    invalid_rows: job.invalid_rows ?? job.error_rows ?? 0,
    result_code: "",
    message: job.message || "",
  };
}

function getConfirmDisplayMessage(summary: ImportConfirmResponse) {
  if (summary.result_code === "IMPORT_JOB_CONFIRM_PARTIAL_FAILED" || summary.failed_rows > 0) {
    return "일부 row를 반영하지 못했습니다.";
  }
  if (summary.status === "APPLIED") {
    return "상품/바코드 마스터에 반영 완료";
  }
  return summary.message || "확정 결과를 확인했습니다.";
}

function formatMappedHeaders(mappedHeaders?: Record<string, string>) {
  return Object.entries(mappedHeaders || {}).map(([standardField, originalHeader]) => `${originalHeader} → ${standardField}`);
}

function getConfirmHelpText(status: string, rowCount: number, confirming: boolean) {
  if (confirming) {
    return "확정 반영 중입니다.";
  }
  if (status === "VALIDATED" && rowCount > 0) {
    return "검증 완료된 자료를 확정 반영할 수 있습니다.";
  }
  if (status === "HAS_ERRORS") {
    return "오류 행이 있어 확정할 수 없습니다.";
  }
  if (status === "APPLIED") {
    return "이미 확정된 자료입니다.";
  }
  if (status === "FAILED") {
    return "확정 처리 실패 상태입니다. 결과를 확인하세요.";
  }
  if (rowCount === 0) {
    return "저장된 row가 있어야 확정할 수 있습니다.";
  }
  return "검증 완료 후 확정할 수 있습니다.";
}

function jobStatus(job: ImportJob | null) {
  return job?.status || "DRAFT";
}

function getClientId(client?: ClientSummary) {
  return Number(client?.client_id || client?.id || 0);
}

function toSelectOption(value: string) {
  return { value, label: value };
}

function toUserMessage(error: unknown) {
  if (error instanceof ApiClientError) {
    return ERROR_MESSAGES[error.resultCode] || `${error.resultCode}: ${error.message}`;
  }
  return "요청 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}
