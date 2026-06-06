import { PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Switch, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "../../api/client";
import {
  createClientUnit,
  disableClientUnit,
  enableClientUnit,
  listClientUnits,
  listClientWarehouseOptions,
  updateClientUnit,
} from "../../api/master";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid";
import type { SmartDataGridColumn, SmartGridRowAction } from "../../components/grid";
import type { ClientUnit, ClientWarehouseOption } from "../../types/master";

interface ClientUnitFormValues {
  unit_code?: string;
  unit_name?: string;
  unit_type?: string | null;
  default_warehouse_id?: number | null;
  return_warehouse_id?: number | null;
  sort_order?: number;
  memo?: string | null;
}

export function ClientUnitsSection({ clientId }: { clientId: number }) {
  const [units, setUnits] = useState<ClientUnit[]>([]);
  const [warehouseOptions, setWarehouseOptions] = useState<ClientWarehouseOption[]>([]);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingUnit, setEditingUnit] = useState<ClientUnit | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [form] = Form.useForm<ClientUnitFormValues>();

  useEffect(() => {
    void loadUnits();
  }, [clientId, includeInactive]);

  const columns = useMemo<SmartDataGridColumn<ClientUnit>[]>(
    () => [
      { key: "unit_code", title: "팀코드", dataIndex: "unit_code", width: 140, copyable: true },
      { key: "unit_name", title: "팀명", dataIndex: "unit_name", minWidth: 180, copyable: true },
      { key: "unit_type", title: "유형", dataIndex: "unit_type", width: 120, render: (value) => toDisplayText(value) },
      {
        key: "default_warehouse_name",
        title: "기본창고",
        dataIndex: "default_warehouse_name",
        minWidth: 160,
        render: (value) => toDisplayText(value),
      },
      {
        key: "return_warehouse_name",
        title: "반품창고",
        dataIndex: "return_warehouse_name",
        minWidth: 160,
        render: (value) => toDisplayText(value),
      },
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

  const rowActions = useMemo<SmartGridRowAction<ClientUnit>[]>(
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

  async function loadUnits() {
    if (!Number.isFinite(clientId) || clientId <= 0) {
      return;
    }
    setLoading(true);
    setErrorMessage("");
    try {
      setUnits(await listClientUnits(clientId, { includeInactive }));
    } catch (error) {
      setErrorMessage(toUserMessage(error, "운영단위/팀 목록을 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function loadWarehouseOptions() {
    try {
      setWarehouseOptions(await listClientWarehouseOptions(clientId, { includeInactive: false }));
    } catch {
      setWarehouseOptions([]);
    }
  }

  function openCreateModal() {
    setEditingUnit(null);
    form.resetFields();
    form.setFieldsValue({ sort_order: units.length + 1 });
    setModalOpen(true);
    void loadWarehouseOptions();
  }

  function openEditModal(unit: ClientUnit) {
    setEditingUnit(unit);
    form.resetFields();
    form.setFieldsValue({
      unit_code: unit.unit_code,
      unit_name: unit.unit_name,
      unit_type: unit.unit_type,
      default_warehouse_id: unit.default_warehouse_id,
      return_warehouse_id: unit.return_warehouse_id,
      sort_order: unit.sort_order,
      memo: unit.memo,
    });
    setModalOpen(true);
    void loadWarehouseOptions();
  }

  async function handleSubmit() {
    const values = await form.validateFields();
    if (!values.unit_code || !values.unit_name) {
      return;
    }
    setSaving(true);
    try {
      if (editingUnit) {
        await updateClientUnit(clientId, editingUnit.unit_id, values);
        message.success("운영단위/팀을 수정했습니다.");
      } else {
        await createClientUnit(clientId, {
          unit_code: values.unit_code,
          unit_name: values.unit_name,
          unit_type: values.unit_type,
          default_warehouse_id: values.default_warehouse_id,
          return_warehouse_id: values.return_warehouse_id,
          sort_order: values.sort_order,
          memo: values.memo,
        });
        message.success("운영단위/팀을 추가했습니다.");
      }
      setModalOpen(false);
      await loadUnits();
    } catch (error) {
      message.error(toUserMessage(error, "운영단위/팀을 저장하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDisable(unit: ClientUnit) {
    setLoading(true);
    try {
      await disableClientUnit(clientId, unit.unit_id);
      message.success("운영단위/팀을 사용중지했습니다.");
      await loadUnits();
    } catch (error) {
      message.error(toUserMessage(error, "운영단위/팀을 사용중지하지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function handleEnable(unit: ClientUnit) {
    setLoading(true);
    try {
      await enableClientUnit(clientId, unit.unit_id);
      message.success("운영단위/팀을 사용 처리했습니다.");
      await loadUnits();
    } catch (error) {
      message.error(toUserMessage(error, "운영단위/팀을 사용 처리하지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card
      className="smart-work-panel"
      title="운영단위/팀"
      extra={
        <Space>
          <Switch checked={includeInactive} onChange={setIncludeInactive} checkedChildren="중지 포함" unCheckedChildren="사용중" />
          <Button icon={<ReloadOutlined />} onClick={() => void loadUnits()} loading={loading}>
            새로고침
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
            팀 추가
          </Button>
        </Space>
      }
    >
      <SmartErrorNotice message={errorMessage} />
      <SmartDataGrid<ClientUnit>
        rows={units}
        rowKey="unit_id"
        columns={columns}
        loading={loading}
        emptyText="등록된 운영단위/팀이 없습니다."
        rowActions={rowActions}
        maxHeight={300}
      />

      <Modal
        title={editingUnit ? "운영단위/팀 수정" : "운영단위/팀 추가"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => void handleSubmit()}
        confirmLoading={saving}
        okText="저장"
        cancelText="취소"
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item name="unit_code" label="팀코드" rules={[{ required: true, message: "팀코드를 입력하세요." }]}>
            <Input maxLength={80} placeholder="예: ONLINE" />
          </Form.Item>
          <Form.Item name="unit_name" label="팀명" rules={[{ required: true, message: "팀명을 입력하세요." }]}>
            <Input maxLength={255} placeholder="예: 온라인팀" />
          </Form.Item>
          <Form.Item name="unit_type" label="유형">
            <Input maxLength={50} placeholder="예: ONLINE, TOOL" />
          </Form.Item>
          <Form.Item name="default_warehouse_id" label="기본창고">
            <Select allowClear options={warehouseSelectOptions(warehouseOptions)} placeholder="기본창고 선택" />
          </Form.Item>
          <Form.Item name="return_warehouse_id" label="반품창고">
            <Select allowClear options={warehouseSelectOptions(warehouseOptions)} placeholder="반품창고 선택" />
          </Form.Item>
          <Form.Item name="sort_order" label="정렬순서">
            <InputNumber min={0} precision={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="memo" label="메모">
            <Input.TextArea rows={3} maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}

function warehouseSelectOptions(options: ClientWarehouseOption[]) {
  return options.map((option) => ({
    value: option.warehouse_id,
    label: `${option.warehouse_name} (${option.warehouse_code})`,
  }));
}

function toDisplayText(value: unknown, fallback = "-") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function toUserMessage(error: unknown, fallback: string) {
  if (error instanceof ApiClientError) {
    return error.message || fallback;
  }
  return fallback;
}
