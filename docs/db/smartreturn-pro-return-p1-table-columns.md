# SmartReturn Pro 반품 P1 테이블 핵심 컬럼 상세

이 문서는 SmartReturn Pro 신규 제작 기준이며, 기존 SmartReturn 구현기록을 그대로 따르지 않는다.

이 문서는 실제 migration 파일이 아니라 반품 MVP P1 테이블별 핵심 컬럼 상세 문서다. 이 문서에서는 SQL DDL을 작성하지 않는다. 실제 DB migration, ORM 모델, API schema는 이 문서를 기준으로 후속 작업에서 만든다.

## 1. 문서 목적

이 문서는 SmartReturn Pro 반품 MVP에 필요한 P1 테이블의 목적, 컬럼 후보, 상태값, 제약조건, 인덱스 후보, 관계를 고정한다.

반품 MVP의 DB 설계는 다음 업무가 같은 기준을 따르도록 해야 한다.

- 반품자료 준비
- 반품처리 작업
- 반품 마감
- 반품 반출
- 반품 통합추적

특히 업체 구글시트/업체 반품접수 자료, CJ/택배 반품예정 자료, 실제 반품처리 원장을 DB 구조에서도 섞지 않는 것이 핵심이다.

## 2. 공통 반품 DB 원칙

- 반품접수자료, 반품예정자료, 실제 반품처리 원장은 분리한다.
- 업체 구글시트 자료는 반품처리 원장이 아니라 업체 반품접수/회신 채널이다.
- CJ/택배 반품예정 자료는 실제 도착 후보 자료이며 상품/수량/판정 확정 자료가 아니다.
- 실제 상품/수량/판정은 반품처리 작업에서 확정한다.
- 매칭은 필수 관문이 아니라 참고/정확도 보조 기능이다.
- 매칭이 없어도 고객사/상품이 확인된 실제 도착 반품은 처리 가능하다.
- 고객사/상품이 확인되지 않은 정체불명 반품은 정상 반품자료로 등록하지 않는다.
- `batch_id`는 원본 추적/이력 보조키이며 반품처리 중심키가 아니다.
- 재고 수량 변경은 `current_inventory` 직접 수정이 아니라 `inventory_events` 경로로 처리한다.
- `scan_events` 또는 업무별 scan log는 스캔 입력 로그이며 재고 원장이 아니다.
- 모든 반품 업무 테이블은 `client_id` scope를 가진다.
- 창고/위치/반출이 필요한 테이블은 `warehouse_id` 또는 `location_id` scope를 가진다.
- 삭제보다 `active_yn=false` 또는 status 변경을 우선한다.
- 운송장번호, 상품코드, 바코드는 원본값과 비교용 정규화값을 분리한다.

## 3. 반품 P1 테이블 그룹

| 그룹 | 테이블 | 주요 책임 |
| --- | --- | --- |
| 반품예정 자료 | `return_expected_batches`, `return_expected_rows` | CJ/택배 반품예정 저장 확정 자료 |
| 업체 반품접수 자료 후보 | `vendor_return_sources`, `vendor_return_rows`, `vendor_return_update_queue` | 업체 접수/회신 채널 후보 |
| 매칭/작업 연결 | `return_match_records` | 예정/접수/처리 원장 간 후보 연결 |
| 실제 반품처리 원장 | `return_receipts`, `return_receipt_items`, `return_receipt_photos` | 실제 도착 반품의 스캔/상품/수량/판정 |
| 반품 개체/라벨 | `return_units`, `return_unit_logs`, `return_label_print_logs` | 반품관리번호, 추적 개체, 라벨 이력 |
| 반품 마감 | `return_closing_sessions`, `return_closing_items`, `return_closing_scan_logs` | 판정 완료 결과의 실물 대조와 마감 |
| 반품 반출 | `return_external_outbound_batches`, `return_external_outbound_items`, `return_external_outbound_scan_logs` | 외부반출 묶음, 스캔 대조, 반출확정 |

## 4. `return_expected_batches`

### 테이블 목적

CJ/택배 반품예정 엑셀 저장 확정 단위 또는 import job 반영 결과의 업무 배치 헤더다. `import_jobs`와 연결될 수 있지만, 업무 조회에서는 반품예정 저장 묶음으로 사용한다.

### 사용 화면/업무

- 반품자료 준비
- 반품예정 업로드 이력
- 반품예정 저장자료 조회

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 반품예정 배치 식별자 |
| `source_job_id` | 연결된 `import_jobs.id` 후보 |
| `client_id` | 고객사 식별자 |
| `source_type` | CJ/택배 등 원본 유형 |
| `source_name` | 원본 표시명 |
| `file_name` | 업로드 파일명 |
| `worksheet_name` | worksheet 이름 |
| `row_count` | 전체 row 수 |
| `inserted_count` | 추가 건수 |
| `updated_count` | 수정 건수 |
| `skipped_count` | 제외 건수 |
| `error_count` | 오류 건수 |
| `status` | 저장 상태 |
| `message` | 처리 메시지 |
| `uploaded_by` | 업로드 사용자 |
| `uploaded_at` | 업로드 시각 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `client_id`
- `source_type`
- `status`
- `uploaded_at`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `source_job_id`
- `source_name`
- `file_name`
- `worksheet_name`
- `message`
- `uploaded_by`

### 상태값 후보

- `READY`
- `SAVED`
- `PARTIAL_SAVED`
- `FAILED`
- `CANCELLED`

### 제약/인덱스 후보

- `index(client_id, uploaded_at)`
- `index(source_job_id)`
- `index(status, uploaded_at)`

### scope 기준

- `client_id` scope를 반드시 가진다.
- 창고가 필요한 경우에는 row 또는 후속 처리 단계에서 `warehouse_id`를 검증한다.

### import job 또는 inventory_events와의 관계

- `source_job_id`로 `import_jobs`와 연결할 수 있다.
- `inventory_events`와 직접 연결하지 않는다.

### 생성/수정/삭제 정책

- import save 확정 시 생성한다.
- 처리 이력 보존을 위해 일반 삭제하지 않는다.
- 이미 반품처리로 연결된 row가 있으면 배치 삭제는 제한한다.

### Codex 구현 시 주의사항

- `batch_id`는 저장 직후 바로보기/이력/원본 추적 보조키다.
- 반품처리 작업의 중심키로 쓰지 않는다.

## 5. `return_expected_rows`

### 테이블 목적

CJ/택배 반품예정의 확정된 업무용 row다. 운송장/고객사/입고후보 조회에 사용하며 `import_job_rows`의 원본/검증 역할과 분리한다.

### 사용 화면/업무

- 반품자료 준비 저장자료 조회
- 반품처리 작업의 운송장 lookup 참고정보
- 반품 통합추적

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 반품예정 row 식별자 |
| `batch_id` | `return_expected_batches.id` |
| `source_job_id` | `import_jobs.id` 후보 |
| `source_row_id` | `import_job_rows.id` 후보 |
| `client_id` | 고객사 식별자 |
| `row_no` | 원본 row 번호 |
| `row_hash` | row 중복/변경 비교 해시 |
| `source_row_key` | 외부 원본 row key |
| `source_type` | CJ/택배 등 원본 유형 |
| `waybill_no` | 반품 운송장번호 원본 |
| `waybill_no_norm` | 반품 운송장번호 비교값 |
| `original_waybill_no` | 원송장번호 원본 |
| `original_waybill_no_norm` | 원송장번호 비교값 |
| `order_no` | 주문번호 후보 |
| `sender_name` | 발송자명 후보 |
| `receiver_name` | 수령자명 후보 |
| `receiver_phone` | 수령자 연락처 후보 |
| `item_name` | 원본 상품명 |
| `item_option_name` | 원본 옵션명 |
| `qty` | 원본 수량 후보 |
| `shipper_customer_code` | 택배/화주 코드 후보 |
| `shipper_customer_name` | 택배/화주명 후보 |
| `expected_status` | 예정자료 상태 |
| `matched_status` | 매칭 상태 |
| `raw_json` | 원본/부가 payload |
| `active_yn` | 사용 여부 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `batch_id`
- `client_id`
- `source_type`
- `expected_status`
- `matched_status`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `source_job_id`
- `source_row_id`
- `row_no`
- `row_hash`
- `source_row_key`
- `waybill_no`
- `waybill_no_norm`
- `original_waybill_no`
- `original_waybill_no_norm`
- `order_no`
- `sender_name`
- `receiver_name`
- `receiver_phone`
- `item_name`
- `item_option_name`
- `qty`
- `shipper_customer_code`
- `shipper_customer_name`
- `raw_json`

### 상태값 후보

`expected_status` 후보는 다음과 같다.

- `EXPECTED`
- `RECEIVED`
- `PROCESSING`
- `COMPLETED`
- `HOLD`
- `CANCELLED`

`matched_status` 후보는 다음과 같다.

- `UNMATCHED`
- `AUTO_MATCHED`
- `CANDIDATE_MATCHED`
- `MANUAL_MATCHED`
- `EXPECTED_ONLY`

### 제약/인덱스 후보

- `index(client_id, waybill_no_norm)`
- `index(client_id, expected_status)`
- `index(batch_id, row_no)`
- `index(source_job_id, source_row_id)`
- `index(row_hash)`
- `index(source_row_key)`

### scope 기준

- `client_id` scope를 반드시 가진다.
- 창고 확정은 반품처리 작업 또는 재고 이벤트 단계에서 판단한다.

### import job 또는 inventory_events와의 관계

- `source_job_id`, `source_row_id`로 import job 결과와 연결할 수 있다.
- 재고 이벤트와 직접 연결하지 않는다.

### 생성/수정/삭제 정책

- 검증된 `import_job_rows`를 업무 테이블에 반영할 때 생성한다.
- 처리 연결 이후에는 물리 삭제하지 않는다.
- 잘못 저장된 row는 `active_yn=false` 또는 `expected_status=CANCELLED` 후보로 처리한다.

### Codex 구현 시 주의사항

- 상품명/수량은 후보/참고값이다.
- 실제 상품/수량/판정은 `return_receipt_items`에서 확정한다.
- 원본 row 보존은 `import_job_rows`가 담당하고, 이 테이블은 업무용 expected row로 유지한다.

## 6. `vendor_return_sources`

### 테이블 목적

업체 구글시트/업체 접수자료 소스 설정 후보 테이블이다. 1차 MVP에서는 실구현 제외 가능하지만, 내부 반품입고예정 화면과 섞지 않기 위해 후보 구조를 문서화한다.

### 사용 화면/업무

- 업체 반품접수 관리 후보
- 구글시트/업체자료 동기화 후보
- 반품처리 작업의 참고정보 후보

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 업체 접수 source 식별자 |
| `client_id` | 고객사 식별자 |
| `source_type` | source 유형 |
| `source_name` | source 표시명 |
| `channel_type` | 업체 채널 유형 |
| `spreadsheet_id` | 구글시트 식별자 후보 |
| `default_worksheet` | 기본 worksheet 후보 |
| `header_row_index` | 헤더 row 번호 후보 |
| `header_aliases_json` | 헤더 매핑 후보 |
| `active_yn` | 사용 여부 |
| `last_pull_at` | 마지막 수신 시각 |
| `last_push_at` | 마지막 회신 시각 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `client_id`
- `source_type`
- `source_name`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `channel_type`
- `spreadsheet_id`
- `default_worksheet`
- `header_row_index`
- `header_aliases_json`
- `last_pull_at`
- `last_push_at`

### 상태값 후보

`source_type` 후보는 다음과 같다.

- `VENDOR_GOOGLE_SHEET`
- `VENDOR_EXCEL`
- `VENDOR_PORTAL`
- `FUTURE_API`

`channel_type` 후보는 다음과 같다.

- `ONLINE`
- `GROUP_BUY`
- `ETC`

### 제약/인덱스 후보

- `index(client_id, source_type)`
- `index(active_yn)`

### scope 기준

- `client_id` scope를 가진다.

### import job 또는 inventory_events와의 관계

- 업체 접수 동기화가 import job을 사용할 수 있는지는 후속 설계에서 결정한다.
- `inventory_events`와 직접 연결하지 않는다.

### 생성/수정/삭제 정책

- 1차 MVP에서는 실구현 제외 가능하다.
- 삭제보다 `active_yn=false`를 우선한다.
- 인증/연동 민감정보는 별도 보안 정책으로 분리한다.

### Codex 구현 시 주의사항

- 내부 반품입고예정 화면에는 업체 구글시트 동기화를 넣지 않는다.
- `spreadsheet_id`는 공통코드에 저장하지 않는다.
- `google-service-account.json`은 인증 파일이지 업체별 `spreadsheet_id` 저장소가 아니다.
- 현장 스캔 중 Google Sheets API를 직접 호출하지 않는다.

## 7. `vendor_return_rows`

### 테이블 목적

업체 반품접수 원본 row 후보 테이블이다. 업체가 입력한 CS/사유/요청/상품후보 정보를 보존하며 실제 반품처리 원장이 아니다.

### 사용 화면/업무

- 업체 반품접수 관리 후보
- 반품처리 작업 참고정보
- 반품 통합추적

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 업체 접수 row 식별자 |
| `source_id` | `vendor_return_sources.id` |
| `client_id` | 고객사 식별자 |
| `worksheet_name` | worksheet 이름 |
| `row_no` | 원본 row 번호 |
| `row_key` | 외부 원본 row key |
| `row_hash` | row 중복/변경 비교 해시 |
| `customer_name` | 고객명 후보 |
| `customer_phone` | 고객 연락처 후보 |
| `order_no` | 주문번호 후보 |
| `waybill_no` | 운송장번호 원본 |
| `waybill_no_norm` | 운송장번호 비교값 |
| `original_waybill_no` | 원송장번호 후보 |
| `return_waybill_no` | 반품 운송장 후보 |
| `product_code` | 업체 입력 상품코드 후보 |
| `product_name` | 업체 입력 상품명 후보 |
| `qty` | 업체 입력 수량 후보 |
| `return_reason` | 반품 사유 후보 |
| `request_status` | 업체 요청 상태 |
| `inbound_status` | 내부 입고 연결 상태 후보 |
| `processed_status` | 처리/회신 상태 |
| `raw_json` | 원본 row |
| `pulled_at` | 수신 시각 |
| `active_yn` | 사용 여부 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `source_id`
- `client_id`
- `processed_status`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `worksheet_name`
- `row_no`
- `row_key`
- `row_hash`
- `customer_name`
- `customer_phone`
- `order_no`
- `waybill_no`
- `waybill_no_norm`
- `original_waybill_no`
- `return_waybill_no`
- `product_code`
- `product_name`
- `qty`
- `return_reason`
- `request_status`
- `inbound_status`
- `raw_json`
- `pulled_at`

### 상태값 후보

`processed_status` 후보는 다음과 같다.

- `NEW`
- `MATCHED`
- `PROCESSING`
- `COMPLETED`
- `UPDATE_QUEUED`
- `UPDATED`
- `HOLD`
- `CANCELLED`

### 제약/인덱스 후보

- `index(client_id, waybill_no_norm)`
- `index(source_id, worksheet_name, row_no)`
- `index(row_key)`
- `index(row_hash)`
- `index(processed_status)`

### scope 기준

- `client_id` scope를 가진다.
- source와 row의 `client_id`가 충돌하면 저장하지 않는다.

### import job 또는 inventory_events와의 관계

- 원본 수신은 import job을 사용할 수도 있으나 1차 MVP에서는 후보로만 둔다.
- `inventory_events`와 직접 연결하지 않는다.

### 생성/수정/삭제 정책

- 동기화 또는 수동 등록 시 생성한다.
- row 변경은 원본 추적을 위해 `row_hash`, `raw_json`, `pulled_at`을 함께 갱신한다.
- 삭제보다 `active_yn=false`를 우선한다.

### Codex 구현 시 주의사항

- `row_no`는 위치 추적 후보지만 단독 기준으로 믿지 않는다.
- 업체 접수자료만으로 실제 도착을 보장하지 않는다.
- 상품정보는 후보/참고값이다.

## 8. `vendor_return_update_queue`

### 테이블 목적

판정 결과를 업체 구글시트 등 외부 채널로 회신하기 위한 큐 후보 테이블이다. 판정 저장과 외부 push를 분리한다.

### 사용 화면/업무

- 업체 회신 큐 관리 후보
- 반품 통합추적의 회신 상태 표시 후보

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 회신 큐 식별자 |
| `vendor_row_id` | 업체 접수 row |
| `receipt_id` | 반품처리 헤더 |
| `receipt_item_id` | 반품처리 line |
| `client_id` | 고객사 식별자 |
| `source_id` | 업체 source |
| `worksheet_name` | 회신 대상 worksheet |
| `row_no` | 회신 대상 row 번호 후보 |
| `target_key` | 회신 대상 key 후보 |
| `update_payload_json` | 회신 payload |
| `status` | 큐 상태 |
| `retry_count` | 재시도 횟수 |
| `error_message` | 오류 메시지 |
| `created_at` | 생성 시각 |
| `pushed_at` | push 완료 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `client_id`
- `status`
- `retry_count`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `vendor_row_id`
- `receipt_id`
- `receipt_item_id`
- `source_id`
- `worksheet_name`
- `row_no`
- `target_key`
- `update_payload_json`
- `error_message`
- `pushed_at`

### 상태값 후보

- `PENDING`
- `PUSHED`
- `FAILED`
- `CONFLICT`
- `SKIPPED`
- `CANCELLED`

### 제약/인덱스 후보

- `unique(receipt_id, vendor_row_id)`
- `index(client_id, status)`
- `index(source_id, worksheet_name, row_no)`

### scope 기준

- `client_id` scope를 가진다.

### import job 또는 inventory_events와의 관계

- `inventory_events`와 직접 연결하지 않는다.
- 판정 완료 이후 회신 후보로 생성될 수 있으나 판정 저장 성공 조건이 아니다.

### 생성/수정/삭제 정책

- 판정 완료 후 큐를 만들 수 있다.
- 실제 Google Sheets push는 별도 수동/후속 흐름이다.
- 실패 큐는 retry 또는 `CANCELLED` 처리 후보로 둔다.

### Codex 구현 시 주의사항

- 큐 생성 실패가 판정 저장 실패가 되면 안 된다.
- 충돌 감지와 재시도 정책은 후속 단계에서 확정한다.

## 9. `return_match_records`

### 테이블 목적

반품예정 자료와 업체 반품접수 자료 또는 실제 처리 원장 간 후보/수동 매칭 결과를 저장한다. 매칭은 필수 관문이 아니라 참고/정확도 보조 기능이다.

### 사용 화면/업무

- 반품자료 준비의 매칭 후보 조회
- 반품처리 작업 lookup 참고정보
- 반품 통합추적

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 매칭 식별자 |
| `client_id` | 고객사 식별자 |
| `expected_row_id` | 반품예정 row |
| `vendor_row_id` | 업체 접수 row |
| `receipt_id` | 실제 반품처리 헤더 |
| `waybill_no` | 매칭 기준 운송장 원본 |
| `waybill_no_norm` | 매칭 기준 운송장 비교값 |
| `match_status` | 매칭 상태 |
| `match_basis` | 매칭 근거 |
| `match_score` | 자동매칭 점수 후보 |
| `candidate_json` | 복수 후보 정보 |
| `manual_note` | 수동 매칭 메모 |
| `confirmed_by` | 확정 사용자 |
| `confirmed_at` | 확정 시각 |
| `active_yn` | 사용 여부 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `client_id`
- `match_status`
- `match_basis`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `expected_row_id`
- `vendor_row_id`
- `receipt_id`
- `waybill_no`
- `waybill_no_norm`
- `match_score`
- `candidate_json`
- `manual_note`
- `confirmed_by`
- `confirmed_at`

### 상태값 후보

`match_status` 후보는 다음과 같다.

- `AUTO_MATCHED`
- `CANDIDATE_MATCHED`
- `MANUAL_MATCHED`
- `UNMATCHED`
- `EXPECTED_ONLY`
- `RECEPTION_ONLY`
- `REJECTED`

`match_basis` 후보는 다음과 같다.

- `WAYBILL`
- `ORDER_NO`
- `CUSTOMER_NAME`
- `PHONE`
- `PRODUCT`
- `MANUAL`

### 제약/인덱스 후보

- `index(client_id, waybill_no_norm)`
- `index(expected_row_id)`
- `index(vendor_row_id)`
- `index(receipt_id)`
- `index(match_status)`

### scope 기준

- `client_id` scope를 가진다.
- 연결 대상 row들의 `client_id`가 서로 달라서는 안 된다.

### import job 또는 inventory_events와의 관계

- import job과 직접 연결하지 않고 expected/vendor row를 통해 간접 연결한다.
- `inventory_events`와 직접 연결하지 않는다.

### 생성/수정/삭제 정책

- 자동 후보, 수동 확정, 거절 상태를 모두 기록할 수 있다.
- 삭제보다 `active_yn=false` 또는 `match_status=REJECTED` 후보를 우선한다.

### Codex 구현 시 주의사항

- `AUTO_MATCHED`는 확정이 아니라 후보일 수 있다.
- 복수 후보는 `candidate_json`에 보관하고 작업자/관리자 선택으로 확정한다.
- 매칭이 없어도 고객사/상품이 확인된 실제 반품은 처리 가능하다.

## 10. `return_receipts`

### 테이블 목적

실제 반품처리 작업 헤더다. 창고에서 실제 도착한 반품을 처리하는 원장이다.

### 사용 화면/업무

- 반품처리 작업
- 반품 통합추적
- 재고 이벤트 생성 후보의 source 헤더

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 반품처리 식별자 |
| `receipt_no` | 내부 반품처리 번호 |
| `client_id` | 고객사 식별자 |
| `warehouse_id` | 처리 창고 |
| `work_date` | 작업일 |
| `waybill_no` | 운송장번호 원본 |
| `waybill_no_norm` | 운송장번호 비교값 |
| `original_waybill_no` | 원송장번호 원본 |
| `original_waybill_no_norm` | 원송장번호 비교값 |
| `return_no` | 반품입고번호 후보 |
| `source_type` | 처리 시작 source 유형 |
| `expected_row_id` | 반품예정 row 후보 |
| `vendor_row_id` | 업체 접수 row 후보 |
| `match_record_id` | 매칭 기록 후보 |
| `receipt_status` | 처리 상태 |
| `operator_id` | 작업자 |
| `expected_total_qty` | 예정 총 수량 후보 |
| `scanned_total_qty` | 스캔 총 수량 |
| `judged_total_qty` | 판정 총 수량 |
| `unknown_scan_count` | 미확인 스캔 수 |
| `hold_reason` | 보류 사유 |
| `intake_note` | 입고 메모 |
| `completed_at` | 처리완료 시각 |
| `inventory_status` | 재고 이벤트 연결 상태 |
| `raw_json` | 부가 payload |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `receipt_no`
- `client_id`
- `warehouse_id`
- `work_date`
- `receipt_status`
- `inventory_status`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `waybill_no`
- `waybill_no_norm`
- `original_waybill_no`
- `original_waybill_no_norm`
- `return_no`
- `source_type`
- `expected_row_id`
- `vendor_row_id`
- `match_record_id`
- `operator_id`
- `expected_total_qty`
- `hold_reason`
- `intake_note`
- `completed_at`
- `raw_json`

### 상태값 후보

`receipt_status` 후보는 다음과 같다.

- `CREATED`
- `SCANNING`
- `JUDGED`
- `COMPLETED`
- `HOLD`
- `CANCELLED`

`inventory_status` 후보는 다음과 같다.

- `NOT_READY`
- `READY`
- `EVENT_CREATED`
- `APPLIED`
- `FAILED`
- `SKIPPED`

### 제약/인덱스 후보

- `unique(receipt_no)`
- `index(client_id, waybill_no_norm)`
- `index(client_id, receipt_status)`
- `index(client_id, work_date)`
- `index(warehouse_id, work_date)`

### scope 기준

- `client_id`와 `warehouse_id` scope를 모두 가진다.
- `warehouse_id`는 선택 고객사의 사용창고여야 한다.

### import job 또는 inventory_events와의 관계

- `expected_row_id`, `vendor_row_id`, `match_record_id`로 원본 후보와 연결한다.
- 처리완료 후 `inventory_events.source_type=RETURN_RECEIPT` 후보로 연결할 수 있다.

### 생성/수정/삭제 정책

- 운송장 lookup 또는 수동 시작 시 생성 후보가 된다.
- 처리 완료 후 일반 삭제를 금지한다.
- 취소/정정은 별도 상태와 권한 흐름으로 분리한다.

### Codex 구현 시 주의사항

- 실제 반품처리 원장이다.
- `expected_row_id`, `vendor_row_id`, `match_record_id`는 nullable 가능하다.
- 둘 다 없어도 고객사/상품이 확인된 수동 처리 후보가 될 수 있다.
- 고객사/상품이 확인되지 않은 정체불명 반품은 정상 등록하지 않는다.

## 11. `return_receipt_items`

### 테이블 목적

실제 반품처리 상품/판정 line이다. 최종 상품, 수량, 판정, 목적 창고의 기준이다.

### 사용 화면/업무

- 반품처리 작업
- 반품 마감 대상 후보
- 재고 이벤트 source line 후보
- 반품 통합추적

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 반품처리 line 식별자 |
| `receipt_id` | `return_receipts.id` |
| `client_id` | 고객사 식별자 |
| `product_id` | 확정 상품 |
| `product_code` | 확정 상품코드 |
| `product_name` | 확정 상품명 |
| `barcode` | 스캔/확정 바코드 후보 |
| `expected_qty` | 예정 수량 후보 |
| `scanned_qty` | 스캔 수량 |
| `judged_qty` | 판정 수량 |
| `judgement_code` | 판정 코드 |
| `judgement_reason_code` | 판정 사유 코드 |
| `destination_warehouse_id` | 목적 창고 |
| `destination_location_id` | 목적 위치 후보 |
| `item_status` | line 상태 |
| `label_required_yn` | 라벨 필요 여부 |
| `return_unit_required_yn` | 반품관리번호 필요 여부 |
| `memo` | 메모 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `receipt_id`
- `client_id`
- `scanned_qty`
- `judged_qty`
- `item_status`
- `label_required_yn`
- `return_unit_required_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `product_id`
- `product_code`
- `product_name`
- `barcode`
- `expected_qty`
- `judgement_code`
- `judgement_reason_code`
- `destination_warehouse_id`
- `destination_location_id`
- `memo`

### 상태값 후보

`judgement_code` 후보는 다음과 같다.

- `GOOD`
- `HOLD`
- `DISPOSAL`
- `REFURB_A`
- `REFURB_B`
- `REFURB_C`
- `MANUFACTURER_RETURN`
- `SAMPLE`

`item_status` 후보는 다음과 같다.

- `PENDING`
- `SCANNED`
- `JUDGED`
- `COMPLETED`
- `HOLD`
- `CANCELLED`

### 제약/인덱스 후보

- `index(receipt_id)`
- `index(client_id, product_id)`
- `index(client_id, judgement_code)`
- `index(destination_warehouse_id)`

### scope 기준

- `client_id` scope를 가진다.
- `destination_warehouse_id`는 선택 고객사의 사용창고여야 한다.

### import job 또는 inventory_events와의 관계

- 반품예정 상품정보가 아니라 실제 확인된 상품 기준이다.
- 재고 이벤트 생성 시 `inventory_events.source_line_id` 후보가 된다.

### 생성/수정/삭제 정책

- 반품처리 작업 중 상품 스캔/선택/판정 시 생성 또는 갱신한다.
- 처리완료 후 일반 수정은 제한한다.
- 정정은 별도 권한과 correction 흐름으로 처리한다.

### Codex 구현 시 주의사항

- 미등록 상품은 `product_id` 없이 임시 후보로 둘 수 있으나 재고반영 대상이 아니다.
- 판정별 목적 창고는 자동 추천하되 작업자 수정 가능 후보를 둔다.

## 12. `return_receipt_photos`

### 테이블 목적

반품 처리 중 사진/증빙 파일 메타데이터를 저장한다.

### 사용 화면/업무

- 반품처리 작업
- 반품 통합추적

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 사진 식별자 |
| `receipt_id` | 반품처리 헤더 |
| `receipt_item_id` | 반품처리 line 후보 |
| `client_id` | 고객사 식별자 |
| `file_name` | 원본 파일명 |
| `stored_file_name` | 저장 파일명 |
| `relative_path` | 상대 저장 경로 |
| `mime_type` | MIME type |
| `size_bytes` | 파일 크기 |
| `photo_type` | 사진 유형 |
| `memo` | 메모 |
| `uploaded_by` | 업로드 사용자 |
| `created_at` | 생성 시각 |
| `active_yn` | 사용 여부 |

### 필수 컬럼

- `id`
- `receipt_id`
- `client_id`
- `file_name`
- `photo_type`
- `created_at`
- `active_yn`

### nullable 허용 후보

- `receipt_item_id`
- `stored_file_name`
- `relative_path`
- `mime_type`
- `size_bytes`
- `memo`
- `uploaded_by`

### 상태값 후보

`photo_type` 후보는 다음과 같다.

- `WAYBILL`
- `PRODUCT`
- `DAMAGE`
- `COMPONENT`
- `ETC`

### 제약/인덱스 후보

- `index(receipt_id)`
- `index(receipt_item_id)`
- `index(client_id, created_at)`

### scope 기준

- `client_id` scope를 가진다.

### import job 또는 inventory_events와의 관계

- import job, inventory event와 직접 연결하지 않는다.

### 생성/수정/삭제 정책

- 파일 업로드 성공 후 메타데이터를 생성한다.
- 삭제보다 `active_yn=false`를 우선한다.

### Codex 구현 시 주의사항

- 원본 파일 저장 위치와 접근권한은 후속 파일 정책에서 확정한다.
- 사진 실패가 판정 저장 실패가 되면 안 되는지 여부는 업무별로 별도 정책화한다.

## 13. `return_units`

### 테이블 목적

반품관리번호가 필요한 개별 반품 단위체를 추적한다. 리퍼/제조사반품/샘플/보류 등 1:1 추적 대상의 기준이다.

### 사용 화면/업무

- 반품처리 작업의 라벨/반품관리번호 생성
- 반품 마감의 1:1 대조
- 반품 반출의 스캔 검수
- 반품 통합추적

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 반품 단위체 식별자 |
| `return_unit_no` | 반품관리번호 |
| `client_id` | 고객사 식별자 |
| `receipt_id` | 반품처리 헤더 |
| `receipt_item_id` | 반품처리 line |
| `product_id` | 상품 식별자 |
| `product_code` | 상품코드 |
| `product_name` | 상품명 |
| `waybill_no` | 운송장번호 원본 |
| `waybill_no_norm` | 운송장번호 비교값 |
| `judgement_code` | 판정 코드 |
| `unit_status` | 단위체 상태 |
| `warehouse_id` | 현재 창고 후보 |
| `location_id` | 현재 위치 후보 |
| `label_printed_at` | 라벨 출력 시각 |
| `disposed_at` | 폐기 처리 시각 후보 |
| `memo` | 메모 |
| `created_by` | 생성 사용자 |
| `updated_by` | 수정 사용자 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `return_unit_no`
- `client_id`
- `receipt_id`
- `receipt_item_id`
- `judgement_code`
- `unit_status`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `product_id`
- `product_code`
- `product_name`
- `waybill_no`
- `waybill_no_norm`
- `warehouse_id`
- `location_id`
- `label_printed_at`
- `disposed_at`
- `memo`
- `created_by`
- `updated_by`

### 상태값 후보

- `CREATED`
- `STORED`
- `HOLD`
- `READY_TO_OUTBOUND`
- `OUTBOUND_RESERVED`
- `OUTBOUND_COMPLETED`
- `DISPOSED`
- `CANCELLED`

### 제약/인덱스 후보

- `unique(return_unit_no)`
- `index(client_id, return_unit_no)`
- `index(receipt_id)`
- `index(receipt_item_id)`
- `index(client_id, judgement_code, unit_status)`

### scope 기준

- `client_id` scope를 가진다.
- 창고 추적이 필요한 경우 `warehouse_id`와 `location_id`를 가진다.

### import job 또는 inventory_events와의 관계

- import job과 직접 연결하지 않는다.
- 반출확정 또는 판정 재고 이벤트의 source 후보가 될 수 있다.

### 생성/수정/삭제 정책

- `return_receipt_items` 판정 결과에 따라 생성한다.
- 처리 이후 물리 삭제하지 않고 상태 변경으로 추적한다.
- 재출력은 기존 `return_unit_no`를 다시 출력한다.

### Codex 구현 시 주의사항

- `GOOD`은 기본적으로 `return_unit` 생성 대상이 아니다.
- `REFURB_A`, `REFURB_B`, `REFURB_C`, `MANUFACTURER_RETURN`, `SAMPLE`은 기본 생성 대상이다.
- `HOLD`, `DISPOSAL`은 설정에 따라 생성 여부를 결정한다.

## 14. `return_unit_logs`

### 테이블 목적

반품 단위체 상태 변경/스캔/라벨/반출 이력을 기록한다.

### 사용 화면/업무

- 반품처리 작업
- 반품 마감
- 반품 반출
- 반품 통합추적

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 로그 식별자 |
| `return_unit_id` | 반품 단위체 |
| `return_unit_no` | 반품관리번호 |
| `client_id` | 고객사 식별자 |
| `event_type` | 이벤트 유형 |
| `from_status` | 변경 전 상태 |
| `to_status` | 변경 후 상태 |
| `warehouse_id` | 창고 후보 |
| `location_id` | 위치 후보 |
| `scanned_value` | 스캔값 후보 |
| `memo` | 메모 |
| `raw_json` | 부가 payload |
| `created_by` | 생성 사용자 |
| `created_at` | 생성 시각 |

### 필수 컬럼

- `id`
- `return_unit_id`
- `return_unit_no`
- `client_id`
- `event_type`
- `created_at`

### nullable 허용 후보

- `from_status`
- `to_status`
- `warehouse_id`
- `location_id`
- `scanned_value`
- `memo`
- `raw_json`
- `created_by`

### 상태값 후보

`event_type` 후보는 다음과 같다.

- `CREATED`
- `LABEL_PRINTED`
- `LABEL_REPRINTED`
- `STATUS_CHANGED`
- `OUTBOUND_SCANNED`
- `OUTBOUND_CONFIRMED`
- `DISPOSED`
- `CANCELLED`

### 제약/인덱스 후보

- `index(return_unit_id)`
- `index(client_id, return_unit_no)`
- `index(event_type, created_at)`

### scope 기준

- `client_id` scope를 가진다.

### import job 또는 inventory_events와의 관계

- `inventory_events`와 직접 동일시하지 않는다.
- 필요 시 inventory event id 연결은 후속 설계에서 검토한다.

### 생성/수정/삭제 정책

- 이력 로그는 생성 후 수정하지 않는 것을 원칙으로 한다.
- 잘못된 로그 정정은 보정 로그 후보로 처리한다.

### Codex 구현 시 주의사항

- 이 테이블은 반품 단위체 이력이지 재고 원장이 아니다.

## 15. `return_label_print_logs`

### 테이블 목적

반품관리번호 라벨 출력/실패/재출력 이력을 기록한다.

### 사용 화면/업무

- 반품처리 작업
- 라벨 재출력
- 반품 통합추적

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 라벨 출력 로그 식별자 |
| `client_id` | 고객사 식별자 |
| `receipt_id` | 반품처리 헤더 |
| `receipt_item_id` | 반품처리 line |
| `return_unit_id` | 반품 단위체 |
| `return_unit_no` | 반품관리번호 |
| `label_type` | 라벨 유형 |
| `print_status` | 출력 상태 |
| `printer_name` | 프린터명 후보 |
| `requested_by` | 요청 사용자 |
| `requested_at` | 요청 시각 |
| `printed_at` | 출력 시각 |
| `error_message` | 오류 메시지 |
| `retry_count` | 재시도 횟수 |
| `raw_json` | Local Agent 응답 등 부가 payload |

### 필수 컬럼

- `id`
- `client_id`
- `print_status`
- `requested_at`

### nullable 허용 후보

- `receipt_id`
- `receipt_item_id`
- `return_unit_id`
- `return_unit_no`
- `label_type`
- `printer_name`
- `requested_by`
- `printed_at`
- `error_message`
- `retry_count`
- `raw_json`

### 상태값 후보

- `PRINT_NOT_REQUIRED`
- `PRINT_PENDING`
- `PRINTED`
- `PRINT_FAILED`
- `DRY_RUN`
- `REPRINTED`
- `SKIPPED`

### 제약/인덱스 후보

- `index(client_id, print_status)`
- `index(return_unit_no)`
- `index(receipt_id)`

### scope 기준

- `client_id` scope를 가진다.

### import job 또는 inventory_events와의 관계

- import job과 직접 연결하지 않는다.
- `inventory_events`와 직접 연결하지 않는다.

### 생성/수정/삭제 정책

- 출력 요청마다 로그를 생성한다.
- 실패 로그도 삭제하지 않고 재시도 로그를 추가한다.

### Codex 구현 시 주의사항

- 라벨 출력 실패는 판정 저장 실패가 아니다.
- 재출력은 새 번호 생성이 아니라 기존 번호 재출력이다.
- Local Agent 실패와 DB 저장은 분리한다.

## 16. `return_closing_sessions`

### 테이블 목적

반품 마감 세션 헤더다. 기간/고객사/상태 기준으로 판정 완료 결과를 대조하고 마감한다.

### 사용 화면/업무

- 반품 마감
- 반품 통합추적

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 마감 세션 식별자 |
| `closing_no` | 마감 번호 |
| `client_id` | 고객사 식별자 |
| `warehouse_id` | 마감 대상 창고 후보 |
| `date_from` | 대상 시작일 |
| `date_to` | 대상 종료일 |
| `closing_status` | 마감 상태 |
| `target_judgement_codes` | 대상 판정 코드 목록 후보 |
| `expected_total_qty` | 대상 수량 |
| `scanned_total_qty` | 스캔 수량 |
| `mismatch_count` | 차이 건수 |
| `confirmed_by` | 확정 사용자 |
| `confirmed_at` | 확정 시각 |
| `memo` | 메모 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `closing_no`
- `client_id`
- `date_from`
- `date_to`
- `closing_status`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `warehouse_id`
- `target_judgement_codes`
- `confirmed_by`
- `confirmed_at`
- `memo`

### 상태값 후보

- `OPEN`
- `CHECKING`
- `DIFF_FOUND`
- `READY_TO_CLOSE`
- `CLOSED`
- `REJECTED`
- `CANCELLED`

### 제약/인덱스 후보

- `unique(closing_no)`
- `index(client_id, date_from, date_to)`
- `index(warehouse_id, closing_status)`

### scope 기준

- `client_id` scope를 가진다.
- 창고별 마감이면 `warehouse_id` scope를 가진다.

### import job 또는 inventory_events와의 관계

- import job과 직접 연결하지 않는다.
- 마감은 대조/확정이며 재고 이벤트 생성 시점은 후속 정책으로 분리한다.

### 생성/수정/삭제 정책

- 마감 세션 생성 후 스캔/대조 결과에 따라 상태 전이한다.
- 차이가 있으면 `CLOSED` 처리하지 않는다.
- 마감 후 정정은 별도 권한 흐름으로 분리한다.

### Codex 구현 시 주의사항

- 마감은 새로운 판정을 하지 않는다.
- 구글시트 동기화 화면이 아니다.

## 17. `return_closing_items`

### 테이블 목적

마감 대상 상품/판정/단위체별 대조 결과다.

### 사용 화면/업무

- 반품 마감
- 반품 통합추적

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 마감 item 식별자 |
| `closing_id` | 마감 세션 |
| `client_id` | 고객사 식별자 |
| `product_id` | 상품 식별자 후보 |
| `product_code` | 상품코드 후보 |
| `judgement_code` | 판정 코드 |
| `return_unit_id` | 반품 단위체 후보 |
| `return_unit_no` | 반품관리번호 후보 |
| `expected_qty` | 기대 수량 |
| `scanned_qty` | 스캔 수량 |
| `item_status` | 대조 상태 |
| `mismatch_reason` | 차이 사유 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `closing_id`
- `client_id`
- `judgement_code`
- `expected_qty`
- `scanned_qty`
- `item_status`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `product_id`
- `product_code`
- `return_unit_id`
- `return_unit_no`
- `mismatch_reason`

### 상태값 후보

- `PENDING`
- `MATCHED`
- `SHORT`
- `OVER`
- `MISMATCH`
- `HOLD`
- `CONFIRMED`

### 제약/인덱스 후보

- `index(closing_id)`
- `index(client_id, product_id)`
- `index(return_unit_no)`
- `index(judgement_code, item_status)`

### scope 기준

- `client_id` scope를 가진다.

### import job 또는 inventory_events와의 관계

- import job과 직접 연결하지 않는다.
- 재고 이벤트와 직접 동일시하지 않는다.

### 생성/수정/삭제 정책

- 마감 세션 생성 시 대상 후보로 생성한다.
- 마감 스캔에 따라 `scanned_qty`, `item_status`를 갱신한다.
- 확정 후 일반 수정은 제한한다.

### Codex 구현 시 주의사항

- `GOOD`/`DISPOSAL`은 상품바코드 수량 대조 중심이다.
- `REFURB_A`, `REFURB_B`, `REFURB_C`, `MANUFACTURER_RETURN`, `SAMPLE`, `HOLD`는 반품관리번호 1:1 대조 중심이다.

## 18. `return_closing_scan_logs`

### 테이블 목적

반품 마감 중 스캔 로그를 저장한다.

### 사용 화면/업무

- 반품 마감
- 반품 통합추적

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 스캔 로그 식별자 |
| `closing_id` | 마감 세션 |
| `closing_item_id` | 마감 item 후보 |
| `client_id` | 고객사 식별자 |
| `scan_value` | 스캔값 |
| `scan_type` | 스캔 유형 |
| `result_code` | 결과 코드 |
| `sound_code` | 작업자 피드백 후보 |
| `message` | 표시 메시지 |
| `operator_id` | 작업자 |
| `created_at` | 생성 시각 |

### 필수 컬럼

- `id`
- `closing_id`
- `client_id`
- `scan_value`
- `scan_type`
- `result_code`
- `created_at`

### nullable 허용 후보

- `closing_item_id`
- `sound_code`
- `message`
- `operator_id`

### 상태값 후보

`scan_type` 후보는 다음과 같다.

- `PRODUCT_BARCODE`
- `RETURN_UNIT_NO`

`result_code` 후보는 다음과 같다.

- `OK`
- `DUPLICATE`
- `NOT_FOUND`
- `MISMATCH`
- `OVER`
- `ERROR`

### 제약/인덱스 후보

- `index(closing_id)`
- `index(client_id, created_at)`
- `index(result_code, created_at)`

### scope 기준

- `client_id` scope를 가진다.

### import job 또는 inventory_events와의 관계

- `scan_events` 성격의 업무별 로그이며 재고 원장이 아니다.

### 생성/수정/삭제 정책

- 스캔마다 생성한다.
- 생성 후 수정하지 않는 것을 원칙으로 한다.

### Codex 구현 시 주의사항

- `sound_code`는 작업자 피드백용이며 DB 저장 성공/실패와 분리한다.

## 19. `return_external_outbound_batches`

### 테이블 목적

반품 외부반출 묶음 헤더다.

### 사용 화면/업무

- 반품 반출
- 반품 통합추적

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 반출 batch 식별자 |
| `outbound_no` | 반출 번호 |
| `client_id` | 고객사 식별자 |
| `warehouse_id` | 반출 창고 |
| `destination_type` | 반출 대상 유형 |
| `destination_name` | 반출처명 |
| `outbound_status` | 반출 상태 |
| `target_judgement_codes` | 대상 판정 코드 목록 후보 |
| `expected_total_qty` | 대상 수량 |
| `scanned_total_qty` | 스캔 수량 |
| `confirmed_by` | 확정 사용자 |
| `confirmed_at` | 확정 시각 |
| `memo` | 메모 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `outbound_no`
- `client_id`
- `warehouse_id`
- `destination_type`
- `outbound_status`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `destination_name`
- `target_judgement_codes`
- `confirmed_by`
- `confirmed_at`
- `memo`

### 상태값 후보

`destination_type` 후보는 다음과 같다.

- `MANUFACTURER`
- `REFURB_VENDOR`
- `SAMPLE_DESTINATION`
- `DISPOSAL_VENDOR`
- `ETC`

`outbound_status` 후보는 다음과 같다.

- `DRAFT`
- `SCANNING`
- `READY_TO_CONFIRM`
- `CONFIRMED`
- `CANCELLED`

### 제약/인덱스 후보

- `unique(outbound_no)`
- `index(client_id, outbound_status)`
- `index(warehouse_id, outbound_status)`

### scope 기준

- `client_id`와 `warehouse_id` scope를 가진다.
- `warehouse_id`는 선택 고객사의 사용창고여야 한다.

### import job 또는 inventory_events와의 관계

- import job과 직접 연결하지 않는다.
- 반출확정 후 `inventory_events`의 `RETURN_EXTERNAL_OUTBOUND` 후보로 연결된다.

### 생성/수정/삭제 정책

- 반출 대상 후보에서 묶음 생성 시 만든다.
- 확정 전 취소 가능 후보로 둔다.
- `CONFIRMED` 이후 일반 수정은 금지한다.

### Codex 구현 시 주의사항

- 반출은 판정 변경이 아니다.
- 반출확정 전 전량 대조가 필요하다.
- 반출확정 후 재고 차감은 `inventory_events` 경로로 처리한다.

## 20. `return_external_outbound_items`

### 테이블 목적

반출 묶음에 포함된 반품 단위체 또는 상품 line이다.

### 사용 화면/업무

- 반품 반출
- 반품 통합추적
- 재고 이벤트 source line 후보

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 반출 item 식별자 |
| `outbound_batch_id` | 반출 batch |
| `client_id` | 고객사 식별자 |
| `return_unit_id` | 반품 단위체 후보 |
| `return_unit_no` | 반품관리번호 후보 |
| `product_id` | 상품 식별자 |
| `product_code` | 상품코드 |
| `judgement_code` | 판정 코드 |
| `expected_qty` | 대상 수량 |
| `scanned_qty` | 스캔 수량 |
| `item_status` | item 상태 |
| `inventory_event_id` | 재고 이벤트 연결 후보 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `outbound_batch_id`
- `client_id`
- `judgement_code`
- `expected_qty`
- `scanned_qty`
- `item_status`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `return_unit_id`
- `return_unit_no`
- `product_id`
- `product_code`
- `inventory_event_id`

### 상태값 후보

- `PENDING`
- `SCANNED`
- `MATCHED`
- `MISSING`
- `CONFIRMED`
- `CANCELLED`

### 제약/인덱스 후보

- `index(outbound_batch_id)`
- `index(return_unit_no)`
- `index(client_id, product_id)`
- `index(inventory_event_id)`

### scope 기준

- `client_id` scope를 가진다.

### import job 또는 inventory_events와의 관계

- import job과 직접 연결하지 않는다.
- 반출확정 후 `inventory_event_id`를 연결할 수 있다.

### 생성/수정/삭제 정책

- 반출 묶음 생성 시 대상 후보로 생성한다.
- 스캔에 따라 상태와 수량을 갱신한다.
- `CONFIRMED` 이후 일반 수정은 금지한다.

### Codex 구현 시 주의사항

- 반품관리번호 중복 포함을 막는다.
- `inventory_event_id`는 반출확정 후 연결 후보로 둔다.

## 21. `return_external_outbound_scan_logs`

### 테이블 목적

반품 반출 검수 중 스캔 로그를 저장한다.

### 사용 화면/업무

- 반품 반출
- 반품 통합추적

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 스캔 로그 식별자 |
| `outbound_batch_id` | 반출 batch |
| `outbound_item_id` | 반출 item 후보 |
| `client_id` | 고객사 식별자 |
| `scan_value` | 스캔값 |
| `result_code` | 결과 코드 |
| `sound_code` | 작업자 피드백 후보 |
| `message` | 표시 메시지 |
| `operator_id` | 작업자 |
| `created_at` | 생성 시각 |

### 필수 컬럼

- `id`
- `outbound_batch_id`
- `client_id`
- `scan_value`
- `result_code`
- `created_at`

### nullable 허용 후보

- `outbound_item_id`
- `sound_code`
- `message`
- `operator_id`

### 상태값 후보

`result_code` 후보는 다음과 같다.

- `OK`
- `DUPLICATE`
- `NOT_IN_BATCH`
- `ALREADY_OUTBOUND`
- `MISMATCH`
- `ERROR`

### 제약/인덱스 후보

- `index(outbound_batch_id)`
- `index(client_id, created_at)`
- `index(result_code, created_at)`

### scope 기준

- `client_id` scope를 가진다.

### import job 또는 inventory_events와의 관계

- `scan_events` 성격의 업무별 로그이며 재고 원장이 아니다.

### 생성/수정/삭제 정책

- 스캔마다 생성한다.
- 생성 후 수정하지 않는 것을 원칙으로 한다.

### Codex 구현 시 주의사항

- 중복 스캔과 대상 외 스캔은 반드시 결과 코드로 남긴다.

## 22. 반품 P1 핵심 관계 흐름

### import job → 반품예정 업무 테이블

```text
import_jobs
  → import_job_rows
  → return_expected_batches
  → return_expected_rows
```

### 업체 접수자료 → 매칭 후보

```text
vendor_return_sources
  → vendor_return_rows
  → return_match_records
```

### 예정/접수 자료 → 실제 반품처리 원장

```text
return_expected_rows ─┐
                      ├→ return_match_records
vendor_return_rows ───┘
  → return_receipts
```

### 실제 반품처리 → 반품 단위체

```text
return_receipts
  → return_receipt_items
  → return_units
  → return_unit_logs
```

### 실제 반품처리 → 재고 이벤트 후보

```text
return_receipts
  → return_receipt_items
  → inventory_events 후보
```

### 반품 단위체 → 마감

```text
return_units
  → return_closing_items
  → return_closing_sessions
```

### 반품 단위체 → 반출

```text
return_units
  → return_external_outbound_items
  → return_external_outbound_batches
  → inventory_events 후보
```

### 라벨 출력 이력

```text
return_receipt_items
  → return_units
  → return_label_print_logs
```

## 23. 반품 P1에서 아직 확정하지 않을 것

아래 항목은 후속 문서로 분리한다.

- 실제 API schema
- 실제 migration DDL
- 구글시트 push 구현
- 파일 업로드 저장소 상세
- 사진 저장소 상세
- ERP 전송 상세
- 정산 연결
- 고객사 포털 반품 조회 상세
- 고급 승인/결재 흐름

## 24. Codex 구현 전 체크

- 이 테이블은 반품자료 준비/반품처리/반품 마감/반품 반출/통합추적 중 어디에 쓰이는가?
- 업체 접수자료와 반품예정자료를 섞고 있지 않은가?
- 실제 반품처리 원장을 `return_receipts` / `return_receipt_items` 기준으로 보고 있는가?
- `batch_id`를 반품처리 중심키로 쓰고 있지 않은가?
- 상품/수량/판정 확정 위치가 `return_receipt_items`로 분리되어 있는가?
- 라벨 출력 실패가 판정 저장 실패가 되지 않도록 로그가 분리되어 있는가?
- `return_units`가 필요한 판정상태와 필요 없는 판정상태를 구분했는가?
- 마감과 반출이 반품처리 작업과 분리되어 있는가?
- 재고 수량 변경은 `inventory_events`와 연결되는가?
- `client_id` / `warehouse_id` scope가 명확한가?
