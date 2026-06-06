import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Button, Card, Descriptions, Input, Select, Space, Typography, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "../../api/client";
import { listClients, listClientUnits } from "../../api/master";
import { assignReturnIntakeRowUnit, listReturnUnitAssignmentPending } from "../../api/returnIntake";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid";
import type { SmartDataGridColumn } from "../../components/grid";
import type { ClientSummary, ClientUnit } from "../../types/master";
import type { ReturnUnitAssignmentPendingRow } from "../../types/returns";

export function ReturnUnitAssignmentPage() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | undefined>();
  const [keyword, setKeyword] = useState("");
  const [rows, setRows] = useState<ReturnUnitAssignmentPendingRow[]>([]);
  const [selectedRow, setSelectedRow] = useState<ReturnUnitAssignmentPendingRow | null>(null);
  const [clientUnits, setClientUnits] = useState<ClientUnit[]>([]);
  const [selectedUnitId, setSelectedUnitId] = useState<number | undefined>();
  const [loading, setLoading] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    void initialize();
  }, []);

  useEffect(() => {
    void loadUnitOptions(selectedRow?.client_id || selectedClientId);
  }, [selectedRow?.client_id, selectedClientId]);

  const columns = useMemo<SmartDataGridColumn<ReturnUnitAssignmentPendingRow>[]>(
    () => [
      { key: "client_name", title: "고객사", dataIndex: "client_name", width: 160, copyable: true },
      { key: "row_no", title: "row_no", dataIndex: "row_no", width: 90, sortable: true },
      {
        key: "team_assign_status",
        title: "팀배정상태",
        dataIndex: "team_assign_status",
        width: 130,
        render: (value) => <SmartStatusBadge status={String(value || "TEAM_ASSIGN_PENDING")} label={toTeamAssignLabel(value)} />,
      },
      { key: "return_tracking_no", title: "운송장번호", dataIndex: "return_tracking_no", width: 150, copyable: true },
      { key: "order_no", title: "주문번호", dataIndex: "order_no", width: 150, copyable: true },
      { key: "product_code", title: "상품코드", dataIndex: "product_code", width: 130, copyable: true },
      { key: "barcode", title: "바코드", dataIndex: "barcode", width: 140, copyable: true },
      { key: "product_name", title: "상품명", dataIndex: "product_name", minWidth: 180 },
      { key: "qty", title: "수량", dataIndex: "qty", width: 80, align: "right" },
      { key: "return_reason", title: "반품사유", dataIndex: "return_reason", width: 160 },
      { key: "created_at", title: "접수일시", dataIndex: "created_at", width: 150, render: (value) => formatDateTime(value) },
    ],
    [],
  );

  async function initialize() {
    setLoading(true);
    setErrorMessage("");
    try {
      const clientItems = await listClients();
      setClients(clientItems);
      await loadRows();
    } catch (error) {
      setErrorMessage(toUserMessage(error, "팀배정대기 목록을 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function loadRows() {
    setLoading(true);
    setErrorMessage("");
    try {
      const page = await listReturnUnitAssignmentPending({
        clientId: selectedClientId,
        keyword,
        pageSize: 200,
      });
      const items = page.items || [];
      setRows(items);
      setSelectedRow((current) => (current && items.some((row) => row.row_id === current.row_id) ? current : null));
    } catch (error) {
      setErrorMessage(toUserMessage(error, "팀배정대기 목록을 불러오지 못했습니다."));
    } finally {
      setLoading(false);
    }
  }

  async function loadUnitOptions(clientId?: number) {
    if (!clientId) {
      setClientUnits([]);
      setSelectedUnitId(undefined);
      return;
    }
    try {
      const units = await listClientUnits(clientId);
      setClientUnits(units.filter((unit) => unit.active_yn));
      setSelectedUnitId(undefined);
    } catch {
      setClientUnits([]);
      setSelectedUnitId(undefined);
    }
  }

  async function handleAssign() {
    if (!selectedRow || !selectedUnitId) {
      message.warning("배정할 반품 row와 운영단위/팀을 선택하세요.");
      return;
    }
    setAssigning(true);
    try {
      await assignReturnIntakeRowUnit(selectedRow.row_id, { client_unit_id: selectedUnitId });
      message.success("운영단위/팀을 배정했습니다.");
      setSelectedRow(null);
      setSelectedUnitId(undefined);
      await loadRows();
    } catch (error) {
      message.error(toUserMessage(error, "운영단위/팀을 배정하지 못했습니다."));
    } finally {
      setAssigning(false);
    }
  }

  return (
    <SmartPage>
      <SmartPageHeader title="반품 팀배정대기" description="운영단위/팀이 필요한 고객사의 미배정 반품 row를 조회하고 배정합니다." />
      <SmartErrorNotice message={errorMessage} />

      <section className="smart-toolbar" aria-label="팀배정대기 필터">
        <Select
          className="smart-control"
          allowClear
          placeholder="고객사"
          value={selectedClientId}
          options={clients.map((client) => ({ value: getClientId(client), label: `${client.client_name} (${client.client_code})` }))}
          onChange={(value) => {
            setSelectedClientId(value);
            setSelectedRow(null);
          }}
        />
        <Input
          className="smart-control"
          allowClear
          prefix={<SearchOutlined />}
          placeholder="운송장/주문번호/상품코드/바코드"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          onPressEnter={() => void loadRows()}
        />
        <Button icon={<ReloadOutlined />} onClick={() => void loadRows()} loading={loading}>
          조회
        </Button>
      </section>

      <div className="smart-split-layout">
        <SmartDataGrid<ReturnUnitAssignmentPendingRow>
          rowKey="row_id"
          rows={rows}
          columns={columns}
          loading={loading}
          emptyText="팀배정대기 반품 row가 없습니다."
          enableCopy
          preserveOriginalOrder
          originalOrderKey="row_no"
          selectedRowKeys={selectedRow ? [selectedRow.row_id] : []}
          enableMultiSelect={false}
          onRowClick={(record) => {
            setSelectedRow(record);
            setSelectedUnitId(undefined);
          }}
          maxHeight={520}
        />

        <Card className="smart-side-panel" title="배정 상세">
          {selectedRow ? (
            <Space direction="vertical" size="middle" style={{ width: "100%" }}>
              <Descriptions size="small" column={1} bordered>
                <Descriptions.Item label="고객사">{toDisplayText(selectedRow.client_name)}</Descriptions.Item>
                <Descriptions.Item label="운송장번호">
                  <Typography.Text copyable>{toDisplayText(selectedRow.return_tracking_no)}</Typography.Text>
                </Descriptions.Item>
                <Descriptions.Item label="주문번호">
                  <Typography.Text copyable>{toDisplayText(selectedRow.order_no)}</Typography.Text>
                </Descriptions.Item>
                <Descriptions.Item label="상품코드">
                  <Typography.Text copyable>{toDisplayText(selectedRow.product_code)}</Typography.Text>
                </Descriptions.Item>
                <Descriptions.Item label="상품명">{toDisplayText(selectedRow.product_name)}</Descriptions.Item>
                <Descriptions.Item label="팀배정상태">{toTeamAssignLabel(selectedRow.team_assign_status)}</Descriptions.Item>
              </Descriptions>
              <Select
                style={{ width: "100%" }}
                placeholder="배정할 운영단위/팀"
                value={selectedUnitId}
                options={clientUnits.map((unit) => ({ value: unit.unit_id, label: `${unit.unit_name} (${unit.unit_code})` }))}
                onChange={setSelectedUnitId}
              />
              <Button type="primary" block onClick={() => void handleAssign()} loading={assigning} disabled={!selectedUnitId}>
                팀 배정
              </Button>
              <Typography.Text type="secondary">팀이 배정되면 반품처리와 후속 라우팅에서 같은 client_unit_id를 유지합니다.</Typography.Text>
            </Space>
          ) : (
            <Typography.Text type="secondary">목록에서 팀배정대기 row를 선택하세요.</Typography.Text>
          )}
        </Card>
      </div>
    </SmartPage>
  );
}

function getClientId(client?: ClientSummary) {
  return Number(client?.client_id || client?.id || 0) || undefined;
}

function toTeamAssignLabel(value: unknown) {
  const status = String(value || "NOT_REQUIRED");
  const labels: Record<string, string> = {
    NOT_REQUIRED: "불필요",
    TEAM_ASSIGN_PENDING: "팀배정대기",
    ASSIGNED: "배정완료",
  };
  return labels[status] || status;
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
  return date.toISOString().replace("T", " ").slice(0, 16);
}

function toUserMessage(error: unknown, fallback: string) {
  if (error instanceof ApiClientError) {
    if (error.resultCode === "NOT_AUTHENTICATED" || error.resultCode === "INVALID_TOKEN") {
      return "로그인이 필요하거나 인증이 만료되었습니다. 다시 로그인해 주세요.";
    }
    if (error.status === 403) {
      return "반품 팀배정 권한이 없습니다.";
    }
    return error.message || fallback;
  }
  return fallback;
}
