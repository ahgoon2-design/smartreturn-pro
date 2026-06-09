import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Input, Select, Space, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ApiClientError } from "../../api/client";
import { listCurrentInventory } from "../../api/inventory";
import { listClients, listWarehouses } from "../../api/master";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartSummaryCard } from "../../components/common/SmartSummaryCard";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn } from "../../components/grid/SmartDataGrid.types";
import type { CurrentInventoryItem } from "../../types/inventory";
import type { ClientSummary, WarehouseSummary } from "../../types/master";
import { getSearchNumber, getSearchString, mergeSearchParams } from "../../utils/routeState";

const STOCK_STATUS_OPTIONS = [
  { value: "ALL", label: "전체 재고상태" },
  { value: "GOOD", label: "정상재고" },
];

export function CurrentInventoryPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [warehouses, setWarehouses] = useState<WarehouseSummary[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | undefined>(() => getSearchNumber(searchParams, "client_id"));
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<number | undefined>(() => getSearchNumber(searchParams, "warehouse_id"));
  const [keyword, setKeyword] = useState(() => getSearchString(searchParams, "keyword"));
  const [stockStatus, setStockStatus] = useState(() => getSearchString(searchParams, "stock_status", "ALL"));
  const [rows, setRows] = useState<CurrentInventoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [optionMessage, setOptionMessage] = useState("");

  useEffect(() => {
    void initialize();
  }, []);

  useEffect(() => {
    setSearchParams(
      mergeSearchParams(searchParams, {
        client_id: selectedClientId,
        warehouse_id: selectedWarehouseId,
        keyword: keyword.trim(),
        stock_status: stockStatus === "ALL" ? undefined : stockStatus,
      }),
      { replace: true },
    );
  }, [selectedClientId, selectedWarehouseId, keyword, stockStatus]);

  const summary = useMemo(
    () => ({
      total: rows.length,
      goodQty: rows
        .filter((row) => row.stock_status === "GOOD")
        .reduce((total, row) => total + Number(row.qty || 0), 0),
    }),
    [rows],
  );

  const columns = useMemo<SmartDataGridColumn<CurrentInventoryItem>[]>(
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
        key: "warehouse_code",
        title: "창고코드",
        dataIndex: "warehouse_code",
        width: 130,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "warehouse_name",
        title: "창고",
        dataIndex: "warehouse_name",
        width: 180,
        render: (value) => toDisplayText(value),
      },
      {
        key: "product_code",
        title: "상품코드",
        dataIndex: "product_code",
        width: 140,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "product_name",
        title: "상품명",
        dataIndex: "product_name",
        width: 220,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "barcode",
        title: "바코드",
        dataIndex: "barcode",
        width: 150,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "stock_status",
        title: "재고상태",
        dataIndex: "stock_status",
        width: 120,
        render: (value) => <SmartStatusBadge status={String(value || "")} label={toStockStatusLabel(value)} />,
      },
      {
        key: "qty",
        title: "현재고 수량",
        dataIndex: "qty",
        width: 120,
        align: "right",
        sortable: (left, right) => Number(left.qty || 0) - Number(right.qty || 0),
        render: (value) => Number(value || 0).toLocaleString(),
      },
      {
        key: "updated_at",
        title: "최종변경일시",
        dataIndex: "updated_at",
        width: 160,
        render: (value) => formatDateText(value),
      },
    ],
    [],
  );

  async function initialize() {
    setLoading(true);
    setErrorMessage("");
    try {
      await Promise.all([loadFilterOptions(), loadInventory()]);
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

  async function loadInventory(overrides?: {
    clientId?: number;
    warehouseId?: number;
    keyword?: string;
    stockStatus?: string;
  }) {
    setLoading(true);
    setErrorMessage("");
    const nextClientId = overrides ? overrides.clientId : selectedClientId;
    const nextWarehouseId = overrides ? overrides.warehouseId : selectedWarehouseId;
    const nextKeyword = overrides ? overrides.keyword || "" : keyword;
    const nextStockStatus = overrides ? overrides.stockStatus || "ALL" : stockStatus;
    try {
      const page = await listCurrentInventory({
        clientId: nextClientId,
        warehouseId: nextWarehouseId,
        keyword: nextKeyword,
        stockStatus: nextStockStatus === "ALL" ? undefined : nextStockStatus,
        pageSize: 300,
      });
      setRows(page.items || []);
    } catch (error) {
      setErrorMessage(toUserMessage(error, "재고현황을 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setSelectedClientId(undefined);
    setSelectedWarehouseId(undefined);
    setKeyword("");
    setStockStatus("ALL");
    void loadInventory({ clientId: undefined, warehouseId: undefined, keyword: "", stockStatus: "ALL" });
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="재고현황"
        description="GOOD 반품 일마감으로 반영된 현재고를 고객사, 창고, 상품 기준으로 조회합니다."
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => void loadInventory()} loading={loading}>
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
        <Select
          style={{ width: 160 }}
          value={stockStatus}
          onChange={setStockStatus}
          options={STOCK_STATUS_OPTIONS}
        />
        <Input
          allowClear
          style={{ width: 260 }}
          placeholder="상품코드/상품명/바코드"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          onPressEnter={() => void loadInventory()}
        />
        <Button type="primary" icon={<SearchOutlined />} onClick={() => void loadInventory()} loading={loading}>
          조회
        </Button>
        <Button onClick={handleReset}>초기화</Button>
      </Space>

      {optionMessage ? <Alert type="info" showIcon message={optionMessage} /> : null}
      {errorMessage ? <SmartErrorNotice message={errorMessage} /> : null}

      <div className="smart-summary-grid">
        <SmartSummaryCard label="조회 재고" value={`${summary.total}건`} />
        <SmartSummaryCard label="정상재고 수량" value={`${summary.goodQty.toLocaleString()}개`} tone="success" />
        <SmartSummaryCard label="표시 기준" value="current_inventory" tone="neutral" />
      </div>

      <Typography.Text type="secondary">
        GOOD/양품 판정 row는 반품 일마감 확정 후 정상재고로 반영됩니다. 재고 이벤트 상세 이력은 후속 화면에서 다룹니다.
      </Typography.Text>

      <SmartDataGrid<CurrentInventoryItem>
        rows={rows}
        columns={columns}
        rowKey="inventory_id"
        loading={loading}
        emptyText="조회된 재고가 없습니다."
        preserveOriginalOrder
        maxHeight={430}
        enableCopy
      />
    </SmartPage>
  );
}

function getClientId(client: ClientSummary) {
  return client.client_id ?? client.id ?? 0;
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
      return "재고현황을 조회할 권한이 없습니다.";
    }
    return error.message || fallback;
  }
  return fallback;
}
