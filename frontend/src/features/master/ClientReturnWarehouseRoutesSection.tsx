import { PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, Form, Input, InputNumber, Select, Space, Switch, Typography, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "../../api/client";
import {
  createReturnWarehouseRoute,
  disableReturnWarehouseRoute,
  enableReturnWarehouseRoute,
  listClientUnits,
  listClientWarehouseOptions,
  listReturnWarehouseRoutes,
  updateReturnWarehouseRoute,
} from "../../api/master";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartDataSection } from "../../components/common/SmartDataSection";
import { SmartModalShell } from "../../components/common/SmartModalShell";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid";
import type { SmartDataGridColumn, SmartGridRowAction } from "../../components/grid";
import type { ClientUnit, ClientWarehouseOption, ReturnWarehouseRoute } from "../../types/master";

const JUDGEMENT_OPTIONS = [
  { value: "GOOD", label: "양품" },
  { value: "REFURB", label: "리퍼" },
  { value: "REFURB_A", label: "리퍼A" },
  { value: "REFURB_B", label: "리퍼B" },
  { value: "REFURB_C", label: "리퍼C" },
  { value: "SAMPLE", label: "샘플" },
  { value: "MANUFACTURER_RETURN", label: "제조사반품" },
  { value: "DISPOSAL", label: "폐기" },
  { value: "HOLD", label: "보류" },
];

interface RouteFormValues {
  client_unit_id?: number | null;
  judgment_code?: string;
  warehouse_id?: number;
  sort_order?: number;
  memo?: string | null;
}

export function ClientReturnWarehouseRoutesSection({ clientId }: { clientId: number }) {
  const [routes, setRoutes] = useState<ReturnWarehouseRoute[]>([]);
  const [units, setUnits] = useState<ClientUnit[]>([]);
  const [warehouseOptions, setWarehouseOptions] = useState<ClientWarehouseOption[]>([]);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRoute, setEditingRoute] = useState<ReturnWarehouseRoute | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [form] = Form.useForm<RouteFormValues>();

  useEffect(() => {
    void loadRoutes();
  }, [clientId, includeInactive]);

  const columns = useMemo<SmartDataGridColumn<ReturnWarehouseRoute>[]>(
    () => [
      {
        key: "judgment_code",
        title: "판정",
        dataIndex: "judgment_code",
        width: 148,
        render: (value) => judgementLabel(String(value || "")),
      },
      {
        key: "client_unit_name",
        title: "운영단위/팀",
        dataIndex: "client_unit_name",
        minWidth: 160,
        render: (value) => toDisplayText(value, "고객사 기본"),
      },
      {
        key: "warehouse_name",
        title: "창고",
        dataIndex: "warehouse_name",
        minWidth: 180,
        copyable: true,
        render: (value, record) => toDisplayText(value || record.warehouse_code),
      },
      { key: "warehouse_code", title: "창고코드", dataIndex: "warehouse_code", width: 132, copyable: true },
      {
        key: "active_yn",
        title: "사용여부",
        dataIndex: "active_yn",
        width: 104,
        render: (value) =>
          value ? <SmartStatusBadge status="NORMAL" label="사용중" /> : <SmartStatusBadge status="INACTIVE" label="사용중지" />,
      },
      { key: "sort_order", title: "정렬", dataIndex: "sort_order", width: 84 },
      { key: "memo", title: "메모", dataIndex: "memo", minWidth: 180, render: (value) => toDisplayText(value) },
    ],
    [],
  );

  const rowActions = useMemo<SmartGridRowAction<ReturnWarehouseRoute>[]>(
    () => [
      { key: "edit", label: "수정", onClick: (record) => openEditModal(record) },
      {
        key: "disable",
        label: "사용중지",
        danger: true,
        disabled: (record) => !record.active_yn,
        onClick: (record) => void handleDisable(record),
      },
      {
        key: "enable",
        label: "사용",
        disabled: (record) => record.active_yn,
        onClick: (record) => void handleEnable(record),
      },
    ],
    [],
  );

  async function loadRoutes() {
    if (!Number.isFinite(clientId) || clientId <= 0) {
      return;
    }
    setLoading(true);
    setErrorMessage("");
    try {
      setRoutes(await listReturnWarehouseRoutes(clientId, { includeInactive }));
    } catch (error) {
      setErrorMessage(toUserMessage(error, "판정별 창고 라우팅 목록을 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function loadOptions() {
    const [nextUnits, nextWarehouses] = await Promise.all([
      listClientUnits(clientId, { includeInactive: false }),
      listClientWarehouseOptions(clientId, { includeInactive: false }),
    ]);
    setUnits(nextUnits.filter((unit) => unit.active_yn));
    setWarehouseOptions(nextWarehouses.filter((warehouse) => warehouse.active_yn));
  }

  function openCreateModal() {
    setEditingRoute(null);
    form.resetFields();
    form.setFieldsValue({ sort_order: routes.length + 1 });
    setModalOpen(true);
    void loadOptions();
  }

  function openEditModal(route: ReturnWarehouseRoute) {
    setEditingRoute(route);
    form.resetFields();
    form.setFieldsValue({
      client_unit_id: route.client_unit_id,
      judgment_code: route.judgment_code,
      warehouse_id: route.warehouse_id,
      sort_order: route.sort_order,
      memo: route.memo,
    });
    setModalOpen(true);
    void loadOptions();
  }

  async function handleSubmit() {
    const values = await form.validateFields();
    if (!values.judgment_code || !values.warehouse_id) {
      return;
    }
    setSaving(true);
    try {
      const payload = {
        client_unit_id: values.client_unit_id ?? null,
        judgment_code: values.judgment_code,
        warehouse_id: values.warehouse_id,
        sort_order: values.sort_order,
        memo: values.memo,
      };
      if (editingRoute) {
        await updateReturnWarehouseRoute(clientId, editingRoute.route_id, payload);
        message.success("판정별 창고 라우팅을 수정했습니다.");
      } else {
        await createReturnWarehouseRoute(clientId, payload);
        message.success("판정별 창고 라우팅을 추가했습니다.");
      }
      setModalOpen(false);
      await loadRoutes();
    } catch (error) {
      message.error(toUserMessage(error, "판정별 창고 라우팅을 저장하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDisable(route: ReturnWarehouseRoute) {
    setSaving(true);
    try {
      await disableReturnWarehouseRoute(clientId, route.route_id);
      message.success("판정별 창고 라우팅을 사용중지했습니다.");
      await loadRoutes();
    } catch (error) {
      message.error(toUserMessage(error, "판정별 창고 라우팅을 사용중지하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleEnable(route: ReturnWarehouseRoute) {
    setSaving(true);
    try {
      await enableReturnWarehouseRoute(clientId, route.route_id);
      message.success("판정별 창고 라우팅을 사용 처리했습니다.");
      await loadRoutes();
    } catch (error) {
      message.error(toUserMessage(error, "판정별 창고 라우팅을 사용 처리하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <SmartDataSection
      title="판정별 창고 라우팅"
      extra={
        <Space>
          <Space size={6}>
            <Typography.Text type="secondary">사용중지 포함</Typography.Text>
            <Switch checked={includeInactive} onChange={setIncludeInactive} />
          </Space>
          <Button icon={<ReloadOutlined />} onClick={() => void loadRoutes()} loading={loading}>
            새로고침
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
            라우팅 추가
          </Button>
        </Space>
      }
    >
      <Typography.Paragraph type="secondary">
        팀별 라우팅이 있으면 우선 적용하고, 없으면 고객사 기본 라우팅을 사용합니다. 최종 창고가 없으면 일마감 재고반영은 실패 처리됩니다.
      </Typography.Paragraph>
      <SmartErrorNotice message={errorMessage} />
      <SmartDataGrid<ReturnWarehouseRoute>
        rows={routes}
        rowKey="route_id"
        columns={columns}
        loading={loading || saving}
        emptyText="등록된 판정별 창고 라우팅이 없습니다."
        rowActions={rowActions}
        preserveOriginalOrder
        originalOrderKey="sort_order"
        enableCopy
        maxHeight={320}
        getRowClassName={(record) => (!record.active_yn ? "smart-grid-row--inactive" : "")}
      />

      <SmartModalShell
        title={editingRoute ? "판정별 창고 라우팅 수정" : "판정별 창고 라우팅 추가"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => void handleSubmit()}
        confirmLoading={saving}
        okText={editingRoute ? "수정" : "추가"}
        cancelText="취소"
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item name="client_unit_id" label="운영단위/팀">
            <Select
              allowClear
              placeholder="미선택 시 고객사 기본 라우팅"
              options={units.map((unit) => ({ value: unit.unit_id, label: `${unit.unit_name} (${unit.unit_code})` }))}
            />
          </Form.Item>
          <Form.Item name="judgment_code" label="판정" rules={[{ required: true, message: "판정을 선택하세요." }]}>
            <Select options={JUDGEMENT_OPTIONS} placeholder="판정을 선택하세요." />
          </Form.Item>
          <Form.Item name="warehouse_id" label="창고" rules={[{ required: true, message: "창고를 선택하세요." }]}>
            <Select
              placeholder="창고를 선택하세요."
              options={warehouseOptions.map((warehouse) => ({
                value: warehouse.warehouse_id,
                label: `${warehouse.warehouse_name} (${warehouse.warehouse_code})`,
              }))}
            />
          </Form.Item>
          <Form.Item name="sort_order" label="정렬순서">
            <InputNumber min={0} precision={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="memo" label="메모">
            <Input.TextArea rows={3} maxLength={500} />
          </Form.Item>
        </Form>
      </SmartModalShell>
    </SmartDataSection>
  );
}

function judgementLabel(value: string) {
  return JUDGEMENT_OPTIONS.find((option) => option.value === value)?.label || value || "-";
}

function toDisplayText(value: unknown, fallback = "-") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function toUserMessage(error: unknown, fallback: string) {
  if (error instanceof ApiClientError) {
    if (error.status === 403) {
      return "판정별 창고 라우팅을 처리할 권한이 없습니다.";
    }
    return error.message || fallback;
  }
  return fallback;
}
