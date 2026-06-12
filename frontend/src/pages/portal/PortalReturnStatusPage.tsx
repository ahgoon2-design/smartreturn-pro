import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Input, Select, Space, Typography } from "antd";
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
import { useAuth } from "../../context/AuthContext";
import type { ClientSummary } from "../../types/master";
import type { ReturnHistoryItem } from "../../types/returns";

// 고객 포털 노출용 판정 라벨. 내부 enum 원문은 노출하지 않는다.
const JUDGEMENT_LABELS: Record<string, string> = {
  GOOD: "양품",
  REFURB: "리퍼",
  REFURB_A: "리퍼A",
  REFURB_B: "리퍼B",
  REFURB_C: "리퍼C",
  SAMPLE: "샘플",
  MANUFACTURER_RETURN: "제조사반품",
  DEFECTIVE: "불량",
  DISPOSAL: "폐기",
  HOLD: "보류",
};

const JUDGEMENT_OPTIONS = [
  { value: "ALL", label: "전체 판정" },
  { value: "GOOD", label: "양품" },
  { value: "REFURB_A", label: "리퍼A" },
  { value: "REFURB_B", label: "리퍼B" },
  { value: "REFURB_C", label: "리퍼C" },
  { value: "SAMPLE", label: "샘플" },
  { value: "MANUFACTURER_RETURN", label: "제조사반품" },
  { value: "DEFECTIVE", label: "불량" },
  { value: "DISPOSAL", label: "폐기" },
  { value: "HOLD", label: "보류" },
];

const STATUS_OPTIONS = [
  { value: "ALL", label: "전체 처리상태" },
  { value: "RECEIVED", label: "접수" },
  { value: "READY_FOR_PROCESSING", label: "처리대기" },
  { value: "PROCESSING", label: "처리중" },
  { value: "COMPLETED", label: "처리완료" },
];

const WORK_STATUS_LABELS: Record<string, string> = {
  RECEIVED: "접수",
  READY_FOR_PROCESSING: "처리대기",
  PROCESSING: "처리중",
  COMPLETED: "처리완료",
  HOLD: "보류",
};

/**
 * 고객 포털 - 반품 처리현황 (조회 전용).
 * 내부 ReturnHistoryPage와 동일한 /api/returns/history를 재사용하며,
 * 고객 사용자는 서버 scope에 의해 자기 client_id 데이터만 조회된다.
 * 저장/수정/삭제/마감/반출 같은 쓰기 기능은 두지 않는다.
 */
export function PortalReturnStatusPage() {
  const { isClientUser, canSelectClient, authContext, hasPermission } = useAuth();

  // 백엔드가 RETURN_VIEW 권한을 강제한다(프론트는 UX 정리만). 권한이 없으면 요청을 보내지 않고 안내만 한다.
  const canViewReturns = hasPermission("RETURN_VIEW");

  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | undefined>();
  const [keyword, setKeyword] = useState("");
  const [trackingNo, setTrackingNo] = useState("");
  const [returnManagementNo, setReturnManagementNo] = useState("");
  const [judgementStatus, setJudgementStatus] = useState("ALL");
  const [workStatus, setWorkStatus] = useState("ALL");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [rows, setRows] = useState<ReturnHistoryItem[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [optionMessage, setOptionMessage] = useState("");

  useEffect(() => {
    if (!canViewReturns) {
      return;
    }
    void initialize();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const summary = useMemo(
    () => ({
      total: rows.length,
      completed: rows.filter((row) => row.status === "COMPLETED").length,
      processing: rows.filter((row) => row.status === "PROCESSING" || row.status === "READY_FOR_PROCESSING").length,
      hold: rows.filter((row) => row.followup_status === "HOLD_PENDING" || row.followup_status === "READY_TO_REJUDGE")
        .length,
    }),
    [rows],
  );

  const columns = useMemo<SmartDataGridColumn<ReturnHistoryItem>[]>(
    () => [
      ...(canSelectClient
        ? [
            {
              key: "client_name",
              title: "고객사",
              dataIndex: "client_name",
              width: 150,
              copyable: true,
              render: (value: unknown) => toDisplayText(value),
            } as SmartDataGridColumn<ReturnHistoryItem>,
          ]
        : []),
      {
        key: "followup_status",
        title: "후속처리 상태",
        dataIndex: "followup_status",
        width: 150,
        fixed: "left",
        exportValue: (row) => row.followup_status_label || toDisplayText(row.followup_status),
        render: (_value, row) => (
          <SmartStatusBadge status={row.followup_status} label={row.followup_status_label || toDisplayText(row.followup_status)} />
        ),
      },
      {
        key: "status",
        title: "처리상태",
        dataIndex: "status",
        width: 120,
        exportValue: (row) => toWorkStatusLabel(row.status),
        render: (value) => <SmartStatusBadge status={String(value || "")} label={toWorkStatusLabel(value)} />,
      },
      {
        key: "judgement_status",
        title: "판정",
        dataIndex: "judgement_status",
        width: 110,
        exportValue: (row) => toJudgementLabel(row.judgement_status),
        render: (value) => <SmartStatusBadge status={String(value || "")} label={toJudgementLabel(value)} />,
      },
      {
        key: "return_tracking_no",
        title: "운송장번호",
        dataIndex: "return_tracking_no",
        width: 150,
        copyable: true,
        exportAsText: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "return_management_no",
        title: "반품관리번호",
        dataIndex: "return_management_no",
        width: 170,
        copyable: true,
        exportAsText: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "product_code",
        title: "상품코드",
        dataIndex: "product_code",
        width: 140,
        copyable: true,
        exportAsText: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "product_name",
        title: "상품명",
        dataIndex: "product_name",
        width: 210,
        render: (value) => toDisplayText(value),
      },
      {
        key: "barcode",
        title: "바코드",
        dataIndex: "barcode",
        width: 140,
        copyable: true,
        exportAsText: true,
        render: (value) => toDisplayText(value),
      },
      { key: "qty", title: "수량", dataIndex: "qty", width: 70, align: "right" },
      {
        key: "created_at",
        title: "입고/접수일",
        dataIndex: "created_at",
        width: 160,
        exportValue: (row) => formatDateText(row.created_at),
        render: (value) => formatDateText(value),
      },
      {
        key: "judged_at",
        title: "처리(판정)일",
        dataIndex: "judged_at",
        width: 160,
        exportValue: (row) => formatDateText(row.judged_at),
        render: (value) => formatDateText(value),
      },
    ],
    [canSelectClient],
  );

  async function initialize() {
    setLoading(true);
    setErrorMessage("");
    try {
      const tasks: Promise<void>[] = [loadHistory()];
      if (canSelectClient) {
        tasks.push(loadFilterOptions());
      }
      await Promise.all(tasks);
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
    trackingNo?: string;
    returnManagementNo?: string;
    judgementStatus?: string;
    workStatus?: string;
    dateFrom?: string;
    dateTo?: string;
  }) {
    setLoading(true);
    setErrorMessage("");
    const nextClientId = overrides ? overrides.clientId : selectedClientId;
    const nextKeyword = overrides ? overrides.keyword || "" : keyword;
    const nextTrackingNo = overrides ? overrides.trackingNo || "" : trackingNo;
    const nextReturnManagementNo = overrides ? overrides.returnManagementNo || "" : returnManagementNo;
    const nextJudgementStatus = overrides ? overrides.judgementStatus || "ALL" : judgementStatus;
    const nextWorkStatus = overrides ? overrides.workStatus || "ALL" : workStatus;
    const nextDateFrom = overrides ? overrides.dateFrom || "" : dateFrom;
    const nextDateTo = overrides ? overrides.dateTo || "" : dateTo;
    try {
      const page = await listReturnHistory({
        clientId: canSelectClient ? nextClientId : undefined,
        keyword: nextKeyword.trim() || undefined,
        trackingNo: nextTrackingNo.trim() || undefined,
        returnManagementNo: nextReturnManagementNo.trim() || undefined,
        judgementStatus: nextJudgementStatus === "ALL" ? undefined : nextJudgementStatus,
        status: nextWorkStatus === "ALL" ? undefined : nextWorkStatus,
        dateFrom: nextDateFrom || undefined,
        dateTo: nextDateTo || undefined,
        pageSize: 300,
      });
      setRows(page.items || []);
      setSelectedRowKeys([]);
    } catch (error) {
      setRows([]);
      setErrorMessage(toUserMessage(error, "반품 처리현황을 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setSelectedClientId(undefined);
    setKeyword("");
    setTrackingNo("");
    setReturnManagementNo("");
    setJudgementStatus("ALL");
    setWorkStatus("ALL");
    setDateFrom("");
    setDateTo("");
    setSelectedRowKeys([]);
    void loadHistory({
      clientId: undefined,
      keyword: "",
      trackingNo: "",
      returnManagementNo: "",
      judgementStatus: "ALL",
      workStatus: "ALL",
      dateFrom: "",
      dateTo: "",
    });
  }

  const clientLabel = authContext?.client_name || "고객사";

  if (!canViewReturns) {
    return (
      <SmartPage>
        <SmartPageHeader
          title="고객 반품 처리현황"
          description="반품 처리현황을 조회하는 화면입니다."
        />
        <Alert
          type="warning"
          showIcon
          message="반품 조회 권한이 없습니다."
          description="현재 계정에는 반품 처리현황 조회 권한(RETURN_VIEW)이 없습니다. 권한이 필요하면 담당 운영자 또는 고객사 관리자에게 문의하세요."
        />
      </SmartPage>
    );
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="고객 반품 처리현황"
        description="반품 접수부터 판정, 처리완료, 후속처리까지 현재 상태를 조회합니다. 이 화면은 조회 전용입니다."
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => void loadHistory()} loading={loading}>
            새로고침
          </Button>
        }
      />

      <Space className="smart-toolbar" wrap>
        {canSelectClient ? (
          <Select
            allowClear
            placeholder="고객사 전체"
            style={{ width: 200 }}
            value={selectedClientId}
            onChange={setSelectedClientId}
            options={clients.map((client) => ({
              value: getClientId(client),
              label: client.client_name,
            }))}
            disabled={clients.length === 0}
          />
        ) : null}
        <Select style={{ width: 150 }} value={judgementStatus} onChange={setJudgementStatus} options={JUDGEMENT_OPTIONS} />
        <Select style={{ width: 150 }} value={workStatus} onChange={setWorkStatus} options={STATUS_OPTIONS} />
        <Input
          allowClear
          placeholder="운송장번호"
          value={trackingNo}
          onChange={(event) => setTrackingNo(event.target.value)}
          onPressEnter={() => void loadHistory()}
          style={{ width: 170 }}
        />
        <Input
          allowClear
          placeholder="반품관리번호"
          value={returnManagementNo}
          onChange={(event) => setReturnManagementNo(event.target.value)}
          onPressEnter={() => void loadHistory()}
          style={{ width: 180 }}
        />
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="상품코드/바코드/상품명"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          onPressEnter={() => void loadHistory()}
          style={{ width: 240 }}
        />
      </Space>

      <Space className="smart-toolbar" wrap>
        <Typography.Text type="secondary">기간</Typography.Text>
        <Input
          type="date"
          value={dateFrom}
          onChange={(event) => setDateFrom(event.target.value)}
          style={{ width: 170 }}
          aria-label="조회 시작일"
        />
        <Typography.Text type="secondary">~</Typography.Text>
        <Input
          type="date"
          value={dateTo}
          onChange={(event) => setDateTo(event.target.value)}
          style={{ width: 170 }}
          aria-label="조회 종료일"
        />
        <Button type="primary" icon={<SearchOutlined />} onClick={() => void loadHistory()} loading={loading}>
          조회
        </Button>
        <Button onClick={handleReset}>초기화</Button>
      </Space>

      {optionMessage ? <Alert type="info" showIcon message={optionMessage} /> : null}
      {errorMessage ? <SmartErrorNotice message={errorMessage} /> : null}

      <div className="smart-summary-grid">
        <SmartSummaryCard label="조회 건수" value={`${summary.total}건`} />
        <SmartSummaryCard label="처리완료" value={`${summary.completed}건`} />
        <SmartSummaryCard label="처리중/대기" value={`${summary.processing}건`} />
        <SmartSummaryCard label="보류/재판정" value={`${summary.hold}건`} />
      </div>

      <Typography.Text type="secondary">
        {isClientUser ? `${clientLabel} 기준으로 조회됩니다. ` : "내부 관리자 미리보기입니다. "}
        처리, 판정, 마감, 반출은 담당 운영자가 진행하며 이 화면에서는 변경할 수 없습니다.
      </Typography.Text>

      <SmartDataGrid<ReturnHistoryItem>
        rows={rows}
        columns={columns}
        rowKey="row_id"
        loading={loading}
        emptyText="조회된 반품 처리현황이 없습니다."
        selectedRowKeys={selectedRowKeys}
        onSelectionChange={(keys) => setSelectedRowKeys(keys)}
        enableMultiSelect={false}
        enableCopy
        preserveOriginalOrder
        originalOrderKey="row_no"
        exportFileName="고객반품처리현황"
        maxHeight={480}
      />
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
  const code = String(value || "");
  if (!code) {
    return "-";
  }
  return JUDGEMENT_LABELS[code] || code;
}

function toWorkStatusLabel(value: unknown): string {
  const code = String(value || "");
  return WORK_STATUS_LABELS[code] || toDisplayText(value);
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
  // 원시 JSON/stack trace를 노출하지 않고, result_code 기준으로 사유와 다음 행동을 안내한다.
  if (error instanceof ApiClientError) {
    if (error.status === 401 || error.resultCode === "NOT_AUTHENTICATED" || error.resultCode === "INVALID_TOKEN") {
      return "로그인이 필요하거나 인증이 만료되었습니다. 다시 로그인해 주세요.";
    }
    if (error.status === 403) {
      if (error.resultCode === "CLIENT_SCOPE_DENIED" || error.resultCode === "WAREHOUSE_SCOPE_DENIED" || error.resultCode?.includes("SCOPE")) {
        return "허용된 고객사/운영단위 범위 밖의 자료입니다. 고객 포털에서 허용된 메뉴를 이용하거나 담당 관리자에게 문의해 주세요.";
      }
      // PERMISSION_DENIED 및 그 외 403은 권한 부족으로 안내한다.
      return "현재 계정 권한으로 사용할 수 없는 기능입니다. 권한이 필요하면 담당 관리자(고객사 관리자/운영자)에게 요청해 주세요.";
    }
    return error.message || fallback;
  }
  return fallback;
}
