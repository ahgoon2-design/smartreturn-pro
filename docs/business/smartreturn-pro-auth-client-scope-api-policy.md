# SmartReturn Pro 권한/agency/client scope API 정책

이 문서는 SmartReturn Pro 신규 제작 기준이며, 기존 SmartReturn 구현기록을 그대로 따르지 않는다.

이 문서는 구현 지시가 아니라 API 설계 전 권한 기준 문서다. 실제 FastAPI dependency, router, service 코드는 후속 작업에서 만든다.

## 1. 문서 목적

SmartReturn Pro의 모든 API는 `role`, `agency_id`, `client_id`, `client_unit_id`, `warehouse_id` 기준을 일관되게 적용해야 한다. 기준정보, 반품, 입고, 출고, 재고, 정산 API가 서로 다른 권한 해석을 가지면 대리점/고객사 데이터 격리와 창고 범위 제한이 무너진다.

이 문서는 다음 기준을 고정한다.

- 내부 운영자와 고객사 사용자는 `client_id` 유무가 아니라 `role` 기준으로 구분한다.
- 서버는 요청마다 인증 컨텍스트를 만들고, 그 컨텍스트로 `effective_agency_id`, `effective_client_id`, `effective_client_unit_id`, `effective_warehouse_id`를 결정한다.
- 프론트의 고객사/창고 선택 제한은 사용자 경험일 뿐이며, 실제 보안은 백엔드 API에서 강제한다.
- 권한 검증 실패 시 데이터 생성, 수정, 확정, 취소, 재고 이벤트 생성은 발생하면 안 된다.

## 2. 기본 역할 정의

| 구분 | role | 의미 |
| --- | --- | --- |
| 내부 운영자 | `SUPER_ADMIN` | 동현물류 최고 관리자. 전체 운영, 시스템 설정, 위험 작업 권한을 가진다. |
| 내부 운영자 | `INTERNAL_ADMIN` | 동현물류 운영 관리자. 고객사/업무 운영과 대부분의 관리 작업을 수행한다. |
| 내부 운영자 | `INTERNAL_WORKER` | 동현물류 작업자. 반품, 입고, 출고 등 현장 업무를 수행한다. |
| 대리점 사용자 | `AGENCY_ADMIN` | 자기 `agency_id` 소속 고객사와 업무 자료를 관리한다. |
| 고객사 사용자 | `CLIENT_ADMIN` | 특정 고객사 관리자. 자기 고객사 자료 조회와 일부 업로드 후보 권한을 가진다. |
| 고객사 사용자 | `CLIENT_USER` | 특정 고객사 일반 사용자. 자기 고객사 조회 중심으로 사용한다. |
| 고객사 사용자 | `READ_ONLY` | 조회 전용 사용자. 변경 작업을 수행하지 않는다. |

정책은 다음과 같다.

- 내부 운영자는 동현물류 운영자다.
- 고객사 사용자는 특정 `client_id`에 소속된 고객사/화주 사용자다.
- `client_id`가 있는 내부 운영자도 고객사 사용자로 판단하지 않는다.
- `role`이 비어 있거나 알 수 없는 사용자는 기본적으로 접근을 제한한다.
- legacy role이 필요하다면 후속 호환 정책으로 분리하고, Pro 신규 기준은 위 role을 표준으로 삼는다.

## 2-1. agency scope 기본 원칙

- 기본 계층은 `platform_owner → agency_id → client_id → client_unit_id → warehouse_id`다.
- `client_id`가 있는 업무 row는 `clients.agency_id` 기준으로 `agency_id`를 확정한다.
- 요청 body의 `agency_id`를 그대로 신뢰하지 않는다.
- `AGENCY_ADMIN`은 자기 `agency_id` 소속 client 자료만 조회, 생성, 수정할 수 있다.
- `client_unit_id`는 해당 `client_id`에 속해야 한다.
- `warehouse_id`는 해당 `agency_id`, `client_id`, 필요 시 `client_unit_id` 범위에 맞아야 한다.
- 프론트 메뉴 숨김만으로 agency 권한을 처리하지 않는다.

## 3. client scope 기본 원칙

- 고객사 선택 가능 여부는 `client_id` 유무가 아니라 `role` 기준이다.
- 내부 운영자는 고객사를 선택할 수 있다.
- 고객사 사용자는 자기 `client_id`로 고정된다.
- 고객사 사용자가 요청 body, query, path에 다른 `client_id`를 넣어도 서버는 신뢰하지 않는다.
- 서버는 로그인 컨텍스트 기준으로 `effective_client_id`를 결정한다.
- 모든 업무 데이터 조회, 생성, 수정, 삭제성 작업은 `client_id` scope를 검증해야 한다.
- 프론트의 고객사 선택 제한은 UX일 뿐이고, 실제 보안은 백엔드에서 강제한다.
- 내부 운영자가 `selected_client_id` 없이 전체 조회를 요청할 수 있는 API는 관리자 통합조회처럼 명시된 API로 제한한다.
- 고객사 사용자는 전체 고객사 조회, 타 고객사 검색, 타 고객사 import job 조회를 할 수 없다.

## 4. warehouse scope 기본 원칙

- 창고 업무 데이터는 `warehouse_id` scope를 가진다.
- 창고 목록은 선택 고객사의 사용창고만 반환해야 한다.
- 고객사 사용자는 자기 고객사에 연결된 창고만 조회/선택할 수 있다.
- 내부 운영자도 특정 고객사를 선택한 업무 화면에서는 해당 고객사의 사용창고만 선택해야 한다.
- 고객사-창고 연결이 없는 창고는 입고/출고/반품 작업에서 선택되지 않아야 한다.
- `warehouse_id`가 필요한 업무에서 `warehouse_id`가 누락되면 생성, 확정, 재고반영을 막는다.
- 창고 전체 목록 조회는 내부 관리자용 기준정보 화면에서만 허용한다.
- `warehouse_id` 검증은 화면 select 옵션과 별개로 API에서 다시 수행한다.

## 5. 인증 컨텍스트 후보

`AuthContext`는 요청마다 서버에서 검증된 사용자, `role`, `client` 기준으로 만든다.

| 필드 | 의미 |
| --- | --- |
| `user_id` | 로그인 사용자 식별자 |
| `login_id` | 로그인 계정 ID |
| `user_name` | 사용자 표시명 |
| `roles` | 사용자에게 부여된 role 목록 |
| `client_id` | 사용자가 소속된 고객사 후보 |
| `agency_id` | 사용자가 소속되거나 접근 가능한 대리점 후보 |
| `client_code` | 고객사 코드 |
| `client_name` | 고객사명 |
| `default_warehouse_id` | 기본 창고 후보 |
| `must_change_password` | 첫 로그인 또는 초기화 후 비밀번호 변경 필요 여부 |
| `is_internal_user` | 내부 운영자 여부 |
| `is_client_user` | 고객사 사용자 여부 |
| `allowed_client_ids` | 접근 가능한 고객사 목록 후보 |
| `allowed_agency_ids` | 접근 가능한 대리점 목록 후보 |
| `selected_client_id` | 프론트 또는 요청에서 선택한 고객사 후보 |
| `selected_agency_id` | 프론트 또는 요청에서 선택한 대리점 후보 |
| `effective_agency_id` | 서버가 최종 결정한 대리점 scope |
| `effective_client_id` | 서버가 최종 결정한 고객사 scope |

정책은 다음과 같다.

- 프론트가 보내는 `client_id`는 요청 의도일 뿐이며, 최종 범위는 서버가 계산한다.
- `must_change_password=true`인 사용자는 비밀번호 변경 API 외 일반 업무 API를 사용할 수 없다.
- `is_internal_user`와 `is_client_user`는 `role` 기준으로 계산한다.
- 내부 운영자에게 `client_id`가 있어도 `is_client_user=true`로 만들지 않는다.
- 고객사 사용자의 `allowed_client_ids`는 기본적으로 자기 `client_id` 하나다.

## 6. 공통 함수/Dependency 후보

아래 항목은 실제 코드가 아니라 API 구현 전 필요한 공통 함수 후보다.

| 후보 | 목적 | 입력값 | 반환값 | 실패 시 처리 |
| --- | --- | --- | --- | --- |
| `get_current_auth_context` | 요청 사용자와 role/client 정보를 검증해 `AuthContext`를 만든다. | 토큰, 세션, 요청 메타 | `AuthContext` | 인증 실패 시 401, 비활성 사용자면 403 |
| `is_internal_user` | 내부 운영자 여부를 판정한다. | `roles` | boolean | 알 수 없는 role이면 false |
| `is_client_user` | 고객사 사용자 여부를 판정한다. | `roles` | boolean | 알 수 없는 role이면 false |
| `resolve_agency_scope` | 요청의 대리점 범위를 서버 기준으로 확정한다. | `AuthContext`, `requested_agency_id`, API scope 옵션 | `effective_agency_id` 또는 전체 scope 허용 표시 | 접근 불가 시 403 |
| `resolve_client_scope` | 요청의 고객사 범위를 서버 기준으로 확정한다. | `AuthContext`, `requested_client_id`, API scope 옵션 | `effective_client_id` 또는 전체 scope 허용 표시 | 접근 불가 시 403 |
| `resolve_client_unit_scope` | 요청의 운영단위가 고객사 범위에 맞는지 확정한다. | `effective_client_id`, `requested_client_unit_id` | `effective_client_unit_id` | 불일치 시 400/403 |
| `resolve_agency_id_from_client` | 고객사 기준으로 대리점 scope를 확정한다. | `client_id` | `agency_id` | 고객사 없음/권한 밖이면 404/403 |
| `require_client_access` | 대상 row의 `client_id` 접근 가능 여부를 검증한다. | `AuthContext`, `row.client_id` | 검증 통과 | 접근 불가 시 403 |
| `require_warehouse_access` | `warehouse_id`가 선택 고객사의 사용창고인지 검증한다. | `AuthContext`, `effective_client_id`, `warehouse_id` | 검증 통과 | 접근 불가 시 403 |
| `require_roles` | API 호출에 필요한 role을 확인한다. | `AuthContext`, 허용 role 목록 | 검증 통과 | 권한 부족 시 403 |
| `require_password_change_completed` | 비밀번호 변경 필요 사용자의 업무 API 접근을 막는다. | `AuthContext` | 검증 통과 | `must_change_password=true`면 403 |
| `resolve_effective_client_id` | 생성/조회/수정 요청에서 사용할 최종 `client_id`를 결정한다. | `AuthContext`, body/query/path의 `client_id` | `effective_client_id` | 불일치 또는 누락 시 403/400 |
| `resolve_effective_warehouse_id` | 업무에 사용할 최종 `warehouse_id`를 결정한다. | `AuthContext`, `effective_client_id`, 요청 `warehouse_id` | `effective_warehouse_id` | 누락 또는 권한 밖이면 400/403 |

### 6-1. `resolve_client_scope` 정책

- 내부 운영자는 `requested_client_id`가 있으면 그 고객사 범위로 처리한다.
- 내부 운영자가 `requested_client_id`를 생략하면 전체 조회가 가능한 API에서만 전체 범위를 허용한다.
- 고객사 사용자는 `requested_client_id`와 관계없이 자기 `client_id`로 고정한다.
- 고객사 사용자가 다른 `client_id`를 요청하면 403을 반환한다.
- `client_id`가 필요한 API에서 최종 `effective_client_id`를 만들 수 없으면 400 또는 403으로 막는다.

### 6-2. `require_client_access` 정책

- 대상 row의 `client_id`와 `AuthContext`의 허용 client 범위를 비교한다.
- 접근 불가 시 403을 반환한다.
- 권한 실패 시 수량, 상태, 로그, 재고 이벤트를 변경하면 안 된다.
- 단건 API는 상세 응답을 만들기 전에 이 검증을 통과해야 한다.

### 6-3. `require_warehouse_access` 정책

- `warehouse_id`가 선택 고객사의 사용창고인지 확인한다.
- 권한 밖 창고이면 403을 반환한다.
- 고객사-창고 연결이 비활성 상태이면 선택할 수 없다.
- 창고가 필요한 확정/재고반영 API에서 `warehouse_id`가 없으면 400으로 막는다.

## 7. API 유형별 권한 기준

### 7-1. 목록 조회 API

예시는 다음과 같다.

- `GET /api/products`
- `GET /api/returns`
- `GET /api/inventory/current`

정책은 다음과 같다.

- 내부 운영자는 `selected_client_id` 기준으로 조회한다.
- 고객사 사용자는 자기 `client_id` 기준으로만 조회한다.
- 고객사 사용자는 전체 client 조회가 불가능하다.
- 목록 조회는 항상 `client_id` 조건이 적용되어야 한다.
- 내부 운영자 전체 조회는 관리자/통합조회 등 명시된 API에서만 허용한다.
- `warehouse_id` 필터가 있는 경우 `require_warehouse_access`를 먼저 통과해야 한다.

### 7-2. 단건 상세 API

예시는 다음과 같다.

- `GET /api/returns/{receipt_id}`
- `GET /api/inventory/events/{event_id}`

정책은 다음과 같다.

- path id로 row를 찾은 뒤 `row.client_id`를 `require_client_access`로 검증한다.
- 권한 검증 전 상세 데이터를 응답하면 안 된다.
- 존재하지 않음과 권한 없음의 메시지는 운영 편의와 보안 균형을 고려한다.
- 상세 row에 `warehouse_id`가 있으면 필요한 API에서 `require_warehouse_access`도 함께 확인한다.

### 7-3. 생성 API

예시는 다음과 같다.

- `POST /api/products`
- `POST /api/returns/expected/import`
- `POST /api/returns/receipts`

정책은 다음과 같다.

- 내부 운영자는 요청 `client_id`를 지정할 수 있다.
- 고객사 사용자는 자기 `client_id`로만 생성 가능하다.
- 고객사 사용자가 body의 `client_id`를 조작해도 서버는 자기 `client_id`로 보정하거나 403 처리한다.
- 창고가 필요한 생성 API는 warehouse access를 확인한다.
- 생성 row의 `client_id`는 프론트 값이 아니라 `effective_client_id`에서 가져온다.

### 7-4. 수정 API

예시는 다음과 같다.

- `PUT /api/products/{id}`
- `POST /api/returns/{id}/judge`
- `POST /api/inbound/tasks/{id}/confirm`

정책은 다음과 같다.

- 대상 row의 `client_id`를 먼저 검증한다.
- 확정, 취소, 정정, 재고반영 같은 위험 작업은 role 또는 permission을 추가 확인한다.
- 고객사 사용자는 기본적으로 내부 재고, 판정, 정산 확정 작업을 수행할 수 없다.
- 고객사 사용자에게 일부 수정 권한을 허용해야 한다면 후속 정책으로 분리한다.
- 권한 검증 실패 후에는 상태 변경, 로그 생성, 재고 이벤트 생성이 발생하면 안 된다.

### 7-5. 삭제/사용중지 API

정책은 다음과 같다.

- 기준정보는 삭제보다 `active_yn=false` 사용중지를 우선한다.
- 업무 데이터는 이미 처리, 확정, 재고반영된 경우 물리 삭제하지 않는다.
- 삭제성 작업은 `SUPER_ADMIN` 또는 `INTERNAL_ADMIN` 중심으로 제한한다.
- 삭제/사용중지 전 대상 `row.client_id` scope 검증을 먼저 수행한다.
- 삭제성 작업은 감사 로그 또는 변경 이력 후보를 둔다.

### 7-6. 파일 업로드/import job API

정책은 다음과 같다.

- import job 생성 시 `requested_client_id`는 권한 검증을 통과해야 한다.
- 고객사 사용자는 자기 `client_id` 외 import job 생성이 불가능하다.
- `import_job_rows`의 실제 `client_id`는 row 검증/매핑 결과에 따라 확정될 수 있다.
- 저장 확정 시에도 target 업무 테이블 반영 전 client scope를 재검증한다.
- import job 조회도 `requested_client_id` 또는 row `client_id` 기준으로 제한한다.
- import job 검증 단계와 업무 테이블 저장 단계는 별도 권한 검증 지점을 가진다.

### 7-7. 재고 이벤트 API

정책은 다음과 같다.

- `inventory_events` 생성은 서버 업무 흐름에서만 가능하다.
- 프론트나 Local Agent가 `inventory_events`를 직접 생성하지 않는다.
- `inventory_events` 조회는 `client_id` scope를 반드시 적용한다.
- `current_inventory` 조회는 `client_id`, `warehouse_id`, `product_id` 기준으로 제한한다.
- `idempotency_key` 중복 처리 시에도 권한 검증을 먼저 한다.
- 재고 정정/취소 API는 일반 수정 API보다 강한 role 또는 permission을 요구한다.

### 7-8. 스캔/Local Agent API

정책은 다음과 같다.

- `scan_events`는 스캔 입력/동기화 로그다.
- `scan_events`도 `client_id` scope를 가진다.
- Local Agent나 로컬 스캔 클라이언트는 재고를 직접 변경하지 않는다.
- 로컬 스캔 이벤트 수신 시 서버가 source 업무 row의 `client_id`를 검증해야 한다.
- `local_event_id` 중복은 `scan_events` idempotency로 처리하고, 재고 이벤트 idempotency와 분리한다.
- Local Agent 실패는 업무 저장 실패가 아니며, 재고 이벤트 생성 조건도 아니다.

## 8. role별 기본 권한 표

| role | 고객사 선택 가능 | 기준정보 관리 | 반품 처리 | 반품 마감 | 반품 반출 | 입고/출고 확정 | 재고 조회 | 재고 조정 | 정산 조회 | 사용자 관리 | 시스템 설정 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `SUPER_ADMIN` | 전체 가능 | 전체 가능 | 가능 | 가능 | 가능 | 가능 | 가능 | 가능 | 가능 | 전체 가능 | 전체 가능 |
| `INTERNAL_ADMIN` | 가능 | 가능 | 가능 | 가능 | 가능 | 가능 | 가능 | 제한적 가능 | 가능 | 가능 | 일부 위험 설정 제한 후보 |
| `INTERNAL_WORKER` | 업무 범위에서 가능 | 조회 중심 | 가능 | 제한적 가능 | 가능 | 가능 | 가능 | 제한 | 제한 | 불가 | 불가 |
| `AGENCY_ADMIN` | 자기 대리점 범위 | 자기 대리점 고객사 기준 | 제한/계약 기준 | 제한/계약 기준 | 제한/계약 기준 | 제한 | 자기 대리점 고객사 조회 | 불가 | 자기 대리점 정산 조회 | 자기 대리점 사용자 후보 | 불가 |
| `CLIENT_ADMIN` | 자기 고객사 고정 | 자기 고객사 조회/일부 요청 후보 | 제한 | 불가 | 불가 | 불가 | 자기 고객사 조회 | 불가 | 자기 고객사 조회 | 자기 고객사 사용자 후보 | 불가 |
| `CLIENT_USER` | 자기 고객사 고정 | 조회 중심 | 제한 | 불가 | 불가 | 불가 | 자기 고객사 조회 | 불가 | 자기 고객사 조회 | 불가 | 불가 |
| `READ_ONLY` | 자기 고객사 또는 허용 범위 | 조회만 | 조회만 | 조회만 | 조회만 | 조회만 | 조회만 | 불가 | 조회만 | 불가 | 불가 |

세부 권한은 `permissions`로 확장할 수 있다. 예를 들어 `RETURN_CLOSE`, `RETURN_OUTBOUND`, `INVENTORY_ADJUST`, `SYSTEM_ADMIN` 같은 위험 권한은 role 기본값에 더해 별도 permission으로 제한할 수 있다.

## 9. 화면별 client/warehouse 선택 기준

| 화면군 | client 선택 가능 여부 | warehouse 선택 가능 여부 | 내부 운영자 동작 | 고객사 사용자 동작 |
| --- | --- | --- | --- | --- |
| 기준정보 화면 | 내부 운영자는 가능 | 창고 기준정보는 전체, 고객사별 연결은 선택 고객사 기준 | 고객사, 창고, 고객사-창고 연결을 관리한다. | 자기 고객사 기준정보 조회 또는 제한된 요청만 가능하다. |
| 반품자료 준비 | 내부 운영자는 필수 선택 | 필요한 경우 선택 고객사의 사용창고만 | 선택 고객사 기준으로 import job과 반품예정 자료를 등록한다. | 자기 고객사 자료만 조회/업로드 후보로 제한한다. |
| 반품처리 작업 | 내부 운영자는 선택 고객사 기준 | 판정/목적 창고는 선택 고객사의 사용창고만 | 현장 스캔, 상품 확인, 판정을 수행한다. | 기본적으로 내부 처리 작업은 제한한다. |
| 반품 마감 | 내부 운영자는 선택 고객사 기준 | 필요 시 선택 고객사 사용창고만 | 기간/고객사/상태 기준 마감 대조와 확정을 수행한다. | 조회만 허용하거나 제한한다. |
| 반품 반출 | 내부 운영자는 선택 고객사 기준 | 반출 대상 창고는 선택 고객사의 사용창고만 | 반출 묶음 생성, 스캔 대조, 반출확정을 수행한다. | 기본적으로 반출확정은 불가하다. |
| 입고자료 준비 | 내부 운영자는 필수 선택 | 입고 대상 창고는 선택 고객사의 사용창고만 | 예정입고 자료 등록과 검증을 수행한다. | 자기 고객사 자료 업로드 후보만 허용한다. |
| 입고검수 작업 | 내부 운영자는 선택 고객사 기준 | 입고 창고 필수 | 입고검수와 확정 후보 작업을 수행한다. | 기본적으로 확정 작업은 제한한다. |
| 출고검수 작업 | 내부 운영자는 선택 고객사 기준 | 출고 창고 필수 | 출고검수와 확정 후보 작업을 수행한다. | 기본적으로 확정 작업은 제한한다. |
| 재고현황/재고이력 | 내부 운영자는 선택 고객사 또는 명시된 통합조회 | 선택 고객사의 사용창고 기준 | 고객사/창고/상품 기준으로 조회한다. | 자기 고객사와 연결 창고 범위만 조회한다. |
| 정산 | 내부 운영자는 선택 고객사 기준 | 필요한 경우 선택 고객사 창고 기준 | 정산 조회/생성/검토 후보 작업을 수행한다. | 자기 고객사 정산 조회 중심으로 제한한다. |
| 고객사 포털 | 선택 불가 | 자기 고객사 연결 창고만 | 내부 운영자용 화면이 아니다. | 자기 고객사 데이터만 조회/업로드한다. |

## 10. 실패/위험 사례

- `client_id`가 있는 내부 운영자를 고객사 사용자로 오판하는 경우.
- 고객사 사용자가 query/body의 `client_id`를 바꿔 타 고객사 자료를 조회하는 경우.
- 대리점 사용자가 query/body의 `agency_id`를 바꿔 타 대리점 자료를 조회하는 경우.
- `client_id`와 `clients.agency_id`가 불일치하는 row 생성을 허용하는 경우.
- `client_unit_id`가 선택 고객사에 속하지 않는데 저장되는 경우.
- `task_id`, `receipt_id`, `event_id` 같은 path id만 보고 client 검증 없이 처리하는 경우.
- 창고 select가 전체 창고를 보여주고 API도 전체 창고를 허용하는 경우.
- import job은 권한 검증했지만 저장 확정 시 target 업무 row client 검증을 빠뜨리는 경우.
- Local Agent `scan_event`가 재고 이벤트를 직접 만드는 경우.
- `must_change_password=true` 사용자가 일반 업무 API를 호출하는 경우.
- 단건 상세 API에서 권한 검증 전 민감한 상세 데이터를 응답하는 경우.
- 고객사-창고 연결이 끊긴 창고로 반품/입고/출고 확정을 허용하는 경우.

## 11. 후속 구현 순서

1. `AuthContext` 모델/스키마
2. role seed
3. password 정책
4. agency scope dependency
5. client scope dependency
6. client_unit scope dependency
7. warehouse scope dependency
8. 기준정보 API 적용
9. import job API 적용
10. 반품 API 적용
11. 재고 API 적용
12. 프론트 agency/client/client_unit/warehouse 선택 유틸 적용

## 12. Codex 구현 전 체크

- 이 API는 어떤 role이 호출할 수 있는가?
- 이 API는 `agency_id` scope가 필요한가?
- 이 API는 `client_id` scope가 필요한가?
- 이 API는 `client_unit_id` scope가 필요한가?
- 이 API는 `warehouse_id` scope가 필요한가?
- 요청 `agency_id`를 그대로 믿고 있지 않은가?
- 요청 `client_id`를 그대로 믿고 있지 않은가?
- path id로 조회한 row의 `client_id`를 검증했는가?
- 고객사 사용자가 다른 고객사의 row를 볼 수 없는가?
- 확정/취소/정정/재고반영 같은 위험 작업에 추가 권한이 있는가?
- `must_change_password=true` 사용자를 차단하는가?
- 실패 시 데이터 변경이 발생하지 않는가?
