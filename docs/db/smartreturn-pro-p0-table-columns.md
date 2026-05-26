# SmartReturn Pro P0 테이블 핵심 컬럼 초안

이 문서는 SmartReturn Pro 신규 제작 기준이며, 기존 SmartReturn 구현기록을 그대로 따르지 않는다.

이 문서는 실제 migration 파일이 아니라 P0 테이블별 핵심 컬럼 초안 문서다. 이 문서에서는 SQL DDL을 작성하지 않고, 백엔드 모델과 migration 작성 전에 테이블 목적, 주요 컬럼, 제약조건, 인덱스 후보, scope 기준을 고정한다.

## 공통 DB 컬럼 원칙

- 대부분의 업무 테이블은 `id`, `created_at`, `updated_at`를 가진다.
- 삭제보다 `active_yn=false` 또는 `status` 변경을 우선한다.
- 외부 원본이나 부가 payload는 `raw_json` 또는 `metadata_json` 성격의 컬럼으로 보존한다.
- 운영자/작업자 추적이 필요한 테이블은 `created_by`, `updated_by` 후보를 둔다.
- 모든 고객사 업무 데이터는 `client_id` scope를 명확히 둔다.
- 창고 업무 데이터는 `warehouse_id` scope를 명확히 둔다.
- 운송장번호, 바코드, 상품코드는 비교용 정규화 컬럼 또는 정규화 함수 기준을 둔다.
- `batch_id`는 업무 중심키가 아니라 import job 또는 원본 추적 보조키다.
- PostgreSQL 우선 설계로 작성하되, DB 중립성을 해치지 않는 범위로 작성한다.

## A. 권한/사용자

## `users`

### 테이블 목적

사용자 계정, 로그인 식별자, 고객사 scope 후보, 기본 창고, 비밀번호 변경 상태를 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 사용자 식별자 |
| `login_id` | 로그인 ID |
| `user_name` | 사용자 표시명 |
| `email` | 이메일 |
| `password_hash` | 해시된 비밀번호 |
| `client_id` | 고객사 사용자일 때 연결되는 고객사 |
| `default_warehouse_id` | 기본 창고 후보 |
| `must_change_password` | 첫 로그인 또는 초기화 후 비밀번호 변경 필요 여부 |
| `last_login_at` | 마지막 로그인 시각 |
| `active_yn` | 사용 여부 |
| `remarks` | 운영 메모 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `login_id`
- `user_name`
- `password_hash`
- `must_change_password`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `email`
- `client_id`
- `default_warehouse_id`
- `last_login_at`
- `remarks`

### unique 제약 후보

- `unique(login_id)`

### index 후보

- `index(client_id)`
- `index(active_yn)`

### scope 기준

- 고객사 사용자는 `client_id`가 필수다.
- 내부 운영자는 `client_id`가 있어도 고객사 사용자로 판단하지 않는다.
- 사용자 성격은 `role` 기준으로 판단한다.

### 생성/수정/삭제 정책

- 실제 비밀번호 평문 저장은 금지한다.
- 운영사 관리자는 비밀번호 조회가 금지되며 초기화/재발급만 가능하다.
- 삭제보다 `active_yn=false` 사용중지를 우선한다.

### Codex 구현 시 주의사항

- `client_id` 유무로 내부/고객사 사용자를 구분하지 않는다.
- 평문 비밀번호를 응답하거나 로그에 남기지 않는다.

## `roles`

### 테이블 목적

표준 role을 관리하고 사용자 권한 분류의 기준을 제공한다.

### 표준 role

- `SUPER_ADMIN`
- `INTERNAL_ADMIN`
- `INTERNAL_WORKER`
- `CLIENT_ADMIN`
- `CLIENT_USER`
- `READ_ONLY`

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | role 식별자 |
| `role_code` | role 저장 코드 |
| `role_name` | role 표시명 |
| `role_type` | 내부 운영자/고객사 사용자 분류 후보 |
| `active_yn` | 사용 여부 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `role_code`
- `role_name`
- `role_type`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- 없음

### unique 제약 후보

- `unique(role_code)`

### index 후보

- `index(role_type)`
- `index(active_yn)`

### scope 기준

- 전역 기준정보로 관리한다.

### 생성/수정/삭제 정책

- 표준 role은 시스템 기준값으로 관리한다.
- 삭제보다 사용중지를 우선하되, 표준 role 삭제는 금지 후보로 둔다.

### Codex 구현 시 주의사항

- 코드에서 임의 문자열 role을 새로 만들지 않는다.

## `user_roles`

### 테이블 목적

사용자와 role의 다대다 연결을 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `user_id` | 사용자 식별자 |
| `role_id` | role 식별자 |
| `created_at` | 연결 생성 시각 |

### 필수 컬럼

- `user_id`
- `role_id`
- `created_at`

### nullable 허용 후보

- 없음

### unique 제약 후보

- `unique(user_id, role_id)`

### index 후보

- `index(user_id)`
- `index(role_id)`

### scope 기준

- 사용자 scope는 `users`에서 판단한다.

### 생성/수정/삭제 정책

- 권한 변경 이력을 별도로 남길지 후속으로 결정한다.
- 연결 삭제는 권한 회수로 취급한다.

### Codex 구현 시 주의사항

- 사용자에게 role이 없는 상태로 일반 업무 API 접근을 허용하지 않는다.

## `permissions`

### 테이블 목적

세부 권한 단위를 관리한다. 1차 MVP에서는 작게 시작하되 위험 작업 권한 확장을 고려한다.

### 권한 후보

- `USER_MANAGE`
- `MASTER_MANAGE`
- `RETURN_PROCESS`
- `RETURN_CLOSE`
- `RETURN_OUTBOUND`
- `INVENTORY_VIEW`
- `INVENTORY_ADJUST`
- `SYSTEM_ADMIN`

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 권한 식별자 |
| `permission_code` | 권한 코드 |
| `permission_name` | 권한 표시명 |
| `description` | 설명 |
| `active_yn` | 사용 여부 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `permission_code`
- `permission_name`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `description`

### unique 제약 후보

- `unique(permission_code)`

### index 후보

- `index(active_yn)`

### scope 기준

- 전역 권한 기준정보로 관리한다.

### 생성/수정/삭제 정책

- 삭제보다 사용중지를 우선한다.
- 이미 role에 연결된 권한은 삭제하지 않는다.

### Codex 구현 시 주의사항

- 위험 작업은 단순 메뉴 접근이 아니라 별도 permission으로 분리한다.

## `role_permissions`

### 테이블 목적

role과 permission의 연결을 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `role_id` | role 식별자 |
| `permission_id` | permission 식별자 |
| `created_at` | 연결 생성 시각 |

### 필수 컬럼

- `role_id`
- `permission_id`
- `created_at`

### nullable 허용 후보

- 없음

### unique 제약 후보

- `unique(role_id, permission_id)`

### index 후보

- `index(role_id)`
- `index(permission_id)`

### scope 기준

- 전역 권한 연결로 관리한다.

### 생성/수정/삭제 정책

- 권한 변경 이력은 후속 감사 로그 정책에서 확정한다.

### Codex 구현 시 주의사항

- 권한 검사를 화면 표시용과 서버 보호용으로 분리해 생각한다.

## `auth_login_logs`

### 테이블 목적

로그인 성공/실패와 보안 이벤트를 기록한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 로그 식별자 |
| `user_id` | 사용자 식별자 후보 |
| `login_id` | 시도한 로그인 ID |
| `result` | 성공/실패 |
| `failure_reason` | 실패 사유 |
| `ip_address` | IP 후보 |
| `user_agent` | user agent 후보 |
| `created_at` | 기록 시각 |

### 필수 컬럼

- `id`
- `login_id`
- `result`
- `created_at`

### nullable 허용 후보

- `user_id`
- `failure_reason`
- `ip_address`
- `user_agent`

### unique 제약 후보

- 없음

### index 후보

- `index(user_id, created_at)`
- `index(login_id, created_at)`
- `index(result, created_at)`

### scope 기준

- 사용자와 연결되면 `users.client_id`를 통해 간접 확인한다.

### 생성/수정/삭제 정책

- 보안 로그는 생성 후 수정하지 않는 것을 원칙으로 한다.
- 보관기간은 후속 보안/운영 정책에서 확정한다.

### Codex 구현 시 주의사항

- 민감정보 과다 저장을 금지한다.
- 비밀번호, 토큰, 인증코드를 로그에 남기지 않는다.

## B. 기준정보

## `clients`

### 테이블 목적

고객사/화주 기준정보를 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 고객사 식별자 |
| `client_code` | 고객사 코드 |
| `client_name` | 고객사명 |
| `business_no` | 사업자번호 후보 |
| `contact_name` | 담당자명 |
| `contact_phone` | 연락처 |
| `contact_email` | 이메일 |
| `use_oms` | OMS 사용 여부 |
| `use_wms` | WMS 사용 여부 |
| `use_returns` | 반품 사용 여부 |
| `use_settlement` | 정산 사용 여부 |
| `active_yn` | 사용 여부 |
| `remarks` | 메모 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `client_code`
- `client_name`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `business_no`
- `contact_name`
- `contact_phone`
- `contact_email`
- `remarks`

### unique 제약 후보

- `unique(client_code)`

### index 후보

- `index(active_yn)`
- `index(client_name)`

### scope 기준

- 고객사는 업무 데이터의 최상위 `client_id` scope 기준이다.

### 생성/수정/삭제 정책

- 고객사는 화주/업체이며 동현물류 운영사와 혼동하지 않는다.
- 삭제보다 사용중지를 우선한다.

### Codex 구현 시 주의사항

- 고객사별 데이터 접근은 role/client scope로 제한한다.

## `warehouses`

### 테이블 목적

창고 기준정보를 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 창고 식별자 |
| `warehouse_code` | 창고 코드 |
| `warehouse_name` | 창고명 |
| `warehouse_type` | 창고 유형 |
| `address` | 주소 |
| `active_yn` | 사용 여부 |
| `remarks` | 메모 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `warehouse_code`
- `warehouse_name`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `warehouse_type`
- `address`
- `remarks`

### unique 제약 후보

- `unique(warehouse_code)`

### index 후보

- `index(active_yn)`
- `index(warehouse_type)`

### scope 기준

- 창고 업무의 `warehouse_id` scope 기준이다.

### 생성/수정/삭제 정책

- 이미 업무 데이터에서 사용된 창고는 삭제하지 않는다.
- 삭제보다 사용중지를 우선한다.

### Codex 구현 시 주의사항

- 창고 전체 목록을 그대로 업무 선택에 노출하지 않고 고객사-창고 연결을 거친다.

## `client_warehouse_settings`

### 테이블 목적

고객사별 사용창고와 업무 용도를 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 연결 식별자 |
| `client_id` | 고객사 식별자 |
| `warehouse_id` | 창고 식별자 |
| `usage_type` | 사용 용도 |
| `is_default` | 기본 여부 |
| `active_yn` | 사용 여부 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### `usage_type` 후보

- `INBOUND`
- `OUTBOUND`
- `RETURN_GOOD`
- `RETURN_HOLD`
- `RETURN_DISPOSAL`
- `RETURN_REFURB`
- `RETURN_MANUFACTURER`
- `SAMPLE`
- `STORAGE`

### 필수 컬럼

- `id`
- `client_id`
- `warehouse_id`
- `usage_type`
- `is_default`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- 없음

### unique 제약 후보

- `unique(client_id, warehouse_id, usage_type)`

### index 후보

- `index(client_id)`
- `index(warehouse_id)`
- `index(client_id, usage_type)`

### scope 기준

- `client_id`와 `warehouse_id`를 함께 가진다.

### 생성/수정/삭제 정책

- 고객사가 사용하지 않는 창고는 입고/출고/반품 작업에서 선택되지 않아야 한다.
- 삭제보다 `active_yn=false` 사용중지를 우선한다.

### Codex 구현 시 주의사항

- 창고 선택은 선택 고객사의 사용창고만 보여준다.

## `locations`

### 테이블 목적

창고 내 위치를 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 위치 식별자 |
| `warehouse_id` | 창고 식별자 |
| `location_code` | 위치 코드 |
| `location_name` | 위치명 |
| `location_type` | 위치 유형 |
| `active_yn` | 사용 여부 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `warehouse_id`
- `location_code`
- `location_name`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `location_type`

### unique 제약 후보

- `unique(warehouse_id, location_code)`

### index 후보

- `index(warehouse_id)`
- `index(active_yn)`

### scope 기준

- `warehouse_id` scope를 가진다.

### 생성/수정/삭제 정책

- 사용된 위치는 삭제보다 사용중지를 우선한다.

### Codex 구현 시 주의사항

- 위치는 고객사 직접 scope가 아니라 창고 scope를 통해 연결된다.

## `products`

### 테이블 목적

고객사별 상품 기준정보와 대표 바코드를 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 상품 식별자 |
| `client_id` | 고객사 식별자 |
| `product_code` | 상품코드 |
| `product_name` | 상품명 |
| `barcode` | 대표 낱개 바코드 |
| `specification` | 규격 |
| `unit_name` | 기본 단위명 |
| `active_yn` | 사용 여부 |
| `remarks` | 메모 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `client_id`
- `product_code`
- `product_name`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `barcode`
- `specification`
- `unit_name`
- `remarks`

### unique 제약 후보

- `unique(client_id, product_code)`

### index 후보

- `index(client_id, product_name)`
- `index(client_id, barcode)`
- `index(client_id, active_yn)`

### scope 기준

- 상품은 `client_id` 범위 안에서 관리한다.

### 생성/수정/삭제 정책

- 대표 바코드는 낱개 기준이며 `unit_qty=1`로 해석한다.
- 삭제보다 사용중지를 우선한다.

### Codex 구현 시 주의사항

- 실제 스캔 매칭은 상품코드, 대표바코드, 추가바코드를 모두 지원해야 한다.

## `product_barcodes`

### 테이블 목적

상품의 추가/박스/카톤/외부 바코드와 스캔 1회당 반영 수량을 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 바코드 식별자 |
| `client_id` | 고객사 식별자 |
| `product_id` | 상품 식별자 |
| `barcode` | 원본 바코드 |
| `barcode_norm` | 비교용 정규화 바코드 |
| `barcode_type` | 바코드 유형 |
| `unit_qty` | 스캔 1회당 반영 수량 |
| `active_yn` | 사용 여부 |
| `remarks` | 메모 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### `barcode_type` 후보

- `EACH`
- `BOX`
- `CARTON`
- `EXTERNAL`

### 필수 컬럼

- `id`
- `client_id`
- `product_id`
- `barcode`
- `barcode_norm`
- `barcode_type`
- `unit_qty`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `remarks`

### unique 제약 후보

- `unique(client_id, barcode_norm)`

### index 후보

- `index(client_id, product_id)`
- `index(client_id, barcode_type)`
- `index(client_id, active_yn)`

### scope 기준

- 바코드 매칭은 반드시 `client_id` 범위 안에서 수행한다.

### 생성/수정/삭제 정책

- `unit_qty`는 1 이상 정수다.
- 카톤/박스/외부 바코드는 `product_barcodes`에 등록한다.
- 기존 사용 바코드는 삭제보다 `active_yn=false` 사용중지를 우선한다.

### Codex 구현 시 주의사항

- 다른 고객사의 같은 `barcode`는 현재 고객사 작업에서 매칭되면 안 된다.

## `common_code_groups`

### 테이블 목적

공통코드 그룹을 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 그룹 식별자 |
| `group_code` | 그룹 코드 |
| `group_name` | 그룹명 |
| `description` | 설명 |
| `active_yn` | 사용 여부 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `group_code`
- `group_name`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `description`

### unique 제약 후보

- `unique(group_code)`

### index 후보

- `index(active_yn)`

### scope 기준

- 기본은 전역 기준정보다.

### 생성/수정/삭제 정책

- 삭제보다 사용중지를 우선한다.
- 시스템에서 사용하는 그룹은 잠금 후보로 둔다.

### Codex 구현 시 주의사항

- `code_masters` 같은 중복 공통코드 구조를 만들지 않는다.

## `common_codes`

### 테이블 목적

공통코드 값을 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 코드 식별자 |
| `group_id` | 그룹 식별자 |
| `code_value` | 저장 키 |
| `code_name` | 표시명 |
| `sort_order` | 정렬순서 |
| `system_yn` | 시스템 코드 여부 |
| `locked_yn` | 잠금 여부 |
| `active_yn` | 사용 여부 |
| `description` | 설명 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### 필수 컬럼

- `id`
- `group_id`
- `code_value`
- `code_name`
- `sort_order`
- `system_yn`
- `locked_yn`
- `active_yn`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `description`

### unique 제약 후보

- `unique(group_id, code_value)`

### index 후보

- `index(group_id, active_yn)`
- `index(sort_order)`

### scope 기준

- 기본은 그룹 기준 전역 코드다.

### 생성/수정/삭제 정책

- `code_value`는 저장 키이며 변경 금지다.
- 표시명은 `code_name`으로 변경 가능하다.
- 삭제보다 사용중지를 우선한다.

### Codex 구현 시 주의사항

- 화면별 enum 하드코딩을 늘리지 말고 공통코드 기준을 우선 확인한다.

## C. import job / 업로드

## `import_jobs`

### 테이블 목적

업로드 작업 단위, 원본 source, 검증/저장 진행 상태, 업로드 이력을 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | import job 식별자 |
| `import_type` | 업무 import 유형 |
| `source_type` | 외부 원본 유형 |
| `source_name` | 원본 이름 |
| `requested_client_id` | 요청 고객사 후보 |
| `requested_warehouse_id` | 요청 창고 후보 |
| `status` | 진행 상태 |
| `total_rows` | 전체 row 수 |
| `parsed_rows` | 파싱 row 수 |
| `valid_rows` | 유효 row 수 |
| `invalid_rows` | 오류 row 수 |
| `inserted_rows` | 추가 row 수 |
| `updated_rows` | 수정 row 수 |
| `skipped_rows` | 제외 row 수 |
| `error_rows` | 처리 오류 row 수 |
| `progress_percent` | 진행률 |
| `file_name` | 원본 파일명 |
| `worksheet_name` | worksheet 이름 |
| `message` | 처리 메시지 |
| `raw_json` | 원본/부가 payload |
| `created_by` | 업로드 사용자 |
| `created_at` | 생성 시각 |
| `started_at` | 시작 시각 |
| `finished_at` | 종료 시각 |
| `updated_at` | 수정 시각 |

### `status` 후보

- `UPLOADED`
- `PARSING`
- `VALIDATING`
- `READY_TO_SAVE`
- `SAVING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

### `import_type` 후보

- `RETURN_EXPECTED`
- `RETURN_RECEPTION`
- `INBOUND_EXPECTED`
- `OUTBOUND_ORDER`
- `PRODUCT_MASTER`
- `PRODUCT_BARCODE`

### 필수 컬럼

- `id`
- `import_type`
- `source_type`
- `status`
- `created_by`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `source_name`
- `requested_client_id`
- `requested_warehouse_id`
- `file_name`
- `worksheet_name`
- `message`
- `raw_json`
- `started_at`
- `finished_at`

### unique 제약 후보

- 없음

### index 후보

- `index(import_type, created_at)`
- `index(status, created_at)`
- `index(requested_client_id, created_at)`

### scope 기준

- 고객사 업무 import는 `requested_client_id`를 가진다.
- 창고 업무 import는 `requested_warehouse_id` 후보를 가진다.

### 생성/수정/삭제 정책

- preview와 save 확정을 분리한다.
- import job은 원본/검증/업로드 이력 담당이다.
- 실제 업무 처리는 target 업무 테이블에 반영된 뒤 진행한다.

### Codex 구현 시 주의사항

- import job 자체를 업무 처리 원장으로 쓰지 않는다.

## `import_job_files`

### 테이블 목적

업로드 파일 메타데이터를 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 파일 식별자 |
| `job_id` | import job 식별자 |
| `file_name` | 원본 파일명 |
| `stored_file_name` | 저장 파일명 |
| `relative_path` | 상대 저장 경로 |
| `mime_type` | MIME type |
| `size_bytes` | 파일 크기 |
| `uploaded_by` | 업로드 사용자 |
| `uploaded_at` | 업로드 시각 |

### 필수 컬럼

- `id`
- `job_id`
- `file_name`
- `uploaded_by`
- `uploaded_at`

### nullable 허용 후보

- `stored_file_name`
- `relative_path`
- `mime_type`
- `size_bytes`

### unique 제약 후보

- 없음

### index 후보

- `index(job_id)`
- `index(uploaded_at)`

### scope 기준

- scope는 `import_jobs`를 통해 간접 확인한다.

### 생성/수정/삭제 정책

- 원본 파일 재다운로드 정책은 후속으로 둔다.
- 민감정보와 보관기간 정책을 나중에 확정한다.

### Codex 구현 시 주의사항

- 파일 저장 경로를 코드에 하드코딩하지 않는다.

## `import_job_rows`

### 테이블 목적

원본 row, 정규화 결과, 검증 상태, 업무 테이블 반영 결과를 row 단위로 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | row 식별자 |
| `job_id` | import job 식별자 |
| `client_id` | 고객사 후보 |
| `row_no` | 원본 row 번호 |
| `source_row_key` | 외부 원본 row key |
| `row_hash` | row 중복/변경 비교 해시 |
| `raw_json` | 원본 row |
| `normalized_json` | 정규화 row |
| `validation_status` | 검증 상태 |
| `validation_message` | 검증 메시지 |
| `target_action` | 업무 반영 액션 |
| `target_table` | 반영 대상 테이블 |
| `target_id` | 반영 대상 식별자 |
| `created_at` | 생성 시각 |
| `updated_at` | 수정 시각 |

### `validation_status` 후보

- `VALID`
- `WARNING`
- `INVALID`

### `target_action` 후보

- `INSERT`
- `UPDATE`
- `SKIP`
- `ERROR`

### 필수 컬럼

- `id`
- `job_id`
- `row_no`
- `raw_json`
- `validation_status`
- `created_at`
- `updated_at`

### nullable 허용 후보

- `client_id`
- `source_row_key`
- `row_hash`
- `normalized_json`
- `validation_message`
- `target_action`
- `target_table`
- `target_id`

### unique 제약 후보

- `unique(job_id, row_no)`

### index 후보

- `index(job_id, row_no)`
- `index(job_id, validation_status)`
- `index(row_hash)`
- `index(source_row_key)`

### scope 기준

- 고객사 매핑이 된 row는 `client_id`를 가진다.
- 고객사 미매칭 row는 업무 테이블 반영 전 오류/경고로 처리한다.

### 생성/수정/삭제 정책

- 원본 `row_no`와 원본 순서를 보존한다.
- `raw_json`과 `normalized_json`을 분리한다.
- row별 `target_table`/`target_id`로 업무 반영 결과를 추적한다.

### Codex 구현 시 주의사항

- import row와 실제 업무 row를 혼동하지 않는다.

## `import_validation_errors`

### 테이블 목적

import job row별 검증 오류와 경고를 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 오류 식별자 |
| `job_id` | import job 식별자 |
| `row_id` | import row 식별자 |
| `row_no` | 원본 row 번호 |
| `field_name` | 오류 필드명 |
| `raw_value` | 원본 값 |
| `error_code` | 오류 코드 |
| `error_message` | 오류 메시지 |
| `severity` | 심각도 |
| `created_at` | 생성 시각 |

### `severity` 후보

- `INFO`
- `WARNING`
- `ERROR`

### 필수 컬럼

- `id`
- `job_id`
- `error_code`
- `error_message`
- `severity`
- `created_at`

### nullable 허용 후보

- `row_id`
- `row_no`
- `field_name`
- `raw_value`

### unique 제약 후보

- 없음

### index 후보

- `index(job_id)`
- `index(row_id)`
- `index(job_id, severity)`

### scope 기준

- scope는 `import_jobs`와 `import_job_rows`를 통해 간접 확인한다.

### 생성/수정/삭제 정책

- 검증 오류는 재검증 시 새로 생성하거나 갱신하는 정책을 후속 확정한다.

### Codex 구현 시 주의사항

- 오류 메시지는 운영자가 이해할 수 있는 한글 설명을 제공한다.

## D. P0 재고 테이블

## `inventory_events`

### 테이블 목적

재고 수량 변경의 원장 이벤트를 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 이벤트 식별자 |
| `event_no` | 이벤트 번호 |
| `client_id` | 고객사 식별자 |
| `warehouse_id` | 창고 식별자 |
| `location_id` | 위치 식별자 |
| `product_id` | 상품 식별자 |
| `product_code` | 이벤트 시점 상품코드 |
| `stock_status` | 재고 상태 |
| `event_type` | 이벤트 유형 |
| `qty_delta` | 증감 수량 |
| `source_type` | 원천 업무 유형 |
| `source_id` | 원천 업무 식별자 |
| `source_line_id` | 원천 업무 라인 식별자 |
| `idempotency_key` | 멱등성 키 |
| `reverse_event_id` | 반전 대상 이벤트 |
| `event_reason` | 이벤트 사유 |
| `memo` | 메모 |
| `created_by` | 생성 사용자 |
| `created_at` | 생성 시각 |
| `raw_json` | 부가 payload |

### `event_type` 후보

- `INBOUND_CONFIRM`
- `INBOUND_CANCEL`
- `INBOUND_ADJUST_PLUS`
- `INBOUND_ADJUST_MINUS`
- `OUTBOUND_SHIP`
- `OUTBOUND_CANCEL`
- `RETURN_JUDGEMENT`
- `RETURN_JUDGEMENT_REVERSAL`
- `RETURN_JUDGEMENT_CORRECTION`
- `RETURN_EXTERNAL_OUTBOUND`
- `MANUAL_ADJUSTMENT`

### `stock_status` 후보

- `GOOD`
- `HOLD`
- `DAMAGED`
- `REFURB_A`
- `REFURB_B`
- `REFURB_C`
- `MANUFACTURER_RETURN`
- `SAMPLE`
- `DISPOSAL`

### 필수 컬럼

- `id`
- `event_no`
- `client_id`
- `warehouse_id`
- `product_id`
- `stock_status`
- `event_type`
- `qty_delta`
- `source_type`
- `source_id`
- `idempotency_key`
- `created_at`

### nullable 허용 후보

- `location_id`
- `product_code`
- `source_line_id`
- `reverse_event_id`
- `event_reason`
- `memo`
- `created_by`
- `raw_json`

### unique 제약 후보

- `unique(idempotency_key)`
- `unique(event_no)`

### index 후보

- `index(client_id, product_id, created_at)`
- `index(source_type, source_id)`
- `index(reverse_event_id)`
- `index(client_id, warehouse_id, product_id, stock_status)`

### scope 기준

- `client_id`, `warehouse_id`, `product_id`, `stock_status`를 기준으로 재고 이벤트를 분리한다.

### 생성/수정/삭제 정책

- `inventory_events`는 재고 원장이다.
- 생성된 이벤트는 삭제하지 않는다.
- 취소/정정은 `reverse_event_id` 또는 보정 이벤트로 처리한다.
- 같은 `idempotency_key`는 중복 반영하지 않는다.

### Codex 구현 시 주의사항

- 현재고를 직접 수정하지 않고 반드시 원장 이벤트를 통해 반영한다.

## `current_inventory`

### 테이블 목적

현재고 빠른 조회를 위한 요약 수량을 관리한다.

### 주요 컬럼 후보

| 컬럼 | 설명 |
| --- | --- |
| `id` | 현재고 식별자 |
| `client_id` | 고객사 식별자 |
| `warehouse_id` | 창고 식별자 |
| `location_id` | 위치 식별자 |
| `product_id` | 상품 식별자 |
| `stock_status` | 재고 상태 |
| `qty_on_hand` | 현재 수량 |
| `updated_at` | 갱신 시각 |

### 필수 컬럼

- `id`
- `client_id`
- `warehouse_id`
- `product_id`
- `stock_status`
- `qty_on_hand`
- `updated_at`

### nullable 허용 후보

- `location_id`

### unique 제약 후보

- `unique(client_id, warehouse_id, location_id, product_id, stock_status)`

### index 후보

- `index(client_id, product_id)`
- `index(warehouse_id, product_id)`
- `index(client_id, warehouse_id, product_id, stock_status)`

### scope 기준

- `client_id`, `warehouse_id`, `location_id`, `product_id`, `stock_status` 조합으로 현재고를 요약한다.

### 생성/수정/삭제 정책

- `current_inventory`는 빠른 조회용 요약이다.
- 최종 이력 기준은 `inventory_events`다.
- `inventory_events` 합계와 `current_inventory`가 맞는지 정합성 점검이 필요하다.

### Codex 구현 시 주의사항

- legacy inventory 테이블을 동시에 원장처럼 사용하지 않는다.

## P0 테이블 간 핵심 관계

```text
users
  → user_roles
  → roles
```

```text
roles
  → role_permissions
  → permissions
```

```text
clients
  → client_warehouse_settings
  → warehouses
```

```text
clients
  → products
  → product_barcodes
```

```text
common_code_groups
  → common_codes
```

```text
import_jobs
  → import_job_rows
  → import_validation_errors
```

```text
import_job_rows
  → target business table
```

```text
inventory_events
  → current_inventory 반영
```

## P0에서 아직 만들지 않을 것

- `return_receipts` 등 반품 업무 테이블 상세
- `inbound_tasks` / `outbound_tasks` 상세
- `settlement_headers` / `settlement_lines`
- ERP 전송 상세 테이블
- 고객사 포털 상세 테이블
- AI 로그 테이블
- Local Agent 자동 업데이트 테이블
- 복잡한 승인/결재 테이블

## 중복/주의사항

- `code_masters`와 `common_codes`를 동시에 만들지 않는다.
- `products.barcode`와 `product_barcodes`의 역할을 혼동하지 않는다.
- `import_job_rows`와 실제 업무 테이블을 혼동하지 않는다.
- `return_expected_rows` 같은 업무 테이블에 import row 역할을 과도하게 넣지 않는다.
- `scan_events`와 `inventory_events`를 섞지 않는다.
- legacy inventory 테이블을 `current_inventory`와 동시에 원장처럼 쓰지 않는다.
- `batch_id`를 업무 중심키로 쓰지 않는다.

## Codex 구현 전 체크

- 이 테이블은 P0에 꼭 필요한가?
- `client_id` scope가 필요한가?
- `warehouse_id` scope가 필요한가?
- 삭제 대신 `active_yn`/`status`로 처리해야 하는가?
- unique/index 후보가 있는가?
- import job과 업무 테이블을 분리했는가?
- 재고 수량 변경은 `inventory_events`를 통해서만 처리되는가?
- 기존 문서와 용어가 충돌하지 않는가?
