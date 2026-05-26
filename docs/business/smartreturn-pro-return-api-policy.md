# SmartReturn Pro 반품 MVP API 정책

이 문서는 SmartReturn Pro 신규 제작 기준이며, 기존 SmartReturn 구현기록을 그대로 따르지 않는다.

이 문서는 구현 지시가 아니라 API 설계 전 기준 문서다. 실제 FastAPI router, service, repository, schema 코드는 후속 작업에서 만든다.

## 1. 문서 목적

이 문서는 SmartReturn Pro 반품 MVP의 API 책임과 엔드포인트 기준을 고정한다. 반품자료 준비, 반품처리 작업, 반품 마감, 반품 반출, 반품 통합추적은 서로 다른 업무이며 API 책임도 분리해야 한다.

반품 API는 다음 문서를 기준으로 설계한다.

- `docs/business/smartreturn-pro-return-mvp-flow.md`
- `docs/business/smartreturn-pro-auth-client-scope-api-policy.md`
- `docs/db/smartreturn-pro-db-and-import-policy.md`
- `docs/business/smartreturn-pro-scan-local-agent-inventory-policy.md`

## 2. 반품 API 설계 기본 원칙

- 반품 API는 화면 책임과 동일하게 분리한다.
- 반품자료 준비 API와 반품처리 작업 API를 섞지 않는다.
- 반품처리 작업 API에서 구글시트 동기화를 실행하지 않는다.
- 현장 스캔 중 Google Sheets API를 직접 호출하지 않는다.
- 반품접수자료와 반품예정자료는 매칭될 수도 있고 안 될 수도 있다.
- 매칭은 필수 관문이 아니라 참고/정확도 보조 기능이다.
- `batch_id`는 원본 추적/이력 보조키이며 반품처리 중심키가 아니다.
- 실제 상품/수량/판정은 반품처리 작업에서 확정한다.
- 라벨 출력 실패는 판정 저장 실패가 아니다.
- 재고 반영은 직접 `current_inventory`를 수정하지 않고 `inventory_events` 경로로 처리한다.
- 모든 API는 `AuthContext` 기준 `client_id` scope와 `warehouse_id` scope를 검증한다.
- 고객사 사용자가 요청에 넣은 `client_id`는 서버가 그대로 신뢰하지 않는다.
- path id로 업무 row를 조회한 뒤에는 반드시 `row.client_id`를 검증한다.

## 3. 반품 API 모듈 분리

### 3-1. `return_expected`

역할은 다음과 같다.

- CJ/택배 반품예정 자료 등록, 검증, 저장, 조회를 담당한다.
- import job 기반 업로드 흐름을 담당한다.
- 반품 판정, 처리완료, 마감, 반출은 담당하지 않는다.

금지 항목은 다음과 같다.

- 구글시트 동기화
- 실제 반품 판정
- 라벨 출력
- 재고 반영
- 마감확정
- 반출확정

### 3-2. `return_reception`

역할은 다음과 같다.

- 업체 반품접수 자료 관리 후보 모듈이다.
- 구글시트, 업체 포털, 업체 엑셀 접수자료를 내부 DB에 동기화 또는 등록하는 흐름을 담당한다.
- 1차 MVP에서는 실구현 제외 또는 문서상 후보로 둔다.
- 현장 반품처리 작업 API와 분리한다.

정책은 다음과 같다.

- 업체 반품접수 자료는 반품처리 원장이 아니다.
- 판정 결과 회신 큐는 만들 수 있으나 현장 처리 API에서 직접 push하지 않는다.
- Google Sheets API 호출은 별도 동기화 흐름에서만 수행한다.

### 3-3. `return_work`

역할은 다음과 같다.

- 실제 도착 반품의 운송장/입고번호 스캔, 상품 확인, 판정, 처리완료를 담당한다.
- 반품처리 작업 화면의 API다.
- 구글시트 동기화, 업로드 이력, 마감, 반출 묶음 생성, 재고 이벤트 상세 재처리는 담당하지 않는다.

정책은 다음과 같다.

- 반품예정/접수 자료는 참고정보로만 조회한다.
- 실제 상품, 수량, 판정, 목적 창고는 반품처리 작업에서 확정한다.
- 라벨 출력은 업무 저장 이후 별도 요청 또는 부가 처리로 본다.

### 3-4. `return_closing`

역할은 다음과 같다.

- 판정 완료 결과의 기간/고객사/상태별 수량대조와 마감을 담당한다.
- 새로운 판정을 하지 않는다.
- 구글시트 동기화를 하지 않는다.
- 반품 반출을 하지 않는다.

### 3-5. `return_external_outbound`

역할은 다음과 같다.

- 리퍼, 제조사반품, 샘플, 보류 등 외부반출 대상의 묶음 생성, 스캔 대조, 반출확정을 담당한다.
- 반출확정은 판정 변경이 아니다.
- 반품 마감과 분리한다.

### 3-6. `return_trace`

역할은 다음과 같다.

- 반품 통합추적 읽기 전용 조회를 담당한다.
- 판정 변경, 마감확정, 반출확정, 구글시트 push 실행, 재고 재처리를 하지 않는다.

## 4. API path 초안

아래 path는 실제 구현 전 후보안이다. 확정 DDL, router 코드, schema 코드는 이 문서에서 만들지 않는다.

### 4-1. 반품예정 자료 API

| API | 목적 | 주요 요청값 | 주요 응답값 | 권한 기준 | 하지 말 것 |
| --- | --- | --- | --- | --- | --- |
| `POST /api/returns/expected/import/preview` | CJ/택배 반품예정 엑셀을 import job으로 읽고 검증 preview를 만든다. | `client_id`, `source_type`, 파일 또는 붙여넣기 데이터, `warehouse_id` 후보 | `job_id`, row 수, 오류/경고 요약, preview rows | 내부 운영자 중심, 고객사 사용자는 자기 고객사 업로드 후보만 허용 | 업무 테이블 확정 저장, 판정, 재고 반영 |
| `POST /api/returns/expected/import/save` | 검증된 import job rows를 반품예정 업무 테이블에 반영한다. | `job_id`, 저장 옵션 | 저장 건수, skip 건수, 오류 건수, 생성된 batch 후보 | `job_id`의 `requested_client_id` 접근 검증, 저장 전 row별 client scope 재검증 | 검증 실패 row 저장, 반품처리 원장 생성 |
| `GET /api/returns/expected/import-jobs` | 반품예정 업로드 이력을 조회한다. | `client_id`, 기간, status, source type | import job 목록, 건수 요약 | `client_id` scope 적용 | 구글시트 접수자료 조회 |
| `GET /api/returns/expected/import-jobs/{job_id}` | import job 상세와 row 검증 결과를 조회한다. | `job_id` | job 요약, rows, validation errors | job의 `requested_client_id` 또는 row client 접근 검증 | 업무 판정/마감 조작 |
| `GET /api/returns/expected/rows` | 저장된 반품예정 업무 자료를 조회한다. | `client_id`, 기간, 운송장번호, status | expected rows 목록 | `client_id` scope 적용 | 업체 접수자료 동기화 |
| `GET /api/returns/expected/rows/{expected_row_id}` | 반품예정 row 상세를 조회한다. | `expected_row_id` | 원본값, 정규화값, 매칭 후보, 처리 연결 상태 | row의 `client_id` 검증 | 판정 확정 |
| `POST /api/returns/expected/rows/{expected_row_id}/disable` | 잘못 저장된 반품예정 row를 사용중지한다. | `expected_row_id`, 사유 | 사용중지 결과 | 내부 운영자 중심, row의 `client_id` 검증 | 물리 삭제, 처리완료 row 강제 삭제 |

정책은 다음과 같다.

- preview는 `import_jobs`와 `import_job_rows` 기준이다.
- save는 검증된 `import_job_rows`를 업무 테이블에 반영한다.
- expected rows 조회는 업무용 저장자료 조회다.
- expected rows에는 구글시트 접수자료 동기화 기능을 넣지 않는다.
- `batch_id`는 업로드 추적 보조키이며 반품처리 중심키가 아니다.

### 4-2. 업체 반품접수 자료 API 후보

1차 MVP에서는 실구현 제외 후보로 두되, 장기 path 후보는 다음과 같이 둔다.

| API | 목적 | 주요 요청값 | 주요 응답값 | 권한 기준 | 하지 말 것 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/returns/receptions/sources` | 업체 반품접수 source 목록을 조회한다. | `client_id`, source type | source 목록 | 내부 운영자 또는 자기 고객사 범위 | 현장 처리 API 대체 |
| `POST /api/returns/receptions/sources` | 업체 접수 source 설정 후보를 등록한다. | `client_id`, source type, 연결 설정 후보 | source id | 내부 관리자 중심 | 민감정보 평문 응답 |
| `POST /api/returns/receptions/sync/preview` | 구글시트/업체자료 동기화 preview를 만든다. | source id, 기간 후보 | preview rows, 오류/경고 | source의 `client_id` 검증 | 실제 판정/처리완료 |
| `POST /api/returns/receptions/sync/run` | 업체 접수자료를 내부 DB로 동기화한다. | source id, sync option | 동기화 결과 | 내부 관리자 중심 | 현장 스캔 중 직접 호출 |
| `GET /api/returns/receptions/rows` | 업체 반품접수 row를 조회한다. | `client_id`, 기간, 상태 | 접수 row 목록 | `client_id` scope 적용 | 반품예정 row처럼 취급 |
| `GET /api/returns/receptions/update-queue` | 판정 완료 후 외부 회신 큐를 조회한다. | `client_id`, status | 큐 목록 | 내부 운영자 중심 | 현장 처리 저장과 결합 |
| `POST /api/returns/receptions/update-queue/{queue_id}/push` | 회신 큐를 외부 채널에 push한다. | `queue_id` | push 결과 | 내부 관리자 중심, queue의 `client_id` 검증 | 판정 저장 실패로 연결 |

정책은 다음과 같다.

- 이 API는 업체 반품접수/회신 채널 관리용이다.
- 반품처리 작업 API에서 호출하지 않는다.
- 현장 스캔 중 Google Sheets API 직접 호출은 금지한다.
- 판정 완료 후 회신 큐를 만들 수 있으나 실제 push는 별도 흐름이다.

### 4-3. 반품처리 작업 API

| API | 목적 | 주요 요청값 | 주요 응답값 | 권한 기준 | 하지 말 것 |
| --- | --- | --- | --- | --- | --- |
| `POST /api/returns/work/lookup` | 운송장/입고번호 기준으로 반품예정/접수 참고정보를 조회한다. | `client_id`, `warehouse_id`, `waybill_no`, `return_no`, `external_ref_no`, `work_batch_id` | lookup case, 후보 목록, 참고정보 | `client_id`, `warehouse_id` scope 검증 | Google Sheets API 직접 호출 |
| `POST /api/returns/work/manual-start` | lookup 결과가 없거나 후보가 불충분할 때 수동 처리 후보를 시작한다. | `client_id`, `warehouse_id`, 고객사/상품 확인값, 사유 | `work_id`, 시작 상태 | 내부 운영자 중심, 고객사/상품 확인 필수 | 정체불명 반품 정상 등록 |
| `POST /api/returns/work/{work_id}/scan-product` | 상품코드/바코드 스캔으로 상품과 수량 후보를 확인한다. | `barcode`, `product_code`, scan qty 후보 | 매칭 결과, `unit_qty`, 후보 상품 | `work_id` row의 `client_id` 검증 | 미등록 상품 재고 반영 |
| `POST /api/returns/work/{work_id}/judge` | 상품/수량/판정/목적 창고를 저장한다. | 판정, 상품, 수량, 목적 창고, 사유 | 판정 저장 결과, 라벨 후보, 다음 액션 | 내부 운영자 중심, 목적 창고 scope 검증 | 구글시트 push, 마감확정 |
| `POST /api/returns/work/{work_id}/photo` | 사진/메모 후보를 업무 row에 연결한다. | 파일 후보, 메모, photo type | 저장 결과 | `work_id` client scope 검증 | 판정 대체 |
| `POST /api/returns/work/{work_id}/complete` | 판정 저장 후 처리완료 상태로 전환한다. | `work_id`, 완료 옵션 | 완료 결과, 재고 이벤트 후보 상태, 라벨 출력 요청 결과 후보 | `RETURN_PROCESS` 권한 후보, client/warehouse 검증 | `current_inventory` 직접 수정 |
| `POST /api/returns/work/{work_id}/hold` | 확인 필요 반품을 보류 상태로 전환한다. | 보류 사유, 보류 창고 후보 | 보류 결과 | client/warehouse 검증 | 마감/반출 확정 |
| `GET /api/returns/work/{work_id}` | 반품처리 작업 상세를 조회한다. | `work_id` | 처리 상태, 판정, 참고정보 | row의 `client_id` 검증 | 권한 검증 전 상세 응답 |
| `GET /api/returns/work/{work_id}/logs` | 처리 작업 로그를 조회한다. | `work_id` | 상태 변경, 스캔, 라벨 요청 로그 | row의 `client_id` 검증 | 재고 이벤트 재처리 |

`lookup` 요청 후보는 다음과 같다.

- `client_id` 또는 `selected_client_id`
- `warehouse_id`
- `waybill_no`
- `return_no`
- `external_ref_no`
- `work_batch_id`

`lookup` 응답 케이스는 다음과 같다.

- `EXPECTED_AND_RECEPTION_FOUND`
- `EXPECTED_ONLY`
- `RECEPTION_ONLY`
- `NOT_FOUND`
- `ALREADY_COMPLETED`
- `MULTIPLE_CANDIDATES`

정책은 다음과 같다.

- `lookup`은 DB에 저장된 반품예정/접수 참고정보만 조회한다.
- Google Sheets API를 직접 호출하지 않는다.
- `NOT_FOUND`여도 고객사/상품이 확인되면 `manual-start` 후보로 이어질 수 있다.
- 고객사/상품이 확인되지 않은 정체불명 반품은 정상 등록하지 않는다.
- `complete`는 판정 저장/처리완료를 담당하지만, 실제 재고 반영은 `inventory_events` 정책에 따라 별도 흐름으로 연결한다.
- 라벨 출력 요청 실패가 `complete` 실패가 되면 안 된다.

### 4-4. 반품 마감 API

| API | 목적 | 주요 요청값 | 주요 응답값 | 권한 기준 | 하지 말 것 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/returns/closing/sessions` | 마감 세션 목록을 조회한다. | `client_id`, 기간, status | 세션 목록, 차이 요약 | `client_id` scope 적용 | 신규 판정 |
| `POST /api/returns/closing/sessions` | 기간/고객사/판정상태 기준 마감 세션을 생성한다. | `client_id`, 기간, 판정상태, warehouse 후보 | `closing_id`, 대상 건수 | 내부 운영자 중심, client/warehouse 검증 | 재고 직접 반영 |
| `GET /api/returns/closing/sessions/{closing_id}` | 마감 세션 상세와 대조 상태를 조회한다. | `closing_id` | 대상 목록, 스캔 결과, 차이 | 세션의 `client_id` 검증 | 권한 검증 전 상세 응답 |
| `POST /api/returns/closing/sessions/{closing_id}/scan` | 마감 대조용 상품바코드 또는 반품관리번호를 스캔한다. | barcode 또는 `return_unit_no` | 대조 결과, 남은 수량, 중복 여부 | 세션 client/warehouse 검증 | 판정 변경 |
| `POST /api/returns/closing/sessions/{closing_id}/confirm` | 차이가 없는 세션을 마감확정한다. | `closing_id`, 확정 메모 | 확정 결과 | `RETURN_CLOSE` 권한 후보 | 차이 있는 세션 확정 |
| `POST /api/returns/closing/sessions/{closing_id}/reject` | 마감 세션을 보류/반려한다. | 사유 | 반려 결과 | 내부 운영자 중심 | 대상 row 삭제 |
| `GET /api/returns/closing/sessions/{closing_id}/logs` | 마감 세션 로그를 조회한다. | `closing_id` | 스캔/상태 변경 로그 | 세션 `client_id` 검증 | 조작 기능 |

정책은 다음과 같다.

- 마감은 새로운 판정을 하지 않는다.
- 마감은 판정 완료 결과의 실물 대조다.
- 양품/폐기는 상품바코드 기준 수량 대조다.
- 리퍼/제조사반품/샘플/보류는 반품관리번호 기준 1:1 대조다.
- 차이가 있으면 `confirm`이 불가능하다.
- `confirm` 후 정정은 별도 권한 흐름으로 분리한다.

### 4-5. 반품 반출 API

| API | 목적 | 주요 요청값 | 주요 응답값 | 권한 기준 | 하지 말 것 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/returns/external-outbound/candidates` | 외부반출 대상 후보를 조회한다. | `client_id`, 기간, 판정상태, 창고 | 후보 목록 | `client_id`, `warehouse_id` scope 검증 | 판정 변경 |
| `POST /api/returns/external-outbound/batches` | 반출 묶음을 생성한다. | 대상 조건 또는 `return_unit_no` 목록 | `batch_id`, 대상 건수 | 내부 운영자 중심 | 마감 세션 대체 |
| `GET /api/returns/external-outbound/batches` | 반출 묶음 목록을 조회한다. | `client_id`, 기간, status | batch 목록 | `client_id` scope 적용 | 구글시트 push |
| `GET /api/returns/external-outbound/batches/{batch_id}` | 반출 묶음 상세를 조회한다. | `batch_id` | 대상 목록, 스캔 상태 | batch의 `client_id` 검증 | 권한 검증 전 상세 응답 |
| `POST /api/returns/external-outbound/batches/{batch_id}/scan` | 반품관리번호를 스캔해 대상 대조를 수행한다. | `return_unit_no` | 스캔 결과, 중복 여부, 남은 건수 | batch client/warehouse 검증 | 재고 직접 차감 |
| `POST /api/returns/external-outbound/batches/{batch_id}/confirm` | 대상 전량 대조 후 반출확정한다. | 확정 메모 | 확정 결과, 재고 이벤트 후보 | `RETURN_OUTBOUND` 권한 후보 | 미스캔 대상 포함 확정 |
| `POST /api/returns/external-outbound/batches/{batch_id}/cancel` | 확정 전 반출 묶음을 취소한다. | 취소 사유 | 취소 결과 | 내부 관리자 후보 | 확정 후 일반 취소 |
| `GET /api/returns/external-outbound/batches/{batch_id}/logs` | 반출 묶음 로그를 조회한다. | `batch_id` | 스캔/상태 변경 로그 | batch의 `client_id` 검증 | 조작 기능 |

정책은 다음과 같다.

- 반출은 판정 변경이 아니다.
- 반출확정 후 재고 차감은 서버 `inventory_events` 흐름으로 처리한다.
- 반품관리번호 중복 스캔을 차단한다.
- 대상 전량 대조 전 `confirm`은 불가능하다.

### 4-6. 반품 통합추적 API

| API | 목적 | 주요 요청값 | 주요 응답값 | 권한 기준 | 하지 말 것 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/returns/trace` | 운송장/반품관리번호/기간 기준으로 통합 이력을 조회한다. | 조회 조건 | trace 목록, 단계별 요약 | `client_id` scope 적용 | 판정/마감/반출 조작 |
| `GET /api/returns/trace/{trace_id}` | 단일 trace 상세를 조회한다. | `trace_id` | 접수, 예정, 처리, 라벨, 마감, 반출, 재고 이벤트 요약 | trace 대상 row의 `client_id` 검증 | 구글시트 push, 재고 재처리 |

조회 기준은 다음과 같다.

- `waybill_no`
- `original_waybill_no`
- `return_unit_no`
- `client_id`
- `product_code`
- `barcode`
- `external_ref_no`
- `work_batch_id`
- `date_from`
- `date_to`

정책은 다음과 같다.

- 읽기 전용 API다.
- 판정 변경, 마감확정, 반출확정, 구글시트 push, 재고 재처리를 제공하지 않는다.
- 여러 원장을 한 번에 보여주되, 조작 책임은 각 업무 화면으로 분리한다.

## 5. 요청/응답 공통 규칙

### 5-1. 요청 공통

- `client_id`는 서버 `AuthContext` 기준으로 검증한다.
- 고객사 사용자가 보낸 `client_id`는 신뢰하지 않는다.
- `warehouse_id`는 선택 고객사의 사용창고인지 확인한다.
- 운송장번호는 `normalized_waybill_no` 기준으로 비교한다.
- 상품코드/바코드는 `ProductScanMatchService` 기준으로 해석한다.
- import job 관련 요청은 job status를 검증한다.
- path id가 있는 요청은 조회된 row의 `client_id`를 다시 검증한다.

### 5-2. 응답 공통

응답에는 운영자가 이해할 수 있는 한글 메시지 후보를 포함한다.

공통 응답 필드 후보는 다음과 같다.

- `success`
- `result_code`
- `message`
- `data`
- `warnings`
- `next_action`
- `sound_code` 후보
- `trace_id` 또는 `request_id` 후보

개발자용 내부값은 기본 UI에 그대로 노출하지 않는다. 예를 들어 내부 stack trace, 원본 외부 인증 정보, 민감한 동기화 설정값은 응답에 포함하지 않는다.

### 5-3. 오류 공통

공통 오류 코드 후보는 다음과 같다.

- `CLIENT_SCOPE_DENIED`
- `WAREHOUSE_SCOPE_DENIED`
- `PASSWORD_CHANGE_REQUIRED`
- `NOT_FOUND`
- `MULTIPLE_CANDIDATES`
- `ALREADY_COMPLETED`
- `INVALID_STATUS`
- `MISSING_REQUIRED_JUDGEMENT`
- `UNREGISTERED_PRODUCT`
- `OVER_QTY`
- `LABEL_PRINT_FAILED`
- `INVENTORY_EVENT_PENDING`
- `INVENTORY_EVENT_FAILED`

`LABEL_PRINT_FAILED`는 판정 저장 실패와 분리한다. 라벨 출력 실패가 있어도 업무 저장 성공 여부는 별도로 판단한다.

## 6. 권한 기준

반품 API는 `docs/business/smartreturn-pro-auth-client-scope-api-policy.md` 기준을 따른다.

### 내부 운영자

- `SUPER_ADMIN`: 전체 관리 가능.
- `INTERNAL_ADMIN`: 반품자료 준비, 반품처리, 마감, 반출, 정정 후보 가능.
- `INTERNAL_WORKER`: 반품처리 작업, 스캔, 판정, 라벨 재출력 후보 가능. 시스템 설정/사용자 관리는 제한한다.

### 고객사 사용자

- `CLIENT_ADMIN`: 자기 고객사 반품 조회/접수 업로드 후보 가능. 내부 판정/마감/반출 확정은 기본 제한한다.
- `CLIENT_USER`: 자기 고객사 조회 중심.
- `READ_ONLY`: 조회만 가능.

정책은 다음과 같다.

- 고객사 사용자는 다른 고객사 반품자료를 볼 수 없다.
- 고객사 사용자는 내부 창고 재고 이벤트 상세를 제한적으로만 볼 수 있다.
- 반품 판정/마감/반출은 내부 운영자 중심이다.
- 위험 작업은 role 기본 권한에 더해 `RETURN_PROCESS`, `RETURN_CLOSE`, `RETURN_OUTBOUND` 같은 permission 후보로 확장할 수 있다.

## 7. 상태 전이 기준

### 7-1. 반품처리 작업 상태 후보

- `CREATED`
- `SCANNING`
- `JUDGED`
- `COMPLETED`
- `HOLD`
- `CANCELLED`

기본 전이는 다음과 같다.

```text
CREATED
→ SCANNING
→ JUDGED
→ COMPLETED
```

보류와 취소는 다음처럼 별도 흐름으로 둔다.

```text
CREATED/SCANNING/JUDGED
→ HOLD

CREATED/SCANNING/JUDGED
→ CANCELLED
```

### 7-2. 마감 상태 후보

- `OPEN`
- `CHECKING`
- `DIFF_FOUND`
- `READY_TO_CLOSE`
- `CLOSED`
- `REJECTED`

정책은 다음과 같다.

- 차이가 있으면 `DIFF_FOUND` 상태로 두고 `CLOSED`로 전환하지 않는다.
- 대상 전량 대조가 끝나면 `READY_TO_CLOSE` 후보가 된다.
- `CLOSED` 후 정정은 별도 권한/정정 API로 분리한다.

### 7-3. 반출 상태 후보

- `DRAFT`
- `SCANNING`
- `READY_TO_CONFIRM`
- `CONFIRMED`
- `CANCELLED`

정책은 다음과 같다.

- 상태 전이는 서버에서 검증한다.
- 이미 `COMPLETED`, `CLOSED`, `CONFIRMED` 상태인 항목은 일반 스캔/수정을 차단한다.
- 정정/취소는 별도 권한과 별도 API 흐름으로 분리한다.
- 반출 `CONFIRMED`는 판정 변경이 아니라 외부반출 확정이다.

## 8. 재고 이벤트 연결 기준

- 반품처리 작업 API는 `current_inventory`를 직접 수정하지 않는다.
- 재고 수량 변경은 `inventory_events` 생성 경로로만 처리한다.
- 반품 관련 `event_type` 후보는 다음과 같다.
  - `RETURN_JUDGEMENT`
  - `RETURN_JUDGEMENT_REVERSAL`
  - `RETURN_JUDGEMENT_CORRECTION`
  - `RETURN_EXTERNAL_OUTBOUND`
- 같은 업무/같은 line은 `idempotency_key`로 중복 반영을 막는다.
- 취소/정정은 기존 이벤트 삭제가 아니라 `reverse_event_id` 또는 correction event로 처리한다.
- 반품 마감은 수량대조/마감확정이며, 재고 이벤트 생성 시점은 후속 정책으로 분리한다.
- 반품 반출확정은 `RETURN_EXTERNAL_OUTBOUND` 이벤트 후보로 연결된다.
- `inventory_events` 생성 전에도 client/warehouse scope를 다시 검증한다.

## 9. `scan_events` 연결 기준

- `scan_events`는 스캔 입력/동기화 로그다.
- `scan_events`는 재고 원장이 아니다.
- 반품처리 작업, 반품 마감, 반품 반출 모두 `scan_events` 또는 업무별 scan log를 남길 수 있다.
- Local Agent/로컬 클라이언트는 `scan_event`를 보낼 수 있지만 `inventory_event`를 직접 만들 수 없다.
- `sound_code`는 작업자 피드백용이며 DB 저장 성공/실패와 분리해서 다룬다.
- `local_event_id` 중복 처리는 스캔 로그 멱등성으로 다루며 재고 이벤트 멱등성과 분리한다.

## 10. API 책임 분리 금지사항

- `return_expected` API에서 판정/라벨/재고반영을 하지 않는다.
- `return_work` API에서 구글시트 동기화/업로드 이력 관리를 하지 않는다.
- `return_closing` API에서 신규 판정을 하지 않는다.
- `return_external_outbound` API에서 판정 변경을 하지 않는다.
- `return_trace` API에서 조작 기능을 제공하지 않는다.
- Local Agent API에서 재고를 변경하지 않는다.
- 고객사 포털 조회 API에서 내부 정정/확정 기능을 제공하지 않는다.
- 반품처리 API가 `batch_id`만으로 업무 대상을 확정하지 않는다.

## 11. 후속 구현 순서

1. 반품 P1 테이블 컬럼 상세 문서
2. 반품 API schema 초안 문서
3. 반품 화면별 상세 설계 문서
4. 반품 API 구현
5. 반품 화면 구현
6. 통합 테스트

## 12. Codex 구현 전 체크

- 이 API가 어느 반품 화면 책임에 속하는가?
- 이 API가 다른 화면 책임을 침범하지 않는가?
- `client_id` scope를 서버에서 검증하는가?
- `warehouse_id` scope를 서버에서 검증하는가?
- path id로 조회한 row의 `client_id`를 검증하는가?
- `batch_id`를 업무 중심키로 쓰고 있지 않은가?
- 구글시트 동기화를 반품처리 API에 넣고 있지 않은가?
- 현장 스캔 중 Google API를 호출하지 않는가?
- `current_inventory`를 직접 수정하지 않는가?
- `inventory_events` idempotency를 고려했는가?
- `scan_events`와 `inventory_events`를 섞지 않았는가?
