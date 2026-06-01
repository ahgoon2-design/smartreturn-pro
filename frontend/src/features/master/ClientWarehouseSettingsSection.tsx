import { PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Checkbox, Form, Modal, Select, Space, Switch, Typography, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "../../api/client";
import {
  createClientWarehouseSetting,
  disableClientWarehouseSetting,
  enableClientWarehouseSetting,
  listClientWarehouseOptions,
  listClientWarehouseSettings,
  setDefaultClientWarehouseSetting,
  updateClientWarehouseSetting,
} from "../../api/master";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid";
import type { SmartDataGridColumn, SmartGridRowAction } from "../../components/grid";
import type { ClientWarehouseOption, ClientWarehouseSetting } from "../../types/master";

const USAGE_TYPE_OPTIONS = [
  { value: "INBOUND", label: "입고" },
  { value: "OUTBOUND", label: "출고" },
  { value: "RETURN_GOOD", label: "반품양품" },
  { value: "RETURN_HOLD", label: "보류" },
  { value: "RETURN_DISPOSAL", label: "폐기" },
  { value: "RETURN_REFURB", label: "리퍼" },
  { value: "RETURN_MANUFACTURER", label: "제조사반품" },
  { value: "SAMPLE", label: "샘플" },
  { value: "STORAGE", label: "보관" },
];

interface WarehouseSettingFormValues {
  warehouse_id?: number;
  usage_type?: string;
  is_default?: boolean;
}

export function ClientWarehouseSettingsSection({ clientId }: { clientId: number }) {
  const [settings, setSettings] = useState<ClientWarehouseSetting[]>([]);
  const [warehouseOptions, setWarehouseOptions] = useState<ClientWarehouseOption[]>([]);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSetting, setEditingSetting] = useState<ClientWarehouseSetting | null>(null);
  const [form] = Form.useForm<WarehouseSettingFormValues>();

  useEffect(() => {
    void loadSettings();
  }, [clientId, includeInactive]);

  const columns = useMemo<SmartDataGridColumn<ClientWarehouseSetting>[]>(
    () => [
      {
        key: "usage_type",
        title: "사용 유형",
        dataIndex: "usage_type",
        width: 132,
        copyable: true,
        render: (_value, record) => record.usage_type_label || usageTypeLabel(record.usage_type),
      },
      {
        key: "warehouse_name",
        title: "창고명",
        dataIndex: "warehouse_name",
        minWidth: 180,
        copyable: true,
      },
      {
        key: "warehouse_code",
        title: "창고 코드",
        dataIndex: "warehouse_code",
        width: 140,
        copyable: true,
      },
      {
        key: "warehouse_type",
        title: "창고 유형",
        dataIndex: "warehouse_type",
        width: 120,
        render: (value) => toDisplayText(value),
      },
      {
        key: "is_default",
        title: "기본 여부",
        dataIndex: "is_default",
        width: 100,
        render: (value) =>
          value ? <SmartStatusBadge status="SUCCESS" label="기본" /> : <SmartStatusBadge status="WAITING" label="일반" />,
      },
      {
        key: "active_yn",
        title: "사용 여부",
        dataIndex: "active_yn",
        width: 110,
        render: (value) =>
          value ? <SmartStatusBadge status="NORMAL" label="사용중" /> : <SmartStatusBadge status="INACTIVE" label="사용중지" />,
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

  const rowActions = useMemo<SmartGridRowAction<ClientWarehouseSetting>[]>(
    () => [
      {
        key: "edit",
        label: "수정",
        disabled: (record) => !record.setting_id || !record.allowed_actions?.can_update,
        onClick: (record) => openEditModal(record),
      },
      {
        key: "set_default",
        label: "기본설정",
        disabled: (record) => !record.setting_id || !record.allowed_actions?.can_set_default,
        onClick: (record) => void handleSetDefault(record),
      },
      {
        key: "disable",
        label: "사용중지",
        danger: true,
        disabled: (record) => !record.setting_id || !record.active_yn || !record.allowed_actions?.can_disable,
        onClick: (record) => void handleDisable(record),
      },
      {
        key: "enable",
        label: "사용",
        disabled: (record) => !record.setting_id || record.active_yn || !record.allowed_actions?.can_enable,
        onClick: (record) => void handleEnable(record),
      },
    ],
    [],
  );

  async function loadSettings() {
    if (!Number.isFinite(clientId) || clientId <= 0) {
      return;
    }
    setLoading(true);
    setErrorMessage("");
    try {
      const data = await listClientWarehouseSettings(clientId, { includeInactive });
      setSettings(data);
    } catch (error) {
      setErrorMessage(toUserMessage(error, "창고/처리장소 설정을 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function loadWarehouseOptions() {
    setOptionsLoading(true);
    try {
      const data = await listClientWarehouseOptions(clientId, { includeInactive: false });
      setWarehouseOptions(data);
    } catch (error) {
      setWarehouseOptions([]);
      message.error(toUserMessage(error, "창고 후보를 불러오지 못했습니다."));
    } finally {
      setOptionsLoading(false);
    }
  }

  function openCreateModal() {
    setEditingSetting(null);
    form.resetFields();
    form.setFieldsValue({ is_default: false });
    setModalOpen(true);
    void loadWarehouseOptions();
  }

  function openEditModal(setting: ClientWarehouseSetting) {
    setEditingSetting(setting);
    form.resetFields();
    form.setFieldsValue({
      warehouse_id: setting.warehouse_id,
      usage_type: setting.usage_type,
      is_default: setting.is_default,
    });
    setModalOpen(true);
    void loadWarehouseOptions();
  }

  async function handleSubmit() {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editingSetting) {
        await updateClientWarehouseSetting(clientId, editingSetting.setting_id, {
          usage_type: values.usage_type,
        });
        message.success("창고 설정을 수정했습니다.");
      } else {
        if (!values.warehouse_id || !values.usage_type) {
          return;
        }
        await createClientWarehouseSetting(clientId, {
          warehouse_id: values.warehouse_id,
          usage_type: values.usage_type,
          is_default: Boolean(values.is_default),
        });
        message.success("창고 설정을 추가했습니다.");
      }
      setModalOpen(false);
      await loadSettings();
    } catch (error) {
      message.error(toUserMessage(error, editingSetting ? "창고 설정을 수정하지 못했습니다." : "창고 설정을 추가하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleSetDefault(record: ClientWarehouseSetting) {
    setSaving(true);
    try {
      await setDefaultClientWarehouseSetting(clientId, record.setting_id);
      message.success("기본 창고로 설정했습니다.");
      await loadSettings();
    } catch (error) {
      message.error(toUserMessage(error, "기본 창고로 설정하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDisable(record: ClientWarehouseSetting) {
    setSaving(true);
    try {
      await disableClientWarehouseSetting(clientId, record.setting_id);
      message.success("창고 설정을 사용중지했습니다.");
      await loadSettings();
    } catch (error) {
      message.error(toUserMessage(error, "창고 설정을 사용중지하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleEnable(record: ClientWarehouseSetting) {
    setSaving(true);
    try {
      await enableClientWarehouseSetting(clientId, record.setting_id);
      message.success("창고 설정을 사용 상태로 변경했습니다.");
      await loadSettings();
    } catch (error) {
      message.error(toUserMessage(error, "창고 설정을 사용 상태로 변경하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card
      className="smart-work-panel"
      title="창고/처리장소 설정"
      extra={
        <Space>
          <Space size={6}>
            <Typography.Text type="secondary">사용중지 포함</Typography.Text>
            <Switch checked={includeInactive} onChange={setIncludeInactive} />
          </Space>
          <Button icon={<ReloadOutlined />} onClick={() => loadSettings()} loading={loading}>
            새로고침
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
            설정 추가
          </Button>
        </Space>
      }
    >
      <Alert
        className="smart-section-notice"
        type="info"
        showIcon
        message="1차에서는 창고 기준으로 입고/출고/반품 등 사용 유형을 설정합니다."
        description="처리장소 개념은 후속 확장 후보이며, 현재 화면은 고객사별 사용 창고와 기본 창고 설정을 관리합니다."
      />

      <SmartErrorNotice message={errorMessage} />

      <SmartDataGrid<ClientWarehouseSetting>
        rows={settings}
        columns={columns}
        rowKey="setting_id"
        loading={loading || saving}
        error={null}
        emptyText="등록된 고객사 창고 설정이 없습니다."
        rowActions={rowActions}
        preserveOriginalOrder
        originalOrderKey="setting_id"
        enableCopy
        enableMultiSelect={false}
        maxHeight={320}
        getRowClassName={(record) => (!record.active_yn ? "smart-grid-row--inactive" : record.is_default ? "smart-grid-row--success" : "")}
      />

      <Modal
        title={editingSetting ? "창고 설정 수정" : "창고 설정 추가"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => void handleSubmit()}
        confirmLoading={saving}
        okText={editingSetting ? "수정" : "추가"}
        cancelText="취소"
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item name="warehouse_id" label="창고" rules={[{ required: !editingSetting, message: "창고를 선택해 주세요." }]}>
            <Select
              disabled={Boolean(editingSetting)}
              loading={optionsLoading}
              placeholder="창고를 선택해 주세요"
              options={warehouseOptions.map((option) => ({
                value: option.warehouse_id,
                label: `${option.warehouse_code} · ${option.warehouse_name}${option.warehouse_type ? ` (${option.warehouse_type})` : ""}`,
                disabled: !option.active_yn,
              }))}
            />
          </Form.Item>

          <Form.Item name="usage_type" label="사용 유형" rules={[{ required: true, message: "사용 유형을 선택해 주세요." }]}>
            <Select placeholder="사용 유형을 선택해 주세요" options={USAGE_TYPE_OPTIONS} />
          </Form.Item>

          {!editingSetting ? (
            <Form.Item name="is_default" valuePropName="checked">
              <Checkbox>이 사용 유형의 기본 창고로 지정</Checkbox>
            </Form.Item>
          ) : (
            <Alert
              type="warning"
              showIcon
              message="기본 창고 지정은 목록의 '기본설정' 작업으로 처리합니다."
              description="기본 창고인 설정의 사용 유형 변경은 서버 정책에 따라 차단될 수 있습니다."
            />
          )}
        </Form>
      </Modal>
    </Card>
  );
}

function usageTypeLabel(value: string) {
  return USAGE_TYPE_OPTIONS.find((option) => option.value === value)?.label || value;
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

function toUserMessage(error: unknown, fallback: string) {
  if (error instanceof ApiClientError) {
    if (error.resultCode === "NOT_AUTHENTICATED" || error.resultCode === "INVALID_TOKEN") {
      return "로그인이 필요하거나 인증이 만료되었습니다. 다시 로그인해 주세요.";
    }
    if (error.resultCode === "MASTER_CLIENT_WAREHOUSE_DEFAULT_DISABLE_DENIED") {
      return "기본 창고 설정은 바로 사용중지할 수 없습니다. 다른 창고를 기본으로 지정한 뒤 다시 시도해 주세요.";
    }
    if (error.resultCode === "MASTER_CLIENT_WAREHOUSE_INACTIVE") {
      return "사용중지된 창고 설정은 기본 창고로 지정할 수 없습니다.";
    }
    if (error.resultCode === "MASTER_CLIENT_WAREHOUSE_DUPLICATED") {
      return "이미 같은 창고와 사용 유형으로 등록된 설정이 있습니다.";
    }
    if (error.status === 403) {
      return "창고 설정을 처리할 권한이 없습니다.";
    }
    return error.message || fallback;
  }
  return fallback;
}
