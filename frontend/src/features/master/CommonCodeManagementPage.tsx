import { PlusOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Form, Input, InputNumber, Modal, Select, Space, Typography, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "../../api/client";
import {
  createCommonCode,
  createCommonCodeGroup,
  disableCommonCode,
  disableCommonCodeGroup,
  enableCommonCode,
  enableCommonCodeGroup,
  listCommonCodeGroups,
  listCommonCodes,
  updateCommonCode,
  updateCommonCodeGroup,
} from "../../api/master";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid";
import type { SmartDataGridColumn, SmartGridRowAction } from "../../components/grid";
import { useAuth } from "../../context/AuthContext";
import type { CommonCodeGroupSummary, CommonCodeSummary } from "../../types/master";

type ActiveFilter = "ALL" | "ACTIVE" | "INACTIVE";
type ModalTarget = "GROUP" | "CODE";

const ACTIVE_FILTER_OPTIONS: Array<{ value: ActiveFilter; label: string }> = [
  { value: "ALL", label: "전체" },
  { value: "ACTIVE", label: "사용" },
  { value: "INACTIVE", label: "중지" },
];

interface CommonCodeGroupFormValues {
  group_code?: string;
  group_name?: string;
  description?: string | null;
}

interface CommonCodeFormValues {
  code_value?: string;
  code_name?: string;
  sort_order?: number | null;
  description?: string | null;
}

export function CommonCodeManagementPage() {
  const { hasPermission } = useAuth();
  const canManageCommonCode = hasPermission("MASTER_MANAGE") && hasPermission("COMMON_CODE_MANAGE");
  const [groups, setGroups] = useState<CommonCodeGroupSummary[]>([]);
  const [codes, setCodes] = useState<CommonCodeSummary[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<CommonCodeGroupSummary | null>(null);
  const [groupKeyword, setGroupKeyword] = useState("");
  const [codeKeyword, setCodeKeyword] = useState("");
  const [groupStatusFilter, setGroupStatusFilter] = useState<ActiveFilter>("ALL");
  const [codeStatusFilter, setCodeStatusFilter] = useState<ActiveFilter>("ALL");
  const [groupsLoading, setGroupsLoading] = useState(false);
  const [codesLoading, setCodesLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [groupErrorMessage, setGroupErrorMessage] = useState("");
  const [codeErrorMessage, setCodeErrorMessage] = useState("");
  const [modalTarget, setModalTarget] = useState<ModalTarget>("GROUP");
  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [codeModalOpen, setCodeModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<CommonCodeGroupSummary | null>(null);
  const [editingCode, setEditingCode] = useState<CommonCodeSummary | null>(null);
  const [groupForm] = Form.useForm<CommonCodeGroupFormValues>();
  const [codeForm] = Form.useForm<CommonCodeFormValues>();

  useEffect(() => {
    void loadGroups();
  }, []);

  useEffect(() => {
    if (selectedGroup) {
      void loadCodes(selectedGroup.group_code);
      return;
    }
    setCodes([]);
  }, [selectedGroup?.group_code]);

  const filteredGroups = useMemo(
    () =>
      groups.filter((group) => {
        const keyword = groupKeyword.trim().toLowerCase();
        const matchesKeyword =
          !keyword ||
          group.group_code.toLowerCase().includes(keyword) ||
          group.group_name.toLowerCase().includes(keyword);
        const matchesStatus =
          groupStatusFilter === "ALL" ||
          (groupStatusFilter === "ACTIVE" && group.active_yn) ||
          (groupStatusFilter === "INACTIVE" && !group.active_yn);
        return matchesKeyword && matchesStatus;
      }),
    [groupKeyword, groupStatusFilter, groups],
  );

  const filteredCodes = useMemo(
    () =>
      codes.filter((code) => {
        const keyword = codeKeyword.trim().toLowerCase();
        const matchesKeyword =
          !keyword ||
          code.code_value.toLowerCase().includes(keyword) ||
          code.code_name.toLowerCase().includes(keyword);
        const matchesStatus =
          codeStatusFilter === "ALL" ||
          (codeStatusFilter === "ACTIVE" && code.active_yn) ||
          (codeStatusFilter === "INACTIVE" && !code.active_yn);
        return matchesKeyword && matchesStatus;
      }),
    [codeKeyword, codeStatusFilter, codes],
  );

  const groupColumns = useMemo<SmartDataGridColumn<CommonCodeGroupSummary>[]>(
    () => [
      {
        key: "group_code",
        title: "코드그룹",
        dataIndex: "group_code",
        width: 170,
        copyable: true,
        sortable: true,
      },
      {
        key: "group_name",
        title: "코드그룹명",
        dataIndex: "group_name",
        minWidth: 180,
        copyable: true,
        sortable: true,
      },
      {
        key: "description",
        title: "설명",
        dataIndex: "description",
        minWidth: 140,
        render: () => "-",
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
        key: "sort_order",
        title: "정렬순서",
        width: 90,
        align: "right",
        render: () => "-",
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

  const codeColumns = useMemo<SmartDataGridColumn<CommonCodeSummary>[]>(
    () => [
      {
        key: "code_value",
        title: "코드값",
        dataIndex: "code_value",
        width: 170,
        copyable: true,
        sortable: true,
      },
      {
        key: "code_name",
        title: "코드명",
        dataIndex: "code_name",
        minWidth: 180,
        copyable: true,
        sortable: true,
      },
      {
        key: "description",
        title: "설명",
        dataIndex: "description",
        minWidth: 140,
        render: () => "-",
      },
      {
        key: "sort_order",
        title: "정렬순서",
        dataIndex: "sort_order",
        width: 100,
        align: "right",
        sortable: true,
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

  const groupRowActions = useMemo<SmartGridRowAction<CommonCodeGroupSummary>[]>(
    () => [
      {
        key: "edit",
        label: "수정",
        disabled: () => !canManageCommonCode,
        onClick: (record) => openGroupEditModal(record),
      },
      {
        key: "disable",
        label: "사용중지",
        danger: true,
        disabled: (record) => !canManageCommonCode || !record.active_yn,
        onClick: (record) => void handleDisableGroup(record),
      },
      {
        key: "enable",
        label: "사용",
        disabled: (record) => !canManageCommonCode || record.active_yn,
        onClick: (record) => void handleEnableGroup(record),
      },
    ],
    [canManageCommonCode],
  );

  const codeRowActions = useMemo<SmartGridRowAction<CommonCodeSummary>[]>(
    () => [
      {
        key: "edit",
        label: "수정",
        disabled: () => !canManageCommonCode,
        onClick: (record) => openCodeEditModal(record),
      },
      {
        key: "disable",
        label: "사용중지",
        danger: true,
        disabled: (record) => !canManageCommonCode || !record.active_yn,
        onClick: (record) => void handleDisableCode(record),
      },
      {
        key: "enable",
        label: "사용",
        disabled: (record) => !canManageCommonCode || record.active_yn,
        onClick: (record) => void handleEnableCode(record),
      },
    ],
    [canManageCommonCode],
  );

  async function loadGroups() {
    setGroupsLoading(true);
    setGroupErrorMessage("");
    try {
      const nextGroups = await listCommonCodeGroups();
      setGroups(nextGroups);
      setSelectedGroup((current) => {
        if (current && nextGroups.some((group) => group.group_id === current.group_id)) {
          return nextGroups.find((group) => group.group_id === current.group_id) || current;
        }
        return nextGroups[0] || null;
      });
    } catch (error) {
      setGroupErrorMessage(toUserMessage(error, "공통코드 그룹을 불러오지 못했습니다."));
    } finally {
      setGroupsLoading(false);
    }
  }

  async function loadCodes(groupCode: string) {
    setCodesLoading(true);
    setCodeErrorMessage("");
    try {
      const nextCodes = await listCommonCodes(groupCode);
      setCodes(nextCodes);
    } catch (error) {
      setCodeErrorMessage(toUserMessage(error, "공통코드를 불러오지 못했습니다."));
    } finally {
      setCodesLoading(false);
    }
  }

  function openGroupCreateModal() {
    setEditingGroup(null);
    groupForm.resetFields();
    setModalTarget("GROUP");
    setGroupModalOpen(true);
  }

  function openGroupEditModal(group: CommonCodeGroupSummary) {
    setEditingGroup(group);
    groupForm.resetFields();
    groupForm.setFieldsValue({
      group_code: group.group_code,
      group_name: group.group_name,
    });
    setModalTarget("GROUP");
    setGroupModalOpen(true);
  }

  function openCodeCreateModal() {
    if (!selectedGroup) {
      message.warning("코드 그룹을 먼저 선택해 주세요.");
      return;
    }
    setEditingCode(null);
    codeForm.resetFields();
    codeForm.setFieldsValue({ sort_order: 0 });
    setModalTarget("CODE");
    setCodeModalOpen(true);
  }

  function openCodeEditModal(code: CommonCodeSummary) {
    setEditingCode(code);
    codeForm.resetFields();
    codeForm.setFieldsValue({
      code_value: code.code_value,
      code_name: code.code_name,
      sort_order: code.sort_order,
    });
    setModalTarget("CODE");
    setCodeModalOpen(true);
  }

  async function handleSubmitGroup() {
    const values = await groupForm.validateFields();
    const groupCode = values.group_code?.trim();
    const groupName = values.group_name?.trim();
    if (!groupName || (!editingGroup && !groupCode)) {
      return;
    }
    setSaving(true);
    try {
      if (editingGroup) {
        await updateCommonCodeGroup(editingGroup.group_id, {
          group_name: groupName,
        });
        message.success("코드 그룹을 수정했습니다.");
      } else {
        await createCommonCodeGroup({
          group_code: groupCode || "",
          group_name: groupName,
          description: normalizeOptionalText(values.description),
        });
        message.success("코드 그룹을 추가했습니다.");
      }
      setGroupModalOpen(false);
      await loadGroups();
    } catch (error) {
      message.error(toUserMessage(error, editingGroup ? "코드 그룹을 수정하지 못했습니다." : "코드 그룹을 저장하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmitCode() {
    if (!selectedGroup) {
      message.warning("코드 그룹을 먼저 선택해 주세요.");
      return;
    }
    const values = await codeForm.validateFields();
    const codeValue = values.code_value?.trim();
    const codeName = values.code_name?.trim();
    const sortOrder = Number(values.sort_order ?? 0);
    if (!codeName || (!editingCode && !codeValue) || !Number.isFinite(sortOrder)) {
      return;
    }
    setSaving(true);
    try {
      if (editingCode) {
        await updateCommonCode(editingCode.code_id, {
          code_name: codeName,
          sort_order: sortOrder,
        });
        message.success("공통코드를 수정했습니다.");
      } else {
        await createCommonCode({
          group_id: selectedGroup.group_id,
          code_value: codeValue || "",
          code_name: codeName,
          sort_order: sortOrder,
          description: normalizeOptionalText(values.description),
        });
        message.success("공통코드를 추가했습니다.");
      }
      setCodeModalOpen(false);
      await loadCodes(selectedGroup.group_code);
    } catch (error) {
      message.error(toUserMessage(error, editingCode ? "공통코드를 수정하지 못했습니다." : "공통코드를 저장하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDisableGroup(group: CommonCodeGroupSummary) {
    setSaving(true);
    try {
      await disableCommonCodeGroup(group.group_id);
      message.success("코드 그룹을 사용중지했습니다.");
      await loadGroups();
    } catch (error) {
      message.error(toUserMessage(error, "코드 그룹을 사용중지하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleEnableGroup(group: CommonCodeGroupSummary) {
    setSaving(true);
    try {
      await enableCommonCodeGroup(group.group_id);
      message.success("코드 그룹을 사용 상태로 변경했습니다.");
      await loadGroups();
    } catch (error) {
      message.error(toUserMessage(error, "코드 그룹을 사용 상태로 변경하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDisableCode(code: CommonCodeSummary) {
    if (!selectedGroup) {
      return;
    }
    setSaving(true);
    try {
      await disableCommonCode(code.code_id);
      message.success("공통코드를 사용중지했습니다.");
      await loadCodes(selectedGroup.group_code);
    } catch (error) {
      message.error(toUserMessage(error, "공통코드를 사용중지하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleEnableCode(code: CommonCodeSummary) {
    if (!selectedGroup) {
      return;
    }
    setSaving(true);
    try {
      await enableCommonCode(code.code_id);
      message.success("공통코드를 사용 상태로 변경했습니다.");
      await loadCodes(selectedGroup.group_code);
    } catch (error) {
      message.error(toUserMessage(error, "공통코드를 사용 상태로 변경하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="공통코드"
        description="업무 화면의 Select 하드코딩을 줄이기 위한 코드 그룹과 코드값을 관리합니다."
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => loadGroups()} loading={groupsLoading}>
              새로고침
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openGroupCreateModal} disabled={!canManageCommonCode}>
              그룹 추가
            </Button>
            <Button icon={<PlusOutlined />} onClick={openCodeCreateModal} disabled={!canManageCommonCode || !selectedGroup}>
              코드 추가
            </Button>
          </Space>
        }
      />

      {!canManageCommonCode ? (
        <Alert
          type="info"
          showIcon
          message="현재 계정은 공통코드 조회만 가능합니다."
          description="코드 그룹과 코드값의 추가, 수정, 사용중지, 사용 처리는 COMMON_CODE_MANAGE 권한이 필요합니다."
        />
      ) : null}

      <div className="smart-master-split">
        <Card className="smart-work-panel smart-master-split-panel" title="코드 그룹">
          <section className="smart-toolbar" aria-label="코드 그룹 필터">
            <Input
              className="smart-control"
              allowClear
              prefix={<SearchOutlined />}
              placeholder="코드그룹 또는 코드그룹명 검색"
              value={groupKeyword}
              onChange={(event) => setGroupKeyword(event.target.value)}
            />
            <Select<ActiveFilter>
              className="smart-control"
              value={groupStatusFilter}
              options={ACTIVE_FILTER_OPTIONS}
              onChange={setGroupStatusFilter}
            />
            <Typography.Text type="secondary">현재 {filteredGroups.length}건</Typography.Text>
          </section>
          <SmartErrorNotice message={groupErrorMessage} />
          <SmartDataGrid<CommonCodeGroupSummary>
            rows={filteredGroups}
            columns={groupColumns}
            rowKey="group_id"
            loading={groupsLoading || saving}
            error={groupErrorMessage || null}
            emptyText="표시할 코드 그룹이 없습니다."
            rowActions={groupRowActions}
            enableCopy
            enableMultiSelect={false}
            selectedRowKeys={selectedGroup ? [selectedGroup.group_id] : []}
            onSelectionChange={(_keys, selectedRows) => setSelectedGroup(selectedRows[0] || null)}
            onRowClick={(record) => setSelectedGroup(record)}
            maxHeight={360}
            getRowClassName={(record) =>
              [!record.active_yn ? "smart-grid-row-muted" : "", selectedGroup?.group_id === record.group_id ? "smart-grid-row--selected" : ""]
                .filter(Boolean)
                .join(" ")
            }
          />
        </Card>

        <Card
          className="smart-work-panel smart-master-split-panel"
          title={selectedGroup ? `코드 목록 · ${selectedGroup.group_name}` : "코드 목록"}
        >
          <section className="smart-toolbar" aria-label="공통코드 필터">
            <Input
              className="smart-control"
              allowClear
              prefix={<SearchOutlined />}
              placeholder="코드값 또는 코드명 검색"
              value={codeKeyword}
              onChange={(event) => setCodeKeyword(event.target.value)}
              disabled={!selectedGroup}
            />
            <Select<ActiveFilter>
              className="smart-control"
              value={codeStatusFilter}
              options={ACTIVE_FILTER_OPTIONS}
              onChange={setCodeStatusFilter}
              disabled={!selectedGroup}
            />
            <Typography.Text type="secondary">{selectedGroup ? `현재 ${filteredCodes.length}건` : "코드 그룹을 선택하세요"}</Typography.Text>
          </section>
          <SmartErrorNotice message={codeErrorMessage} />
          <SmartDataGrid<CommonCodeSummary>
            rows={selectedGroup ? filteredCodes : []}
            columns={codeColumns}
            rowKey="code_id"
            loading={codesLoading || saving}
            error={codeErrorMessage || null}
            emptyText={selectedGroup ? "표시할 공통코드가 없습니다." : "코드 그룹을 선택하세요."}
            rowActions={codeRowActions}
            enableCopy
            preserveOriginalOrder
            originalOrderKey="sort_order"
            enableMultiSelect={false}
            maxHeight={360}
            getRowClassName={(record) => (!record.active_yn ? "smart-grid-row-muted" : "")}
          />
        </Card>
      </div>

      <Alert
        type="warning"
        showIcon
        message="현재 공통코드 API 응답 기준 안내"
        description="목록 API는 현재 active 데이터 중심이며 설명, 등록일, 수정일, locked/system 여부를 응답하지 않습니다. 해당 값은 화면에서 추정하지 않고 '-' 또는 후속 항목으로 표시합니다."
      />

      <Modal
        title={editingGroup ? "코드 그룹 수정" : "코드 그룹 추가"}
        open={groupModalOpen && modalTarget === "GROUP"}
        onCancel={() => setGroupModalOpen(false)}
        onOk={() => void handleSubmitGroup()}
        confirmLoading={saving}
        okText={editingGroup ? "수정" : "추가"}
        cancelText="취소"
        destroyOnHidden
      >
        <Form form={groupForm} layout="vertical">
          <Form.Item name="group_code" label="코드그룹" rules={[{ required: !editingGroup, message: "코드그룹을 입력해 주세요." }]}>
            <Input disabled={Boolean(editingGroup)} placeholder="예: RETURN_STATUS" />
          </Form.Item>
          <Form.Item name="group_name" label="코드그룹명" rules={[{ required: true, message: "코드그룹명을 입력해 주세요." }]}>
            <Input placeholder="예: 반품상태" />
          </Form.Item>
          {!editingGroup ? (
            <Form.Item name="description" label="설명">
              <Input.TextArea rows={3} placeholder="필요 시 설명을 입력해 주세요." />
            </Form.Item>
          ) : (
            <Alert type="info" showIcon message="코드그룹 값은 생성 후 변경하지 않습니다." />
          )}
        </Form>
      </Modal>

      <Modal
        title={editingCode ? "공통코드 수정" : "공통코드 추가"}
        open={codeModalOpen && modalTarget === "CODE"}
        onCancel={() => setCodeModalOpen(false)}
        onOk={() => void handleSubmitCode()}
        confirmLoading={saving}
        okText={editingCode ? "수정" : "추가"}
        cancelText="취소"
        destroyOnHidden
      >
        <Form form={codeForm} layout="vertical">
          <Form.Item name="code_value" label="코드값" rules={[{ required: !editingCode, message: "코드값을 입력해 주세요." }]}>
            <Input disabled={Boolean(editingCode)} placeholder="예: RECEIVED" />
          </Form.Item>
          <Form.Item name="code_name" label="코드명" rules={[{ required: true, message: "코드명을 입력해 주세요." }]}>
            <Input placeholder="예: 접수" />
          </Form.Item>
          <Form.Item name="sort_order" label="정렬순서" rules={[{ required: true, message: "정렬순서를 입력해 주세요." }]}>
            <InputNumber className="smart-control" precision={0} />
          </Form.Item>
          {!editingCode ? (
            <Form.Item name="description" label="설명">
              <Input.TextArea rows={3} placeholder="필요 시 설명을 입력해 주세요." />
            </Form.Item>
          ) : (
            <Alert type="info" showIcon message="코드값은 생성 후 변경하지 않습니다. 코드명과 정렬순서만 수정합니다." />
          )}
        </Form>
      </Modal>
    </SmartPage>
  );
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
      return "공통코드를 처리할 권한이 없습니다.";
    }
    if (error.resultCode === "MASTER_COMMON_CODE_GROUP_DUPLICATED") {
      return "이미 등록된 코드 그룹입니다.";
    }
    if (error.resultCode === "MASTER_COMMON_CODE_DUPLICATED") {
      return "이미 등록된 공통코드입니다.";
    }
    if (error.resultCode === "MASTER_COMMON_CODE_GROUP_NOT_FOUND") {
      return "코드 그룹을 찾을 수 없습니다.";
    }
    if (error.resultCode === "MASTER_COMMON_CODE_NOT_FOUND") {
      return "공통코드를 찾을 수 없습니다.";
    }
    if (error.resultCode === "MASTER_COMMON_CODE_GROUP_INACTIVE") {
      return "사용중지된 코드 그룹에는 코드를 추가할 수 없습니다.";
    }
    if (error.resultCode === "MASTER_COMMON_CODE_LOCKED") {
      return "시스템 또는 잠긴 공통코드는 변경할 수 없습니다.";
    }
    if (error.status === 422) {
      return "입력값을 다시 확인해 주세요.";
    }
    return error.message || fallback;
  }
  return fallback;
}
