# UI Grid Skill

## 목적

SmartReturn Pro의 grid/table/preview 화면 작업 기준을 정리한다.

## 기본 원칙

- 업무 화면에서 grid/table 직접 구현을 남발하지 않는다.
- 실사용 화면은 `SmartDataGrid`, `SmartEditableDataGrid`, `SmartExcelPreviewGrid` 같은 wrapper 기준으로 확장한다.
- AG Grid를 쓰더라도 화면에서 직접 import하지 않고 wrapper 내부에서만 사용한다.
- skeleton 단계에서 기본 table을 쓰더라도 실사용 전 공통 Grid wrapper로 전환한다.

## 원본 순서 보존

- import preview와 엑셀 preview는 원본 row 순서를 보존한다.
- `row_no` 또는 `original_row_no`를 표시한다.
- 사용자가 필터를 바꿔도 기본 정렬은 원본 row 순서로 돌아올 수 있어야 한다.
- 자동 정렬로 원본 행 순서를 잃지 않는다.

## 상태 표시

grid row에는 상태가 한눈에 보여야 한다.

- 정상
- 경고
- 오류
- 검증 전
- 처리중
- 보류

상태는 badge, 색상, 한글 문구를 함께 사용한다.

## 화면 밀도

- 1366x768 기준에서 주요 버튼, 요약, 하단 action bar가 사라지지 않아야 한다.
- grid 첫 5행 정도는 보여야 한다.
- 과한 카드와 설명문이 grid를 밀어내지 않아야 한다.

## 관리자 화면과 작업자 화면

관리자 화면:

- 필터
- grid
- 상세 패널
- 권한/상태/이력 확인

작업자 화면:

- 큰 입력
- 현재 작업 대상 강조
- 빠른 피드백
- 마우스 클릭 최소화
- 다음 처리 대상 row 강조

## 재사용 범위

아래 화면은 공통 grid 기준을 재사용해야 한다.

- Import Preview
- 기준정보
- 입고
- 출고
- 반품
- 재고
- 정산

화면별 table이 계속 커지면 공통 Grid wrapper로 전환한다.
