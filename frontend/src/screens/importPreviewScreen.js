import {
  createImportJob,
  listImportJobErrors,
  listImportJobRows,
  savePasteRows,
  validateImportJob,
} from "../api/importJobs.js";
import { listClients } from "../api/master.js";
import { ApiClientError, getStoredApiBaseUrl, hasAccessToken, setStoredApiBaseUrl } from "../lib/apiClient.js";

const IMPORT_TYPES = ["PRODUCT_MASTER", "PRODUCT_BARCODE"];
const SOURCE_TYPES = ["PASTE", "MANUAL"];
const STATUS_LABELS = {
  DRAFT: "작성 중",
  READY_TO_VALIDATE: "검증 대기",
  VALIDATING: "검증 중",
  VALIDATED: "검증 완료",
  HAS_ERRORS: "오류 있음",
  FAILED: "실패",
};
const VALIDATION_LABELS = {
  VALID: "정상",
  WARNING: "경고",
  INVALID: "오류",
  NOT_VALIDATED: "검증 전",
};
const ERROR_MESSAGES = {
  NOT_AUTHENTICATED: "로그인이 필요합니다. 기존 인증 화면에서 다시 로그인해 주세요.",
  INVALID_TOKEN: "로그인 정보가 만료되었거나 올바르지 않습니다. 다시 로그인해 주세요.",
  IMPORT_JOB_NOT_FOUND: "Import job을 찾을 수 없습니다.",
  IMPORT_JOB_VALIDATE_ALREADY_DONE: "이미 검증이 완료된 자료입니다.",
  IMPORT_JOB_VALIDATE_FORCE_UNSUPPORTED: "강제 재검증은 아직 지원하지 않습니다.",
  IMPORT_JOB_VALIDATE_SOURCE_TYPE_INVALID: "현재 source_type에서는 검증을 실행할 수 없습니다.",
  IMPORT_JOB_VALIDATE_STATUS_INVALID: "현재 상태에서는 검증을 실행할 수 없습니다.",
  IMPORT_JOB_VALIDATE_NO_ROWS: "검증할 row가 없습니다.",
  API_BASE_URL_REQUIRED: "API 서버 주소를 입력해 주세요.",
};

export function mountImportPreviewScreen(root) {
  const state = {
    apiBaseUrl: getStoredApiBaseUrl(),
    clients: [],
    selectedClientId: "",
    importType: "PRODUCT_MASTER",
    sourceType: "PASTE",
    pasteText: "",
    parsedRows: [],
    job: null,
    rows: [],
    errors: [],
    validationSummary: null,
    filter: "ALL",
    isLoadingClients: false,
    isSavingRows: false,
    isValidating: false,
    notice: "",
    error: "",
  };

  root.innerHTML = `
    <section class="page-shell">
      <header class="work-header">
        <div>
          <p class="eyebrow">SmartReturn Pro</p>
          <h1>Import Preview Skeleton</h1>
        </div>
        <div class="auth-hint" data-role="auth-hint"></div>
      </header>

      <section class="toolbar" aria-label="import preview controls">
        <label>
          API 서버
          <input data-field="apiBaseUrl" type="url" placeholder="API 서버 주소 입력" />
        </label>
        <label>
          고객사
          <select data-field="clientId"></select>
        </label>
        <label>
          import_type
          <select data-field="importType"></select>
        </label>
        <label>
          source_type
          <select data-field="sourceType"></select>
        </label>
        <div class="status-chip" data-role="job-status">작성 중</div>
      </section>

      <section class="work-band input-band">
        <div class="section-heading">
          <h2>붙여넣기 입력</h2>
          <p>첫 행은 header로 사용한다. 예: product_code, product_name, barcode, unit_qty</p>
        </div>
        <textarea data-field="pasteText" spellcheck="false" placeholder="product_code\tproduct_name\tbarcode&#10;LOCAL-001\t테스트 상품\t880000000001"></textarea>
        <div class="inline-actions">
          <button type="button" data-action="resetPaste">붙여넣기 초기화</button>
          <button type="button" data-action="saveRows">미리보기/행 저장</button>
          <button type="button" data-action="validate">검증 실행</button>
        </div>
      </section>

      <section class="summary-grid" data-role="summary"></section>

      <section class="work-band grid-band">
        <div class="section-heading">
          <h2>Preview Grid</h2>
          <p>기본 정렬은 원본 row_no asc 기준이다.</p>
        </div>
        <div class="filter-bar">
          <button type="button" data-filter="ALL">전체 보기</button>
          <button type="button" data-filter="ERROR">오류 행만 보기</button>
          <button type="button" data-filter="WARNING">경고 행만 보기</button>
          <button type="button" data-filter="ORIGINAL">원본 순서 보기</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>행번호</th>
                <th>상태</th>
                <th>오류/경고</th>
                <th>product_code</th>
                <th>product_name</th>
                <th>barcode</th>
                <th>barcode_type</th>
                <th>unit_qty</th>
                <th>처리 메시지</th>
              </tr>
            </thead>
            <tbody data-role="rows"></tbody>
          </table>
        </div>
      </section>

      <section class="work-band detail-band">
        <div class="section-heading">
          <h2>오류/경고 상세</h2>
          <p>errors 조회 결과를 row_no 기준으로 연결한다.</p>
        </div>
        <div class="error-list" data-role="errors"></div>
      </section>

      <div class="message-area" data-role="message"></div>

      <footer class="action-bar">
        <span data-role="flow-hint">다음 단계 진행은 skeleton에서 비활성 상태다.</span>
        <button type="button" disabled>다음 단계 진행 준비중</button>
      </footer>
    </section>
  `;

  const refs = {
    apiBaseUrl: root.querySelector('[data-field="apiBaseUrl"]'),
    clientId: root.querySelector('[data-field="clientId"]'),
    importType: root.querySelector('[data-field="importType"]'),
    sourceType: root.querySelector('[data-field="sourceType"]'),
    pasteText: root.querySelector('[data-field="pasteText"]'),
    authHint: root.querySelector('[data-role="auth-hint"]'),
    jobStatus: root.querySelector('[data-role="job-status"]'),
    summary: root.querySelector('[data-role="summary"]'),
    rows: root.querySelector('[data-role="rows"]'),
    errors: root.querySelector('[data-role="errors"]'),
    message: root.querySelector('[data-role="message"]'),
    saveRows: root.querySelector('[data-action="saveRows"]'),
    validate: root.querySelector('[data-action="validate"]'),
    resetPaste: root.querySelector('[data-action="resetPaste"]'),
  };

  refs.apiBaseUrl.value = state.apiBaseUrl;
  renderSelectOptions(refs.importType, IMPORT_TYPES, state.importType);
  renderSelectOptions(refs.sourceType, SOURCE_TYPES, state.sourceType);

  refs.apiBaseUrl.addEventListener("change", () => {
    state.apiBaseUrl = setStoredApiBaseUrl(refs.apiBaseUrl.value);
    refs.apiBaseUrl.value = state.apiBaseUrl;
    render(state, refs);
  });
  refs.clientId.addEventListener("change", () => {
    state.selectedClientId = refs.clientId.value;
    render(state, refs);
  });
  refs.importType.addEventListener("change", () => {
    state.importType = refs.importType.value;
    resetJobState(state);
    render(state, refs);
  });
  refs.sourceType.addEventListener("change", () => {
    state.sourceType = refs.sourceType.value;
    resetJobState(state);
    render(state, refs);
  });
  refs.pasteText.addEventListener("input", () => {
    state.pasteText = refs.pasteText.value;
    state.parsedRows = parsePasteRows(state.pasteText);
    render(state, refs);
  });
  refs.resetPaste.addEventListener("click", () => {
    state.pasteText = "";
    state.parsedRows = [];
    resetJobState(state);
    refs.pasteText.value = "";
    render(state, refs);
  });
  refs.saveRows.addEventListener("click", () => runSaveRows(state, refs));
  refs.validate.addEventListener("click", () => runValidate(state, refs));
  root.querySelectorAll("[data-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      const nextFilter = button.getAttribute("data-filter");
      state.filter = nextFilter === "ORIGINAL" ? "ALL" : nextFilter;
      render(state, refs);
    });
  });

  loadClients(state, refs);
  render(state, refs);
}

async function loadClients(state, refs) {
  state.isLoadingClients = true;
  state.error = "";
  render(state, refs);
  try {
    state.clients = await listClients();
    const activeClient = state.clients.find((client) => client.active_yn);
    state.selectedClientId = activeClient ? String(activeClient.client_id) : "";
  } catch (error) {
    setSafeError(state, error);
  } finally {
    state.isLoadingClients = false;
    render(state, refs);
  }
}

async function runSaveRows(state, refs) {
  state.isSavingRows = true;
  state.error = "";
  state.notice = "";
  render(state, refs);
  try {
    const job = await createImportJob({
      import_type: state.importType,
      source_type: state.sourceType,
      requested_client_id: Number(state.selectedClientId),
      source_name: "frontend-preview-skeleton",
    });
    const jobId = getJobId(job);
    await savePasteRows(jobId, {
      rows: state.parsedRows.map((row) => ({
        raw_json: row.raw_json,
        normalized_json: row.normalized_json || null,
        source_row_key: row.source_row_key || null,
      })),
      replace_existing: false,
      source_name: "frontend-preview-skeleton",
    });
    state.job = { ...job, status: "READY_TO_VALIDATE", total_rows: state.parsedRows.length, parsed_rows: state.parsedRows.length };
    await refreshRowsAndErrors(state, jobId);
    state.notice = "rows 저장이 완료되었습니다. 검증을 실행할 수 있습니다.";
  } catch (error) {
    setSafeError(state, error);
  } finally {
    state.isSavingRows = false;
    render(state, refs);
  }
}

async function runValidate(state, refs) {
  if (!state.job) {
    return;
  }
  state.isValidating = true;
  state.error = "";
  state.notice = "";
  render(state, refs);
  try {
    const jobId = getJobId(state.job);
    const summary = await validateImportJob(jobId);
    state.validationSummary = summary;
    state.job = { ...state.job, ...summary, job_id: jobId };
    await refreshRowsAndErrors(state, jobId);
    state.notice = "검증이 완료되었습니다.";
  } catch (error) {
    setSafeError(state, error);
  } finally {
    state.isValidating = false;
    render(state, refs);
  }
}

async function refreshRowsAndErrors(state, jobId) {
  const [rowsResult, errorsResult] = await Promise.all([listImportJobRows(jobId), listImportJobErrors(jobId)]);
  state.rows = [...(rowsResult.items || [])].sort((left, right) => left.row_no - right.row_no);
  state.errors = [...(errorsResult.items || [])].sort((left, right) => (left.row_no || 0) - (right.row_no || 0) || left.error_id - right.error_id);
}

function render(state, refs) {
  refs.authHint.textContent = hasAccessToken() ? "인증 정보 감지됨" : "기존 인증 토큰 필요";
  refs.clientId.innerHTML = state.isLoadingClients
    ? '<option value="">고객사 불러오는 중</option>'
    : '<option value="">고객사 선택</option>' +
      state.clients
        .filter((client) => client.active_yn)
        .map((client) => `<option value="${client.client_id}">${escapeHtml(client.client_code)} · ${escapeHtml(client.client_name)}</option>`)
        .join("");
  refs.clientId.value = state.selectedClientId;
  refs.jobStatus.textContent = getStatusLabel(state.job?.status || "DRAFT");
  refs.jobStatus.dataset.status = state.job?.status || "DRAFT";

  const canSaveRows = Boolean(state.selectedClientId && state.importType && state.pasteText.trim() && state.parsedRows.length > 0 && !state.job);
  const canValidate = Boolean(state.job?.status === "READY_TO_VALIDATE" && state.rows.length > 0 && !state.isValidating);
  refs.saveRows.disabled = !canSaveRows || state.isSavingRows || state.isValidating;
  refs.validate.disabled = !canValidate || state.isSavingRows || state.isValidating;
  refs.resetPaste.disabled = state.isSavingRows || state.isValidating || (!state.pasteText && !state.job);

  refs.summary.innerHTML = renderSummary(state);
  refs.rows.innerHTML = renderRows(state);
  refs.errors.innerHTML = renderErrors(state);
  refs.message.innerHTML = renderMessage(state);
}

function renderSummary(state) {
  const warningRows = countWarningRows(state.errors);
  const values = [
    ["전체 행", state.job?.total_rows ?? state.rows.length ?? 0],
    ["정상 행", state.validationSummary?.valid_rows ?? state.job?.valid_rows ?? 0],
    ["경고 행", state.validationSummary?.warning_rows ?? warningRows],
    ["오류 행", state.validationSummary?.invalid_rows ?? state.job?.invalid_rows ?? 0],
    ["오류 발생 행", state.validationSummary?.error_rows ?? state.job?.error_rows ?? 0],
    ["진행률", `${state.validationSummary?.progress_percent ?? state.job?.progress_percent ?? 0}%`],
    ["job status", getStatusLabel(state.job?.status || "DRAFT")],
    ["import_type", state.importType],
    ["source_type", state.sourceType],
  ];
  return values
    .map(
      ([label, value]) => `
        <div class="summary-item">
          <span>${label}</span>
          <strong>${escapeHtml(String(value))}</strong>
        </div>
      `,
    )
    .join("");
}

function renderRows(state) {
  const rows = getFilteredRows(state);
  if (rows.length === 0) {
    return '<tr><td colspan="9" class="empty-cell">표시할 row가 없습니다.</td></tr>';
  }
  return rows
    .map((row) => {
      const rowData = row.normalized_json || row.raw_json || {};
      const rowErrors = state.errors.filter((error) => error.row_id === row.row_id || error.row_no === row.row_no);
      return `
        <tr>
          <td>${row.row_no}</td>
          <td><span class="validation-badge" data-status="${escapeHtml(row.validation_status)}">${getValidationLabel(row.validation_status)}</span></td>
          <td>${rowErrors.length}</td>
          <td>${escapeHtml(rowData.product_code)}</td>
          <td>${escapeHtml(rowData.product_name)}</td>
          <td>${escapeHtml(rowData.barcode)}</td>
          <td>${escapeHtml(rowData.barcode_type)}</td>
          <td>${escapeHtml(rowData.unit_qty)}</td>
          <td>${escapeHtml(row.validation_message || summarizeErrors(rowErrors))}</td>
        </tr>
      `;
    })
    .join("");
}

function renderErrors(state) {
  if (state.errors.length === 0) {
    return '<p class="empty-note">표시할 오류/경고가 없습니다.</p>';
  }
  return state.errors
    .map(
      (error) => `
        <article class="error-item" data-severity="${escapeHtml(error.severity)}">
          <strong>${escapeHtml(error.severity)} · row ${escapeHtml(error.row_no)}</strong>
          <span>${escapeHtml(error.error_code)}</span>
          <p>${escapeHtml(error.error_message)}</p>
        </article>
      `,
    )
    .join("");
}

function renderMessage(state) {
  if (state.error) {
    return `<div class="message error-message">${escapeHtml(state.error)}</div>`;
  }
  if (state.notice) {
    return `<div class="message notice-message">${escapeHtml(state.notice)}</div>`;
  }
  return "";
}

function getFilteredRows(state) {
  const rows = [...state.rows].sort((left, right) => left.row_no - right.row_no);
  if (state.filter === "ERROR") {
    return rows.filter((row) => row.validation_status === "INVALID");
  }
  if (state.filter === "WARNING") {
    return rows.filter((row) => row.validation_status === "WARNING");
  }
  return rows;
}

function parsePasteRows(text) {
  const trimmed = text.trim();
  if (!trimmed) {
    return [];
  }
  try {
    const parsed = JSON.parse(trimmed);
    if (Array.isArray(parsed)) {
      return parsed.map((item, index) => ({ raw_json: item, source_row_key: `row-${index + 1}` }));
    }
  } catch {
    // Continue with delimited text parsing.
  }

  const lines = trimmed.split(/\r?\n/).filter((line) => line.trim());
  if (lines.length < 2) {
    return [];
  }
  const delimiter = lines[0].includes("\t") ? "\t" : ",";
  const headers = lines[0].split(delimiter).map((header) => header.trim());
  return lines.slice(1).map((line, index) => {
    const values = line.split(delimiter);
    const rawJson = {};
    headers.forEach((header, headerIndex) => {
      rawJson[header] = (values[headerIndex] || "").trim();
    });
    return { raw_json: rawJson, source_row_key: `row-${index + 1}` };
  });
}

function setSafeError(state, error) {
  if (error instanceof ApiClientError) {
    state.error = ERROR_MESSAGES[error.resultCode] || `${error.resultCode}: ${error.message}`;
    return;
  }
  state.error = "일반 서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
}

function renderSelectOptions(select, options, selectedValue) {
  select.innerHTML = options.map((value) => `<option value="${value}">${value}</option>`).join("");
  select.value = selectedValue;
}

function resetJobState(state) {
  state.job = null;
  state.rows = [];
  state.errors = [];
  state.validationSummary = null;
  state.notice = "";
  state.error = "";
}

function getJobId(job) {
  return job.job_id || job.id;
}

function getStatusLabel(status) {
  return STATUS_LABELS[status] || status;
}

function getValidationLabel(status) {
  return VALIDATION_LABELS[status] || status || "검증 전";
}

function countWarningRows(errors) {
  return new Set(errors.filter((error) => error.severity === "WARNING").map((error) => error.row_id || error.row_no)).size;
}

function summarizeErrors(errors) {
  if (errors.length === 0) {
    return "";
  }
  return errors.map((error) => error.error_code).join(", ");
}

function escapeHtml(value) {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
