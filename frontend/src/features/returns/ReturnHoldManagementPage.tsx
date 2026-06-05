import { ReloadOutlined, SaveOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Descriptions, Input, Select, Space, Typography, message } from "antd";
import type { Key } from "react";
import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "../../api/client";
import { listClients } from "../../api/master";
import { listReturnHoldCandidates, updateReturnHoldTask } from "../../api/returnIntake";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn } from "../../components/grid/SmartDataGrid.types";
import type { ClientSummary } from "../../types/master";
import type { ReturnHoldCandidate, ReturnHoldStatus } from "../../types/returns";

const HOLD_STATUS_OPTIONS: Array<{ value: ReturnHoldStatus | "ALL"; label: string }> = [
  { value: "ALL", label: "전체 보류상태" },
  { value: "HOLD_PENDING", label: "보류중" },
  { value: "CUSTOMER_CHECKING", label: "고객사 확인중" },
  { value: "READY_TO_REJUDGE", label: "재판정 준비" },
  { value: "RESOLVED", label: "해결됨" },
];

export function ReturnHoldManagementPage() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | undefined>();
  const [holdStatusFilter, setHoldStatusFilter] = useState<ReturnHoldStatus | "ALL">("ALL");
  const [returnManagementNo, setReturnManagementNo] = useState("");
  const [trackingNo, setTrackingNo] = useState("");
  const [rows, setRows] = useState<ReturnHoldCandidate[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [selectedRow, setSelectedRow] = useState<ReturnHoldCandidate | null>(null);
  const [formHoldStatus, setFormHoldStatus] = useState<ReturnHoldStatus>("HOLD_PENDING");
  const [formHoldReason, setFormHoldReason] = useState("");
  const [formHoldResponseMemo, setFormHoldResponseMemo] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [saveMessage, setSaveMessage] = useState("");

  useEffect(() => {
    void initialize();
  }, []);

  const summary = useMemo(
    () => ({
      total: rows.length,
      checking: rows.filter((row) => row.hold_status === "CUSTOMER_CHECKING").length,
      readyToRejudge: rows.filter((row) => row.hold_status === "READY_TO_REJUDGE").length,
    }),
    [rows],
  );

  const columns = useMemo<SmartDataGridColumn<ReturnHoldCandidate>[]>(
    () => [
      {
        key: "hold_status",
        title: "보류상태",
        dataIndex: "hold_status",
        width: 140,
        fixed: "left",
        render: (value) => <SmartStatusBadge status={String(value)} label={toHoldStatusLabel(value)} />,
      },
      { key: "client_name", title: "고객사", dataIndex: "client_name", width: 160, copyable: true },
      {
        key: "return_management_no",
        title: "반품관리번호",
        dataIndex: "return_management_no",
        width: 180,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      {
        key: "return_label_no",
        title: "라벨번호",
        dataIndex: "return_label_no",
        width: 180,
        copyable: true,
        render: (value) => toDisplayText(value),
      },
      { key: "return_tracking_no", title: "운송장번호", dataIndex: "return_tracking_no", width: 150, copyable: true },
      { key: "order_no", title: "주문번호", dataIndex: "order_no", width: 150, copyable: true },
      { key: "product_code", title: "상품코드", dataIndex: "product_code", width: 130, copyable: true },
      { key: "barcode", title: "바코드", dataIndex: "barcode", width: 140, copyable: true },
      { key: "product_name", title: "상품명", dataIndex: "product_name", width: 190, render: (value) => toDisplayText(value) },
      { key: "qty", title: "수량", dataIndex: "qty", width: 80, align: "right" },
      { key: "return_reason", title: "반품사유", dataIndex: "return_reason", width: 180, render: (value) => toDisplayText(value) },
      { key: "judgement_memo", title: "판정메모", dataIndex: "judgement_memo", width: 220, render: (value) => toDisplayText(value) },
      { key: "judged_at", title: "판정일시", dataIndex: "judged_at", width: 150, render: (value) => formatDateText(value) },
    ],
    [],
  );

  async function initialize() {
    setLoading(true);
    setErrorMessage("");
    try {
      const clientItems = await listClients();
      setClients(clientItems);
      await loadCandidates();
    } catch (error) {
      setErrorMessage(toUserMessage(error, "반품 보류 정보를 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function loadCandidates() {
    setLoading(true);
    setErrorMessage("");
    try {
      const page = await listReturnHoldCandidates({
        clientId: selectedClientId,
        holdStatus: holdStatusFilter === "ALL" ? undefined : holdStatusFilter,
        returnManagementNo: returnManagementNo.trim() || undefined,
        trackingNo: trackingNo.trim() || undefined,
        pageSize: 300,
      });
      const items = page.items || [];
      setRows(items);
      setSelectedRow((current) => {
        if (!current) {
          return null;
        }
        const next = items.find((row) => row.row_id === current.row_id) || null;
        if (next) {
          setSelectedRowKeys([next.row_id]);
          hydrateForm(next);
        } else {
          setSelectedRowKeys([]);
          resetForm();
        }
        return next;
      });
    } catch (error) {
      setErrorMessage(toUserMessage(error, "반품 보류 후보를 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  function handleSelectRow(row: ReturnHoldCandidate) {
    setSelectedRow(row);
    setSelectedRowKeys([row.row_id]);
    hydrateForm(row);
    setSaveMessage("");
  }

  function hydrateForm(row: ReturnHoldCandidate) {
    setFormHoldStatus(normalizeHoldStatus(row.hold_status));
    setFormHoldReason(row.hold_reason || "");
    setFormHoldResponseMemo(row.hold_response_memo || "");
  }

  function resetForm() {
    setFormHoldStatus("HOLD_PENDING");
    setFormHoldReason("");
    setFormHoldResponseMemo("");
  }

  async function handleSave() {
    if (!selectedRow) {
      message.warning("저장할 보류 대상을 선택하세요.");
      return;
    }
    setSaving(true);
    setErrorMessage("");
    setSaveMessage("");
    try {
      const updated = await updateReturnHoldTask(selectedRow.row_id, {
        hold_status: formHoldStatus,
        hold_reason: formHoldReason,
        hold_response_memo: formHoldResponseMemo,
      });
      setSaveMessage(updated.message || "반품 보류 정보를 저장했습니다.");
      message.success("반품 보류 정보를 저장했습니다.");
      if (updated.hold_status === "RESOLVED") {
        setRows((current) => current.filter((row) => row.row_id !== updated.row_id));
        setSelectedRow(null);
        setSelectedRowKeys([]);
        resetForm();
      } else {
        setRows((current) => current.map((row) => (row.row_id === updated.row_id ? updated : row)));
        setSelectedRow(updated);
        setSelectedRowKeys([updated.row_id]);
        hydrateForm(updated);
      }
    } catch (error) {
      setErrorMessage(toUserMessage(error, "반품 보류 정보를 저장하지 못했습니다."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="반품 보류관리"
        description="HOLD 판정된 반품의 고객사 확인 메모와 재판정 준비 상태를 관리합니다."
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => void loadCandidates()} loading={loading}>
              새로고침
            </Button>
            <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving} disabled={!selectedRow}>
              저장
            </Button>
          </Space>
        }
      />

      <Space className="smart-toolbar" wrap>
        <Select
          allowClear
          placeholder="고객사 전체"
          style={{ width: 220 }}
          value={selectedClientId}
          onChange={setSelectedClientId}
          options={clients.map((client) => ({
            value: getClientId(client),
            label: client.client_name,
          }))}
        />
        <Select
          style={{ width: 180 }}
          value={holdStatusFilter}
          onChange={setHoldStatusFilter}
          options={HOLD_STATUS_OPTIONS}
        />
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="반품관리번호 또는 라벨번호"
          value={returnManagementNo}
          onChange={(event) => setReturnManagementNo(event.target.value)}
          onPressEnter={() => void loadCandidates()}
          style={{ width: 260 }}
        />
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="운송장번호 또는 주문번호"
          value={trackingNo}
          onChange={(event) => setTrackingNo(event.target.value)}
          onPressEnter={() => void loadCandidates()}
          style={{ width: 240 }}
        />
        <Button icon={<SearchOutlined />} onClick={() => void loadCandidates()} loading={loading}>
          후보 조회
        </Button>
      </Space>

      {errorMessage ? <SmartErrorNotice message={errorMessage} /> : null}
      {saveMessage ? <Alert type="success" showIcon message={saveMessage} style={{ marginBottom: 12 }} /> : null}

      <Space wrap style={{ marginBottom: 12 }}>
        <Typography.Text strong>보류 후보 {summary.total}건</Typography.Text>
        <Typography.Text>고객사 확인중 {summary.checking}건</Typography.Text>
        <Typography.Text>재판정 준비 {summary.readyToRejudge}건</Typography.Text>
      </Space>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 360px", gap: 16, alignItems: "start" }}>
        <SmartDataGrid
          rows={rows}
          columns={columns}
          rowKey="row_id"
          loading={loading}
          emptyText="보류 후보가 없습니다"
          selectedRowKeys={selectedRowKeys}
          onRowClick={handleSelectRow}
          onSelectionChange={(keys, selectedRows) => {
            const row = selectedRows[0];
            if (row) {
              handleSelectRow(row);
            } else {
              setSelectedRow(null);
              setSelectedRowKeys(keys);
              resetForm();
            }
          }}
          enableMultiSelect={false}
          enableCopy
          preserveOriginalOrder
          originalOrderKey="row_no"
          maxHeight={430}
          getRowClassName={(row) => (row.row_id === selectedRow?.row_id ? "smart-grid-row-selected" : "")}
        />

        <section className="smart-panel">
          <Typography.Title level={5}>보류 상세</Typography.Title>
          {selectedRow ? (
            <Space direction="vertical" size={12} style={{ width: "100%" }}>
              <Descriptions size="small" column={1} bordered>
                <Descriptions.Item label="반품관리번호">{toDisplayText(selectedRow.return_management_no)}</Descriptions.Item>
                <Descriptions.Item label="라벨번호">{toDisplayText(selectedRow.return_label_no)}</Descriptions.Item>
                <Descriptions.Item label="운송장번호">{toDisplayText(selectedRow.return_tracking_no)}</Descriptions.Item>
                <Descriptions.Item label="주문번호">{toDisplayText(selectedRow.order_no)}</Descriptions.Item>
                <Descriptions.Item label="상품">{toDisplayText(selectedRow.product_name)}</Descriptions.Item>
                <Descriptions.Item label="판정메모">{toDisplayText(selectedRow.judgement_memo)}</Descriptions.Item>
              </Descriptions>
              <Select
                value={formHoldStatus}
                onChange={setFormHoldStatus}
                options={HOLD_STATUS_OPTIONS.filter((option) => option.value !== "ALL")}
                style={{ width: "100%" }}
              />
              <Input.TextArea
                value={formHoldReason}
                onChange={(event) => setFormHoldReason(event.target.value)}
                rows={3}
                placeholder="보류 사유"
                maxLength={500}
                showCount
              />
              <Input.TextArea
                value={formHoldResponseMemo}
                onChange={(event) => setFormHoldResponseMemo(event.target.value)}
                rows={4}
                placeholder="고객사 회신 메모"
                maxLength={1000}
                showCount
              />
              <Alert
                type="info"
                showIcon
                message="사진은 선택사항입니다. 재판정은 다음 단계에서 구현합니다."
              />
              <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving} block>
                보류 정보 저장
              </Button>
            </Space>
          ) : (
            <Alert type="info" showIcon message="보류 후보를 선택하세요." />
          )}
        </section>
      </div>
    </SmartPage>
  );
}

function getClientId(client: ClientSummary): number {
  return Number(client.client_id ?? client.id);
}

function normalizeHoldStatus(value: unknown): ReturnHoldStatus {
  const status = String(value || "HOLD_PENDING").toUpperCase();
  if (status === "CUSTOMER_CHECKING" || status === "READY_TO_REJUDGE" || status === "RESOLVED") {
    return status;
  }
  return "HOLD_PENDING";
}

function toHoldStatusLabel(value: unknown): string {
  switch (String(value || "")) {
    case "CUSTOMER_CHECKING":
      return "고객사 확인중";
    case "READY_TO_REJUDGE":
      return "재판정 준비";
    case "RESOLVED":
      return "해결됨";
    case "HOLD_PENDING":
      return "보류중";
    default:
      return "-";
  }
}

function toDisplayText(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function formatDateText(value: unknown): string {
  if (!value) {
    return "-";
  }
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString("ko-KR", { hour12: false });
}

function toUserMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401 || error.status === 403) {
      return "권한이 없거나 로그인이 만료되었습니다.";
    }
    return error.message || fallback;
  }
  return fallback;
}
