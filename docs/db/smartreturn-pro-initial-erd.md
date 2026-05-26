# SmartReturn Pro 초기 ERD 설계

이 문서는 실제 migration 파일이 아니라 SmartReturn Pro의 초기 ERD 설계 문서다. 테이블의 모든 세부 컬럼을 확정하기보다 DB 큰 구조, 도메인 경계, 원장 관계, 후속 설계 범위를 잡는 데 목적이 있다.

이 문서는 SmartReturn Pro 신규 제작 기준이며, 기존 SmartReturn 구현기록을 그대로 따르지 않는다.

## DB 설계 기본 원칙

- PostgreSQL 우선 설계로 작성한다.
- 특정 DB 기능에 과도하게 종속되지 않도록 DB 중립성을 고려한다.
- 모든 업무 테이블은 `client_id` scope를 고려한다.
- 창고 관련 업무는 `warehouse_id` scope를 고려한다.
- 기준정보와 업무 데이터는 삭제보다 `active_yn` 또는 `status`를 통한 사용중지를 우선한다.
- 주요 테이블은 `created_at`, `updated_at`을 기본으로 가진다.
- `raw_json`은 외부 원본 또는 부가 payload 보존용으로 사용한다.
- 운송장번호, 바코드, 상품코드는 비교용 정규화 기준을 사용한다.
- import job과 실제 업무 테이블을 분리한다.
- `scan_events`와 `inventory_events`를 분리한다.

## A. 권한/사용자

### 테이블 초안

| 테이블 | 역할 | 주요 관계/주의사항 |
| --- | --- | --- |
| `users` | 사용자 계정과 로그인 상태를 관리한다. | `client_id`, `must_change_password`, `status`를 고려한다. |
| `roles` | 표준 role을 관리한다. | `SUPER_ADMIN`, `INTERNAL_ADMIN`, `INTERNAL_WORKER`, `CLIENT_ADMIN`, `CLIENT_USER`, `READ_ONLY`를 기준으로 한다. |
| `user_roles` | 사용자와 role의 연결을 관리한다. | 한 사용자가 여러 role을 가질 수 있는지 후속 결정한다. |
| `permissions` | 세부 권한 단위를 관리한다. | 메뉴 접근, 조회, 생성, 수정, 확정, 삭제 권한을 분리한다. |
| `role_permissions` | role과 permission의 연결을 관리한다. | role 기준 권한 확장의 중심 테이블이다. |
| `auth_login_logs` | 로그인 성공/실패와 보안 이벤트를 기록한다. | 실패 사유, 접속 위치, user agent 등은 보안 기준에 맞춰 보존한다. |

### 핵심 정책

- 내부 운영자와 고객사 사용자는 `role` 기준으로 구분한다.
- `client_id` 유무로 사용자 성격을 판단하지 않는다.
- 첫 로그인 또는 초기화 후 `must_change_password`를 지원한다.
- 운영사 관리자는 비밀번호를 조회할 수 없고 초기화/재발급만 할 수 있다.
- 평문 비밀번호는 저장하거나 응답하지 않는다.

## B. 기준정보

### 테이블 초안

| 테이블 | 역할 | 주요 관계/주의사항 |
| --- | --- | --- |
| `clients` | 고객사/화주 기본 정보를 관리한다. | 모든 업무 scope의 기준이다. |
| `warehouses` | 창고 기본 정보를 관리한다. | 창고 업무와 재고 scope의 기준이다. |
| `client_warehouses` 또는 `client_warehouse_settings` | 고객사별 사용창고와 설정을 관리한다. | 고객사-창고 연결은 필수다. |
| `locations` | 창고 내 위치를 관리한다. | `warehouse_id` scope를 가진다. |
| `products` | 고객사별 상품 기준정보를 관리한다. | `client_id`, `product_code`, 대표 `barcode`를 가진다. |
| `product_barcodes` | 추가/박스/카톤/외부 바코드를 관리한다. | `unit_qty`는 필수 후보로 둔다. |
| `common_code_groups` | 공통코드 그룹을 관리한다. | 업무 상태, 사유, 택배사 등 그룹을 정의한다. |
| `common_codes` | 공통코드 값을 관리한다. | 화면 하드코딩을 막기 위한 기준이다. |

### 핵심 정책

- 고객사-창고 연결은 필수다.
- 창고 선택은 선택 고객사의 사용창고만 표시한다.
- 상품 바코드는 대표 바코드와 추가 바코드를 분리한다.
- `products.barcode`는 대표 낱개 바코드다.
- `product_barcodes.unit_qty`는 스캔 1회당 반영 수량으로 필수 후보다.
- 공통코드는 화면 하드코딩을 금지하기 위한 기준정보다.

## C. import job / 업로드

### 테이블 초안

| 테이블 | 역할 | 주요 관계/주의사항 |
| --- | --- | --- |
| `import_jobs` | 업로드 작업 단위를 관리한다. | source type, 사용자, 상태, `client_id`, `warehouse_id`를 고려한다. |
| `import_job_files` | 업로드 파일 메타데이터를 관리한다. | 파일명, 크기, 해시, 저장 위치 또는 외부 참조를 기록한다. |
| `import_job_rows` | 원본 row 단위 데이터를 보존한다. | `row_no`, `row_hash`, `source_row_key`, `raw_json`을 보존한다. |
| `import_validation_errors` | 검증 오류와 경고를 관리한다. | row 단위 오류와 job 단위 오류를 구분한다. |

### 핵심 정책

- preview, save, history, 업무반영을 분리한다.
- 원본 `row_no`, `row_hash`, `source_row_key`를 보존한다.
- `batch_id`는 원본 추적 보조키이며 업무 중심키가 아니다.
- 검증 실패 row는 업무 테이블에 반영하지 않는다.

## D. 반품

### 테이블 초안

| 테이블 | 역할 | 주요 관계/주의사항 |
| --- | --- | --- |
| `return_expected_batches` | 택배/CJ 반품예정 자료 묶음을 관리한다. | import job과 연결될 수 있으나 업무 중심키는 아니다. |
| `return_expected_rows` | 반품예정 row를 관리한다. | 운송장번호, 후보 상품, 후보 수량을 보존한다. |
| `vendor_return_sources` 또는 `return_vendor_sources` | 구글시트 등 업체 접수 source를 관리한다. | 명명은 후속 설계에서 하나로 확정한다. |
| `vendor_return_rows` 또는 `return_vendor_rows` | 업체 반품접수 row를 관리한다. | 구글시트 원본과 회신 상태를 보존한다. |
| `return_match_records` | 접수자료와 예정자료의 매칭 결과를 관리한다. | 매칭은 보조 기능이며 필수 관문이 아니다. |
| `return_receipts` | 실제 반품처리 작업 단위를 관리한다. | 스캔/판정 작업의 상위 원장 후보다. |
| `return_receipt_items` | 반품처리 상품/수량/판정 항목을 관리한다. | 실제 확정 상품과 수량을 기록한다. |
| `return_units` | 반품관리번호 단위 추적 대상을 관리한다. | 리퍼/제조사반품/샘플/보류 추적에 사용한다. |
| `return_label_print_logs` | 라벨 출력/재출력 이력을 관리한다. | 출력 실패는 판정 저장 실패가 아니다. |
| `return_closing_sessions` | 반품 마감 세션을 관리한다. | 기간, 고객사, 판정 상태 기준 대조를 관리한다. |
| `return_closing_items` | 마감 대상과 대조 결과를 관리한다. | 마감은 재고반영이 아니라 대조 흐름이다. |
| `return_external_outbound_batches` | 외부 반출 묶음을 관리한다. | 마감과 별도 흐름이다. |
| `return_external_outbound_items` | 반출 대상 반품 단위를 관리한다. | 반품관리번호 스캔과 반출 확정을 지원한다. |

### 핵심 정책

- 구글시트 접수자료와 택배 반품예정자료는 독립된 원본이다.
- 매칭은 필수 관문이 아니라 참고/정확도 보조 기능이다.
- 실제 처리 원장은 반품처리 작업 결과다.
- 리퍼, 제조사반품, 샘플, 보류는 반품관리번호 추적을 우선한다.

## E. 입고

### 테이블 초안

| 테이블 | 역할 | 주요 관계/주의사항 |
| --- | --- | --- |
| `inbound_expected_batches` | 예정입고 자료 묶음을 관리한다. | import job과 연결될 수 있다. |
| `inbound_expected_rows` | 예정입고 row를 관리한다. | 후보 상품/수량과 원본 정보를 보존한다. |
| `inbound_tasks` | 입고검수 작업 단위를 관리한다. | 예정입고와 무예정 입고를 모두 지원한다. |
| `inbound_task_items` | 검수 상품/수량 항목을 관리한다. | 확정 전 재고 반영 금지다. |
| `inbound_exception_items` | 미등록 상품, 수량 불일치 등 예외를 관리한다. | 미등록 상품은 재고반영 금지다. |

### 핵심 정책

- 예정입고와 무예정 입고를 모두 지원한다.
- 입고 confirm과 apply-inventory를 분리한다.
- 미등록 상품은 재고반영을 금지한다.
- 입고 확정 시 서버에서 재고 이벤트를 생성한다.

## F. 출고/OMS

### 테이블 초안

| 테이블 | 역할 | 주요 관계/주의사항 |
| --- | --- | --- |
| `order_import_jobs` 또는 `import_jobs` | 주문자료 업로드 단위를 관리한다. | 별도 테이블 여부는 후속 확정한다. |
| `orders` | 주문 헤더를 관리한다. | 고객사 주문번호, 수령자, 배송 상태를 고려한다. |
| `order_items` | 주문 상품 항목을 관리한다. | 상품, 수량, 출고대상 생성 기준이 된다. |
| `outbound_tasks` | 출고검수 작업 단위를 관리한다. | 주문/출고대상과 연결한다. |
| `outbound_task_items` | 출고검수 상품 항목을 관리한다. | 검수 결과와 확정 수량을 기록한다. |
| `outbound_scan_events` | 출고 업무 관점의 스캔 결과를 관리한다. | 공통 `scan_events`와의 통합 여부는 후속 확정한다. |

### 핵심 정책

- 출고 스캔 중 재고 차감을 금지한다.
- 출고 완료/확정 시 서버에서 재고 이벤트를 생성한다.
- 웹 출고검수와 로컬 스캔 클라이언트 역할을 분리한다.

## G. 재고

### 테이블 초안

| 테이블 | 역할 | 주요 관계/주의사항 |
| --- | --- | --- |
| `inventory_events` | 재고 이벤트 원장이다. | 모든 재고 증감, 보정, 취소를 이벤트로 기록한다. |
| `current_inventory` | 현재고 요약이다. | 원장 이벤트 결과로 갱신한다. |

### 핵심 정책

- `inventory_events`는 재고 원장이다.
- `current_inventory`는 현재고 요약이다.
- `idempotency_key`는 필수 후보로 둔다.
- 취소/정정은 `reverse_event_id`로 추적한다.
- 원장 이벤트 없이 현재고만 직접 수정하지 않는다.

## H. 스캔/Local Agent

### 테이블 초안

| 테이블 | 역할 | 주요 관계/주의사항 |
| --- | --- | --- |
| `scan_sessions` | 스캔 작업 세션을 관리한다. | 사용자, 업무 목적, 고객사, 창고, 시작/종료 상태를 기록한다. |
| `scan_events` | 스캔 이벤트 로그다. | 재고 원장이 아니다. |
| `local_agent_devices` | 연결 장치, 프린터, 사운드 상태를 관리한다. | 장치 제어 상태 표시의 기준이다. |
| `local_agent_setting_history` | Local Agent 설정 변경 이력을 관리한다. | 원격 강제 변경은 초기 제외 범위다. |

### 핵심 정책

- `scan_events`는 재고 원장이 아니다.
- 로컬 클라이언트는 재고를 직접 변경하지 않는다.
- Local Agent는 사운드, 라벨, 프린터, 장치 제어를 담당한다.
- Local Agent 실패가 업무 저장 실패가 되면 안 된다.

## I. 정산

### 테이블 초안

| 테이블 | 역할 | 주요 관계/주의사항 |
| --- | --- | --- |
| `billing_contracts` 또는 `billing_policies` | 고객사별 계약/단가 기준을 관리한다. | 상세 단가 정책은 후속 설계한다. |
| `settlement_headers` | 정산 생성 단위를 관리한다. | 기간, 고객사, 상태를 가진다. |
| `settlement_lines` | 정산 항목을 관리한다. | 운영 이벤트 기반 산출 결과를 보존한다. |
| `billing_logs` | 정산 생성/수정/마감 로그를 관리한다. | 감사 추적용이다. |

### 핵심 정책

- 초기에는 상세 구현을 제외한다.
- 운영 이벤트 기반 마감 스냅샷 구조로 확장한다.
- 정산 고도화는 초기 제외 범위다.

## 핵심 관계 흐름

### import job → 업무 테이블 반영

```text
원본 파일/외부 원본
  → import_jobs
  → import_job_files
  → import_job_rows
  → import_validation_errors
  → 검증 통과 row만 업무 테이블 후보로 반영
```

### 반품접수/반품예정 → 반품처리 → 재고 이벤트 → 마감 → 반출

```text
vendor_return_rows ─┐
                    ├→ return_match_records
return_expected_rows ┘
  → return_receipts
  → return_receipt_items / return_units
  → inventory_events
  → return_closing_sessions / return_closing_items
  → return_external_outbound_batches / return_external_outbound_items
```

### 입고예정/무예정 → 입고검수 → 확정 → 재고 이벤트

```text
inbound_expected_rows 또는 무예정 입력
  → inbound_tasks
  → inbound_task_items / inbound_exception_items
  → 입고 확정
  → inventory_events
  → current_inventory
```

### OMS/출고자료 → 출고검수 → 출고확정 → 재고 이벤트

```text
orders / order_items
  → outbound_tasks
  → outbound_task_items
  → 출고 확정
  → inventory_events
  → current_inventory
```

### scan_events → 업무 서비스 → inventory_events

```text
scan_sessions
  → scan_events
  → 업무 서비스 검증/확정
  → inventory_events
  → current_inventory
```

## 설계상 아직 확정하지 않을 것

- ERP 실제 API 전송 테이블 상세
- 고객사 포털 상세 테이블
- 정산 상세 단가 정책
- AI 도우미 로그 구조
- Local Agent 자동 업데이트 구조

## Codex 구현 전 체크

- 이 문서가 migration 파일이 아니라 ERD 설계 문서임을 유지했는가?
- 모든 업무 테이블에서 `client_id` scope를 고려했는가?
- 창고 업무에서 `warehouse_id` scope를 고려했는가?
- import job과 실제 업무 테이블을 분리했는가?
- `scan_events`와 `inventory_events`를 분리했는가?
- 반품 접수자료, 반품예정자료, 반품처리 원장의 책임을 분리했는가?
- 재고 변경이 서버 업무 확정 흐름에서만 발생하는가?
- 초기 제외 범위를 세부 테이블로 확정하지 않았는가?
