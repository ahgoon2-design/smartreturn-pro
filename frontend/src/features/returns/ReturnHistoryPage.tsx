import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Descriptions, Input, Select, Space, Typography } from "antd";
import type { Key } from "react";
import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "../../api/client";
import { listClients } from "../../api/master";
import { listReturnHistory } from "../../api/returnIntake";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartSummaryCard } from "../../components/common/SmartSummaryCard";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn } from "../../components/grid/SmartDataGrid.types";
import type { ClientSummary } from "../../types/master";
import type { ReturnHistoryItem } from "../../types/returns";

const JUDGEMENT_OPTIONS = [
  { value: "ALL", label: "전체 판정" },
  { value: "GOOD", label: "양품" },
  { value: "REFURB", label: "리퍼" },
  { value: "SAMPLE", label: "샘플" },
  { value: "MANUFACTURER_RETURN", label: "제조사반품" },
  { value: "DISPOSAL", label: "폐기" },
  { value: "HOLD", label: "보류" },
];

const STATUS_OPTIONS = [
  { value: "ALL", label: "전체 작업상태" },
  { value: "RECEIVED", label: "접수" },
  { value: "READY_FOR_PROCESSING", label: "처리대기" },
  { value: "PROCESSING", label: "처리중" },
  { value: "COMPLETED", label: "처리완료" },
];

const FOLLOWUP_OPTIONS = [
  { value: "ALL", label: "전체 후속상태" },
  { value: "RECEIVED", label: "접수" },
  { value: "PROCESSING_READY", label: "처리대기" },
  { value: "JUDGED", label: "판정완료" },
  { value: "INVENTORY_REFLECTED", label: "정상재고반영" },
  { value: "EXTERNAL_OUTBOUND_TARGET", label: "외부반출대상" },
  { value: "EXTERNAL_OUTBOUND_CONFIRMED", label: "외부반출완료" },
  { value: "HOLD_PENDING", label: "보류중" },
  { value: "READY_TO_REJUDGE", label: "재판정준비" },
  { value: "DISPOSAL_TARGET", label: "폐기대상" },
  { value: "DISPOSAL_CONFIRMED", label: "폐기확정" },
];

export function ReturnHistoryPage() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | undefined>();
  const [keyword, setKeyword] = useState("");
  const [judgementStatus, setJudgementStatus] = useState("ALL");
  const [workStatus, setWorkStatus] = useState("ALL");
  const [followupStatus, setFollowupStatus] = useState("ALL");
  const [rows, setRows] = useState<ReturnHistoryItem[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [selectedRow, setSelectedRow] = useState<ReturnHistoryItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [optionMessage, setOptionMessage] = useState("");

  useEffect(() => {
    void initialize();
  }, []);

  const summary = useMemo(
    () => ({
      total: rows.length,
      reflected: rows.filter((row) => row.inventory_reflected_yn).length,
      outbound: rows.filter((row) => row.external_outbound_status === "CONFIRMED").length,
      hold: rows.filter((row) => row.followup_status === "HOLD_PENDING" || row.followup_status === "READY_TO_REJUDGE")
        .length,
      disposal: rows.filter((row) => row.disposal_status === "DISPOSAL_CONFIRMED").length,
    }),
    [rows],
  );

  const columns = useMemo<SmartDataGridColumn<ReturnHistoryItem>[]>(
    () => [
      {
        key: "client_name",
        title: "고객사",
        dataIndex: "client_name",
        width: 160,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "followup_status",
        title: "후속상태",
        dataIndex: "followup_status",
        width: 150,
        fixed: "left",
        render: (_value, row) => (
          <SmartStatusBadge status={row.followup_status} label={row.followup_status_label || toFollowupStatusLabel(row.followup_status)} />
        ),
      },
      {
        key: "judgement_status",
        title: "판정",
        dataIndex: "judgement_status",
        width: 130,
        render: (value) => <SmartStatusBadge status={String(value || "")} label={toJudgementLabel(value)} />,
      },
      {
        key: "status",
        title: "작업상태",
        dataIndex: "status",
        width: 130,
        render: (value) => <SmartStatusBadge status={String(value || "")} label={toWorkStatusLabel(value)} />,
      },
      { key: "return_tracking_no", title: "운송장번호", dataIndex: "return_tracking_no", width: 150, copyable: true },
      { key: "order_no", title: "주문번호", dataIndex: "order_no", width: 150, copyable: true },
      { key: "product_code", title: "상품코드", dataIndex: "product_code", width: 140, copyable: true },
      { key: "barcode", title: "바코드", dataIndex: "barcode", width: 140, copyable: true },
      { key: "product_name", title: "상품명", dataIndex: "product_name", width: 210, render: (value) => toDisplayText(value) },
      { key: "qty", title: "수량", dataIndex: "qty", width: 80, align: "right" },
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
      {
        key: "label_print_status",
        title: "라벨상태",
        dataIndex: "label_print_status",
        width: 140,
        render: (value, row) =>
          row.label_print_required ? (
            <SmartStatusBadge status={String(value || "")} label={toLabelStatusLabel(value)} />
          ) : (
            "미대상"
          ),
      },
      {
        key: "inventory_reflected_yn",
        title: "재고반영",
        dataIndex: "inventory_reflected_yn",
        width: 120,
        render: (value) => (value ? <SmartStatusBadge status="DONE" label="반영완료" /> : "미반영"),
      },
      {
        key: "external_outbound_status",
        title: "외부반출",
        dataIndex: "external_outbound_status",
        width: 130,
        render: (value) => toOutboundStatusLabel(value),
      },
      { key: "hold_status", title: "보류", dataIndex: "hold_status", width: 130, render: (value) => toHoldStatusLabel(value) },
      {
        key: "disposal_status",
        title: "폐기",
        dataIndex: "disposal_status",
        width: 130,
        render: (value) => toDisposalStatusLabel(value),
      },
      { key: "judged_at", title: "판정일시", dataIndex: "judged_at", width: 160, render: (value) => formatDateText(value) },
    ],
    [],
  );

  async function initialize() {
    setLoading(true);
    setErrorMessage("");
    try {
      await Promise.all([loadFilterOptions(), loadHistory()]);
    } finally {
      setLoading(false);
    }
  }

  async function loadFilterOptions() {
    setOptionMessage("");
    try {
      const clientItems = await listClients();
      setClients(clientItems);
    } catch {
      setClients([]);
      setOptionMessage("고객사 선택 목록은 권한이 있을 때만 표시됩니다.");
    }
  }

  async function loadHistory(overrides?: {
    clientId?: number;
    keyword?: string;
    judgementStatus?: string;
    workStatus?: string;
    followupStatus?: string;
  }) {
    setLoading(true);
    setErrorMessage("");
    const nextClientId = overrides ? overrides.clientId : selectedClientId;
    const nextKeyword = overrides ? overrides.keyword || "" : keyword;
    const nextJudgementStatus = overrides ? overrides.judgementStatus || "ALL" : judgementStatus;
    const nextWorkStatus = overrides ? overrides.workStatus || "ALL" : workStatus;
    const nextFollowupStatus = overrides ? overrides.followupStatus || "ALL" : followupStatus;
    try {
      const page = await listReturnHistory({
        clientId: nextClientId,
        keyword: nextKeyword.trim() || undefined,
        judgementStatus: nextJudgementStatus === "ALL" ? undefined : nextJudgementStatus,
        status: nextWorkStatus === "ALL" ? undefined : nextWorkStatus,
        followupStatus: nextFollowupStatus === "ALL" ? undefined : nextFollowupStatus,
        pageSize: 300,
      });
      const items = page.items || [];
      setRows(items);
      setSelectedRow((current) => {
        if (!current) {
          setSelectedRowKeys([]);
          return null;
        }
        const next = items.find((row) => row.row_id === current.row_id) || null;
        setSelectedRowKeys(next ? [next.row_id] : []);
        return next;
      });
    } catch (error) {
      setErrorMessage(toUserMessage(error, "반품 이력을 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setSelectedClientId(undefined);
    setKeyword("");
    setJudgementStatus("ALL");
    setWorkStatus("ALL");
    setFollowupStatus("ALL");
    setSelectedRow(null);
    setSelectedRowKeys([]);
    void loadHistory({
      clientId: undefined,
      keyword: "",
      judgementStatus: "ALL",
      workStatus: "ALL",
      followupStatus: "ALL",
    });
  }

  function handleSelectRow(row: ReturnHistoryItem) {
    setSelectedRow(row);
    setSelectedRowKeys([row.row_id]);
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="반품 이력조회"
        description="반품 접수부터 판정, 라벨, 일마감, 외부반출, 보류, 폐기까지 row 현재 상태를 조회합니다."
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => void loadHistory()} loading={loading}>
            새로고침
          </Button>
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
          disabled={clients.length === 0}
        />
        <Select style={{ width: 160 }} value={judgementStatus} onChange={setJudgementStatus} options={JUDGEMENT_OPTIONS} />
        <Select style={{ width: 170 }} value={workStatus} onChange={setWorkStatus} options={STATUS_OPTIONS} />
        <Select style={{ width: 190 }} value={followupStatus} onChange={setFollowupStatus} options={FOLLOWUP_OPTIONS} />
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="운송장/주문/상품/바코드/반품관리번호"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          onPressEnter={() => void loadHistory()}
          style={{ width: 320 }}
        />
        <Button type="primary" icon={<SearchOutlined />} onClick={() => void loadHistory()} loading={loading}>
          조회
        </Button>
        <Button onClick={handleReset}>초기화</Button>
      </Space>

      {optionMessage ? <Alert type="info" showIcon message={optionMessage} /> : null}
      {errorMessage ? <SmartErrorNotice message={errorMessage} /> : null}

      <div className="smart-summary-grid">
        <SmartSummaryCard label="조회 이력" value={`${summary.total}건`} />
        <SmartSummaryCard label="재고반영" value={`${summary.reflected}건`} />
        <SmartSummaryCard label="외부반출완료" value={`${summary.outbound}건`} />
        <SmartSummaryCard label="보류/재판정" value={`${summary.hold}건`} />
        <SmartSummaryCard label="폐기확정" value={`${summary.disposal}건`} />
      </div>

      <Typography.Text type="secondary">
        이 화면은 조회 전용입니다. 판정, 일마감, 외부반출, 보류, 폐기 처리는 각 전용 화면에서 진행하세요.
      </Typography.Text>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 380px", gap: 16, alignItems: "start" }}>
        <SmartDataGrid<ReturnHistoryItem>
          rows={rows}
          columns={columns}
          rowKey="row_id"
          loading={loading}
          emptyText="조회된 반품 이력이 없습니다."
          selectedRowKeys={selectedRowKeys}
          onRowClick={handleSelectRow}
          onSelectionChange={(keys, selectedRows) => {
            const row = selectedRows[0];
            if (row) {
              handleSelectRow(row);
            } else {
              setSelectedRow(null);
              setSelectedRowKeys(keys);
            }
          }}
          enableMultiSelect={false}
          enableCopy
          preserveOriginalOrder
          originalOrderKey="row_no"
          maxHeight={470}
          getRowClassName={(row) => (row.row_id === selectedRow?.row_id ? "smart-grid-row-selected" : "")}
        />

        <section className="smart-panel">
          <Typography.Title level={5}>이력 상세</Typography.Title>
          {selectedRow ? (
            <Space direction="vertical" size={12} style={{ width: "100%" }}>
              <Descriptions size="small" column={1} bordered>
                <Descriptions.Item label="후속상태">{selectedRow.followup_status_label}</Descriptions.Item>
                <Descriptions.Item label="접수 정보">
                  {toDisplayText(selectedRow.return_tracking_no)} / {toDisplayText(selectedRow.order_no)}
                </Descriptions.Item>
                <Descriptions.Item label="상품 정보">
                  {toDisplayText(selectedRow.product_code)} / {toDisplayText(selectedRow.barcode)}
                  <br />
                  {toDisplayText(selectedRow.product_name)}
                </Descriptions.Item>
                <Descriptions.Item label="판정 정보">
                  {toJudgementLabel(selectedRow.judgement_status)} / {toDisplayText(selectedRow.judgement_memo)}
                </Descriptions.Item>
                <Descriptions.Item label="라벨 정보">
                  관리번호 {toDisplayText(selectedRow.return_management_no)}
                  <br />
                  라벨번호 {toDisplayText(selectedRow.return_label_no)}
                  <br />
                  상태 {selectedRow.label_print_required ? toLabelStatusLabel(selectedRow.label_print_status) : "라벨 출력 대상 아님"}
                </Descriptions.Item>
                <Descriptions.Item label="재고반영">
                  {selectedRow.inventory_reflected_yn ? "반영완료" : "미반영"}
                  {selectedRow.inventory_reflected_at ? ` / ${formatDateText(selectedRow.inventory_reflected_at)}` : ""}
                </Descriptions.Item>
                <Descriptions.Item label="외부반출">
                  {toOutboundStatusLabel(selectedRow.external_outbound_status)}
                  {selectedRow.external_outbound_at ? ` / ${formatDateText(selectedRow.external_outbound_at)}` : ""}
                </Descriptions.Item>
                <Descriptions.Item label="보류">
                  {toHoldStatusLabel(selectedRow.hold_status)}
                  <br />
                  {toDisplayText(selectedRow.hold_reason || selectedRow.hold_response_memo)}
                </Descriptions.Item>
                <Descriptions.Item label="폐기">
                  {toDisposalStatusLabel(selectedRow.disposal_status)}
                  {selectedRow.disposal_confirmed_at ? ` / ${formatDateText(selectedRow.disposal_confirmed_at)}` : ""}
                </Descriptions.Item>
                <Descriptions.Item label="사진/증빙">
                  {selectedRow.attachment_count > 0 ? `${selectedRow.attachment_count}건 첨부` : "첨부 없음"}
                  <br />
                  사진은 선택사항이며 미첨부를 오류로 보지 않습니다.
                </Descriptions.Item>
              </Descriptions>
              <Alert type="info" showIcon message="이력조회 화면에서는 수정하지 않습니다. 처리는 각 전용 화면에서 진행하세요." />
            </Space>
          ) : (
            <Alert type="info" showIcon message="목록에서 반품 이력을 선택하세요." />
          )}
        </section>
      </div>
    </SmartPage>
  );
}

function getClientId(client: ClientSummary) {
  return client.client_id ?? client.id ?? 0;
}

function toDisplayText(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function toJudgementLabel(value: unknown): string {
  switch (String(value || "")) {
    case "GOOD":
      return "양품";
    case "REFURB":
      return "리퍼";
    case "SAMPLE":
      return "샘플";
    case "MANUFACTURER_RETURN":
      return "제조사반품";
    case "DISPOSAL":
      return "폐기";
    case "HOLD":
      return "보류";
    default:
      return "-";
  }
}

function toWorkStatusLabel(value: unknown): string {
  switch (String(value || "")) {
    case "RECEIVED":
      return "접수";
    case "READY_FOR_PROCESSING":
      return "처리대기";
    case "PROCESSING":
      return "처리중";
    case "COMPLETED":
      return "처리완료";
    case "HOLD":
      return "보류";
    default:
      return toDisplayText(value);
  }
}

function toFollowupStatusLabel(value: unknown): string {
  const match = FOLLOWUP_OPTIONS.find((option) => option.value === value);
  return match && match.value !== "ALL" ? match.label : toDisplayText(value);
}

function toLabelStatusLabel(value: unknown): string {
  switch (String(value || "")) {
    case "NOT_REQUIRED":
      return "미대상";
    case "PRINT_PENDING":
      return "출력 대기";
    case "PRINTED":
      return "출력 완료";
    case "PRINT_FAILED":
      return "출력 실패";
    case "LOCAL_AGENT_NOT_CONNECTED":
      return "Local Agent 미연결";
    default:
      return toDisplayText(value);
  }
}

function toOutboundStatusLabel(value: unknown): string {
  switch (String(value || "")) {
    case "READY":
      return "반출대기";
    case "SCANNED":
      return "스캔완료";
    case "CONFIRMED":
      return "반출완료";
    case "NOT_REQUIRED":
    case "":
      return "-";
    default:
      return toDisplayText(value);
  }
}

function toHoldStatusLabel(value: unknown): string {
  switch (String(value || "")) {
    case "HOLD_PENDING":
      return "보류중";
    case "CUSTOMER_CHECKING":
      return "고객사 확인중";
    case "READY_TO_REJUDGE":
      return "재판정 준비";
    case "RESOLVED":
      return "해결됨";
    case "":
      return "-";
    default:
      return toDisplayText(value);
  }
}

function toDisposalStatusLabel(value: unknown): string {
  switch (String(value || "")) {
    case "DISPOSAL_PENDING":
      return "폐기 대기";
    case "DISPOSAL_CONFIRMED":
      return "폐기 확정";
    case "":
      return "-";
    default:
      return toDisplayText(value);
  }
}

function formatDateText(value: unknown) {
  if (!value) {
    return "-";
  }
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString("ko-KR", { hour12: false });
}

function toUserMessage(error: unknown, fallback: string) {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "로그인이 필요하거나 인증이 만료되었습니다.";
    }
    if (error.status === 403) {
      return "반품 이력을 조회할 권한이 없습니다.";
    }
    return error.message || fallback;
  }
  return fallback;
}
