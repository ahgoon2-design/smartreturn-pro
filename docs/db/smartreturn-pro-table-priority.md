# SmartReturn Pro 테이블 우선순위

이 문서는 초기 ERD 문서의 테이블 후보를 개발 우선순위로 재정리하는 문서다. 실제 migration이 아니라 어떤 테이블을 먼저 설계하고 검증할지 정하는 기준 문서다.

## 테이블 우선순위 등급

- P0: 프로젝트 시작 직후 필요한 기반 테이블
- P1: 반품 MVP에 필요한 테이블
- P2: 입고/출고 MVP에 필요한 테이블
- P3: 정산/포털/고도화에 필요한 테이블
- HOLD: 설계 후보지만 당장 만들지 않는 테이블

## P0 테이블 후보

| 테이블 | 목적 | 왜 P0인지 | 주요 scope | 핵심 제약/인덱스 후보 |
| --- | --- | --- | --- | --- |
| `users` | 사용자 계정과 로그인 상태 관리 | 모든 업무 접근의 출발점 | `client_id` 후보, `role`은 연결 테이블 기준 | `login_id` unique, `status`, `must_change_password` |
| `roles` | 표준 role 관리 | 내부/고객사 사용자 구분의 기준 | 전역 | `role_code` unique |
| `user_roles` | 사용자-role 연결 | 권한 판단의 기본 연결 | 사용자 기준 | `(user_id, role_id)` unique |
| `permissions` | 세부 권한 단위 관리 | 메뉴/업무 권한 확장에 필요 | 전역 | `permission_code` unique |
| `role_permissions` | role-permission 연결 | role 기반 권한 부여에 필요 | 전역 | `(role_id, permission_id)` unique |
| `auth_login_logs` | 로그인/보안 이벤트 기록 | 보안 추적과 운영 감사에 필요 | 사용자 기준 | `user_id`, `created_at`, 결과 상태 인덱스 |
| `clients` | 고객사 기준정보 | 모든 업무의 `client_id` scope 기준 | `client_id` 자체 | `client_code` unique, `status` |
| `warehouses` | 창고 기준정보 | 재고와 창고 업무의 기준 | `warehouse_id` 자체 | `warehouse_code` unique, `status` |
| `client_warehouse_settings` | 고객사-창고 연결 | 고객사별 사용창고 제한에 필요 | `client_id`, `warehouse_id` | `(client_id, warehouse_id)` unique, `active_yn` |
| `products` | 고객사별 상품 기준정보 | 스캔, import, 재고, 반품의 공통 기준 | `client_id` | `(client_id, product_code)` unique, `(client_id, barcode)` 후보 |
| `product_barcodes` | 추가/박스/카톤/외부 바코드 관리 | `unit_qty`와 스캔 매칭에 필요 | `client_id`, 상품 기준 | `(client_id, barcode)`, `product_id`, `unit_qty` |
| `common_code_groups` | 공통코드 그룹 관리 | 화면 하드코딩 방지에 필요 | 전역 또는 `client_id` 후보 | `group_code` unique |
| `common_codes` | 공통코드 값 관리 | 상태/사유/택배사/소스 기준에 필요 | 그룹 기준, 필요 시 `client_id` | `(group_id, code)` unique, `sort_order`, `active_yn` |
| `import_jobs` | 업로드 작업 단위 관리 | 모든 자료 준비 흐름의 기반 | `client_id`, `warehouse_id` 후보 | `source_type`, `status`, `created_at` |
| `import_job_rows` | 원본 row 보존 | 검증/이력/업무반영 분리에 필요 | `import_job_id` | `(import_job_id, row_no)`, `row_hash`, `source_row_key` |
| `import_validation_errors` | row별 검증 오류 관리 | preview/save 전 검증에 필요 | `import_job_id`, row 기준 | `import_job_id`, `row_no`, 오류 등급 |
| `inventory_events` | 재고 이벤트 원장 | 재고 변경의 유일한 원장 | `client_id`, `warehouse_id`, 상품 기준 | `idempotency_key` unique 후보, `reverse_event_id`, `created_at` |
| `current_inventory` | 현재고 요약 | 현황 조회 성능과 운영 화면에 필요 | `client_id`, `warehouse_id`, 상품 기준 | `(client_id, warehouse_id, product_id, location_id)` unique 후보 |

## P1 반품 MVP 테이블 후보

| 테이블 | 목적 | 반품 MVP에서 쓰는 위치 | import job 또는 inventory_events와의 관계 |
| --- | --- | --- | --- |
| `return_expected_batches` | CJ/택배 반품예정 묶음 관리 | 반품자료 준비 | `import_jobs`와 연결 가능하나 업무 중심키는 아님 |
| `return_expected_rows` | 반품예정 row 관리 | 반품자료 준비, 반품처리 후보 정보 | `import_job_rows`에서 검증 통과 후 반영 |
| `return_match_records` | 접수자료/예정자료 매칭 결과 관리 | 반품자료 준비 또는 후속 매칭 조회 | 매칭은 보조 기능이며 재고 이벤트와 직접 연결하지 않음 |
| `return_receipts` | 실제 반품처리 작업 헤더 | 반품처리 작업 | 처리완료 후 재고 이벤트 생성 후보와 연결 |
| `return_receipt_items` | 반품처리 상품/수량/판정 항목 | 반품처리 작업 | 확정 상품/수량이 `inventory_events` 후보가 됨 |
| `return_units` | 반품관리번호 단위 추적 | 반품처리, 마감, 반출 | 리퍼/제조사반품/샘플/보류 1:1 대조 기준 |
| `return_label_print_logs` | 라벨 출력/재출력 이력 | 반품처리 작업 | 출력 실패는 업무 저장 실패나 재고 이벤트 실패가 아님 |
| `return_closing_sessions` | 반품 마감 세션 | 반품 마감 | 재고반영과 분리된 대조/확정 단위 |
| `return_closing_items` | 마감 대상과 대조 결과 | 반품 마감 | 마감 결과가 후속 재고 이벤트 또는 반출 후보와 연결될 수 있음 |
| `return_external_outbound_batches` | 외부반출 묶음 | 반품 반출 | 반출확정 시 서버 경로에서 재고 이벤트 후보 생성 |
| `return_external_outbound_items` | 반출 대상 반품 단위 | 반품 반출 | `return_units`와 연결하고 반출 이벤트 후보가 됨 |
| `scan_sessions` | 스캔 작업 세션 | 반품처리 작업, 반품 반출 | 업무별 스캔 묶음이며 재고 원장이 아님 |
| `scan_events` | 스캔 이벤트 로그 | 반품처리 작업, 반품 반출 | 업무 서비스 검증 후 `inventory_events`로 이어질 수 있으나 직접 원장 아님 |

## P2 입고/출고 MVP 테이블 후보

| 테이블 | 목적 | 적용 위치 | 주요 주의사항 |
| --- | --- | --- | --- |
| `inbound_expected_batches` | 예정입고 자료 묶음 | 입고자료 준비 | import job과 연결 가능 |
| `inbound_expected_rows` | 예정입고 row | 입고자료 준비, 입고검수 후보 | 원본 row와 업무 row를 분리 |
| `inbound_tasks` | 입고검수 작업 헤더 | 입고검수 작업 | 예정/무예정 모두 지원 |
| `inbound_task_items` | 입고검수 상품/수량 항목 | 입고검수 작업, 입고확정 | 확정 전 재고 반영 금지 |
| `inbound_exception_items` | 입고 예외 항목 | 입고검수/확정 | 미등록 상품은 재고반영 금지 |
| `orders` | 주문 헤더 | OMS, 출고자료 준비 | 출고검수와 분리 |
| `order_items` | 주문 상품 항목 | OMS, 출고대상 생성 | 상품/수량 기준 |
| `outbound_tasks` | 출고검수 작업 헤더 | 출고검수 작업 | 확정 시 서버 재고 이벤트 후보 |
| `outbound_task_items` | 출고검수 상품 항목 | 출고검수 작업, 출고확정 | 스캔 중 재고 차감 금지 |
| `outbound_scan_events` | 출고 업무 관점 스캔 결과 | 출고검수 작업 | 공통 `scan_events` 통합 여부 후속 결정 |

## P3 / HOLD 후보

| 항목 | 등급 | 이유 |
| --- | --- | --- |
| `settlement_headers` | P3 | 정산 생성/마감은 1차 MVP 제외이며 운영 이벤트 기반으로 후속 확장한다. |
| `settlement_lines` | P3 | 정산 상세 라인은 정산 정책 확정 후 설계한다. |
| `billing_policies` | P3 | 상세 단가 정책은 후속 고도화 범위다. |
| `billing_logs` | P3 | 정산 기능이 구체화된 뒤 감사 로그와 함께 설계한다. |
| 고객사 포털 관련 테이블 | P3 | 고객사 포털 전체 구현은 1차 MVP 제외다. |
| ERP 전송 상세 테이블 | HOLD | ERP 실제 API 전송은 초기 제외 범위다. |
| AI 로그 테이블 | HOLD | AI 도우미는 초기 제외 범위다. |
| Local Agent 자동 업데이트 관련 테이블 | HOLD | 자동 업데이트와 원격 설정 강제 변경은 초기 제외 범위다. |
| 고급 작업자 통계 테이블 | HOLD | 고급 통계/작업자 성과 분석은 1차 MVP 제외다. |

## 중복/주의 테이블

- `code_masters`와 `common_codes` 같은 중복 공통코드 구조를 만들지 않는다.
- legacy inventory와 `current_inventory`를 동시에 원장처럼 쓰지 않는다.
- `return_expected_rows`가 import row와 업무 row를 동시에 맡지 않게 한다.
- `scan_events`와 `inventory_events`를 섞지 않는다.
- `batch_id`를 업무 중심키로 쓰지 않는다.
- 구글시트 접수자료와 CJ/택배 반품예정자료를 하나의 원장으로 합치지 않는다.
- 반품처리 결과와 반품 마감/반출 결과를 한 테이블에 몰아넣지 않는다.

## Codex 구현 전 체크

- 지금 설계하려는 테이블의 우선순위 등급을 확인했는가?
- P0 기반 없이 P1 반품 테이블부터 만들고 있지 않은가?
- 공통코드 구조를 중복으로 만들고 있지 않은가?
- `scan_events`와 `inventory_events`가 분리되어 있는가?
- `batch_id`를 업무 중심키로 사용하지 않았는가?
- import row와 업무 row의 책임이 분리되어 있는가?
- 1차 MVP 제외 범위의 테이블을 확정 구현처럼 만들고 있지 않은가?
