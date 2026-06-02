import { ClearOutlined, ScanOutlined, SearchOutlined } from "@ant-design/icons";
import { Alert, Button, Descriptions, Input, Space, Typography } from "antd";
import type { InputRef } from "antd";
import type { RefObject } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { ApiClientError } from "../../api/client";
import { listReturnProcessingTasks } from "../../api/returnIntake";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn } from "../../components/grid/SmartDataGrid.types";
import type { ReturnProcessingTask } from "../../types/returns";

type ScanFeedback = {
  type: "info" | "success" | "warning" | "error";
  message: string;
  description?: string;
};

const INITIAL_SCAN_FEEDBACK: ScanFeedback = {
  type: "info",
  message: "운송장번호를 스캔하거나 Enter로 대기 대상을 조회하세요.",
};

export function ReturnProcessingWorkspacePage() {
  const scanInputRef = useRef<InputRef>(null);
  const [trackingNo, setTrackingNo] = useState("");
  const [tasks, setTasks] = useState<ReturnProcessingTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<ReturnProcessingTask | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [scanFeedback, setScanFeedback] = useState<ScanFeedback>(INITIAL_SCAN_FEEDBACK);

  useEffect(() => {
    focusScanInput(scanInputRef);
    void loadTasks();
  }, []);

  const columns = useMemo<SmartDataGridColumn<ReturnProcessingTask>[]>(
    () => [
      {
        key: "status",
        title: "상태",
        dataIndex: "status",
        width: 130,
        minWidth: 120,
        render: (value) => <SmartStatusBadge status={String(value)} label={toRowStatusLabel(value)} />,
      },
      { key: "row_no", title: "row", dataIndex: "row_no", width: 80, minWidth: 70, sortable: true },
      {
        key: "return_tracking_no",
        title: "운송장번호",
        dataIndex: "return_tracking_no",
        width: 170,
        minWidth: 160,
        copyable: true,
      },
      { key: "order_no", title: "주문번호", dataIndex: "order_no", width: 160, minWidth: 150, copyable: true },
      { key: "product_code", title: "상품코드", dataIndex: "product_code", width: 140, minWidth: 130, copyable: true },
      { key: "barcode", title: "바코드", dataIndex: "barcode", width: 150, minWidth: 140, copyable: true },
      { key: "product_name", title: "상품명", dataIndex: "product_name", width: 220, minWidth: 190 },
      { key: "option_name", title: "옵션명", dataIndex: "option_name", width: 180, minWidth: 160, render: (value) => toDisplayText(value) },
      { key: "qty", title: "수량", dataIndex: "qty", width: 80, minWidth: 70, align: "right" },
      { key: "return_reason", title: "반품사유", dataIndex: "return_reason", width: 180, minWidth: 160, render: (value) => toDisplayText(value) },
      {
        key: "validation_status",
        title: "검증상태",
        dataIndex: "validation_status",
        width: 120,
        minWidth: 110,
        render: (value) => <SmartStatusBadge status={String(value)} label={toValidationLabel(value)} />,
      },
      {
        key: "work_status",
        title: "작업상태",
        dataIndex: "status",
        width: 130,
        minWidth: 120,
        render: (value) => <SmartStatusBadge status={String(value)} label={toRowStatusLabel(value)} />,
      },
      { key: "judgement", title: "판정", width: 110, minWidth: 100, render: () => <Typography.Text type="secondary">후속</Typography.Text> },
      { key: "photo", title: "사진", width: 100, minWidth: 90, render: () => <Typography.Text type="secondary">후속</Typography.Text> },
      { key: "label", title: "라벨", width: 100, minWidth: 90, render: () => <Typography.Text type="secondary">후속</Typography.Text> },
    ],
    [],
  );

  const selectedKey = selectedTask ? [selectedTask.task_id] : [];
  const summaryText = `${tasks.length}건 표시`;
  const warningCount = tasks.filter((item) => item.validation_status === "WARNING").length;

  async function loadTasks(nextTrackingNo = trackingNo) {
    setLoading(true);
    setErrorMessage("");
    const normalizedTrackingNo = nextTrackingNo.trim();
    try {
      const page = await listReturnProcessingTasks({
        trackingNo: normalizedTrackingNo || undefined,
        status: "READY_FOR_PROCESSING",
        pageSize: 200,
      });
      const nextItems = page.items || [];
      const nextSelectedTask = pickPreferredProcessingTask(nextItems);
      setTasks(nextItems);
      setSelectedTask(nextSelectedTask);
      setScanFeedback(buildScanFeedback(normalizedTrackingNo, nextItems.length, nextSelectedTask));
      focusScanInput(scanInputRef, { select: nextItems.length === 0 || Boolean(normalizedTrackingNo) });
    } catch (error) {
      const message = toUserMessage(error, "반품처리 대상을 조회하지 못했습니다.");
      setTasks([]);
      setSelectedTask(null);
      setErrorMessage(message);
      setScanFeedback({
        type: "error",
        message,
        description: "운송장번호를 확인한 뒤 다시 스캔하세요.",
      });
      focusScanInput(scanInputRef, { select: true });
    } finally {
      setLoading(false);
    }
  }

  function handleScanEnter() {
    void loadTasks(trackingNo);
  }

  function handleReset() {
    setTrackingNo("");
    setSelectedTask(null);
    setScanFeedback(INITIAL_SCAN_FEEDBACK);
    void loadTasks("");
  }

  return (
    <SmartPage>
      <SmartPageHeader
        title="반품처리 작업"
        description="운송장 스캔으로 READY_FOR_PROCESSING 대상을 조회하고 작업 row를 확인하는 1차 skeleton 화면입니다."
        extra={
          <Space>
            <Button icon={<ClearOutlined />} onClick={handleReset}>
              초기화
            </Button>
            <Button icon={<SearchOutlined />} type="primary" onClick={() => void loadTasks()} loading={loading}>
              조회
            </Button>
          </Space>
        }
      />

      <section className="return-processing-scan-panel" aria-label="운송장 스캔">
        <div className="return-processing-scan-main">
          <Typography.Text strong>운송장번호 스캔</Typography.Text>
          <Input
            ref={scanInputRef}
            className="return-processing-scan-input"
            size="large"
            prefix={<ScanOutlined />}
            allowClear
            value={trackingNo}
            placeholder="스캔 또는 입력 후 Enter"
            onChange={(event) => setTrackingNo(event.target.value)}
            onPressEnter={handleScanEnter}
          />
        </div>
        <div className="return-processing-scan-status">
          <Typography.Text strong>{summaryText}</Typography.Text>
          <Typography.Text type={warningCount > 0 ? "warning" : "secondary"}>경고 {warningCount}건</Typography.Text>
        </div>
        <Alert
          className="return-processing-scan-feedback"
          type={scanFeedback.type}
          showIcon
          message={scanFeedback.message}
          description={scanFeedback.description}
        />
      </section>

      <SmartErrorNotice message={errorMessage} />

      <div className="return-processing-workspace">
        <section className="return-processing-grid-panel" aria-label="반품처리 대기 대상">
          <SmartDataGrid<ReturnProcessingTask>
            rowKey="task_id"
            rows={tasks}
            columns={columns}
            loading={loading}
            error={null}
            emptyText="반품처리 대기 대상이 없습니다."
            enableCopy
            preserveOriginalOrder
            originalOrderKey="row_no"
            enableOriginalOrderReset
            pagination={false}
            maxHeight={420}
            selectedRowKeys={selectedKey}
            enableMultiSelect={false}
            onRowClick={(record) => setSelectedTask(record)}
            getRowClassName={(record) =>
              [
                record.validation_status === "WARNING" ? "smart-grid-row-warning" : "",
                selectedTask?.task_id === record.task_id ? "smart-grid-row--selected" : "",
              ]
                .filter(Boolean)
                .join(" ")
            }
          />
        </section>

        <aside className="return-processing-detail-panel" aria-label="선택 row 상세">
          <Typography.Title level={4}>선택 row 상세</Typography.Title>
          {selectedTask ? (
            <>
              <Descriptions size="small" column={1} bordered>
                <Descriptions.Item label="운송장번호">{toDisplayText(selectedTask.return_tracking_no)}</Descriptions.Item>
                <Descriptions.Item label="주문번호">{toDisplayText(selectedTask.order_no)}</Descriptions.Item>
                <Descriptions.Item label="상품코드">{toDisplayText(selectedTask.product_code)}</Descriptions.Item>
                <Descriptions.Item label="바코드">{toDisplayText(selectedTask.barcode)}</Descriptions.Item>
                <Descriptions.Item label="상품명">{toDisplayText(selectedTask.product_name)}</Descriptions.Item>
                <Descriptions.Item label="옵션명">{toDisplayText(selectedTask.option_name)}</Descriptions.Item>
                <Descriptions.Item label="수량">{toDisplayText(selectedTask.qty)}</Descriptions.Item>
                <Descriptions.Item label="반품사유">{toDisplayText(selectedTask.return_reason)}</Descriptions.Item>
                <Descriptions.Item label="검증상태">
                  <SmartStatusBadge status={selectedTask.validation_status} label={toValidationLabel(selectedTask.validation_status)} />
                </Descriptions.Item>
                <Descriptions.Item label="작업상태">
                  <SmartStatusBadge status={selectedTask.status} label={toRowStatusLabel(selectedTask.status)} />
                </Descriptions.Item>
              </Descriptions>
              <Alert
                className="return-processing-placeholder"
                type="info"
                showIcon
                message="다음 단계"
                description="다음 단계에서 상품 바코드 스캔을 연결합니다. 현재는 선택 row 확인까지만 수행합니다."
              />
              <Alert
                className="return-processing-placeholder"
                type="info"
                showIcon
                message="후속 구현 범위"
                description="판정 선택, 사진 등록, 라벨 출력, 처리 완료는 다음 단계에서 API와 함께 연결합니다."
              />
            </>
          ) : (
            <Alert
              type="info"
              showIcon
              message="운송장번호를 스캔하거나 목록에서 대상을 선택하세요."
              description="조회 결과가 있으면 처리 가능한 첫 번째 row가 자동 선택됩니다."
            />
          )}
        </aside>
      </div>
    </SmartPage>
  );
}

function toValidationLabel(value: unknown) {
  const status = String(value || "");
  const labels: Record<string, string> = {
    NOT_VALIDATED: "검증 전",
    VALID: "정상",
    WARNING: "경고",
    INVALID: "오류",
  };
  return labels[status] || status;
}

function toRowStatusLabel(value: unknown) {
  const status = String(value || "");
  const labels: Record<string, string> = {
    RECEIVED: "접수",
    READY_FOR_PROCESSING: "처리 대기",
    PROCESSING: "처리 중",
    COMPLETED: "처리 완료",
    HOLD: "보류",
  };
  return labels[status] || status;
}

function pickPreferredProcessingTask(items: ReturnProcessingTask[]) {
  return (
    items.find((item) => item.status === "READY_FOR_PROCESSING") ||
    items.find((item) => item.status === "RECEIVED") ||
    items[0] ||
    null
  );
}

function buildScanFeedback(trackingNo: string, resultCount: number, selectedTask: ReturnProcessingTask | null): ScanFeedback {
  if (trackingNo && resultCount === 0) {
    return {
      type: "warning",
      message: "해당 운송장번호의 반품처리 대기 대상이 없습니다.",
      description: "운송장번호를 확인한 뒤 다시 스캔하세요.",
    };
  }

  if (trackingNo && resultCount === 1) {
    return {
      type: "success",
      message: "대기 대상 1건을 찾았습니다.",
      description: "해당 처리 대상을 자동 선택했습니다.",
    };
  }

  if (trackingNo && resultCount > 1) {
    return {
      type: "success",
      message: `대기 대상 ${resultCount}건을 찾았습니다.`,
      description: selectedTask
        ? "첫 번째 처리 가능 대상을 자동 선택했습니다."
        : "목록에서 처리할 대상을 선택하세요.",
    };
  }

  if (resultCount === 0) {
    return {
      type: "info",
      message: "반품처리 대기 대상이 없습니다.",
      description: "운송장번호를 스캔하면 해당 대상을 조회합니다.",
    };
  }

  return {
    type: "info",
    message: `전체 반품처리 대기 대상 ${resultCount}건을 조회했습니다.`,
    description: selectedTask ? "첫 번째 처리 가능 대상을 자동 선택했습니다." : undefined,
  };
}

function focusScanInput(ref: RefObject<InputRef | null>, options: { select?: boolean } = {}) {
  window.setTimeout(() => {
    ref.current?.focus();
    if (options.select) {
      ref.current?.select?.();
    }
  }, 0);
}

function toDisplayText(value: unknown, fallback = "-") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function toUserMessage(error: unknown, fallback: string) {
  if (error instanceof ApiClientError) {
    if (error.resultCode === "NOT_AUTHENTICATED" || error.resultCode === "INVALID_TOKEN") {
      return "로그인이 필요하거나 인증이 만료되었습니다. 다시 로그인해 주세요.";
    }
    if (error.status === 403) {
      return "반품처리 작업 화면에 접근할 권한이 없습니다.";
    }
    return error.message || fallback;
  }
  return fallback;
}
