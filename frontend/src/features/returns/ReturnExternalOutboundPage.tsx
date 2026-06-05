import { CheckCircleOutlined, ReloadOutlined, ScanOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Input, Select, Space, Typography, message } from "antd";
import type { InputRef } from "antd";
import type { Key } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { ApiClientError } from "../../api/client";
import { listClients } from "../../api/master";
import {
  confirmReturnExternalOutbound,
  listReturnExternalOutboundCandidates,
} from "../../api/returnIntake";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartSummaryCard } from "../../components/common/SmartSummaryCard";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn } from "../../components/grid/SmartDataGrid.types";
import type { ClientSummary } from "../../types/master";
import type {
  ReturnExternalOutboundCandidate,
  ReturnExternalOutboundConfirmResponse,
} from "../../types/returns";

const OUTBOUND_JUDGEMENT_OPTIONS = [
  { value: "ALL", label: "전체 판정" },
  { value: "REFURB", label: "리퍼" },
  { value: "SAMPLE", label: "샘플" },
  { value: "MANUFACTURER_RETURN", label: "제조사반품" },
];

export function ReturnExternalOutboundPage() {
  const scanInputRef = useRef<InputRef>(null);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | undefined>();
  const [judgementStatus, setJudgementStatus] = useState("ALL");
  const [scanValue, setScanValue] = useState("");
  const [rows, setRows] = useState<ReturnExternalOutboundCandidate[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [scannedRowIds, setScannedRowIds] = useState<number[]>([]);
  const [scannedNumbers, setScannedNumbers] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<{ type: "success" | "warning" | "error" | "info"; message: string } | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [confirmSummary, setConfirmSummary] = useState<ReturnExternalOutboundConfirmResponse | null>(null);

  useEffect(() => {
    void initialize();
    window.setTimeout(() => scanInputRef.current?.focus(), 80);
  }, []);

  const summary = useMemo(
    () => ({
      total: rows.length,
      scanned: scannedRowIds.length,
      selected: selectedRowKeys.length,
      manufacturer: rows.filter((row) => row.judgement_status === "MANUFACTURER_RETURN").length,
    }),
    [rows, scannedRowIds.length, selectedRowKeys.length],
  );

  const columns = useMemo<SmartDataGridColumn<ReturnExternalOutboundCandidate>[]>(
    () => [
      {
        key: "scan_status",
        title: "스캔상태",
        width: 120,
        fixed: "left",
        render: (_value, record) =>
          scannedRowIds.includes(record.row_id) ? (
            <SmartStatusBadge status="VALID" label="스캔 완료" />
          ) : (
            <SmartStatusBadge status="PENDING" label="대기" />
          ),
      },
      {
        key: "client_name",
        title: "고객사",
        dataIndex: "client_name",
        width: 160,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "judgement_status",
        title: "판정",
        dataIndex: "judgement_status",
        width: 130,
        render: (value) => <SmartStatusBadge status={String(value)} label={toJudgementLabel(value)} />,
      },
      {
        key: "return_management_no",
        title: "반품관리번호",
        dataIndex: "return_management_no",
        width: 180,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "return_label_no",
        title: "라벨번호",
        dataIndex: "return_label_no",
        width: 180,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      { key: "return_tracking_no", title: "운송장번호", dataIndex: "return_tracking_no", width: 150, copyable: true },
      { key: "order_no", title: "주문번호", dataIndex: "order_no", width: 150, copyable: true },
      { key: "product_code", title: "상품코드", dataIndex: "product_code", width: 130, copyable: true },
      { key: "barcode", title: "바코드", dataIndex: "barcode", width: 140, copyable: true },
      { key: "product_name", title: "상품명", dataIndex: "product_name", width: 190 },
      { key: "qty", title: "수량", dataIndex: "qty", width: 80, align: "right" },
      {
        key: "external_outbound_status",
        title: "외부반출상태",
        dataIndex: "external_outbound_status",
        width: 140,
        render: (value) => <SmartStatusBadge status={String(value)} label={toOutboundStatusLabel(value)} />,
      },
      { key: "judged_at", title: "판정일시", dataIndex: "judged_at", width: 150, render: (value) => formatDateText(value) },
    ],
    [scannedRowIds],
  );

  async function initialize() {
    setLoading(true);
    setErrorMessage("");
    try {
      const clientItems = await listClients();
      setClients(clientItems);
      await loadCandidates();
    } catch (error) {
      setErrorMessage(toUserMessage(error, "반품 외부반출 정보를 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function loadCandidates() {
    setLoading(true);
    setErrorMessage("");
    try {
      const page = await listReturnExternalOutboundCandidates({
        clientId: selectedClientId,
        judgementStatus: judgementStatus === "ALL" ? undefined : judgementStatus,
        pageSize: 300,
      });
      const items = page.items || [];
      setRows(items);
      setSelectedRowKeys((current) => current.filter((key) => items.some((row) => row.row_id === key)));
      setScannedRowIds((current) => current.filter((rowId) => items.some((row) => row.row_id === rowId)));
      setScannedNumbers((current) =>
        current.filter((number) => items.some((row) => rowMatchesScannedNumber(row, number))),
      );
      if (items.length === 0) {
        setFeedback({ type: "info", message: "외부반출 후보가 없습니다." });
      }
    } catch (error) {
      setErrorMessage(toUserMessage(error, "외부반출 후보를 불러오지 못했습니다."));
    } finally {
      setLoading(false);
      focusScanInput();
    }
  }

  function handleScan() {
    const normalized = normalizeScanNumber(scanValue);
    if (!normalized) {
      setFeedback({ type: "warning", message: "반품관리번호 또는 라벨번호를 스캔하세요." });
      focusScanInput();
      return;
    }
    if (scannedNumbers.includes(normalized)) {
      setFeedback({ type: "warning", message: "이미 스캔한 번호입니다." });
      setScanValue("");
      focusScanInput();
      return;
    }

    const matched = rows.find((row) => rowMatchesScannedNumber(row, normalized));
    if (!matched) {
      setFeedback({ type: "error", message: "외부반출 후보에 없는 번호입니다." });
      setScanValue("");
      focusScanInput();
      return;
    }

    setScannedRowIds((current) => [...current, matched.row_id]);
    setScannedNumbers((current) => [...current, normalized]);
    setSelectedRowKeys((current) => Array.from(new Set([...current, matched.row_id])));
    setFeedback({ type: "success", message: `${toDisplayText(matched.return_management_no || matched.return_label_no)} 스캔 완료` });
    setScanValue("");
    focusScanInput();
  }

  async function handleConfirm() {
    if (scannedRowIds.length === 0) {
      message.warning("반출 확정할 후보를 먼저 스캔하세요.");
      return;
    }
    setConfirming(true);
    setErrorMessage("");
    try {
      const result = await confirmReturnExternalOutbound({
        row_ids: scannedRowIds,
        scanned_numbers: scannedNumbers,
        client_id: selectedClientId,
      });
      setConfirmSummary(result);
      setFeedback({
        type: result.failed_rows > 0 ? "warning" : "success",
        message: result.batch_no
          ? `외부반출 batch ${result.batch_no} 생성 · 확정 ${result.confirmed_rows}건 / 건너뜀 ${result.skipped_rows}건 / 실패 ${result.failed_rows}건`
          : `확정 ${result.confirmed_rows}건 / 건너뜀 ${result.skipped_rows}건 / 실패 ${result.failed_rows}건`,
      });
      setSelectedRowKeys([]);
      setScannedRowIds([]);
      setScannedNumbers([]);
      await loadCandidates();
    } catch (error) {
      setErrorMessage(toUserMessage(error, "반출 확정을 처리하지 못했습니다."));
    } finally {
      setConfirming(false);
      focusScanInput();
    }
  }

  function handleReset() {
    setScanValue("");
    setSelectedRowKeys([]);
    setScannedRowIds([]);
    setScannedNumbers([]);
    setConfirmSummary(null);
    setFeedback({ type: "info", message: "스캔 상태를 초기화했습니다." });
    focusScanInput();
  }

  function focusScanInput() {
    window.setTimeout(() => scanInputRef.current?.focus(), 50);
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="반품 외부반출"
        description="제조사반품, 리퍼, 샘플 대상만 반품관리번호 또는 라벨번호 기준으로 1:1 검수합니다. 현재고는 변경하지 않습니다."
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => void loadCandidates()} loading={loading}>
              새로고침
            </Button>
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => void handleConfirm()}
              loading={confirming}
              disabled={scannedRowIds.length === 0}
            >
              반출 확정
            </Button>
          </Space>
        }
      />

      <Space className="smart-toolbar" wrap>
        <Input
          ref={scanInputRef}
          size="large"
          prefix={<ScanOutlined />}
          placeholder="반품관리번호 또는 라벨번호 스캔"
          value={scanValue}
          onChange={(event) => setScanValue(event.target.value)}
          onPressEnter={handleScan}
          style={{ width: 360 }}
        />
        <Button icon={<ScanOutlined />} onClick={handleScan}>
          스캔 확인
        </Button>
        <Select
          allowClear
          placeholder="고객사 전체"
          style={{ width: 220 }}
          value={selectedClientId}
          onChange={setSelectedClientId}
          options={clients.map((client) => ({
            value: getClientId(client),
            label: client.client_name,
          }))}
        />
        <Select
          style={{ width: 180 }}
          value={judgementStatus}
          onChange={setJudgementStatus}
          options={OUTBOUND_JUDGEMENT_OPTIONS}
        />
        <Button icon={<SearchOutlined />} onClick={() => void loadCandidates()} loading={loading}>
          후보 조회
        </Button>
        <Button onClick={handleReset}>초기화</Button>
      </Space>

      {feedback ? <Alert type={feedback.type} showIcon message={feedback.message} /> : null}
      {errorMessage ? <SmartErrorNotice message={errorMessage} /> : null}

      <div className="smart-summary-grid">
        <SmartSummaryCard label="외부반출 후보" value={`${summary.total}건`} />
        <SmartSummaryCard label="스캔 완료" value={`${summary.scanned}건`} />
        <SmartSummaryCard label="선택" value={`${summary.selected}건`} />
        <SmartSummaryCard label="제조사반품" value={`${summary.manufacturer}건`} />
      </div>

      <Typography.Text type="secondary">
        REFURB/리퍼, SAMPLE/샘플, MANUFACTURER_RETURN/제조사반품만 조회됩니다. GOOD/HOLD/DISPOSAL은 외부반출 대상이 아닙니다.
      </Typography.Text>

      {confirmSummary ? (
        <Alert
          type={confirmSummary.failed_rows > 0 ? "warning" : "success"}
          showIcon
          message="반출 확정 결과"
          description={
            <Space direction="vertical" size={2}>
              <Typography.Text>
                {confirmSummary.batch_no
                  ? `외부반출 batch ${confirmSummary.batch_no}가 생성되었습니다.`
                  : "확정된 신규 row가 없어 외부반출 batch를 생성하지 않았습니다."}
              </Typography.Text>
              <Typography.Text>
                확정 {confirmSummary.confirmed_rows}건 / 건너뜀 {confirmSummary.skipped_rows}건 / 실패{" "}
                {confirmSummary.failed_rows}건. current_inventory는 변경하지 않았습니다.
              </Typography.Text>
            </Space>
          }
        />
      ) : null}

      <SmartDataGrid<ReturnExternalOutboundCandidate>
        rows={rows}
        columns={columns}
        rowKey="row_id"
        loading={loading}
        emptyText="외부반출 후보가 없습니다."
        selectedRowKeys={selectedRowKeys}
        onSelectionChange={(keys) => setSelectedRowKeys(keys)}
        onRowClick={(record) => setSelectedRowKeys((current) => Array.from(new Set([...current, record.row_id])))}
        preserveOriginalOrder
        originalOrderKey="row_no"
        enableOriginalOrderReset
        enableCopy
        maxHeight={430}
        getRowClassName={(record) => (scannedRowIds.includes(record.row_id) ? "smart-grid-row--success" : "")}
      />
    </SmartPage>
  );
}

function rowMatchesScannedNumber(row: ReturnExternalOutboundCandidate, normalized: string) {
  return [row.return_management_no, row.return_label_no]
    .map((value) => normalizeScanNumber(value))
    .filter(Boolean)
    .includes(normalized);
}

function normalizeScanNumber(value: string | null | undefined) {
  const text = String(value || "").trim();
  if (!text) {
    return "";
  }
  return text.replace(/\s+/g, "").toUpperCase();
}

function getClientId(client: ClientSummary) {
  return client.client_id ?? client.id ?? 0;
}

function toJudgementLabel(value: unknown) {
  const map: Record<string, string> = {
    REFURB: "리퍼",
    SAMPLE: "샘플",
    MANUFACTURER_RETURN: "제조사반품",
  };
  return map[String(value)] || toDisplayText(value);
}

function toOutboundStatusLabel(value: unknown) {
  const map: Record<string, string> = {
    NOT_REQUIRED: "미대상",
    READY: "반출 대기",
    SCANNED: "스캔 완료",
    CONFIRMED: "확정 완료",
  };
  return map[String(value)] || toDisplayText(value);
}

function toDisplayText(value: unknown) {
  if (value === undefined || value === null || value === "") {
    return "-";
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
  return date.toLocaleString("ko-KR", {
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function toUserMessage(error: unknown, fallback: string) {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "로그인이 필요합니다.";
    }
    if (error.status === 403) {
      return "반품 외부반출 권한이 없습니다.";
    }
    return error.message || fallback;
  }
  if (error instanceof Error) {
    return error.message || fallback;
  }
  return fallback;
}
