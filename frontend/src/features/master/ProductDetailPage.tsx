import { ArrowLeftOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, Card, Descriptions, Form, Input, InputNumber, Modal, Result, Skeleton, Space, Typography, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiClientError } from "../../api/client";
import { createProductBarcode, disableProductBarcode, enableProductBarcode, getProduct, updateProductBarcode } from "../../api/master";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn, SmartGridRowAction } from "../../components/grid/SmartDataGrid.types";
import { useAuth } from "../../context/AuthContext";
import { ROUTE_PATHS } from "../../routes/routePaths";
import type { ProductBarcodeSummary, ProductDetail } from "../../types/master";

interface BarcodeFormValues {
  barcode?: string;
  barcode_type?: string;
  unit_qty?: number | null;
  remarks?: string | null;
}

export function ProductDetailPage() {
  const navigate = useNavigate();
  const { productId } = useParams();
  const { hasPermission } = useAuth();
  const parsedProductId = useMemo(() => Number(productId), [productId]);
  const canManageProduct = hasPermission("MASTER_MANAGE") && hasPermission("PRODUCT_MANAGE");
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingBarcode, setEditingBarcode] = useState<ProductBarcodeSummary | null>(null);
  const [form] = Form.useForm<BarcodeFormValues>();

  useEffect(() => {
    if (!Number.isFinite(parsedProductId) || parsedProductId <= 0) {
      setNotFound(true);
      setProduct(null);
      return;
    }
    void loadProduct(parsedProductId);
  }, [parsedProductId]);

  const barcodeColumns = useMemo<SmartDataGridColumn<ProductBarcodeSummary>[]>(
    () => [
      {
        key: "barcode",
        title: "바코드",
        dataIndex: "barcode",
        minWidth: 190,
        copyable: true,
        sortable: true,
      },
      {
        key: "barcode_type",
        title: "바코드 유형",
        dataIndex: "barcode_type",
        width: 140,
        copyable: true,
        sortable: true,
      },
      {
        key: "unit_qty",
        title: "수량",
        dataIndex: "unit_qty",
        width: 90,
        align: "right",
        sortable: true,
      },
      {
        key: "representative",
        title: "대표 여부",
        width: 110,
        align: "center",
        render: (_value, record) =>
          product?.barcode && record.barcode === product.barcode ? (
            <SmartStatusBadge status="SUCCESS" label="대표" />
          ) : (
            <SmartStatusBadge status="WAITING" label="일반" />
          ),
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
      {
        key: "remarks",
        title: "메모",
        dataIndex: "remarks",
        minWidth: 160,
        render: (value) => toDisplayText(value),
      },
    ],
    [product?.barcode],
  );

  const barcodeRowActions = useMemo<SmartGridRowAction<ProductBarcodeSummary>[]>(
    () => [
      {
        key: "edit",
        label: "수정",
        disabled: (record) => !canManageProduct || !record.barcode_id,
        onClick: (record) => openEditModal(record),
      },
      {
        key: "disable",
        label: "사용중지",
        danger: true,
        disabled: (record) => !canManageProduct || !record.barcode_id || !record.active_yn,
        onClick: (record) => void handleDisableBarcode(record),
      },
      {
        key: "enable",
        label: "사용",
        disabled: (record) => !canManageProduct || !record.barcode_id || record.active_yn,
        onClick: (record) => void handleEnableBarcode(record),
      },
    ],
    [canManageProduct],
  );

  async function loadProduct(nextProductId = parsedProductId) {
    if (!Number.isFinite(nextProductId) || nextProductId <= 0) {
      setNotFound(true);
      return;
    }
    setLoading(true);
    setErrorMessage("");
    setNotFound(false);
    try {
      const nextProduct = await getProduct(nextProductId);
      if (!nextProduct) {
        setProduct(null);
        setNotFound(true);
        return;
      }
      setProduct(nextProduct);
    } catch (error) {
      setErrorMessage(toUserMessage(error, "상품 정보를 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  function openCreateModal() {
    setEditingBarcode(null);
    form.resetFields();
    form.setFieldsValue({ unit_qty: 1 });
    setModalOpen(true);
  }

  function openEditModal(barcode: ProductBarcodeSummary) {
    setEditingBarcode(barcode);
    form.resetFields();
    form.setFieldsValue({
      barcode: barcode.barcode,
      barcode_type: barcode.barcode_type,
      unit_qty: barcode.unit_qty,
      remarks: barcode.remarks,
    });
    setModalOpen(true);
  }

  async function handleSubmitBarcode() {
    const values = await form.validateFields();
    const barcode = values.barcode?.trim();
    const barcodeType = values.barcode_type?.trim();
    const unitQty = Number(values.unit_qty);
    if (!barcode || !barcodeType || !Number.isFinite(unitQty) || unitQty < 1) {
      return;
    }

    setSaving(true);
    try {
      if (editingBarcode) {
        await updateProductBarcode(editingBarcode.barcode_id, {
          barcode,
          barcode_type: barcodeType,
          unit_qty: unitQty,
          remarks: normalizeOptionalText(values.remarks),
        });
        message.success("바코드를 수정했습니다.");
      } else {
        await createProductBarcode({
          product_id: parsedProductId,
          barcode,
          barcode_type: barcodeType,
          unit_qty: unitQty,
          remarks: normalizeOptionalText(values.remarks),
        });
        message.success("바코드를 추가했습니다.");
      }
      setModalOpen(false);
      await loadProduct();
    } catch (error) {
      message.error(toUserMessage(error, editingBarcode ? "바코드를 수정하지 못했습니다." : "바코드를 저장하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDisableBarcode(barcode: ProductBarcodeSummary) {
    setSaving(true);
    try {
      await disableProductBarcode(barcode.barcode_id);
      message.success("바코드를 사용중지했습니다.");
      await loadProduct();
    } catch (error) {
      message.error(toUserMessage(error, "바코드를 사용중지하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleEnableBarcode(barcode: ProductBarcodeSummary) {
    setSaving(true);
    try {
      await enableProductBarcode(barcode.barcode_id);
      message.success("바코드를 사용 상태로 변경했습니다.");
      await loadProduct();
    } catch (error) {
      message.error(toUserMessage(error, "바코드를 사용 상태로 변경하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="상품 상세"
        description="상품 기본정보와 상품별 바코드를 관리합니다. 상품 기본정보 수정은 후속 단계로 분리합니다."
        extra={
          <Space>
            {product ? <SmartStatusBadge status={product.active_yn ? "NORMAL" : "INACTIVE"} label={product.active_yn ? "사용중" : "사용중지"} /> : null}
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(ROUTE_PATHS.masterProducts)}>
              목록으로
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => loadProduct()} loading={loading}>
              새로고침
            </Button>
          </Space>
        }
      />

      <SmartErrorNotice message={errorMessage} />

      {loading ? <Skeleton active paragraph={{ rows: 8 }} /> : null}

      {!loading && notFound ? (
        <Result
          status="warning"
          title="상품을 찾을 수 없습니다."
          subTitle="요청한 상품 ID가 없거나 현재 계정으로 접근할 수 없습니다."
          extra={
            <Button type="primary" onClick={() => navigate(ROUTE_PATHS.masterProducts)}>
              목록으로
            </Button>
          }
        />
      ) : null}

      {!loading && product ? (
        <>
          <Card className="smart-work-panel" title="상품 기본정보">
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="product_id">
                <Typography.Text copyable>{product.product_id}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="사용 여부">
                <SmartStatusBadge status={product.active_yn ? "NORMAL" : "INACTIVE"} label={product.active_yn ? "사용중" : "사용중지"} />
              </Descriptions.Item>
              <Descriptions.Item label="상품코드">
                <Typography.Text copyable>{toDisplayText(product.product_code)}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="상품명">
                <Typography.Text copyable>{toDisplayText(product.product_name)}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="고객사">{toDisplayText(product.client_name)}</Descriptions.Item>
              <Descriptions.Item label="대표 바코드">
                {product.barcode ? <Typography.Text copyable>{product.barcode}</Typography.Text> : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="규격">{toDisplayText(product.specification)}</Descriptions.Item>
              <Descriptions.Item label="단위">{toDisplayText(product.unit_name)}</Descriptions.Item>
              <Descriptions.Item label="상품군">{toDisplayText(undefined, "후속")}</Descriptions.Item>
              <Descriptions.Item label="브랜드">{toDisplayText(undefined, "후속")}</Descriptions.Item>
              <Descriptions.Item label="등록일">{formatDateText(product.created_at)}</Descriptions.Item>
              <Descriptions.Item label="수정일">{formatDateText(product.updated_at)}</Descriptions.Item>
              <Descriptions.Item label="메모" span={2}>
                {toDisplayText(product.remarks)}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card
            className="smart-work-panel"
            title="바코드 관리"
            extra={
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal} disabled={!canManageProduct}>
                바코드 추가
              </Button>
            }
          >
            {!canManageProduct ? (
              <SmartErrorNotice message="현재 계정에는 상품바코드 변경 권한이 없어 조회만 가능합니다." />
            ) : null}
            <SmartDataGrid<ProductBarcodeSummary>
              rows={product.barcodes || []}
              columns={barcodeColumns}
              rowKey="barcode_id"
              loading={saving}
              emptyText="등록된 상품 바코드가 없습니다."
              rowActions={barcodeRowActions}
              enableCopy
              pagination={false}
              maxHeight={320}
              getRowClassName={(record) => (record.active_yn ? "" : "smart-grid-row-muted")}
            />
          </Card>

          <Card className="smart-work-panel" title="후속 구현">
            <Typography.Paragraph>
              상품 기본정보 수정, 대표 바코드 지정, 상품군/판정정책 연결은 후속 단계에서 별도 API 계약을 확인한 뒤 연결합니다.
            </Typography.Paragraph>
          </Card>
        </>
      ) : null}

      <Modal
        title={editingBarcode ? "바코드 수정" : "바코드 추가"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => void handleSubmitBarcode()}
        confirmLoading={saving}
        okText={editingBarcode ? "수정" : "추가"}
        cancelText="취소"
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item name="barcode" label="바코드" rules={[{ required: true, message: "바코드를 입력해 주세요." }]}>
            <Input placeholder="바코드" />
          </Form.Item>
          <Form.Item name="barcode_type" label="바코드 유형" rules={[{ required: true, message: "바코드 유형을 입력해 주세요." }]}>
            <Input placeholder="예: EACH, BOX, CARTON" />
          </Form.Item>
          <Form.Item name="unit_qty" label="수량" rules={[{ required: true, message: "수량을 입력해 주세요." }]}>
            <InputNumber className="smart-control" min={1} precision={0} placeholder="1" />
          </Form.Item>
          <Form.Item name="remarks" label="메모">
            <Input.TextArea rows={3} placeholder="필요 시 메모를 입력해 주세요." />
          </Form.Item>
        </Form>
      </Modal>
    </SmartPage>
  );
}

function toDisplayText(value: unknown, fallback = "-") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function normalizeOptionalText(value: string | null | undefined) {
  const normalized = value?.trim();
  return normalized || null;
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
      return "상품/바코드를 처리할 권한이 없습니다.";
    }
    if (error.status === 404 || error.resultCode === "MASTER_PRODUCT_NOT_FOUND") {
      return "상품을 찾을 수 없습니다.";
    }
    if (error.resultCode === "MASTER_PRODUCT_BARCODE_NOT_FOUND") {
      return "상품바코드를 찾을 수 없습니다.";
    }
    if (error.resultCode === "MASTER_PRODUCT_BARCODE_DUPLICATED") {
      return "이미 등록된 바코드입니다.";
    }
    if (error.resultCode === "MASTER_PRODUCT_BARCODE_INVALID" || error.status === 422) {
      return "바코드 입력값을 다시 확인해 주세요.";
    }
    return error.message || fallback;
  }
  return fallback;
}
