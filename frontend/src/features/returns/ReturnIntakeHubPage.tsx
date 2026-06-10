import { CheckCircleOutlined, ReloadOutlined, SaveOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Input, Modal, Select, Space, Typography, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ApiClientError } from "../../api/client";
import { listClients, listClientUnits } from "../../api/master";
import {
  createReturnIntakeBatch,
  listReturnIntakeBatches,
  listReturnProcessingTasks,
  listReturnIntakeRows,
  pasteReturnIntakeRows,
  prepareReturnIntakeBatchForProcessing,
  validateReturnIntakeBatch,
} from "../../api/returnIntake";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartSummaryCard } from "../../components/common/SmartSummaryCard";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn, SmartGridRowAction } from "../../components/grid/SmartDataGrid.types";
import type { ClientSummary, ClientUnit } from "../../types/master";
import type {
  ReturnIntakeBatchSummary,
  ReturnIntakePasteRow,
  ReturnIntakeRow,
  ReturnProcessingTask,
} from "../../types/returns";
import { getSearchNumber, getSearchString, mergeSearchParams } from "../../utils/routeState";

const PASTE_SAMPLE = [
  "order_no\treturn_tracking_no\tproduct_code\tbarcode\tproduct_name\tqty\treturn_reason",
  "ORDER-001\tRTN-001\tP001\t880001\t샘플상품\t1\t단순변심",
].join("\n");

export function ReturnIntakeHubPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | undefined>(() => getSearchNumber(searchParams, "client_id"));
  const [clientUnits, setClientUnits] = useState<ClientUnit[]>([]);
  const [selectedClientUnitId, setSelectedClientUnitId] = useState<number | undefined>(() => getSearchNumber(searchParams, "client_unit_id"));
  const [sourceType, setSourceType] = useState("PASTE");
  const [sourceName, setSourceName] = useState("");
  const [pasteText, setPasteText] = useState(PASTE_SAMPLE);
  const [batches, setBatches] = useState<ReturnIntakeBatchSummary[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<number | undefined>(() => getSearchNumber(searchParams, "batch_id"));
  const [rows, setRows] = useState<ReturnIntakeRow[]>([]);
  const [processingTasks, setProcessingTasks] = useState<ReturnProcessingTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [rowsLoading, setRowsLoading] = useState(false);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [prepareSummary, setPrepareSummary] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [keyword, setKeyword] = useState(() => getSearchString(searchParams, "keyword"));

  useEffect(() => {
    void initialize();
  }, []);

  useEffect(() => {
    setSearchParams(
      mergeSearchParams(searchParams, {
        client_id: selectedClientId,
        client_unit_id: selectedClientUnitId,
        batch_id: selectedBatchId,
        keyword: keyword.trim(),
      }),
      { replace: true },
    );
  }, [selectedClientId, selectedClientUnitId, selectedBatchId, keyword]);

  useEffect(() => {
    if (selectedBatchId) {
      void loadRows(selectedBatchId);
    } else {
      setRows([]);
    }
  }, [selectedBatchId]);

  useEffect(() => {
    void loadClientUnits();
  }, [selectedClientId]);

  useEffect(() => {
    void loadProcessingTasks();
  }, [selectedBatchId, selectedClientId]);

  const selectedBatch = useMemo(
    () => batches.find((batch) => batch.batch_id === selectedBatchId),
    [batches, selectedBatchId],
  );

  const canPrepareProcessing = Boolean(
    selectedBatch &&
      selectedBatch.total_rows > 0 &&
      ["VALIDATED", "HAS_ERRORS", "READY_FOR_PROCESSING"].includes(String(selectedBatch.status)),
  );

  const filteredBatches = useMemo(() => {
    const normalized = keyword.trim().toLowerCase();
    if (!normalized) {
      return batches;
    }
    return batches.filter((batch) =>
      [batch.batch_id, batch.client_name, batch.client_code, batch.source_name, batch.status]
        .filter((value) => value !== undefined && value !== null)
        .some((value) => String(value).toLowerCase().includes(normalized)),
    );
  }, [batches, keyword]);

  const batchColumns = useMemo<SmartDataGridColumn<ReturnIntakeBatchSummary>[]>(
    () => [
      { key: "batch_id", title: "Batch", dataIndex: "batch_id", width: 90, sortable: true, copyable: true },
      { key: "client_name", title: "고객사", dataIndex: "client_name", width: 180, copyable: true },
      { key: "client_unit_name", title: "팀/운영단위", dataIndex: "client_unit_name", width: 150, render: (value) => toDisplayText(value) },
      { key: "source_type", title: "Source", dataIndex: "source_type", width: 110 },
      { key: "source_name", title: "자료명", dataIndex: "source_name", width: 170, render: (value) => toDisplayText(value) },
      {
        key: "status",
        title: "상태",
        dataIndex: "status",
        width: 120,
        render: (value) => <SmartStatusBadge status={String(value)} label={toBatchStatusLabel(value)} />,
      },
      { key: "total_rows", title: "전체", dataIndex: "total_rows", width: 80, align: "right" },
      { key: "warning_rows", title: "경고", dataIndex: "warning_rows", width: 80, align: "right" },
      { key: "error_rows", title: "오류", dataIndex: "error_rows", width: 80, align: "right" },
      { key: "created_at", title: "등록일", dataIndex: "created_at", width: 120, render: (value) => formatDateText(value) },
    ],
    [],
  );

  const batchActions = useMemo<SmartGridRowAction<ReturnIntakeBatchSummary>[]>(
    () => [
      {
        key: "select",
        label: "선택",
        onClick: (record) => setSelectedBatchId(record.batch_id),
      },
    ],
    [],
  );

  const rowColumns = useMemo<SmartDataGridColumn<ReturnIntakeRow>[]>(
    () => [
      { key: "row_no", title: "행", dataIndex: "row_no", width: 80, sortable: true },
      {
        key: "validation_status",
        title: "검증",
        dataIndex: "validation_status",
        width: 120,
        render: (value) => <SmartStatusBadge status={String(value)} label={toValidationLabel(value)} />,
      },
      {
        key: "team_assign_status",
        title: "팀배정",
        dataIndex: "team_assign_status",
        width: 130,
        render: (value) => <SmartStatusBadge status={String(value || "NOT_REQUIRED")} label={toTeamAssignLabel(value)} />,
      },
      { key: "order_no", title: "주문번호", dataIndex: "order_no", width: 150, copyable: true },
      { key: "return_tracking_no", title: "반품 운송장", dataIndex: "return_tracking_no", width: 150, copyable: true },
      { key: "product_code", title: "상품코드", dataIndex: "product_code", width: 130, copyable: true },
      { key: "barcode", title: "바코드", dataIndex: "barcode", width: 140, copyable: true },
      { key: "product_name", title: "상품명", dataIndex: "product_name", width: 180 },
      { key: "qty", title: "수량", dataIndex: "qty", width: 80, align: "right" },
      { key: "return_reason", title: "반품사유", dataIndex: "return_reason", width: 160 },
      { key: "validation_message", title: "메시지", dataIndex: "validation_message", width: 260, render: (value) => toDisplayText(value) },
    ],
    [],
  );

  const processingTaskColumns = useMemo<SmartDataGridColumn<ReturnProcessingTask>[]>(
    () => [
      { key: "batch_id", title: "Batch", dataIndex: "batch_id", width: 90, sortable: true },
      { key: "row_no", title: "행", dataIndex: "row_no", width: 70, sortable: true },
      { key: "client_name", title: "고객사", dataIndex: "client_name", width: 160, copyable: true },
      { key: "client_unit_name", title: "팀/운영단위", dataIndex: "client_unit_name", width: 150, render: (value) => toDisplayText(value) },
      { key: "return_tracking_no", title: "반품 운송장", dataIndex: "return_tracking_no", width: 150, copyable: true },
      { key: "order_no", title: "주문번호", dataIndex: "order_no", width: 150, copyable: true },
      { key: "product_code", title: "상품코드", dataIndex: "product_code", width: 130, copyable: true },
      { key: "barcode", title: "바코드", dataIndex: "barcode", width: 140, copyable: true },
      { key: "product_name", title: "상품명", dataIndex: "product_name", width: 180 },
      { key: "qty", title: "수량", dataIndex: "qty", width: 80, align: "right" },
      {
        key: "validation_status",
        title: "검증",
        dataIndex: "validation_status",
        width: 110,
        render: (value) => <SmartStatusBadge status={String(value)} label={toValidationLabel(value)} />,
      },
      {
        key: "status",
        title: "작업상태",
        dataIndex: "status",
        width: 130,
        render: (value) => <SmartStatusBadge status={String(value)} label={toRowStatusLabel(value)} />,
      },
    ],
    [],
  );

  async function initialize() {
    setLoading(true);
    setErrorMessage("");
    try {
      const [clientItems, batchPage] = await Promise.all([listClients(), listReturnIntakeBatches()]);
      setClients(clientItems);
      setSelectedClientId((current) => current || getClientId(clientItems[0]));
      setBatches(batchPage.items || []);
      setSelectedBatchId((current) =>
        current && batchPage.items?.some((batch) => batch.batch_id === current)
          ? current
          : batchPage.items?.[0]?.batch_id,
      );
    } catch (error) {
      setErrorMessage(toUserMessage(error, "반품 접수 정보를 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function loadBatches() {
    setLoading(true);
    setErrorMessage("");
    try {
      const batchPage = await listReturnIntakeBatches({ clientId: selectedClientId });
      setBatches(batchPage.items || []);
      if (!batchPage.items?.some((batch) => batch.batch_id === selectedBatchId)) {
        setSelectedBatchId(batchPage.items?.[0]?.batch_id);
      }
    } catch (error) {
      setErrorMessage(toUserMessage(error, "반품 접수 batch 목록을 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function loadRows(batchId: number) {
    setRowsLoading(true);
    setErrorMessage("");
    try {
      const page = await listReturnIntakeRows(batchId);
      setRows(page.items || []);
    } catch (error) {
      setErrorMessage(toUserMessage(error, "반품 접수 row를 불러오지 못했습니다."));
    } finally {
      setRowsLoading(false);
    }
  }

  async function loadProcessingTasks() {
    setTasksLoading(true);
    try {
      const page = await listReturnProcessingTasks({
        clientId: selectedClientId,
        batchId: selectedBatchId,
      });
      setProcessingTasks(page.items || []);
    } catch (error) {
      setErrorMessage(toUserMessage(error, "반품처리 대기 대상 목록을 불러오지 못했습니다."));
    } finally {
      setTasksLoading(false);
    }
  }

  async function loadClientUnits() {
    if (!selectedClientId) {
      setClientUnits([]);
      setSelectedClientUnitId(undefined);
      return;
    }
    try {
      const units = await listClientUnits(selectedClientId);
      const activeUnits = units.filter((unit) => unit.active_yn);
      setClientUnits(activeUnits);
      setSelectedClientUnitId((current) =>
        current && activeUnits.some((unit) => unit.unit_id === current) ? current : undefined,
      );
    } catch {
      setClientUnits([]);
      setSelectedClientUnitId(undefined);
    }
  }

  async function handleCreateAndSave() {
    if (!selectedClientId) {
      setErrorMessage("고객사를 선택해 주세요.");
      return;
    }
    const parsedRows = parsePasteRows(pasteText);
    if (parsedRows.length === 0) {
      setErrorMessage("저장할 반품 접수 row가 없습니다.");
      return;
    }
    setSaving(true);
    setErrorMessage("");
    try {
      const batch = await createReturnIntakeBatch({
        client_id: selectedClientId,
        client_unit_id: selectedClientUnitId,
        source_type: sourceType,
        source_name: sourceName || "반품 접수 붙여넣기",
      });
      await pasteReturnIntakeRows(batch.batch_id, { rows: parsedRows, client_unit_id: selectedClientUnitId });
      message.success("반품 접수 row를 저장했습니다.");
      await loadBatches();
      setSelectedBatchId(batch.batch_id);
      await loadRows(batch.batch_id);
    } catch (error) {
      setErrorMessage(toUserMessage(error, "반품 접수 row를 저장하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleValidate() {
    if (!selectedBatchId) {
      setErrorMessage("검증할 batch를 선택해 주세요.");
      return;
    }
    setValidating(true);
    setErrorMessage("");
    try {
      await validateReturnIntakeBatch(selectedBatchId);
      message.success("반품 접수 자료를 검증했습니다.");
      await loadBatches();
      await loadRows(selectedBatchId);
    } catch (error) {
      setErrorMessage(toUserMessage(error, "반품 접수 자료를 검증하지 못했습니다."));
    } finally {
      setValidating(false);
    }
  }

  function handlePrepareProcessing() {
    if (!selectedBatchId) {
      setErrorMessage("처리대상을 생성할 batch를 선택해 주세요.");
      return;
    }
    Modal.confirm({
      title: "처리대상을 생성할까요?",
      content: "정상/경고 row를 반품처리 대기 대상으로 전환합니다. 오류 row는 제외됩니다.",
      okText: "처리대상 생성",
      cancelText: "취소",
      onOk: async () => {
        setPreparing(true);
        setErrorMessage("");
        setPrepareSummary("");
        try {
          const result = await prepareReturnIntakeBatchForProcessing(selectedBatchId);
          const summary = `준비된 행: ${result.prepared_rows}건 / 이미 준비됨: ${result.skipped_rows}건 / 제외된 오류 행: ${result.invalid_rows}건`;
          setPrepareSummary(summary);
          message.success(result.message || "처리대상 생성 완료");
          await loadBatches();
          await loadRows(selectedBatchId);
          await loadProcessingTasks();
        } catch (error) {
          setErrorMessage(toUserMessage(error, "처리대상을 생성하지 못했습니다."));
        } finally {
          setPreparing(false);
        }
      },
    });
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="반품 자료"
        description="업체 반품 세부정보와 CJ 반품 운송장 자료를 저장·검증하고 현장 반품처리 대상을 만듭니다. 업체 세부정보는 참고자료이고, return_tracking_no는 현장 스캔 기준입니다."
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadBatches} loading={loading}>
              새로고침
            </Button>
            <Button icon={<CheckCircleOutlined />} onClick={handleValidate} loading={validating} disabled={!selectedBatchId}>
              검증 실행
            </Button>
            <Button onClick={handlePrepareProcessing} loading={preparing} disabled={!canPrepareProcessing}>
              처리대상 생성
            </Button>
          </Space>
        }
      />

      <section className="smart-toolbar" aria-label="반품 접수 입력">
        <Select
          className="smart-control"
          placeholder="고객사 선택"
          value={selectedClientId}
          options={clients.map((client) => ({ value: getClientId(client), label: `${client.client_name} (${client.client_code})` }))}
          onChange={(value) => {
            setSelectedClientId(value);
            setSelectedClientUnitId(undefined);
          }}
        />
        <Select
          className="smart-control"
          allowClear
          placeholder="운영단위/팀 선택"
          value={selectedClientUnitId}
          options={clientUnits.map((unit) => ({ value: unit.unit_id, label: `${unit.unit_name} (${unit.unit_code})` }))}
          onChange={setSelectedClientUnitId}
        />
        <Select
          className="smart-control"
          value={sourceType}
          options={[
            { value: "PASTE", label: "붙여넣기" },
            { value: "MANUAL", label: "수동 입력" },
          ]}
          onChange={setSourceType}
        />
        <Input className="smart-control" placeholder="자료명" value={sourceName} onChange={(event) => setSourceName(event.target.value)} />
        <Button icon={<SaveOutlined />} type="primary" onClick={handleCreateAndSave} loading={saving}>
          Batch 생성/row 저장
        </Button>
      </section>

      <Input.TextArea
        value={pasteText}
        onChange={(event) => setPasteText(event.target.value)}
        rows={5}
        placeholder="첫 행은 header로 입력합니다. order_no, return_tracking_no, product_code, barcode, product_name, qty, return_reason을 지원합니다."
      />

      <Alert
        type="info"
        showIcon
        message="세부항목 없는 반품 등록"
        description="운송장은 도착했지만 업체 세부 row가 없으면 return_tracking_no, 상품코드/바코드, 수량을 수동 등록한 뒤 검증과 처리대상 생성을 진행하세요. original_tracking_no는 원주문 보조 조회용이며 반품 현장 스캔 기준으로 자동확정하지 않습니다."
      />

      <SmartErrorNotice message={errorMessage} />
      {prepareSummary ? <Alert type="success" showIcon message="처리대상 생성 완료" description={prepareSummary} /> : null}

      <div className="smart-summary-row">
        <SmartSummaryCard label="전체" value={selectedBatch?.total_rows || 0} />
        <SmartSummaryCard label="정상" value={selectedBatch?.valid_rows || 0} />
        <SmartSummaryCard label="경고" value={selectedBatch?.warning_rows || 0} />
        <SmartSummaryCard label="오류" value={selectedBatch?.error_rows || 0} />
      </div>

      <Alert
        type="info"
        showIcon
        message="자료 역할"
        description="업체 반품 세부정보와 CJ 배송상태는 반품처리 참고자료입니다. 실제 상품/수량/판정은 반품 처리 센터에서 확정하고, 재고반영은 반품 일마감 또는 반출/폐기 확정 후 진행합니다."
      />

      <section className="smart-toolbar" aria-label="반품 접수 batch 필터">
        <Input
          className="smart-control"
          allowClear
          prefix={<SearchOutlined />}
          placeholder="Batch, 고객사, 자료명 검색"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
        <Typography.Text type="secondary">현재 {filteredBatches.length}건 표시</Typography.Text>
      </section>

      <SmartDataGrid<ReturnIntakeBatchSummary>
        rowKey="batch_id"
        rows={filteredBatches}
        columns={batchColumns}
        loading={loading}
        error={null}
        emptyText="반품 접수 batch가 없습니다."
        enableCopy
        rowActions={batchActions}
        onRowClick={(record) => setSelectedBatchId(record.batch_id)}
        selectedRowKeys={selectedBatchId ? [selectedBatchId] : []}
        enableMultiSelect={false}
        preserveOriginalOrder
        originalOrderKey="batch_id"
        pagination={false}
        maxHeight={240}
      />

      <Typography.Title level={4}>선택 batch row</Typography.Title>
      <SmartDataGrid<ReturnIntakeRow>
        rowKey="row_id"
        rows={rows}
        columns={rowColumns}
        loading={rowsLoading}
        error={null}
        emptyText={selectedBatchId ? "저장된 반품 접수 row가 없습니다." : "Batch를 선택해 주세요."}
        enableCopy
        preserveOriginalOrder
        originalOrderKey="row_no"
        enableOriginalOrderReset
        pagination={false}
        maxHeight={320}
        getRowClassName={(record) =>
          record.validation_status === "INVALID"
            ? "smart-grid-row-error"
            : record.validation_status === "WARNING"
              ? "smart-grid-row-warning"
              : ""
        }
      />

      <Typography.Title level={4}>반품처리 대기 대상</Typography.Title>
      <SmartDataGrid<ReturnProcessingTask>
        rowKey="task_id"
        rows={processingTasks}
        columns={processingTaskColumns}
        loading={tasksLoading}
        error={null}
        emptyText="반품처리 대기 대상이 없습니다."
        enableCopy
        preserveOriginalOrder
        originalOrderKey="row_no"
        enableOriginalOrderReset
        pagination={false}
        maxHeight={300}
        getRowClassName={(record) => (record.validation_status === "WARNING" ? "smart-grid-row-warning" : "")}
      />
    </SmartPage>
  );
}

function getClientId(client?: ClientSummary) {
  return Number(client?.client_id || client?.id || 0) || undefined;
}

function parsePasteRows(text: string): ReturnIntakePasteRow[] {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length < 2) {
    return [];
  }
  const delimiter = lines[0].includes("\t") ? "\t" : ",";
  const headers = lines[0].split(delimiter).map((header) => header.trim());
  return lines.slice(1).map((line, index) => {
    const values = line.split(delimiter).map((value) => value.trim());
    const row: Record<string, string | number | null> = { row_no: index + 1 };
    headers.forEach((header, headerIndex) => {
      const key = normalizeHeader(header);
      if (!key) {
        return;
      }
      row[key] = values[headerIndex] || null;
    });
    if (row.qty !== null && row.qty !== undefined && row.qty !== "") {
      row.qty = Number(row.qty);
    }
    return row as ReturnIntakePasteRow;
  });
}

function normalizeHeader(header: string) {
  const normalized = header.trim().toLowerCase();
  const map: Record<string, keyof ReturnIntakePasteRow> = {
    row_no: "row_no",
    order_no: "order_no",
    order: "order_no",
    주문번호: "order_no",
    return_tracking_no: "return_tracking_no",
    return_waybill_no: "return_tracking_no",
    반품운송장: "return_tracking_no",
    반품운송장번호: "return_tracking_no",
    product_code: "product_code",
    상품코드: "product_code",
    barcode: "barcode",
    바코드: "barcode",
    product_name: "product_name",
    상품명: "product_name",
    option_name: "option_name",
    옵션명: "option_name",
    qty: "qty",
    수량: "qty",
    return_reason: "return_reason",
    반품사유: "return_reason",
  };
  return map[normalized];
}

function toBatchStatusLabel(value: unknown) {
  const status = String(value || "");
  const labels: Record<string, string> = {
    DRAFT: "작성 중",
    RECEIVED: "접수",
    VALIDATED: "검증 완료",
    HAS_ERRORS: "오류 있음",
    READY_FOR_PROCESSING: "처리 대기",
  };
  return labels[status] || status;
}

function toValidationLabel(value: unknown) {
  const status = String(value || "");
  const labels: Record<string, string> = {
    NOT_VALIDATED: "검증 전",
    VALID: "정상",
    WARNING: "경고",
    INVALID: "오류",
  };
  return labels[status] || status;
}

function toRowStatusLabel(value: unknown) {
  const status = String(value || "");
  const labels: Record<string, string> = {
    RECEIVED: "접수",
    READY_FOR_PROCESSING: "처리 대기",
    PROCESSING: "처리 중",
    COMPLETED: "처리 완료",
    HOLD: "보류",
  };
  return labels[status] || status;
}

function toTeamAssignLabel(value: unknown) {
  const status = String(value || "NOT_REQUIRED");
  const labels: Record<string, string> = {
    NOT_REQUIRED: "불필요",
    TEAM_ASSIGN_PENDING: "팀배정대기",
    ASSIGNED: "배정완료",
  };
  return labels[status] || status;
}

function toDisplayText(value: unknown, fallback = "-") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function formatDateText(value: unknown) {
  if (!value) {
    return "-";
  }
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toISOString().slice(0, 10);
}

function toUserMessage(error: unknown, fallback: string) {
  if (error instanceof ApiClientError) {
    if (error.resultCode === "NOT_AUTHENTICATED" || error.resultCode === "INVALID_TOKEN") {
      return "로그인이 필요하거나 인증이 만료되었습니다. 다시 로그인해 주세요.";
    }
    if (error.status === 403) {
      return "반품 접수 자료에 접근할 권한이 없습니다.";
    }
    return error.message || fallback;
  }
  return fallback;
}
