import { CheckCircleOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Checkbox, Modal, Select, Space, Typography, message } from "antd";
import type { Key } from "react";
import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "../../api/client";
import { listClients } from "../../api/master";
import { confirmReturnClosing, listReturnClosingCandidates } from "../../api/returnIntake";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartSummaryCard } from "../../components/common/SmartSummaryCard";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn } from "../../components/grid/SmartDataGrid.types";
import type { ClientSummary } from "../../types/master";
import type {
  ReturnClosingCandidate,
  ReturnClosingConfirmResponse,
  ReturnJudgementStatus,
} from "../../types/returns";

const JUDGEMENT_OPTIONS = [
  { value: "ALL", label: "전체 판정" },
  { value: "GOOD", label: "양품" },
  { value: "REFURB", label: "리퍼" },
  { value: "SAMPLE", label: "샘플" },
  { value: "MANUFACTURER_RETURN", label: "제조사반품" },
  { value: "DISPOSAL", label: "폐기" },
  { value: "HOLD", label: "보류" },
];

export function ReturnClosingPage() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | undefined>();
  const [judgementStatus, setJudgementStatus] = useState("ALL");
  const [rows, setRows] = useState<ReturnClosingCandidate[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [confirmSummary, setConfirmSummary] = useState<ReturnClosingConfirmResponse | null>(null);
  const [includeRoutedJudgements, setIncludeRoutedJudgements] = useState(false);

  useEffect(() => {
    void initialize();
  }, []);

  const selectedRows = useMemo(
    () => rows.filter((row) => selectedRowKeys.includes(row.row_id)),
    [rows, selectedRowKeys],
  );

  const summary = useMemo(() => {
    const goodRows = rows.filter((row) => row.judgement_status === "GOOD").length;
    const followupRows = rows.length - goodRows;
    return {
      total: rows.length,
      goodRows,
      followupRows,
      selected: selectedRowKeys.length,
    };
  }, [rows, selectedRowKeys.length]);

  const columns = useMemo<SmartDataGridColumn<ReturnClosingCandidate>[]>(
    () => [
      {
        key: "client_name",
        title: "고객사",
        dataIndex: "client_name",
        width: 170,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "judgement_status",
        title: "판정",
        dataIndex: "judgement_status",
        width: 120,
        render: (value) => <SmartStatusBadge status={String(value)} label={toJudgementLabel(value)} />,
      },
      { key: "return_tracking_no", title: "운송장번호", dataIndex: "return_tracking_no", width: 150, copyable: true },
      { key: "order_no", title: "주문번호", dataIndex: "order_no", width: 150, copyable: true },
      { key: "product_code", title: "상품코드", dataIndex: "product_code", width: 130, copyable: true },
      { key: "barcode", title: "바코드", dataIndex: "barcode", width: 140, copyable: true },
      { key: "product_name", title: "상품명", dataIndex: "product_name", width: 190 },
      { key: "qty", title: "수량", dataIndex: "qty", width: 80, align: "right" },
      {
        key: "return_management_no",
        title: "반품관리번호",
        dataIndex: "return_management_no",
        width: 170,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "inventory_reflected_yn",
        title: "재고반영",
        dataIndex: "inventory_reflected_yn",
        width: 110,
        render: (value) => (
          <SmartStatusBadge status={value ? "DONE" : "PENDING"} label={value ? "반영완료" : "미반영"} />
        ),
      },
      {
        key: "closing_action",
        title: "판단",
        dataIndex: "closing_action",
        width: 140,
        render: (_value, record) =>
          record.judgement_status === "GOOD" ? (
            <SmartStatusBadge status="VALID" label="재고반영 대상" />
          ) : (
            <SmartStatusBadge status="WARNING" label="후속 처리 대상" />
          ),
      },
      { key: "message", title: "메시지", dataIndex: "message", width: 260, render: (value) => toDisplayText(value) },
      { key: "judged_at", title: "판정일시", dataIndex: "judged_at", width: 150, render: (value) => formatDateText(value) },
    ],
    [],
  );

  async function initialize() {
    setLoading(true);
    setErrorMessage("");
    try {
      const clientItems = await listClients();
      setClients(clientItems);
      await loadCandidates();
    } catch (error) {
      setErrorMessage(toUserMessage(error, "반품 일마감 정보를 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function loadCandidates() {
    setLoading(true);
    setErrorMessage("");
    try {
      const page = await listReturnClosingCandidates({
        clientId: selectedClientId,
        judgementStatus: judgementStatus === "ALL" ? undefined : judgementStatus,
        pageSize: 200,
      });
      setRows(page.items || []);
      setSelectedRowKeys((current) => current.filter((key) => page.items?.some((row) => row.row_id === key)));
    } catch (error) {
      setErrorMessage(toUserMessage(error, "재고반영 후보를 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  function handleConfirm() {
    if (selectedRowKeys.length === 0) {
      message.warning("마감 확정할 row를 선택하세요.");
      return;
    }
    Modal.confirm({
      title: "마감 확정",
      content: "선택한 row를 기준으로 GOOD/양품만 정상재고에 반영합니다. 이미 반영된 row는 중복 반영되지 않습니다.",
      okText: "마감 확정",
      cancelText: "취소",
      onOk: () => confirmSelectedRows(),
    });
  }

  async function confirmSelectedRows() {
    setConfirming(true);
    setErrorMessage("");
    try {
      const result = await confirmReturnClosing({
        row_ids: selectedRowKeys.map((key) => Number(key)),
        client_id: selectedClientId,
        confirm_good_only: !includeRoutedJudgements,
      });
      setConfirmSummary(result);
      message.success("반품 일마감을 처리했습니다.");
      setSelectedRowKeys([]);
      await loadCandidates();
    } catch (error) {
      setErrorMessage(toUserMessage(error, "마감 확정을 처리하지 못했습니다."));
    } finally {
      setConfirming(false);
    }
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="반품 일마감"
        description="판정 완료 row 중 미반영 자료를 확인하고, GOOD/양품만 정상재고에 반영합니다."
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => void loadCandidates()} loading={loading}>
              새로고침
            </Button>
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={handleConfirm}
              loading={confirming}
              disabled={selectedRowKeys.length === 0}
            >
              마감 확정
            </Button>
          </Space>
        }
      />

      <Space className="smart-toolbar" wrap>
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
          options={JUDGEMENT_OPTIONS}
        />
        <Checkbox checked={includeRoutedJudgements} onChange={(event) => setIncludeRoutedJudgements(event.target.checked)}>
          라우팅 설정된 GOOD 외 판정도 재고반영
        </Checkbox>
        <Button icon={<SearchOutlined />} onClick={() => void loadCandidates()} loading={loading}>
          후보 조회
        </Button>
        <Typography.Text type="secondary">GOOD/양품만 정상재고에 반영되고, 다른 판정은 후속 처리 대상입니다.</Typography.Text>
      </Space>

      {errorMessage ? <SmartErrorNotice message={errorMessage} /> : null}

      <div className="smart-summary-grid">
        <SmartSummaryCard label="전체 후보" value={`${summary.total}건`} />
        <SmartSummaryCard label="재고반영 대상" value={`${summary.goodRows}건`} />
        <SmartSummaryCard label="후속 처리 대상" value={`${summary.followupRows}건`} />
        <SmartSummaryCard label="선택" value={`${summary.selected}건`} />
      </div>

      {confirmSummary ? (
        <Alert
          type={confirmSummary.failed_rows > 0 ? "warning" : "success"}
          showIcon
          message="마감 처리 결과"
          description={`반영 ${confirmSummary.reflected_rows}건 / 후속 ${confirmSummary.followup_rows}건 / 건너뜀 ${confirmSummary.skipped_rows}건 / 실패 ${confirmSummary.failed_rows}건`}
        />
      ) : null}

      <SmartDataGrid<ReturnClosingCandidate>
        rows={rows}
        columns={columns}
        rowKey="row_id"
        loading={loading}
        emptyText="재고반영 후보가 없습니다."
        selectedRowKeys={selectedRowKeys}
        onSelectionChange={(keys) => setSelectedRowKeys(keys)}
        preserveOriginalOrder
        originalOrderKey="row_no"
        enableOriginalOrderReset
        enableCopy
        maxHeight={440}
        getRowClassName={(record) => (record.judgement_status === "GOOD" ? "smart-grid-row--success" : "")}
      />
    </SmartPage>
  );
}

function getClientId(client: ClientSummary) {
  return client.client_id ?? client.id ?? 0;
}

function toJudgementLabel(value: unknown) {
  const map: Record<string, string> = {
    GOOD: "양품",
    REFURB: "리퍼",
    SAMPLE: "샘플",
    MANUFACTURER_RETURN: "제조사반품",
    DISPOSAL: "폐기",
    HOLD: "보류",
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
      return "반품 일마감 권한이 없습니다.";
    }
    return error.message || fallback;
  }
  if (error instanceof Error) {
    return error.message || fallback;
  }
  return fallback;
}
