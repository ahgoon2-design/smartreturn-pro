import { DeleteOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Descriptions, Input, Modal, Select, Space, Typography, message } from "antd";
import type { Key } from "react";
import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "../../api/client";
import { listClients } from "../../api/master";
import { confirmReturnDisposalTask, listReturnDisposalCandidates } from "../../api/returnIntake";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn } from "../../components/grid/SmartDataGrid.types";
import type { ClientSummary } from "../../types/master";
import type { ReturnDisposalCandidate, ReturnDisposalStatus } from "../../types/returns";

const DISPOSAL_STATUS_OPTIONS: Array<{ value: ReturnDisposalStatus | "ALL"; label: string }> = [
  { value: "ALL", label: "전체 폐기상태" },
  { value: "DISPOSAL_PENDING", label: "폐기 대기" },
];

export function ReturnDisposalManagementPage() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | undefined>();
  const [disposalStatusFilter, setDisposalStatusFilter] = useState<ReturnDisposalStatus | "ALL">("ALL");
  const [returnManagementNo, setReturnManagementNo] = useState("");
  const [trackingNo, setTrackingNo] = useState("");
  const [rows, setRows] = useState<ReturnDisposalCandidate[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [selectedRow, setSelectedRow] = useState<ReturnDisposalCandidate | null>(null);
  const [disposalReason, setDisposalReason] = useState("");
  const [disposalMemo, setDisposalMemo] = useState("");
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [confirmMessage, setConfirmMessage] = useState("");

  useEffect(() => {
    void initialize();
  }, []);

  const summary = useMemo(
    () => ({
      total: rows.length,
      pending: rows.filter((row) => row.disposal_status === "DISPOSAL_PENDING").length,
    }),
    [rows],
  );

  const columns = useMemo<SmartDataGridColumn<ReturnDisposalCandidate>[]>(
    () => [
      {
        key: "disposal_status",
        title: "폐기상태",
        dataIndex: "disposal_status",
        width: 130,
        fixed: "left",
        render: (value) => <SmartStatusBadge status={String(value)} label={toDisposalStatusLabel(value)} />,
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
      setErrorMessage(toUserMessage(error, "반품 폐기 정보를 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function loadCandidates() {
    setLoading(true);
    setErrorMessage("");
    try {
      const page = await listReturnDisposalCandidates({
        clientId: selectedClientId,
        disposalStatus: disposalStatusFilter === "ALL" ? undefined : disposalStatusFilter,
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
      setErrorMessage(toUserMessage(error, "반품 폐기 후보를 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  function handleSelectRow(row: ReturnDisposalCandidate) {
    setSelectedRow(row);
    setSelectedRowKeys([row.row_id]);
    hydrateForm(row);
    setConfirmMessage("");
  }

  function hydrateForm(row: ReturnDisposalCandidate) {
    setDisposalReason(row.disposal_reason || "");
    setDisposalMemo(row.disposal_memo || "");
  }

  function resetForm() {
    setDisposalReason("");
    setDisposalMemo("");
  }

  function handleConfirm() {
    if (!selectedRow) {
      message.warning("폐기 확정할 대상을 선택하세요.");
      return;
    }
    Modal.confirm({
      title: "폐기 확정",
      content: "선택한 DISPOSAL row를 폐기 확정합니다. 정상재고/current_inventory는 변경되지 않습니다.",
      okText: "폐기 확정",
      cancelText: "취소",
      okButtonProps: { danger: true },
      onOk: () => confirmSelectedRow(),
    });
  }

  async function confirmSelectedRow() {
    if (!selectedRow) {
      return;
    }
    setConfirming(true);
    setErrorMessage("");
    setConfirmMessage("");
    try {
      const result = await confirmReturnDisposalTask(selectedRow.row_id, {
        disposal_reason: disposalReason,
        disposal_memo: disposalMemo,
      });
      setConfirmMessage(result.message || "폐기 확정 완료");
      message.success("폐기 확정 완료");
      setRows((current) => current.filter((row) => row.row_id !== result.row_id));
      setSelectedRow(null);
      setSelectedRowKeys([]);
      resetForm();
    } catch (error) {
      setErrorMessage(toUserMessage(error, "반품 폐기를 확정하지 못했습니다."));
    } finally {
      setConfirming(false);
    }
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="반품 폐기관리"
        description="DISPOSAL 판정된 반품을 폐기 확정합니다. 폐기 확정은 정상재고를 변경하지 않습니다."
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => void loadCandidates()} loading={loading}>
              새로고침
            </Button>
            <Button
              danger
              type="primary"
              icon={<DeleteOutlined />}
              onClick={handleConfirm}
              loading={confirming}
              disabled={!selectedRow}
            >
              폐기 확정
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
          value={disposalStatusFilter}
          onChange={setDisposalStatusFilter}
          options={DISPOSAL_STATUS_OPTIONS}
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
      {confirmMessage ? <Alert type="success" showIcon message={confirmMessage} style={{ marginBottom: 12 }} /> : null}

      <Space wrap style={{ marginBottom: 12 }}>
        <Typography.Text strong>폐기 후보 {summary.total}건</Typography.Text>
        <Typography.Text>폐기 대기 {summary.pending}건</Typography.Text>
        <Typography.Text type="secondary">사진은 선택사항이며, 미첨부로 폐기 확정을 막지 않습니다.</Typography.Text>
      </Space>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 360px", gap: 16, alignItems: "start" }}>
        <SmartDataGrid
          rows={rows}
          columns={columns}
          rowKey="row_id"
          loading={loading}
          emptyText="폐기 후보가 없습니다"
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
          <Typography.Title level={5}>폐기 상세</Typography.Title>
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
              <Input.TextArea
                value={disposalReason}
                onChange={(event) => setDisposalReason(event.target.value)}
                rows={3}
                placeholder="폐기 사유"
                maxLength={500}
                showCount
              />
              <Input.TextArea
                value={disposalMemo}
                onChange={(event) => setDisposalMemo(event.target.value)}
                rows={4}
                placeholder="폐기 메모"
                maxLength={1000}
                showCount
              />
              <Alert
                type="warning"
                showIcon
                message="폐기 확정 시 정상재고는 변경되지 않습니다. 사진은 선택사항입니다."
              />
              <Button danger type="primary" icon={<DeleteOutlined />} onClick={handleConfirm} loading={confirming} block>
                폐기 확정
              </Button>
            </Space>
          ) : (
            <Alert type="info" showIcon message="폐기 후보를 선택하세요." />
          )}
        </section>
      </div>
    </SmartPage>
  );
}

function getClientId(client: ClientSummary): number {
  return Number(client.client_id ?? client.id);
}

function toDisposalStatusLabel(value: unknown): string {
  switch (String(value || "")) {
    case "DISPOSAL_CONFIRMED":
      return "폐기 확정";
    case "DISPOSAL_PENDING":
      return "폐기 대기";
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
