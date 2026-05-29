import { ReloadOutlined, SaveOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Input, Select, Space, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useState } from "react";
import { createImportJob, listImportJobErrors, listImportJobRows, savePasteRows, validateImportJob } from "../../api/importJobs";
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
  ImportValidationError,
  ImportValidationRunResponse,
} from "../../types/import";

const IMPORT_TYPES: ImportType[] = ["PRODUCT_MASTER", "PRODUCT_BARCODE"];
const SOURCE_TYPES: SourceType[] = ["PASTE", "MANUAL"];
type RowFilter = "ALL" | "ERROR" | "WARNING";

const ERROR_MESSAGES: Record<string, string> = {
  NOT_AUTHENTICATED: "로그인이 필요합니다. 기존 인증 화면에서 로그인한 뒤 다시 시도해 주세요.",
  INVALID_TOKEN: "로그인 정보가 만료되었거나 올바르지 않습니다. 다시 로그인해 주세요.",
  IMPORT_JOB_NOT_FOUND: "Import job을 찾을 수 없습니다.",
  IMPORT_JOB_VALIDATE_ALREADY_DONE: "이미 검증이 완료된 자료입니다.",
  IMPORT_JOB_VALIDATE_FORCE_UNSUPPORTED: "강제 재검증은 아직 지원하지 않습니다.",
  IMPORT_JOB_VALIDATE_SOURCE_TYPE_INVALID: "현재 source_type에서는 검증을 실행할 수 없습니다.",
  IMPORT_JOB_VALIDATE_STATUS_INVALID: "현재 상태에서는 검증을 실행할 수 없습니다.",
  IMPORT_JOB_VALIDATE_NO_ROWS: "검증할 row가 없습니다.",
};

export function ImportPreviewPage() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [clientId, setClientId] = useState<number | null>(null);
  const [importType, setImportType] = useState<ImportType>("PRODUCT_MASTER");
  const [sourceType, setSourceType] = useState<SourceType>("PASTE");
  const [pasteText, setPasteText] = useState(samplePasteText);
  const [job, setJob] = useState<ImportJob | null>(null);
  const [rows, setRows] = useState<ImportJobRow[]>([]);
  const [errors, setErrors] = useState<ImportValidationError[]>([]);
  const [validationSummary, setValidationSummary] = useState<ImportValidationRunResponse | null>(null);
  const [rowFilter, setRowFilter] = useState<RowFilter>("ALL");
  const [loadingClients, setLoadingClients] = useState(false);
  const [savingRows, setSavingRows] = useState(false);
  const [validating, setValidating] = useState(false);
  const [notice, setNotice] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const parsedRows = useMemo(() => parsePasteRows(pasteText), [pasteText]);
  const warningRows = useMemo(() => countRowsBySeverity(errors, "WARNING"), [errors]);
  const filteredRows = useMemo(() => {
    const orderedRows = [...rows].sort((left, right) => left.row_no - right.row_no);
    if (rowFilter === "ERROR") {
      return orderedRows.filter((row) => row.validation_status === "INVALID");
    }
    if (rowFilter === "WARNING") {
      return orderedRows.filter((row) => row.validation_status === "WARNING");
    }
    return orderedRows;
  }, [rowFilter, rows]);

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

  const canSaveRows = Boolean(clientId && importType && pasteText.trim() && parsedRows.length > 0 && !job);
  const canValidate = Boolean(jobStatus(job) === "READY_TO_VALIDATE" && rows.length > 0 && !validating);

  const columns: ColumnsType<ImportJobRow> = [
    { title: "행번호", dataIndex: "row_no", width: 72, fixed: "left" },
    {
      title: "상태",
      dataIndex: "validation_status",
      width: 110,
      render: (status: string) => <SmartStatusBadge status={status} />,
    },
    {
      title: "오류/경고",
      width: 92,
      render: (_, row) => getRowErrors(errors, row).length,
    },
    { title: "product_code", render: (_, row) => readRowValue(row, "product_code") },
    { title: "product_name", render: (_, row) => readRowValue(row, "product_name") },
    { title: "barcode", render: (_, row) => readRowValue(row, "barcode") },
    { title: "barcode_type", render: (_, row) => readRowValue(row, "barcode_type") },
    { title: "unit_qty", render: (_, row) => readRowValue(row, "unit_qty") },
    {
      title: "처리 메시지",
      render: (_, row) => row.validation_message || getRowErrors(errors, row).map((item) => item.error_code).join(", "),
    },
  ];

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
        source_name: "frontend-react-preview",
      });
      const nextJobId = getJobId(createdJob);
      await savePasteRows(nextJobId, {
        rows: parsedRows,
        replace_existing: false,
        source_name: "frontend-react-preview",
      });
      setJob({ ...createdJob, status: "READY_TO_VALIDATE", total_rows: parsedRows.length, parsed_rows: parsedRows.length });
      await refreshRowsAndErrors(nextJobId);
      setNotice("rows 저장이 완료되었습니다. 검증을 실행할 수 있습니다.");
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
      setJob({ ...job, ...summary, id: job.id, job_id: jobId });
      await refreshRowsAndErrors(jobId);
      setNotice("검증이 완료되었습니다.");
    } catch (error) {
      setErrorMessage(toUserMessage(error));
    } finally {
      setValidating(false);
    }
  }

  async function refreshRowsAndErrors(jobId: number) {
    const [rowsResult, errorsResult] = await Promise.all([listImportJobRows(jobId), listImportJobErrors(jobId)]);
    setRows((rowsResult.items || []).sort((left, right) => left.row_no - right.row_no));
    setErrors((errorsResult.items || []).sort((left, right) => left.row_no - right.row_no || getErrorId(left) - getErrorId(right)));
  }

  function resetInput() {
    setPasteText("");
    setJob(null);
    setRows([]);
    setErrors([]);
    setValidationSummary(null);
    setRowFilter("ALL");
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
        extra={<SmartStatusBadge status={jobStatus(job)} />}
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
        <Select className="smart-control" value={sourceType} options={SOURCE_TYPES.map(toSelectOption)} onChange={setSourceType} />
      </section>

      <SmartErrorNotice message={errorMessage} />
      {notice ? <Alert type="success" message={notice} showIcon /> : null}

      <Card className="smart-work-panel" title="Paste 입력">
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
            }
          }}
        />
        <Space className="smart-inline-actions">
          <Button icon={<ReloadOutlined />} onClick={resetInput} disabled={savingRows || validating}>
            붙여넣기 초기화
          </Button>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSaveRows} loading={savingRows} disabled={!canSaveRows || validating}>
            미리보기/행 저장
          </Button>
          <Button icon={<SearchOutlined />} onClick={handleValidate} loading={validating} disabled={!canValidate || savingRows}>
            검증 실행
          </Button>
        </Space>
      </Card>

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
              전체 보기
            </Button>
            <Button type={rowFilter === "ERROR" ? "primary" : "default"} onClick={() => setRowFilter("ERROR")}>
              오류 행만 보기
            </Button>
            <Button type={rowFilter === "WARNING" ? "primary" : "default"} onClick={() => setRowFilter("WARNING")}>
              경고 행만 보기
            </Button>
            <Button onClick={() => setRowFilter("ALL")}>원본 순서 보기</Button>
          </Space>
        }
      >
        <SmartDataGrid<ImportJobRow> rowKey={(row) => getRowId(row)} columns={columns} dataSource={filteredRows} loading={savingRows || validating} />
      </Card>

      <Card className="smart-work-panel" title="오류/경고 상세">
        {errors.length === 0 ? (
          <Typography.Text type="secondary">표시할 오류/경고가 없습니다.</Typography.Text>
        ) : (
          <div className="smart-error-list">
            {errors.map((item) => (
              <article className="smart-error-item" key={getErrorId(item)}>
                <Space>
                  <SmartStatusBadge status={item.severity === "ERROR" ? "INVALID" : "WARNING"} />
                  <strong>row {item.row_no}</strong>
                  <span>{item.error_code}</span>
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

function readRowValue(row: ImportJobRow, key: string) {
  const data = row.normalized_json || row.raw_json || {};
  const value = data[key];
  return value === null || value === undefined ? "" : String(value);
}

function getRowErrors(errors: ImportValidationError[], row: ImportJobRow) {
  return errors.filter((item) => item.row_id === row.row_id || item.row_id === row.id || item.row_no === row.row_no);
}

function countRowsBySeverity(errors: ImportValidationError[], severity: string) {
  return new Set(errors.filter((item) => item.severity === severity).map((item) => item.row_id || item.row_no)).size;
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
