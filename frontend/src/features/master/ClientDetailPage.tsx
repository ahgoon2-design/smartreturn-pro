import { ArrowLeftOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, Card, Descriptions, Result, Skeleton, Space, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiClientError } from "../../api/client";
import { getClient } from "../../api/master";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { ROUTE_PATHS } from "../../routes/routePaths";
import type { ClientDetail } from "../../types/master";
import { ClientReturnWarehouseRoutesSection } from "./ClientReturnWarehouseRoutesSection";
import { ClientUnitsSection } from "./ClientUnitsSection";
import { ClientWarehouseSettingsSection } from "./ClientWarehouseSettingsSection";

export function ClientDetailPage() {
  const navigate = useNavigate();
  const { clientId } = useParams();
  const parsedClientId = useMemo(() => Number(clientId), [clientId]);
  const [client, setClient] = useState<ClientDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!Number.isFinite(parsedClientId) || parsedClientId <= 0) {
      setNotFound(true);
      setClient(null);
      return;
    }
    void loadClient(parsedClientId);
  }, [parsedClientId]);

  async function loadClient(nextClientId = parsedClientId) {
    if (!Number.isFinite(nextClientId) || nextClientId <= 0) {
      setNotFound(true);
      return;
    }
    setLoading(true);
    setErrorMessage("");
    setNotFound(false);
    try {
      const nextClient = await getClient(nextClientId);
      if (!nextClient) {
        setClient(null);
        setNotFound(true);
        return;
      }
      setClient(nextClient);
    } catch (error) {
      setErrorMessage(toUserMessage(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="고객사 상세"
        description="현재 고객사 상세 API 기준으로 기본정보만 표시하는 skeleton 화면입니다."
        extra={
          <Space>
            {client ? <SmartStatusBadge status={client.active_yn ? "NORMAL" : "INACTIVE"} label={client.active_yn ? "사용중" : "사용중지"} /> : null}
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(ROUTE_PATHS.masterClients)}>
              목록으로
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => loadClient()} loading={loading}>
              새로고침
            </Button>
          </Space>
        }
      />

      <SmartErrorNotice message={errorMessage} />

      {loading ? <Skeleton active paragraph={{ rows: 8 }} /> : null}

      {!loading && notFound ? (
        <Result
          status="warning"
          title="고객사를 찾을 수 없습니다."
          subTitle="요청한 고객사 ID가 없거나 현재 계정으로 접근할 수 없습니다."
          extra={
            <Button type="primary" onClick={() => navigate(ROUTE_PATHS.masterClients)}>
              목록으로
            </Button>
          }
        />
      ) : null}

      {!loading && client ? (
        <>
          <Card className="smart-work-panel" title="기본정보">
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="client_id">
                <Typography.Text copyable>{getClientId(client)}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="사용 여부">
                <SmartStatusBadge status={client.active_yn ? "NORMAL" : "INACTIVE"} label={client.active_yn ? "사용중" : "사용중지"} />
              </Descriptions.Item>
              <Descriptions.Item label="고객사명">
                <Typography.Text copyable>{toDisplayText(client.client_name)}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="고객사 코드">
                <Typography.Text copyable>{toDisplayText(client.client_code)}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="사업자번호">{toDisplayText(client.business_no)}</Descriptions.Item>
              <Descriptions.Item label="담당자">{toDisplayText(client.contact_name)}</Descriptions.Item>
              <Descriptions.Item label="연락처">{toDisplayText(client.contact_phone)}</Descriptions.Item>
              <Descriptions.Item label="이메일">{toDisplayText(client.contact_email)}</Descriptions.Item>
              <Descriptions.Item label="OMS 사용">{toBooleanText(client.use_oms)}</Descriptions.Item>
              <Descriptions.Item label="WMS 사용">{toBooleanText(client.use_wms)}</Descriptions.Item>
              <Descriptions.Item label="반품 사용">{toBooleanText(client.use_returns)}</Descriptions.Item>
              <Descriptions.Item label="정산 사용">{toBooleanText(client.use_settlement)}</Descriptions.Item>
              <Descriptions.Item label="계약 유형">{toDisplayText(client.contract_type, "후속")}</Descriptions.Item>
              <Descriptions.Item label="운영 주체">{toDisplayText(client.owner_type, "후속")}</Descriptions.Item>
              <Descriptions.Item label="기본 창고">{toDisplayText(client.default_warehouse)}</Descriptions.Item>
              <Descriptions.Item label="기본 처리장소">{toDisplayText(client.default_processing_site)}</Descriptions.Item>
              <Descriptions.Item label="등록일">{formatDateText(client.created_at)}</Descriptions.Item>
              <Descriptions.Item label="수정일">{formatDateText(client.updated_at)}</Descriptions.Item>
              <Descriptions.Item label="메모" span={2}>
                {toDisplayText(client.remarks)}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <ClientWarehouseSettingsSection clientId={getClientId(client)} />
          <ClientUnitsSection clientId={getClientId(client)} />
          <ClientReturnWarehouseRoutesSection clientId={getClientId(client)} />
        </>
      ) : null}
    </SmartPage>
  );
}

function getClientId(client: ClientDetail) {
  return Number(client.client_id || client.id || 0);
}

function toDisplayText(value: unknown, fallback = "-") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function toBooleanText(value: boolean | undefined) {
  if (value === undefined) {
    return "-";
  }
  return value ? "사용" : "미사용";
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

function toUserMessage(error: unknown) {
  if (error instanceof ApiClientError) {
    if (error.resultCode === "NOT_AUTHENTICATED" || error.resultCode === "INVALID_TOKEN") {
      return "로그인이 필요하거나 인증이 만료되었습니다. 다시 로그인해 주세요.";
    }
    if (error.status === 403) {
      return "고객사 상세를 볼 권한이 없습니다.";
    }
    if (error.status === 404) {
      return "고객사를 찾을 수 없습니다.";
    }
    return error.message || "고객사 정보를 불러오지 못했습니다.";
  }
  return "고객사 정보를 불러오지 못했습니다.";
}
