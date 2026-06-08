import { ApiOutlined, PlusOutlined, ReloadOutlined, SyncOutlined } from "@ant-design/icons";
import { Alert, Button, Form, Input, Select, Space, Switch, Typography, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "../../api/client";
import {
  createChannelAccount,
  disableChannelAccount,
  listChannelAccounts,
  listChannelRawEvents,
  listChannelReturnCandidates,
  listChannelSyncJobs,
  markChannelReturnCandidateReviewed,
  reprocessChannelReturnCandidate,
  runChannelDryRunSync,
  testChannelConnection,
  transformChannelAccountRawEvents,
  updateChannelAccount,
} from "../../api/channels";
import { listClients, listClientUnits } from "../../api/master";
import { SmartDataSection } from "../../components/common/SmartDataSection";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartModalShell } from "../../components/common/SmartModalShell";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartSummaryCard } from "../../components/common/SmartSummaryCard";
import { SmartDataGrid } from "../../components/grid";
import type { SmartDataGridColumn, SmartGridRowAction } from "../../components/grid";
import type {
  ChannelAccount,
  ChannelAccountCreatePayload,
  ChannelRawEventListItem,
  ChannelReturnCandidate,
  ChannelReturnCandidateStatus,
  ChannelSyncJob,
  ChannelType,
} from "../../types/channels";
import type { ClientSummary, ClientUnit } from "../../types/master";

interface ChannelAccountFormValues {
  client_id?: number;
  client_unit_id?: number | null;
  channel_type?: ChannelType;
  account_name?: string;
  store_name?: string;
  external_account_id?: string | null;
  credential_ref?: string | null;
  sync_enabled?: boolean;
}

const CHANNEL_OPTIONS: Array<{ value: ChannelType; label: string }> = [
  { value: "NAVER_SMARTSTORE", label: "네이버 스마트스토어" },
  { value: "COUPANG", label: "쿠팡 준비" },
  { value: "CAFE24", label: "카페24 준비" },
  { value: "EASYADMIN", label: "이지어드민 준비" },
  { value: "COURIER", label: "택배사 준비" },
];

const CANDIDATE_STATUS_OPTIONS: Array<{ value: ChannelReturnCandidateStatus | "ALL"; label: string }> = [
  { value: "ALL", label: "전체" },
  { value: "READY_FOR_INTAKE", label: "입고 준비" },
  { value: "TEAM_ASSIGN_PENDING", label: "팀 배정 필요" },
  { value: "PRODUCT_MATCH_PENDING", label: "상품 매칭 필요" },
  { value: "RETURN_TRACKING_PENDING", label: "반품송장 필요" },
  { value: "NEEDS_REVIEW", label: "확인 필요" },
  { value: "BLOCKED", label: "차단" },
];

export function ChannelAccountManagementScreen() {
  const [accounts, setAccounts] = useState<ChannelAccount[]>([]);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [clientUnits, setClientUnits] = useState<ClientUnit[]>([]);
  const [syncJobs, setSyncJobs] = useState<ChannelSyncJob[]>([]);
  const [rawEvents, setRawEvents] = useState<ChannelRawEventListItem[]>([]);
  const [candidates, setCandidates] = useState<ChannelReturnCandidate[]>([]);
  const [candidateSummary, setCandidateSummary] = useState<Record<string, number>>({});
  const [candidateStatusFilter, setCandidateStatusFilter] = useState<ChannelReturnCandidateStatus | "ALL">("ALL");
  const [selectedAccount, setSelectedAccount] = useState<ChannelAccount | null>(null);
  const [editingAccount, setEditingAccount] = useState<ChannelAccount | null>(null);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [notice, setNotice] = useState("");
  const [form] = Form.useForm<ChannelAccountFormValues>();
  const selectedClientId = Form.useWatch("client_id", form);

  useEffect(() => {
    void loadInitialData();
  }, [includeInactive, candidateStatusFilter]);

  useEffect(() => {
    if (selectedClientId) {
      void loadClientUnits(selectedClientId);
    } else {
      setClientUnits([]);
    }
  }, [selectedClientId]);

  const accountColumns = useMemo<SmartDataGridColumn<ChannelAccount>[]>(
    () => [
      { key: "store_name", title: "스토어명", dataIndex: "store_name", minWidth: 180, copyable: true },
      { key: "account_name", title: "계정명", dataIndex: "account_name", minWidth: 160, copyable: true },
      { key: "client_id", title: "고객사", dataIndex: "client_id", width: 150, render: (value) => clientName(Number(value)) },
      { key: "client_unit_id", title: "팀/운영단위", dataIndex: "client_unit_id", width: 150, render: (value) => unitName(Number(value)) },
      { key: "channel_type", title: "채널", dataIndex: "channel_type", width: 150, render: (value) => channelLabel(String(value)) },
      {
        key: "status",
        title: "상태",
        dataIndex: "status",
        width: 120,
        render: (value) => <SmartStatusBadge status={String(value)} label={accountStatusLabel(String(value))} />,
      },
      {
        key: "auth_status",
        title: "인증",
        dataIndex: "auth_status",
        width: 130,
        render: (value) => <SmartStatusBadge status={String(value)} label={authStatusLabel(String(value))} />,
      },
      {
        key: "sync_enabled",
        title: "수집",
        dataIndex: "sync_enabled",
        width: 90,
        render: (value) => (value ? <SmartStatusBadge status="SUCCESS" label="사용" /> : <SmartStatusBadge status="WAITING" label="중지" />),
      },
      { key: "credential_ref_masked", title: "인증 참조", dataIndex: "credential_ref_masked", width: 130, render: (value) => toDisplayText(value, "미연결") },
      { key: "last_success_sync_at", title: "마지막 성공", dataIndex: "last_success_sync_at", width: 150, render: formatDateTime },
    ],
    [clients, clientUnits],
  );

  const accountActions = useMemo<SmartGridRowAction<ChannelAccount>[]>(
    () => [
      { key: "edit", label: "수정", onClick: openEditModal },
      { key: "test", label: "연결 테스트", icon: <ApiOutlined />, onClick: (record) => void handleConnectionTest(record) },
      { key: "dry-run", label: "Dry-run 수집", icon: <SyncOutlined />, onClick: (record) => void handleDryRun(record) },
      { key: "transform", label: "원본 변환", icon: <SyncOutlined />, onClick: (record) => void handleTransformAccount(record) },
      {
        key: "disable",
        label: "비활성화",
        danger: true,
        disabled: (record) => record.status === "INACTIVE",
        onClick: (record) => void handleDisable(record),
      },
    ],
    [],
  );

  const jobColumns = useMemo<SmartDataGridColumn<ChannelSyncJob>[]>(
    () => [
      { key: "id", title: "Job ID", dataIndex: "id", width: 90 },
      { key: "job_type", title: "유형", dataIndex: "job_type", width: 180 },
      { key: "status", title: "상태", dataIndex: "status", width: 120, render: (value) => <SmartStatusBadge status={String(value)} /> },
      { key: "total_collected", title: "수집", dataIndex: "total_collected", width: 80, align: "right" },
      { key: "total_inserted", title: "추가", dataIndex: "total_inserted", width: 80, align: "right" },
      { key: "total_updated", title: "갱신", dataIndex: "total_updated", width: 80, align: "right" },
      { key: "finished_at", title: "완료시각", dataIndex: "finished_at", minWidth: 160, render: formatDateTime },
    ],
    [],
  );

  const rawEventColumns = useMemo<SmartDataGridColumn<ChannelRawEventListItem>[]>(
    () => [
      { key: "event_type", title: "이벤트", dataIndex: "event_type", width: 150 },
      { key: "external_product_order_id", title: "상품주문 ID", dataIndex: "external_product_order_id", minWidth: 180, copyable: true },
      { key: "external_claim_id", title: "클레임 ID", dataIndex: "external_claim_id", minWidth: 160, copyable: true },
      { key: "process_status", title: "처리상태", dataIndex: "process_status", width: 130, render: (value) => <SmartStatusBadge status={String(value)} /> },
      { key: "external_tracking_no_hash", title: "송장 hash", dataIndex: "external_tracking_no_hash", width: 150, render: (value) => shortHash(value) },
      { key: "collected_at", title: "수집시각", dataIndex: "collected_at", minWidth: 160, render: formatDateTime },
    ],
    [],
  );

  const candidateColumns = useMemo<SmartDataGridColumn<ChannelReturnCandidate>[]>(
    () => [
      {
        key: "match_status",
        title: "상태",
        dataIndex: "match_status",
        width: 150,
        render: (value) => <SmartStatusBadge status={String(value)} label={candidateStatusLabel(String(value))} />,
      },
      { key: "match_reason", title: "사유", dataIndex: "match_reason", minWidth: 240 },
      { key: "external_product_order_id", title: "상품주문 ID", dataIndex: "external_product_order_id", minWidth: 160, copyable: true },
      { key: "external_claim_id", title: "클레임 ID", dataIndex: "external_claim_id", minWidth: 140, copyable: true },
      { key: "tracking_no_for_scan", title: "스캔 송장", dataIndex: "tracking_no_for_scan", width: 140, copyable: true, render: (value) => toDisplayText(value) },
      { key: "product_code", title: "상품코드", dataIndex: "product_code", width: 130, copyable: true, render: (value) => toDisplayText(value) },
      { key: "product_name", title: "상품명", dataIndex: "product_name", minWidth: 180, render: (value) => toDisplayText(value) },
      { key: "qty", title: "수량", dataIndex: "qty", width: 80, align: "right", render: (value) => toDisplayText(value) },
      { key: "risk_flags", title: "위험", dataIndex: "risk_flags", minWidth: 170, render: (_value, record) => record.risk_flags?.join(", ") || "-" },
      { key: "updated_at", title: "갱신시각", dataIndex: "updated_at", width: 150, render: formatDateTime },
    ],
    [],
  );

  const candidateActions = useMemo<SmartGridRowAction<ChannelReturnCandidate>[]>(
    () => [
      { key: "reprocess", label: "재처리", icon: <SyncOutlined />, onClick: (record) => void handleReprocessCandidate(record) },
      {
        key: "reviewed",
        label: "확인 처리",
        disabled: (record) => Boolean(record.reviewed_at),
        onClick: (record) => void handleMarkReviewed(record),
      },
      { key: "create-return-expected", label: "반품예정 생성 예정", disabled: true, onClick: () => undefined },
    ],
    [],
  );

  async function loadInitialData() {
    setLoading(true);
    setErrorMessage("");
    try {
      const [clientItems, accountResult, jobResult, rawEventResult, candidateResult] = await Promise.all([
        listClients(),
        listChannelAccounts({ includeInactive }),
        listChannelSyncJobs(),
        listChannelRawEvents(),
        listChannelReturnCandidates(),
      ]);
      setClients(clientItems);
      setAccounts(accountResult.items);
      setSyncJobs(jobResult.items);
      setRawEvents(rawEventResult.items);
      setCandidates(candidateResult.items);
      setCandidateSummary(candidateResult.summary);
      setNotice("채널 연동 관리 정보를 불러왔습니다.");
    } catch (error) {
      setErrorMessage(toUserMessage(error, "채널 연동 관리 정보를 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function loadClientUnits(clientId: number) {
    try {
      setClientUnits(await listClientUnits(clientId, { includeInactive: false }));
    } catch {
      setClientUnits([]);
    }
  }

  function openCreateModal() {
    setEditingAccount(null);
    form.resetFields();
    form.setFieldsValue({ channel_type: "NAVER_SMARTSTORE", sync_enabled: false });
    setClientUnits([]);
    setModalOpen(true);
  }

  function openEditModal(account: ChannelAccount) {
    setEditingAccount(account);
    form.resetFields();
    form.setFieldsValue({
      client_id: account.client_id,
      client_unit_id: account.client_unit_id,
      channel_type: account.channel_type,
      account_name: account.account_name,
      store_name: account.store_name,
      external_account_id: account.external_account_id,
      credential_ref: undefined,
      sync_enabled: account.sync_enabled,
    });
    void loadClientUnits(account.client_id);
    setModalOpen(true);
  }

  async function handleSubmit() {
    const values = await form.validateFields();
    if (!values.client_id || !values.account_name || !values.store_name || !values.channel_type) {
      return;
    }
    setSaving(true);
    try {
      if (editingAccount) {
        await updateChannelAccount(editingAccount.id, {
          client_unit_id: values.client_unit_id,
          account_name: values.account_name,
          store_name: values.store_name,
          external_account_id: values.external_account_id,
          credential_ref: values.credential_ref,
          sync_enabled: values.sync_enabled,
        });
        message.success("채널 계정을 수정했습니다.");
      } else {
        const payload: ChannelAccountCreatePayload = {
          client_id: values.client_id,
          client_unit_id: values.client_unit_id,
          channel_type: values.channel_type,
          account_name: values.account_name,
          store_name: values.store_name,
          external_account_id: values.external_account_id,
          credential_ref: values.credential_ref,
          sync_enabled: Boolean(values.sync_enabled),
        };
        await createChannelAccount(payload);
        message.success("채널 계정을 추가했습니다.");
      }
      setModalOpen(false);
      await loadInitialData();
    } catch (error) {
      message.error(toUserMessage(error, "채널 계정을 저장하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  async function handleConnectionTest(account: ChannelAccount) {
    setActionLoadingId(account.id);
    try {
      const result = await testChannelConnection(account.id);
      message.success(result.message);
      await loadInitialData();
    } catch (error) {
      message.error(toUserMessage(error, "dry-run 연결 테스트에 실패했습니다."));
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleDryRun(account: ChannelAccount) {
    setActionLoadingId(account.id);
    try {
      const result = await runChannelDryRunSync(account.id, { job_type: "DRY_RUN", save_mock_event: true });
      message.success(result.message);
      setSelectedAccount(account);
      await loadInitialData();
    } catch (error) {
      message.error(toUserMessage(error, "dry-run 수집을 실행하지 못했습니다."));
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleTransformAccount(account: ChannelAccount) {
    setActionLoadingId(account.id);
    try {
      const result = await transformChannelAccountRawEvents(account.id);
      message.success(`원본 ${result.transformed_count}건을 반품접수 후보로 변환했습니다.`);
      setSelectedAccount(account);
      await loadInitialData();
    } catch (error) {
      message.error(toUserMessage(error, "원본 이벤트 변환을 실행하지 못했습니다."));
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleReprocessCandidate(candidate: ChannelReturnCandidate) {
    setActionLoadingId(candidate.channel_account_id);
    try {
      const result = await reprocessChannelReturnCandidate(candidate.id);
      message.success(result.message);
      await loadInitialData();
    } catch (error) {
      message.error(toUserMessage(error, "후보 재처리를 실행하지 못했습니다."));
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleMarkReviewed(candidate: ChannelReturnCandidate) {
    setActionLoadingId(candidate.channel_account_id);
    try {
      const result = await markChannelReturnCandidateReviewed(candidate.id);
      message.success(result.message);
      await loadInitialData();
    } catch (error) {
      message.error(toUserMessage(error, "후보 확인 처리를 실행하지 못했습니다."));
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleDisable(account: ChannelAccount) {
    setActionLoadingId(account.id);
    try {
      await disableChannelAccount(account.id);
      message.success("채널 계정을 비활성화했습니다.");
      await loadInitialData();
    } catch (error) {
      message.error(toUserMessage(error, "채널 계정을 비활성화하지 못했습니다."));
    } finally {
      setActionLoadingId(null);
    }
  }

  function clientName(clientId: number) {
    const item = clients.find((client) => Number(client.client_id || client.id) === clientId);
    return item ? item.client_name : `#${clientId}`;
  }

  function unitName(unitId: number) {
    if (!unitId) {
      return "-";
    }
    const item = clientUnits.find((unit) => unit.unit_id === unitId);
    return item ? item.unit_name : `#${unitId}`;
  }

  const selectedJobs = selectedAccount ? syncJobs.filter((job) => job.channel_account_id === selectedAccount.id) : syncJobs;
  const selectedEvents = selectedAccount ? rawEvents.filter((event) => event.channel_account_id === selectedAccount.id) : rawEvents;
  const filteredCandidates = candidates.filter(
    (candidate) => candidateStatusFilter === "ALL" || candidate.match_status === candidateStatusFilter,
  );
  const selectedCandidates = selectedAccount
    ? filteredCandidates.filter((candidate) => candidate.channel_account_id === selectedAccount.id)
    : filteredCandidates;

  return (
    <SmartPage>
      <SmartPageHeader
        title="채널 연동 관리"
        description="외부 채널 자동수집 계정과 dry-run 수집 상태를 관리합니다."
        extra={
          <Space>
            <Switch checked={includeInactive} onChange={setIncludeInactive} checkedChildren="중지 포함" unCheckedChildren="사용중" />
            <Button icon={<ReloadOutlined />} onClick={() => void loadInitialData()} loading={loading}>
              새로고침
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
              계정 추가
            </Button>
          </Space>
        }
      />

      <Alert
        type="info"
        showIcon
        message="현재는 실제 네이버 API 호출 전 skeleton 단계입니다."
        description="secret/token은 화면에 표시하지 않습니다. return_tracking_no는 현장 스캔 기준이며 원송장은 보조 조회 후보로만 사용합니다."
      />
      <SmartErrorNotice message={errorMessage} />
      {notice && !errorMessage ? <Typography.Text type="secondary">{notice}</Typography.Text> : null}

      <SmartDataSection title="채널 계정">
        <SmartDataGrid<ChannelAccount>
          rows={accounts}
          rowKey="id"
          columns={accountColumns}
          loading={loading || actionLoadingId !== null}
          emptyText="등록된 채널 계정이 없습니다."
          rowActions={accountActions}
          onRowClick={setSelectedAccount}
          selectedRowKeys={selectedAccount ? [selectedAccount.id] : []}
          maxHeight={360}
          enableCopy
        />
      </SmartDataSection>

      <SmartDataSection title={selectedAccount ? `${selectedAccount.store_name} dry-run 이력` : "dry-run 이력"}>
        <SmartDataGrid<ChannelSyncJob>
          rows={selectedJobs}
          rowKey="id"
          columns={jobColumns}
          loading={loading}
          emptyText="dry-run 수집 job이 없습니다."
          maxHeight={240}
        />
      </SmartDataSection>

      <SmartDataSection title="원본 이벤트 요약">
        <SmartDataGrid<ChannelRawEventListItem>
          rows={selectedEvents}
          rowKey="id"
          columns={rawEventColumns}
          loading={loading}
          emptyText="수집된 원본 이벤트 요약이 없습니다."
          maxHeight={260}
          enableCopy
        />
      </SmartDataSection>

      <section className="smart-summary-grid" aria-label="채널 반품 후보 요약">
        <SmartSummaryCard label="입고 준비" value={`${candidateSummary.READY_FOR_INTAKE || 0}건`} />
        <SmartSummaryCard label="팀 배정 필요" value={`${candidateSummary.TEAM_ASSIGN_PENDING || 0}건`} />
        <SmartSummaryCard label="상품 매칭 필요" value={`${candidateSummary.PRODUCT_MATCH_PENDING || 0}건`} />
        <SmartSummaryCard label="반품송장 필요" value={`${candidateSummary.RETURN_TRACKING_PENDING || 0}건`} />
        <SmartSummaryCard label="확인 필요" value={`${candidateSummary.NEEDS_REVIEW || 0}건`} />
        <SmartSummaryCard label="차단" value={`${candidateSummary.BLOCKED || 0}건`} />
      </section>

      <SmartDataSection
        title={selectedAccount ? `${selectedAccount.store_name} 반품접수 후보` : "반품접수 후보"}
        extra={
          <Space>
            <Select
              style={{ width: 180 }}
              value={candidateStatusFilter}
              options={CANDIDATE_STATUS_OPTIONS}
              onChange={setCandidateStatusFilter}
            />
            <Button
              icon={<SyncOutlined />}
              disabled={!selectedAccount}
              loading={actionLoadingId === selectedAccount?.id}
              onClick={() => selectedAccount && void handleTransformAccount(selectedAccount)}
            >
              선택 계정 원본 변환
            </Button>
          </Space>
        }
      >
        <SmartDataGrid<ChannelReturnCandidate>
          rows={selectedCandidates}
          rowKey="id"
          columns={candidateColumns}
          loading={loading || actionLoadingId !== null}
          emptyText="변환된 반품접수 후보가 없습니다."
          rowActions={candidateActions}
          maxHeight={360}
          enableCopy
        />
      </SmartDataSection>

      <SmartModalShell
        title={editingAccount ? "채널 계정 수정" : "채널 계정 추가"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => void handleSubmit()}
        confirmLoading={saving}
        okText="저장"
        cancelText="취소"
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item name="client_id" label="고객사" rules={[{ required: true, message: "고객사를 선택하세요." }]}>
            <Select showSearch optionFilterProp="label" disabled={Boolean(editingAccount)} options={clientOptions(clients)} placeholder="고객사 선택" />
          </Form.Item>
          <Form.Item name="client_unit_id" label="팀/운영단위">
            <Select allowClear optionFilterProp="label" options={unitOptions(clientUnits)} placeholder="선택 사항" />
          </Form.Item>
          <Form.Item name="channel_type" label="채널 유형" rules={[{ required: true, message: "채널 유형을 선택하세요." }]}>
            <Select options={CHANNEL_OPTIONS} />
          </Form.Item>
          <Form.Item name="account_name" label="계정명" rules={[{ required: true, message: "계정명을 입력하세요." }]}>
            <Input maxLength={255} placeholder="예: 네이버 기본 계정" />
          </Form.Item>
          <Form.Item name="store_name" label="스토어명" rules={[{ required: true, message: "스토어명을 입력하세요." }]}>
            <Input maxLength={255} placeholder="예: 스마트스토어명" />
          </Form.Item>
          <Form.Item name="external_account_id" label="외부 계정 ID">
            <Input maxLength={255} placeholder="선택 사항" />
          </Form.Item>
          <Form.Item name="credential_ref" label="인증 참조">
            <Input maxLength={255} placeholder="예: channel/naver/store-a" />
          </Form.Item>
          <Form.Item name="sync_enabled" label="자동수집 사용" valuePropName="checked">
            <Switch checkedChildren="사용" unCheckedChildren="중지" />
          </Form.Item>
        </Form>
      </SmartModalShell>
    </SmartPage>
  );
}

function clientOptions(clients: ClientSummary[]) {
  return clients.map((client) => ({
    value: Number(client.client_id || client.id),
    label: `${client.client_name} (${client.client_code})`,
  }));
}

function unitOptions(units: ClientUnit[]) {
  return units.map((unit) => ({
    value: unit.unit_id,
    label: `${unit.unit_name} (${unit.unit_code})`,
  }));
}

function channelLabel(value: string) {
  return CHANNEL_OPTIONS.find((option) => option.value === value)?.label || value;
}

function accountStatusLabel(value: string) {
  return (
    {
      ACTIVE: "사용",
      INACTIVE: "비활성",
      AUTH_REQUIRED: "인증 필요",
      ERROR: "오류",
    }[value] || value
  );
}

function authStatusLabel(value: string) {
  return (
    {
      NOT_CONNECTED: "미연결",
      CONNECTED: "연결됨",
      EXPIRED: "만료",
      ERROR: "오류",
    }[value] || value
  );
}

function candidateStatusLabel(value: string) {
  return (
    {
      READY_FOR_INTAKE: "입고 준비",
      TEAM_ASSIGN_PENDING: "팀 배정 필요",
      PRODUCT_MATCH_PENDING: "상품 매칭 필요",
      RETURN_TRACKING_PENDING: "반품송장 필요",
      NEEDS_REVIEW: "확인 필요",
      BLOCKED: "차단",
    }[value] || value
  );
}

function toDisplayText(value: unknown, fallback = "-") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function formatDateTime(value: unknown) {
  if (!value) {
    return "-";
  }
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString("ko-KR", { hour12: false });
}

function shortHash(value: unknown) {
  const text = toDisplayText(value);
  return text.length > 16 ? `${text.slice(0, 12)}...` : text;
}

function toUserMessage(error: unknown, fallback: string) {
  if (error instanceof ApiClientError) {
    if (error.status === 403) {
      return "채널 연동 관리 권한이 없습니다.";
    }
    return error.message || fallback;
  }
  return fallback;
}
