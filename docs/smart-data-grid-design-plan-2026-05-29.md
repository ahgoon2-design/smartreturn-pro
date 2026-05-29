# SmartDataGrid Wrapper 설계 기준

## 1. 문서 목적

이 문서는 SmartReturn Pro의 업무 화면에서 공통으로 사용할 `SmartDataGrid` wrapper 설계 기준을 정리한다.

목적은 화면별 table/grid 직접 구현을 줄이고, 기준정보, Import Preview, 입고, 출고, 반품, 재고, 정산 화면의 데이터 표시 기준을 통일하는 것이다. 구현 전에 디자인, UX, 데이터 표시, 상태 표시, 행 선택, 필터, 정렬, 액션 기준을 먼저 확정한다.

이번 문서는 설계 기준 문서이며 `SmartDataGrid` 구현, package 변경, backend 변경, DB 변경은 포함하지 않는다.

## 2. 적용 대상

`SmartDataGrid` 기준은 아래 화면에 공통 적용한다.

- Import Preview
- 기준정보 관리
- 상품/상품바코드 관리
- 고객사/창고 관리
- 입고 예정/입고 검수
- 출고 검수
- 반품처리
- 반품마감
- 반품 외부반출
- 재고현황/재고실사
- 정산 조회

단, 작업자용 스캔 화면은 그리드가 보조 수단일 수 있다. 스캔 입력, 현재 작업 대상, 성공/오류 피드백이 우선이며 그리드는 필요한 컬럼만 표시한다.

## 3. 현재 상태 요약

React/Vite/TypeScript 앱 스캐폴드는 완료되어 있으며, AuthContext/Route Guard도 실제 로그인 흐름과 연결되어 있다. 관련 마감 문서는 아래에 있다.

- `docs/frontend-app-scaffold-closeout-2026-05-29.md`
- `docs/frontend-auth-route-guard-closeout-2026-05-29.md`

현재 프론트 grid/table 상태:

- `frontend/src/components/grid/SmartDataGrid.tsx`가 존재한다.
- 현재 `SmartDataGrid`는 Ant Design `Table`을 얇게 감싼 최소 wrapper다.
- 현재 props는 `rowKey`, `columns`, `dataSource`, `loading` 중심이다.
- 현재 wrapper는 `pagination=false`, `size="small"`, `scroll={{ x: 960, y: 320 }}`를 고정으로 사용한다.
- 아직 정식 공통 grid 정책인 row selection, row action, empty/error 상태, 원본 순서 복원, sticky action bar 연동, status column 표준화는 구현되어 있지 않다.

Import Preview 화면 상태:

- 구현 파일: `frontend/src/features/import/ImportPreviewPage.tsx`
- rows는 `GET /api/import-jobs/{job_id}/rows` 결과를 `row_no asc`로 정렬해 표시한다.
- errors는 `GET /api/import-jobs/{job_id}/errors` 결과를 `row_no asc`, 같은 row 안에서는 id 기준으로 정렬한다.
- row grid는 현재 `SmartDataGrid` wrapper를 사용하지만, column 정의는 화면 내부에서 Ant Design `ColumnsType`으로 직접 작성한다.
- 오류/경고 상세는 grid 밖의 `Card` 영역에서 별도 목록으로 표시한다.
- 상태 표시는 `SmartStatusBadge`를 사용한다.
- 전체/오류/경고 필터는 화면 내부 상태로 처리한다.

기존 `docs/skills/ui-grid.md` 기준과 충돌하는 부분:

- 현재 화면은 `SmartDataGrid`를 사용하지만 wrapper가 아직 정책을 강제하지 못한다.
- 화면 내부에서 Ant Design `ColumnsType`을 직접 작성하고 있어 column 정의 표준화가 아직 부족하다.
- 원본 순서 보존은 Import Preview 화면 로직에서 직접 처리하고 있으며, wrapper 옵션으로 추상화되어 있지 않다.

따라서 현재 상태는 “최소 wrapper는 있으나 실사용 공통 Grid wrapper는 아직 설계/구현 전”으로 본다.

## 4. SmartDataGrid 기본 역할

`SmartDataGrid`는 아래 역할에 집중한다.

- 데이터 목록 표시
- 원본 row 순서 보존
- 상태 뱃지 표시
- row selection
- loading / empty / error 상태 표시
- pagination 또는 internal scroll 처리
- column 정의 표준화
- row action 버튼 표시
- bulk action과 하단 `SmartActionBar` 연동
- 접근 권한과 상태에 따른 action 비활성 표시

필터와 검색 영역은 grid 내부에 모두 넣지 않는다. 상단 조건 영역은 `SmartFilterPanel`, `SmartToolbar`, 화면별 toolbar와 조합한다. 요약은 `SmartSummaryCard` 또는 향후 `SmartKpiCard` 계열이 담당한다.

## 5. 기술 선택 방향

### 1단계: Ant Design Table 기반의 얇은 wrapper

초기에는 AG Grid를 바로 도입하지 않는다. React table wrapper 또는 Ant Design `Table` 기반의 얇은 `SmartDataGrid`를 우선 검토한다.

목적은 화면들이 동일한 props와 사용법을 따르도록 하는 것이다. 즉, 구현체보다 “화면에서 사용하는 계약”을 먼저 고정한다.

1단계에서 우선 제공할 것:

- 공통 column 정의
- 상태 cell 표준화
- loading / empty / error 표시
- row selection
- row action
- 원본 순서 보존 옵션
- 내부 scroll과 compact density

### 2단계: AG Grid 도입 검토

대량 데이터, 고급 필터, column resize, column pinning, virtual scroll, clipboard, 대량 편집이 본격적으로 필요해지면 AG Grid 도입을 검토한다.

AG Grid를 도입하더라도 업무 화면에서 `AgGridReact`를 직접 사용하지 않는다. 모든 업무 화면은 `SmartDataGrid` 또는 용도별 wrapper를 통해서만 grid 구현체를 사용한다.

원칙:

- 업무 화면에서 grid 구현체를 직접 호출하지 않는다.
- 화면별 table이 커지면 `SmartDataGrid` 기능을 확장한다.
- 구현체 교체가 필요해도 화면 코드가 크게 바뀌지 않도록 wrapper 계약을 유지한다.

## 6. 추천 컴포넌트 구조

구현 시 후보 구조는 아래와 같다.

```text
frontend/src/components/grid/
  SmartDataGrid.tsx
  SmartDataGrid.types.ts
  SmartDataGrid.helpers.ts
  SmartGridStatusCell.tsx
  SmartGridActionCell.tsx
  SmartGridEmptyState.tsx
  SmartGridErrorState.tsx
  index.ts
```

파일별 역할:

| 파일 | 역할 |
| --- | --- |
| `SmartDataGrid.tsx` | 화면에서 사용하는 grid wrapper 진입점 |
| `SmartDataGrid.types.ts` | rows, columns, action, selection, pagination 등 공통 타입 |
| `SmartDataGrid.helpers.ts` | 원본 순서 정렬, status map, row key 보정 등 순수 helper |
| `SmartGridStatusCell.tsx` | `SmartStatusBadge`와 연결되는 상태 cell |
| `SmartGridActionCell.tsx` | row action 버튼 묶음 |
| `SmartGridEmptyState.tsx` | 빈 데이터 표시 |
| `SmartGridErrorState.tsx` | grid 영역 오류 표시 |
| `index.ts` | 외부 import 경로 통일 |

향후 editable grid가 필요하면 `SmartEditableDataGrid`를 별도로 분리한다. import/excel preview 전용 기능이 커지면 `SmartExcelPreviewGrid` 또는 `SmartImportPreviewGrid`를 `SmartDataGrid` 위에 얹는 방식으로 확장한다.

## 7. props 설계 초안

실제 TypeScript 구현 전 문서 수준의 props 후보는 아래와 같다.

| prop | 목적 |
| --- | --- |
| `rows` | 표시할 row 배열 |
| `columns` | 공통 column 정의 배열 |
| `rowKey` | row 고유 식별자 |
| `loading` | 로딩 상태 |
| `error` | grid 영역 오류 상태 |
| `emptyText` | 빈 데이터 문구 |
| `selectedRowKeys` | 선택된 row key 목록 |
| `onSelectionChange` | row selection 변경 callback |
| `onRowClick` | row 클릭 callback |
| `rowActions` | row별 action 버튼 정의 |
| `pagination` | page/pageSize/total/onChange 계약 |
| `preserveOriginalOrder` | 원본 순서 보존 여부 |
| `originalOrderKey` | `row_no`, `original_row_no` 등 원본 순서 기준 key |
| `statusColumn` | 상태 column 자동 표시 옵션 |
| `density` | `compact`, `standard`, `comfortable` 같은 밀도 옵션 |
| `stickyHeader` | header 고정 여부 |
| `stickyActionBar` | 하단 action bar와 조합할 때 여백/고정 기준 |
| `maxHeight` | grid 내부 scroll 높이 |
| `getRowClassName` | row 상태별 className |
| `summary` | grid 하단 또는 상단의 간단 요약 표시 후보 |
| `footerActions` | grid 하단 보조 action 후보 |

1차 구현에서는 모든 props를 한 번에 구현하지 않는다. 최소 wrapper 구현 단계에서는 `rows`, `columns`, `rowKey`, `loading`, `error`, `emptyText`, `preserveOriginalOrder`, `originalOrderKey`, `density`, `maxHeight`부터 검토한다.

## 8. column 정의 기준

화면별 Ant Design `ColumnsType`을 직접 넘기는 방식은 빠르지만 표준화가 어렵다. 실사용 기준에서는 `SmartDataGridColumn` 같은 공통 column 정의를 둔다.

column 정의 후보:

| 항목 | 목적 |
| --- | --- |
| `key` | column 고유 key |
| `title` | 화면 표시명 |
| `dataIndex` | row data 접근 key |
| `width` | column 폭 |
| `align` | 정렬 |
| `renderType` | `text`, `number`, `date`, `status`, `action`, `tag`, `money` 등 |
| `statusMap` | 상태값과 `SmartStatusBadge` 표시 규칙 연결 |
| `sortable` | 정렬 가능 여부 |
| `filterable` | column filter 가능 여부 |
| `fixed` | 좌/우 고정 여부 |
| `hiddenOnCompact` | compact 모드에서 숨김 여부 |
| `tooltip` | header 또는 cell tooltip |
| `copyable` | 값 복사 가능 여부 |
| `editable` | 편집 가능 여부. 1차 범위에서는 제외하고 후속 검토 |

1차에서는 editable grid를 만들지 않는다. 편집 가능한 기준정보 화면이 필요해지면 `SmartEditableDataGrid` 또는 row edit modal 방식 중 하나를 별도로 설계한다.

## 9. 상태 표시 기준

상태 표시는 `SmartStatusBadge`와 연동한다. 색상만으로 의미를 전달하지 않고 한글 문구를 함께 표시한다.

공통 상태:

| 의미 | 표시 방향 |
| --- | --- |
| 정상 | 초록 계열, “정상” |
| 경고 | 노랑/주황 계열, “경고” |
| 오류 | 빨강 계열, “오류” |
| 대기 | 회색/파랑 계열, “대기” |
| 처리중 | 파랑 계열과 loading indicator, “처리중” |
| 완료 | 초록 계열, “완료” |
| 보류 | 보라/회색 계열, “보류” |
| 취소 | 회색 계열, “취소” |
| 비활성 | 낮은 대비 회색, “비활성” |

Import Preview 상태:

| enum | 화면 문구 |
| --- | --- |
| `VALID` | 정상 |
| `WARNING` | 경고 |
| `INVALID` | 오류 |
| `NOT_VALIDATED` | 검증 전 |

작업 화면 상태:

- 미처리
- 처리중
- 처리완료
- 수량부족
- 수량초과
- 미등록
- 중복
- 보류

상태 map은 화면마다 흩어지지 않게 `SmartStatusBadge` 또는 grid helper에서 재사용 가능하게 둔다.

## 10. 원본 순서 보존 기준

원본 row 기반 데이터는 원본 순서를 기본 정렬로 유지한다.

적용 대상:

- Import Preview
- Excel preview
- Google Sheet preview
- 입고예정 조회
- 반품예정 조회
- 외부 업로드/붙여넣기 기반 데이터

기준:

- `row_no` 또는 `original_row_no`를 표시한다.
- 기본 정렬은 원본 순서 기준이다.
- 사용자가 정렬을 바꾸더라도 원본 순서로 되돌리는 기능이 필요하다.
- 필터를 적용해도 내부 정렬은 `row_no` 기준을 유지한다.
- 자동 정렬로 원본 행 순서를 잃지 않는다.

`SmartDataGrid` 1차 구현에서는 `preserveOriginalOrder=true`와 `originalOrderKey="row_no"` 조합을 우선 지원하는 방향을 추천한다.

## 11. 필터/검색/요약 영역과의 관계

`SmartDataGrid`가 화면 전체를 모두 처리하지 않도록 분리한다.

역할 분리:

- 상단 조건 영역: `SmartFilterPanel`, `SmartToolbar`, 화면별 toolbar
- 요약 카드: `SmartSummaryCard` 또는 향후 `SmartKpiCard`
- grid: rows 표시, 상태 표시, row selection, row action
- 하단 주요 버튼: `SmartActionBar`
- 상세 패널: 화면별 detail panel 또는 오류/경고 panel

Grid가 필터, 요약, action, 상세를 모두 품기 시작하면 화면이 무거워진다. 공통 wrapper는 row 표시와 row-level interaction에 집중한다.

## 12. 1366x768 레이아웃 기준

1366x768 기준에서 주요 작업 버튼이 화면 아래로 사라지면 안 된다.

레이아웃 기준:

- 그리드는 남은 공간을 차지하고 내부 scroll을 가진다.
- 상단 필터/요약 영역은 compact 모드를 고려한다.
- pagination 또는 action bar는 sticky/fixed 기준이 필요하다.
- grid 첫 5행 정도는 보여야 한다.
- 안내문, 카드, 배너가 grid를 밀어내면 실패다.
- 작업자 화면에서는 grid보다 스캔 입력과 피드백이 우선일 수 있다.

`SmartDataGrid`는 `maxHeight`, `density`, `stickyHeader` 같은 옵션으로 화면 밀도 조정을 지원하는 방향을 추천한다.

## 13. 관리자 화면과 작업자 화면 차이

### 관리자 화면

관리자 화면은 검색, 필터, 정렬, 상세 조회 중심이다.

특징:

- 많은 컬럼 표시 가능
- row action, modal, 상세 패널 사용
- pagination 또는 서버 필터 필요
- 권한과 상태에 따른 action 비활성 표시 필요
- 반복 조회와 비교 작업에 적합한 밀도 필요

### 작업자 화면

작업자 화면은 관리자 조회 화면처럼 만들지 않는다.

특징:

- 필요한 컬럼만 표시
- 다음 처리 대상 row 강조
- 스캔 입력과 피드백 우선
- 복잡한 필터 최소화
- 오류/보류/완료 상태를 크게 표시
- 마우스 클릭보다 Enter/스캔 흐름 우선

작업자 화면에서는 `SmartDataGrid`를 쓰더라도 column 수와 action 수를 줄이고, 현재 작업 대상이 한눈에 보이도록 강조한다.

## 14. Import Preview 적용 기준

현재 Import Preview를 `SmartDataGrid` 정식 wrapper로 전환할 때 기준은 아래와 같다.

필수 기준:

- `row_no` 기준 원본 순서 유지
- `validation_status` badge 표시
- `product_code`, `product_name`, `barcode`, `barcode_type`, `unit_qty` 표시
- 전체/오류/경고 필터 유지
- errors 상세와 row 연결
- 다음 단계 버튼은 아직 비활성 또는 준비중
- API 응답 필드 부족 시 프론트 추정 금지

전환 방향:

- 현재 화면 내부의 `ColumnsType<ImportJobRow>` 정의를 `SmartDataGridColumn` 정의로 옮긴다.
- `row_no asc` 정렬은 화면 로직이 아니라 `preserveOriginalOrder` 옵션으로 처리한다.
- row별 오류/경고 count는 현재처럼 errors 조회 결과에서 연결하되, API 보강 가능성은 별도 후보로 둔다.
- 상태 badge는 `SmartStatusBadge`를 유지한다.
- 오류/경고 상세 panel은 grid 밖에 두되, 선택 row와 연결할 수 있도록 `onRowClick`을 사용한다.

## 15. 구현 단계 제안

추천 구현 순서:

1. `SmartDataGrid` 최소 wrapper 구현
2. `SmartStatusBadge`와 연동
3. loading / empty / error 상태 구현
4. `row_no` 원본 순서 보존 옵션 구현
5. selection / row action 최소 구현
6. Import Preview를 `SmartDataGrid`로 전환
7. 기준정보 화면에 적용
8. 필요 시 pagination / virtual scroll / AG Grid 전환 검토

1차 구현에서는 AG Grid를 설치하지 않는다. Ant Design Table 기반으로 공통 props와 사용법을 먼저 고정한다.

## 16. 구현 전 체크리스트

새 grid 화면을 만들기 전 아래를 확인한다.

- 현재 화면이 관리자용인지 작업자용인지 확인했는가?
- 원본 순서 보존이 필요한 데이터인가?
- `row_no` 또는 `original_row_no`가 있는가?
- row selection이 필요한가?
- bulk action이 필요한가?
- row action이 필요한가?
- sticky action bar가 필요한가?
- pagination 또는 internal scroll 기준이 정해졌는가?
- status badge map이 공통 상태와 맞는가?
- API 응답 필드를 추정하고 있지 않은가?
- client scope / permission에 따라 action이 달라지는가?
- 화면별 임시 table이 아니라 공통 wrapper로 해결 가능한가?

## 17. closeout 결론

다음 작업은 목표추진 모드로 `SmartDataGrid` 최소 wrapper를 구현하는 것을 추천한다.

그 다음 Import Preview를 `SmartDataGrid` 정식 wrapper로 전환하고, 이후 기준정보 화면 디자인 토론으로 넘어가는 순서가 안전하다.

이 순서가 좋은 이유:

- Import Preview는 이미 rows/errors/status/filter 흐름이 있어 wrapper 검증에 적합하다.
- 기준정보 화면은 CRUD, disable/enable, 권한별 action이 섞이므로 Grid 계약이 먼저 있어야 중복 구현을 줄일 수 있다.
- 입고/출고/반품/재고 화면은 작업자 UX와 관리자 조회 UX가 갈리므로 공통 기준 없이 바로 만들면 재작업 가능성이 높다.
