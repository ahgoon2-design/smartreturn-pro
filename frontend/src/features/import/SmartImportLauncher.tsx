import { CheckCircleOutlined, DownloadOutlined, FileExcelOutlined, InboxOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Input, Select, Space, Spin, Statistic, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import {
  applyImportJobMapping,
  autoMapImportJob,
  confirmImportJob,
  createImportJob,
  downloadImportTemplate,
  getImportSourceTypeFields,
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
  ImportCanonicalField,
  ImportJob,
  ImportJobRow,
  ImportMappingResponse,
  ImportPasteRowItem,
  ImportType,
  ImportValidationError,
  SourceType,
} from "../../types/import";
import {
  createImportPreviewColumns,
  filterImportPreviewRows,
  type ImportPreviewMessageFormatter,
  type ImportPreviewRowFilter,
} from "./importPreviewGrid";

interface SmartImportLauncherProps {
  importType: ImportType;
  buttonLabel?: string;
  onConfirmed?: () => void | Promise<void>;
  /** 모달 제목. 기본은 상품/바코드 대량 등록. */
  title?: string;
  /** 붙여넣기 초기 샘플. import_type별 헤더 예시를 넘긴다. */
  samplePasteText?: string;
  /** 확정 성공 안내 문구. 기본은 상품/바코드 마스터 기준. */
  confirmSuccessMessage?: string;
  /** 고객 포털처럼 client가 고정된 화면에서 사용. 지정 시 고객사 선택 UI를 숨기고 목록 조회를 하지 않는다. */
  fixedClientId?: number;
  /** 양식 다운로드 버튼 노출 여부. backend가 양식을 제공하지 않는 import_type은 숨긴다. */
  showTemplateDownload?: boolean;
  /** import job source_name에 저장할 식별자 접두어. */
  sourceName?: string;
  /** 오류 문구 변환기. null/undefined를 반환하면 기본 문구를 쓴다. */
  formatErrorMessage?: (error: unknown) => string | null | undefined;
  /** true면 미리보기 데이터 컬럼을 import_type의 canonical 필드 기준으로 만든다. 기본은 기존 상품 컬럼 유지. */
  useCanonicalPreviewColumns?: boolean;
  /** 검증 row 메시지 변환기. 고객 화면에서 내부 필드명/영문 문구를 감출 때 사용한다. */
  formatPreviewMessage?: ImportPreviewMessageFormatter;
}

const SOURCE_OPTIONS: Array<{ value: SourceType; label: string }> = [
  { value: "PASTE", label: "붙여넣기" },
  { value: "EXCEL_FILE", label: "엑셀 업로드" },
];

const sampleProductPasteText =
  "상품코드\t상품명\t옵션명\t대표바코드\t추가바코드\t카톤바코드\t카톤입수\t사용여부\t메모\n" +
  "LOCAL-001\t테스트 상품\t기본\t880000000001\t\t1880000000001\t12\t사용\t";

export function SmartImportLauncher({
  importType,
  buttonLabel = "대량 등록",
  onConfirmed,
  title = "상품/바코드 대량 등록",
  samplePasteText = sampleProductPasteText,
  confirmSuccessMessage = "상품/바코드 마스터에 확정 반영했습니다.",
  fixedClientId,
  showTemplateDownload = true,
  sourceName = "product-master",
  formatErrorMessage,
  useCanonicalPreviewColumns = false,
  formatPreviewMessage,
}: SmartImportLauncherProps) {
  const [open, setOpen] = useState(false);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [clientId, setClientId] = useState<number | null>(fixedClientId ?? null);
  const [sourceType, setSourceType] = useState<SourceType>("PASTE");
  const [pasteText, setPasteText] = useState(samplePasteText);
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [job, setJob] = useState<ImportJob | null>(null);
  const [rows, setRows] = useState<ImportJobRow[]>([]);
  const [errors, setErrors] = useState<ImportValidationError[]>([]);
  const [mapping, setMapping] = useState<ImportMappingResponse | null>(null);
  const [mappingReviewed, setMappingReviewed] = useState(false);
  const [fieldOptions, setFieldOptions] = useState<ImportCanonicalField[]>([]);
  const [confirmSummary, setConfirmSummary] = useState<ImportConfirmResponse | null>(null);
  const [rowFilter, setRowFilter] = useState<ImportPreviewRowFilter>("ALL");
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("");
  const [notice, setNotice] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [fileInputKey, setFileInputKey] = useState(0);

  const parsedRows = useMemo(() => parsePasteRows(pasteText), [pasteText]);
  const columns = useMemo(
    () =>
      createImportPreviewColumns(
        errors,
        useCanonicalPreviewColumns && fieldOptions.length
          ? fieldOptions.map((field) => ({ key: field.field_name, title: field.label || field.field_name }))
          : undefined,
        formatPreviewMessage,
      ),
    [errors, fieldOptions, useCanonicalPreviewColumns, formatPreviewMessage],
  );
  const filteredRows = useMemo(() => filterImportPreviewRows(rows, errors, rowFilter), [errors, rowFilter, rows]);
  const currentJobStatus = job?.status || "DRAFT";
  const skippedImportRows = (job?.skipped_empty_rows || 0) + (job?.skipped_noise_rows || 0);
  const totalReadRows = job?.total_read_rows || job?.total_rows || 0;
  const actualRows = job?.total_rows || rows.length || 0;
  const errorRows = useMemo(() => new Set(errors.filter((item) => item.severity === "ERROR").map((item) => item.row_id || item.row_no)).size, [errors]);
  const canCreatePreview = Boolean(clientId && !job && (sourceType === "EXCEL_FILE" ? excelFile : parsedRows.length > 0));
  const mappingBlocked = Boolean((mapping?.blocked_count || 0) > 0 || (mapping?.required_missing_fields?.length || 0) > 0);
  const mappingReviewRequired = Boolean((mapping?.needs_review_count || 0) > 0 || (mapping?.low_confidence_count || 0) > 0);
  const canReviewMapping = Boolean(job && mapping);
  const canValidate = Boolean(
    job && currentJobStatus === "READY_TO_VALIDATE" && rows.length > 0 && !mappingBlocked && (!mappingReviewRequired || mappingReviewed),
  );
  const canConfirm = Boolean(
    job && currentJobStatus === "VALIDATED" && rows.length > 0 && errorRows === 0 && !mappingBlocked && (!mappingReviewRequired || mappingReviewed),
  );

  const resolveErrorMessage = (error: unknown) => formatErrorMessage?.(error) || toUserMessage(error);

  useEffect(() => {
    if (!open) {
      return;
    }
    if (fixedClientId) {
      // client 고정 화면(고객 포털)은 고객사 목록 권한이 없으므로 목록 조회를 하지 않는다.
      setClientId(fixedClientId);
    } else {
      listClients()
        .then((items) => {
          const activeClients = items.filter((client) => client.active_yn);
          setClients(activeClients);
          setClientId((current) => current || getClientId(activeClients[0]) || null);
        })
        .catch((error) => setErrorMessage(resolveErrorMessage(error)));
    }
    getImportSourceTypeFields(importType)
      .then((response) => setFieldOptions(response.fields || []))
      .catch((error) => setErrorMessage(resolveErrorMessage(error)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [importType, open, fixedClientId]);

  function resetState() {
    setSourceType("PASTE");
    setPasteText(samplePasteText);
    setExcelFile(null);
    setJob(null);
    setRows([]);
    setErrors([]);
    setMapping(null);
    setMappingReviewed(false);
    setFieldOptions([]);
    setConfirmSummary(null);
    setRowFilter("ALL");
    setNotice("");
    setErrorMessage("");
    setLoadingMessage("");
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
      setErrorMessage(resolveErrorMessage(error));
    }
  }

  async function handleCreatePreview() {
    if (!clientId) {
      return;
    }
    setLoading(true);
    setLoadingMessage(sourceType === "EXCEL_FILE" ? "파일을 읽는 중입니다..." : "붙여넣기 자료를 읽는 중입니다...");
    setNotice("");
    setErrorMessage("");
    try {
      const createdJob = await createImportJob({
        import_type: importType,
        source_type: sourceType,
        requested_client_id: clientId,
        source_name: sourceType === "EXCEL_FILE" ? excelFile?.name || `${sourceName}-upload` : `${sourceName}-paste`,
        file_name: sourceType === "EXCEL_FILE" ? excelFile?.name : undefined,
      });
      const jobId = getJobId(createdJob);
      if (sourceType === "EXCEL_FILE") {
        if (!excelFile) {
          return;
        }
        setLoadingMessage("시트 목록을 불러오는 중입니다...");
        const upload = await uploadImportExcelFile(jobId, excelFile);
        setLoadingMessage("헤더를 찾는 중입니다...");
        setJob({ ...createdJob, ...upload, id: createdJob.id, job_id: jobId, status: upload.status });
      } else {
        setLoadingMessage("실제 데이터 행을 판별하는 중입니다...");
        const savedRows = await savePasteRows(jobId, {
          rows: parsedRows,
          replace_existing: false,
          source_name: `${sourceName}-paste`,
        });
        setJob({
          ...createdJob,
          ...savedRows,
          id: createdJob.id,
          job_id: jobId,
          status: savedRows.status,
          total_rows: savedRows.total_rows,
        });
      }
      setLoadingMessage("컬럼을 자동매핑하는 중입니다...");
      const nextMapping = await autoMapImportJob(jobId);
      setMapping(nextMapping);
      setMappingReviewed(
        !((nextMapping.needs_review_count || 0) > 0 || (nextMapping.low_confidence_count || 0) > 0 || (nextMapping.blocked_count || 0) > 0),
      );
      setLoadingMessage("미리보기를 생성하는 중입니다...");
      await refreshRowsAndErrors(jobId);
      setNotice("미리보기와 추천 매핑을 생성했습니다. 매핑 결과를 확인한 뒤 검증을 실행하세요.");
    } catch (error) {
      setErrorMessage(resolveErrorMessage(error));
    } finally {
      setLoading(false);
      setLoadingMessage("");
    }
  }

  async function handleValidate() {
    if (!job) {
      return;
    }
    setLoading(true);
    setLoadingMessage("검증 중입니다...");
    setNotice("");
    setErrorMessage("");
    try {
      const jobId = getJobId(job);
      const summary = await validateImportJob(jobId);
      setJob({ ...job, ...summary, id: job.id, job_id: jobId });
      await refreshRowsAndErrors(jobId);
      setNotice(summary.status === "HAS_ERRORS" ? "검증 결과 오류 행이 있습니다. 확정할 수 없습니다." : "검증이 완료되었습니다.");
    } catch (error) {
      setErrorMessage(resolveErrorMessage(error));
    } finally {
      setLoading(false);
      setLoadingMessage("");
    }
  }

  async function handleReviewMapping() {
    if (!job || !mapping) {
      return;
    }
    setLoading(true);
    setLoadingMessage("매핑 확인 내용을 저장하는 중입니다...");
    setNotice("");
    setErrorMessage("");
    try {
      const jobId = getJobId(job);
      const nextMapping = await applyImportJobMapping(jobId, {
        mappingJson: mapping.applied_mapping,
        saveProfile: true,
        profileName: `${importType} 기본 매핑`,
      });
      setMapping(nextMapping);
      setMappingReviewed(true);
      await refreshRowsAndErrors(jobId);
      setNotice("매핑 확인이 저장되었습니다. 이제 검증을 실행할 수 있습니다.");
    } catch (error) {
      setErrorMessage(resolveErrorMessage(error));
    } finally {
      setLoading(false);
      setLoadingMessage("");
    }
  }

  function handleMappingFieldChange(sourceHeader: string, nextField?: string) {
    if (!mapping || !sourceHeader) {
      return;
    }
    const nextAppliedMapping = { ...mapping.applied_mapping };
    if (nextField) {
      nextAppliedMapping[sourceHeader] = nextField;
    } else {
      delete nextAppliedMapping[sourceHeader];
    }
    setMapping({
      ...mapping,
      applied_mapping: nextAppliedMapping,
      suggestions: mapping.suggestions.map((item) =>
        item.source_header === sourceHeader
          ? {
              ...item,
              target_field: nextField || null,
              canonical_field: nextField || null,
              provider: "MANUAL",
              providers: ["MANUAL"],
              decision_level: nextField ? "NEEDS_REVIEW" : "LOW_CONFIDENCE",
              reason: nextField ? "사용자가 화면에서 수정한 매핑입니다. 매핑 확인 저장이 필요합니다." : "사용자가 매핑에서 제외했습니다.",
              user_action_required: true,
              needs_user_confirmation: true,
              is_auto_applied: false,
            }
          : item,
      ),
    });
    setMappingReviewed(false);
  }

  async function handleConfirm() {
    if (!job || !canConfirm) {
      return;
    }
    setLoading(true);
    setLoadingMessage("저장 중입니다...");
    setNotice("");
    setErrorMessage("");
    try {
      const jobId = getJobId(job);
      const summary = await confirmImportJob(jobId);
      setLoadingMessage("저장 결과를 불러오는 중입니다...");
      setConfirmSummary(summary);
      setJob({ ...job, ...summary, id: job.id, job_id: jobId });
      await refreshRowsAndErrors(jobId);
      await onConfirmed?.();
      setNotice(confirmSuccessMessage);
    } catch (error) {
      setErrorMessage(resolveErrorMessage(error));
    } finally {
      setLoading(false);
      setLoadingMessage("");
    }
  }

  async function refreshRowsAndErrors(jobId: number) {
    const [rowsResult, errorsResult] = await Promise.all([listImportJobRows(jobId), listImportJobErrors(jobId)]);
    setRows([...(rowsResult.items || [])].sort((left, right) => left.row_no - right.row_no));
    setErrors([...(errorsResult.items || [])].sort((left, right) => left.row_no - right.row_no));
  }

  return (
    <>
      {showTemplateDownload ? (
        <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>
          양식 다운로드
        </Button>
      ) : null}
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
        title={title}
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
          <Button key="review-mapping" loading={loading} disabled={!canReviewMapping || mappingReviewed} onClick={handleReviewMapping}>
            매핑 확인
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
          <section className="smart-toolbar" aria-label="import 설정">
            {!fixedClientId ? (
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
            ) : null}
            <Select className="smart-control" value={sourceType} options={SOURCE_OPTIONS} onChange={setSourceType} disabled={Boolean(job)} />
            <SmartStatusBadge status={currentJobStatus} />
          </section>

          <SmartErrorNotice message={errorMessage} />
          {loading && loadingMessage ? (
            <Alert type="info" showIcon message={<Spin size="small" />} description={loadingMessage} />
          ) : null}
          {notice ? <Alert type={currentJobStatus === "HAS_ERRORS" ? "warning" : "success"} showIcon message={notice} /> : null}
          {skippedImportRows ? (
            <Alert
              type="info"
              showIcon
              message={`빈 행 ${job?.skipped_empty_rows || 0}건, 무의미 행 ${job?.skipped_noise_rows || 0}건은 import 대상에서 제외했습니다.`}
              description="제외된 행은 오류가 아니며, 미리보기와 확정 반영 대상에 포함되지 않습니다."
            />
          ) : null}

          {job ? (
            <SmartDataSection title="Import 요약">
              <Space wrap>
                <Statistic title="전체 읽은 행" value={totalReadRows} />
                <Statistic title="실제 자료 행" value={actualRows} />
                <Statistic title="제외 행" value={skippedImportRows} />
                <Statistic title="정상 행" value={job.valid_rows || 0} />
                <Statistic title="경고 행" value={job.warning_rows || 0} />
                <Statistic title="오류 행" value={job.error_rows || 0} />
              </Space>
              {job.header_row_no ? <Typography.Text type="secondary">헤더 행: {job.header_row_no}행</Typography.Text> : null}
            </SmartDataSection>
          ) : null}
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
            <SmartDataSection title="매핑 안전 판정">
              <Space direction="vertical" size={6}>
                <Alert
                  type={mappingBlocked ? "error" : mappingReviewRequired && !mappingReviewed ? "warning" : "success"}
                  showIcon
                  message={`자동적용 ${mapping.auto_apply_count || 0}개 / 확인필요 ${mapping.needs_review_count || 0}개 / 낮은신뢰도 ${
                    mapping.low_confidence_count || 0
                  }개 / 차단 ${mapping.blocked_count || 0}개`}
                  description={
                    mappingReviewed
                      ? "매핑 확인이 저장되었습니다. 저장 전 검증과 확정 단계는 그대로 유지됩니다."
                      : "자동매핑은 추천 결과입니다. 확인필요 또는 낮은신뢰도 필드는 매핑 확인 후 검증할 수 있습니다."
                  }
                />
                {mapping.blocked_reasons?.length ? (
                  <Typography.Text type="danger">차단 사유: {mapping.blocked_reasons.join(", ")}</Typography.Text>
                ) : null}
                <Space direction="vertical" size={6} className="smart-full-width">
                  {mapping.suggestions.slice(0, 12).map((item) => (
                    <Space key={`${item.source_header || item.target_field}-${item.target_field || "none"}`} wrap className="smart-full-width">
                      <SmartStatusBadge status={formatDecisionLevel(item.decision_level)} />
                      <Typography.Text strong>{item.source_header || "(필수필드)"}</Typography.Text>
                      <Select
                        allowClear
                        showSearch
                        size="small"
                        style={{ minWidth: 220 }}
                        placeholder="매핑 선택"
                        value={item.source_header ? mapping.applied_mapping[item.source_header] || undefined : item.target_field || undefined}
                        disabled={!item.source_header}
                        options={fieldOptions.map((field) => ({
                          value: field.field_name,
                          label: `${field.label}${field.required ? " *" : ""} (${field.field_name})`,
                        }))}
                        optionFilterProp="label"
                        onChange={(value) => handleMappingFieldChange(item.source_header, value)}
                      />
                      <Typography.Text type={item.decision_level === "BLOCKED" ? "danger" : "secondary"}>
                        {Math.round((item.confidence || 0) * 100)}% · {item.provider || "RULE"} · {item.reason || item.status}
                      </Typography.Text>
                    </Space>
                  ))}
                </Space>
              </Space>
            </SmartDataSection>
          ) : null}

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
  if (!text.trim()) {
    return [];
  }
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const headerIndex = lines.findIndex((line) => line.trim());
  if (headerIndex < 0 || headerIndex >= lines.length - 1) {
    return [];
  }
  const headerLine = lines[headerIndex];
  const delimiter = headerLine.includes("\t") ? "\t" : ",";
  const headers = headerLine.split(delimiter).map((header) => header.trim());
  return lines.slice(headerIndex + 1).map((line, index) => {
    const values = line.split(delimiter);
    const rawJson = headers.reduce<Record<string, string>>((acc, header, headerIndex) => {
      acc[header] = (values[headerIndex] || "").trim();
      return acc;
    }, {});
    const rowNo = headerIndex + index + 2;
    return { row_no: rowNo, raw_json: rawJson, source_row_key: `row-${rowNo}` };
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

function formatDecisionLevel(level?: string | null) {
  if (level === "AUTO_APPLY") {
    return "자동적용";
  }
  if (level === "NEEDS_REVIEW") {
    return "확인필요";
  }
  if (level === "LOW_CONFIDENCE") {
    return "낮은신뢰도";
  }
  if (level === "BLOCKED") {
    return "차단";
  }
  return level || "미판정";
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
