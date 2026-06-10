import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Descriptions, Input, Select, Space, Typography } from "antd";
import type { Key } from "react";
import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "../../api/client";
import { listClients } from "../../api/master";
import { getReturnExternalOutboundBatch, listReturnExternalOutboundBatches } from "../../api/returnIntake";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartSummaryCard } from "../../components/common/SmartSummaryCard";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn } from "../../components/grid/SmartDataGrid.types";
import type { ClientSummary } from "../../types/master";
import type {
  ReturnExternalOutboundBatch,
  ReturnExternalOutboundBatchDetail,
  ReturnExternalOutboundBatchRow,
} from "../../types/returns";

const STATUS_OPTIONS = [
  { value: "ALL", label: "전체 상태" },
  { value: "CONFIRMED", label: "확정 완료" },
  { value: "DRAFT", label: "작성 중" },
];

export function ReturnExternalOutboundBatchesPage() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | undefined>();
  const [status, setStatus] = useState("ALL");
  const [keyword, setKeyword] = useState("");
  const [batches, setBatches] = useState<ReturnExternalOutboundBatch[]>([]);
  const [selectedBatchKey, setSelectedBatchKey] = useState<Key[]>([]);
  const [selectedBatchDetail, setSelectedBatchDetail] = useState<ReturnExternalOutboundBatchDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [detailErrorMessage, setDetailErrorMessage] = useState("");

  useEffect(() => {
    void initialize();
  }, []);

  const summary = useMemo(
    () => ({
      total: batches.length,
      confirmed: batches.filter((batch) => batch.status === "CONFIRMED").length,
      rows: batches.reduce((sum, batch) => sum + (batch.confirmed_rows || 0), 0),
      selectedRows: selectedBatchDetail?.rows.length || 0,
    }),
    [batches, selectedBatchDetail],
  );

  const batchColumns = useMemo<SmartDataGridColumn<ReturnExternalOutboundBatch>[]>(
    () => [
      {
        key: "batch_no",
        title: "반출 묶음번호",
        dataIndex: "batch_no",
        width: 190,
        fixed: "left",
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "client_name",
        title: "고객사",
        dataIndex: "client_name",
        width: 170,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "status",
        title: "상태",
        dataIndex: "status",
        width: 120,
        render: (value) => <SmartStatusBadge status={String(value)} label={toBatchStatusLabel(value)} />,
      },
      { key: "total_rows", title: "총 건수", dataIndex: "total_rows", width: 90, align: "right" },
      { key: "confirmed_rows", title: "확정 건수", dataIndex: "confirmed_rows", width: 100, align: "right" },
      {
        key: "target_type",
        title: "대상",
        dataIndex: "target_type",
        width: 170,
        render: (value) => toTargetTypeLabel(value),
      },
      {
        key: "created_at",
        title: "생성일시",
        dataIndex: "created_at",
        width: 150,
        render: (value) => formatDateText(value),
      },
      {
        key: "confirmed_at",
        title: "확정일시",
        dataIndex: "confirmed_at",
        width: 150,
        render: (value) => formatDateText(value),
      },
      { key: "confirmed_by", title: "작업자", dataIndex: "confirmed_by", width: 90, render: (value) => toDisplayText(value) },
    ],
    [],
  );

  const rowColumns = useMemo<SmartDataGridColumn<ReturnExternalOutboundBatchRow>[]>(
    () => [
      {
        key: "judgement_status",
        title: "판정",
        dataIndex: "judgement_status",
        width: 130,
        fixed: "left",
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
      { key: "product_code", title: "상품코드", dataIndex: "product_code", width: 140, copyable: true },
      { key: "barcode", title: "바코드", dataIndex: "barcode", width: 140, copyable: true },
      { key: "product_name", title: "상품명", dataIndex: "product_name", width: 210, render: (value) => toDisplayText(value) },
      { key: "qty", title: "수량", dataIndex: "qty", width: 80, align: "right" },
      {
        key: "external_outbound_status",
        title: "외부반출상태",
        dataIndex: "external_outbound_status",
        width: 140,
        render: (value) => <SmartStatusBadge status={String(value)} label={toOutboundStatusLabel(value)} />,
      },
    ],
    [],
  );

  async function initialize() {
    setLoading(true);
    setErrorMessage("");
    try {
      const clientItems = await listClients();
      setClients(clientItems);
      await loadBatches();
    } catch (error) {
      setErrorMessage(toUserMessage(error, "외부반출 이력을 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function loadBatches() {
    setLoading(true);
    setErrorMessage("");
    try {
      const page = await listReturnExternalOutboundBatches({
        clientId: selectedClientId,
        status: status === "ALL" ? undefined : status,
        keyword: keyword.trim() || undefined,
        pageSize: 200,
      });
      const items = page.items || [];
      setBatches(items);
      const currentSelected = selectedBatchKey[0];
      if (!items.some((batch) => batch.batch_id === currentSelected)) {
        setSelectedBatchKey([]);
        setSelectedBatchDetail(null);
      }
    } catch (error) {
      setErrorMessage(toUserMessage(error, "외부반출 batch 이력을 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function selectBatch(batch: ReturnExternalOutboundBatch) {
    setSelectedBatchKey([batch.batch_id]);
    setDetailLoading(true);
    setDetailErrorMessage("");
    try {
      const detail = await getReturnExternalOutboundBatch(batch.batch_id);
      setSelectedBatchDetail(detail);
    } catch (error) {
      setSelectedBatchDetail(null);
      setDetailErrorMessage(toUserMessage(error, "외부반출 batch 상세를 불러오지 못했습니다."));
    } finally {
      setDetailLoading(false);
    }
  }

  function handleReset() {
    setSelectedClientId(undefined);
    setStatus("ALL");
    setKeyword("");
    setSelectedBatchKey([]);
    setSelectedBatchDetail(null);
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="반품 외부반출 이력"
        description="외부반출 확정으로 생성된 batch와 포함 row를 조회합니다. 이 화면은 조회 전용이며 current_inventory는 변경하지 않습니다."
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => void loadBatches()} loading={loading}>
              새로고침
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
        <Select style={{ width: 160 }} value={status} onChange={setStatus} options={STATUS_OPTIONS} />
        <Input
          allowClear
          placeholder="batch 번호 또는 고객사 검색"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          onPressEnter={() => void loadBatches()}
          style={{ width: 260 }}
        />
        <Button icon={<SearchOutlined />} type="primary" onClick={() => void loadBatches()} loading={loading}>
          조회
        </Button>
        <Button onClick={handleReset}>초기화</Button>
      </Space>

      {errorMessage ? <SmartErrorNotice message={errorMessage} /> : null}

      <div className="smart-summary-grid">
        <SmartSummaryCard label="외부반출 batch" value={`${summary.total}건`} />
        <SmartSummaryCard label="확정 완료" value={`${summary.confirmed}건`} />
        <SmartSummaryCard label="확정 row" value={`${summary.rows}건`} />
        <SmartSummaryCard label="선택 batch row" value={`${summary.selectedRows}건`} />
      </div>

      <Alert
        type="info"
        showIcon
        message="조회 전용 화면입니다"
        description="외부반출 batch는 REFURB, SAMPLE, MANUFACTURER_RETURN 확정 row를 묶어 추적합니다. 재고는 변경되지 않습니다."
      />

      <SmartDataGrid<ReturnExternalOutboundBatch>
        rows={batches}
        columns={batchColumns}
        rowKey="batch_id"
        loading={loading}
        emptyText="조회된 외부반출 batch가 없습니다."
        selectedRowKeys={selectedBatchKey}
        onSelectionChange={(keys) => {
          const nextKey = keys[0];
          const nextBatch = batches.find((batch) => batch.batch_id === nextKey);
          if (nextBatch) {
            void selectBatch(nextBatch);
          }
        }}
        onRowClick={(record) => void selectBatch(record)}
        enableMultiSelect={false}
        enableCopy
        maxHeight={300}
      />

      {detailErrorMessage ? <SmartErrorNotice message={detailErrorMessage} /> : null}

      <section className="smart-section">
        <Typography.Title level={5}>batch 상세</Typography.Title>
        {selectedBatchDetail ? (
          <Descriptions size="small" column={4} bordered>
            <Descriptions.Item label="반출 묶음번호">{selectedBatchDetail.batch_no}</Descriptions.Item>
            <Descriptions.Item label="상태">{toBatchStatusLabel(selectedBatchDetail.status)}</Descriptions.Item>
            <Descriptions.Item label="확정 건수">{selectedBatchDetail.confirmed_rows}건</Descriptions.Item>
            <Descriptions.Item label="확정일시">{formatDateText(selectedBatchDetail.confirmed_at)}</Descriptions.Item>
            <Descriptions.Item label="고객사">{toDisplayText(selectedBatchDetail.client_name)}</Descriptions.Item>
            <Descriptions.Item label="대상">{toTargetTypeLabel(selectedBatchDetail.target_type)}</Descriptions.Item>
            <Descriptions.Item label="생성일시">{formatDateText(selectedBatchDetail.created_at)}</Descriptions.Item>
            <Descriptions.Item label="메모">{toDisplayText(selectedBatchDetail.memo)}</Descriptions.Item>
          </Descriptions>
        ) : (
          <Typography.Text type="secondary">batch를 선택하면 포함 row를 확인할 수 있습니다.</Typography.Text>
        )}
      </section>

      <SmartDataGrid<ReturnExternalOutboundBatchRow>
        rows={selectedBatchDetail?.rows || []}
        columns={rowColumns}
        rowKey="row_id"
        loading={detailLoading}
        emptyText="선택한 batch에 표시할 row가 없습니다."
        preserveOriginalOrder
        originalOrderKey="row_no"
        enableOriginalOrderReset
        enableCopy
        maxHeight={360}
      />
    </SmartPage>
  );
}

function getClientId(client: ClientSummary) {
  return client.client_id ?? client.id ?? 0;
}

function toDisplayText(value: unknown) {
  if (value === undefined || value === null || value === "") {
    return "-";
  }
  return String(value);
}

function toBatchStatusLabel(value: unknown) {
  const map: Record<string, string> = {
    DRAFT: "작성 중",
    CONFIRMED: "확정 완료",
  };
  return map[String(value)] || toDisplayText(value);
}

function toTargetTypeLabel(value: unknown) {
  const map: Record<string, string> = {
    NON_GOOD_EXTERNAL_OUTBOUND: "GOOD 외 외부반출",
  };
  return map[String(value)] || toDisplayText(value);
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
      return "반품 외부반출 이력 조회 권한이 없습니다.";
    }
    return error.message || fallback;
  }
  if (error instanceof Error) {
    return error.message || fallback;
  }
  return fallback;
}
