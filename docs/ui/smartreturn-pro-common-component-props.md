# SmartReturn Pro 공통 UI 컴포넌트 props/상태 설계

이 문서는 SmartReturn Pro 신규 제작 기준이며, 기존 SmartReturn 구현기록을 그대로 따르지 않는다.

이 문서는 실제 React 코드가 아니다. 실제 컴포넌트 구현 전에 공통 UI 컴포넌트의 책임, props 후보, 상태 처리 기준, 사용 금지 기준을 고정하기 위한 기준 문서다.

## 공통 컴포넌트 설계 원칙

- 화면별 임시 table, input, button, modal, card를 새로 만들지 않는다.
- 반복되는 UI 문제는 화면별 CSS 땜질이 아니라 공통 컴포넌트 개선으로 해결한다.
- 업무 화면에서 `AgGridReact`를 직접 사용하지 않는다.
- 저장자료, 목록, 이력은 `SmartDataGrid`를 사용한다.
- 직접 입력, 수정, 붙여넣기 편집은 `SmartEditableDataGrid`를 사용한다.
- 엑셀 원본 preview와 매핑 확인은 `SmartExcelPreviewGrid`를 사용한다.
- 현장 스캔 입력은 `SmartScanPanel`을 사용한다.
- 우측 정보패널은 `SmartInfoPanel`을 사용한다.
- 하단 액션바는 `SmartActionBar`를 사용한다.
- 모달은 `SmartModalShell`을 사용한다.
- 고객사, 상품, 창고, 공통코드 선택은 `SmartLookupModal` 또는 `SmartCommonCodeSelect` 계열을 사용한다.
- 버튼이 아닌 카드/정보패널은 버튼처럼 보이면 안 된다.
- 클릭 가능한 요소만 hover와 `cursor:pointer`를 사용한다.

## SmartWorkLayout

### 목적

- SmartReturn Pro 업무 화면의 표준 레이아웃 shell이다.
- 좌측 작업 메뉴, 상단 작업바, 중앙 메인 영역, 우측 정보패널, 하단 액션바를 안정적으로 배치한다.

### props 후보

- `title`
- `subtitle`
- `leftNav`
- `toolbar`
- `main`
- `infoPanel`
- `actionBar`
- `statusBar`
- `layoutType`
- `density`
- `minWidth`
- `rightPanelWidth`
- `leftPanelWidth`
- `loading`
- `error`
- `className`

### `layoutType` 후보

- `dashboard`
- `adminList`
- `uploadValidation`
- `workerScan`
- `judgement`
- `closingCompare`

### 상태 처리

- `loading`이면 중앙 `main` 영역에만 로딩 표시한다.
- `error`이면 전체 화면을 덮지 말고 `SmartErrorNotice` 후보로 표시한다.
- `infoPanel`이 없어도 중앙 `main`이 정상 확장되어야 한다.
- `actionBar`는 하단에 항상 보이게 한다.

### 금지

- 우측 `infoPanel`이 중앙 `main` 위에 겹치면 안 된다.
- 페이지 전체 가로 스크롤을 만들면 안 된다.
- `actionBar`가 `main` 영역을 덮으면 안 된다.

## SmartPage / SmartPageHeader

### 목적

- 화면 제목, 설명, 현재 위치, 주요 상태를 통일한다.

### SmartPage props 후보

- `title`
- `children`
- `className`
- `loading`
- `error`

### SmartPageHeader props 후보

- `title`
- `subtitle`
- `breadcrumb`
- `statusBadge`
- `actions`
- `compact`
- `rightExtra`

### 규칙

- 제목은 사용자 업무명 기준으로 한글 표시한다.
- 개발자용 module key를 제목으로 표시하지 않는다.
- header 높이가 과도하게 커져 그리드를 밀어내면 실패다.
- 주요 액션은 `SmartActionBar` 또는 `toolbar`에 배치하고, header에 너무 많이 넣지 않는다.

## SmartFilterPanel

### 목적

- 고객사, 창고, 기간, 상태, 검색어 같은 조회 조건을 통일한다.

### props 후보

- `fields`
- `values`
- `onChange`
- `onSearch`
- `onReset`
- `actions`
- `compact`
- `columns`
- `disabled`
- `loading`

### field 후보

- `client`
- `warehouse`
- `dateRange`
- `date`
- `status`
- `keyword`
- `commonCode`
- `custom`

### 규칙

- 상단 조건영역은 1~2줄을 우선한다.
- 고객사/창고 선택은 공통 lookup/select를 사용한다.
- 조회/초기화 버튼은 항상 보이게 한다.
- 긴 안내문을 filter panel 안에 넣지 않는다.
- 필터가 중앙 그리드보다 커지면 실패다.

## SmartDataGrid

### 목적

- 저장된 업무 데이터 목록, 조회 결과, 이력, 상세 목록을 표시한다.

### props 후보

- `rows`
- `columns`
- `rowKey`
- `loading`
- `error`
- `selectedRowKey`
- `onRowClick`
- `onRowDoubleClick`
- `onSelectionChange`
- `page`
- `pageSize`
- `totalCount`
- `onPageChange`
- `onPageSizeChange`
- `emptyMessage`
- `getRowClassName`
- `heightMode`
- `showFooter`
- `enableFilter`
- `enableSort`
- `enableColumnResize`
- `enableExcelDownload`
- `className`

### 상태 처리

- `loading`
- `empty`
- `error`
- `selected`
- disabled row
- warning row
- error row

### 규칙

- 서버 `totalCount` 기준으로 페이지를 표시한다.
- `rows.length`를 전체 건수처럼 표시하지 않는다.
- 그리드 내부 세로/가로 스크롤을 사용한다.
- 페이지 전체 가로 스크롤을 만들지 않는다.
- 핵심 버튼을 그리드 가로 스크롤 뒤에 넣지 않는다.
- 업무 화면에서 `AgGridReact`를 직접 import하지 않는다.

## SmartEditableDataGrid

### 목적

- 엑셀 붙여넣기, 직접 입력, 검증 전 row 편집을 처리한다.

### props 후보

- `rows`
- `columns`
- `rowKey`
- `onRowsChange`
- `pasteEnabled`
- `editable`
- `validationErrors`
- `selectedCell`
- `onCellChange`
- `onPaste`
- `onValidate`
- `addRowEnabled`
- `deleteRowEnabled`
- `emptyMessage`

### 규칙

- `textarea` 기반 엑셀 붙여넣기는 신규 화면에서 사용하지 않는다.
- 붙여넣은 원본 row 순서를 보존한다.
- 오류 셀과 경고 셀을 시각적으로 구분한다.
- 저장 확정 전 preview/validation 단계에서 사용한다.
- 업무 확정 데이터 조회에는 `SmartDataGrid`를 사용한다.

## SmartExcelPreviewGrid

### 목적

- 엑셀 업로드 전 원본 preview와 컬럼 매핑 확인을 표시한다.

### props 후보

- `rows`
- `columns`
- `rowKey`
- `showRowNumber`
- `getRowClassName`
- `maxHeight`
- `emptyMessage`
- `stickyHeader`
- `horizontalScroll`
- `onRowClick`
- `renderCell`

### 규칙

- 헤더는 sticky로 유지한다.
- 셀은 nowrap, ellipsis 기준으로 표시한다.
- 원본 `row_no`를 보존하고 보여줄 수 있어야 한다.
- 미리보기/매핑 화면의 핵심 영역을 차지해야 한다.
- 우측 정보패널이 preview grid를 과도하게 줄이면 실패다.
- 업로드 전 preview 전용이며, 저장된 업무 목록에는 사용하지 않는다.

## SmartScanPanel

### 목적

- 운송장, 상품바코드, 반품관리번호, 시리얼 등 현장 스캔 입력을 통일한다.

### props 후보

- `title`
- `scanValue`
- `onScanValueChange`
- `onSubmit`
- `placeholder`
- `autoFocus`
- `disabled`
- `lastResult`
- `soundCode`
- `status`
- `helperText`
- `inputMode`
- `size`
- `nextFocusTarget`
- `recentLogs`

### `inputMode` 후보

- `waybill`
- `productBarcode`
- `returnUnitNo`
- `serialNo`
- `location`
- `generic`

### `lastResult` 후보

- `result_code`
- `message`
- `sound_code`
- `scanned_value`
- `matched_name`
- `applied_qty`
- `created_at`

### 규칙

- 현장 작업자 화면에서는 입력창이 크고 명확해야 한다.
- Enter 처리 후 입력값은 clear되어야 한다.
- 스캔 후 포커스가 유지되어야 한다.
- 오류 메시지는 입력창 근처에 즉시 표시한다.
- 정상/오류/초과/중복/완료 `sound_code` 연결을 고려한다.
- 안내문이 스캔 입력을 밀어내면 실패다.

## SmartInfoPanel

### 목적

- 우측 정보패널의 구조를 통일한다.

### props 후보

- `title`
- `subtitle`
- `sections`
- `actions`
- `status`
- `width`
- `loading`
- `emptyMessage`
- `footer`

### section 후보

- `key`
- `title`
- `content`
- `status`
- `collapsible`
- `defaultOpen`

### 규칙

- 우측 패널은 보조 정보와 현재 선택 항목의 상세를 보여준다.
- 중앙 그리드/작업영역을 침범하지 않는다.
- 클릭 불가능한 정보패널은 버튼처럼 보이면 안 된다.
- 수정/확정 같은 핵심 액션을 우측 패널 안에만 숨기지 않는다.
- 작업자 화면에서는 판정/사진/메모처럼 현재 작업에 직접 필요한 요소만 둔다.

## SmartActionBar

### 목적

- 현재 단계의 핵심 버튼과 상태를 하단에 고정한다.

### props 후보

- `left`
- `center`
- `right`
- `primaryAction`
- `secondaryActions`
- `dangerActions`
- `statusText`
- `disabled`
- `loading`

### action 후보

- `key`
- `label`
- `variant`
- `icon`
- `disabled`
- `loading`
- `onClick`
- `confirmRequired`

### `variant` 후보

- `primary`
- `secondary`
- `softPrimary`
- `danger`
- `ghost`

### 규칙

- 저장/확정/완료 같은 최종 액션은 오른쪽에 둔다.
- `primary`는 화면당 1~2개만 사용한다.
- 위험 동작은 `danger`로 구분한다.
- 핵심 버튼이 스크롤 아래로 밀리면 실패다.
- 하단 action bar가 그리드를 덮으면 실패다.

## SmartModalShell

### 목적

- 공통 모달의 크기, 헤더, body, footer, 버튼 위치를 통일한다.

### props 후보

- `open`
- `title`
- `subtitle`
- `width`
- `size`
- `children`
- `footer`
- `onClose`
- `closeDisabled`
- `confirmOnClose`
- `loading`
- `error`

### `size` 후보

- `sm`
- `md`
- `lg`
- `xl`
- `fullscreenCandidate`

### 규칙

- header는 고정한다.
- footer는 고정한다.
- body만 스크롤한다.
- 취소/닫기는 왼쪽 또는 보조 영역에 둔다.
- 저장/선택/확정은 오른쪽에 둔다.
- 배경 클릭으로 닫히지 않게 한다.
- 입력 중 변경사항이 있으면 닫기 전 확인을 둔다.
- 화면마다 모달 크기와 버튼 위치가 제각각이면 실패다.

## SmartLookupModal / SmartLookupInput

### 목적

- 고객사, 상품, 창고, 공통코드, 택배사, 반품소스, 판정사유, 보류사유 등 코드성 선택을 통일한다.

### props 후보

- `lookupType`
- `title`
- `value`
- `displayValue`
- `onSelect`
- `onClear`
- `searchParams`
- `columns`
- `page`
- `pageSize`
- `totalCount`
- `selectionMode`
- `manageActionsEnabled`
- `disabled`

### `lookupType` 후보

- `client`
- `product`
- `warehouse`
- `commonCode`
- `carrier`
- `returnSource`
- `judgementReason`
- `holdReason`
- `outboundDestination`

### 규칙

- 기본 선택은 단일 선택이다.
- 여러 행이 동시에 선택 표시되면 버그다.
- `totalCount`는 서버 기준이다.
- footer는 항상 보여야 한다.
- 관리 액션은 권한 있는 내부 관리자에게만 제공한다.
- 삭제보다 사용중지를 우선한다.
- `groupCode` 같은 개발자용 값은 사용자 제목에 노출하지 않는다.

## SmartButton / SmartField / SmartStatusBadge

### SmartButton

#### props 후보

- `variant`
- `size`
- `icon`
- `children`
- `disabled`
- `loading`
- `onClick`
- `confirmRequired`

#### `variant` 후보

- `primary`
- `secondary`
- `softPrimary`
- `danger`
- `ghost`

#### 규칙

- 버튼은 카드처럼 보이면 안 된다.
- `primary`는 최종 액션에 제한한다.
- 버튼 높이는 34~36px 기준이다.

### SmartField

#### props 후보

- `label`
- `required`
- `help`
- `error`
- `children`
- `layout`
- `width`

#### 규칙

- label/help/error 구조를 화면마다 다시 만들지 않는다.
- 입력칸은 임의로 늘어나지 않게 한다.

### SmartStatusBadge

#### props 후보

- `status`
- `label`
- `tone`
- `size`
- `tooltip`

#### `tone` 후보

- `success`
- `warning`
- `danger`
- `info`
- `neutral`

#### 규칙

- 색상만으로 상태를 표현하지 않는다.
- 텍스트를 함께 표시한다.
- 상태배지는 버튼처럼 보이면 안 된다.

## SmartLogPanel

### 목적

- 최근 스캔, 처리 로그, 상태 변경 로그를 compact하게 표시한다.

### props 후보

- `logs`
- `maxRows`
- `emptyMessage`
- `onMore`
- `compact`

### log row 후보

- `time`
- `type`
- `message`
- `result_code`
- `sound_code`
- `operator_name`

### 규칙

- 로그가 중앙 그리드보다 커지면 실패다.
- 작업자 화면에서는 최근 로그 일부만 표시한다.
- 전체 로그는 상세/통합추적에서 조회한다.

## 상태/오류/빈 화면 공통 처리

- loading: 현재 영역 안에서만 표시한다.
- empty: 무엇을 해야 하는지 한 줄 안내와 다음 행동 버튼을 제공한다.
- error: 오류 메시지와 재시도/닫기 버튼을 제공한다.
- success: 과한 모달 대신 짧은 상태 표시를 우선한다.
- warning: 숫자와 목록을 함께 보여준다.
- validation error: 행/셀 단위로 표시한다.

## 반품 화면과 컴포넌트 매핑

| 화면 | 레이아웃 | 메인 그리드 | 우측 패널 | 스캔 입력 | 하단 액션 | 모달/조회 |
| --- | --- | --- | --- | --- | --- | --- |
| 반품자료 준비 | `SmartWorkLayout` | `SmartExcelPreviewGrid` / `SmartEditableDataGrid` / `SmartDataGrid` | `SmartInfoPanel` | 없음 | `SmartActionBar` | `SmartLookupModal`, `SmartModalShell` |
| 반품처리 작업 | `SmartWorkLayout` | `SmartDataGrid` | `SmartInfoPanel` | `SmartScanPanel` | `SmartActionBar` | `SmartModalShell`, `SmartLookupModal` |
| 반품 마감 | `SmartWorkLayout` | `SmartDataGrid` | `SmartInfoPanel` | `SmartScanPanel` | `SmartActionBar` | `SmartModalShell` |
| 반품 반출 | `SmartWorkLayout` | `SmartDataGrid` | `SmartInfoPanel` | `SmartScanPanel` | `SmartActionBar` | `SmartLookupModal`, `SmartModalShell` |
| 반품 통합추적 | `SmartWorkLayout` | `SmartDataGrid` | `SmartInfoPanel`, `SmartLogPanel` | 없음 | `SmartActionBar` | `SmartLookupModal`, `SmartModalShell` |

## 금지 패턴

- 화면별 임시 table 생성 금지.
- 화면별 임시 Select 생성 금지.
- 화면별 임시 modal 생성 금지.
- `textarea` 기반 엑셀 붙여넣기 금지.
- `AgGridReact` 직접 사용 금지.
- 안내문/카드가 그리드를 밀어내는 구조 금지.
- 버튼 아닌 요소에 `cursor:pointer` 적용 금지.
- 핵심 버튼이 가로 스크롤 뒤에 숨는 구조 금지.
- `raw_json`, `batch_id`, `import_job_id` 같은 내부값 기본 노출 금지.
- 반품처리 작업 화면에 구글시트 동기화 버튼 추가 금지.

## Codex 구현 전 체크

- 새 화면에서 사용할 페이지 템플릿이 정해졌는가?
- 기존 공통 컴포넌트로 해결 가능한가?
- 새 컴포넌트를 만들기 전에 공통 컴포넌트 확장을 검토했는가?
- 그리드 종류가 `SmartDataGrid`, `SmartEditableDataGrid`, `SmartExcelPreviewGrid` 중 올바르게 선택되었는가?
- 스캔 입력은 `SmartScanPanel`을 사용하는가?
- 우측 패널은 `SmartInfoPanel`을 사용하는가?
- 하단 버튼은 `SmartActionBar`를 사용하는가?
- 모달은 `SmartModalShell`을 사용하는가?
- 고객사/상품/창고/공통코드 선택은 SmartLookup 계열을 사용하는가?
- 버튼과 비버튼이 명확히 구분되는가?
- 1366x768 기준 핵심 조작이 보이는가?
