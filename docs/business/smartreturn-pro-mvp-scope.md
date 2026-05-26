# SmartReturn Pro MVP 범위

이 문서는 SmartReturn Pro 1차 MVP 범위를 확정하기 위한 기준 문서다. 전체 OMS/WMS/정산 플랫폼을 한 번에 완성하는 문서가 아니라, 반품 MVP를 안전하게 만들기 위해 먼저 필요한 기반과 제외 범위를 정한다.

## MVP 목표

SmartReturn Pro 1차 MVP는 전체 OMS/WMS/정산 플랫폼 완성이 아니라 아래 기반을 먼저 완성하는 것을 목표로 한다.

- 기준정보
- 권한/client scope
- import job
- 상품/바코드/unit_qty
- 재고 이벤트 원장
- 반품자료 준비
- 반품처리 작업
- 반품 마감
- 반품 반출의 최소 흐름

반품은 1차 업무 MVP의 최우선 대상이다. 다만 반품 화면부터 바로 만들지 않고, 기준정보, 권한, import job, 스캔 로그, 재고 이벤트 구조를 먼저 갖춘 뒤 진행한다.

## MVP 선행 기반

반품 화면부터 바로 만들지 말고 아래 순서를 따른다.

1. 권한/사용자/client scope
2. 기준정보
3. 상품/바코드/unit_qty
4. import job / 업로드 검증 구조
5. scan_events / 스캔 로그 구조
6. inventory_events / current_inventory
7. 반품자료 준비
8. 반품처리 작업
9. 반품 마감
10. 반품 반출

## 1차 MVP 포함 범위

### 권한/사용자

- 로그인
- `role` 기준 내부/고객사 사용자 구분
- `client_id` scope
- `warehouse_id` scope 기본
- `must_change_password`
- 관리자 비밀번호 조회 금지, 초기화/재발급만 허용

### 기준정보

- 고객사
- 창고
- 고객사-창고 연결
- 상품
- 상품 추가바코드
- 공통코드
- 사용자/권한

### import job

- 엑셀 업로드
- 엑셀 붙여넣기 후보
- preview
- validation
- save 확정
- import job 이력
- 원본 `row_no` / `row_hash` / `source_row_key` 보존

### 반품자료 준비

- CJ/택배 반품예정 엑셀 등록
- 반품예정 저장자료 조회
- 반품예정 업로드 이력
- 업체 구글시트는 내부 반품입고예정 화면에서 제외
- 업체 반품접수 자료는 별도 후속 모듈 또는 별도 화면으로 분리

### 반품처리 작업

- 운송장 또는 입고번호 스캔
- 고객사 확정
- 상품 스캔/확인
- 판정
- 목적 창고 추천
- 사진/메모 후보
- 라벨 출력 요청 후보
- 처리완료
- 재고반영은 직접 하지 않고 `READY` 상태 또는 이벤트 생성 후보로 분리

### 반품 마감

- 기간/고객사/판정상태 조회
- 양품/폐기 상품바코드 수량 대조
- 리퍼/제조사반품/샘플/보류 반품관리번호 1:1 대조
- 마감 확정
- 재고반영과 분리

### 반품 반출

- 외부반출 대상 조회
- 반출 묶음 생성
- 반품관리번호 스캔
- 반출확정
- 재고 이벤트는 서버 경로에서 처리

### 재고

- `inventory_events`
- `current_inventory`
- `idempotency_key`
- `reverse_event_id`
- 재고 현황/이력 기본 조회

## MVP 제외 범위

아래 항목은 1차 MVP에서 제외한다.

- ERP 실제 API 전송
- 고객사 포털 전체 구현
- 정산 생성/마감 전체 구현
- Local Agent 자동 업데이트
- 원격 설정 강제 변경
- AI 도우미
- 자동 구글시트 스케줄러
- 구글시트 실시간 스캔 조회
- 복잡한 승인/결재 워크플로우
- 고급 통계/작업자 성과 분석
- 모바일 전용 화면

## 업무별 MVP 우선순위

업무와 기반의 우선순위는 다음과 같다.

1. 기준정보
2. 권한/client scope
3. import job
4. 재고 이벤트
5. 반품 MVP
6. 입고 MVP
7. 출고 MVP
8. OMS
9. 정산
10. 고객사 포털

실제 개발은 기준정보, 권한/client scope, import job, 재고 이벤트가 먼저다. 업무 MVP 중 첫 번째는 반품이며, 입고와 출고는 반품 MVP 이후에 진행한다.

## 메뉴/ERD 정합성 점검

- 메뉴 문서의 기준정보 화면은 P0 기준정보 테이블과 연결된다.
- 반품자료 준비 화면은 `import_jobs`, `import_job_rows`, `import_validation_errors`, `return_expected_batches`, `return_expected_rows`와 연결된다.
- 반품처리 작업 화면은 `scan_sessions`, `scan_events`, `return_receipts`, `return_receipt_items`, `return_units`와 연결된다.
- 반품 마감 화면은 `return_closing_sessions`, `return_closing_items`와 연결된다.
- 반품 반출 화면은 `return_external_outbound_batches`, `return_external_outbound_items`와 연결된다.
- 재고 현황/이력 화면은 `inventory_events`, `current_inventory`와 연결된다.
- OMS, 입고, 출고, 정산, 고객사 포털 메뉴는 문서상 구조를 유지하되 1차 MVP에서는 후속 범위로 둔다.

## Codex 구현 전 체크

- 이 기능이 MVP 포함 범위인지 확인했는가?
- 기존 문서와 충돌하지 않는가?
- 한 화면에 여러 업무를 섞고 있지 않은가?
- `client_id`/`warehouse_id` scope가 명확한가?
- 재고를 직접 변경하지 않고 `inventory_events` 흐름을 타는가?
- import job과 업무 테이블을 분리했는가?
