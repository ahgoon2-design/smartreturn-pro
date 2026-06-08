import { CheckCircleOutlined, DownloadOutlined, FileExcelOutlined, InboxOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Input, Select, Space, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import {
  autoMapImportJob,
  confirmImportJob,
  createImportJob,
  downloadImportTemplate,
  listImportJobErrors,
  listImportJobRows,
  savePasteRows,
  uploadImportExcelFile,
  validateImportJob,
} from "../../api/importJobs";
import { ApiClientError } from "../../api/client";
import { listClients } from "../../api/master";
import { SmartDataSection } from "../../components/common/SmartDataSection";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartModalShell } from "../../components/common/SmartModalShell";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { ClientSummary } from "../../types/master";
import type {
  ImportConfirmResponse,
  ImportJob,
  ImportJobRow,
  ImportMappingResponse,
  ImportPasteRowItem,
  ImportType,
  ImportValidationError,
  SourceType,
} from "../../types/import";
import { createImportPreviewColumns, filterImportPreviewRows, type ImportPreviewRowFilter } from "./importPreviewGrid";

interface SmartImportLauncherProps {
  importType: ImportType;
  buttonLabel?: string;
  onConfirmed?: () => void | Promise<void>;
}

const SOURCE_OPTIONS: Array<{ value: SourceType; label: string }> = [
  { value: "PASTE", label: "붙여넣기" },
  { value: "EXCEL_FILE", label: "엑셀 업로드" },
];

const sampleProductPasteText =
  "상품코드\t상품명\t옵션명\t대표바코드\t추가바코드\t카톤바코드\t카톤입수\t사용여부\t메모\n" +
  "LOCAL-001\t테스트 상품\t기본\t880000000001\t\t1880000000001\t12\t사용\t";

export function SmartImportLauncher({ importType, buttonLabel = "대량 등록", onConfirmed }: SmartImportLauncherProps) {
  const [open, setOpen] = useState(false);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [clientId, setClientId] = useState<number | null>(null);
  const [sourceType, setSourceType] = useState<SourceType>("PASTE");
  const [pasteText, setPasteText] = useState(sampleProductPasteText);
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [job, setJob] = useState<ImportJob | null>(null);
  const [rows, setRows] = useState<ImportJobRow[]>([]);
  const [errors, setErrors] = useState<ImportValidationError[]>([]);
  const [mapping, setMapping] = useState<ImportMappingResponse | null>(null);
  const [confirmSummary, setConfirmSummary] = useState<ImportConfirmResponse | null>(null);
  const [rowFilter, setRowFilter] = useState<ImportPreviewRowFilter>("ALL");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [fileInputKey, setFileInputKey] = useState(0);

  const parsedRows = useMemo(() => parsePasteRows(pasteText), [pasteText]);
  const columns = useMemo(() => createImportPreviewColumns(errors), [errors]);
  const filteredRows = useMemo(() => filterImportPreviewRows(rows, errors, rowFilter), [errors, rowFilter, rows]);
  const currentJobStatus = job?.status || "DRAFT";
  const errorRows = useMemo(() => new Set(errors.filter((item) => item.severity === "ERROR").map((item) => item.row_id || item.row_no)).size, [errors]);
  const canCreatePreview = Boolean(clientId && !job && (sourceType === "EXCEL_FILE" ? excelFile : parsedRows.length > 0));
  const canValidate = Boolean(job && currentJobStatus === "READY_TO_VALIDATE" && rows.length > 0);
  const canConfirm = Boolean(job && currentJobStatus === "VALIDATED" && rows.length > 0 && errorRows === 0);

  useEffect(() => {
    if (!open) {
      return;
    }
    listClients()
      .then((items) => {
        const activeClients = items.filter((client) => client.active_yn);
        setClients(activeClients);
        setClientId((current) => current || getClientId(activeClients[0]) || null);
      })
      .catch((error) => setErrorMessage(toUserMessage(error)));
  }, [open]);

  function resetState() {
    setSourceType("PASTE");
    setPasteText(sampleProductPasteText);
    setExcelFile(null);
    setJob(null);
    setRows([]);
    setErrors([]);
    setMapping(null);
    setConfirmSummary(null);
    setRowFilter("ALL");
    setNotice("");
    setErrorMessage("");
    setFileInputKey((value) => value + 1);
  }

  async function handleDownloadTemplate() {
    setErrorMessage("");
    try {
      const blob = await downloadImportTemplate(importType);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "product-master-template.csv";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setErrorMessage(toUserMessage(error));
    }
  }

  async function handleCreatePreview() {
    if (!clientId) {
      return;
    }
    setLoading(true);
    setNotice("");
    setErrorMessage("");
    try {
      const createdJob = await createImportJob({
        import_type: importType,
        source_type: sourceType,
        requested_client_id: clientId,
        source_name: sourceType === "EXCEL_FILE" ? excelFile?.name || "product-master-upload" : "product-master-paste",
        file_name: sourceType === "EXCEL_FILE" ? excelFile?.name : undefined,
      });
      const jobId = getJobId(createdJob);
      if (sourceType === "EXCEL_FILE") {
        if (!excelFile) {
          return;
        }
        const upload = await uploadImportExcelFile(jobId, excelFile);
        setJob({ ...createdJob, ...upload, id: createdJob.id, job_id: jobId, status: upload.status });
      } else {
        await savePasteRows(jobId, {
          rows: parsedRows,
          replace_existing: false,
          source_name: "product-master-paste",
        });
        setJob({ ...createdJob, job_id: jobId, status: "READY_TO_VALIDATE", total_rows: parsedRows.length });
      }
      const nextMapping = await autoMapImportJob(jobId);
      setMapping(nextMapping);
      await refreshRowsAndErrors(jobId);
      setNotice("미리보기와 추천 매핑을 생성했습니다. 매핑 결과를 확인한 뒤 검증을 실행하세요.");
    } catch (error) {
      setErrorMessage(toUserMessage(error));
    } finally {
      setLoading(false);
    }
  }

  async function handleValidate() {
    if (!job) {
      return;
    }
    setLoading(true);
    setNotice("");
    setErrorMessage("");
    try {
      const jobId = getJobId(job);
      const summary = await validateImportJob(jobId);
      setJob({ ...job, ...summary, id: job.id, job_id: jobId });
      await refreshRowsAndErrors(jobId);
      setNotice(summary.status === "HAS_ERRORS" ? "검증 결과 오류 행이 있습니다. 확정할 수 없습니다." : "검증이 완료되었습니다.");
    } catch (error) {
      setErrorMessage(toUserMessage(error));
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    if (!job || !canConfirm) {
      return;
    }
    setLoading(true);
    setNotice("");
    setErrorMessage("");
    try {
      const jobId = getJobId(job);
      const summary = await confirmImportJob(jobId);
      setConfirmSummary(summary);
      setJob({ ...job, ...summary, id: job.id, job_id: jobId });
      await refreshRowsAndErrors(jobId);
      await onConfirmed?.();
      setNotice("상품/바코드 마스터에 확정 반영했습니다.");
    } catch (error) {
      setErrorMessage(toUserMessage(error));
    } finally {
      setLoading(false);
    }
  }

  async function refreshRowsAndErrors(jobId: number) {
    const [rowsResult, errorsResult] = await Promise.all([listImportJobRows(jobId), listImportJobErrors(jobId)]);
    setRows([...(rowsResult.items || [])].sort((left, right) => left.row_no - right.row_no));
    setErrors([...(errorsResult.items || [])].sort((left, right) => left.row_no - right.row_no));
  }

  return (
    <>
      <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>
        양식 다운로드
      </Button>
      <Button
        type="primary"
        icon={<InboxOutlined />}
        onClick={() => {
          resetState();
          setOpen(true);
        }}
      >
        {buttonLabel}
      </Button>

      <SmartModalShell
        title="상품/바코드 대량 등록"
        open={open}
        width={1100}
        onCancel={() => setOpen(false)}
        footer={[
          <Button key="close" onClick={() => setOpen(false)}>
            닫기
          </Button>,
          <Button key="preview" icon={<FileExcelOutlined />} loading={loading} disabled={!canCreatePreview} onClick={handleCreatePreview}>
            미리보기 생성
          </Button>,
          <Button key="validate" icon={<SearchOutlined />} loading={loading} disabled={!canValidate} onClick={handleValidate}>
            검증 실행
          </Button>,
          <Button key="confirm" type="primary" icon={<CheckCircleOutlined />} loading={loading} disabled={!canConfirm} onClick={handleConfirm}>
            확정 반영
          </Button>,
        ]}
      >
        <Space direction="vertical" size={12} className="smart-full-width">
          <Alert
            type="info"
            showIcon
            message="자동매핑은 추천입니다"
            description="원본 행 순서를 보존하며, 검증 결과 ERROR가 있으면 확정 반영할 수 없습니다."
          />
          <section className="smart-toolbar" aria-label="상품 import 설정">
            <Select
              className="smart-control"
              placeholder="고객사 선택"
              value={clientId ?? undefined}
              options={clients.map((client) => ({
                value: getClientId(client),
                label: `${client.client_code} · ${client.client_name}`,
              }))}
              onChange={setClientId}
              disabled={Boolean(job)}
            />
            <Select className="smart-control" value={sourceType} options={SOURCE_OPTIONS} onChange={setSourceType} disabled={Boolean(job)} />
            <SmartStatusBadge status={currentJobStatus} />
          </section>

          <SmartErrorNotice message={errorMessage} />
          {notice ? <Alert type={currentJobStatus === "HAS_ERRORS" ? "warning" : "success"} showIcon message={notice} /> : null}
          {confirmSummary ? (
            <Alert
              type={confirmSummary.failed_rows ? "warning" : "success"}
              showIcon
              message={`반영 ${confirmSummary.applied_rows}건 / 건너뜀 ${confirmSummary.skipped_rows}건 / 실패 ${confirmSummary.failed_rows}건`}
            />
          ) : null}

          <SmartDataSection title={sourceType === "EXCEL_FILE" ? "엑셀 업로드" : "붙여넣기 입력"}>
            {sourceType === "EXCEL_FILE" ? (
              <Space direction="vertical" className="smart-full-width">
                <Typography.Text type="secondary">.xlsx 파일을 선택하세요. 첫 번째 행은 헤더로 사용합니다.</Typography.Text>
                <Input
                  key={fileInputKey}
                  type="file"
                  accept=".xlsx"
                  disabled={Boolean(job)}
                  onChange={(event) => setExcelFile(event.target.files?.[0] || null)}
                />
                <Typography.Text>{excelFile ? excelFile.name : "선택된 파일이 없습니다."}</Typography.Text>
              </Space>
            ) : (
              <Input.TextArea
                value={pasteText}
                rows={6}
                disabled={Boolean(job)}
                spellCheck={false}
                onChange={(event) => setPasteText(event.target.value)}
              />
            )}
          </SmartDataSection>

          {mapping ? (
            <SmartDataSection title="매핑 추천 결과">
              <Space direction="vertical" size={6}>
                <Typography.Text>
                  적용 매핑:{" "}
                  {Object.entries(mapping.applied_mapping)
                    .map(([header, field]) => `${header} → ${field}`)
                    .join(", ") || "없음"}
                </Typography.Text>
                <Typography.Text type={mapping.required_missing_fields.length ? "danger" : "secondary"}>
                  필수 필드 미매핑: {mapping.required_missing_fields.join(", ") || "없음"}
                </Typography.Text>
                <Typography.Text type={mapping.ambiguous_headers.length || mapping.unmapped_headers.length ? "warning" : "secondary"}>
                  확인 필요 컬럼: {[...mapping.ambiguous_headers, ...mapping.unmapped_headers].join(", ") || "없음"}
                </Typography.Text>
              </Space>
            </SmartDataSection>
          ) : null}

          <SmartDataSection
            title="미리보기"
            extra={
              <Space>
                <Button type={rowFilter === "ALL" ? "primary" : "default"} onClick={() => setRowFilter("ALL")}>
                  전체
                </Button>
                <Button type={rowFilter === "ERROR" ? "primary" : "default"} onClick={() => setRowFilter("ERROR")}>
                  오류
                </Button>
                <Button type={rowFilter === "WARNING" ? "primary" : "default"} onClick={() => setRowFilter("WARNING")}>
                  경고
                </Button>
              </Space>
            }
          >
            <SmartDataGrid<ImportJobRow>
              rowKey={(row) => getRowId(row)}
              columns={columns}
              rows={filteredRows}
              loading={loading}
              emptyText="미리보기 생성 후 원본 순서대로 표시됩니다."
              preserveOriginalOrder
              originalOrderKey="row_no"
              enableOriginalOrderReset
              enableCopy
              pagination={false}
              maxHeight={320}
            />
          </SmartDataSection>
        </Space>
      </SmartModalShell>
    </>
  );
}

function parsePasteRows(text: string): ImportPasteRowItem[] {
  const trimmed = text.trim();
  if (!trimmed) {
    return [];
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

function getClientId(client?: ClientSummary) {
  return Number(client?.client_id || client?.id || 0);
}

function toUserMessage(error: unknown) {
  if (error instanceof ApiClientError) {
    return error.message || error.resultCode || "Import 처리 중 오류가 발생했습니다.";
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Import 처리 중 오류가 발생했습니다.";
}
