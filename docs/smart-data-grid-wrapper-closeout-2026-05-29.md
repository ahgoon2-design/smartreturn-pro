# SmartDataGrid 최소 Wrapper 구현 마감

## 1. 작업 목적

`docs/smart-data-grid-design-plan-2026-05-29.md`의 설계 기준을 바탕으로 SmartReturn Pro 업무 화면에서 공통으로 사용할 `SmartDataGrid` 최소 wrapper를 구현했다.

이번 작업은 `SmartDataGrid`의 1차 기반을 잡는 범위이며, Import Preview 전체 전환, 파일 업로드, 기준정보 화면 제작, AG Grid 도입은 포함하지 않았다.

## 2. 변경 전 SmartDataGrid 상태

변경 전 `frontend/src/components/grid/SmartDataGrid.tsx`는 Ant Design `Table`을 얇게 감싼 최소 wrapper였다.

기존 상태:

- props: `rowKey`, `columns`, `dataSource`, `loading`
- 내부 구현체: Ant Design `Table`
- pagination: false 고정
- size: small 고정
- scroll: `x=960`, `y=320` 고정
- 공통 column type, selection, row action, error/empty 상태, 원본 순서 보존 옵션, 셀 복사 기능은 없었다.

## 3. 구현한 파일 목록

추가:

- `frontend/src/components/grid/SmartDataGrid.css`
- `frontend/src/components/grid/SmartDataGrid.helpers.tsx`
- `frontend/src/components/grid/SmartDataGrid.types.ts`
- `frontend/src/components/grid/SmartGridActionCell.tsx`
- `frontend/src/components/grid/SmartGridStatusCell.tsx`
- `frontend/src/components/grid/SmartGridToolbar.tsx`
- `frontend/src/components/grid/index.ts`

수정:

- `frontend/src/components/grid/SmartDataGrid.tsx`
- `frontend/src/components/common/SmartStatusBadge.tsx`
- `frontend/src/features/import/ImportPreviewPage.tsx`
- `docs/smartreturn-pro-doc-index.md`

문서:

- `docs/smart-data-grid-wrapper-closeout-2026-05-29.md`

## 4. 구현한 props 기준

1차 wrapper에서 아래 props 기반을 마련했다.

- `rows`
- `dataSource` 기존 호환
- `columns`
- `rowKey`
- `loading`
- `error`
- `emptyText`
- `selectedRowKeys`
- `onSelectionChange`
- `onRowClick`
- `rowActions`
- `pagination`
- `preserveOriginalOrder`
- `originalOrderKey`
- `enableOriginalOrderReset`
- `density`
- `stickyHeader`
- `maxHeight`
- `getRowClassName`
- `footerActions`
- `enableCopy`
- `enableMultiSelect`

`enableColumnResize`, `enableColumnSettings`, virtual scroll, AG Grid 내부 전환, 사용자별 컬럼 설정 저장은 후속 항목으로 남겼다.

## 5. 구현한 column 기준

`SmartDataGridColumn` 타입을 추가했다.

포함 기준:

- `key`
- `title`
- `dataIndex`
- `width`
- `minWidth`
- `align`
- `render`
- `renderType`
- `statusMap`
- `sortable`
- `copyable`
- `tooltip`
- `fixed`
- `errorHighlight`
- `warningHighlight`
- `className`

화면은 SmartReturn Pro 자체 column type을 사용하고, 내부 helper가 Ant Design Table column으로 변환한다. 이 구조는 향후 AG Grid로 내부 구현체를 바꿀 때 화면 쪽 column 계약을 유지하기 위한 1차 기반이다.

## 6. 공통 모양 기준

`SmartDataGrid.css`를 추가해 grid 공통 모양 기준을 분리했다.

적용 기준:

- header 높이 기준
- row 높이 기준
- font size 기준
- cell padding 기준
- border 기준
- hover row 표시
- selected row 표시
- focused row 표시
- 오류/경고 cell 강조
- copy cell 표시
- row action 위치
- compact / standard / comfortable density

기존 `global.css`에 모든 grid 스타일을 몰아넣지 않고, grid 컴포넌트 단위 CSS로 분리했다.

## 7. 상태 표시 기준

`SmartGridStatusCell`을 추가하고 기존 `SmartStatusBadge`를 재사용했다.

`SmartStatusBadge`는 기존 import 상태 외에 공통 업무 상태를 표시할 수 있도록 확장했다.

추가 표시 후보:

- `NORMAL`
- `SUCCESS`
- `ERROR`
- `WAITING`
- `PROCESSING`
- `COMPLETED`
- `HOLD`
- `CANCELLED`
- `INACTIVE`
- `SHORTAGE`
- `OVERAGE`
- `UNREGISTERED`
- `DUPLICATED`

한글 상태값도 최소 범위에서 색상 매핑을 지원한다.

## 8. 원본 순서 보존 구현 내용

`preserveOriginalOrder`와 `originalOrderKey`를 추가했다.

동작:

- `preserveOriginalOrder=true`이고 `originalOrderKey`가 있으면 해당 key 기준으로 asc 정렬한 복사본을 표시한다.
- props로 받은 `rows` 원본 배열은 mutate하지 않는다.
- `enableOriginalOrderReset=true`이면 `SmartGridToolbar`에 “원본 순서” 버튼을 노출할 수 있다.
- 원본 순서 복귀 버튼은 Ant Design Table 내부 정렬 상태를 초기화할 수 있도록 table key를 갱신한다.

## 9. copy 기능 구현 내용

`enableCopy`와 column별 `copyable` 기준으로 셀 값 복사 기능을 추가했다.

기준:

- `enableCopy=true`이고 column의 `copyable=true`인 경우 복사 버튼을 표시한다.
- 복사 성공 시 Ant Design `message`로 피드백을 표시한다.
- 민감값은 column에서 `copyable`을 켜지 않는 것을 기본 원칙으로 주석에 남겼다.
- 실제 token, password, secret 값을 복사 대상으로 만들지 않는다.

## 10. selection / row action 구현 내용

selection:

- `selectedRowKeys`
- `onSelectionChange`
- `enableMultiSelect`

row action:

- `SmartGridRowAction` 타입 추가
- `SmartGridActionCell` 추가
- `rowActions`가 있으면 우측 “작업” column을 자동 추가한다.
- action 클릭 시 row click과 충돌하지 않도록 이벤트 전파를 막는다.

bulk action은 이번 범위에서 구현하지 않고 `footerActions` 또는 향후 `SmartActionBar` 연동 자리로 남겼다.

## 11. loading / empty / error 구현 내용

`SmartDataGrid` 내부에서 표준 표시를 제공한다.

- `loading`: Ant Design Table loading 사용
- `emptyText`: Ant Design Empty 기반 표시
- `error`: 안전한 메시지만 `Alert`로 표시

error에는 stack trace를 그대로 표시하지 않고, `Error.message` 또는 안전한 문자열만 표시한다.

## 12. Import Preview 영향 확인

이번 작업에서 Import Preview를 전면 전환하지 않았다.

다만 기존 `SmartDataGrid` 사용 방식이 새 props와 맞도록 최소 조정했다.

확인 내용:

- `frontend/src/features/import/ImportPreviewPage.tsx`의 API 호출 흐름은 변경하지 않았다.
- rows/errors 조회 함수는 변경하지 않았다.
- `VALID`, `WARNING`, `INVALID`, `NOT_VALIDATED` 표시 흐름은 유지했다.
- row_no 기준 원본 순서 표시는 `preserveOriginalOrder`, `originalOrderKey="row_no"` 옵션을 사용한다.
- 일부 column에 `copyable`을 켜서 1차 copy 기능을 확인할 수 있게 했다.

## 13. 미구현/후속 항목

- Import Preview의 완전한 `SmartDataGridColumn` 정책 전환
- row별 오류/경고 count API 보강
- SmartGridExportButton 또는 엑셀 다운로드 실제 구현
- column resize
- column settings
- 사용자별 컬럼 설정 저장
- server pagination 고도화
- virtual scroll
- AG Grid 내부 전환
- SmartEditableDataGrid
- 기준정보 화면 적용

## 14. 검증 결과

- `npm.cmd run typecheck`: 통과
- `npm.cmd run build`: 통과
- `git diff --check`: 통과

backend 코드는 변경하지 않아 backend pytest는 생략했다.

## 15. 다음 추천 작업

1. Import Preview를 새 `SmartDataGrid` 계약으로 전환
2. 기준정보 화면 디자인 토론
3. 파일 업로드 `EXCEL_FILE` skeleton 설계
