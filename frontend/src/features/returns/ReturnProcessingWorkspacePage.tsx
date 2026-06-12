import { ClearOutlined, DeleteOutlined, PaperClipOutlined, PlusOutlined, PrinterOutlined, ScanOutlined, SearchOutlined, UploadOutlined } from "@ant-design/icons";
import { Alert, Button, Descriptions, Input, InputNumber, List, Select, Space, Tag, Tooltip, Typography } from "antd";
import type { InputRef } from "antd";
import type { RefObject } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { ApiClientError } from "../../api/client";
import { listClients, listProducts, listReturnWarehouseRoutes } from "../../api/master";
import {
  createReturnProcessingManualRow,
  disableReturnProcessingAttachment,
  judgeReturnProcessingTask,
  listReturnProcessingAttachments,
  listReturnProcessingTasks,
  uploadReturnProcessingAttachment,
} from "../../api/returnIntake";
import { SmartErrorNotice } from "../../components/common/SmartErrorNotice";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import { SmartHelpButton } from "../../components/help/SmartHelpButton";
import { SmartScanPanel } from "../../components/common/SmartScanPanel";
import { SmartStatusBadge } from "../../components/common/SmartStatusBadge";
import { SmartDataGrid } from "../../components/grid/SmartDataGrid";
import type { SmartDataGridColumn } from "../../components/grid/SmartDataGrid.types";
import { ROUTE_PATHS } from "../../routes/routePaths";
import type { ClientSummary, ProductSummary, ReturnWarehouseRoute } from "../../types/master";
import type { ReturnJudgementStatus, ReturnProcessingAttachment, ReturnProcessingTask } from "../../types/returns";
import { getSearchNumber, getSearchString, mergeSearchParams } from "../../utils/routeState";
import { useNavigate, useSearchParams } from "react-router-dom";

type ScanFeedback = {
  type: "info" | "success" | "warning" | "error";
  message: string;
  description?: string;
};

type ProductCheckStatus = "NO_TARGET" | "PENDING" | "NEEDS_INPUT" | "MATCHED" | "MISMATCHED";
type ProcessingMethod = "SCAN" | "GRID_SELECT" | "MANUAL_QUANTITY" | "BULK_CONFIRM";

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

// 정본 판정 코드(명확 코드). generic REFURB는 신규 판정 선택지로 제공하지 않는다(레거시 표시용 라벨만 유지).
// DEFECTIVE("불량")는 backend ALLOWED + 창고 라우팅 허용 코드에 포함되어 지원된다(고객사 DEFECTIVE 창고 라우팅 설정 없으면 처리완료 차단).
const JUDGEMENT_OPTIONS: Array<{ value: ReturnJudgementStatus; label: string }> = [
  { value: "GOOD", label: "양품" },
  { value: "REFURB_A", label: "리퍼A" },
  { value: "REFURB_B", label: "리퍼B" },
  { value: "REFURB_C", label: "리퍼C" },
  { value: "SAMPLE", label: "샘플" },
  { value: "MANUFACTURER_RETURN", label: "제조사반품" },
  { value: "DEFECTIVE", label: "불량" },
  { value: "DISPOSAL", label: "폐기" },
  { value: "HOLD", label: "보류" },
];

const LABEL_REQUIRED_JUDGEMENTS = new Set<ReturnJudgementStatus>([
  "REFURB_A",
  "REFURB_B",
  "REFURB_C",
  "SAMPLE",
  "MANUFACTURER_RETURN",
  "DEFECTIVE",
  "HOLD",
]);

export function ReturnProcessingWorkspacePage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTaskIdRef = useRef(getSearchNumber(searchParams, "task_id"));
  const scanInputRef = useRef<InputRef>(null);
  const manualProductScanInputRef = useRef<InputRef>(null);
  const productScanInputRef = useRef<InputRef>(null);
  const attachmentInputRef = useRef<HTMLInputElement>(null);
  const [trackingNo, setTrackingNo] = useState(() => getSearchString(searchParams, "tracking_no"));
  const [manualProductScanValue, setManualProductScanValue] = useState("");
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
  const [selectedProcessingMethod, setSelectedProcessingMethod] = useState<ProcessingMethod | null>(null);
  const [noDetailTrackingNo, setNoDetailTrackingNo] = useState("");
  const [returnWarehouseRoutes, setReturnWarehouseRoutes] = useState<ReturnWarehouseRoute[]>([]);
  const [routesLoading, setRoutesLoading] = useState(false);
  const [routesErrorMessage, setRoutesErrorMessage] = useState("");
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [manualClientId, setManualClientId] = useState<number | null>(null);
  const [manualQuantity, setManualQuantity] = useState(1);
  const [manualProductKeyword, setManualProductKeyword] = useState("");
  const [manualProducts, setManualProducts] = useState<ProductSummary[]>([]);
  const [manualProductLoading, setManualProductLoading] = useState(false);
  const [manualRowSaving, setManualRowSaving] = useState(false);
  const [manualFeedback, setManualFeedback] = useState<ScanFeedback | null>(null);

  useEffect(() => {
    focusScanInput(scanInputRef);
    void loadClientsForManualMode();
    void loadTasks(trackingNo, initialTaskIdRef.current);
  }, []);

  useEffect(() => {
    void loadReturnWarehouseRoutesForTask(selectedTask);
  }, [selectedTask?.client_id]);

  const columns = useMemo<SmartDataGridColumn<ReturnProcessingTask>[]>(
    () => [
      {
        key: "status",
        title: "상태",
        dataIndex: "status",
        width: 130,
        minWidth: 120,
        render: (value) => <SmartStatusBadge status={String(value)} label={toRowStatusLabel(value)} />,
        exportValue: (record) => toRowStatusLabel(record.status),
      },
      {
        key: "source_type",
        title: "출처",
        dataIndex: "source_type",
        width: 130,
        minWidth: 120,
        render: (_value, record) => <SmartStatusBadge status={record.source_type || "MANUAL"} label={toSourceLabel(record)} />,
        exportValue: (record) => toSourceLabel(record),
      },
      { key: "row_no", title: "순번", dataIndex: "row_no", width: 80, minWidth: 70, sortable: true },
      {
        key: "return_tracking_no",
        title: "반품 운송장번호",
        dataIndex: "return_tracking_no",
        width: 170,
        minWidth: 160,
        copyable: true,
        exportAsText: true,
      },
      { key: "order_no", title: "주문번호", dataIndex: "order_no", width: 160, minWidth: 150, copyable: true, exportAsText: true },
      { key: "product_code", title: "상품코드", dataIndex: "product_code", width: 140, minWidth: 130, copyable: true, exportAsText: true },
      { key: "barcode", title: "바코드", dataIndex: "barcode", width: 150, minWidth: 140, copyable: true, exportAsText: true },
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
        exportValue: (record) => toValidationLabel(record.validation_status),
      },
      {
        key: "work_status",
        title: "작업상태",
        dataIndex: "status",
        width: 130,
        minWidth: 120,
        render: (value) => <SmartStatusBadge status={String(value)} label={toRowStatusLabel(value)} />,
        exportable: false,
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
        exportValue: (record) => (record.judgement_status ? toJudgementLabel(record.judgement_status) : "미판정"),
      },
      {
        key: "return_label_no",
        title: "라벨번호",
        dataIndex: "return_label_no",
        width: 170,
        minWidth: 160,
        copyable: true,
        render: (_value, record) => renderLabelNumber(record),
        exportAsText: true,
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
  const isNoDetailMode = Boolean(noDetailTrackingNo);
  const completedCount = tasks.filter((item) => item.status === "COMPLETED").length;
  const pendingCount = Math.max(tasks.length - completedCount, 0);
  const summaryText = isNoDetailMode ? `추가된 상품 ${tasks.length}건` : `조회된 상품 ${tasks.length}건`;
  const processingProgressText =
    tasks.length > 0 ? `처리완료 ${completedCount}건 / 미처리 ${pendingCount}건` : isNoDetailMode ? "상품 추가 대기" : "운송장 조회 대기";
  const warningCount = tasks.filter((item) => item.validation_status === "WARNING").length;
  const isSelectedTaskCompleted = selectedTask?.status === "COMPLETED";
  const judgementOptions = useMemo(
    () => buildJudgementOptions(returnWarehouseRoutes),
    [returnWarehouseRoutes],
  );
  const selectedWarehouseRoute = useMemo(
    () => findWarehouseRoute(returnWarehouseRoutes, selectedTask, selectedJudgement),
    [returnWarehouseRoutes, selectedJudgement, selectedTask],
  );
  const manualClient = clients.find((client) => getClientOptionId(client) === manualClientId) || null;
  const contextClientName = selectedTask?.client_name || manualClient?.client_name || "고객사 선택 필요";
  const contextUnitName = selectedTask?.client_unit_name || "운영단위 미지정";
  const contextModeLabel = selectedTask ? toProcessingModeLabel(selectedTask) : isNoDetailMode ? "현장 수동 처리" : "운송장 조회 대기";
  const contextWarehouseLabel = selectedWarehouseRoute
    ? selectedWarehouseRoute.warehouse_name || selectedWarehouseRoute.warehouse_code || "창고 확인됨"
    : selectedJudgement
      ? "창고 확인 필요"
      : "판정 선택 후 자동 배정";
  const canSaveJudgement =
    Boolean(selectedTask) &&
    !isSelectedTaskCompleted &&
    selectedTask?.validation_status !== "INVALID" &&
    productCheckFeedback.status === "MATCHED" &&
    Boolean(selectedJudgement) &&
    Boolean(selectedWarehouseRoute?.warehouse_id) &&
    !judging;
  const showHoldMemoWarning = selectedJudgement === "HOLD" && !judgementMemo.trim();

  useEffect(() => {
    function handleProcessingShortcut(event: KeyboardEvent) {
      if (event.defaultPrevented || event.ctrlKey || event.altKey || event.metaKey || isShortcutInputTarget(event.target)) {
        return;
      }
      if (/^[1-9]$/.test(event.key)) {
        const option = judgementOptions[Number(event.key) - 1];
        if (!option || !selectedTask || isSelectedTaskCompleted || judging) {
          return;
        }
        event.preventDefault();
        selectJudgementOption(option);
        return;
      }
      if (event.key === "Enter" && canSaveJudgement) {
        event.preventDefault();
        void handleJudgementSave();
      }
    }

    window.addEventListener("keydown", handleProcessingShortcut);
    return () => window.removeEventListener("keydown", handleProcessingShortcut);
  }, [canSaveJudgement, isSelectedTaskCompleted, judgementOptions, judging, selectedTask, selectedWarehouseRoute, returnWarehouseRoutes.length, routesErrorMessage, routesLoading]);

  async function loadTasks(nextTrackingNo = trackingNo, preferredTaskId?: number) {
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
      const nextSelectedTask = pickPreferredProcessingTask(nextItems, preferredTaskId);
      setTasks(nextItems);
      setNoDetailTrackingNo(normalizedTrackingNo && nextItems.length === 0 ? normalizedTrackingNo : "");
      selectProcessingTask(nextSelectedTask, { focusProduct: Boolean(normalizedTrackingNo && nextSelectedTask) });
      persistProcessingRouteState(normalizedTrackingNo, nextSelectedTask?.task_id);
      setScanFeedback(buildScanFeedback(normalizedTrackingNo, nextItems.length, nextSelectedTask));
      if (!nextSelectedTask || !normalizedTrackingNo) {
        focusScanInput(scanInputRef, { select: nextItems.length === 0 || Boolean(normalizedTrackingNo) });
      }
    } catch (error) {
      const message = toUserMessage(error, "반품처리 대상을 조회하지 못했습니다.");
      setTasks([]);
      selectProcessingTask(null);
      persistProcessingRouteState(normalizedTrackingNo, undefined);
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

  async function loadReturnWarehouseRoutesForTask(task: ReturnProcessingTask | null) {
    setRoutesErrorMessage("");
    setReturnWarehouseRoutes([]);
    if (!task?.client_id) {
      return;
    }
    setRoutesLoading(true);
    try {
      const routes = await listReturnWarehouseRoutes(task.client_id);
      setReturnWarehouseRoutes(routes.filter((route) => route.active_yn));
    } catch (error) {
      setRoutesErrorMessage(toUserMessage(error, "고객사별 판정/창고 라우팅을 불러오지 못했습니다."));
      setReturnWarehouseRoutes([]);
    } finally {
      setRoutesLoading(false);
    }
  }

  async function loadClientsForManualMode() {
    try {
      const nextClients = await listClients();
      setClients(nextClients);
      if (nextClients.length === 1) {
        setManualClientId(getClientOptionId(nextClients[0]));
      }
    } catch {
      setClients([]);
    }
  }

  async function searchManualProducts(keyword = manualProductKeyword) {
    const clientId = manualClientId;
    const cleanKeyword = keyword.trim();
    if (!clientId) {
      setManualFeedback({
        type: "warning",
        message: "고객사를 먼저 선택하세요.",
      });
      return;
    }
    if (!cleanKeyword) {
      setManualFeedback({
        type: "warning",
        message: "상품코드, 바코드 또는 상품명을 입력하세요.",
      });
      return;
    }
    setManualProductLoading(true);
    setManualFeedback(null);
    try {
      const response = await listProducts({ clientId, keyword: cleanKeyword, pageSize: 20 });
      setManualProducts(response.items || []);
      if ((response.items || []).length === 0) {
        setManualFeedback({
          type: "warning",
          message: "상품마스터에 없는 상품입니다.",
          description: "확인필요 또는 보류로 분리한 뒤 상품 연결 후 처리하세요.",
        });
      }
    } catch (error) {
      setManualFeedback({
        type: "error",
        message: toUserMessage(error, "상품을 검색하지 못했습니다."),
      });
    } finally {
      setManualProductLoading(false);
    }
  }

  async function createManualRowFromProduct(product: ProductSummary, processingMethod: ProcessingMethod | "MANUAL_QUANTITY") {
    if (!noDetailTrackingNo) {
      return;
    }
    if (!manualClientId) {
      setManualFeedback({
        type: "warning",
        message: "고객사를 먼저 선택하세요.",
      });
      return;
    }
    const quantity = Math.max(1, manualQuantity || 1);
    setManualRowSaving(true);
    setManualFeedback(null);
    try {
      const created = await createReturnProcessingManualRow({
        client_id: manualClientId,
        return_tracking_no: noDetailTrackingNo,
        product_id: product.product_id,
        quantity,
        processing_method: processingMethod,
        memo: "반품처리 화면에서 세부항목 없는 반품 상품 추가",
      });
      upsertManualTask(created);
      setManualFeedback({
        type: "success",
        message: created.message,
        description: "추가된 상품을 선택했습니다. 판정별 창고를 확인한 뒤 처리완료하세요.",
      });
      setManualQuantity(1);
      setManualProductKeyword("");
      setManualProducts([]);
      focusScanInput(manualProductScanInputRef, { select: true });
    } catch (error) {
      setManualFeedback({
        type: "error",
        message: toUserMessage(error, "세부항목 없는 반품 상품을 추가하지 못했습니다."),
      });
    } finally {
      setManualRowSaving(false);
    }
  }

  async function createManualRowFromScan(scannedValue: string) {
    if (!manualClientId) {
      setManualFeedback({
        type: "warning",
        message: "고객사를 먼저 선택하세요.",
      });
      return;
    }
    setManualRowSaving(true);
    setManualFeedback(null);
    try {
      const created = await createReturnProcessingManualRow({
        client_id: manualClientId,
        return_tracking_no: noDetailTrackingNo,
        barcode: scannedValue,
        product_code: scannedValue,
        quantity: 1,
        processing_method: "SCAN",
        memo: "상품 스캔으로 세부항목 없는 반품 상품 추가",
      });
      upsertManualTask(created);
      setManualProductScanValue("");
      setManualFeedback({
        type: "success",
        message: created.message,
        description: created.created ? "상품 1개를 추가했습니다." : "같은 상품의 처리수량을 1개 늘렸습니다.",
      });
      focusScanInput(manualProductScanInputRef, { select: true });
    } catch (error) {
      setManualFeedback({
        type: "error",
        message: toUserMessage(error, "상품마스터에 없는 상품입니다. 확인필요 또는 보류로 분리한 뒤 상품 연결 후 처리하세요."),
      });
      focusScanInput(manualProductScanInputRef, { select: true });
    } finally {
      setManualRowSaving(false);
    }
  }

  function upsertManualTask(task: ReturnProcessingTask) {
    setTasks((previous) => {
      const exists = previous.some((item) => item.task_id === task.task_id);
      return exists ? previous.map((item) => (item.task_id === task.task_id ? task : item)) : [task, ...previous];
    });
    selectProcessingTask(task, { focusProduct: true });
    setProductCheckFeedback({
      status: "MATCHED",
      type: "success",
      message: "상품 확인 완료",
      description: "세부항목 없는 반품 상품이 상품마스터 기준으로 추가되었습니다.",
    });
    setSelectedProcessingMethod((task.processing_method as ProcessingMethod) || "SCAN");
    setScanFeedback({
      type: "success",
      message: "세부항목 없는 반품 상품을 처리 화면에 추가했습니다.",
      description: "현재 화면에서 판정/창고 확인 후 처리완료할 수 있습니다.",
    });
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
    setNoDetailTrackingNo("");
    selectProcessingTask(null);
    persistProcessingRouteState("", undefined);
    setScanFeedback(INITIAL_SCAN_FEEDBACK);
    void loadTasks("");
  }

  function selectProcessingTask(task: ReturnProcessingTask | null, options: { focusProduct?: boolean } = {}) {
    setSelectedTask(task);
    persistProcessingRouteState(trackingNo.trim() || task?.return_tracking_no || "", task?.task_id);
    setProductScanValue("");
    setSelectedJudgement(toJudgementStatus(task?.judgement_status));
    setJudgementMemo(task?.judgement_memo || "");
    setJudgementFeedback(null);
    setAttachmentFile(null);
    setAttachmentNote("");
    setAttachmentFeedback(null);
    setAttachments([]);
    setSelectedProcessingMethod(null);
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

  function persistProcessingRouteState(nextTrackingNo: string, nextTaskId?: number) {
    setSearchParams(
      mergeSearchParams(searchParams, {
        tracking_no: nextTrackingNo.trim(),
        task_id: nextTaskId,
      }),
      { replace: true },
    );
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
        message: "선택 상품에 비교할 바코드/상품코드가 없습니다.",
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
        description: "스캔한 바코드/상품코드가 선택된 상품과 일치합니다. 처리방식은 스캔 처리로 기록됩니다.",
      });
      setSelectedProcessingMethod("SCAN");
      setProductScanValue("");
      focusScanInput(productScanInputRef);
      return;
    }

    setProductCheckFeedback({
      status: "MISMATCHED",
      type: "error",
      message: "바코드가 일치하지 않습니다.",
      description: "선택 상품의 바코드 또는 상품코드와 다른 값입니다. 상품을 다시 확인하세요.",
    });
    focusScanInput(productScanInputRef, { select: true });
  }

  function handleManualProductScanEnter() {
    const scannedBarcode = manualProductScanValue.trim();
    if (!scannedBarcode) {
      setManualFeedback({
        type: "warning",
        message: "상품 바코드를 입력하세요.",
        description: "상품을 스캔하거나 상품코드/바코드를 입력한 뒤 Enter를 누르세요.",
      });
      focusScanInput(manualProductScanInputRef, { select: true });
      return;
    }
    void createManualRowFromScan(scannedBarcode);
  }

  function handleGridSelectConfirm() {
    if (!selectedTask) {
      setProductCheckFeedback(NO_TARGET_PRODUCT_FEEDBACK);
      focusScanInput(scanInputRef, { select: true });
      return;
    }
    if (selectedTask.status === "COMPLETED") {
      setProductCheckFeedback({
        status: "MATCHED",
        type: "success",
        message: "이미 처리 완료된 항목입니다.",
        description: "저장된 판정과 처리 이력을 확인하세요.",
      });
      return;
    }
    if (selectedTask.validation_status === "INVALID") {
      setProductCheckFeedback({
        status: "MISMATCHED",
        type: "error",
        message: "오류 항목은 선택 처리할 수 없습니다.",
        description: "반품 자료 화면에서 오류/누락을 먼저 보정하세요.",
      });
      return;
    }
    if (!hasAnyProductHint(selectedTask)) {
      setProductCheckFeedback({
        status: "MISMATCHED",
        type: "warning",
        message: "상품 정보가 없어 선택 처리할 수 없습니다.",
        description: "상품마스터에 있는 상품코드/바코드/상품명 중 하나를 반품 자료에 보강한 뒤 처리하세요.",
      });
      return;
    }
    setProductCheckFeedback({
      status: "MATCHED",
      type: "success",
      message: "그리드 선택 확인 완료",
      description: "실물 확인 후 선택 상품을 처리 대상으로 지정했습니다. 처리방식은 선택 처리로 기록됩니다.",
    });
    setSelectedProcessingMethod("GRID_SELECT");
  }

  function selectJudgementOption(option: { value: ReturnJudgementStatus; label: string }) {
    const nextWarehouseRoute = findWarehouseRoute(returnWarehouseRoutes, selectedTask, option.value);
    setSelectedJudgement(option.value);
    setJudgementFeedback({
      type: nextWarehouseRoute ? "info" : "warning",
      message: `${option.label} 판정을 선택했습니다.`,
      description: buildSelectedJudgementDescription(
        option.value,
        nextWarehouseRoute,
        returnWarehouseRoutes.length,
        routesErrorMessage,
        routesLoading,
      ),
    });
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
    if (!selectedWarehouseRoute?.warehouse_id) {
      setJudgementFeedback({
        type: "warning",
        message: "창고가 확정되어야 처리완료할 수 있습니다.",
        description: buildWarehouseMissingGuidance(selectedJudgement, returnWarehouseRoutes.length),
      });
      return;
    }

    setJudging(true);
    setJudgementFeedback(null);
    try {
      const response = await judgeReturnProcessingTask(selectedTask.task_id, {
        judgement_status: selectedJudgement,
        judgement_memo: buildJudgementMemoForSave(judgementMemo, selectedProcessingMethod || "GRID_SELECT"),
        print_label: isLabelRequiredJudgement(selectedJudgement),
        processing_method: selectedProcessingMethod || "GRID_SELECT",
      });
      const updatedTask: ReturnProcessingTask = { ...selectedTask, ...response };
      setTasks((previous) => previous.map((item) => (item.task_id === updatedTask.task_id ? updatedTask : item)));
      setSelectedTask(updatedTask);
      setSelectedJudgement(toJudgementStatus(updatedTask.judgement_status));
      setJudgementMemo(updatedTask.judgement_memo || "");
      setSelectedProcessingMethod(null);
      setJudgementFeedback({
        type: "success",
        message: "처리완료했습니다.",
        description: buildJudgementSavedDescription(updatedTask),
      });
      setTrackingNo("");
      focusScanInput(scanInputRef, { select: true });
    } catch (error) {
      setJudgementFeedback({
        type: "error",
        message: toUserMessage(error, "처리완료하지 못했습니다."),
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
        title="반품 처리 센터"
        description="운송장 스캔 또는 그리드 선택으로 상품을 확인하고 판정합니다. 처리완료는 현장 판정 완료이며, 재고는 일마감 또는 반출/폐기 확정 후 반영됩니다."
        extra={
          <Space>
            <SmartHelpButton screenKey="returns.processing" />
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
          <Typography.Text type="secondary">{processingProgressText}</Typography.Text>
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

      <div className="return-processing-context-strip" aria-label="반품 처리 흐름과 작업 맥락">
        <Space wrap size={[6, 6]}>
          {["1. 운송장 확인", "2. 상품 추가", "3. 판정", "4. 창고 확정", "5. 처리완료"].map((step) => (
            <Tag key={step} className="return-processing-step-tag">
              {step}
            </Tag>
          ))}
        </Space>
        <Space wrap size={[6, 6]}>
          <Tag>고객사: {contextClientName}</Tag>
          <Tag>운영단위: {contextUnitName}</Tag>
          <Tag>처리 모드: {contextModeLabel}</Tag>
          <Tag>창고: {contextWarehouseLabel}</Tag>
        </Space>
      </div>

      {noDetailTrackingNo ? (
        <section className="return-processing-manual-panel" aria-label="세부항목 없는 반품 상품 추가">
          <Space align="center" wrap>
            <Typography.Text strong>상품 추가</Typography.Text>
            <SmartStatusBadge status="WARNING" label="현장 수동 처리" />
            <Typography.Text type="secondary">반품 운송장번호 {noDetailTrackingNo}</Typography.Text>
          </Space>
          <Space wrap align="center">
            <Typography.Text type="secondary">
              원자료가 없더라도 현재 화면에서 처리할 수 있습니다. 필요하면 나중에 원자료를 보정하세요.
            </Typography.Text>
            <Button type="link" size="small" onClick={() => navigate(ROUTE_PATHS.returnIntake)}>
              원자료 보정
            </Button>
          </Space>
          <Space wrap align="center">
            <Select
              style={{ width: 220 }}
              placeholder="고객사 선택"
              value={manualClientId ?? undefined}
              options={clients.map((client) => ({
                value: getClientOptionId(client),
                label: `${client.client_name} (${client.client_code})`,
              }))}
              onChange={(value) => {
                setManualClientId(value);
                setManualProducts([]);
                setManualFeedback(null);
              }}
            />
            <Input
              style={{ width: 280 }}
              value={manualProductKeyword}
              placeholder="상품코드/바코드/상품명 검색"
              allowClear
              onChange={(event) => setManualProductKeyword(event.target.value)}
              onPressEnter={() => void searchManualProducts()}
            />
            <InputNumber
              min={1}
              value={manualQuantity}
              onChange={(value) => setManualQuantity(Number(value || 1))}
              addonBefore="수량"
            />
            <Button icon={<SearchOutlined />} loading={manualProductLoading} onClick={() => void searchManualProducts()}>
              상품 검색
            </Button>
          </Space>
          <Input
            ref={manualProductScanInputRef}
            size="large"
            prefix={<ScanOutlined />}
            allowClear
            disabled={!manualClientId || manualRowSaving}
            value={manualProductScanValue}
            placeholder={manualClientId ? "상품 바코드 스캔 후 Enter" : "고객사를 먼저 선택해야 상품을 추가할 수 있습니다."}
            onChange={(event) => setManualProductScanValue(event.target.value)}
            onPressEnter={handleManualProductScanEnter}
          />
          {manualFeedback ? (
            <Alert
              className="return-processing-placeholder"
              type={manualFeedback.type}
              showIcon
              message={manualFeedback.message}
              description={manualFeedback.description}
            />
          ) : null}
          {manualProducts.length > 0 ? (
            <List
              size="small"
              dataSource={manualProducts}
              renderItem={(product) => (
                <List.Item
                  actions={[
                    <Button
                      key="add"
                      size="small"
                      icon={<PlusOutlined />}
                      loading={manualRowSaving}
                      onClick={() => void createManualRowFromProduct(product, "MANUAL_QUANTITY")}
                    >
                      상품 추가
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={`${product.product_name} / ${product.product_code}`}
                    description={`바코드 ${product.barcode || "-"} · 고객사 ${product.client_name}`}
                  />
                </List.Item>
              )}
            />
          ) : null}
        </section>
      ) : null}

      <SmartErrorNotice message={errorMessage} />

      <div className="return-processing-workspace">
        <section className="return-processing-grid-panel" aria-label="반품처리 대기 대상">
          <SmartDataGrid<ReturnProcessingTask>
            rowKey="task_id"
            rows={tasks}
            columns={columns}
            loading={loading}
            error={null}
            emptyText={noDetailTrackingNo ? "아직 추가된 상품이 없습니다. 상품을 스캔하거나 검색해서 추가하세요." : "반품처리 대기 대상이 없습니다."}
            enableCopy
            exportFileName="반품처리"
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

        <aside className="return-processing-detail-panel" aria-label={selectedTask ? "선택 상품 처리" : "상품 추가 안내"}>
          <Typography.Title level={4}>{selectedTask ? "선택 상품 처리" : tasks.length > 0 ? "처리할 상품 선택" : "상품 추가 안내"}</Typography.Title>
          {!selectedTask && tasks.length === 0 ? (
            <Alert
              type="info"
              showIcon
              message="아직 추가된 상품이 없습니다."
              description={noDetailTrackingNo ? "상품을 스캔하거나 검색해서 추가하세요." : "운송장번호를 스캔하면 처리할 상품을 조회합니다."}
            />
          ) : null}
          {!selectedTask && tasks.length > 0 ? (
            <Alert type="info" showIcon message="처리할 상품을 선택하세요." description="목록에서 상품을 선택하면 판정/창고/처리완료 영역이 표시됩니다." />
          ) : null}
          {selectedTask ? (
          <div className="return-processing-product-scan" aria-label="상품 바코드 스캔">
            <Space align="center" wrap>
              <Typography.Text strong>상품 바코드 스캔</Typography.Text>
              <SmartStatusBadge status={toProductCheckBadgeStatus(productCheckFeedback.status)} label={toProductCheckLabel(productCheckFeedback.status)} />
              {selectedProcessingMethod ? (
                <SmartStatusBadge status="INFO" label={toProcessingMethodLabel(selectedProcessingMethod)} />
              ) : null}
            </Space>
            <Input
              ref={productScanInputRef}
              size="large"
              prefix={<ScanOutlined />}
              allowClear
              disabled={(!selectedTask && !noDetailTrackingNo) || selectedTask?.status === "COMPLETED" || manualRowSaving}
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
            <Space wrap>
              <Button
                onClick={handleGridSelectConfirm}
                disabled={!selectedTask || selectedTask.status === "COMPLETED"}
              >
                선택 상품 확인
              </Button>
              <Typography.Text type="secondary">
                스캔이 어려운 소량/예외 건은 목록에서 상품을 선택한 뒤 실물 확인으로 처리할 수 있습니다.
              </Typography.Text>
            </Space>
          </div>
          ) : null}
          {selectedTask ? (
            <>
              <Descriptions size="small" column={1} bordered>
                <Descriptions.Item label="반품 운송장번호">{toDisplayText(selectedTask.return_tracking_no)}</Descriptions.Item>
                <Descriptions.Item label="고객사">{toDisplayText(selectedTask.client_name)}</Descriptions.Item>
                <Descriptions.Item label="운영단위">{toDisplayText(selectedTask.client_unit_name)}</Descriptions.Item>
                <Descriptions.Item label="창고">{contextWarehouseLabel}</Descriptions.Item>
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
                <Descriptions.Item label="처리방식">
                  {selectedProcessingMethod ? toProcessingMethodLabel(selectedProcessingMethod) : "상품 스캔 또는 선택 확인 전"}
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
              <details className="return-processing-label-panel" aria-label="Local Agent 라벨 출력">
                <summary className="return-processing-collapse-summary">
                  <PrinterOutlined />
                  <Typography.Text strong>Local Agent 라벨 출력</Typography.Text>
                  <SmartStatusBadge status="WARNING" label="Local Agent 미연결" />
                </summary>
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
              </details>
              <section className="return-processing-judgement-panel" aria-label="판정/창고/처리완료">
                <Space align="center" wrap>
                  <Typography.Text strong>판정/창고</Typography.Text>
                  {selectedJudgement ? (
                    <SmartStatusBadge status="SUCCESS" label={toJudgementLabel(selectedJudgement)} />
                  ) : (
                    <SmartStatusBadge status="WAITING" label="미선택" />
                  )}
                  {returnWarehouseRoutes.length > 0 ? (
                    <SmartStatusBadge status="INFO" label="고객사 라우팅 기준" />
                  ) : (
                    <SmartStatusBadge status="WARNING" label="기본 판정 세트" />
                  )}
                </Space>
                <Space wrap className="return-processing-judgement-buttons">
                  {judgementOptions.map((option, index) => (
                    <Button
                      key={option.value}
                      type={selectedJudgement === option.value ? "primary" : "default"}
                      disabled={isSelectedTaskCompleted || judging}
                      onClick={() => {
                        const nextWarehouseRoute = findWarehouseRoute(returnWarehouseRoutes, selectedTask, option.value);
                        setSelectedJudgement(option.value);
                        setJudgementFeedback({
                          type: nextWarehouseRoute ? "info" : "warning",
                          message: `${option.label} 판정을 선택했습니다.`,
                          description: buildSelectedJudgementDescription(
                            option.value,
                            nextWarehouseRoute,
                            returnWarehouseRoutes.length,
                            routesErrorMessage,
                            routesLoading,
                          ),
                        });
                      }}
                    >
                      {index < 9 ? `${index + 1}. ` : ""}
                      {option.label}
                    </Button>
                  ))}
                </Space>
                <Input.TextArea
                  rows={2}
                  value={judgementMemo}
                  disabled={isSelectedTaskCompleted || judging}
                  placeholder="판정 메모를 입력하세요"
                  onChange={(event) => setJudgementMemo(event.target.value)}
                />
                {showHoldMemoWarning ? (
                  <Alert
                    className="return-processing-placeholder"
                    type="warning"
                    showIcon
                    message="보류 판정은 사유를 남기면 나중에 확인하기 쉽습니다."
                  />
                ) : null}
                <Alert
                  className="return-processing-placeholder"
                  type={judgementFeedback?.type || "info"}
                  showIcon
                  message={judgementFeedback?.message || getJudgementHelpMessage(selectedTask, productCheckFeedback.status, selectedJudgement)}
                  description={
                    judgementFeedback?.description ||
                    buildSelectedJudgementDescription(selectedJudgement, selectedWarehouseRoute, returnWarehouseRoutes.length, routesErrorMessage, routesLoading)
                  }
                />
                <Button type="primary" onClick={handleJudgementSave} disabled={!canSaveJudgement} loading={judging}>
                  처리완료
                </Button>
                {judgementFeedback?.type === "success" ? (
                  <Button type="link" size="small" onClick={() => navigate(ROUTE_PATHS.returnClosing)}>
                    일마감 화면으로 이동
                  </Button>
                ) : null}
                {selectedJudgement && !selectedWarehouseRoute?.warehouse_id ? (
                  <Space direction="vertical" size={2}>
                    <Typography.Text type="warning">
                      {buildWarehouseMissingGuidance(selectedJudgement, returnWarehouseRoutes.length)}
                    </Typography.Text>
                    {selectedTask?.client_id ? (
                      <Button
                        type="link"
                        size="small"
                        style={{ paddingLeft: 0 }}
                        onClick={() =>
                          window.open(`${ROUTE_PATHS.masterClients}/${selectedTask.client_id}`, "_blank", "noopener")
                        }
                      >
                        고객사 판정/창고 설정 열기
                      </Button>
                    ) : null}
                  </Space>
                ) : null}
              </section>
              <details className="return-processing-attachments-panel" aria-label="사진/증빙">
                <summary className="return-processing-collapse-summary">
                  <PaperClipOutlined />
                  <Typography.Text strong>사진/증빙</Typography.Text>
                  <SmartStatusBadge status="WAITING" label="선택 사항" />
                </summary>
                <Typography.Text type="secondary">
                  필요한 경우 사진을 첨부하세요. 사진이 없어도 처리완료는 가능합니다.
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
              </details>
              <Alert
                className="return-processing-placeholder return-processing-inventory-notice"
                type="info"
                showIcon
                message="재고는 아직 변경되지 않습니다. 일마감 화면에서 확정 후 재고에 반영됩니다."
              />
            </>
          ) : null}
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
    DEFECTIVE: "불량",
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
  if (task.source_type === "NO_DETAIL_MANUAL_INTAKE") {
    return "현장 수동 처리";
  }
  if (task.source_type === "UNKNOWN_TRACKING_MANUAL_INTAKE") {
    return "운송장 수동 처리";
  }
  if (task.source_type === "MANUAL") {
    return "수동/업로드";
  }
  return task.source_type ? "접수자료" : "수동/업로드";
}

function toProcessingModeLabel(task: ReturnProcessingTask) {
  const processingMode = String((task as { processing_mode?: string }).processing_mode || task.source_type || "");
  const labels: Record<string, string> = {
    NORMAL_MATCHED: "자료 매칭 처리",
    NO_DETAIL_MANUAL_INTAKE: "현장 수동 처리",
    UNKNOWN_TRACKING_MANUAL_INTAKE: "운송장 수동 처리",
    CHANNEL_API: "채널 수집 처리",
    MANUAL: "수동/업로드 처리",
  };
  return labels[processingMode] || toSourceLabel(task);
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

function isShortcutInputTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  const tagName = target.tagName.toLowerCase();
  return tagName === "input" || tagName === "textarea" || tagName === "select" || target.isContentEditable;
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
    return "추적 대상 판정입니다. 저장 시 반품관리번호/라벨번호를 생성하고, 고객사별 판정-창고 라우팅 기준의 추천 창고를 함께 반영합니다.";
  }
  if (judgementStatus === "DISPOSAL") {
    return "폐기는 1차 정책에서 기본 라벨 미출력 대상입니다. 필요 시 후속 정책으로 선택 출력 여부를 정합니다.";
  }
  return "양품은 기본 라벨 미출력 대상입니다. 재고는 처리완료 즉시가 아니라 일마감 확정 후 반영됩니다.";
}

function buildSelectedJudgementDescription(
  judgementStatus: ReturnJudgementStatus | null,
  route: ReturnWarehouseRoute | null,
  routeCount: number,
  routeErrorMessage: string,
  routesLoading: boolean,
) {
  if (!judgementStatus) {
    return "상품 스캔 또는 선택 처리 확인 후 판정과 창고를 확정하세요.";
  }
  if (routesLoading) {
    return "고객사별 판정-창고 라우팅 설정을 확인하는 중입니다.";
  }
  if (routeErrorMessage) {
    return `${routeErrorMessage} 현재는 기본 판정 세트를 표시합니다. 일마감 시 최종 창고가 없으면 재고반영이 차단됩니다.`;
  }
  if (route) {
    return `${buildLabelPolicyDescription(judgementStatus)} 배정 창고: ${route.warehouse_name || route.warehouse_code || "창고 확인됨"}.`;
  }
  // 판정 직후 피드백은 짧게만 알리고, 원인/해결 상세는 처리완료 가드 영역에서 한 번만 안내한다.
  return `'${toJudgementLabel(judgementStatus)}' 판정에 사용할 창고가 아직 설정되지 않았습니다. 처리완료 버튼 아래 안내를 확인하세요.`;
}

/**
 * 창고 미확정 원인별 상세 안내(처리완료 가드 전용). backend는 판정 코드 →
 * 고객사 판정-창고 라우팅으로만 창고를 결정하므로(판정 저장 API에 창고 직접 지정 필드 없음)
 * 화면에서 임의 창고를 고를 수 없다. 원인 → 해결 → 결과 순으로 안내한다.
 */
function buildWarehouseMissingGuidance(judgementStatus: ReturnJudgementStatus, routeCount: number) {
  const judgementLabel = toJudgementLabel(judgementStatus);
  if (routeCount === 0) {
    return "이 고객사는 판정-창고 라우팅이 등록되어 있지 않습니다. 고객사 관리에서 창고와 판정별 기본 창고를 먼저 등록하세요.";
  }
  return `'${judgementLabel}' 판정에 사용할 창고가 설정되어 있지 않습니다. 고객사 관리 > 판정/창고 라우팅에서 '${judgementLabel}' 창고를 지정하면 처리완료할 수 있습니다.`;
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
    return "상품 스캔 또는 그리드 선택 확인 후 판정할 수 있습니다.";
  }
  if (!judgementStatus) {
    return "판정을 선택하세요.";
  }
  return "처리완료할 수 있습니다. 완료 후에도 현재고는 즉시 변경되지 않습니다.";
}

function buildJudgementSavedDescription(task: ReturnProcessingTask) {
  const labelNo = task.return_label_no || task.return_management_no;
  const inventoryNotice = "현재고는 즉시 변경하지 않고 일마감/반출 확정 단계에서 반영합니다.";
  if (task.label_print_required) {
    return labelNo
      ? `반품관리번호/라벨번호 ${labelNo}가 생성되었습니다. ${toLabelStatusLabel(task)} 상태입니다. ${inventoryNotice}`
      : `${toLabelStatusLabel(task)} 상태입니다. ${inventoryNotice}`;
  }
  return `라벨 출력 대상이 아니며 처리 완료로 표시했습니다. ${inventoryNotice}`;
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
      description: "선택 상품에 비교할 바코드/상품코드가 없습니다. 실물과 접수 자료를 확인한 뒤 선택 처리로 진행할 수 있습니다.",
    };
  }

  return {
    status: "PENDING",
    type: "info",
    message: "선택된 상품을 확인하세요.",
    description: "선택된 반품 상품의 바코드 또는 상품코드를 스캔하세요.",
  };
}

function buildJudgementOptions(routes: ReturnWarehouseRoute[]) {
  const activeCodes = Array.from(
    new Set(routes.filter((route) => route.active_yn).map((route) => route.judgment_code.trim().toUpperCase())),
  );
  const routeOptions = activeCodes
    .map((code) => JUDGEMENT_OPTIONS.find((option) => option.value === code))
    .filter((option): option is { value: ReturnJudgementStatus; label: string } => Boolean(option));
  return routeOptions.length > 0 ? routeOptions : JUDGEMENT_OPTIONS;
}

function findWarehouseRoute(
  routes: ReturnWarehouseRoute[],
  task: ReturnProcessingTask | null,
  judgementStatus: ReturnJudgementStatus | null,
) {
  if (!task || !judgementStatus) {
    return null;
  }
  const matched = routes.filter(
    (route) =>
      route.active_yn &&
      route.judgment_code.trim().toUpperCase() === judgementStatus &&
      (!route.client_unit_id || route.client_unit_id === task.client_unit_id),
  );
  return matched.find((route) => route.client_unit_id === task.client_unit_id) || matched[0] || null;
}

function hasAnyProductHint(task: ReturnProcessingTask) {
  return Boolean(task.product_code || task.barcode || task.product_name);
}

function toProcessingMethodLabel(method: ProcessingMethod) {
  const labels: Record<ProcessingMethod, string> = {
    SCAN: "스캔 처리",
    GRID_SELECT: "선택 처리",
    MANUAL_QUANTITY: "수량 직접 입력",
    BULK_CONFIRM: "일괄 확인",
  };
  return labels[method];
}

function buildJudgementMemoForSave(memo: string, method: ProcessingMethod) {
  const cleanMemo = memo
    .replace(/\[처리방식: (SCAN|GRID_SELECT|MANUAL_QUANTITY|BULK_CONFIRM|스캔 처리|선택 처리|수량 직접 입력|일괄 확인)\]/g, "")
    .trim();
  const methodTag = `[처리방식: ${toProcessingMethodLabel(method)}]`;
  return cleanMemo ? `${cleanMemo}\n${methodTag}` : methodTag;
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

function pickPreferredProcessingTask(items: ReturnProcessingTask[], preferredTaskId?: number) {
  return (
    items.find((item) => item.task_id === preferredTaskId) ||
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
      message: "세부항목 없는 반품입니다.",
      description: "상품을 스캔하거나 검색해서 현장 처리 상품을 추가한 뒤 판정하세요.",
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

function getClientOptionId(client: ClientSummary) {
  return Number(client.client_id ?? client.id);
}
