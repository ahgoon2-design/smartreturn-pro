# SmartReturn Pro 공통 컴포넌트 기준

이 문서는 SmartReturn Pro 신규 제작 기준이다. 기존 SmartReturn의 구현기록이나 화면별 임시 컴포넌트를 그대로 따르지 않는다.

## 기본 원칙

- 신규 화면에서 화면별 table, input, button, select, modal을 임시로 만들지 않는다.
- 화면 구현 전에 공통 컴포넌트의 책임과 사용 기준을 먼저 확인한다.
- 같은 역할의 UI는 같은 컴포넌트를 사용한다.
- AG Grid는 직접 사용하지 않고 공통 래퍼를 통해서만 사용한다.
- 현장 작업자 화면은 내부 enum, DB 필드명, 개발자 용어를 숨기고 작업자가 이해하는 말로 표시한다.
- 주요 업무 화면은 다음 행동이 제일 먼저 보여야 하며 같은 의미의 안내문을 반복하지 않는다.

## 공통 컴포넌트 후보

- `SmartWorkLayout`: 좌측 메뉴, 상단 헤더, 중앙 작업영역, 우측 정보패널, 하단 액션바를 묶는 작업 화면 레이아웃.
- `SmartPage`: 일반 페이지의 기본 여백, 폭, 배경, 스크롤 정책을 담당한다.
- `SmartPageHeader`: 화면 제목, 상태, 보조 액션을 통일한다.
- `SmartFilterPanel`: 조회 조건, 고객사/창고 조건, 기간 조건을 통일한다.
- `SmartInfoPanel`: 선택 행 상세, 상태 요약, 보조 판단 정보를 표시한다.
- `SmartDataGrid`: 조회 중심 그리드 래퍼다.
- `SmartEditableDataGrid`: 편집 가능한 업무 입력 그리드 래퍼다.
- `SmartExcelPreviewGrid`: 엑셀 원본 preview와 검증 결과 표시 기준이다.
- `SmartScanPanel`: 스캔 입력, 최근 스캔, 매칭 결과를 묶는다.
- `SmartScanPanel`은 스캔 처리만 강제하지 않고 필요 시 그리드 선택 처리와 같은 backend 검증 흐름으로 이어져야 한다.
- `SmartActionBar`: 저장, 확정, 취소, 처리 같은 주요 액션을 고정 배치한다.
- `SmartModalShell`: 공통 모달 크기, header, body, footer를 통일한다.
- `SmartLookupModal`: 고객사, 상품, 창고 등 조회 선택을 통일한다.
- `SmartButton`: 버튼 종류, 크기, disabled, loading 표현을 통일한다.
- `SmartField`: label, 입력, 오류, 도움말 표시를 통일한다.
- `SmartStatusBadge`: 업무 상태, 검증 상태, 연결 상태를 통일한다.
- `SmartLogPanel`: 처리 로그, 오류 로그, 작업 이력을 표시한다.

## 금지 기준

- `AgGridReact`를 화면에서 직접 사용하지 않는다.
- 엑셀 직접 붙여넣기를 textarea로 처리하지 않는다.
- 엑셀 원본 preview를 일반 table로 임시 구현하지 않는다.
- 고객사/상품/창고/공통코드 선택을 화면별 Select로 만들지 않는다.
- 모달마다 크기, footer, 버튼 위치, 입력 폭을 다르게 만들지 않는다.

## 엑셀 입력과 preview 기준

- 엑셀 직접 붙여넣기는 `SmartEditableDataGrid` 기준으로 처리한다.
- 엑셀 원본 preview는 `SmartExcelPreviewGrid` 기준으로 처리한다.
- 원본 row, 검증 오류, 매핑 상태가 분리되어 보여야 한다.
- 업로드 화면에서 실제 업무 확정이나 재고 반영까지 처리하지 않는다.

## Lookup/Input 정책

- 고객사: 내부 운영자는 선택 가능하고 고객사 사용자는 자기 `client_id`로 고정한다.
- 상품: 선택된 `client_id` 범위 안에서만 조회한다.
- 창고: 선택 고객사의 사용창고만 표시한다.
- 공통코드: 화면 하드코딩을 금지하고 공용코드 기준으로 조회한다.
- 택배사: 공통코드 또는 기준정보로 관리한다.
- 반품소스: 구글시트, CJ/택배 엑셀 등 source type을 기준화한다.
- 판정사유: 반품/입고/출고 업무별로 공통코드화한다.
- 보류사유: 업무 처리를 멈추는 사유로 별도 코드 관리한다.

## 모달 표준

- header는 고정한다.
- body만 스크롤한다.
- footer는 고정한다.
- 취소 버튼은 왼쪽에 둔다.
- 저장, 선택, 확정 같은 주요 버튼은 오른쪽에 둔다.
- 크기, 입력폭, 버튼 위치를 통일한다.
- 모달 안에 또 다른 카드형 페이지 레이아웃을 넣지 않는다.

## Codex 구현 전 체크

- 화면별 임시 table/input/button/select/modal을 만들고 있지 않은가?
- `AgGridReact`를 직접 사용하지 않았는가?
- 엑셀 원본 preview는 `SmartExcelPreviewGrid` 기준인가?
- 엑셀 붙여넣기는 `SmartEditableDataGrid` 기준인가?
- 고객사/상품/창고/공통코드 선택이 lookup 정책을 따르는가?
- 모달 header/body/footer와 버튼 위치가 표준을 따르는가?
