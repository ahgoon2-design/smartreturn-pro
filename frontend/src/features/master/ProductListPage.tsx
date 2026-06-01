import { EyeOutlined, PlusOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Input, Result, Select, Space, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiClientError } from "../../api/client";
import { listProducts } from "../../api/master";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn, SmartGridRowAction } from "../../components/grid/SmartDataGrid.types";
import { ROUTE_PATHS } from "../../routes/routePaths";
import type { ProductSummary } from "../../types/master";

type ProductStatusFilter = "ALL" | "ACTIVE" | "INACTIVE";

const PRODUCT_STATUS_OPTIONS: Array<{ value: ProductStatusFilter; label: string }> = [
  { value: "ALL", label: "전체" },
  { value: "ACTIVE", label: "사용" },
  { value: "INACTIVE", label: "중지" },
];

export function ProductListPage() {
  const navigate = useNavigate();
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [keyword, setKeyword] = useState("");
  const [statusFilter, setStatusFilter] = useState<ProductStatusFilter>("ALL");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    void loadProducts();
  }, []);

  const filteredProducts = useMemo(
    () =>
      products.filter((product) => {
        const normalizedKeyword = keyword.trim().toLowerCase();
        const matchesKeyword =
          !normalizedKeyword ||
          product.product_code.toLowerCase().includes(normalizedKeyword) ||
          product.product_name.toLowerCase().includes(normalizedKeyword) ||
          product.client_name.toLowerCase().includes(normalizedKeyword) ||
          (product.barcode || "").toLowerCase().includes(normalizedKeyword);
        const matchesStatus =
          statusFilter === "ALL" ||
          (statusFilter === "ACTIVE" && product.active_yn) ||
          (statusFilter === "INACTIVE" && !product.active_yn);
        return matchesKeyword && matchesStatus;
      }),
    [keyword, products, statusFilter],
  );

  const columns = useMemo<SmartDataGridColumn<ProductSummary>[]>(
    () => [
      {
        key: "product_code",
        title: "상품코드",
        dataIndex: "product_code",
        width: 150,
        copyable: true,
        sortable: true,
      },
      {
        key: "product_name",
        title: "상품명",
        dataIndex: "product_name",
        minWidth: 220,
        copyable: true,
        sortable: true,
      },
      {
        key: "client_name",
        title: "고객사",
        dataIndex: "client_name",
        width: 180,
        copyable: true,
        sortable: true,
      },
      {
        key: "barcode",
        title: "대표 바코드",
        dataIndex: "barcode",
        width: 160,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "barcode_count",
        title: "바코드 수",
        width: 100,
        align: "right",
        render: () => "-",
      },
      {
        key: "product_group",
        title: "상품군",
        width: 120,
        render: () => "후속",
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
        key: "created_at",
        title: "등록일",
        dataIndex: "created_at",
        width: 116,
        render: (value) => formatDateText(value),
      },
      {
        key: "updated_at",
        title: "수정일",
        dataIndex: "updated_at",
        width: 116,
        render: (value) => formatDateText(value),
      },
    ],
    [],
  );

  const rowActions = useMemo<SmartGridRowAction<ProductSummary>[]>(
    () => [
      {
        key: "detail",
        label: "상세",
        icon: <EyeOutlined />,
        disabled: (record) => !record.product_id,
        onClick: (record) => navigate(`/master/products/${record.product_id}`),
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

  async function loadProducts() {
    setLoading(true);
    setErrorMessage("");
    try {
      const page = await listProducts({ page: 1, pageSize: 100 });
      setProducts(page.items);
      setTotalCount(page.total_count);
    } catch (error) {
      setErrorMessage(toUserMessage(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="상품/바코드"
        description="현재 상품 목록 API 기준으로 상품코드, 상품명, 대표 바코드, 사용 여부를 표시하는 기준정보 skeleton 화면입니다."
        extra={
          <Button icon={<PlusOutlined />} disabled>
            신규 상품 준비중
          </Button>
        }
      />

      <section className="smart-toolbar" aria-label="상품 목록 필터">
        <Input
          className="smart-control"
          allowClear
          prefix={<SearchOutlined />}
          placeholder="상품코드, 상품명, 고객사, 대표 바코드 검색"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
        <Select<ProductStatusFilter>
          className="smart-control"
          value={statusFilter}
          options={PRODUCT_STATUS_OPTIONS}
          onChange={setStatusFilter}
        />
        <Button onClick={loadProducts} loading={loading}>
          새로고침
        </Button>
        <Typography.Text type="secondary">
          현재 {filteredProducts.length}건 표시 / API 기준 {totalCount}건
        </Typography.Text>
      </section>

      <SmartErrorNotice message={errorMessage} />

      <SmartDataGrid<ProductSummary>
        rowKey="product_id"
        rows={filteredProducts}
        columns={columns}
        loading={loading}
        error={errorMessage || null}
        emptyText="표시할 상품/바코드가 없습니다."
        enableCopy
        rowActions={rowActions}
        pagination={false}
        maxHeight={420}
        getRowClassName={(record) => (record.active_yn ? "" : "smart-grid-row-muted")}
      />

      <Alert
        type="info"
        showIcon
        message="상품 상세와 바코드 관리는 다음 단계에서 구현합니다."
        description="현재 상품 목록 API에는 대표 바코드 외 바코드 수, 상품군, 비활성 포함 조회가 없어 해당 값은 '-' 또는 후속 항목으로 표시합니다."
      />
    </SmartPage>
  );
}

export function ProductDetailPlaceholderPage() {
  const navigate = useNavigate();
  const { productId } = useParams();

  return (
    <SmartPage>
      <Result
        status="info"
        title="상품 상세와 바코드 관리는 다음 단계에서 구현합니다."
        subTitle={`선택한 product_id: ${productId || "-"}. 이번 단계에서는 상품/바코드 목록과 상세 진입 경로만 연결했습니다.`}
        extra={
          <Space>
            <Button onClick={() => navigate(ROUTE_PATHS.masterProducts)}>상품 목록으로</Button>
          </Space>
        }
      />
    </SmartPage>
  );
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
      return "상품 목록을 볼 권한이 없습니다.";
    }
    return error.message || "상품 목록을 불러오지 못했습니다.";
  }
  return "상품 목록을 불러오지 못했습니다.";
}
