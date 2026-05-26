# SmartReturn Pro 반품 MVP API schema 초안

이 문서는 SmartReturn Pro 신규 제작 기준이며, 기존 SmartReturn 구현기록을 그대로 따르지 않는다.

이 문서는 실제 Pydantic 코드가 아니다. 실제 schema 구현 전 필드명, 책임, 상태값, 응답 구조를 고정하기 위한 기준 문서다.

## 1. 문서 목적

이 문서는 SmartReturn Pro 반품 MVP API의 request/response schema 초안을 정의한다. 반품예정, 업체접수 후보, 반품처리 작업, 반품 마감, 반품 반출, 반품 통합추적은 서로 다른 책임을 가지며 schema도 분리한다.

schema 설계는 다음 문서를 기준으로 한다.

- `docs/business/smartreturn-pro-return-api-policy.md`
- `docs/db/smartreturn-pro-return-p1-table-columns.md`
- `docs/business/smartreturn-pro-auth-client-scope-api-policy.md`
- `docs/business/smartreturn-pro-scan-local-agent-inventory-policy.md`

## 2. schema 설계 공통 원칙

- schema는 화면 책임과 API 책임을 따라 분리한다.
- 반품예정 schema와 반품처리 작업 schema를 섞지 않는다.
- 업체 반품접수 schema는 참고/회신 채널용이며, 실제 반품처리 원장이 아니다.
- 내부 개발용 필드와 운영자 표시 필드를 구분한다.
- `client_id`, `warehouse_id`, `raw_json`, `batch_id`, `import_job_id` 같은 내부값은 운영 기본 UI에 그대로 노출하지 않는다.
- API 내부에서는 필요한 식별자를 주고받되, 프론트 화면 표시용 DTO는 한글 표시명/요약값을 별도로 제공한다.
- 모든 업무 변경 schema는 `AuthContext` 기준 client/warehouse scope 검증을 전제로 한다.
- 재고 수량 변경은 schema에서 직접 `current_inventory` 수량을 받지 않는다.
- 재고 반영은 `inventory_events` 경로로 연결한다.
- `sound_code`는 작업자 피드백용이며 DB 저장 성공/실패와 혼동하지 않는다.
- 라벨 출력 실패는 판정 저장 실패와 분리해서 표현한다.

## 3. 공통 응답 schema 후보

### 3-1. `ApiResult`

| 필드 | 설명 |
| --- | --- |
| `success` | API 처리 성공 여부 |
| `result_code` | 프론트 분기와 테스트에 사용할 안정 코드 |
| `message` | 운영자가 이해할 수 있는 한글 문구 후보 |
| `data` | 실제 응답 데이터 |
| `warnings` | 경고 목록 |
| `errors` | 오류 목록 |
| `next_action` | 다음 처리 제안 |
| `request_id` | 요청 추적 ID 후보 |
| `sound_code` | 작업자 피드백 사운드 코드 후보 |

정책은 다음과 같다.

- `message`는 운영자가 이해할 수 있는 한글 문구 후보를 포함한다.
- `result_code`는 프론트 분기와 테스트에 사용 가능한 안정 코드다.
- `sound_code`는 작업자 피드백용이며, DB 저장 성공/실패와 혼동하지 않는다.
- 오류여도 가능하면 `next_action`을 제공한다.
- 내부 stack trace나 민감한 설정값은 `errors`에 그대로 넣지 않는다.

### 3-2. `PageResponse`

| 필드 | 설명 |
| --- | --- |
| `rows` | 현재 페이지 row 목록 |
| `total_count` | 전체 건수 |
| `page` | 현재 페이지 |
| `page_size` | 페이지 크기 |
| `has_next` | 다음 페이지 여부 |
| `has_prev` | 이전 페이지 여부 |

정책은 다음과 같다.

- 전체 건수는 `rows.length`가 아니라 서버 `total_count` 기준이다.
- `page_size` 변경 시 1페이지부터 조회하는 UI 정책을 고려한다.
- 필터 조건은 응답에 그대로 반복하지 않고 필요한 경우 별도 `summary` 후보로 둔다.

### 3-3. `LookupOption`

| 필드 | 설명 |
| --- | --- |
| `id` | 내부 식별자 |
| `code` | 저장 코드 |
| `name` | 표시명 |
| `status` | 사용 상태 후보 |
| `extra` | 추가 표시 정보 후보 |

정책은 다음과 같다.

- 고객사/상품/창고/공통코드 lookup은 공통 lookup schema를 재사용할 수 있게 둔다.
- `extra`는 기본 UI에 필요한 요약값만 담고, 원본 `raw_json`은 넣지 않는다.

## 4. 반품예정 import schema

대상 API는 다음과 같다.

- `POST /api/returns/expected/import/preview`
- `POST /api/returns/expected/import/save`
- `GET /api/returns/expected/import-jobs`
- `GET /api/returns/expected/rows`

### 4-1. `ReturnExpectedImportPreviewRequest`

| 필드 | 설명 |
| --- | --- |
| `client_id` | 내부 운영자의 고객사 선택 의도값 |
| `warehouse_id` | 창고 후보 |
| `source_type` | CJ/택배 등 source 유형 |
| `file` | 업로드 파일 후보 |
| `worksheet_name` | worksheet 이름 후보 |
| `header_row_index` | 헤더 row 번호 후보 |
| `mapping_options` | 컬럼 매핑 옵션 후보 |
| `memo` | 업로드 메모 |

정책은 다음과 같다.

- `client_id`는 내부 운영자 요청 의도값이며 서버에서 scope 검증한다.
- 고객사 사용자는 자기 `client_id`로 고정된다.
- preview 단계에서는 업무 테이블에 바로 반영하지 않는다.
- file schema는 실제 구현 시 multipart 또는 별도 업로드 방식으로 정한다.

### 4-2. `ReturnExpectedImportPreviewResponse`

| 필드 | 설명 |
| --- | --- |
| `import_job_id` | 생성된 import job 식별자 |
| `status` | import job 상태 |
| `total_rows` | 전체 row 수 |
| `valid_rows` | 정상 row 수 |
| `warning_rows` | 경고 row 수 |
| `invalid_rows` | 오류 row 수 |
| `preview_rows` | 미리보기 row 목록 |
| `validation_errors` | 검증 오류 목록 |
| `summary` | 운영자용 요약 |
| `next_action` | 다음 행동 후보 |

### 4-3. `ReturnExpectedPreviewRow`

| 필드 | 설명 |
| --- | --- |
| `row_no` | 원본 row 번호 |
| `row_status` | row 검증 상태 |
| `waybill_no` | 원본 운송장번호 |
| `waybill_no_display` | 화면 표시용 운송장번호 |
| `waybill_no_norm` | 비교용 정규화 운송장번호 |
| `shipper_customer_code` | 택배/화주 코드 후보 |
| `shipper_customer_name` | 택배/화주명 후보 |
| `mapped_client_id` | 매핑된 고객사 식별자 후보 |
| `mapped_client_name` | 매핑된 고객사명 |
| `receiver_name` | 수령자명 후보 |
| `item_name` | 원본 상품명 후보 |
| `qty` | 원본 수량 후보 |
| `warnings` | row 경고 목록 |
| `errors` | row 오류 목록 |

정책은 다음과 같다.

- 원본 row 순서를 유지한다.
- 운송장 비교는 norm 기준, 화면 표시는 display 기준이다.
- 상품명/수량은 후보값이며 최종 판정값이 아니다.

### 4-4. `ReturnExpectedImportSaveRequest`

| 필드 | 설명 |
| --- | --- |
| `import_job_id` | 저장할 import job |
| `confirm_save` | 저장 확정 여부 |
| `memo` | 저장 메모 |

정책은 다음과 같다.

- 저장 가능한 import job 상태는 `READY_TO_SAVE`만 허용한다.
- `INVALID` row는 업무 테이블에 반영하지 않는다.
- 저장 확정 후 `return_expected_rows`에 업무용 데이터로 반영한다.

### 4-5. `ReturnExpectedImportSaveResponse`

| 필드 | 설명 |
| --- | --- |
| `import_job_id` | import job 식별자 |
| `batch_id` | 반품예정 저장 묶음 식별자 후보 |
| `inserted_count` | 추가 건수 |
| `updated_count` | 수정 건수 |
| `skipped_count` | 제외 건수 |
| `error_count` | 오류 건수 |
| `saved_rows` | 저장된 row 요약 |
| `next_action` | 다음 행동 후보 |

정책은 다음과 같다.

- `batch_id`는 원본 추적/이력 보조키이며 반품처리 중심키가 아니다.
- 운영 기본 UI에서는 `batch_id`를 전면 노출하지 않는다.

## 5. 반품예정 저장자료 조회 schema

### 5-1. `ReturnExpectedRowQuery`

| 필드 | 설명 |
| --- | --- |
| `client_id` | 고객사 조회 조건 후보 |
| `warehouse_id` | 창고 조회 조건 후보 |
| `date_from` | 조회 시작일 |
| `date_to` | 조회 종료일 |
| `waybill_no` | 운송장번호 검색값 |
| `keyword` | 통합 검색어 |
| `expected_status` | 예정자료 상태 |
| `matched_status` | 매칭 상태 |
| `page` | 페이지 |
| `page_size` | 페이지 크기 |

### 5-2. `ReturnExpectedRowSummary`

| 필드 | 설명 |
| --- | --- |
| `expected_row_id` | 반품예정 row 식별자 |
| `client_id` | 고객사 식별자 |
| `client_name` | 고객사명 |
| `warehouse_id` | 창고 식별자 후보 |
| `warehouse_name` | 창고명 후보 |
| `row_no` | 원본 row 번호 |
| `waybill_no` | 원본 운송장번호 |
| `waybill_no_display` | 화면 표시용 운송장번호 |
| `order_no` | 주문번호 후보 |
| `receiver_name` | 수령자명 후보 |
| `item_name` | 원본 상품명 후보 |
| `qty` | 원본 수량 후보 |
| `expected_status` | 예정자료 상태 |
| `matched_status` | 매칭 상태 |
| `created_at` | 생성 시각 |

정책은 다음과 같다.

- 운영 기본 UI에서는 내부 `batch_id`, `raw_json`, `row_hash`를 기본 노출하지 않는다.
- 상세/고급 정보에서만 원본 row 정보를 확인할 수 있게 한다.
- `qty`는 예정자료 수량 후보이며 실제 판정 수량이 아니다.

## 6. 업체 반품접수 schema 후보

1차 MVP에서는 실구현 제외 후보로 둘 수 있으나 schema 후보는 문서화한다.

### 6-1. `VendorReturnSourceSummary`

| 필드 | 설명 |
| --- | --- |
| `source_id` | 업체 source 식별자 |
| `client_id` | 고객사 식별자 |
| `client_name` | 고객사명 |
| `source_type` | source 유형 |
| `source_name` | source 표시명 |
| `channel_type` | 채널 유형 |
| `active_yn` | 사용 여부 |
| `last_pull_at` | 마지막 수신 시각 |
| `last_push_at` | 마지막 회신 시각 |

### 6-2. `VendorReturnRowSummary`

| 필드 | 설명 |
| --- | --- |
| `vendor_row_id` | 업체 접수 row 식별자 |
| `client_id` | 고객사 식별자 |
| `client_name` | 고객사명 |
| `source_id` | 업체 source 식별자 |
| `source_name` | 업체 source 표시명 |
| `worksheet_name` | worksheet 이름 |
| `row_no` | row 번호 후보 |
| `customer_name` | 고객명 후보 |
| `order_no` | 주문번호 후보 |
| `waybill_no` | 운송장번호 원본 |
| `waybill_no_display` | 화면 표시용 운송장번호 |
| `product_name` | 업체 입력 상품명 후보 |
| `qty` | 업체 입력 수량 후보 |
| `return_reason` | 업체 입력 반품 사유 |
| `request_status` | 업체 요청 상태 |
| `processed_status` | 내부 처리/회신 상태 |
| `matched_status` | 매칭 상태 후보 |

정책은 다음과 같다.

- 업체 접수자료는 실제 도착 보장 자료가 아니다.
- 현장 스캔 중 Google Sheets API를 호출하지 않는다.
- 반품처리 작업에서는 DB에 저장된 참고정보만 표시한다.

### 6-3. `VendorReturnUpdateQueueSummary`

| 필드 | 설명 |
| --- | --- |
| `queue_id` | 회신 큐 식별자 |
| `vendor_row_id` | 업체 접수 row |
| `receipt_id` | 반품처리 헤더 후보 |
| `client_id` | 고객사 식별자 |
| `source_name` | source 표시명 |
| `worksheet_name` | worksheet 이름 |
| `row_no` | row 번호 후보 |
| `status` | 큐 상태 |
| `retry_count` | 재시도 횟수 |
| `error_message` | 오류 메시지 |
| `created_at` | 생성 시각 |
| `pushed_at` | push 완료 시각 |

정책은 다음과 같다.

- 판정 저장과 외부 push는 분리한다.
- push 실패가 판정 저장 실패가 되면 안 된다.

## 7. 반품처리 작업 lookup schema

대상 API는 다음과 같다.

- `POST /api/returns/work/lookup`

### 7-1. `ReturnWorkLookupRequest`

| 필드 | 설명 |
| --- | --- |
| `client_id` | 고객사 선택 의도값 |
| `warehouse_id` | 작업 창고 |
| `waybill_no` | 운송장번호 입력값 |
| `return_no` | 반품입고번호 후보 |
| `external_ref_no` | 외부 참조번호 후보 |
| `work_batch_id` | 내부 작업 묶음 후보 |

정책은 다음과 같다.

- 운송장번호는 입력값과 정규화값을 모두 관리한다.
- `client_id`/`warehouse_id`는 서버에서 scope 검증한다.
- Google Sheets API 직접 호출은 금지한다.

### 7-2. `ReturnWorkLookupResponse`

| 필드 | 설명 |
| --- | --- |
| `result_code` | 결과 코드 |
| `message` | 운영자용 한글 메시지 |
| `lookup_case` | lookup 케이스 |
| `candidates` | 후보 목록 |
| `expected_info` | 반품예정 참고정보 |
| `vendor_reception_info` | 업체 접수 참고정보 |
| `existing_receipt` | 기존 처리건 후보 |
| `next_action` | 다음 행동 후보 |
| `sound_code` | 작업자 피드백 사운드 |

`lookup_case` 후보는 다음과 같다.

- `EXPECTED_AND_RECEPTION_FOUND`
- `EXPECTED_ONLY`
- `RECEPTION_ONLY`
- `NOT_FOUND`
- `ALREADY_COMPLETED`
- `MULTIPLE_CANDIDATES`

### 7-3. `ReturnWorkCandidate`

| 필드 | 설명 |
| --- | --- |
| `candidate_id` | 후보 식별자 |
| `candidate_type` | 후보 유형 |
| `client_id` | 고객사 식별자 |
| `client_name` | 고객사명 |
| `warehouse_id` | 창고 식별자 후보 |
| `warehouse_name` | 창고명 후보 |
| `waybill_no` | 운송장번호 원본 |
| `waybill_no_display` | 화면 표시용 운송장번호 |
| `receiver_name` | 수령자명 후보 |
| `item_summary` | 상품/수량 요약 후보 |
| `match_status` | 매칭 상태 |
| `confidence_score` | 매칭 신뢰도 후보 |
| `warning_message` | 경고 메시지 |

`candidate_type` 후보는 다음과 같다.

- `EXPECTED_ROW`
- `VENDOR_ROW`
- `RECEIPT`
- `MANUAL`

정책은 다음과 같다.

- 복수 후보는 자동 확정하지 않는다.
- 작업자 선택 또는 관리자 확인을 요구한다.

## 8. 반품처리 작업 schema

대상 API는 다음과 같다.

- `POST /api/returns/work/manual-start`
- `POST /api/returns/work/{work_id}/scan-product`
- `POST /api/returns/work/{work_id}/judge`
- `POST /api/returns/work/{work_id}/complete`
- `GET /api/returns/work/{work_id}`

### 8-1. `ReturnWorkStartRequest`

| 필드 | 설명 |
| --- | --- |
| `client_id` | 고객사 선택 의도값 |
| `warehouse_id` | 작업 창고 |
| `waybill_no` | 운송장번호 후보 |
| `expected_row_id` | 반품예정 row 후보 |
| `vendor_row_id` | 업체 접수 row 후보 |
| `match_record_id` | 매칭 기록 후보 |
| `manual_reason_code` | 수동 시작 사유 코드 |
| `memo` | 메모 |

정책은 다음과 같다.

- `expected_row_id`, `vendor_row_id`, `match_record_id`는 nullable 가능하다.
- 고객사/상품이 확인되지 않은 정체불명 반품은 정상 등록하지 않는다.

### 8-2. `ReturnWorkDetailResponse`

| 필드 | 설명 |
| --- | --- |
| `work_id` | 작업 식별자 후보 |
| `receipt_id` | 반품처리 헤더 식별자 |
| `receipt_no` | 반품처리 번호 |
| `client_id` | 고객사 식별자 |
| `client_name` | 고객사명 |
| `warehouse_id` | 창고 식별자 |
| `warehouse_name` | 창고명 |
| `waybill_no` | 운송장번호 원본 |
| `waybill_no_display` | 화면 표시용 운송장번호 |
| `receipt_status` | 처리 상태 |
| `inventory_status` | 재고 이벤트 연결 상태 |
| `expected_info` | 반품예정 참고정보 |
| `vendor_reception_info` | 업체 접수 참고정보 |
| `items` | 처리 line 목록 |
| `photos` | 사진 목록 |
| `label_logs` | 라벨 로그 요약 |
| `work_logs` | 작업 로그 요약 |
| `available_actions` | 현재 가능한 액션 |

### 8-3. `ReturnWorkItemDto`

| 필드 | 설명 |
| --- | --- |
| `item_id` | 반품처리 line 식별자 |
| `product_id` | 상품 식별자 |
| `product_code` | 상품코드 |
| `product_name` | 상품명 |
| `barcode` | 스캔/확정 바코드 |
| `expected_qty` | 예정 수량 후보 |
| `scanned_qty` | 스캔 수량 |
| `judged_qty` | 판정 수량 |
| `judgement_code` | 판정 코드 |
| `judgement_name` | 판정 표시명 |
| `judgement_reason_code` | 판정 사유 코드 |
| `destination_warehouse_id` | 목적 창고 |
| `destination_warehouse_name` | 목적 창고명 |
| `destination_location_id` | 목적 위치 |
| `destination_location_name` | 목적 위치명 |
| `item_status` | line 상태 |
| `label_required_yn` | 라벨 필요 여부 |
| `return_unit_required_yn` | 반품관리번호 필요 여부 |
| `return_unit_no` | 반품관리번호 후보 |
| `memo` | 메모 |

정책은 다음과 같다.

- `expected_qty`는 후보값일 수 있다.
- 실제 판정 수량은 `judged_qty` 기준이다.
- 미등록 상품은 재고반영 대상이 아니다.

### 8-4. `ReturnProductScanRequest`

| 필드 | 설명 |
| --- | --- |
| `scan_value` | 스캔 입력값 |
| `quantity` | 수량 후보 |
| `operator_id` | 작업자 후보 |
| `local_event_id` | 로컬 이벤트 멱등성 후보 |
| `scan_source` | 스캔 source |

`scan_source` 후보는 다음과 같다.

- `WEB`
- `LOCAL_CLIENT`
- `LOCAL_AGENT`

### 8-5. `ReturnProductScanResponse`

| 필드 | 설명 |
| --- | --- |
| `result_code` | 스캔 결과 코드 |
| `message` | 운영자용 한글 메시지 |
| `matched_product` | 매칭 상품 |
| `applied_qty` | 적용 수량 후보 |
| `item` | 갱신된 line 후보 |
| `work_summary` | 작업 요약 |
| `sound_code` | 작업자 피드백 사운드 |
| `next_action` | 다음 행동 후보 |

`result_code` 후보는 다음과 같다.

- `OK`
- `NOT_FOUND`
- `NOT_IN_EXPECTED`
- `OVER_QTY`
- `DUPLICATE`
- `UNREGISTERED_PRODUCT`
- `INVALID_STATUS`
- `ERROR`

### 8-6. `ReturnJudgeRequest`

| 필드 | 설명 |
| --- | --- |
| `item_id` | 판정 대상 line |
| `product_id` | 확정 상품 |
| `judged_qty` | 판정 수량 |
| `judgement_code` | 판정 코드 |
| `judgement_reason_code` | 판정 사유 코드 |
| `destination_warehouse_id` | 목적 창고 |
| `destination_location_id` | 목적 위치 후보 |
| `memo` | 판정 메모 |
| `label_print_requested` | 라벨 출력 요청 여부 |
| `photo_required_ack` | 사진 필요 안내 확인 여부 후보 |

정책은 다음과 같다.

- `judgement_code`는 공통코드 또는 시스템 판정 코드 기준이다.
- 목적 창고는 추천값이 있어도 서버에서 고객사-창고 scope를 검증한다.
- `label_print_requested` 실패가 판정 저장 실패가 되면 안 된다.

### 8-7. `ReturnJudgeResponse`

| 필드 | 설명 |
| --- | --- |
| `success` | 판정 저장 성공 여부 |
| `result_code` | 결과 코드 |
| `message` | 운영자용 한글 메시지 |
| `item` | 저장된 line |
| `return_unit` | 생성/연결된 반품 단위체 후보 |
| `label_request` | 라벨 출력 요청 결과 |
| `inventory_event_candidate` | 재고 이벤트 후보 상태 |
| `sound_code` | 작업자 피드백 사운드 |
| `next_action` | 다음 행동 후보 |

### 8-8. `ReturnCompleteRequest`

| 필드 | 설명 |
| --- | --- |
| `work_id` | 작업 식별자 |
| `complete_memo` | 완료 메모 |
| `operator_id` | 작업자 후보 |
| `confirm_unprinted_labels` | 미출력 라벨 확인 여부 |

정책은 다음과 같다.

- 완료 전 필수 판정 누락 여부를 검증한다.
- 라벨 미출력/출력실패가 있어도 정책에 따라 완료 가능 여부를 판단한다.
- 재고 이벤트는 별도 서버 업무 흐름에서 생성 후보 또는 `READY` 상태로 연결한다.

## 9. 사진/파일 schema 후보

대상 API는 다음과 같다.

- `POST /api/returns/work/{work_id}/photo`

### 9-1. `ReturnPhotoUploadRequest`

| 필드 | 설명 |
| --- | --- |
| `receipt_id` | 반품처리 헤더 |
| `item_id` | 반품처리 line 후보 |
| `photo_type` | 사진 유형 |
| `file` | 업로드 파일 |
| `memo` | 메모 |

### 9-2. `ReturnPhotoDto`

| 필드 | 설명 |
| --- | --- |
| `photo_id` | 사진 식별자 |
| `receipt_id` | 반품처리 헤더 |
| `item_id` | 반품처리 line 후보 |
| `file_name` | 원본 파일명 |
| `relative_path` | 상대 경로 후보 |
| `mime_type` | MIME type |
| `size_bytes` | 파일 크기 |
| `photo_type` | 사진 유형 |
| `memo` | 메모 |
| `uploaded_by` | 업로드 사용자 |
| `created_at` | 생성 시각 |

정책은 다음과 같다.

- 실제 파일 저장소와 접근권한은 후속 파일 정책에서 확정한다.
- 사진 실패가 판정 저장 실패가 될지 여부는 업무 단계별로 별도 결정한다.

## 10. 반품 마감 schema

대상 API는 다음과 같다.

- `GET /api/returns/closing/sessions`
- `POST /api/returns/closing/sessions`
- `GET /api/returns/closing/sessions/{closing_id}`
- `POST /api/returns/closing/sessions/{closing_id}/scan`
- `POST /api/returns/closing/sessions/{closing_id}/confirm`

### 10-1. `ReturnClosingCreateRequest`

| 필드 | 설명 |
| --- | --- |
| `client_id` | 고객사 선택 의도값 |
| `warehouse_id` | 창고 후보 |
| `date_from` | 대상 시작일 |
| `date_to` | 대상 종료일 |
| `target_judgement_codes` | 대상 판정 코드 목록 |
| `memo` | 메모 |

### 10-2. `ReturnClosingSessionDto`

| 필드 | 설명 |
| --- | --- |
| `closing_id` | 마감 세션 식별자 |
| `closing_no` | 마감 번호 |
| `client_id` | 고객사 식별자 |
| `client_name` | 고객사명 |
| `warehouse_id` | 창고 식별자 |
| `warehouse_name` | 창고명 |
| `date_from` | 대상 시작일 |
| `date_to` | 대상 종료일 |
| `closing_status` | 마감 상태 |
| `expected_total_qty` | 대상 수량 |
| `scanned_total_qty` | 스캔 수량 |
| `mismatch_count` | 차이 건수 |
| `target_judgement_codes` | 대상 판정 코드 목록 |
| `items` | 마감 item 목록 |
| `available_actions` | 현재 가능한 액션 |

### 10-3. `ReturnClosingItemDto`

| 필드 | 설명 |
| --- | --- |
| `closing_item_id` | 마감 item 식별자 |
| `product_id` | 상품 식별자 후보 |
| `product_code` | 상품코드 후보 |
| `product_name` | 상품명 후보 |
| `judgement_code` | 판정 코드 |
| `return_unit_no` | 반품관리번호 후보 |
| `expected_qty` | 기대 수량 |
| `scanned_qty` | 스캔 수량 |
| `item_status` | 대조 상태 |
| `mismatch_reason` | 차이 사유 |

### 10-4. `ReturnClosingScanRequest`

| 필드 | 설명 |
| --- | --- |
| `scan_value` | 스캔값 |
| `scan_type` | 스캔 유형 |
| `operator_id` | 작업자 후보 |
| `local_event_id` | 로컬 이벤트 멱등성 후보 |

`scan_type` 후보는 다음과 같다.

- `PRODUCT_BARCODE`
- `RETURN_UNIT_NO`

### 10-5. `ReturnClosingScanResponse`

| 필드 | 설명 |
| --- | --- |
| `result_code` | 스캔 결과 코드 |
| `message` | 운영자용 한글 메시지 |
| `matched_item` | 매칭된 마감 item |
| `closing_summary` | 마감 요약 |
| `sound_code` | 작업자 피드백 사운드 |
| `next_action` | 다음 행동 후보 |

정책은 다음과 같다.

- 마감은 새로운 판정을 하지 않는다.
- 차이가 있으면 confirm 불가다.
- `GOOD`/`DISPOSAL`은 상품바코드 수량 대조 중심이다.
- `REFURB_A`, `REFURB_B`, `REFURB_C`, `MANUFACTURER_RETURN`, `SAMPLE`, `HOLD`는 반품관리번호 1:1 대조 중심이다.

## 11. 반품 반출 schema

대상 API는 다음과 같다.

- `GET /api/returns/external-outbound/candidates`
- `POST /api/returns/external-outbound/batches`
- `GET /api/returns/external-outbound/batches/{batch_id}`
- `POST /api/returns/external-outbound/batches/{batch_id}/scan`
- `POST /api/returns/external-outbound/batches/{batch_id}/confirm`

### 11-1. `ReturnExternalOutboundCandidateQuery`

| 필드 | 설명 |
| --- | --- |
| `client_id` | 고객사 조회 조건 후보 |
| `warehouse_id` | 창고 조회 조건 후보 |
| `judgement_codes` | 판정 코드 목록 |
| `destination_type` | 반출처 유형 |
| `date_from` | 조회 시작일 |
| `date_to` | 조회 종료일 |
| `page` | 페이지 |
| `page_size` | 페이지 크기 |

### 11-2. `ReturnExternalOutboundBatchCreateRequest`

| 필드 | 설명 |
| --- | --- |
| `client_id` | 고객사 선택 의도값 |
| `warehouse_id` | 반출 창고 |
| `destination_type` | 반출처 유형 |
| `destination_name` | 반출처명 |
| `target_judgement_codes` | 대상 판정 코드 목록 |
| `selected_return_unit_ids` | 선택한 반품 단위체 목록 |
| `memo` | 메모 |

### 11-3. `ReturnExternalOutboundBatchDto`

| 필드 | 설명 |
| --- | --- |
| `outbound_batch_id` | 반출 batch 식별자 |
| `outbound_no` | 반출 번호 |
| `client_id` | 고객사 식별자 |
| `client_name` | 고객사명 |
| `warehouse_id` | 창고 식별자 |
| `warehouse_name` | 창고명 |
| `destination_type` | 반출처 유형 |
| `destination_name` | 반출처명 |
| `outbound_status` | 반출 상태 |
| `expected_total_qty` | 대상 수량 |
| `scanned_total_qty` | 스캔 수량 |
| `items` | 반출 item 목록 |
| `available_actions` | 현재 가능한 액션 |

### 11-4. `ReturnExternalOutboundItemDto`

| 필드 | 설명 |
| --- | --- |
| `outbound_item_id` | 반출 item 식별자 |
| `return_unit_id` | 반품 단위체 식별자 |
| `return_unit_no` | 반품관리번호 |
| `product_id` | 상품 식별자 |
| `product_code` | 상품코드 |
| `product_name` | 상품명 |
| `judgement_code` | 판정 코드 |
| `expected_qty` | 대상 수량 |
| `scanned_qty` | 스캔 수량 |
| `item_status` | item 상태 |

### 11-5. `ReturnExternalOutboundScanRequest`

| 필드 | 설명 |
| --- | --- |
| `scan_value` | 반품관리번호 등 스캔값 |
| `operator_id` | 작업자 후보 |
| `local_event_id` | 로컬 이벤트 멱등성 후보 |

### 11-6. `ReturnExternalOutboundScanResponse`

| 필드 | 설명 |
| --- | --- |
| `result_code` | 스캔 결과 코드 |
| `message` | 운영자용 한글 메시지 |
| `matched_item` | 매칭된 반출 item |
| `batch_summary` | 반출 묶음 요약 |
| `sound_code` | 작업자 피드백 사운드 |
| `next_action` | 다음 행동 후보 |

정책은 다음과 같다.

- 반출확정은 판정 변경이 아니다.
- 반출확정 후 재고 차감은 `inventory_events` 후보로 연결한다.
- 반품관리번호 중복 스캔을 차단한다.

## 12. 반품 통합추적 schema

대상 API는 다음과 같다.

- `GET /api/returns/trace`
- `GET /api/returns/trace/{trace_id}`

### 12-1. `ReturnTraceQuery`

| 필드 | 설명 |
| --- | --- |
| `client_id` | 고객사 조회 조건 후보 |
| `waybill_no` | 반품 운송장번호 |
| `original_waybill_no` | 원송장번호 |
| `return_unit_no` | 반품관리번호 |
| `product_code` | 상품코드 |
| `barcode` | 바코드 |
| `external_ref_no` | 외부 참조번호 |
| `work_batch_id` | 작업 묶음 후보 |
| `date_from` | 조회 시작일 |
| `date_to` | 조회 종료일 |
| `page` | 페이지 |
| `page_size` | 페이지 크기 |

### 12-2. `ReturnTraceSummaryDto`

| 필드 | 설명 |
| --- | --- |
| `trace_id` | 통합추적 식별자 후보 |
| `client_id` | 고객사 식별자 |
| `client_name` | 고객사명 |
| `waybill_no` | 운송장번호 원본 |
| `waybill_no_display` | 화면 표시용 운송장번호 |
| `return_unit_no` | 반품관리번호 후보 |
| `product_code` | 상품코드 후보 |
| `product_name` | 상품명 후보 |
| `current_stage` | 현재 단계 |
| `current_status` | 현재 상태 |
| `last_event_at` | 마지막 이벤트 시각 |

### 12-3. `ReturnTraceDetailDto`

| 필드 | 설명 |
| --- | --- |
| `trace_id` | 통합추적 식별자 후보 |
| `expected_info` | 반품예정 정보 |
| `vendor_reception_info` | 업체 접수 정보 |
| `receipt_info` | 실제 반품처리 정보 |
| `judgement_info` | 판정 정보 |
| `label_info` | 라벨 정보 |
| `closing_info` | 마감 정보 |
| `external_outbound_info` | 반출 정보 |
| `inventory_events` | 재고 이벤트 요약 |
| `timeline` | 단계별 이력 |

정책은 다음과 같다.

- 통합추적은 읽기 전용이다.
- 판정 변경, 마감확정, 반출확정, 구글시트 push, 재고 재처리를 제공하지 않는다.
- 여러 원장 정보를 보여주더라도 조작 책임은 각 업무 API로 분리한다.

## 13. 공통 오류/결과 코드

공통 `result_code` 후보는 다음과 같다.

- `OK`
- `CREATED`
- `UPDATED`
- `COMPLETED`
- `NOT_FOUND`
- `MULTIPLE_CANDIDATES`
- `ALREADY_COMPLETED`
- `INVALID_STATUS`
- `CLIENT_SCOPE_DENIED`
- `WAREHOUSE_SCOPE_DENIED`
- `PASSWORD_CHANGE_REQUIRED`
- `UNREGISTERED_PRODUCT`
- `OVER_QTY`
- `DUPLICATE`
- `LABEL_PRINT_FAILED`
- `INVENTORY_EVENT_PENDING`
- `INVENTORY_EVENT_FAILED`
- `ERROR`

`sound_code` 후보는 다음과 같다.

- `OK`
- `ERROR`
- `OVER`
- `COMPLETE`
- `UNKNOWN`
- `DUPLICATE`
- `READY`
- `HOLD`
- `CANCEL`
- `SYNC_ERROR`
- `LABEL_PRINT`
- `REPRINT`
- `LOCKED`

정책은 다음과 같다.

- `result_code`는 업무 판단용이다.
- `sound_code`는 작업자 피드백용이다.
- 둘을 혼동하지 않는다.
- `LABEL_PRINT_FAILED`는 판정 저장 실패가 아니라 라벨 출력 계열 실패로 분리한다.

## 14. 운영 UI 노출 주의

운영 기본 UI에 직접 노출하지 않을 값은 다음과 같다.

- `raw_json`
- `metadata_json`
- `batch_id`
- `import_job_id`
- `row_hash`
- `source_row_key`
- `idempotency_key`
- `reverse_event_id`

정책은 다음과 같다.

- 필요한 경우 고급 상세/개발자 모드/관리자 상세에서만 표시한다.
- 작업자 화면에는 한글 상태명, 다음 행동, 경고 메시지를 우선 표시한다.
- 내부 식별자는 API 내부 추적과 권한 검증에 사용하되, 작업자가 이해해야 하는 업무명과 분리한다.

## 15. Codex 구현 전 체크

- 이 schema가 어느 API 책임에 속하는가?
- 반품예정/업체접수/실제처리 원장을 섞고 있지 않은가?
- `client_id`/`warehouse_id` scope 검증에 필요한 필드가 있는가?
- 작업자 화면용 DTO와 내부 개발용 필드가 구분되어 있는가?
- `batch_id`/`import_job_id`/`raw_json`을 운영 기본 UI에 노출하지 않도록 했는가?
- 재고 수량 직접 변경 필드를 받지 않는가?
- `scan_events`와 `inventory_events`가 분리되어 있는가?
- 라벨 출력 실패를 판정 저장 실패로 처리하지 않도록 응답 구조가 분리되어 있는가?
