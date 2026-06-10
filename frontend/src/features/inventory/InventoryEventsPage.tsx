import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Descriptions, Input, Select, Space, Typography } from "antd";
import type { Key } from "react";
import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "../../api/client";
import { listInventoryEvents } from "../../api/inventory";
import { listClients, listWarehouses } from "../../api/master";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartSummaryCard } from "../../components/common/SmartSummaryCard";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn } from "../../components/grid/SmartDataGrid.types";
import type { InventoryEventItem } from "../../types/inventory";
import type { ClientSummary, WarehouseSummary } from "../../types/master";

const EVENT_TYPE_OPTIONS = [
  { value: "ALL", label: "전체 이벤트유형" },
  { value: "RETURN_GOOD_IN", label: "반품양품입고" },
];

const SOURCE_TYPE_OPTIONS = [
  { value: "ALL", label: "전체 source_type" },
  { value: "RETURN_CLOSING", label: "반품일마감" },
];

export function InventoryEventsPage() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [warehouses, setWarehouses] = useState<WarehouseSummary[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | undefined>();
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<number | undefined>();
  const [keyword, setKeyword] = useState("");
  const [eventType, setEventType] = useState("ALL");
  const [sourceType, setSourceType] = useState("ALL");
  const [rows, setRows] = useState<InventoryEventItem[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [selectedRow, setSelectedRow] = useState<InventoryEventItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [optionMessage, setOptionMessage] = useState("");

  useEffect(() => {
    void initialize();
  }, []);

  const summary = useMemo(
    () => ({
      total: rows.length,
      goodIn: rows.filter((row) => row.event_type === "RETURN_GOOD_IN").length,
      qty: rows.reduce((total, row) => total + Number(row.qty || 0), 0),
    }),
    [rows],
  );

  const columns = useMemo<SmartDataGridColumn<InventoryEventItem>[]>(
    () => [
      { key: "created_at", title: "발생일시", dataIndex: "created_at", width: 160, fixed: "left", render: (value) => formatDateText(value) },
      { key: "client_name", title: "고객사", dataIndex: "client_name", width: 160, copyable: true, render: (value) => toDisplayText(value) },
      { key: "warehouse_code", title: "창고코드", dataIndex: "warehouse_code", width: 130, copyable: true, render: (value) => toDisplayText(value) },
      { key: "warehouse_name", title: "창고", dataIndex: "warehouse_name", width: 170, render: (value) => toDisplayText(value) },
      { key: "product_code", title: "상품코드", dataIndex: "product_code", width: 140, copyable: true, render: (value) => toDisplayText(value) },
      { key: "product_name", title: "상품명", dataIndex: "product_name", width: 220, copyable: true, render: (value) => toDisplayText(value) },
      { key: "barcode", title: "바코드", dataIndex: "barcode", width: 150, copyable: true, render: (value) => toDisplayText(value) },
      {
        key: "event_type",
        title: "이벤트유형",
        dataIndex: "event_type",
        width: 150,
        render: (value) => <SmartStatusBadge status={String(value || "")} label={toEventTypeLabel(value)} />,
      },
      { key: "source_type", title: "source_type", dataIndex: "source_type", width: 150, render: (value) => toSourceTypeLabel(value) },
      { key: "source_id", title: "source_id", dataIndex: "source_id", width: 120, copyable: true },
      {
        key: "stock_status",
        title: "재고상태",
        dataIndex: "stock_status",
        width: 120,
        render: (value) => <SmartStatusBadge status={String(value || "")} label={toStockStatusLabel(value)} />,
      },
      {
        key: "qty",
        title: "수량",
        dataIndex: "qty",
        width: 100,
        align: "right",
        sortable: (left, right) => Number(left.qty || 0) - Number(right.qty || 0),
        render: (value) => Number(value || 0).toLocaleString(),
      },
      {
        key: "idempotency_key",
        title: "멱등키",
        dataIndex: "idempotency_key",
        width: 240,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
    ],
    [],
  );

  async function initialize() {
    setLoading(true);
    setErrorMessage("");
    try {
      await Promise.all([loadFilterOptions(), loadEvents()]);
    } finally {
      setLoading(false);
    }
  }

  async function loadFilterOptions() {
    setOptionMessage("");
    try {
      const [clientItems, warehouseItems] = await Promise.all([listClients(), listWarehouses()]);
      setClients(clientItems);
      setWarehouses(warehouseItems);
    } catch {
      setClients([]);
      setWarehouses([]);
      setOptionMessage("고객사/창고 선택 목록은 권한이 있을 때만 표시됩니다.");
    }
  }

  async function loadEvents(overrides?: {
    clientId?: number;
    warehouseId?: number;
    keyword?: string;
    eventType?: string;
    sourceType?: string;
  }) {
    setLoading(true);
    setErrorMessage("");
    const nextClientId = overrides ? overrides.clientId : selectedClientId;
    const nextWarehouseId = overrides ? overrides.warehouseId : selectedWarehouseId;
    const nextKeyword = overrides ? overrides.keyword || "" : keyword;
    const nextEventType = overrides ? overrides.eventType || "ALL" : eventType;
    const nextSourceType = overrides ? overrides.sourceType || "ALL" : sourceType;
    try {
      const page = await listInventoryEvents({
        clientId: nextClientId,
        warehouseId: nextWarehouseId,
        keyword: nextKeyword.trim() || undefined,
        eventType: nextEventType === "ALL" ? undefined : nextEventType,
        sourceType: nextSourceType === "ALL" ? undefined : nextSourceType,
        pageSize: 300,
      });
      const items = page.items || [];
      setRows(items);
      setSelectedRow((current) => {
        if (!current) {
          setSelectedRowKeys([]);
          return null;
        }
        const next = items.find((row) => row.event_id === current.event_id) || null;
        setSelectedRowKeys(next ? [next.event_id] : []);
        return next;
      });
    } catch (error) {
      setErrorMessage(toUserMessage(error, "재고 이벤트를 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setSelectedClientId(undefined);
    setSelectedWarehouseId(undefined);
    setKeyword("");
    setEventType("ALL");
    setSourceType("ALL");
    setSelectedRow(null);
    setSelectedRowKeys([]);
    void loadEvents({ clientId: undefined, warehouseId: undefined, keyword: "", eventType: "ALL", sourceType: "ALL" });
  }

  function handleSelectRow(row: InventoryEventItem) {
    setSelectedRow(row);
    setSelectedRowKeys([row.event_id]);
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="재고 이벤트 이력"
        description="재고가 어떤 이벤트로 움직였는지 고객사, 창고, 상품, source 기준으로 조회합니다."
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => void loadEvents()} loading={loading}>
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
          options={clients.map((client) => ({ value: getClientId(client), label: client.client_name }))}
          disabled={clients.length === 0}
        />
        <Select
          allowClear
          placeholder="창고 전체"
          style={{ width: 240 }}
          value={selectedWarehouseId}
          onChange={setSelectedWarehouseId}
          options={warehouses.map((warehouse) => ({
            value: warehouse.warehouse_id,
            label: `${warehouse.warehouse_code} · ${warehouse.warehouse_name}`,
          }))}
          disabled={warehouses.length === 0}
        />
        <Select style={{ width: 180 }} value={eventType} onChange={setEventType} options={EVENT_TYPE_OPTIONS} />
        <Select style={{ width: 180 }} value={sourceType} onChange={setSourceType} options={SOURCE_TYPE_OPTIONS} />
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="상품/바코드/source/idempotency"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          onPressEnter={() => void loadEvents()}
          style={{ width: 300 }}
        />
        <Button type="primary" icon={<SearchOutlined />} onClick={() => void loadEvents()} loading={loading}>
          조회
        </Button>
        <Button onClick={handleReset}>초기화</Button>
      </Space>

      {optionMessage ? <Alert type="info" showIcon message={optionMessage} /> : null}
      {errorMessage ? <SmartErrorNotice message={errorMessage} /> : null}

      <div className="smart-summary-grid">
        <SmartSummaryCard label="조회 이벤트" value={`${summary.total}건`} />
        <SmartSummaryCard label="반품양품입고" value={`${summary.goodIn}건`} />
        <SmartSummaryCard label="수량 합계" value={`${summary.qty.toLocaleString()}개`} />
        <SmartSummaryCard label="화면 성격" value="조회 전용" />
      </div>

      <Typography.Text type="secondary">
        이 화면은 조회 전용입니다. 재고조정, 수정, 삭제는 제공하지 않습니다.
      </Typography.Text>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 360px", gap: 16, alignItems: "start" }}>
        <SmartDataGrid<InventoryEventItem>
          rows={rows}
          columns={columns}
          rowKey="event_id"
          loading={loading}
          emptyText="조회된 재고 이벤트가 없습니다."
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
          maxHeight={470}
          getRowClassName={(row) => (row.event_id === selectedRow?.event_id ? "smart-grid-row-selected" : "")}
        />

        <section className="smart-panel">
          <Typography.Title level={5}>이벤트 상세</Typography.Title>
          {selectedRow ? (
            <Space direction="vertical" size={12} style={{ width: "100%" }}>
              <Descriptions size="small" column={1} bordered>
                <Descriptions.Item label="이벤트번호">{toDisplayText(selectedRow.event_no)}</Descriptions.Item>
                <Descriptions.Item label="발생일시">{formatDateText(selectedRow.created_at)}</Descriptions.Item>
                <Descriptions.Item label="이벤트유형">{toEventTypeLabel(selectedRow.event_type)}</Descriptions.Item>
                <Descriptions.Item label="source">
                  {toSourceTypeLabel(selectedRow.source_type)} / {selectedRow.source_id}
                </Descriptions.Item>
                <Descriptions.Item label="상품">
                  {toDisplayText(selectedRow.product_code)} / {toDisplayText(selectedRow.barcode)}
                  <br />
                  {toDisplayText(selectedRow.product_name)}
                </Descriptions.Item>
                <Descriptions.Item label="창고">
                  {toDisplayText(selectedRow.warehouse_code)} / {toDisplayText(selectedRow.warehouse_name)}
                </Descriptions.Item>
                <Descriptions.Item label="재고상태">{toStockStatusLabel(selectedRow.stock_status)}</Descriptions.Item>
                <Descriptions.Item label="수량">{Number(selectedRow.qty || 0).toLocaleString()}</Descriptions.Item>
                <Descriptions.Item label="멱등키">{toDisplayText(selectedRow.idempotency_key)}</Descriptions.Item>
                <Descriptions.Item label="사유">{toDisplayText(selectedRow.event_reason)}</Descriptions.Item>
              </Descriptions>
              <Alert type="info" showIcon message="GOOD 반품 일마감 이벤트는 RETURN_GOOD_IN / RETURN_CLOSING으로 기록됩니다." />
            </Space>
          ) : (
            <Alert type="info" showIcon message="목록에서 재고 이벤트를 선택하세요." />
          )}
        </section>
      </div>
    </SmartPage>
  );
}

function getClientId(client: ClientSummary) {
  return client.client_id ?? client.id ?? 0;
}

function toEventTypeLabel(value: unknown) {
  if (value === "RETURN_GOOD_IN") {
    return "반품양품입고";
  }
  return toDisplayText(value);
}

function toSourceTypeLabel(value: unknown) {
  if (value === "RETURN_CLOSING") {
    return "반품일마감";
  }
  return toDisplayText(value);
}

function toStockStatusLabel(value: unknown) {
  if (value === "GOOD") {
    return "정상재고";
  }
  return toDisplayText(value);
}

function toDisplayText(value: unknown) {
  if (value === null || value === undefined || value === "") {
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
  return date.toLocaleString("ko-KR", { hour12: false });
}

function toUserMessage(error: unknown, fallback: string) {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "로그인이 필요하거나 인증이 만료되었습니다.";
    }
    if (error.status === 403) {
      return "재고 이벤트를 조회할 권한이 없습니다.";
    }
    return error.message || fallback;
  }
  return fallback;
}
