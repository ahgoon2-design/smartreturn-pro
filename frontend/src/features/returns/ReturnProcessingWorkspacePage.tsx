import { ClearOutlined, DeleteOutlined, PaperClipOutlined, PrinterOutlined, ScanOutlined, SearchOutlined, UploadOutlined } from "@ant-design/icons";
import { Alert, Button, Descriptions, Input, List, Space, Tooltip, Typography } from "antd";
import type { InputRef } from "antd";
import type { RefObject } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { ApiClientError } from "../../api/client";
import {
  disableReturnProcessingAttachment,
  judgeReturnProcessingTask,
  listReturnProcessingAttachments,
  listReturnProcessingTasks,
  uploadReturnProcessingAttachment,
} from "../../api/returnIntake";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartScanPanel } from "../../components/common/SmartScanPanel";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn } from "../../components/grid/SmartDataGrid.types";
import type { ReturnJudgementStatus, ReturnProcessingAttachment, ReturnProcessingTask } from "../../types/returns";

type ScanFeedback = {
  type: "info" | "success" | "warning" | "error";
  message: string;
  description?: string;
};

type ProductCheckStatus = "NO_TARGET" | "PENDING" | "NEEDS_INPUT" | "MATCHED" | "MISMATCHED";

type ProductCheckFeedback = {
  status: ProductCheckStatus;
  type: "info" | "success" | "warning" | "error";
  message: string;
  description?: string;
};

const INITIAL_SCAN_FEEDBACK: ScanFeedback = {
  type: "info",
  message: "운송장번호를 스캔하거나 Enter로 대기 대상을 조회하세요.",
};

const NO_TARGET_PRODUCT_FEEDBACK: ProductCheckFeedback = {
  status: "NO_TARGET",
  type: "info",
  message: "먼저 운송장번호를 스캔해 처리 대상을 선택하세요.",
};

const JUDGEMENT_OPTIONS: Array<{ value: ReturnJudgementStatus; label: string }> = [
  { value: "GOOD", label: "양품" },
  { value: "REFURB", label: "리퍼" },
  { value: "REFURB_A", label: "리퍼A" },
  { value: "REFURB_B", label: "리퍼B" },
  { value: "REFURB_C", label: "리퍼C" },
  { value: "SAMPLE", label: "샘플" },
  { value: "MANUFACTURER_RETURN", label: "제조사반품" },
  { value: "DISPOSAL", label: "폐기" },
  { value: "HOLD", label: "보류" },
];

const LABEL_REQUIRED_JUDGEMENTS = new Set<ReturnJudgementStatus>([
  "REFURB",
  "REFURB_A",
  "REFURB_B",
  "REFURB_C",
  "SAMPLE",
  "MANUFACTURER_RETURN",
  "HOLD",
]);

export function ReturnProcessingWorkspacePage() {
  const scanInputRef = useRef<InputRef>(null);
  const productScanInputRef = useRef<InputRef>(null);
  const attachmentInputRef = useRef<HTMLInputElement>(null);
  const [trackingNo, setTrackingNo] = useState("");
  const [productScanValue, setProductScanValue] = useState("");
  const [tasks, setTasks] = useState<ReturnProcessingTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<ReturnProcessingTask | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [scanFeedback, setScanFeedback] = useState<ScanFeedback>(INITIAL_SCAN_FEEDBACK);
  const [productCheckFeedback, setProductCheckFeedback] = useState<ProductCheckFeedback>(NO_TARGET_PRODUCT_FEEDBACK);
  const [selectedJudgement, setSelectedJudgement] = useState<ReturnJudgementStatus | null>(null);
  const [judgementMemo, setJudgementMemo] = useState("");
  const [judging, setJudging] = useState(false);
  const [judgementFeedback, setJudgementFeedback] = useState<ScanFeedback | null>(null);
  const [attachments, setAttachments] = useState<ReturnProcessingAttachment[]>([]);
  const [attachmentsLoading, setAttachmentsLoading] = useState(false);
  const [attachmentUploading, setAttachmentUploading] = useState(false);
  const [attachmentFile, setAttachmentFile] = useState<File | null>(null);
  const [attachmentNote, setAttachmentNote] = useState("");
  const [attachmentFeedback, setAttachmentFeedback] = useState<ScanFeedback | null>(null);

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
      {
        key: "source_type",
        title: "출처",
        dataIndex: "source_type",
        width: 130,
        minWidth: 120,
        render: (_value, record) => <SmartStatusBadge status={record.source_type || "MANUAL"} label={toSourceLabel(record)} />,
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
      {
        key: "judgement",
        title: "판정",
        dataIndex: "judgement_status",
        width: 130,
        minWidth: 120,
        render: (value) =>
          value ? (
            <SmartStatusBadge status="SUCCESS" label={toJudgementLabel(value)} />
          ) : (
            <Typography.Text type="secondary">미판정</Typography.Text>
          ),
      },
      {
        key: "return_label_no",
        title: "라벨번호",
        dataIndex: "return_label_no",
        width: 170,
        minWidth: 160,
        copyable: true,
        render: (_value, record) => renderLabelNumber(record),
      },
      { key: "photo", title: "사진", width: 100, minWidth: 90, render: () => <Typography.Text type="secondary">후속</Typography.Text> },
      {
        key: "label",
        title: "라벨상태",
        width: 170,
        minWidth: 160,
        render: (_value, record) => (
          <SmartStatusBadge status={toLabelBadgeStatus(record.label_print_status, record.label_print_required)} label={toLabelStatusLabel(record)} />
        ),
      },
    ],
    [],
  );

  const selectedKey = selectedTask ? [selectedTask.task_id] : [];
  const summaryText = `${tasks.length}건 표시`;
  const warningCount = tasks.filter((item) => item.validation_status === "WARNING").length;
  const isSelectedTaskCompleted = selectedTask?.status === "COMPLETED";
  const canSaveJudgement =
    Boolean(selectedTask) &&
    !isSelectedTaskCompleted &&
    selectedTask?.validation_status !== "INVALID" &&
    productCheckFeedback.status === "MATCHED" &&
    Boolean(selectedJudgement) &&
    !judging;

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
      selectProcessingTask(nextSelectedTask, { focusProduct: Boolean(normalizedTrackingNo && nextSelectedTask) });
      setScanFeedback(buildScanFeedback(normalizedTrackingNo, nextItems.length, nextSelectedTask));
      if (!nextSelectedTask || !normalizedTrackingNo) {
        focusScanInput(scanInputRef, { select: nextItems.length === 0 || Boolean(normalizedTrackingNo) });
      }
    } catch (error) {
      const message = toUserMessage(error, "반품처리 대상을 조회하지 못했습니다.");
      setTasks([]);
      selectProcessingTask(null);
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

  async function loadTaskAttachments(taskId: number) {
    setAttachmentsLoading(true);
    setAttachmentFeedback(null);
    try {
      const response = await listReturnProcessingAttachments(taskId);
      setAttachments(response.items || []);
    } catch (error) {
      setAttachments([]);
      setAttachmentFeedback({
        type: "error",
        message: toUserMessage(error, "사진/증빙 목록을 불러오지 못했습니다."),
      });
    } finally {
      setAttachmentsLoading(false);
    }
  }

  function handleScanEnter() {
    void loadTasks(trackingNo);
  }

  function handleReset() {
    setTrackingNo("");
    selectProcessingTask(null);
    setScanFeedback(INITIAL_SCAN_FEEDBACK);
    void loadTasks("");
  }

  function selectProcessingTask(task: ReturnProcessingTask | null, options: { focusProduct?: boolean } = {}) {
    setSelectedTask(task);
    setProductScanValue("");
    setSelectedJudgement(toJudgementStatus(task?.judgement_status));
    setJudgementMemo(task?.judgement_memo || "");
    setJudgementFeedback(null);
    setAttachmentFile(null);
    setAttachmentNote("");
    setAttachmentFeedback(null);
    setAttachments([]);
    if (attachmentInputRef.current) {
      attachmentInputRef.current.value = "";
    }
    setProductCheckFeedback(task ? buildPendingProductFeedback(task) : NO_TARGET_PRODUCT_FEEDBACK);
    if (task) {
      void loadTaskAttachments(task.task_id);
    }
    if (options.focusProduct && task && task.status !== "COMPLETED") {
      focusScanInput(productScanInputRef, { select: true });
    }
  }

  function handleProductScanEnter() {
    const scannedBarcode = productScanValue.trim();
    if (!selectedTask) {
      setProductCheckFeedback(NO_TARGET_PRODUCT_FEEDBACK);
      focusScanInput(scanInputRef, { select: true });
      return;
    }

    if (!scannedBarcode) {
      setProductCheckFeedback({
        status: "NEEDS_INPUT",
        type: "warning",
        message: "상품 바코드를 입력하세요.",
        description: "선택된 반품 상품의 바코드 또는 상품코드를 스캔하세요.",
      });
      focusScanInput(productScanInputRef, { select: true });
      return;
    }

    const expectedValues = getExpectedProductScanValues(selectedTask);
    if (expectedValues.length === 0) {
      setProductCheckFeedback({
        status: "MISMATCHED",
        type: "warning",
        message: "선택 row에 비교할 바코드/상품코드가 없습니다.",
        description: "상품마스터 또는 접수 자료 보강이 필요합니다.",
      });
      focusScanInput(productScanInputRef, { select: true });
      return;
    }

    if (expectedValues.includes(scannedBarcode)) {
      setProductCheckFeedback({
        status: "MATCHED",
        type: "success",
        message: "상품 확인 완료",
        description: "스캔한 바코드가 선택된 상품과 일치합니다.",
      });
      setProductScanValue("");
      focusScanInput(productScanInputRef);
      return;
    }

    setProductCheckFeedback({
      status: "MISMATCHED",
      type: "error",
      message: "바코드가 일치하지 않습니다.",
      description: "선택된 row의 바코드 또는 상품코드와 다른 값입니다. 상품을 다시 확인하세요.",
    });
    focusScanInput(productScanInputRef, { select: true });
  }

  async function handleJudgementSave() {
    if (!selectedTask) {
      setJudgementFeedback({
        type: "warning",
        message: "판정할 반품처리 대상을 선택하세요.",
      });
      focusScanInput(scanInputRef, { select: true });
      return;
    }
    if (selectedTask.status === "COMPLETED") {
      setJudgementFeedback({
        type: "warning",
        message: "이미 처리 완료된 항목입니다.",
      });
      return;
    }
    if (productCheckFeedback.status !== "MATCHED") {
      setJudgementFeedback({
        type: "warning",
        message: "상품 확인 후 판정할 수 있습니다.",
        description: "선택된 반품 상품의 바코드 또는 상품코드를 먼저 스캔하세요.",
      });
      focusScanInput(productScanInputRef, { select: true });
      return;
    }
    if (!selectedJudgement) {
      setJudgementFeedback({
        type: "warning",
        message: "판정을 선택하세요.",
      });
      return;
    }

    setJudging(true);
    setJudgementFeedback(null);
    try {
      const response = await judgeReturnProcessingTask(selectedTask.task_id, {
        judgement_status: selectedJudgement,
        judgement_memo: judgementMemo,
        print_label: isLabelRequiredJudgement(selectedJudgement),
      });
      const updatedTask: ReturnProcessingTask = { ...selectedTask, ...response };
      setTasks((previous) => previous.map((item) => (item.task_id === updatedTask.task_id ? updatedTask : item)));
      setSelectedTask(updatedTask);
      setSelectedJudgement(toJudgementStatus(updatedTask.judgement_status));
      setJudgementMemo(updatedTask.judgement_memo || "");
      setJudgementFeedback({
        type: "success",
        message: "판정을 저장했습니다.",
        description: buildJudgementSavedDescription(updatedTask),
      });
      setTrackingNo("");
      focusScanInput(scanInputRef, { select: true });
    } catch (error) {
      setJudgementFeedback({
        type: "error",
        message: toUserMessage(error, "판정을 저장하지 못했습니다."),
        description: "처리 상태와 권한을 확인한 뒤 다시 시도하세요.",
      });
    } finally {
      setJudging(false);
    }
  }

  async function handleAttachmentUpload() {
    if (!selectedTask) {
      setAttachmentFeedback({
        type: "warning",
        message: "먼저 반품처리 대상을 선택하세요.",
      });
      return;
    }
    if (!attachmentFile) {
      setAttachmentFeedback({
        type: "warning",
        message: "첨부할 이미지 파일을 선택하세요.",
      });
      return;
    }
    if (!isAllowedAttachmentFile(attachmentFile)) {
      setAttachmentFeedback({
        type: "error",
        message: "jpg, jpeg, png, webp 이미지 파일만 첨부할 수 있습니다.",
        description: "파일 크기는 10MB 이하만 지원합니다.",
      });
      return;
    }
    if (attachmentFile.size > 10 * 1024 * 1024) {
      setAttachmentFeedback({
        type: "error",
        message: "첨부 파일은 10MB 이하만 업로드할 수 있습니다.",
      });
      return;
    }

    setAttachmentUploading(true);
    setAttachmentFeedback(null);
    try {
      const uploaded = await uploadReturnProcessingAttachment(selectedTask.task_id, attachmentFile, {
        attachment_type: "PHOTO",
        note: attachmentNote,
      });
      setAttachments((previous) => [uploaded, ...previous]);
      setAttachmentFile(null);
      setAttachmentNote("");
      if (attachmentInputRef.current) {
        attachmentInputRef.current.value = "";
      }
      setAttachmentFeedback({
        type: "success",
        message: "사진/증빙을 업로드했습니다.",
      });
    } catch (error) {
      setAttachmentFeedback({
        type: "error",
        message: toUserMessage(error, "사진/증빙을 업로드하지 못했습니다."),
      });
    } finally {
      setAttachmentUploading(false);
    }
  }

  async function handleAttachmentDisable(attachment: ReturnProcessingAttachment) {
    if (!selectedTask) {
      return;
    }
    setAttachmentFeedback(null);
    try {
      await disableReturnProcessingAttachment(selectedTask.task_id, attachment.attachment_id);
      setAttachments((previous) => previous.filter((item) => item.attachment_id !== attachment.attachment_id));
      setAttachmentFeedback({
        type: "success",
        message: "사진/증빙을 목록에서 제거했습니다.",
      });
    } catch (error) {
      setAttachmentFeedback({
        type: "error",
        message: toUserMessage(error, "사진/증빙을 제거하지 못했습니다."),
      });
    }
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

      <SmartScanPanel className="return-processing-scan-panel" ariaLabel="운송장 스캔">
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
      </SmartScanPanel>

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
            onRowClick={(record) => selectProcessingTask(record, { focusProduct: true })}
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
          <div className="return-processing-product-scan" aria-label="상품 바코드 스캔">
            <Space align="center" wrap>
              <Typography.Text strong>상품 바코드 스캔</Typography.Text>
              <SmartStatusBadge status={toProductCheckBadgeStatus(productCheckFeedback.status)} label={toProductCheckLabel(productCheckFeedback.status)} />
            </Space>
            <Input
              ref={productScanInputRef}
              size="large"
              prefix={<ScanOutlined />}
              allowClear
              disabled={!selectedTask || selectedTask.status === "COMPLETED"}
              value={productScanValue}
              placeholder={
                selectedTask?.status === "COMPLETED"
                  ? "이미 처리 완료된 항목입니다"
                  : selectedTask
                    ? "선택된 반품 상품의 바코드를 스캔하세요"
                    : "먼저 운송장번호를 스캔해 처리 대상을 선택하세요"
              }
              onChange={(event) => setProductScanValue(event.target.value)}
              onPressEnter={handleProductScanEnter}
            />
            <Alert
              className="return-processing-product-feedback"
              type={productCheckFeedback.type}
              showIcon
              message={productCheckFeedback.message}
              description={productCheckFeedback.description}
            />
          </div>
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
                <Descriptions.Item label="판정">
                  {selectedTask.judgement_status ? (
                    <SmartStatusBadge status="SUCCESS" label={toJudgementLabel(selectedTask.judgement_status)} />
                  ) : (
                    toDisplayText(null)
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="반품관리번호">{toDisplayText(selectedTask.return_management_no)}</Descriptions.Item>
                <Descriptions.Item label="라벨번호">{toDisplayText(selectedTask.return_label_no)}</Descriptions.Item>
                <Descriptions.Item label="라벨 출력 대상">
                  <SmartStatusBadge
                    status={selectedTask.label_print_required ? "WARNING" : "WAITING"}
                    label={selectedTask.label_print_required ? "라벨 출력 대상" : "라벨 출력 대상 아님"}
                  />
                </Descriptions.Item>
                <Descriptions.Item label="라벨상태">
                  <SmartStatusBadge
                    status={toLabelBadgeStatus(selectedTask.label_print_status, selectedTask.label_print_required)}
                    label={toLabelStatusLabel(selectedTask)}
                  />
                </Descriptions.Item>
                <Descriptions.Item label="출력일시">{toDisplayText(selectedTask.label_printed_at)}</Descriptions.Item>
              </Descriptions>
              <section className="return-processing-label-panel" aria-label="Local Agent 라벨 출력">
                <Space align="center" wrap>
                  <PrinterOutlined />
                  <Typography.Text strong>Local Agent 라벨 출력</Typography.Text>
                  <SmartStatusBadge status="WARNING" label="Local Agent 미연결" />
                </Space>
                <Alert
                  className="return-processing-placeholder"
                  type="warning"
                  showIcon
                  message="라벨 출력 준비중"
                  description="기존 SmartReturn Local Agent endpoint가 확인되기 전까지 실제 출력 호출은 하지 않습니다. 현재는 라벨번호 생성과 출력 필요 상태만 표시합니다."
                />
                <Descriptions size="small" column={1} bordered>
                  <Descriptions.Item label="반품관리번호">{toDisplayText(selectedTask.return_management_no)}</Descriptions.Item>
                  <Descriptions.Item label="라벨번호">{toDisplayText(selectedTask.return_label_no)}</Descriptions.Item>
                  <Descriptions.Item label="라벨상태">
                    <SmartStatusBadge
                      status={toLabelBadgeStatus(selectedTask.label_print_status, selectedTask.label_print_required)}
                      label={toLabelStatusLabel(selectedTask)}
                    />
                  </Descriptions.Item>
                  <Descriptions.Item label="출력 정책">{buildLabelTargetDescription(selectedTask)}</Descriptions.Item>
                </Descriptions>
                <Space wrap>
                  <Tooltip title={getLabelActionDisabledReason(selectedTask)}>
                    <span>
                      <Button icon={<PrinterOutlined />} disabled>
                        라벨 출력
                      </Button>
                    </span>
                  </Tooltip>
                  <Tooltip title={getLabelActionDisabledReason(selectedTask)}>
                    <span>
                      <Button icon={<PrinterOutlined />} disabled>
                        라벨 재출력
                      </Button>
                    </span>
                  </Tooltip>
                </Space>
              </section>
              <section className="return-processing-judgement-panel" aria-label="판정 저장">
                <Space align="center" wrap>
                  <Typography.Text strong>판정 선택</Typography.Text>
                  {selectedJudgement ? (
                    <SmartStatusBadge status="SUCCESS" label={toJudgementLabel(selectedJudgement)} />
                  ) : (
                    <SmartStatusBadge status="WAITING" label="미선택" />
                  )}
                </Space>
                <Space wrap className="return-processing-judgement-buttons">
                  {JUDGEMENT_OPTIONS.map((option) => (
                    <Button
                      key={option.value}
                      type={selectedJudgement === option.value ? "primary" : "default"}
                      disabled={isSelectedTaskCompleted || judging}
                      onClick={() => {
                        setSelectedJudgement(option.value);
                        setJudgementFeedback({
                          type: "info",
                          message: `${option.label} 판정을 선택했습니다.`,
                          description: buildLabelPolicyDescription(option.value),
                        });
                      }}
                    >
                      {option.label}
                    </Button>
                  ))}
                </Space>
                <Input.TextArea
                  rows={3}
                  value={judgementMemo}
                  disabled={isSelectedTaskCompleted || judging}
                  placeholder="판정 메모를 입력하세요"
                  onChange={(event) => setJudgementMemo(event.target.value)}
                />
                <Alert
                  className="return-processing-placeholder"
                  type={judgementFeedback?.type || "info"}
                  showIcon
                  message={judgementFeedback?.message || getJudgementHelpMessage(selectedTask, productCheckFeedback.status, selectedJudgement)}
                  description={judgementFeedback?.description || buildSelectedJudgementDescription(selectedJudgement)}
                />
                <Button type="primary" onClick={handleJudgementSave} disabled={!canSaveJudgement} loading={judging}>
                  판정 저장
                </Button>
              </section>
              <section className="return-processing-attachments-panel" aria-label="사진/증빙">
                <Space align="center" wrap>
                  <PaperClipOutlined />
                  <Typography.Text strong>사진/증빙</Typography.Text>
                  <SmartStatusBadge status="WAITING" label="선택 사항" />
                </Space>
                <Typography.Text type="secondary">
                  필요한 경우 사진을 첨부하세요. 사진이 없어도 판정 저장은 가능합니다.
                </Typography.Text>
                <Typography.Text type="secondary">
                  리퍼, 제조사반품, 보류, 폐기 등은 사진 첨부를 권장합니다.
                </Typography.Text>
                <div className="return-processing-attachment-upload">
                  <input
                    ref={attachmentInputRef}
                    type="file"
                    accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                    disabled={!selectedTask || attachmentUploading}
                    onChange={(event) => setAttachmentFile(event.target.files?.[0] || null)}
                  />
                  <Input.TextArea
                    rows={2}
                    value={attachmentNote}
                    disabled={!selectedTask || attachmentUploading}
                    placeholder="첨부 메모를 입력하세요."
                    onChange={(event) => setAttachmentNote(event.target.value)}
                  />
                  <Button
                    icon={<UploadOutlined />}
                    onClick={() => void handleAttachmentUpload()}
                    loading={attachmentUploading}
                    disabled={!selectedTask || !attachmentFile}
                  >
                    업로드
                  </Button>
                </div>
                {attachmentFeedback ? (
                  <Alert
                    className="return-processing-placeholder"
                    type={attachmentFeedback.type}
                    showIcon
                    message={attachmentFeedback.message}
                    description={attachmentFeedback.description}
                  />
                ) : null}
                <List
                  size="small"
                  loading={attachmentsLoading}
                  dataSource={attachments}
                  locale={{ emptyText: "첨부된 사진/증빙이 없습니다." }}
                  renderItem={(attachment) => (
                    <List.Item
                      actions={[
                        <Button
                          key="disable"
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => void handleAttachmentDisable(attachment)}
                        >
                          제거
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={attachment.original_filename}
                        description={`${toFileSizeLabel(attachment.file_size)} · ${attachment.content_type}${
                          attachment.note ? ` · ${attachment.note}` : ""
                        }`}
                      />
                    </List.Item>
                  )}
                />
              </section>
              <Alert
                className="return-processing-placeholder"
                type="info"
                showIcon
                message="후속 구현 범위"
                description="사진 등록, 실제 Local Agent 라벨 출력, 재고 반영은 다음 단계에서 연결합니다."
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

function toJudgementLabel(value: unknown) {
  const status = String(value || "");
  const labels: Record<string, string> = {
    GOOD: "양품",
    REFURB: "리퍼",
    REFURB_A: "리퍼A",
    REFURB_B: "리퍼B",
    REFURB_C: "리퍼C",
    SAMPLE: "샘플",
    MANUFACTURER_RETURN: "제조사반품",
    DISPOSAL: "폐기",
    HOLD: "보류",
  };
  return labels[status] || status;
}

function toJudgementStatus(value: unknown): ReturnJudgementStatus | null {
  const status = String(value || "") as ReturnJudgementStatus;
  return JUDGEMENT_OPTIONS.some((option) => option.value === status) ? status : null;
}

function isLabelRequiredJudgement(value: ReturnJudgementStatus) {
  return LABEL_REQUIRED_JUDGEMENTS.has(value);
}

function toLabelBadgeStatus(status: unknown, required: unknown) {
  if (!required) {
    return "WAITING";
  }
  const normalized = String(status || "");
  const statusMap: Record<string, string> = {
    PRINT_PENDING: "WARNING",
    PRINTED: "SUCCESS",
    PRINT_FAILED: "ERROR",
    LOCAL_AGENT_NOT_CONNECTED: "WARNING",
  };
  return statusMap[normalized] || "WARNING";
}

function toLabelStatusLabel(task: ReturnProcessingTask) {
  if (!task.label_print_required) {
    return "라벨 미대상";
  }
  const status = String(task.label_print_status || "");
  const labels: Record<string, string> = {
    PRINT_PENDING: "출력 대기",
    PRINTED: "출력 완료",
    PRINT_FAILED: "출력 실패",
    LOCAL_AGENT_NOT_CONNECTED: "Local Agent 미연결",
  };
  return labels[status] || "라벨 출력 필요";
}

function toSourceLabel(task: ReturnProcessingTask) {
  if (task.source_type === "CHANNEL_API") {
    return task.source_origin ? `채널:${task.source_origin}` : "채널 자동수집";
  }
  return task.source_type || "수동/업로드";
}

function getLabelNumber(task: ReturnProcessingTask) {
  return task.return_label_no || task.return_management_no || "";
}

function renderLabelNumber(task: ReturnProcessingTask) {
  if (!task.label_print_required) {
    return <Typography.Text type="secondary">미대상</Typography.Text>;
  }
  const labelNo = getLabelNumber(task);
  return labelNo ? labelNo : <Typography.Text type="secondary">라벨번호 미생성</Typography.Text>;
}

function buildLabelTargetDescription(task: ReturnProcessingTask) {
  if (!task.label_print_required) {
    return "라벨 출력 대상 아님";
  }
  if (!getLabelNumber(task)) {
    return "라벨 출력 대상이지만 라벨번호가 아직 생성되지 않았습니다.";
  }
  return "라벨 출력 대상입니다. Local Agent 연동 후 출력/재출력을 사용할 수 있습니다.";
}

function getLabelActionDisabledReason(task: ReturnProcessingTask) {
  if (!task.label_print_required) {
    return "라벨 출력 대상이 아닙니다.";
  }
  if (!getLabelNumber(task)) {
    return "라벨번호가 생성된 뒤 출력할 수 있습니다.";
  }
  return "Local Agent 연동 후 사용할 수 있습니다.";
}

function isAllowedAttachmentFile(file: File) {
  const extension = file.name.split(".").pop()?.toLowerCase();
  return (
    Boolean(extension && ["jpg", "jpeg", "png", "webp"].includes(extension)) &&
    ["image/jpeg", "image/png", "image/webp"].includes(file.type)
  );
}

function toFileSizeLabel(size: number) {
  if (size >= 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(1)}MB`;
  }
  if (size >= 1024) {
    return `${Math.ceil(size / 1024)}KB`;
  }
  return `${size}B`;
}

function buildLabelPolicyDescription(judgementStatus: ReturnJudgementStatus) {
  if (isLabelRequiredJudgement(judgementStatus)) {
    return "추적 대상 판정입니다. 저장 시 반품관리번호/라벨번호를 생성하고 Local Agent 출력 연결을 시도할 수 있는 상태로 표시합니다.";
  }
  if (judgementStatus === "DISPOSAL") {
    return "폐기는 1차 정책에서 기본 라벨 미출력 대상입니다. 필요 시 후속 정책으로 선택 출력 여부를 정합니다.";
  }
  return "양품은 기본 라벨 미출력 대상입니다.";
}

function buildSelectedJudgementDescription(judgementStatus: ReturnJudgementStatus | null) {
  if (!judgementStatus) {
    return "상품 확인 후 판정을 선택하고 저장하세요.";
  }
  return buildLabelPolicyDescription(judgementStatus);
}

function getJudgementHelpMessage(
  task: ReturnProcessingTask | null,
  productCheckStatus: ProductCheckStatus,
  judgementStatus: ReturnJudgementStatus | null,
) {
  if (!task) {
    return "판정할 처리 대상을 선택하세요.";
  }
  if (task.status === "COMPLETED") {
    return "이미 처리 완료된 항목입니다.";
  }
  if (productCheckStatus !== "MATCHED") {
    return "상품 확인 후 판정할 수 있습니다.";
  }
  if (!judgementStatus) {
    return "판정을 선택하세요.";
  }
  return "판정을 저장할 수 있습니다.";
}

function buildJudgementSavedDescription(task: ReturnProcessingTask) {
  const labelNo = task.return_label_no || task.return_management_no;
  if (task.label_print_required) {
    return labelNo
      ? `반품관리번호/라벨번호 ${labelNo}가 생성되었습니다. ${toLabelStatusLabel(task)} 상태입니다.`
      : `${toLabelStatusLabel(task)} 상태입니다.`;
  }
  return "라벨 출력 대상이 아니며 처리 완료로 표시했습니다.";
}

function buildPendingProductFeedback(task: ReturnProcessingTask): ProductCheckFeedback {
  if (task.status === "COMPLETED") {
    return {
      status: "MATCHED",
      type: "success",
      message: "이미 처리 완료된 항목입니다.",
      description: "저장된 판정과 라벨 상태를 확인하세요.",
    };
  }
  const expectedValues = getExpectedProductScanValues(task);
  if (expectedValues.length === 0) {
    return {
      status: "PENDING",
      type: "warning",
      message: "선택된 상품을 확인하세요.",
      description: "선택 row에 비교할 바코드/상품코드가 없어 접수 자료 확인이 필요합니다.",
    };
  }

  return {
    status: "PENDING",
    type: "info",
    message: "선택된 상품을 확인하세요.",
    description: "선택된 반품 상품의 바코드 또는 상품코드를 스캔하세요.",
  };
}

function getExpectedProductScanValues(task: ReturnProcessingTask) {
  return [task.barcode, task.product_code]
    .map((value) => String(value || "").trim())
    .filter((value) => value.length > 0);
}

function toProductCheckBadgeStatus(status: ProductCheckStatus) {
  const statusMap: Record<ProductCheckStatus, string> = {
    NO_TARGET: "WAITING",
    PENDING: "WAITING",
    NEEDS_INPUT: "WARNING",
    MATCHED: "SUCCESS",
    MISMATCHED: "ERROR",
  };
  return statusMap[status];
}

function toProductCheckLabel(status: ProductCheckStatus) {
  const labels: Record<ProductCheckStatus, string> = {
    NO_TARGET: "대상 미선택",
    PENDING: "미확인",
    NEEDS_INPUT: "입력 필요",
    MATCHED: "확인 완료",
    MISMATCHED: "불일치",
  };
  return labels[status];
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
