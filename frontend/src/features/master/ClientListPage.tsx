import { EyeOutlined, PlusOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Input, Select, Space, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ApiClientError } from "../../api/client";
import { listClients } from "../../api/master";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn, SmartGridRowAction } from "../../components/grid/SmartDataGrid.types";
import type { ClientSummary } from "../../types/master";
import { getSearchString, mergeSearchParams } from "../../utils/routeState";

type ClientStatusFilter = "ALL" | "ACTIVE" | "INACTIVE";

const CLIENT_STATUS_OPTIONS: Array<{ value: ClientStatusFilter; label: string }> = [
  { value: "ALL", label: "전체" },
  { value: "ACTIVE", label: "사용" },
  { value: "INACTIVE", label: "중지" },
];

export function ClientListPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [keyword, setKeyword] = useState(() => getSearchString(searchParams, "keyword"));
  const [statusFilter, setStatusFilter] = useState<ClientStatusFilter>(() =>
    toClientStatusFilter(getSearchString(searchParams, "status", "ALL")),
  );
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    void loadClients();
  }, []);

  useEffect(() => {
    setSearchParams(
      mergeSearchParams(searchParams, {
        keyword: keyword.trim(),
        status: statusFilter === "ALL" ? undefined : statusFilter,
      }),
      { replace: true },
    );
  }, [keyword, statusFilter]);

  const filteredClients = useMemo(
    () =>
      clients.filter((client) => {
        const normalizedKeyword = keyword.trim().toLowerCase();
        const matchesKeyword =
          !normalizedKeyword ||
          client.client_code.toLowerCase().includes(normalizedKeyword) ||
          client.client_name.toLowerCase().includes(normalizedKeyword);
        const matchesStatus =
          statusFilter === "ALL" ||
          (statusFilter === "ACTIVE" && client.active_yn) ||
          (statusFilter === "INACTIVE" && !client.active_yn);
        return matchesKeyword && matchesStatus;
      }),
    [clients, keyword, statusFilter],
  );

  const columns = useMemo<SmartDataGridColumn<ClientSummary>[]>(
    () => [
      {
        key: "client_name",
        title: "고객사명",
        dataIndex: "client_name",
        width: 220,
        copyable: true,
        sortable: true,
      },
      {
        key: "client_code",
        title: "고객사 코드",
        dataIndex: "client_code",
        width: 170,
        copyable: true,
        sortable: true,
      },
      {
        key: "agency_name",
        title: "대리점/운영사",
        dataIndex: "agency_name",
        width: 160,
        render: (value) => toDisplayText(value, "본사 직영"),
      },
      {
        key: "active_yn",
        title: "사용 여부",
        dataIndex: "active_yn",
        width: 110,
        align: "center",
        render: (value) => <SmartStatusBadge status={value ? "NORMAL" : "INACTIVE"} label={value ? "사용중" : "사용중지"} />,
      },
      {
        key: "contract_type",
        title: "계약 유형",
        dataIndex: "contract_type",
        width: 130,
        render: (value) => toDisplayText(value, "후속"),
      },
      {
        key: "owner_type",
        title: "운영 주체",
        dataIndex: "owner_type",
        width: 130,
        render: (value) => toDisplayText(value, "후속"),
      },
      {
        key: "default_warehouse",
        title: "기본 창고",
        dataIndex: "default_warehouse",
        width: 150,
        render: (value) => toDisplayText(value),
      },
      {
        key: "default_processing_site",
        title: "기본 처리장소",
        dataIndex: "default_processing_site",
        width: 150,
        render: (value) => toDisplayText(value),
      },
      {
        key: "created_at",
        title: "등록일",
        dataIndex: "created_at",
        width: 120,
        render: (value) => formatDateText(value),
      },
      {
        key: "updated_at",
        title: "수정일",
        dataIndex: "updated_at",
        width: 120,
        render: (value) => formatDateText(value),
      },
    ],
    [],
  );

  const rowActions = useMemo<SmartGridRowAction<ClientSummary>[]>(
    () => [
      {
        key: "detail",
        label: "상세",
        icon: <EyeOutlined />,
        disabled: (record) => !getClientId(record),
        onClick: (record) => navigate(`/master/clients/${getClientId(record)}`),
      },
      {
        key: "edit",
        label: "수정 준비중",
        disabled: true,
        onClick: () => undefined,
      },
      {
        key: "disable",
        label: "사용중지 준비중",
        danger: true,
        disabled: true,
        onClick: () => undefined,
      },
    ],
    [navigate],
  );

  async function loadClients() {
    setLoading(true);
    setErrorMessage("");
    setNotice("");
    try {
      const items = await listClients();
      setClients(items);
      setNotice("고객사 목록을 불러왔습니다.");
    } catch (error) {
      setErrorMessage(toUserMessage(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="고객사/셀러"
        description="현재 고객사 목록 API 기준으로 고객사명, 코드, 사용 여부를 표시하는 기준정보 skeleton 화면입니다."
        extra={
          <Button icon={<PlusOutlined />} disabled>
            신규 고객사 준비중
          </Button>
        }
      />

      <section className="smart-toolbar" aria-label="고객사 목록 필터">
        <Input
          className="smart-control"
          allowClear
          prefix={<SearchOutlined />}
          placeholder="고객사명 또는 코드 검색"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
        <Select<ClientStatusFilter>
          className="smart-control"
          value={statusFilter}
          options={CLIENT_STATUS_OPTIONS}
          onChange={setStatusFilter}
        />
        <Button onClick={loadClients} loading={loading}>
          새로고침
        </Button>
        <Typography.Text type="secondary">현재 {filteredClients.length}건 표시</Typography.Text>
      </section>

      <SmartErrorNotice message={errorMessage} />
      {notice && !errorMessage ? <Alert type="success" message={notice} showIcon /> : null}

      <SmartDataGrid<ClientSummary>
        rowKey={(record) => getClientId(record)}
        rows={filteredClients}
        columns={columns}
        loading={loading}
        error={errorMessage || null}
        emptyText="표시할 고객사/셀러가 없습니다."
        enableCopy
        rowActions={rowActions}
        pagination={false}
        maxHeight={420}
        getRowClassName={(record) => (record.active_yn ? "" : "smart-grid-row-muted")}
      />

      <Alert
        type="info"
        showIcon
        message="상세와 창고/처리장소 설정은 후속 단계입니다."
        description="고객사 상세의 창고/처리장소 설정은 client_warehouse_settings API 보강 후 연결합니다."
      />
    </SmartPage>
  );
}

function getClientId(client: ClientSummary) {
  return Number(client.client_id || client.id || 0);
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

function toUserMessage(error: unknown) {
  if (error instanceof ApiClientError) {
    if (error.resultCode === "NOT_AUTHENTICATED" || error.resultCode === "INVALID_TOKEN") {
      return "로그인이 필요하거나 인증이 만료되었습니다. 다시 로그인해 주세요.";
    }
    if (error.status === 403) {
      return "고객사 목록을 볼 권한이 없습니다.";
    }
    return error.message || "고객사 목록을 불러오지 못했습니다.";
  }
  return "고객사 목록을 불러오지 못했습니다.";
}

function toClientStatusFilter(value: string): ClientStatusFilter {
  return value === "ACTIVE" || value === "INACTIVE" ? value : "ALL";
}
