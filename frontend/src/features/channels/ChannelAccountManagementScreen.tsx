import { ApiOutlined, EditOutlined, PlusOutlined, ReloadOutlined, SyncOutlined } from "@ant-design/icons";
import { Alert, Button, Form, Input, InputNumber, Modal, Segmented, Select, Space, Switch, Typography, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "../../api/client";
import {
  approveProductChannelMapping,
  createChannelAccount,
  createReturnExpectedFromChannelAccount,
  createReturnExpectedFromChannelCandidate,
  clearChannelReturnCandidateCorrection,
  disableProductChannelMapping,
  disableChannelAccount,
  enableProductChannelMapping,
  getChannelDashboardSummary,
  listChannelAccounts,
  listProductChannelMappings,
  listChannelRawEvents,
  listChannelReturnCandidates,
  listChannelSyncJobs,
  markChannelReturnCandidateReviewed,
  reprocessChannelReturnCandidate,
  rebuildProductChannelMappingConflicts,
  rejectProductChannelMapping,
  runChannelDryRunSync,
  testChannelConnection,
  transformChannelAccountRawEvents,
  updateChannelAccount,
  updateChannelReturnCandidateCorrection,
} from "../../api/channels";
import { listClients, listClientUnits, listProducts } from "../../api/master";
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
  ChannelDashboardSummary,
  ChannelRawEventListItem,
  ChannelReturnCandidate,
  ChannelReturnCandidateCorrectionPayload,
  ChannelReturnNextAction,
  ChannelReturnCandidateStatus,
  ChannelSyncJob,
  ChannelType,
  ProductChannelMapping,
} from "../../types/channels";
import type { ClientSummary, ClientUnit, ProductSummary } from "../../types/master";

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

interface CandidateCorrectionFormValues {
  client_unit_id?: number | null;
  product_id?: number | null;
  return_tracking_no?: string | null;
  original_tracking_no?: string | null;
  qty?: number | null;
  review_note?: string | null;
}

const CHANNEL_OPTIONS: Array<{ value: ChannelType; label: string }> = [
  { value: "NAVER_SMARTSTORE", label: "네이버 스마트스토어" },
  { value: "COUPANG", label: "쿠팡 준비" },
  { value: "CAFE24", label: "카페24 준비" },
  { value: "EASYADMIN", label: "이지어드민 준비" },
  { value: "COURIER", label: "택배사 준비" },
];

type CandidateStatusFilter = ChannelReturnCandidateStatus | "ALL" | "CREATED";

const CANDIDATE_STATUS_OPTIONS: Array<{ value: CandidateStatusFilter; label: string }> = [
  { value: "ALL", label: "전체" },
  { value: "READY_FOR_INTAKE", label: "입고 준비" },
  { value: "TEAM_ASSIGN_PENDING", label: "팀 배정 필요" },
  { value: "PRODUCT_MATCH_PENDING", label: "상품 매칭 필요" },
  { value: "RETURN_TRACKING_PENDING", label: "반품송장 필요" },
  { value: "NEEDS_REVIEW", label: "확인 필요" },
  { value: "BLOCKED", label: "차단" },
  { value: "CREATED", label: "생성됨" },
];

const DASHBOARD_EMPTY: ChannelDashboardSummary = {
  total_accounts: 0,
  active_accounts: 0,
  auth_required_accounts: 0,
  error_accounts: 0,
  total_raw_events: 0,
  raw_events_today: 0,
  raw_event_failed_count: 0,
  total_candidates: 0,
  candidates_today: 0,
  ready_for_intake_count: 0,
  team_assign_pending_count: 0,
  product_match_pending_count: 0,
  return_tracking_pending_count: 0,
  needs_review_count: 0,
  blocked_count: 0,
  return_expected_created_count: 0,
  return_expected_failed_count: 0,
  correction_required_count: 0,
  corrected_count: 0,
  product_mapping_count: 0,
  product_mapping_conflict_count: 0,
};

export function ChannelAccountManagementScreen() {
  const [accounts, setAccounts] = useState<ChannelAccount[]>([]);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [clientUnits, setClientUnits] = useState<ClientUnit[]>([]);
  const [correctionUnits, setCorrectionUnits] = useState<ClientUnit[]>([]);
  const [correctionProducts, setCorrectionProducts] = useState<ProductSummary[]>([]);
  const [syncJobs, setSyncJobs] = useState<ChannelSyncJob[]>([]);
  const [rawEvents, setRawEvents] = useState<ChannelRawEventListItem[]>([]);
  const [candidates, setCandidates] = useState<ChannelReturnCandidate[]>([]);
  const [dashboardSummary, setDashboardSummary] = useState<ChannelDashboardSummary>(DASHBOARD_EMPTY);
  const [productMappings, setProductMappings] = useState<ProductChannelMapping[]>([]);
  const [productMappingSummary, setProductMappingSummary] = useState<Record<string, number>>({});
  const [candidateSummary, setCandidateSummary] = useState<Record<string, number>>({});
  const [candidateStatusFilter, setCandidateStatusFilter] = useState<CandidateStatusFilter>("ALL");
  const [candidateKeyword, setCandidateKeyword] = useState("");
  const [mappingStatusFilter, setMappingStatusFilter] = useState<"ALL" | "ACTIVE" | "CONFLICT" | "INACTIVE" | "REJECTED">("ALL");
  const [selectedAccount, setSelectedAccount] = useState<ChannelAccount | null>(null);
  const [editingAccount, setEditingAccount] = useState<ChannelAccount | null>(null);
  const [correctingCandidate, setCorrectingCandidate] = useState<ChannelReturnCandidate | null>(null);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [notice, setNotice] = useState("");
  const [form] = Form.useForm<ChannelAccountFormValues>();
  const [correctionForm] = Form.useForm<CandidateCorrectionFormValues>();
  const selectedClientId = Form.useWatch("client_id", form);

  useEffect(() => {
    void loadInitialData();
  }, [includeInactive, candidateStatusFilter, mappingStatusFilter]);

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
      {
        key: "next_recommended_action",
        title: "다음 작업",
        dataIndex: "next_recommended_action",
        width: 150,
        render: (value) => <SmartStatusBadge status={String(value || "WAITING")} label={nextActionLabel(value as ChannelReturnNextAction)} />,
      },
      { key: "action_reason", title: "작업 사유", dataIndex: "action_reason", minWidth: 220, render: (value) => toDisplayText(value) },
      { key: "match_reason", title: "사유", dataIndex: "match_reason", minWidth: 240 },
      { key: "external_product_order_id", title: "상품주문 ID", dataIndex: "external_product_order_id", minWidth: 160, copyable: true },
      { key: "external_claim_id", title: "클레임 ID", dataIndex: "external_claim_id", minWidth: 140, copyable: true },
      { key: "tracking_no_for_scan", title: "스캔 송장", dataIndex: "tracking_no_for_scan", width: 140, copyable: true, render: (value) => toDisplayText(value) },
      { key: "product_code", title: "상품코드", dataIndex: "product_code", width: 130, copyable: true, render: (value) => toDisplayText(value) },
      { key: "product_name", title: "상품명", dataIndex: "product_name", minWidth: 180, render: (value) => toDisplayText(value) },
      { key: "qty", title: "수량", dataIndex: "qty", width: 80, align: "right", render: (value) => toDisplayText(value) },
      { key: "risk_flags", title: "위험", dataIndex: "risk_flags", minWidth: 170, render: (_value, record) => record.risk_flags?.join(", ") || "-" },
      {
        key: "correction_status",
        title: "보정",
        dataIndex: "correction_status",
        width: 120,
        render: (value) => <SmartStatusBadge status={String(value)} label={correctionStatusLabel(String(value))} />,
      },
      {
        key: "return_expected_create_status",
        title: "반품예정",
        dataIndex: "return_expected_create_status",
        width: 130,
        render: (value) => <SmartStatusBadge status={String(value)} label={returnExpectedCreateStatusLabel(String(value))} />,
      },
      {
        key: "return_expected_id",
        title: "연결 row",
        dataIndex: "return_expected_id",
        width: 100,
        render: (value) => toDisplayText(value),
      },
      {
        key: "return_expected_create_error",
        title: "생성 사유",
        dataIndex: "return_expected_create_error",
        minWidth: 180,
        render: (value) => toDisplayText(value),
      },
      { key: "updated_at", title: "갱신시각", dataIndex: "updated_at", width: 150, render: formatDateTime },
    ],
    [],
  );

  const candidateActions = useMemo<SmartGridRowAction<ChannelReturnCandidate>[]>(
    () => [
      {
        key: "reprocess",
        label: "재처리",
        icon: <SyncOutlined />,
        disabled: (record) => !record.safe_to_reprocess,
        onClick: (record) => void handleReprocessCandidate(record),
      },
      {
        key: "correction",
        label: "보정",
        icon: <EditOutlined />,
        disabled: (record) => !record.safe_to_correct,
        onClick: (record) => void openCorrectionModal(record),
      },
      {
        key: "reviewed",
        label: "확인 처리",
        disabled: (record) => Boolean(record.reviewed_at),
        onClick: (record) => void handleMarkReviewed(record),
      },
      {
        key: "create-return-expected",
        label: "반품예정 생성",
        disabled: (record) => !record.safe_to_create_return_expected,
        onClick: (record) => void handleCreateReturnExpected(record),
      },
    ],
    [],
  );

  const productMappingColumns = useMemo<SmartDataGridColumn<ProductChannelMapping>[]>(
    () => [
      {
        key: "conflict_status",
        title: "충돌",
        dataIndex: "conflict_status",
        width: 120,
        render: (value) =>
          value === "CONFLICT" ? <SmartStatusBadge status="ERROR" label="충돌" /> : <SmartStatusBadge status="SUCCESS" label="정상" />,
      },
      { key: "account_name", title: "계정", dataIndex: "account_name", width: 150, render: (value) => toDisplayText(value) },
      { key: "external_seller_product_code", title: "외부 상품코드", dataIndex: "external_seller_product_code", minWidth: 160, copyable: true },
      { key: "external_product_name_norm", title: "외부 상품명", dataIndex: "external_product_name_norm", minWidth: 170 },
      { key: "external_option_name_norm", title: "외부 옵션명", dataIndex: "external_option_name_norm", minWidth: 150 },
      { key: "product_code", title: "연결 상품코드", dataIndex: "product_code", width: 150, copyable: true },
      { key: "product_name", title: "연결 상품명", dataIndex: "product_name", minWidth: 170, render: (value) => toDisplayText(value) },
      {
        key: "status",
        title: "상태",
        dataIndex: "status",
        width: 110,
        render: (value) => <SmartStatusBadge status={String(value)} label={mappingStatusLabel(String(value))} />,
      },
      { key: "decision_type", title: "이력", dataIndex: "decision_type", width: 110, render: (value) => <SmartStatusBadge status={String(value)} label={String(value)} /> },
      { key: "confidence", title: "신뢰도", dataIndex: "confidence", width: 90, align: "right", render: (value) => `${value || 0}%` },
      { key: "used_count", title: "사용", dataIndex: "used_count", width: 80, align: "right", render: (value) => `${value || 0}` },
      { key: "last_used_at", title: "마지막 사용", dataIndex: "last_used_at", width: 150, render: formatDateTime },
      { key: "created_from_candidate_id", title: "후보 ID", dataIndex: "created_from_candidate_id", width: 100, render: (value) => toDisplayText(value) },
      { key: "conflict_reason", title: "충돌 사유", dataIndex: "conflict_reason", minWidth: 220, render: (value) => toDisplayText(value) },
      { key: "updated_at", title: "갱신시각", dataIndex: "updated_at", width: 150, render: formatDateTime },
    ],
    [],
  );

  const productMappingActions = useMemo<SmartGridRowAction<ProductChannelMapping>[]>(
    () => [
      {
        key: "approve",
        label: "승인",
        disabled: (record) => record.status === "ACTIVE" && record.conflict_status !== "CONFLICT",
        onClick: (record) => confirmMappingAction(record, "approve"),
      },
      {
        key: "disable",
        label: "비활성",
        disabled: (record) => record.status === "INACTIVE",
        onClick: (record) => confirmMappingAction(record, "disable"),
      },
      {
        key: "enable",
        label: "재활성",
        disabled: (record) => record.status === "ACTIVE",
        onClick: (record) => confirmMappingAction(record, "enable"),
      },
      {
        key: "reject",
        label: "거부",
        danger: true,
        disabled: (record) => record.status === "REJECTED",
        onClick: (record) => confirmMappingAction(record, "reject"),
      },
    ],
    [],
  );

  async function loadInitialData() {
    setLoading(true);
    setErrorMessage("");
    try {
      const candidateOptions = {
        matchStatus: candidateStatusFilter === "CREATED" ? undefined : candidateStatusFilter,
        returnExpectedCreateStatus: candidateStatusFilter === "CREATED" ? "CREATED" : undefined,
        keyword: candidateKeyword,
        sortBy: "created_at",
      };
      const [clientItems, accountResult, jobResult, rawEventResult, candidateResult, dashboardResult, mappingResult] = await Promise.all([
        listClients(),
        listChannelAccounts({ includeInactive }),
        listChannelSyncJobs(),
        listChannelRawEvents(),
        listChannelReturnCandidates(candidateOptions),
        getChannelDashboardSummary(),
        listProductChannelMappings({
          status: mappingStatusFilter === "ALL" || mappingStatusFilter === "CONFLICT" ? undefined : mappingStatusFilter,
          conflictOnly: mappingStatusFilter === "CONFLICT",
          sortBy: "updated_at",
        }),
      ]);
      setClients(clientItems);
      setAccounts(accountResult.items);
      setSyncJobs(jobResult.items);
      setRawEvents(rawEventResult.items);
      setCandidates(candidateResult.items);
      setCandidateSummary(candidateResult.summary);
      setDashboardSummary(dashboardResult);
      setProductMappings(mappingResult.items);
      setProductMappingSummary(mappingResult.summary);
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

  async function openCorrectionModal(candidate: ChannelReturnCandidate) {
    setCorrectingCandidate(candidate);
    correctionForm.resetFields();
    correctionForm.setFieldsValue({
      client_unit_id: candidate.manual_client_unit_id ?? candidate.client_unit_id ?? null,
      product_id: candidate.manual_product_id ?? candidate.product_id ?? null,
      return_tracking_no: candidate.manual_return_tracking_no ?? candidate.return_tracking_no ?? null,
      original_tracking_no: candidate.manual_original_tracking_no ?? candidate.original_tracking_no ?? null,
      qty: candidate.manual_qty ?? candidate.qty ?? null,
      review_note: candidate.manual_review_note ?? null,
    });
    try {
      const [units, products] = await Promise.all([
        listClientUnits(candidate.client_id, { includeInactive: false }),
        listProducts({ clientId: candidate.client_id, pageSize: 200 }),
      ]);
      setCorrectionUnits(units);
      setCorrectionProducts(products.items);
    } catch (error) {
      message.error(toUserMessage(error, "보정 후보 정보를 불러오지 못했습니다."));
      setCorrectionUnits([]);
      setCorrectionProducts([]);
    }
  }

  async function handleSubmitCorrection() {
    if (!correctingCandidate) {
      return;
    }
    const values = await correctionForm.validateFields();
    setActionLoadingId(correctingCandidate.channel_account_id);
    try {
      const payload: ChannelReturnCandidateCorrectionPayload = {
        client_unit_id: values.client_unit_id ?? null,
        product_id: values.product_id ?? null,
        return_tracking_no: values.return_tracking_no,
        original_tracking_no: values.original_tracking_no,
        qty: values.qty ?? null,
        review_note: values.review_note,
      };
      const result = await updateChannelReturnCandidateCorrection(correctingCandidate.id, payload);
      message.success(result.message);
      setCorrectingCandidate(null);
      await loadInitialData();
    } catch (error) {
      message.error(toUserMessage(error, "후보 보정값을 저장하지 못했습니다."));
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleClearCorrection() {
    if (!correctingCandidate) {
      return;
    }
    setActionLoadingId(correctingCandidate.channel_account_id);
    try {
      const result = await clearChannelReturnCandidateCorrection(correctingCandidate.id);
      message.success(result.message);
      setCorrectingCandidate(null);
      await loadInitialData();
    } catch (error) {
      message.error(toUserMessage(error, "후보 보정값을 초기화하지 못했습니다."));
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleCreateReturnExpected(candidate: ChannelReturnCandidate) {
    setActionLoadingId(candidate.channel_account_id);
    try {
      const result = await createReturnExpectedFromChannelCandidate(candidate.id);
      message.success(result.message);
      setNotice(result.message);
      await loadInitialData();
    } catch (error) {
      message.error(toUserMessage(error, "반품예정자료를 생성하지 못했습니다."));
    } finally {
      setActionLoadingId(null);
    }
  }

  function confirmMappingAction(mapping: ProductChannelMapping, action: "approve" | "disable" | "enable" | "reject") {
    const label = {
      approve: "승인",
      disable: "비활성",
      enable: "재활성",
      reject: "거부",
    }[action];
    Modal.confirm({
      title: `상품 매핑 ${label}`,
      content:
        action === "approve"
          ? "충돌이 남아 있으면 승인 후에도 자동확정에서 제외될 수 있습니다."
          : "이 작업은 원본 이벤트를 수정하지 않고 상품 매핑 학습 상태만 변경합니다.",
      okText: label,
      cancelText: "취소",
      okButtonProps: { danger: action === "reject" },
      onOk: () => handleProductMappingAction(mapping, action),
    });
  }

  async function handleProductMappingAction(mapping: ProductChannelMapping, action: "approve" | "disable" | "enable" | "reject") {
    setActionLoadingId(mapping.mapping_id);
    try {
      const note = `채널 연동 관리 화면에서 ${action} 처리`;
      const result =
        action === "approve"
          ? await approveProductChannelMapping(mapping.mapping_id, note)
          : action === "disable"
            ? await disableProductChannelMapping(mapping.mapping_id, note)
            : action === "enable"
              ? await enableProductChannelMapping(mapping.mapping_id, note)
              : await rejectProductChannelMapping(mapping.mapping_id, note);
      message.success(result.message);
      await loadInitialData();
    } catch (error) {
      message.error(toUserMessage(error, "상품 매핑 상태를 변경하지 못했습니다."));
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleRebuildProductMappingConflicts() {
    setActionLoadingId(-1);
    try {
      const result = await rebuildProductChannelMappingConflicts();
      message.success(`충돌 재계산 완료: 충돌 ${result.conflict_count}건, 갱신 ${result.updated_count}건`);
      await loadInitialData();
    } catch (error) {
      message.error(toUserMessage(error, "상품 매핑 충돌을 재계산하지 못했습니다."));
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleBulkCreateReturnExpected(account: ChannelAccount) {
    setActionLoadingId(account.id);
    try {
      const result = await createReturnExpectedFromChannelAccount(account.id);
      const summary = `생성 ${result.created_count}건, 중복 ${result.skipped_duplicate_count}건, 차단 ${result.blocked_count}건, 실패 ${result.failed_count}건`;
      message.success(summary);
      setNotice(summary);
      await loadInitialData();
    } catch (error) {
      message.error(toUserMessage(error, "반품예정자료 일괄 생성을 실행하지 못했습니다."));
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
  const filteredCandidates = candidates.filter((candidate) => {
    if (candidateStatusFilter === "ALL") {
      return true;
    }
    if (candidateStatusFilter === "CREATED") {
      return ["CREATED", "SKIPPED_DUPLICATE"].includes(candidate.return_expected_create_status);
    }
    return candidate.match_status === candidateStatusFilter;
  });
  const selectedCandidates = selectedAccount
    ? filteredCandidates.filter((candidate) => candidate.channel_account_id === selectedAccount.id)
    : filteredCandidates;

  return (
    <SmartPage>
      <SmartPageHeader
        title="채널 연동 관리"
        description="외부 채널 자동수집 현황, 예외 후보, 상품 매핑 학습 상태를 관리합니다."
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

      <section className="smart-summary-grid" aria-label="채널 자동수집 운영 요약">
        <SmartSummaryCard label="연동 계정" value={`${dashboardSummary.active_accounts}/${dashboardSummary.total_accounts}`} />
        <SmartSummaryCard label="오늘 수집" value={`${dashboardSummary.raw_events_today}건`} />
        <SmartSummaryCard label="READY" value={`${dashboardSummary.ready_for_intake_count}건`} />
        <SmartSummaryCard label="예외 필요" value={`${dashboardSummary.correction_required_count}건`} />
        <SmartSummaryCard label="반품예정 생성" value={`${dashboardSummary.return_expected_created_count}건`} />
        <SmartSummaryCard label="오류" value={`${dashboardSummary.error_accounts + dashboardSummary.raw_event_failed_count + dashboardSummary.return_expected_failed_count}건`} />
      </section>

      <Alert
        type="info"
        showIcon
        message="현재는 실제 네이버 API 호출 전 운영 skeleton 단계입니다."
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

      <section className="smart-summary-grid" aria-label="채널 반품 후보 상태 요약">
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
            <Segmented
              value={candidateStatusFilter}
              options={CANDIDATE_STATUS_OPTIONS}
              onChange={(value) => setCandidateStatusFilter(value as CandidateStatusFilter)}
            />
            <Input.Search
              allowClear
              style={{ width: 220 }}
              value={candidateKeyword}
              placeholder="외부 ID/상품 검색"
              onChange={(event) => setCandidateKeyword(event.target.value)}
              onSearch={() => void loadInitialData()}
            />
            <Button
              icon={<SyncOutlined />}
              disabled={!selectedAccount}
              loading={actionLoadingId === selectedAccount?.id}
              onClick={() => selectedAccount && void handleTransformAccount(selectedAccount)}
            >
              선택 계정 원본 변환
            </Button>
            <Button
              type="primary"
              disabled={!selectedAccount || readyNotCreatedCount(selectedCandidates) === 0}
              loading={actionLoadingId === selectedAccount?.id}
              onClick={() => selectedAccount && void handleBulkCreateReturnExpected(selectedAccount)}
            >
              입고 준비 일괄 생성
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

      <SmartDataSection
        title="상품 매핑 학습"
        extra={
          <Space>
            <Segmented
              value={mappingStatusFilter}
              options={[
                { value: "ALL", label: "전체" },
                { value: "ACTIVE", label: "활성" },
                { value: "CONFLICT", label: "충돌" },
                { value: "INACTIVE", label: "비활성" },
                { value: "REJECTED", label: "거부" },
              ]}
              onChange={(value) => setMappingStatusFilter(value as typeof mappingStatusFilter)}
            />
            <Button icon={<SyncOutlined />} loading={actionLoadingId === -1} onClick={() => void handleRebuildProductMappingConflicts()}>
              충돌 재계산
            </Button>
            <Typography.Text type="secondary">
              학습 {productMappingSummary.total || 0}건 / 충돌 {productMappingSummary.conflict_count || 0}건
            </Typography.Text>
          </Space>
        }
      >
        <section className="smart-summary-grid" aria-label="상품 매핑 학습 요약">
          <SmartSummaryCard label="전체 매핑" value={`${productMappingSummary.total || 0}건`} />
          <SmartSummaryCard label="활성 매핑" value={`${productMappingSummary.active_count || 0}건`} />
          <SmartSummaryCard label="충돌 매핑" value={`${productMappingSummary.conflict_count || 0}건`} />
          <SmartSummaryCard label="비활성/거부" value={`${(productMappingSummary.inactive_count || 0) + (productMappingSummary.rejected_count || 0)}건`} />
        </section>
        <Alert
          type={dashboardSummary.product_mapping_conflict_count > 0 ? "warning" : "info"}
          showIcon
          message="상품 매핑 학습 상태"
          description="충돌, 비활성, 거부 매핑은 자동확정 대상에서 제외됩니다. 상품명/옵션명 유사도만으로는 자동확정하지 않습니다."
        />
        <SmartDataGrid<ProductChannelMapping>
          rows={productMappings}
          rowKey="mapping_id"
          columns={productMappingColumns}
          loading={loading || actionLoadingId !== null}
          emptyText="학습된 상품 매핑이 없습니다."
          rowActions={productMappingActions}
          maxHeight={260}
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

      <SmartModalShell
        title="반품접수 후보 보정"
        open={Boolean(correctingCandidate)}
        onCancel={() => setCorrectingCandidate(null)}
        onOk={() => void handleSubmitCorrection()}
        confirmLoading={actionLoadingId === correctingCandidate?.channel_account_id}
        okText="보정 저장"
        cancelText="닫기"
        destroyOnHidden
      >
        <Alert
          type="warning"
          showIcon
          message="return_tracking_no가 현장 스캔 기준입니다."
          description="original_tracking_no는 보조 조회 후보이며, 원송장만으로는 READY_FOR_INTAKE로 전환되지 않습니다."
        />
        <Space>
          <Button danger disabled={!correctingCandidate || Boolean(correctingCandidate.return_expected_id)} onClick={() => void handleClearCorrection()}>
            보정 초기화
          </Button>
        </Space>
        <Form form={correctionForm} layout="vertical">
          <Form.Item name="client_unit_id" label="팀/운영단위">
            <Select allowClear options={unitOptions(correctionUnits)} placeholder="팀/운영단위 선택" />
          </Form.Item>
          <Form.Item name="product_id" label="상품">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              options={productOptions(correctionProducts)}
              placeholder="상품 선택"
            />
          </Form.Item>
          <Form.Item name="return_tracking_no" label="반품송장번호">
            <Input maxLength={100} placeholder="현장 스캔 기준 송장" />
          </Form.Item>
          <Form.Item name="original_tracking_no" label="원송장번호">
            <Input maxLength={100} placeholder="보조 조회 후보" />
          </Form.Item>
          <Form.Item name="qty" label="수량" rules={[{ type: "number", min: 1, message: "수량은 1 이상이어야 합니다." }]}>
            <InputNumber min={1} precision={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="review_note" label="검토 메모">
            <Input.TextArea maxLength={500} rows={3} placeholder="보정 사유 또는 확인 내용을 입력하세요." />
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

function productOptions(products: ProductSummary[]) {
  return products.map((product) => ({
    value: product.product_id,
    label: `${product.product_code} / ${product.product_name}`,
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

function returnExpectedCreateStatusLabel(value: string) {
  return (
    {
      NOT_CREATED: "미생성",
      CREATED: "생성됨",
      SKIPPED_DUPLICATE: "중복 연결",
      FAILED: "생성 실패",
    }[value] || value
  );
}

function correctionStatusLabel(value: string) {
  return (
    {
      NONE: "없음",
      CORRECTED: "보정됨",
      REVIEWED: "확인됨",
      REPROCESS_REQUIRED: "재처리 필요",
    }[value] || value
  );
}

function mappingStatusLabel(value: string) {
  return (
    {
      ACTIVE: "활성",
      INACTIVE: "비활성",
      CONFLICT: "충돌",
      REJECTED: "거부",
    }[value] || value
  );
}

function nextActionLabel(value?: ChannelReturnNextAction | null) {
  const labels: Record<ChannelReturnNextAction, string> = {
    ASSIGN_TEAM: "팀 배정",
    MATCH_PRODUCT: "상품 매칭",
    ENTER_RETURN_TRACKING: "반품송장 입력",
    REVIEW_CONFLICT: "충돌 확인",
    CREATE_RETURN_EXPECTED: "반품예정 생성",
    ALREADY_CREATED: "생성됨",
    BLOCKED_NO_ACTION: "차단",
  };
  return value ? labels[value] : "-";
}

function canCreateReturnExpected(candidate: ChannelReturnCandidate) {
  return candidate.safe_to_create_return_expected;
}

function readyNotCreatedCount(candidates: ChannelReturnCandidate[]) {
  return candidates.filter((candidate) => canCreateReturnExpected(candidate)).length;
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
