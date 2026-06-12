import { ReloadOutlined, SearchOutlined, StopOutlined, UndoOutlined } from "@ant-design/icons";
import { Alert, Button, Input, Select, Space, Tabs, Tag, Tooltip, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "../../api/client";
import {
  activateImportMappingDecision,
  activateImportMappingProfile,
  deactivateImportMappingDecision,
  deactivateImportMappingProfile,
  listImportMappingDecisions,
  listImportMappingProfiles,
  listImportSourceTypes,
} from "../../api/importJobs";
import { listClients } from "../../api/master";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartModalShell } from "../../components/common/SmartModalShell";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn } from "../../components/grid/SmartDataGrid.types";
import type { ImportMappingDecision, ImportMappingProfile } from "../../types/import";
import type { ClientSummary } from "../../types/master";

const MIN_REASON_LENGTH = 5;

const ACTIVE_FILTER_OPTIONS = [
  { value: "ALL", label: "전체 상태" },
  { value: "ACTIVE", label: "활성만" },
  { value: "INACTIVE", label: "비활성만" },
];

const DECISION_TYPE_LABELS: Record<string, string> = {
  CONFIRMED: "확정",
  CORRECTED: "수정 확정",
  REJECTED: "거절(차단 학습)",
  AUTO_APPLIED_CONFIRMED: "자동적용 확정",
};

interface DeactivateTarget {
  kind: "profile" | "decision";
  id: number;
  label: string;
  isGlobal: boolean;
}

/**
 * 내부 운영자용 매핑 학습 관리 화면.
 * 잘못 학습된 mapping profile / decision을 soft 비활성화(active_yn=false)하거나 되돌린다.
 * 물리 삭제와 일괄 비활성화는 정책상 제공하지 않으며, REJECTED decision은 backend와 동일하게 끌 수 없다.
 */
export function ImportMappingLearningPage() {
  const [activeTab, setActiveTab] = useState<"profiles" | "decisions">("profiles");
  const [profiles, setProfiles] = useState<ImportMappingProfile[]>([]);
  const [decisions, setDecisions] = useState<ImportMappingDecision[]>([]);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [importTypes, setImportTypes] = useState<string[]>([]);
  const [sourceTypes, setSourceTypes] = useState<string[]>([]);

  const [filterImportType, setFilterImportType] = useState<string>("ALL");
  const [filterSourceType, setFilterSourceType] = useState<string>("ALL");
  const [filterClientId, setFilterClientId] = useState<number | undefined>();
  const [filterActive, setFilterActive] = useState<string>("ALL");
  const [filterKeyword, setFilterKeyword] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [notice, setNotice] = useState("");

  const [deactivateTarget, setDeactivateTarget] = useState<DeactivateTarget | null>(null);
  const [deactivateReason, setDeactivateReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    void initialize();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function initialize() {
    try {
      const sourceTypesResponse = await listImportSourceTypes();
      setImportTypes(sourceTypesResponse.import_types || []);
      setSourceTypes(sourceTypesResponse.source_types || []);
    } catch {
      setImportTypes([]);
      setSourceTypes([]);
    }
    try {
      const clientItems = await listClients();
      setClients(clientItems);
    } catch {
      setClients([]);
    }
    await loadData();
  }

  async function loadData() {
    setLoading(true);
    setErrorMessage("");
    try {
      const filters = {
        clientId: filterClientId,
        importType: filterImportType === "ALL" ? undefined : filterImportType,
        sourceType: filterSourceType === "ALL" ? undefined : filterSourceType,
        includeInactive: true,
      };
      const [profilesResponse, decisionsResponse] = await Promise.all([
        listImportMappingProfiles(filters),
        listImportMappingDecisions(filters),
      ]);
      setProfiles(profilesResponse.items || []);
      setDecisions(decisionsResponse.items || []);
    } catch (error) {
      setProfiles([]);
      setDecisions([]);
      setErrorMessage(toLearningErrorMessage(error, "매핑 학습 목록을 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  function matchesCommonFilters(item: {
    active_yn: boolean;
    created_at: string;
    searchText: string;
  }) {
    if (filterActive === "ACTIVE" && !item.active_yn) {
      return false;
    }
    if (filterActive === "INACTIVE" && item.active_yn) {
      return false;
    }
    const keyword = filterKeyword.trim().toLowerCase();
    if (keyword && !item.searchText.toLowerCase().includes(keyword)) {
      return false;
    }
    const createdDate = String(item.created_at || "").slice(0, 10);
    if (filterDateFrom && createdDate && createdDate < filterDateFrom) {
      return false;
    }
    if (filterDateTo && createdDate && createdDate > filterDateTo) {
      return false;
    }
    return true;
  }

  const filteredProfiles = useMemo(
    () =>
      profiles.filter((profile) =>
        matchesCommonFilters({
          active_yn: profile.active_yn,
          created_at: profile.created_at,
          searchText: [profile.profile_name, profile.header_signature, Object.entries(profile.mapping_json || {}).flat().join(" ")].join(" "),
        }),
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [profiles, filterActive, filterKeyword, filterDateFrom, filterDateTo],
  );

  const filteredDecisions = useMemo(
    () =>
      decisions.filter((decision) =>
        matchesCommonFilters({
          active_yn: decision.active_yn,
          created_at: decision.created_at,
          searchText: [decision.original_header, decision.normalized_header, decision.canonical_field || ""].join(" "),
        }),
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [decisions, filterActive, filterKeyword, filterDateFrom, filterDateTo],
  );

  function clientNameOf(clientId: number | null | undefined) {
    if (clientId === null || clientId === undefined) {
      return null;
    }
    const found = clients.find((client) => (client.client_id ?? client.id) === clientId);
    return found?.client_name || `고객사 #${clientId}`;
  }

  function renderScopeTag(clientId: number | null | undefined) {
    const name = clientNameOf(clientId);
    return name ? <Tag color="geekblue">{name}</Tag> : <Tag color="orange">전역(모든 고객사)</Tag>;
  }

  function renderActiveBadge(active: boolean) {
    return active ? <SmartStatusBadge status="VALID" label="활성" /> : <SmartStatusBadge status="INVALID" label="비활성" />;
  }

  async function runAction(action: () => Promise<unknown>, successMessage: string) {
    setActionLoading(true);
    setErrorMessage("");
    setNotice("");
    try {
      await action();
      setNotice(successMessage);
      setDeactivateTarget(null);
      setDeactivateReason("");
      await loadData();
    } catch (error) {
      setErrorMessage(toLearningErrorMessage(error, "처리하지 못했습니다."));
    } finally {
      setActionLoading(false);
    }
  }

  function handleDeactivateSubmit() {
    if (!deactivateTarget || deactivateReason.trim().length < MIN_REASON_LENGTH) {
      return;
    }
    const reason = deactivateReason.trim();
    if (deactivateTarget.kind === "profile") {
      void runAction(
        () => deactivateImportMappingProfile(deactivateTarget.id, reason),
        "매핑 프로필을 비활성화했습니다. 다음 업로드부터 자동매핑 추천에 사용되지 않습니다.",
      );
    } else {
      void runAction(
        () => deactivateImportMappingDecision(deactivateTarget.id, reason),
        "결정 이력을 비활성화했습니다. 다음 업로드부터 추천 계산에 사용되지 않습니다.",
      );
    }
  }

  const profileColumns = useMemo<SmartDataGridColumn<ImportMappingProfile>[]>(
    () => [
      { key: "profile_id", title: "ID", dataIndex: "profile_id", width: 70 },
      { key: "scope", title: "범위", width: 150, render: (_value, row) => renderScopeTag(row.client_id) },
      { key: "import_type", title: "자료유형", dataIndex: "import_type", width: 150 },
      { key: "source_type", title: "소스", dataIndex: "source_type", width: 100 },
      { key: "profile_name", title: "프로필명", dataIndex: "profile_name", width: 170, copyable: true },
      {
        key: "header_signature",
        title: "헤더 구성",
        dataIndex: "header_signature",
        width: 230,
        render: (value) => summarizeSignature(value),
      },
      { key: "active_yn", title: "상태", width: 90, render: (_value, row) => renderActiveBadge(row.active_yn) },
      { key: "last_used_at", title: "마지막 사용", width: 150, render: (_value, row) => formatDateText(row.last_used_at) },
      { key: "deactivated_at", title: "비활성화 일시", width: 150, render: (_value, row) => formatDateText(row.deactivated_at) },
      {
        key: "deactivate_reason",
        title: "비활성화 사유",
        dataIndex: "deactivate_reason",
        width: 190,
        render: (value) => (value ? String(value) : "-"),
      },
      {
        key: "actions",
        title: "액션",
        width: 110,
        exportable: false,
        render: (_value, row) =>
          row.active_yn ? (
            <Button
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() =>
                setDeactivateTarget({
                  kind: "profile",
                  id: row.profile_id,
                  label: `프로필 #${row.profile_id} · ${row.profile_name}`,
                  isGlobal: row.client_id === null || row.client_id === undefined,
                })
              }
            >
              비활성화
            </Button>
          ) : (
            <Button
              size="small"
              icon={<UndoOutlined />}
              loading={actionLoading}
              onClick={() =>
                void runAction(
                  () => activateImportMappingProfile(row.profile_id),
                  "매핑 프로필을 다시 활성화했습니다. 다음 업로드부터 추천 후보로 사용됩니다.",
                )
              }
            >
              재활성화
            </Button>
          ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [actionLoading, clients],
  );

  const decisionColumns = useMemo<SmartDataGridColumn<ImportMappingDecision>[]>(
    () => [
      { key: "decision_id", title: "ID", dataIndex: "decision_id", width: 70 },
      { key: "scope", title: "범위", width: 150, render: (_value, row) => renderScopeTag(row.client_id) },
      { key: "import_type", title: "자료유형", dataIndex: "import_type", width: 140 },
      { key: "source_type", title: "소스", dataIndex: "source_type", width: 95 },
      { key: "original_header", title: "원본 헤더", dataIndex: "original_header", width: 140, copyable: true },
      { key: "canonical_field", title: "매핑 필드", dataIndex: "canonical_field", width: 150, render: (value) => (value ? String(value) : "-") },
      {
        key: "decision_type",
        title: "결정 유형",
        dataIndex: "decision_type",
        width: 130,
        render: (value) => {
          const code = String(value || "");
          return code === "REJECTED" ? (
            <Tag color="red">{DECISION_TYPE_LABELS[code]}</Tag>
          ) : (
            DECISION_TYPE_LABELS[code] || code
          );
        },
      },
      {
        key: "confidence",
        title: "신뢰도(전→후)",
        width: 120,
        render: (_value, row) => `${formatConfidence(row.confidence_before)} → ${formatConfidence(row.confidence_after)}`,
      },
      { key: "active_yn", title: "상태", width: 90, render: (_value, row) => renderActiveBadge(row.active_yn) },
      { key: "confirmed_at", title: "확정 일시", width: 150, render: (_value, row) => formatDateText(row.confirmed_at) },
      { key: "deactivated_at", title: "비활성화 일시", width: 150, render: (_value, row) => formatDateText(row.deactivated_at) },
      {
        key: "deactivate_reason",
        title: "비활성화 사유",
        dataIndex: "deactivate_reason",
        width: 180,
        render: (value) => (value ? String(value) : "-"),
      },
      {
        key: "actions",
        title: "액션",
        width: 110,
        exportable: false,
        render: (_value, row) => {
          if (row.decision_type === "REJECTED") {
            return (
              <Tooltip title="거절 이력은 잘못된 매핑을 차단하는 학습입니다. 끄면 차단되던 매핑이 다시 추천될 수 있어 비활성화할 수 없습니다.">
                <Typography.Text type="secondary" style={{ fontSize: 12, cursor: "help" }}>
                  끌 수 없음
                </Typography.Text>
              </Tooltip>
            );
          }
          return row.active_yn ? (
            <Button
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() =>
                setDeactivateTarget({
                  kind: "decision",
                  id: row.decision_id,
                  label: `결정 #${row.decision_id} · ${row.original_header} → ${row.canonical_field || "-"}`,
                  isGlobal: row.client_id === null || row.client_id === undefined,
                })
              }
            >
              비활성화
            </Button>
          ) : (
            <Button
              size="small"
              icon={<UndoOutlined />}
              loading={actionLoading}
              onClick={() =>
                void runAction(
                  () => activateImportMappingDecision(row.decision_id),
                  "결정 이력을 다시 활성화했습니다. 다음 업로드부터 추천 후보로 사용됩니다.",
                )
              }
            >
              재활성화
            </Button>
          );
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [actionLoading, clients],
  );

  const reasonTooShort = deactivateReason.trim().length < MIN_REASON_LENGTH;

  return (
    <SmartPage>
      <SmartPageHeader
        title="매핑 학습 관리"
        description="잘못 학습된 자동매핑을 비활성화하거나 다시 활성화합니다."
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => void loadData()} loading={loading}>
            새로고침
          </Button>
        }
      />

      <Alert
        type="info"
        showIcon
        message="비활성화는 다음 업로드부터 적용되며 이미 확정된 자료는 바뀌지 않습니다. 삭제는 없고 언제든 재활성화로 되돌릴 수 있습니다."
      />

      <Space className="smart-toolbar" wrap>
        <Select
          style={{ width: 190 }}
          value={filterImportType}
          onChange={setFilterImportType}
          options={[{ value: "ALL", label: "전체 자료유형" }, ...importTypes.map((value) => ({ value, label: value }))]}
        />
        <Select
          style={{ width: 150 }}
          value={filterSourceType}
          onChange={setFilterSourceType}
          options={[{ value: "ALL", label: "전체 소스" }, ...sourceTypes.map((value) => ({ value, label: value }))]}
        />
        <Select
          allowClear
          placeholder="고객사 전체(전역 포함)"
          style={{ width: 200 }}
          value={filterClientId}
          onChange={setFilterClientId}
          options={clients.map((client) => ({
            value: client.client_id ?? client.id ?? 0,
            label: client.client_name,
          }))}
        />
        <Select style={{ width: 120 }} value={filterActive} onChange={setFilterActive} options={ACTIVE_FILTER_OPTIONS} />
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="헤더명/필드/프로필명 검색"
          value={filterKeyword}
          onChange={(event) => setFilterKeyword(event.target.value)}
          style={{ width: 220 }}
        />
        <Input type="date" value={filterDateFrom} onChange={(event) => setFilterDateFrom(event.target.value)} style={{ width: 150 }} aria-label="조회 시작일" />
        <Typography.Text type="secondary">~</Typography.Text>
        <Input type="date" value={filterDateTo} onChange={(event) => setFilterDateTo(event.target.value)} style={{ width: 150 }} aria-label="조회 종료일" />
        <Button type="primary" icon={<SearchOutlined />} onClick={() => void loadData()} loading={loading}>
          조회
        </Button>
      </Space>

      {errorMessage ? <SmartErrorNotice message={errorMessage} /> : null}
      {notice ? <Alert type="success" showIcon message={notice} /> : null}

      <Tabs
        activeKey={activeTab}
        onChange={(key) => setActiveTab(key as "profiles" | "decisions")}
        items={[
          {
            key: "profiles",
            label: `매핑 프로필 (${filteredProfiles.length})`,
            children: (
              <SmartDataGrid<ImportMappingProfile>
                rows={filteredProfiles}
                columns={profileColumns}
                rowKey="profile_id"
                loading={loading}
                emptyText="조회된 매핑 프로필이 없습니다."
                enableCopy
                exportFileName="매핑프로필"
                maxHeight={352}
              />
            ),
          },
          {
            key: "decisions",
            label: `결정 이력 (${filteredDecisions.length})`,
            children: (
              <Space direction="vertical" size={8} className="smart-full-width">
                <Alert
                  type="warning"
                  showIcon
                  message="REJECTED 이력은 잘못된 매핑을 차단하는 학습입니다. 비활성화하면 차단되던 매핑이 다시 추천될 수 있어 1차 정책에서는 끌 수 없습니다."
                />
                <SmartDataGrid<ImportMappingDecision>
                  rows={filteredDecisions}
                  columns={decisionColumns}
                  rowKey="decision_id"
                  loading={loading}
                  emptyText="조회된 결정 이력이 없습니다."
                  enableCopy
                  exportFileName="매핑결정이력"
                  maxHeight={300}
                />
              </Space>
            ),
          },
        ]}
      />

      <SmartModalShell
        title="매핑 학습 비활성화"
        open={Boolean(deactivateTarget)}
        width={560}
        onCancel={() => {
          setDeactivateTarget(null);
          setDeactivateReason("");
        }}
        footer={[
          <Button
            key="cancel"
            onClick={() => {
              setDeactivateTarget(null);
              setDeactivateReason("");
            }}
          >
            취소
          </Button>,
          <Button key="submit" type="primary" danger loading={actionLoading} disabled={reasonTooShort} onClick={handleDeactivateSubmit}>
            비활성화
          </Button>,
        ]}
      >
        <Space direction="vertical" size={10} className="smart-full-width">
          <Typography.Text strong>{deactivateTarget?.label}</Typography.Text>
          {deactivateTarget?.isGlobal ? (
            <Alert
              type="error"
              showIcon
              message="전역 학습입니다. 모든 고객사의 자동매핑에 영향을 줍니다."
              description="특정 고객사 문제라면 해당 고객사 학습만 비활성화하는 것이 안전합니다."
            />
          ) : (
            <Alert
              type="warning"
              showIcon
              message="이 학습을 끄면 다음 업로드부터 자동매핑 추천에 사용되지 않습니다."
              description="이미 확정된 자료는 변경되지 않으며, 재활성화로 되돌릴 수 있습니다."
            />
          )}
          <div>
            <Typography.Text>비활성화 사유 (필수, {MIN_REASON_LENGTH}자 이상)</Typography.Text>
            <Input.TextArea
              rows={3}
              value={deactivateReason}
              onChange={(event) => setDeactivateReason(event.target.value)}
              placeholder="예: 운송장번호 헤더가 주문번호로 잘못 학습되어 비활성화"
              maxLength={300}
              showCount
            />
            {reasonTooShort && deactivateReason.length > 0 ? (
              <Typography.Text type="danger">사유를 {MIN_REASON_LENGTH}자 이상 입력해 주세요.</Typography.Text>
            ) : null}
          </div>
        </Space>
      </SmartModalShell>
    </SmartPage>
  );
}

function summarizeSignature(value: unknown) {
  const text = String(value || "");
  if (!text) {
    return "-";
  }
  const headers = text.split("|").filter(Boolean);
  if (headers.length <= 4) {
    return headers.join(", ");
  }
  return `${headers.slice(0, 4).join(", ")} 외 ${headers.length - 4}개`;
}

function formatConfidence(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${Math.round(value * 100)}%`;
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

function toLearningErrorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "로그인이 필요하거나 인증이 만료되었습니다.";
    }
    if (error.resultCode === "CLIENT_SCOPE_DENIED" || error.resultCode?.includes("SCOPE")) {
      return "허용된 고객사 범위 밖의 학습 데이터입니다.";
    }
    if (error.status === 403) {
      return "현재 계정 권한으로 매핑 학습 관리를 사용할 수 없습니다.";
    }
    if (error.resultCode === "IMPORT_MAPPING_REJECTED_DECISION_CANNOT_BE_DEACTIVATED") {
      return "REJECTED 이력은 차단 학습이므로 비활성화할 수 없습니다.";
    }
    return error.message || fallback;
  }
  return fallback;
}
